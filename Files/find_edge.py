import os
import subprocess

print("Searching for Microsoft Edge...\n")

# Try using registry/system
try:
    result = subprocess.run(
        ['powershell', '-Command', 
         '(Get-Command msedge -ErrorAction SilentlyContinue).Source'],
        capture_output=True, text=True, timeout=5
    )
    if result.stdout.strip():
        print(f"✓ Found Edge: {result.stdout.strip()}")
        input("Press Enter to close...")
        exit(0)
except Exception as e:
    print(f"PowerShell search failed: {e}\n")

# Search common locations
search_paths = [
    r"C:\Program Files\Microsoft\Edge\Application",
    r"C:\Program Files (x86)\Microsoft\Edge\Application",
    r"C:\Users\btarabocchia\AppData\Local\Microsoft\Edge\Application",
    r"C:\Program Files\WindowsApps",
]

found = False
for path in search_paths:
    if os.path.exists(path):
        print(f"Searching in: {path}")
        for root, dirs, files in os.walk(path):
            if 'msedge.exe' in files:
                full_path = os.path.join(root, 'msedge.exe')
                print(f"\n✓✓✓ FOUND: {full_path}\n")
                found = True
                break
        if found:
            break

if not found:
    print("\n✗ Edge not found in common locations")
    print("\nPlease copy the full path manually and share it.")

input("Press Enter to close...")

