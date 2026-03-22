with open('public/script.js', 'rb') as f:
    raw = f.read()

# Find playNative
import re
for m in re.finditer(b'playNative|_nativePlaying|_nativePaused', raw):
    start = max(0, m.start()-120)
    end = min(len(raw), m.end()+120)
    print(f"--- {m.group()} at {m.start()} ---")
    print(raw[start:end])
    print()
