with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# The namida block marker
marker = '// ============================================================\n// NAMIDA UI'

# Find all occurrences
positions = []
start = 0
while True:
    idx = content.find(marker, start)
    if idx == -1:
        break
    positions.append(idx)
    start = idx + 1

print(f"Found {len(positions)} NAMIDA blocks at positions: {positions}")

if len(positions) == 2:
    # Keep only the LAST one (most recent), remove the first
    first_start = positions[0]
    second_start = positions[1]
    # Remove from first_start to second_start
    content = content[:first_start] + content[second_start:]
    print("Removed first duplicate block")
elif len(positions) == 1:
    print("Only one block, no dedup needed")
else:
    print(f"Unexpected count: {len(positions)}")

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
c2 = open('public/script.js', 'r', encoding='utf-8').read()
print("function _setArtPlaying:", c2.count('function _setArtPlaying'))
print("function _initWaveform:", c2.count('function _initWaveform'))
print("function _updateWaveform:", c2.count('function _updateWaveform'))
print("_setArtRotation remaining:", c2.count('_setArtRotation'))
