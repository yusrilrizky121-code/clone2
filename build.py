"""
Build script Auspoty — jalankan dari folder root:
  python build.py

Otomatis:
1. Sync web assets
2. Build APK release
3. Copy APK ke folder root (Auspoty-release.apk), hapus yang lama
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FLUTTER_DIR = os.path.join(ROOT, 'auspoty-flutter')
APK_SRC = os.path.join(FLUTTER_DIR, 'build', 'app', 'outputs', 'flutter-apk', 'app-release.apk')
APK_DST = os.path.join(ROOT, 'Auspoty-release.apk')

def run(cmd, cwd=None):
    print(f'\n>>> {cmd}')
    result = subprocess.run(cmd, shell=True, cwd=cwd or FLUTTER_DIR)
    if result.returncode != 0:
        print(f'ERROR: command failed (exit {result.returncode})')
        sys.exit(result.returncode)

# 1. Sync assets
run('python setup_assets.py')

# 2. Build APK
run('flutter build apk --release')

# 3. Copy & replace APK
if os.path.exists(APK_SRC):
    if os.path.exists(APK_DST):
        os.remove(APK_DST)
        print(f'Deleted old: {APK_DST}')
    shutil.copy2(APK_SRC, APK_DST)
    size_mb = os.path.getsize(APK_DST) / 1024 / 1024
    print(f'\n✓ APK ready: Auspoty-release.apk ({size_mb:.1f} MB)')
else:
    print('ERROR: APK not found after build!')
    sys.exit(1)
