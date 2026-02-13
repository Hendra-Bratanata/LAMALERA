# Fix LQ45 folders - Keep only official LQ45 stocks plus BUMI, CDIA, Saham
$official = @('ACES','ADMR','ADRO','AKRA','AMMN','AMRT','ANTM','ARTO','ASII','BBCA','BBNI','BBRI','BBTN','BMRI','BRIS','BRPT','CPIN','CTRA','ESSA','EXCL','GOTO','ICBP','INCO','INDF','INKP','ISAT','ITMG','JPFA','JSMR','KLBF','MAPA','MAPI','MBMA','MDKA','MEDC','PGAS','PGEO','PTBA','SIDO','SMGR','SMRA','TLKM','TOWR','UNTR','UNVR')
$keep = @('BUMI','CDIA','Saham')
$basePath = 'C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\Analisis'

# Get existing folders
$existing = Get-ChildItem $basePath -Directory | Select-Object -ExpandProperty Name

# Folders to delete (existing but not in official list or keep list)
$toDelete = $existing | Where-Object { $_ -notin $official -and $_ -notin $keep }

# Delete unwanted folders
foreach ($folder in $toDelete) {
    $path = Join-Path $basePath $folder
    Remove-Item -Path $path -Recurse -Force
    Write-Host "Deleted: $folder"
}

# Folders to create (in official list but don't exist)
$toCreate = $official | Where-Object { $_ -notin $existing -or $_ -in $toDelete }

foreach ($folder in $toCreate) {
    $path = Join-Path $basePath $folder
    if (-not (Test-Path $path)) {
        New-Item -Path $path -ItemType Directory -Force | Out-Null
        Write-Host "Created: $folder"
    }
}

Write-Host "`nSummary:"
Write-Host "Deleted: $($toDelete.Count) folders"
Write-Host "Created: $($toCreate.Count) folders"
Write-Host "Total LQ45 folders should be: 45"
