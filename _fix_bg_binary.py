with open('public/script.js', 'rb') as f:
    content = f.read()

# Decode as UTF-8
text = content.decode('utf-8')

# Normalize CRLF to LF for processing
text = text.replace('\r\n', '\n')

import re

# ---- 1. Fix playMusic block ----
# Find the block from "// *** KUNCI" to the closing "}" of the if/else
pattern = re.compile(
    r'    // \*\*\* KUNCI BACKGROUND AUDIO \*\*\*\n'
    r'    // Cek AndroidBridge\.playNative.*?\n'
    r'    if \(window\.AndroidBridge.*?'
    r'    \}\n',
    re.DOTALL
)
m = pattern.search(text)
if m:
    print(f"Found playMusic block at {m.start()}-{m.end()}")
    new_block = (
        "    // Putar via ytPlayer — background audio dijaga oleh foreground service\n"
        "    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);\n"
    )
    text = text[:m.start()] + new_block + text[m.end():]
    print("OK: playMusic block replaced")
else:
    print("FAIL: playMusic block not found, trying broader pattern...")
    # Broader: find from "// *** KUNCI" to "    } else {\n        // Fallback"
    idx_start = text.find('    // *** KUNCI BACKGROUND AUDIO ***\n')
    if idx_start >= 0:
        # Find the closing "    }\n" after the else block
        idx_else = text.find('    } else {\n', idx_start)
        if idx_else >= 0:
            # Find end of else block
            idx_end = text.find('\n    }\n', idx_else)
            if idx_end >= 0:
                idx_end += len('\n    }\n')
                old_block = text[idx_start:idx_end]
                print(f"Found block: {repr(old_block[:100])}")
                new_block = (
                    "    // Putar via ytPlayer — background audio dijaga oleh foreground service\n"
                    "    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);\n"
                )
                text = text[:idx_start] + new_block + text[idx_end:]
                print("OK: playMusic block replaced (manual)")
            else:
                print("FAIL: could not find end of else block")
        else:
            print("FAIL: could not find else block")
    else:
        print("FAIL: could not find start of block")

# ---- 2. Fix _nativePlaying/_nativePaused in startLyricsScroll ----
# Replace the native check in lyricsScroll
old_lyrics = (
    "        if (window._nativePlaying || window._nativePaused) {\n"
    "            const bar = document.getElementById('progressBar');\n"
    "            const tt = document.getElementById('totalTime');\n"
)
# Find and show context
idx = text.find('window._nativePlaying || window._nativePaused')
if idx >= 0:
    print(f"\nFound native check in lyrics at {idx}")
    print(repr(text[max(0,idx-100):idx+300]))

# ---- 3. Remove native state vars if still present ----
for old in [
    'window._nativePlaying = false;\nwindow._nativeLoading = false;\nwindow._nativePaused = false;\n',
    'window._nativePlaying = false;\nwindow._nativeLoading = false;\n',
]:
    if old in text:
        text = text.replace(old, '', 1)
        print(f"OK: removed native state vars")

# ---- 4. Fix the lyrics scroll native check ----
# Find the setInterval in startLyricsScroll that checks _nativePlaying
# Replace the whole native branch with just ytPlayer check
old_lyrics_block = re.compile(
    r'        if \(window\._nativePlaying \|\| window\._nativePaused\) \{.*?'
    r'        \} else if \(ytPlayer',
    re.DOTALL
)
m2 = old_lyrics_block.search(text)
if m2:
    print(f"\nFound lyrics native block at {m2.start()}")
    print(repr(text[m2.start():m2.end()]))
    # Replace with just ytPlayer check
    text = text[:m2.start()] + '        if (ytPlayer' + text[m2.end():]
    print("OK: lyrics native block replaced")
else:
    print("INFO: lyrics native block not found (may already be fixed)")

# Write back
with open('public/script.js', 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

# Final verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    result = f.read()

print("\n=== FINAL VERIFY ===")
print(f"_nativePlaying: {result.count('_nativePlaying')}")
print(f"_nativeLoading: {result.count('_nativeLoading')}")
print(f"_nativePaused: {result.count('_nativePaused')}")
print(f"playNative: {result.count('playNative')}")
print(f"onMusicPlaying: {result.count('onMusicPlaying')}")
print(f"onMusicPaused: {result.count('onMusicPaused')}")
print(f"loadVideoById: {result.count('loadVideoById')}")
