// Clean, tested price calculation code
// Replace the entire "CALCULATE PRICE RECOMMENDATIONS" section

const newPriceCalcSection = `
            // ===== CALCULATE PRICE RECOMMENDATIONS =====
            // Get price data from daily averages
            const allBuyAvgs = daily.map(d => d.shark_buyavg || 0).filter(v => v > 0);
            const allSellAvgs = daily.map(d => d.shark_sellavg || 0).filter(v => v > 0);

            const minPrice = Math.min(...allBuyAvgs, ...allSellAvgs);
            const maxPrice = Math.max(...allBuyAvgs, ...allSellAvgs);
            const avgPrice = (s.shark_buyavg + s.shark_sellavg + s.retail_buyavg + s.retail_sellavg) / 4;

            // STOP LOSS - 3-5% below buy zone
            const stopLoss = buyZone * 0.95;

            // SELL ZONE - Based on Shark's sell avg (they know fair value to take profit)
            // Shark sell avg + small premium (1-2%) or resistance level
            const allSharkSellPrices = daily.map(d => d.shark_sellavg || 0).filter(v => v > 0);
            const avgSharkSell = allSharkSellPrices.length > 0 ? allSharkSellPrices.reduce((a, b) => a + b, 0) / allSharkSellPrices.length : 0;
            const maxSharkSell = allSharkSellPrices.length > 0 ? Math.max(...allSharkSellPrices) : 0;
            let sellZone = Math.max(avgSharkSell, maxSharkSell * 1.01);

            // TARGET - Shark's average sell price (their fair value/exit point)
            const targetPrice = avgSharkSell;

            // Update price UI
            document.getElementById('buyZone').textContent = \`Rp \${buyZone.toFixed(0)}\`;
            document.getElementById('targetPrice').textContent = \`Rp \${targetPrice.toFixed(0)}\`;
            document.getElementById('sellZone').textContent = \`Rp \${sellZone.toFixed(0)}\`;
            document.getElementById('stopLoss').textContent = \`Rp \${stopLoss.toFixed(0)}\`;

            // Generate price advice based on recommendation
            let priceAdvice = '';
            if (recommendation === 'BUY') {
                priceAdvice = \`💡 <strong>SARAN ENTRY</strong>: Tunggu harga mendekati area beli <strong>Rp \${buyZone.toFixed(0)}</strong>. \`;
                priceAdvice += \`Target price di <strong>Rp \${targetPrice.toFixed(0)}</strong> (potensi +\${((targetPrice - buyZone) / buyZone * 100).toFixed(1)}%). \`;
                priceAdvice += \`Stop Loss di <strong>Rp \${stopLoss.toFixed(0)}</strong> untuk proteksi. \`;
                priceAdvice += \`Area beli berdasarkan rata-rata Shark buy (Rp \${avgSharkBuy.toFixed(0)}) dengan diskon dinamis.\`;
            } else if (recommendation === 'SELL') {
                priceAdvice = \`💡 <strong>SARAN EXIT</strong>: Pertimbangkan jual saat harga mendekati area jual <strong>Rp \${sellZone.toFixed(0)}</strong>. \`;
                priceAdvice += \`Jika masih hold, pasang Stop Loss di <strong>Rp \${stopLoss.toFixed(0)}</strong>. \`;
                priceAdvice += \`Area jual berdasarkan rata-rata Shark sell (Rp \${avgSharkSell.toFixed(0)}) sebagai fair value exit.\`;
            } else {
                priceAdvice = \`💡 <strong>STRATEGI WAIT</strong>: Saatnya tunggu. \`;
                priceAdvice += \`Area beli: <strong>Rp \${buyZone.toFixed(0)}</strong> | Area jual: <strong>Rp \${sellZone.toFixed(0)}</strong>. \`;
                priceAdvice += \`Tunggu breakout atau rejection di salah satu level ini sebelum entry. \`;
                priceAdvice += \`Harga saat ini berada di kisaran rata-rata periode Rp \${avgPrice.toFixed(0)}.\`;
            }

            document.getElementById('priceAdvice').innerHTML = priceAdvice;
`;

console.log('Copy this code and replace the section in dashboard.html');
console.log('Find the line: // ===== CALCULATE PRICE RECOMMENDATIONS =====');
console.log('Delete from there to: let priceAdvice = \'\';');
console.log('Then paste the new code above');
