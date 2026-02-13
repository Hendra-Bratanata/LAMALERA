#!/usr/bin/env python3
"""
Generate JSON data from CSV broker analysis files.
CSV files contain CUMULATIVE (YTD) data - need to calculate daily by subtracting previous day.
Updated to correctly parse dates from CSV files and folder names.
"""

import os
import json
from datetime import datetime
from collections import OrderedDict

# Shark brokers (institusional) - sesuai referensi broker_saham_indonesia.md
SHARK_BROKERS = {
    'AK',  # UBS Sekuritas Indonesia
    'CC',  # Mandiri Sekuritas
    'BK',  # J.P. Morgan Sekuritas
    'GW',  # HSBC Sekuritas Indonesia
    'AI',  # UOB Kay Hian Sekuritas
    'KZ',  # CLSA Sekuritas Indonesia
    'DX',  # Bahana Sekuritas
    'DD',  # Makindo Sekuritas
    'RX',  # Macquarie Sekuritas
    'KK',  # Phillip Sekuritas Indonesia
    'CG',  # Ciptadana Sekuritas Asia
    'DR',  # RHB Sekuritas (Hybrid)
    'TP',  # OCBC Sekuritas (Hybrid)
    'SQ',  # BCA Sekuritas (Hybrid)
    'NI',  # BNI Sekuritas (Hybrid)
    'CD',  # Mega Capital Sekuritas
    'OD',  # BRI Danareksa
}

def parse_date_from_header(line):
    """Parse date from CSV header line."""
    try:
        parts = line.strip().split('\t')
        # Look for Start and End with their date values
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

def read_csv_file_cumulative(file_path):
    """
    Read CSV file and extract CUMULATIVE values per broker.
    """
    result = {
        'date_start': None,
        'date_end': None,
        'date_display': None,
        'shark_buyavg': 0,
        'shark_sellavg': 0,
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

            # Buy Lot at column 1 (BLot), Buy value at column 2 (BVal), Buy Avg at column 3 (BAvg)
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

            # Sell Lot at column 6 (SLot), Sell value at column 7 (SVal), Sell Avg at column 8 (SAvg)
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

            # Accumulate for weighted average
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

        # Calculate weighted averages
        if shark_total_buy_val > 0:
            result['shark_buyavg'] = shark_total_buy_avg / shark_total_buy_val
        if shark_total_sell_val > 0:
            result['shark_sellavg'] = shark_total_sell_avg / shark_total_sell_val
        if retail_total_buy_val > 0:
            result['retail_buyavg'] = retail_total_buy_avg / retail_total_buy_val
        if retail_total_sell_val > 0:
            result['retail_sellavg'] = retail_total_sell_avg / retail_total_sell_val

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return result

def scan_stock_folder(stock_path):
    """
    Scan all CSV files in stock folder and its subfolders.
    Extract date from folder name (JAN26, FEB26) and file number.
    """
    csv_files = []

    def extract_date_from_path(path, folder_name):
        """Extract date from folder (JAN26, FEB26) and filename (2.csv, 11.csv)"""
        # Folder name format: BBTNJAN26, BBTNFEB26
        # File format: just number.csv (2.csv, 11.csv)

        # Extract month from folder name
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

        # Extract year from folder name (last 2-4 digits)
        year_match = None
        import re
        year_match = re.search(r'(\d{2,4})$', folder_name)
        if year_match:
            year_suffix = year_match.group(1)
            if len(year_suffix) == 2:
                # Convert 25 -> 2025, 26 -> 2026
                year = '20' + year_suffix
            else:
                year = year_suffix
        else:
            year = '2026'  # default

        # Extract day from filename
        filename = os.path.basename(path).replace('.csv', '')
        try:
            day = int(filename)
            # Pad to 2 digits with leading zero
            day_str = f"{day:02d}"
        except ValueError:
            return None

        if month and year and day:
            return f"{year}-{month}-{day_str}"
        return None

    # Walk through all subdirectories
    for root, dirs, files in os.walk(stock_path):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                folder_name = os.path.basename(root)
                date_str = extract_date_from_path(file_path, folder_name)
                if date_str:
                    csv_files.append((file_path, date_str, file))

    # Sort by date
    csv_files.sort(key=lambda x: x[1] if x[1] else '9999-99-99')

    return csv_files

def process_stock_folder(stock_code, base_path):
    """Process all CSV files for a stock"""
    stock_path = os.path.join(base_path, stock_code)

    if not os.path.exists(stock_path):
        print(f"Folder not found: {stock_path}")
        return None

    csv_files = scan_stock_folder(stock_path)

    if not csv_files:
        print(f"No CSV files found in {stock_path}")
        return None

    print(f"  Found {len(csv_files)} CSV files")

    # First, read all files to get cumulative data
    cumulative_data = []
    for file_path, date_str, filename in csv_files:
        data = read_csv_file_cumulative(file_path)
        data['date_start'] = date_str  # Use extracted date from folder/file
        if data['date_start']:
            data['date_display'] = format_date_for_display(data['date_start'])
        cumulative_data.append(data)

    # Calculate daily values by subtracting previous cumulative
    daily_data = []
    prev_cumulative = {}

    # Overall cumulative tracking
    total_shark_cum_buy = 0
    total_shark_cum_sell = 0
    total_retail_cum_buy = 0
    total_retail_cum_sell = 0

    # For weighted average price tracking
    total_shark_buyavg_weighted = 0
    total_shark_sellavg_weighted = 0
    total_retail_buyavg_weighted = 0
    total_retail_sellavg_weighted = 0

    # For lot/share tracking
    total_shark_cum_buy_lot = 0
    total_shark_cum_sell_lot = 0
    total_retail_cum_buy_lot = 0
    total_retail_cum_sell_lot = 0

    # For summary average calculation using LOT
    total_shark_buy_lot_for_avg = 0
    total_shark_sell_lot_for_avg = 0
    total_retail_buy_lot_for_avg = 0
    total_retail_sell_lot_for_avg = 0

    # Per-broker tracking
    all_brokers_data = {}

    for i, cum_data in enumerate(cumulative_data):
        day_num = i + 1

        # Calculate DAILY values
        daily_shark_buy = 0
        daily_shark_sell = 0
        daily_retail_buy = 0
        daily_retail_sell = 0
        daily_shark_buy_lot = 0
        daily_shark_sell_lot = 0
        daily_retail_buy_lot = 0
        daily_retail_sell_lot = 0

        # For weighted average calculation - accumulate avg*LOT (not value!)
        daily_shark_buyavg_weighted = 0
        daily_shark_sellavg_weighted = 0
        daily_retail_buyavg_weighted = 0
        daily_retail_sellavg_weighted = 0

        for broker_code, broker_cum in cum_data['brokers'].items():
            prev_buy = prev_cumulative.get(broker_code, {}).get('buy', 0)
            prev_sell = prev_cumulative.get(broker_code, {}).get('sell', 0)
            prev_buy_lot = prev_cumulative.get(broker_code, {}).get('buy_lot', 0)
            prev_sell_lot = prev_cumulative.get(broker_code, {}).get('sell_lot', 0)

            # Detect cumulative reset (when current < previous, indicating new period/month)
            # If reset detected, use current value as daily (no subtraction)
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

            # For weighted avg, only consider BUYING activity (positive daily_buy_lot)
            if daily_buy_lot > 0:
                buy_lot_for_avg = daily_buy_lot
            else:
                buy_lot_for_avg = 0

            # For weighted avg, only consider SELLING activity (positive daily_sell_lot)
            if daily_sell_lot > 0:
                sell_lot_for_avg = daily_sell_lot
            else:
                sell_lot_for_avg = 0

            # Initialize broker
            if broker_code not in all_brokers_data:
                category = 'shark' if broker_code in SHARK_BROKERS else 'retail'
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

            # Add to totals (only if there's activity)
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

            # Categorize
            if broker_code in SHARK_BROKERS:
                daily_shark_buy += daily_buy
                daily_shark_sell += daily_sell
                daily_shark_buy_lot += daily_buy_lot
                daily_shark_sell_lot += daily_sell_lot
                # Accumulate weighted average: avg * LOT (not value!)
                if buy_lot_for_avg > 0:
                    daily_shark_buyavg_weighted += daily_buyavg * buy_lot_for_avg
                if sell_lot_for_avg > 0:
                    daily_shark_sellavg_weighted += daily_sellavg * sell_lot_for_avg
            else:
                daily_retail_buy += daily_buy
                daily_retail_sell += daily_sell
                daily_retail_buy_lot += daily_buy_lot
                daily_retail_sell_lot += daily_sell_lot
                # Accumulate weighted average: avg * LOT (not value!)
                if buy_lot_for_avg > 0:
                    daily_retail_buyavg_weighted += daily_buyavg * buy_lot_for_avg
                if sell_lot_for_avg > 0:
                    daily_retail_sellavg_weighted += daily_sellavg * sell_lot_for_avg

        # Calculate TODAY'S total lots for weighted average (handle resets)
        today_shark_buy_lot = 0
        today_shark_sell_lot = 0
        today_retail_buy_lot = 0
        today_retail_sell_lot = 0

        for broker_code in cum_data['brokers']:
            if broker_code not in prev_cumulative:
                # New broker, use current lot as daily
                lot = cum_data['brokers'][broker_code].get('buy_lot', 0)
            else:
                # Check for reset
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

        # Retail buy lots
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

        # Update cumulative totals
        total_shark_cum_buy += daily_shark_buy
        total_shark_cum_sell += daily_shark_sell
        total_retail_cum_buy += daily_retail_buy
        total_retail_cum_sell += daily_retail_sell
        total_shark_cum_buy_lot += daily_shark_buy_lot
        total_shark_cum_sell_lot += daily_shark_sell_lot
        total_retail_cum_buy_lot += daily_retail_buy_lot
        total_retail_cum_sell_lot += daily_retail_sell_lot

        # Update weighted average tracking for summary using LOT (not value!)
        if today_shark_buy_lot > 0:
            total_shark_buyavg_weighted += daily_shark_buyavg * today_shark_buy_lot
        if today_shark_sell_lot > 0:
            total_shark_sellavg_weighted += daily_shark_sellavg * today_shark_sell_lot
        if today_retail_buy_lot > 0:
            total_retail_buyavg_weighted += daily_retail_buyavg * today_retail_buy_lot
        if today_retail_sell_lot > 0:
            total_retail_sellavg_weighted += daily_retail_sellavg * today_retail_sell_lot

        # Track total lots for summary
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
            'shark_buy': round(daily_shark_buy, 2),
            'retail_buy': round(daily_retail_buy, 2),
            'shark_sell': round(daily_shark_sell, 2),
            'retail_sell': round(daily_retail_sell, 2),
            'shark_buyavg': round(daily_shark_buyavg, 2),
            'shark_sellavg': round(daily_shark_sellavg, 2),
            'retail_buyavg': round(daily_retail_buyavg, 2),
            'retail_sellavg': round(daily_retail_sellavg, 2),
            'shark_cum_buy': round(total_shark_cum_buy, 2),
            'retail_cum_buy': round(total_retail_cum_buy, 2),
            'shark_cum_sell': round(total_shark_cum_sell, 2),
            'retail_cum_sell': round(total_retail_cum_sell, 2),
            'shark_net': round(shark_net, 2),
            'retail_net': round(retail_net, 2),
            'shark_cum_net': round(total_shark_cum_buy - total_shark_cum_sell, 2),
            'retail_cum_net': round(total_retail_cum_buy - total_retail_cum_sell, 2),
            'shark_cum_buy_lot': round(total_shark_cum_buy_lot),
            'shark_cum_sell_lot': round(total_shark_cum_sell_lot),
            'retail_cum_buy_lot': round(total_retail_cum_buy_lot),
            'retail_cum_sell_lot': round(total_retail_cum_sell_lot),
            'shark_net_lot': round(shark_net_lot),
            'retail_net_lot': round(retail_net_lot)
        })

        # Store current cumulative as previous
        prev_cumulative = cum_data['brokers']

    # Calculate final weighted averages for summary using LOT (not value!)
    summary_shark_buyavg = total_shark_buyavg_weighted / total_shark_buy_lot_for_avg if total_shark_buy_lot_for_avg > 0 else 0
    summary_shark_sellavg = total_shark_sellavg_weighted / total_shark_sell_lot_for_avg if total_shark_sell_lot_for_avg > 0 else 0
    summary_retail_buyavg = total_retail_buyavg_weighted / total_retail_buy_lot_for_avg if total_retail_buy_lot_for_avg > 0 else 0
    summary_retail_sellavg = total_retail_sellavg_weighted / total_retail_sell_lot_for_avg if total_retail_sell_lot_for_avg > 0 else 0

    # Get overall date range
    first_date = daily_data[0]['date'] if daily_data else 'Unknown'
    last_date = daily_data[-1].get('date_end', daily_data[-1].get('date', 'Unknown')) if daily_data else 'Unknown'

    # Process broker data
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

    return {
        'code': stock_code,
        'date_start': first_date,
        'date_end': last_date,
        'summary': {
            'shark_buy': round(total_shark_cum_buy, 2),
            'retail_buy': round(total_retail_cum_buy, 2),
            'shark_sell': round(total_shark_cum_sell, 2),
            'retail_sell': round(total_retail_cum_sell, 2),
            'shark_buyavg': round(summary_shark_buyavg, 2),
            'retail_buyavg': round(summary_retail_buyavg, 2),
            'shark_sellavg': round(summary_shark_sellavg, 2),
            'retail_sellavg': round(summary_retail_sellavg, 2),
            'shark_net': round(total_shark_cum_buy - total_shark_cum_sell, 2),
            'retail_net': round(total_retail_cum_buy - total_retail_cum_sell, 2),
            'total_buy': round(total_shark_cum_buy + total_retail_cum_buy, 2),
            'total_sell': round(total_shark_cum_sell + total_retail_cum_sell, 2),
            'shark_cum_buy_lot': round(total_shark_cum_buy_lot),
            'shark_cum_sell_lot': round(total_shark_cum_sell_lot),
            'retail_cum_buy_lot': round(total_retail_cum_buy_lot),
            'retail_cum_sell_lot': round(total_retail_cum_sell_lot),
            'shark_net_lot': round(total_shark_cum_buy_lot - total_shark_cum_sell_lot),
            'retail_net_lot': round(total_retail_cum_buy_lot - total_retail_cum_sell_lot)
        },
        'brokers': brokers_list,
        'daily': daily_data
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
