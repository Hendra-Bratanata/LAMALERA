# Create folders for Top 30 stocks from topstok.csv
$top30 = @('BUMI','PTRO','BBCA','RAJA','BBRI','DEWA','CUAN','BUVA','MINA','ANTM',
           'BMRI','PADI','RATU','TLKM','INCO','BRPT','ENRG','UNTR','BKSL','BIPI',
           'INET','TINS','BRMS','AADI','WIFI','ADRO','VKTR','ARCI','ASII','CDIA')

$basePath = 'C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\Analisis'

# Get existing folders
$existing = Get-ChildItem $basePath -Directory | Select-Object -ExpandProperty Name

# Create folders that don't exist yet
foreach ($stock in $top30) {
    $path = Join-Path $basePath $stock
    if (-not (Test-Path $path)) {
        New-Item -Path $path -ItemType Directory -Force | Out-Null
        Write-Host "Created: $stock"
    } else {
        Write-Host "Exists:  $stock"
    }
}

Write-Host "`nTotal Top 30 stocks processed"
