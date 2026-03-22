with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Check what's actually in the file around _nativePlaying
idx = content.find('_nativePlaying')
if idx >= 0:
    print("Found _nativePlaying at:", idx)
    print(repr(content[max(0,idx-100):idx+200]))
else:
    print("_nativePlaying NOT found")

idx2 = content.find('playNative')
if idx2 >= 0:
    print("\nFound playNative at:", idx2)
    print(repr(content[max(0,idx2-50):idx2+200]))
else:
    print("playNative NOT found")

# Check togglePlay
idx3 = content.find('function togglePlay')
if idx3 >= 0:
    print("\nFound togglePlay at:", idx3)
    print(repr(content[idx3:idx3+400]))
