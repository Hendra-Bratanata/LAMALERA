import os
import glob

path = r'C:\Users\Hendra.LAPTOP-M9SC6TF3\Saham\Analisis\BBTN'

# Method 1: Check all files
print("=== Method 1: os.walk ===")
all_files = []
for root, dirs, files in os.walk(path):
    for f in files:
        if f.endswith('.csv'):
            all_files.append(os.path.join(root, f))

print(f"Total CSV files: {len(all_files)}")
all_files.sort()
for f in all_files[:15]:
    print(f"  {f}")

# Method 2: Check subfolders
print("\n=== Method 2: Subfolders ===")
for d in os.listdir(path):
    full_path = os.path.join(path, d)
    if os.path.isdir(full_path):
        csv_files = [f for f in os.listdir(full_path) if f.endswith('.csv')]
        csv_files.sort()
        print(f"Folder {d}: {len(csv_files)} files")
        for cf in csv_files[:5]:
            print(f"  {cf}")

# Method 3: Check for specific pattern
print("\n=== Checking for 2-26 or retail-2-26 pattern ===")
for root, dirs, files in os.walk(path):
    for d in dirs:
        if '2-26' in d.lower() or 'retail' in d.lower():
            full_path = os.path.join(root, d)
            print(f"Found folder: {full_path}")
            csv_files = [f for f in os.listdir(full_path) if f.endswith('.csv')]
            csv_files.sort()
            for cf in csv_files[:5]:
                print(f"  {cf}")
