@echo off
REM Backup System for Dashboard
REM Simply creates backups before any edits

set DASHBOARD=C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\dashboard.html
set BACKUP_DIR=C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\backups

echo.
echo ============================================================
echo          DASHBOARD BACKUP SYSTEM
echo ============================================================
echo.
echo Current file: %DASHBOARD%
echo Backup directory: %BACKUP_DIR%
echo.
echo Commands:
echo   backup       - Creates backup of current dashboard
echo   restore [ver] - Restores from specific backup
echo.
echo ============================================================
