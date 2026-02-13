# Backup System for Dashboard - PowerShell version
# Creates automatic backups before any edits

$ErrorActionPreference = "SilentlyContinue"

$dashboardFile = "C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\dashboard.html"
$backupDir = "C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\backups"
$versionFile = Join-Path $backupDir "version.json"

function Create-Backup {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = Join-Path $backupDir "dashboard_backup_$timestamp.html"

    if (-Not (Test-Path $dashboardFile)) {
        Write-Error "❌ Dashboard file not found!"
        return
    }

    try {
        Copy-Item -Path $dashboardFile -Destination $backupFile -Force -ErrorAction Stop
        Write-Host "✅ Backup created: $backupFile"

        # Update version file
        if (Test-Path $versionFile) {
            $currentVersion = (Get-Content $versionFile -Raw | ConvertFrom-Json).version
        } else {
            $currentVersion = "0.0"
        }

        $changeLog = @{
            timestamp = $timestamp
            version = $currentVersion
            changes = @("Initial backup")
        }

        # Save to version.json
        $data = @{
            version = $currentVersion
            changes = @($changeLog)
        }
        $data | ConvertTo-Json | Set-Content $versionFile

        Write-Host "📝 Version: $currentVersion"
    }
    catch {
        Write-Error "❌ Backup failed: $_"
    }
}

function Restore-Version {
    param([string]$Version)

    # List available backups
    $backups = Get-ChildItem -Path $backupDir -Filter "dashboard_backup_*" |
                 Sort-Object LastWriteTime -Descending

    if ($backups.Count -eq 0) {
        Write-Error "❌ No backups found to restore!"
        return
    }

    # Use specified version or latest
    if ($Version) {
        $targetBackup = $backups | Where-Object { $_.Name -like "*$Version*" }
    } else {
        $targetBackup = $backups[0]
    }

    $restoreFile = $targetBackup.FullName

    try {
        Copy-Item -Path $restoreFile -Destination $dashboardFile -Force -ErrorAction Stop
        Write-Host "✅ Restored from: $($targetBackup.Name -replace 'dashboard_backup_', '')"
        Write-Host "📝 Version: $($targetBackup.Name -replace 'dashboard_backup_', '')"

        # Update version file
        $data = @{
            version = "$($targetBackup.Name -replace 'dashboard_backup_', '')"
            changes = @("Restored from backup")
        }
        $data | ConvertTo-Json | Set-Content $versionFile

        Write-Host "✅ Restore completed!"
    }
    catch {
        Write-Error "❌ Restore failed: $_"
    }
}

function Show-Version {
    if (-Not (Test-Path $versionFile)) {
        $currentVersion = "0.0"
    } else {
        try {
            $currentVersion = (Get-Content $versionFile -Raw | ConvertFrom-Json).version
        }
        catch {
            $currentVersion = "0.0"
        }
    }

    Write-Host ""
    Write-Host "============================================================="
    Write-Host "          DASHBOARD BACKUP SYSTEM"
    Write-Host "============================================================="
    Write-Host ""
    Write-Host "Current Version: $currentVersion"
    Write-Host "Backup Directory: $backupDir"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  .\backup        - Creates backup of current dashboard"
    Write-Host "  .\restore [ver]  Restores from specific backup (or latest if no version)"
    Write-Host "  .\version        - Show current version history"
    Write-Host ""
    Write-Host "Version History: backup.ps1"
    Write-Host "============================================================="
}

function main {
    # Default action
    $action = if ($args.Count -gt 0) { $args[0] } else { "help" }

    switch ($action) {
        "backup" { Create-Backup }
        "restore" {
            if ($args.Count -lt 2) {
                Write-Error "❌ Usage: backup.ps1 restore [version]"
                return
            }
            Restore-Version $args[1]
        }
        "version" { Show-Version }
        Show-Version
        default {
            Write-Error "❌ Unknown command: $action"
            Write-Host "Usage: backup.ps1 [backup|restore|version|help]"
        }
    }
}

# Run
main
