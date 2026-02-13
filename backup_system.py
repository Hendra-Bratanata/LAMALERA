#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe backup and versioning system for dashboard.html
Creates backups before any modification and tracks version history
"""
"""

import os
import shutil
from datetime import datetime
import hashlib
import json

# Configuration
DASHBOARD_FILE = r"C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\dashboard.html"
BACKUP_DIR = r"C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\backups"
VERSION_FILE = os.path.join(BACKUP_DIR, "version.json")
MAX_VERSIONS = 10  # # Keep maximum 10 versioned backups

def calculate_file_hash(filepath):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096)):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def load_version():
    """Load current version information"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return json.load(f)
    return {"version": "unknown", "changes": []}

def save_version(version, changes):
    """Save version information with timestamp"""
    data = load_version()

    # Create new version entry
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "version": version,
        "changes": changes,
        "hash": calculate_file_hash(DASHBOARD_FILE)
    }

    # Add to history
    data["changes"].append(new_entry)

    # Keep only MAX_VERSIONS entries
    if len(data["changes"]) > MAX_VERSIONS:
        # Remove oldest entries
        data["changes"] = data["changes"][-MAX_VERSIONS:]

    # Save
    with open(VERSION_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    return new_entry

def create_backup():
    """Create a backup before making changes"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"dashboard_backup_{timestamp}.html")

    # Copy current dashboard to backup
    shutil.copy2(DASHBOARD_FILE, backup_file)

    print(f"✅ Backup created: {backup_file}")
    return backup_file

def get_next_version():
    """Determine next version number"""
    data = load_version()
    current_version = data.get("version", "1.0")

    # Extract version number (assuming format X.Y)
    try:
        version_num = float(current_version.split(".")[0])
        next_version = f"{version_num + 1}.1"
    except:
        next_version = "2.0"

    return next_version

def main():
    """Main function - always create backup before allowing edits"""
    import sys

    # Ensure backup directory exists
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "backup":
            # Create backup of current file
            backup_file = create_backup()

            # Update version to next
            next_ver = get_next_version()
            save_version(
                next_ver,
                ["Manual backup before modification"]
            )

            print(f"✅ Backup created: {backup_file}")
            print(f"📝 Version updated to: {next_ver}")

        elif command == "restore":
            # Restore from latest backup
            # List available backups
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("dashboard_backup_") and f.endswith(".html")]
            backups.sort(reverse=True)

            if not backups:
                print("❌ No backups found to restore!")
                return

            # Use latest backup
            latest_backup = backups[0]
            restore_file = os.path.join(BACKUP_DIR, latest_backup)

            # Restore
            shutil.copy2(restore_file, DASHBOARD_FILE)

            # Get version info from backup
            backup_version = "unknown"
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    ver_data = json.load(f)
                    # Find this backup's version
                    for entry in ver_data.get("changes", []):
                        if os.path.basename(restore_file) in entry.get("changes", []):
                            backup_version = entry.get("version", "unknown")
                            break

            print(f"✅ Restored from: {latest_backup}")
            print(f"📝 Version: {backup_version}")

        else:
            print("❌ Unknown command!")
            print(f"Usage: python backup_system.py [backup|restore]")

    else:
        # Default: create backup
        print("ℹ️ No command specified - creating backup...")
        backup_file = create_backup()

        # Don't auto-update version on manual backup
        print("💡 To make changes to dashboard.html:")
        print("   1. Run: python backup_system.py backup")
        print("   2. Make your edits")
        print("   3. Run: python backup_system.py restore [version_name]")
        print("   4. Dashboard will auto-restore from latest backup on load")

if __name__ == "__main__":
    main()
