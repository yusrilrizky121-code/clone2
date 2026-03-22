with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all playNative occurrences
import re
for m in re.finditer('playNative|_nativePlaying|_nativeLoading', content):
    start = max(0, m.start()-80)
    end = min(len(content), m.end()+80)
    print(f"--- {m.group()} at {m.start()} ---")
    print(repr(content[start:end]))
    print()
