content = open('public/script.js', encoding='utf-8').read()
lines = content.split('\n')

# Cek duplikat fungsi
import re
funcs = re.findall(r'^(?:async )?function (\w+)\(', content, re.MULTILINE)
from collections import Counter
dupes = {k: v for k, v in Counter(funcs).items() if v > 1}
if dupes:
    print("DUPLIKAT FUNGSI:", dupes)
else:
    print("OK: Tidak ada duplikat fungsi")

# Cek orphan code (baris yang dimulai dengan await/window.AndroidBridge di luar fungsi)
for i, l in enumerate(lines):
    s = l.strip()
    if s.startswith('await window.flutter') and not any(lines[max(0,i-5):i]):
        print(f"ORPHAN line {i+1}: {s[:80]}")
    if 'AndroidBridge.playNative' in s:
        print(f"OLD CODE line {i+1}: {s[:80]}")

# Cek apakah _playNativeStream ada
if '_playNativeStream' in content:
    print("OK: _playNativeStream ada")
if 'callHandler(\'playStream\'' in content:
    print("OK: callHandler playStream ada")
if 'callHandler(\'pauseAudio\'' in content:
    print("OK: callHandler pauseAudio ada")
if 'callHandler(\'seekAudio\'' in content:
    print("OK: callHandler seekAudio ada")

print(f"\nTotal lines: {len(lines)}")
