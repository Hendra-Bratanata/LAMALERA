#!/usr/bin/env python3
"""
Generate JSON data from CSV broker analysis files with ALL calculations included.
CSV files contain CUMULATIVE (YTD) data - need to calculate daily by subtracting previous day.
All standalone calculations (score, recommendation, buyZone, etc.) are done here in Python.
"""

import os
import json
from datetime import datetime
from collections import OrderedDict

# Shark brokers (institusional) - sesuai referensi broker_saham_indonesia.md
SHARK_BROKERS = {
    'AK', 'CC', 'BK', 'GW', 'AI', 'KZ', 'DX', 'DD', 'RX', 'KK', 'CG',
    'DR', 'TP', 'SQ', 'NI', 'CD', 'OD'
}

def parse_date_from_header(line):
    """Parse date from CSV header line."""
    try:
        parts = line.strip().split('\t')
        start_date = None
        end_date = None
        for i, part in enumerate(parts):
            if part == 'Start' and i + 1 < len(parts):
                start_date = parts[i + 1]
            elif part == 'End' and i + 1 < len(parts):
                end_date = parts[i + 1]
        return start_date, end_date
    except Exception as e:
        print(f"Error parsing date from header: {e}")
        return None, None

def format_date_for_display(date_str):
    """Convert YYYY-MM-DD to DD/MM/YYYY format for display"""
    if not date_str or date_str == 'Start':
        return date_str
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return date_str
    except:
        return date_str

def get_broker_name(code):
    """Get broker name from code"""
    broker_names = {
        'CC': 'Mandiri Sekuritas', 'XL': 'Stockbit', 'PD': 'IPOT',
        'YP': 'Mirae Asset', 'NI': 'BNI Sekuritas', 'KI': 'Kingsford',
        'SQ': 'BCA Sekuritas', 'DR': 'RHB/Danareksa', 'EP': 'MNC Sekuritas',
        'BK': 'JP Morgan', 'GR': 'Gundalah', 'ZP': 'Maybank Sekuritas',
        'YU': 'Yuanta Sekuritas', 'XC': 'Ajaib Sekuritas', 'AK': 'UBS Sekuritas',
        'KK': 'Phillip Sekuritas', 'OD': 'BRI Danareksa', 'AZ': 'Asia Trade',
        'DX': 'Bahana Sekuritas', 'TP': 'OCBC Sekuritas', 'AR': 'Artha Sekuritas',
        'XA': 'NH Korindo', 'YB': 'Yulie Sekuritas', 'DH': 'Sinarmas Sekuritas',
        'CP': 'Ciptadana Sekuritas', 'AT': 'Phintraco Sekuritas', 'YJ': 'Lotus Andalan',
        'HD': 'KGI Sekuritas', 'RG': 'RHB Sekuritas', 'BQ': 'Korea Investment',
        'HP': 'Hanson Sekuritas', 'IF': 'Samuel Sekuritas', 'MU': 'Mandiri Investasi',
        'LS': 'Lippo Sekuritas', 'AG': 'Agra Sekuritas', 'TF': 'Trust Sekuritas',
        'LG': 'Trimegah Sekuritas', 'MG': 'MNC Sekuritas', 'AI': 'UOB Kay Hian',
        'MR': 'Mandiri Manajemen', 'CM': 'CIMB Sekuritas', 'VS': 'Valbury Sekuritas',
        'YT': 'Yulie Sekuritas', 'PT': 'Pioneer Investama', 'NL': 'NASD',
        'MZ': 'MNC Sekuritas', 'TN': 'Trimegah Tbk', 'TH': 'Tech Sekuritas',
        'RX': 'Macquarie Sekuritas'
    }
    return broker_names.get(code, f'Broker {code}')

# ===== BEI TICK SIZE FUNCTIONS =====
def get_bei_tick_size(price):
    """Get BEI tick size based on price range"""
    if price <= 200:
        return 1
    elif price <= 500:
        return 2
    elif price <= 2000:
        return 5
    elif price <= 5000:
        return 10
    elif price <= 10000:
        return 25
    elif price <= 25000:
        return 50
    else:
        return 100

def round_to_bei_tick(price, round_down=True):
    """Round price to nearest tick"""
    tick = get_bei_tick_size(price)
    if round_down:
        rounded = (price // tick) * tick
    else:
        rounded = -(-price // tick) * tick  # ceil for positive numbers
    return max(rounded, tick)

def round_price_by_purpose(price, purpose):
    """Round price with safety margin based on purpose"""
    if purpose == 'buy':
        return round_to_bei_tick(price, True)
    elif purpose == 'target':
        return round_to_bei_tick(price, False)
    elif purpose == 'sell':
        return round_to_bei_tick(price, False)
    elif purpose == 'stoploss':
        return round_to_bei_tick(price, True)
    else:
        return round_to_bei_tick(price, True)

# ===== CALCULATION FUNCTIONS =====
def calculate_signals_and_recommendation(summary, daily):
    """Calculate score, signals, and recommendation"""
    s = summary
    score = 0
    signals = []
    shark_signal = 'neutral'
    retail_signal = 'neutral'
    price_trend = 'neutral'
    retail_bullish_reason = ''
    retail_bearish_reason = ''

    # ===== TRAPPED WHALE DETECTION =====
    is_whale_trapped = False
    whale_trap_level = 'none'  # none, mild, severe

    avg_whale_buy = s.get('whale_buyavg', 0)
    avg_whale_sell = s.get('whale_sellavg', 0)

    # Get last price (most recent whale buyavg as proxy)
    last_price = None
    for d in reversed(daily):
        if d.get('whale_buyavg', 0) > 0:
            last_price = d.get('whale_buyavg', 0)
            break

    if last_price and avg_whale_buy > 0:
        price_diff_ratio = (avg_whale_buy - last_price) / avg_whale_buy
        if price_diff_ratio > 0.20:  # More than 20% below = severely trapped
            is_whale_trapped = True
            whale_trap_level = 'severe'
            score -= 3  # Heavy penalty for severely trapped whale
            signals.append(f'⚠️ WHALE TERJEBAK BERAT (harga {price_diff_ratio*100:.0f}% di bawah rata-rata beli)')
        elif price_diff_ratio > 0.10:  # More than 10% below = mildly trapped
            is_whale_trapped = True
            whale_trap_level = 'mild'
            score -= 1  # Penalty for trapped whale
            signals.append(f'⚠️ Whale terjebak (harga {price_diff_ratio*100:.0f}% di bawah rata-rata beli)')
    else:
        signals.append('Status whale: Normal')

    # Signal 1: Shark accumulation/distribution
    whale_net = s.get('whale_net', 0)
    if whale_net > 5:
        shark_signal = 'bullish'
        score += 2
        signals.append('Whale sedang akumulasi kuat')
    elif whale_net > 1:
        shark_signal = 'bullish'
        score += 1
        signals.append('Whale sedang akumulasi moderat')
    elif whale_net < -5:
        shark_signal = 'bearish'
        score -= 2
        signals.append('Whale sedang distribusi kuat')
    elif whale_net < -1:
        shark_signal = 'bearish'
        score -= 1
        signals.append('Whale sedang distribusi moderat')
    else:
        signals.append('Whale netral/sideways')

    # Signal 2: Retail behavior (contrarian indicator)
    fishermen_net = s.get('retail_net', 0)
    if fishermen_net < -5:
        retail_signal = 'bullish'
        retail_bullish_reason = 'kontrarian'
        score += 1
        signals.append('Retail panic selling (kontrarian bullish)')
    elif fishermen_net < -1:
        retail_signal = 'bearish'
        retail_bearish_reason = 'distribusi'
        score -= 0.5
        signals.append('Retail distribusi')
    elif fishermen_net > 5:
        retail_signal = 'bearish'
        retail_bearish_reason = 'euforia'
        score -= 1
        signals.append('Retail euforia/akumulasi berlebih (tanda top)')
    elif fishermen_net > 1:
        retail_signal = 'bullish'
        retail_bullish_reason = 'akumulasi'
        score += 0.5
        signals.append('Retail akumulasi biasa')
    else:
        retail_signal = 'neutral'
        signals.append('Retail netral (sideways)')

    # Signal 3: Price trend (recent 5 days vs overall)
    if len(daily) >= 5:
        recent_5_days = daily[-5:]
    else:
        recent_5_days = daily

    avg_recent_buy = sum(d.get('whale_buyavg', 0) for d in recent_5_days) / len(recent_5_days) if recent_5_days else 0
    overall_avg_buy = s.get('whale_buyavg', 0)

    if overall_avg_buy > 0:
        if avg_recent_buy > overall_avg_buy * 1.02:
            price_trend = 'up'
            score += 0.5
            signals.append('Tren harga naik (5 hari terakhir)')
        elif avg_recent_buy < overall_avg_buy * 0.98:
            price_trend = 'down'
            score -= 0.5
            signals.append('Tren harga turun (5 hari terakhir)')
        else:
            signals.append('Tren harga stabil/sideways')

    # Signal 4: Shark pricing behavior
    avg_buy = s.get('whale_buyavg', 0)
    avg_sell = s.get('whale_sellavg', 0)
    if avg_buy > 0:
        if avg_sell > avg_buy * 1.05:
            score += 1
            signals.append('Whale jual di harga lebih tinggi (take profit)')
        elif avg_sell < avg_buy * 0.95:
            score -= 1
            signals.append('Whale jual di harga lebih rendah (cut loss)')

    # Determine strength
    if abs(score) >= 3:
        strength = 'strong'
    elif abs(score) >= 1.5:
        strength = 'moderate'
    else:
        strength = 'weak'

    # Final recommendation (with trapped whale consideration)
    if is_whale_trapped:
        # When whale is trapped, be more conservative
        if whale_trap_level == 'severe':
            recommendation = 'HOLD'  # Don't buy when whale is severely underwater
            signals.append('Rekomendasi: HOLD - Tunggu harga stabil di dekat area beli whale')
        elif whale_trap_level == 'mild':
            if score >= 2:
                recommendation = 'BUY'
                signals.append('Rekomendasi: BUY (spekulatif) - Whale terjebak ringan')
            else:
                recommendation = 'HOLD'
                signals.append('Rekomendasi: HOLD - Whale terjebak, tunggu konfirmasi')
        else:
            recommendation = 'HOLD'
    else:
        # Normal recommendation logic
        if score >= 2.5:
            recommendation = 'BUY'
        elif score >= 1:
            recommendation = 'BUY'
        elif score <= -2.5:
            recommendation = 'SELL'
        elif score <= -1:
            recommendation = 'SELL'
        else:
            recommendation = 'HOLD'

    return {
        'score': round(score, 2),
        'signals': signals,
        'whaleSignal': shark_signal,
        'retailSignal': retail_signal,
        'retailBullishReason': retail_bullish_reason,
        'retailBearishReason': retail_bearish_reason,
        'priceTrend': price_trend,
        'strength': strength,
        'recommendation': recommendation,
        'isWhaleTrapped': is_whale_trapped,
        'whaleTrapLevel': whale_trap_level,
        'lastPrice': last_price if last_price else avg_whale_buy,
        'avgWhaleBuy': avg_whale_buy
    }

def calculate_volatility_and_trend(daily, summary):
    """Calculate volatility, trend direction and strength"""
    all_shark_buy_prices = [d.get('whale_buyavg', 0) for d in daily if d.get('whale_buyavg', 0) > 0]
    all_shark_sell_prices = [d.get('whale_sellavg', 0) for d in daily if d.get('whale_sellavg', 0) > 0]

    if not all_shark_buy_prices:
        return {
            'volatilityFactor': 0.05,
            'trendDirection': 'SIDEWAYS',
            'trendStrength': 0,
            'minWhaleBuy': 0,
            'maxWhaleBuy': 0,
            'avgWhaleBuy': 0,
            'avgWhaleSell': 0,
            'lastWhaleBuyPrice': 0
        }

    min_shark_buy = min(all_shark_buy_prices)
    max_shark_buy = max(all_shark_buy_prices)
    avg_shark_buy = sum(all_shark_buy_prices) / len(all_shark_buy_prices)
    avg_shark_sell = sum(all_shark_sell_prices) / len(all_shark_sell_prices) if all_shark_sell_prices else 0

    # Volatility calculation
    price_range = max_shark_buy - min_shark_buy

    # Daily ranges (intraday high-low approximation)
    daily_ranges = []
    for d in daily:
        buy = d.get('whale_buyavg', 0)
        sell = d.get('whale_sellavg', 0)
        if buy > 0 and sell > buy:
            daily_ranges.append((sell - buy) / buy)

    avg_daily_range = sum(daily_ranges) / len(daily_ranges) if daily_ranges else 0.02

    # Combined volatility factor
    range_volatility = price_range / avg_shark_buy if avg_shark_buy > 0 else 0.05
    volatility_factor = max(range_volatility, avg_daily_range)

    # Trend analysis
    mid_point = len(daily) // 2
    first_half = daily[:mid_point] if mid_point > 0 else daily
    second_half = daily[mid_point:] if mid_point > 0 else daily

    first_half_avg_buy = sum(d.get('whale_buyavg', 0) for d in first_half) / len(first_half) if first_half else 0
    second_half_avg_buy = sum(d.get('whale_buyavg', 0) for d in second_half) / len(second_half) if second_half else 0

    if first_half_avg_buy > 0:
        trend_percent = ((second_half_avg_buy - first_half_avg_buy) / first_half_avg_buy) * 100
    else:
        trend_percent = 0

    if trend_percent > 2:
        trend_direction = 'UPTREND'
    elif trend_percent < -2:
        trend_direction = 'DOWNTREND'
    else:
        trend_direction = 'SIDEWAYS'

    trend_strength = abs(trend_percent)

    return {
        'volatilityFactor': round(volatility_factor, 4),
        'trendDirection': trend_direction,
        'trendStrength': round(trend_strength, 2),
        'minWhaleBuy': round(min_shark_buy, 2),
        'maxWhaleBuy': round(max_shark_buy, 2),
        'avgWhaleBuy': round(avg_shark_buy, 2),
        'avgWhaleSell': round(avg_shark_sell, 2),
        'lastWhaleBuyPrice': round(all_shark_buy_prices[-1], 2) if all_shark_buy_prices else 0
    }

def calculate_price_recommendations(summary, daily, vt_data, signal_data):
    """Calculate buyZone, targetPrice, sellZone, stopLoss with BEI tick size"""
    all_shark_buy_prices = [d.get('whale_buyavg', 0) for d in daily if d.get('whale_buyavg', 0) > 0]
    all_shark_sell_prices = [d.get('whale_sellavg', 0) for d in daily if d.get('whale_sellavg', 0) > 0]

    if not all_shark_buy_prices or not all_shark_sell_prices:
        return {
            'buyZone': None,
            'targetPrice': None,
            'sellZone': None,
            'stopLoss': None,
            'rrRatio': 0,
            'potentialProfit': 0,
            'potentialLoss': 0
        }

    min_shark_buy = vt_data['minWhaleBuy']
    max_shark_buy = vt_data['maxWhaleBuy']
    avg_shark_buy = vt_data['avgWhaleBuy']
    avg_shark_sell = vt_data['avgWhaleSell']
    volatility_factor = vt_data['volatilityFactor']
    trend_direction = vt_data['trendDirection']

    # Get trapped whale status from signal_data
    is_whale_trapped = signal_data.get('isWhaleTrapped', False)
    whale_trap_level = signal_data.get('whaleTrapLevel', 'none')
    last_price = signal_data.get('lastPrice', avg_shark_buy)

    # Get recent 5 days
    if len(daily) >= 5:
        recent_5_days = daily[-5:]
    else:
        recent_5_days = daily

    recent_buy_prices = [d.get('whale_buyavg', 0) for d in recent_5_days if d.get('whale_buyavg', 0) > 0]
    lowest_recent_buy = min(recent_buy_prices) if recent_buy_prices else min_shark_buy

    # VWAP calculation
    weighted_buy_sum = 0
    total_buy_weight = 0
    for d in daily:
        shark_buyavg = d.get('whale_buyavg', 0)
        shark_buy = d.get('whale_buy', 0)
        if shark_buyavg > 0 and shark_buy > 0:
            weighted_buy_sum += shark_buyavg * shark_buy
            total_buy_weight += shark_buy

    vwap_buy_price = weighted_buy_sum / total_buy_weight if total_buy_weight > 0 else avg_shark_buy

    # ===== CRITICAL FIX: Trapped Whale Detection =====
    if is_whale_trapped:
        # When whale is trapped, buy zone should be based on CURRENT price + premium
        # NOT on whale's historical average (which is too high)
        trapped_buy_premium = max(0.02, min(0.05, volatility_factor * 0.5))
        buy_zone = last_price * (1 + trapped_buy_premium)

        # Override stop loss for trapped scenario - closer to current price
        structure_stop_loss = last_price * 0.95
    else:
        # Normal logic when whale is NOT trapped
        discount_percent = max(0.02, min(0.06, volatility_factor * 0.6))
        discount_buy_zone = vwap_buy_price * (1 - discount_percent)

        buy_zone = max(
            discount_buy_zone,
            lowest_recent_buy * 0.98,
            min_shark_buy * 1.01
        )
        structure_stop_loss = lowest_recent_buy * 0.97

    # Target price calculation
    base_target = avg_shark_sell

    # Resistance zones
    resistance_levels = [d for d in daily if d.get('whale_sellavg', 0) > avg_shark_sell * 1.02]
    if resistance_levels:
        strong_resistance = sum(d.get('whale_sellavg', 0) for d in resistance_levels) / len(resistance_levels)
    else:
        strong_resistance = avg_shark_sell

    # Risk amount
    risk_percent = max(0.03, min(0.05, volatility_factor))
    risk_amount = buy_zone * risk_percent

    target_1_rr = buy_zone + (risk_amount * 1.5)
    target_2_rr = buy_zone + (risk_amount * 2.5)
    target_3_rr = buy_zone + (risk_amount * 4)

    # ===== TRAPPED WHALE: Conservative target =====
    if is_whale_trapped:
        # When whale is trapped, target should be realistic
        # Aim for whale's breakeven (avg_buy) or slightly below avg_sell
        trapped_target = min(avg_shark_buy, avg_shark_sell)

        # But also consider buy_zone + reasonable profit (10-20%)
        trapped_target_from_entry = buy_zone * 1.15

        # Use the lower of the two - more conservative
        target_price = min(trapped_target, trapped_target_from_entry)

        # Sell zone should also be conservative when trapped
        sell_zone = min(
            avg_shark_buy * 1.03,  # Just 3% above whale avg (breakeven area)
            avg_shark_sell,           # Or at whale sell average
            buy_zone * 1.20          # Max 20% from entry
        )
    else:
        # Normal target calculation when whale is NOT trapped
        target_price = min(base_target, strong_resistance, target_2_rr)

        # Sell zone calculation
        high_sell_activity_days = [
            d for d in daily
            if d.get('whale_sell', 0) > d.get('whale_buy', 0) * 1.5 and d.get('whale_sellavg', 0) > avg_shark_buy
        ]

        if high_sell_activity_days:
            distribution_zone = sum(d.get('whale_sellavg', 0) for d in high_sell_activity_days) / len(high_sell_activity_days)
        else:
            distribution_zone = avg_shark_sell

        sell_zone = max(
            distribution_zone,
            avg_shark_sell * 1.02,
            max_shark_buy * 1.05
        )

    # Daily ranges for ATR-like calculation
    daily_ranges = []
    for d in daily:
        buy = d.get('whale_buyavg', 0)
        sell = d.get('whale_sellavg', 0)
        if buy > 0 and sell > buy:
            daily_ranges.append((sell - buy) / buy)

    avg_daily_range = sum(daily_ranges) / len(daily_ranges) if daily_ranges else 0.02
    atr_multiplier = max(1.5, min(2.5, volatility_factor * 20))
    volatility_stop_loss = buy_zone - (buy_zone * avg_daily_range * atr_multiplier)

    # Percentage-based with trend adjustment
    base_stop_percent = max(0.03, min(0.05, volatility_factor))
    if trend_direction == 'UPTREND':
        base_stop_percent *= 1.2
    elif trend_direction == 'DOWNTREND':
        base_stop_percent *= 0.8

    percentage_stop_loss = buy_zone * (1 - base_stop_percent)

    # Final stop loss
    stop_loss = max(structure_stop_loss, volatility_stop_loss, percentage_stop_loss)

    # Apply BEI tick size rounding
    buy_zone = round_price_by_purpose(buy_zone, 'buy')
    target_price = round_price_by_purpose(target_price, 'target')
    sell_zone = round_price_by_purpose(sell_zone, 'sell')
    stop_loss = round_price_by_purpose(stop_loss, 'stoploss')

    # Validate stop loss gap (minimum 3% from buy zone)
    min_stop_gap = buy_zone * 0.03
    if (buy_zone - stop_loss) < min_stop_gap:
        stop_loss = buy_zone - min_stop_gap

    # Calculate R:RR and potentials
    rr_ratio = (target_price - buy_zone) / (buy_zone - stop_loss) if (buy_zone - stop_loss) > 0 else 0
    potential_profit = round(((target_price - buy_zone) / buy_zone * 100), 1)
    potential_loss = round(((buy_zone - stop_loss) / buy_zone * 100), 1)

    # Get tick sizes
    buy_tick = get_bei_tick_size(buy_zone)
    target_tick = get_bei_tick_size(target_price)
    sell_tick = get_bei_tick_size(sell_zone)
    stop_tick = get_bei_tick_size(stop_loss)

    return {
        'buyZone': round(buy_zone, 0),
        'targetPrice': round(target_price, 0),
        'sellZone': round(sell_zone, 0),
        'stopLoss': round(stop_loss, 0),
        'rrRatio': round(rr_ratio, 2),
        'displayRR': round(min(rr_ratio, 10), 1),
        'potentialProfit': potential_profit,
        'potentialLoss': potential_loss,
        'discountPercent': round(discount_percent if not is_whale_trapped else trapped_buy_premium, 4),
        'isWhaleTrapped': is_whale_trapped,
        'whaleTrapLevel': whale_trap_level,
        'lastPrice': round(last_price, 0),
        'avgWhaleBuy': round(avg_shark_buy, 0),
        'buyTick': buy_tick,
        'targetTick': target_tick,
        'sellTick': sell_tick,
        'stopTick': stop_tick,
        'lowestRecentBuy': round(round_to_bei_tick(lowest_recent_buy, True), 0),
        'strongResistance': round(round_to_bei_tick(strong_resistance, False), 0),
        'minWhaleBuyTick': round(round_to_bei_tick(min_shark_buy, True), 0),
        'maxWhaleBuyTick': round(round_to_bei_tick(max_shark_buy, False), 0)
    }

def calculate_confidence_score(summary, vt_data, signal_data, price_data, recommendation):
    """Calculate confidence score (0-100) and factors"""
    confidence_score = 0
    confidence_factors = []

    shark_net = summary.get('whale_net', 0)
    trend_direction = vt_data['trendDirection']
    rr_ratio = price_data.get('rrRatio', 0)
    min_shark_buy = vt_data['minWhaleBuy']
    max_shark_buy = vt_data['maxWhaleBuy']
    avg_shark_buy = vt_data['avgWhaleBuy']
    volatility_factor = vt_data['volatilityFactor']

    # Factor 1: Shark accumulation strength
    if shark_net > 5:
        confidence_score += 25
        confidence_factors.append('Akumulasi Whale kuat')
    elif shark_net > 1:
        confidence_score += 15
        confidence_factors.append('Akumulasi Whale moderat')

    # Factor 2: Trend alignment
    if trend_direction == 'UPTREND' and recommendation == 'BUY':
        confidence_score += 20
        confidence_factors.append('Trend naik, align dengan BUY')
    elif trend_direction == 'DOWNTREND' and recommendation == 'SELL':
        confidence_score += 20
        confidence_factors.append('Trend turun, align dengan SELL')
    elif trend_direction == 'SIDEWAYS':
        confidence_score += 5
        confidence_factors.append('Market sideways, waspada')

    # Factor 3: Risk-Reward Ratio
    display_rr = price_data.get('displayRR', 0)
    if rr_ratio >= 3:
        confidence_score += 20
        confidence_factors.append(f"R:RR excellent ({display_rr}:1)")
    elif rr_ratio >= 2:
        confidence_score += 15
        confidence_factors.append(f"R:RR baik ({display_rr}:1)")
    elif rr_ratio >= 1.5:
        confidence_score += 10
        confidence_factors.append(f"R:RR moderat ({display_rr}:1)")
    else:
        confidence_score -= 10
        confidence_factors.append(f"R:RR kurang ideal ({display_rr}:1)")

    # Factor 4: Price position in range
    if max_shark_buy > min_shark_buy:
        price_position = (avg_shark_buy - min_shark_buy) / (max_shark_buy - min_shark_buy)
        if price_position < 0.3:
            confidence_score += 15
            confidence_factors.append('Harga dekat support bawah')
        elif price_position > 0.7:
            confidence_score -= 10
            confidence_factors.append('Harga dekat resistance atas')

    # Factor 5: Volatility check
    if volatility_factor < 0.05:
        confidence_score += 10
        confidence_factors.append('Volatilitas rendah (stable)')
    elif volatility_factor > 0.15:
        confidence_score -= 10
        confidence_factors.append('Volatilitas tinggi (risky)')

    # Clamp confidence score
    confidence_score = max(0, min(100, confidence_score))

    if confidence_score >= 70:
        confidence_level = 'TINGGI'
    elif confidence_score >= 50:
        confidence_level = 'SEDANG'
    else:
        confidence_level = 'RENDAH'

    return {
        'confidenceScore': confidence_score,
        'confidenceLevel': confidence_level,
        'confidenceFactors': confidence_factors
    }

def generate_insights(summary, daily, vt_data):
    """Generate shark and retail insights"""
    days = len(daily)

    # Find peaks
    shark_peak = -float('inf')
    shark_peak_day = 0
    retail_peak = -float('inf')
    retail_peak_day = 0

    for d in daily:
        if d.get('whale_cum_net', 0) > shark_peak:
            shark_peak = d.get('whale_cum_net', 0)
            shark_peak_day = d.get('day', 0)
        if d.get('retail_cum_net', 0) > retail_peak:
            retail_peak = d.get('retail_cum_net', 0)
            retail_peak_day = d.get('day', 0)

    whale_net = summary.get('whale_net', 0)
    fishermen_net = summary.get('retail_net', 0)

    # Shark insight
    if whale_net < 0:
        shark_insight = f"Whale melakukan <span class=\"highlight\">DISTRIBUSI</span> sebesar <span class=\"highlight\">Rp {abs(whale_net):.1f} Miliar</span> dalam {days} hari transaksi. "
        if shark_peak_day > 0:
            shark_insight += f"Puncak akumulasi tercapai di hari ke-{shark_peak_day} (+{shark_peak:.1f} M), setelah itu mulai distribusi bertahap. "
        shark_insight += "Ini mengindikasikan <span class=\"highlight\">take profit</span> oleh institusi besar."
    else:
        shark_insight = f"Whale melakukan <span class=\"highlight\">AKUMULASI</span> sebesar <span class=\"highlight\">Rp {whale_net:.1f} Miliar</span> dalam {days} hari transaksi. Institusi sedang membeli saham ini."

    # Retail insight
    if fishermen_net > 0:
        retail_insight = f"Retail melakukan <span class=\"highlight\">AKUMULASI</span> sebesar <span class=\"highlight\">Rp {fishermen_net:.1f} Miliar</span> dalam {days} hari transaksi. "
        if retail_peak_day > 0:
            retail_insight += f"Puncak akumulasi di hari ke-{retail_peak_day} (+{retail_peak:.1f} M). "
        retail_insight += "Ini menunjukkan minat beli yang kuat dari investor retail."
    else:
        retail_insight = f"Retail melakukan <span class=\"highlight\">DISTRIBUSI</span> sebesar <span class=\"highlight\">Rp {abs(fishermen_net):.1f} Miliar</span> dalam {days} hari transaksi. Investor retail sedang profit taking."

    return {
        'whaleInsight': shark_insight,
        'retailInsight': retail_insight,
        'whalePeak': round(shark_peak, 2),
        'whalePeakDay': shark_peak_day,
        'retailPeak': round(retail_peak, 2),
        'retailPeakDay': retail_peak_day
    }

def read_csv_file_cumulative(file_path):
    """Read CSV file and extract CUMULATIVE values per broker."""
    result = {
        'date_start': None,
        'date_end': None,
        'date_display': None,
        'whale_buyavg': 0,
        'whale_sellavg': 0,
        'retail_buyavg': 0,
        'retail_sellavg': 0,
        'brokers': {}
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) > 0:
            start_date, end_date = parse_date_from_header(lines[0])
            result['date_start'] = start_date
            result['date_end'] = end_date
            if start_date:
                result['date_display'] = format_date_for_display(start_date)

        data_start_idx = 3

        shark_total_buy_val = 0
        shark_total_sell_val = 0
        shark_total_buy_avg = 0
        shark_total_sell_avg = 0
        retail_total_buy_val = 0
        retail_total_sell_val = 0
        retail_total_buy_avg = 0
        retail_total_sell_avg = 0

        for line in lines[data_start_idx:]:
            line = line.strip()
            if not line or '\t' not in line:
                continue

            parts = line.split('\t')
            if len(parts) < 9:
                continue

            broker_code = parts[0].strip().upper()
            if not broker_code or broker_code in ['BY', 'Board', ''] or len(broker_code) > 3:
                continue

            if broker_code not in result['brokers']:
                result['brokers'][broker_code] = {'buy': 0, 'sell': 0, 'buyavg': 0, 'sellavg': 0, 'buy_lot': 0, 'sell_lot': 0}

            try:
                buy_lot_str = parts[1].replace(',', '') if parts[1] else '0'
                buy_lot = float(buy_lot_str)
                buy_val_str = parts[2].replace(',', '')
                buy_val = float(buy_val_str) / 1_000_000_000
                buy_avg = float(parts[3]) if parts[3] else 0
            except (ValueError, IndexError):
                buy_lot = 0
                buy_val = 0
                buy_avg = 0

            try:
                sell_lot_str = parts[6].replace(',', '') if len(parts) > 6 else '0'
                sell_lot = float(sell_lot_str)
                sell_val_str = parts[7].replace(',', '') if len(parts) > 7 else '0'
                sell_val = float(sell_val_str) / 1_000_000_000
                sell_avg = float(parts[8]) if len(parts) > 8 else 0
            except (ValueError, IndexError):
                sell_lot = 0
                sell_val = 0
                sell_avg = 0

            result['brokers'][broker_code]['buy'] = buy_val
            result['brokers'][broker_code]['sell'] = sell_val
            result['brokers'][broker_code]['buyavg'] = buy_avg
            result['brokers'][broker_code]['sellavg'] = sell_avg
            result['brokers'][broker_code]['buy_lot'] = buy_lot
            result['brokers'][broker_code]['sell_lot'] = sell_lot

            if broker_code in SHARK_BROKERS:
                shark_total_buy_val += buy_val
                shark_total_sell_val += sell_val
                shark_total_buy_avg += buy_avg * buy_val
                shark_total_sell_avg += sell_avg * sell_val
            else:
                retail_total_buy_val += buy_val
                retail_total_sell_val += sell_val
                retail_total_buy_avg += buy_avg * buy_val
                retail_total_sell_avg += sell_avg * sell_val

        if shark_total_buy_val > 0:
            result['whale_buyavg'] = shark_total_buy_avg / shark_total_buy_val
        if shark_total_sell_val > 0:
            result['whale_sellavg'] = shark_total_sell_avg / shark_total_sell_val
        if retail_total_buy_val > 0:
            result['retail_buyavg'] = retail_total_buy_avg / retail_total_buy_val
        if retail_total_sell_val > 0:
            result['retail_sellavg'] = retail_total_sell_avg / retail_total_sell_val

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return result

def scan_stock_folder(stock_path):
    """Scan all CSV files in stock folder and its subfolders."""
    import re
    csv_files = []

    def extract_date_from_path(path, folder_name):
        month = None
        if 'JAN' in folder_name:
            month = '01'
        elif 'FEB' in folder_name:
            month = '02'
        elif 'MAR' in folder_name:
            month = '03'
        elif 'APR' in folder_name:
            month = '04'
        elif 'MAY' in folder_name:
            month = '05'
        elif 'JUN' in folder_name:
            month = '06'
        elif 'JUL' in folder_name:
            month = '07'
        elif 'AUG' in folder_name:
            month = '08'
        elif 'SEP' in folder_name:
            month = '09'
        elif 'OCT' in folder_name:
            month = '10'
        elif 'NOV' in folder_name:
            month = '11'
        elif 'DEC' in folder_name or 'DES' in folder_name:
            month = '12'

        year_match = re.search(r'(\d{2,4})$', folder_name)
        if year_match:
            year_suffix = year_match.group(1)
            if len(year_suffix) == 2:
                year = '20' + year_suffix
            else:
                year = year_suffix
        else:
            year = '2026'

        filename = os.path.basename(path).replace('.csv', '')
        try:
            day = int(filename)
            day_str = f"{day:02d}"
        except ValueError:
            return None

        if month and year and day:
            return f"{year}-{month}-{day_str}"
        return None

    for root, dirs, files in os.walk(stock_path):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                folder_name = os.path.basename(root)
                date_str = extract_date_from_path(file_path, folder_name)
                if date_str:
                    csv_files.append((file_path, date_str, file))

    csv_files.sort(key=lambda x: x[1] if x[1] else '9999-99-99')
    return csv_files

def process_stock_folder(stock_code, base_path):
    """Process all CSV files for a stock with all calculations"""
    stock_path = os.path.join(base_path, stock_code)

    if not os.path.exists(stock_path):
        print(f"Folder not found: {stock_path}")
        return None

    csv_files = scan_stock_folder(stock_path)

    if not csv_files:
        print(f"No CSV files found in {stock_path}")
        return None

    print(f"  Found {len(csv_files)} CSV files")

    cumulative_data = []
    for file_path, date_str, filename in csv_files:
        data = read_csv_file_cumulative(file_path)
        data['date_start'] = date_str
        if data['date_start']:
            data['date_display'] = format_date_for_display(data['date_start'])
        cumulative_data.append(data)

    daily_data = []
    prev_cumulative = {}

    total_shark_cum_buy = 0
    total_shark_cum_sell = 0
    total_retail_cum_buy = 0
    total_retail_cum_sell = 0

    total_shark_buyavg_weighted = 0
    total_shark_sellavg_weighted = 0
    total_retail_buyavg_weighted = 0
    total_retail_sellavg_weighted = 0

    total_shark_cum_buy_lot = 0
    total_shark_cum_sell_lot = 0
    total_retail_cum_buy_lot = 0
    total_retail_cum_sell_lot = 0

    total_shark_buy_lot_for_avg = 0
    total_shark_sell_lot_for_avg = 0
    total_retail_buy_lot_for_avg = 0
    total_retail_sell_lot_for_avg = 0

    all_brokers_data = {}

    for i, cum_data in enumerate(cumulative_data):
        day_num = i + 1

        daily_shark_buy = 0
        daily_shark_sell = 0
        daily_retail_buy = 0
        daily_retail_sell = 0
        daily_shark_buy_lot = 0
        daily_shark_sell_lot = 0
        daily_retail_buy_lot = 0
        daily_retail_sell_lot = 0

        daily_shark_buyavg_weighted = 0
        daily_shark_sellavg_weighted = 0
        daily_retail_buyavg_weighted = 0
        daily_retail_sellavg_weighted = 0

        for broker_code, broker_cum in cum_data['brokers'].items():
            prev_buy = prev_cumulative.get(broker_code, {}).get('buy', 0)
            prev_sell = prev_cumulative.get(broker_code, {}).get('sell', 0)
            prev_buy_lot = prev_cumulative.get(broker_code, {}).get('buy_lot', 0)
            prev_sell_lot = prev_cumulative.get(broker_code, {}).get('sell_lot', 0)

            if broker_cum['buy'] < prev_buy or prev_buy == 0:
                daily_buy = broker_cum['buy']
            else:
                daily_buy = broker_cum['buy'] - prev_buy

            if broker_cum['sell'] < prev_sell or prev_sell == 0:
                daily_sell = broker_cum['sell']
            else:
                daily_sell = broker_cum['sell'] - prev_sell

            if broker_cum.get('buy_lot', 0) < prev_buy_lot or prev_buy_lot == 0:
                daily_buy_lot = broker_cum.get('buy_lot', 0)
            else:
                daily_buy_lot = broker_cum.get('buy_lot', 0) - prev_buy_lot

            if broker_cum.get('sell_lot', 0) < prev_sell_lot or prev_sell_lot == 0:
                daily_sell_lot = broker_cum.get('sell_lot', 0)
            else:
                daily_sell_lot = broker_cum.get('sell_lot', 0) - prev_sell_lot

            daily_buyavg = broker_cum.get('buyavg', 0)
            daily_sellavg = broker_cum.get('sellavg', 0)

            buy_lot_for_avg = daily_buy_lot if daily_buy_lot > 0 else 0
            sell_lot_for_avg = daily_sell_lot if daily_sell_lot > 0 else 0

            if broker_code not in all_brokers_data:
                category = 'whale' if broker_code in SHARK_BROKERS else 'retail'
                all_brokers_data[broker_code] = {
                    'code': broker_code,
                    'name': get_broker_name(broker_code),
                    'category': category,
                    'buy': 0,
                    'sell': 0,
                    'buyavg': 0,
                    'sellavg': 0,
                    'buyavg_weighted': 0,
                    'sellavg_weighted': 0
                }

            if daily_buy > 0 or daily_sell > 0:
                all_brokers_data[broker_code]['buy'] += daily_buy
                all_brokers_data[broker_code]['sell'] += daily_sell
                all_brokers_data[broker_code]['buyavg'] = daily_buyavg
                all_brokers_data[broker_code]['sellavg'] = daily_sellavg
                all_brokers_data[broker_code]['buyavg_weighted'] = (
                    all_brokers_data[broker_code].get('buyavg_weighted', 0) + daily_buyavg * daily_buy
                )
                all_brokers_data[broker_code]['sellavg_weighted'] = (
                    all_brokers_data[broker_code].get('sellavg_weighted', 0) + daily_sellavg * daily_sell
                )

            if broker_code in SHARK_BROKERS:
                daily_shark_buy += daily_buy
                daily_shark_sell += daily_sell
                daily_shark_buy_lot += daily_buy_lot
                daily_shark_sell_lot += daily_sell_lot
                if buy_lot_for_avg > 0:
                    daily_shark_buyavg_weighted += daily_buyavg * buy_lot_for_avg
                if sell_lot_for_avg > 0:
                    daily_shark_sellavg_weighted += daily_sellavg * sell_lot_for_avg
            else:
                daily_retail_buy += daily_buy
                daily_retail_sell += daily_sell
                daily_retail_buy_lot += daily_buy_lot
                daily_retail_sell_lot += daily_sell_lot
                if buy_lot_for_avg > 0:
                    daily_retail_buyavg_weighted += daily_buyavg * buy_lot_for_avg
                if sell_lot_for_avg > 0:
                    daily_retail_sellavg_weighted += daily_sellavg * sell_lot_for_avg

        today_shark_buy_lot = 0
        today_shark_sell_lot = 0
        today_retail_buy_lot = 0
        today_retail_sell_lot = 0

        for broker_code in cum_data['brokers']:
            if broker_code not in prev_cumulative:
                lot = cum_data['brokers'][broker_code].get('buy_lot', 0)
            else:
                curr_lot = cum_data['brokers'][broker_code].get('buy_lot', 0)
                prev_lot = prev_cumulative[broker_code].get('buy_lot', 0)
                if curr_lot < prev_lot or prev_lot == 0:
                    lot = curr_lot
                else:
                    lot = curr_lot - prev_lot

            if broker_code in SHARK_BROKERS:
                today_shark_buy_lot += max(0, lot)

        for broker_code in cum_data['brokers']:
            if broker_code not in prev_cumulative:
                lot = cum_data['brokers'][broker_code].get('sell_lot', 0)
            else:
                curr_lot = cum_data['brokers'][broker_code].get('sell_lot', 0)
                prev_lot = prev_cumulative[broker_code].get('sell_lot', 0)
                if curr_lot < prev_lot or prev_lot == 0:
                    lot = curr_lot
                else:
                    lot = curr_lot - prev_lot

            if broker_code in SHARK_BROKERS:
                today_shark_sell_lot += max(0, lot)
            else:
                today_retail_sell_lot += max(0, lot)

        for broker_code in cum_data['brokers']:
            if broker_code not in prev_cumulative:
                lot = cum_data['brokers'][broker_code].get('buy_lot', 0)
            else:
                curr_lot = cum_data['brokers'][broker_code].get('buy_lot', 0)
                prev_lot = prev_cumulative[broker_code].get('buy_lot', 0)
                if curr_lot < prev_lot or prev_lot == 0:
                    lot = curr_lot
                else:
                    lot = curr_lot - prev_lot

            if broker_code not in SHARK_BROKERS:
                today_retail_buy_lot += max(0, lot)

        daily_shark_buyavg = daily_shark_buyavg_weighted / today_shark_buy_lot if today_shark_buy_lot > 0 else 0
        daily_shark_sellavg = daily_shark_sellavg_weighted / today_shark_sell_lot if today_shark_sell_lot > 0 else 0
        daily_retail_buyavg = daily_retail_buyavg_weighted / today_retail_buy_lot if today_retail_buy_lot > 0 else 0
        daily_retail_sellavg = daily_retail_sellavg_weighted / today_retail_sell_lot if today_retail_sell_lot > 0 else 0

        total_shark_cum_buy += daily_shark_buy
        total_shark_cum_sell += daily_shark_sell
        total_retail_cum_buy += daily_retail_buy
        total_retail_cum_sell += daily_retail_sell
        total_shark_cum_buy_lot += daily_shark_buy_lot
        total_shark_cum_sell_lot += daily_shark_sell_lot
        total_retail_cum_buy_lot += daily_retail_buy_lot
        total_retail_cum_sell_lot += daily_retail_sell_lot

        if today_shark_buy_lot > 0:
            total_shark_buyavg_weighted += daily_shark_buyavg * today_shark_buy_lot
        if today_shark_sell_lot > 0:
            total_shark_sellavg_weighted += daily_shark_sellavg * today_shark_sell_lot
        if today_retail_buy_lot > 0:
            total_retail_buyavg_weighted += daily_retail_buyavg * today_retail_buy_lot
        if today_retail_sell_lot > 0:
            total_retail_sellavg_weighted += daily_retail_sellavg * today_retail_sell_lot

        total_shark_buy_lot_for_avg += today_shark_buy_lot
        total_shark_sell_lot_for_avg += today_shark_sell_lot
        total_retail_buy_lot_for_avg += today_retail_buy_lot
        total_retail_sell_lot_for_avg += today_retail_sell_lot

        shark_net = daily_shark_buy - daily_shark_sell
        retail_net = daily_retail_buy - daily_retail_sell
        shark_net_lot = total_shark_cum_buy_lot - total_shark_cum_sell_lot
        retail_net_lot = total_retail_cum_buy_lot - total_retail_cum_sell_lot

        daily_data.append({
            'day': day_num,
            'date': cum_data['date_start'] or 'Unknown',
            'date_display': cum_data['date_display'] or 'Unknown',
            'date_end': cum_data['date_end'] or 'Unknown',
            'whale_buy': round(daily_shark_buy, 2),
            'retail_buy': round(daily_retail_buy, 2),
            'whale_sell': round(daily_shark_sell, 2),
            'retail_sell': round(daily_retail_sell, 2),
            'whale_buyavg': round(daily_shark_buyavg, 2),
            'whale_sellavg': round(daily_shark_sellavg, 2),
            'retail_buyavg': round(daily_retail_buyavg, 2),
            'retail_sellavg': round(daily_retail_sellavg, 2),
            'whale_cum_buy': round(total_shark_cum_buy, 2),
            'retail_cum_buy': round(total_retail_cum_buy, 2),
            'whale_cum_sell': round(total_shark_cum_sell, 2),
            'retail_cum_sell': round(total_retail_cum_sell, 2),
            'whale_net': round(shark_net, 2),
            'retail_net': round(retail_net, 2),
            'whale_cum_net': round(total_shark_cum_buy - total_shark_cum_sell, 2),
            'retail_cum_net': round(total_retail_cum_buy - total_retail_cum_sell, 2),
            'whale_cum_buy_lot': round(total_shark_cum_buy_lot),
            'whale_cum_sell_lot': round(total_shark_cum_sell_lot),
            'retail_cum_buy_lot': round(total_retail_cum_buy_lot),
            'retail_cum_sell_lot': round(total_retail_cum_sell_lot),
            'whale_net_lot': round(shark_net_lot),
            'retail_net_lot': round(retail_net_lot)
        })

        prev_cumulative = cum_data['brokers']

    summary_shark_buyavg = total_shark_buyavg_weighted / total_shark_buy_lot_for_avg if total_shark_buy_lot_for_avg > 0 else 0
    summary_shark_sellavg = total_shark_sellavg_weighted / total_shark_sell_lot_for_avg if total_shark_sell_lot_for_avg > 0 else 0
    summary_retail_buyavg = total_retail_buyavg_weighted / total_retail_buy_lot_for_avg if total_retail_buy_lot_for_avg > 0 else 0
    summary_retail_sellavg = total_retail_sellavg_weighted / total_retail_sell_lot_for_avg if total_retail_sell_lot_for_avg > 0 else 0

    first_date = daily_data[0]['date'] if daily_data else 'Unknown'
    last_date = daily_data[-1].get('date_end', daily_data[-1].get('date', 'Unknown')) if daily_data else 'Unknown'

    brokers_list = []
    for code, data in all_brokers_data.items():
        data['net'] = round(data['buy'] - data['sell'], 2)
        data['total'] = round(data['buy'] + data['sell'], 2)
        data['buy'] = round(data['buy'], 2)
        data['sell'] = round(data['sell'], 2)
        data['buyavg'] = round(data.get('buyavg_weighted', data['buy']) / data['buy'], 2) if data['buy'] > 0 else 0
        data['sellavg'] = round(data.get('sellavg_weighted', data['sell']) / data['sell'], 2) if data['sell'] > 0 else 0
        brokers_list.append(data)

    brokers_list.sort(key=lambda x: x['total'], reverse=True)

    # Build summary
    summary = {
        'whale_buy': round(total_shark_cum_buy, 2),
        'retail_buy': round(total_retail_cum_buy, 2),
        'whale_sell': round(total_shark_cum_sell, 2),
        'retail_sell': round(total_retail_cum_sell, 2),
        'whale_buyavg': round(summary_shark_buyavg, 2),
        'retail_buyavg': round(summary_retail_buyavg, 2),
        'whale_sellavg': round(summary_shark_sellavg, 2),
        'retail_sellavg': round(summary_retail_sellavg, 2),
        'whale_net': round(total_shark_cum_buy - total_shark_cum_sell, 2),
        'retail_net': round(total_retail_cum_buy - total_retail_cum_sell, 2),
        'total_buy': round(total_shark_cum_buy + total_retail_cum_buy, 2),
        'total_sell': round(total_shark_cum_sell + total_retail_cum_sell, 2),
        'whale_cum_buy_lot': round(total_shark_cum_buy_lot),
        'whale_cum_sell_lot': round(total_shark_cum_sell_lot),
        'retail_cum_buy_lot': round(total_retail_cum_buy_lot),
        'retail_cum_sell_lot': round(total_retail_cum_sell_lot),
        'whale_net_lot': round(total_shark_cum_buy_lot - total_shark_cum_sell_lot),
        'retail_net_lot': round(total_retail_cum_buy_lot - total_retail_cum_sell_lot)
    }

    # ===== ALL CALCULATIONS DONE IN PYTHON =====

    # 1. Calculate signals and recommendation
    signal_data = calculate_signals_and_recommendation(summary, daily_data)

    # 2. Calculate volatility and trend
    vt_data = calculate_volatility_and_trend(daily_data, summary)

    # 3. Calculate price recommendations
    price_data = calculate_price_recommendations(summary, daily_data, vt_data, signal_data)

    # 4. Calculate confidence score
    confidence_data = calculate_confidence_score(summary, vt_data, signal_data, price_data, signal_data['recommendation'])

    # 5. Generate insights
    insights_data = generate_insights(summary, daily_data, vt_data)

    return {
        'code': stock_code,
        'date_start': first_date,
        'date_end': last_date,
        'summary': summary,
        'brokers': brokers_list,
        'daily': daily_data,
        'recommendation': signal_data,
        'volatilityTrend': vt_data,
        'priceRecommendation': price_data,
        'confidence': confidence_data,
        'insights': insights_data
    }

def main():
    base_path = r'C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\Analisis'

    try:
        stock_folders = [d for d in os.listdir(base_path)
                        if os.path.isdir(os.path.join(base_path, d))]
    except FileNotFoundError:
        print(f"Base path not found: {base_path}")
        return

    stocks_data = {}

    for stock_code in sorted(stock_folders):
        print(f"Processing {stock_code}...")
        stock_data = process_stock_folder(stock_code, base_path)
        if stock_data:
            stocks_data[stock_code] = stock_data
            print(f"  Date range: {stock_data['date_start']} to {stock_data['date_end']}")
            print(f"  Total days: {len(stock_data['daily'])}")
            print(f"  Recommendation: {stock_data['recommendation']['recommendation']}")

    output = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stocks': stocks_data
    }

    output_path = r'C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\broker_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to {output_path}")
    print(f"Total stocks processed: {len(stocks_data)}")

if __name__ == '__main__':
    main()
