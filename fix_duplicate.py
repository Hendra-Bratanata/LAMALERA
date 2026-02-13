# Fix duplicate code in dashboard.html
import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the problematic section - stop loss calculation duplicated
# Pattern: lines with "// STOP LOSS" followed by duplicate calculation
pattern = r"(// STOP LOSS.*?\n\s+const stopLossPercent.*?\n\s+stopLoss = buyZone.*?\n\s+const recentAvgBuy = recent5Days.*?\n\s+const recentAvgSell = recent5Days.*?\n\s+// Calculate price levels.*?\n\s+let buyZone.*?\n\s+// Support.*?\n\s+const recentBuyPrices.*?\n\s+const lowestRecentBuy.*?\n\s+// Buy zone.*?\n\s+buyZone = lowestRecentBuy.*?\n\s+// Resistance.*?\n\s+sellZone = Math\.min.*?\n\s+if \(recentAvgSell.*?\n\s+\}.*?\n\s+// Target.*?\n\s+targetPrice = s\.shark_sellavg.*?\n\s+// Stop Loss.*?\n\s+stopLoss = buyZone \* 0\.95;"

# Find and replace with clean version (stop after "// STOP LOSS" line)
replacement = r"// STOP LOSS - Dynamic based on volatility (3-5% below buy zone)\n            const stopLossPercent = Math\.max\(0\.03, Math\.min\(0\.05, volatilityFactor\));\n            stopLoss = buyZone \* \(1 - stopLossPercent\);"

# Apply the fix
new_content = re.sub(pattern, replacement, content)

# Write back
with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed!")
