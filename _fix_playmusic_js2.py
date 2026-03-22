"""
Fix playMusic() di script.js - pakai byte-level replacement
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find exact position
idx = content.find('Putar via ytPlayer')
if idx < 0:
    print("ERROR: 'Putar via ytPlayer' not found!")
    exit(1)

# Find the end of this block (next empty line after closing brace)
end_marker = '\n\n    setTimeout'
end_idx = content.find(end_marker, idx)
if end_idx < 0:
    print("ERROR: end marker not found!")
    exit(1)

old_block = content[idx:end_idx]
print(f"Found block ({len(old_block)} chars):")
print(repr(old_block))
print()

new_block = """Putar audio
    if (window.flutter_inappwebview) {
        // APK Flutter: kirim ke MediaPlayer native, ytPlayer di-mute agar tidak bentrok
        try { if (ytPlayer && ytPlayer.mute) ytPlayer.mute(); } catch(e) {}
        isPlaying = true;
        updatePlayPauseBtn(true);
        try {
            window.flutter_inappwebview.callHandler('onMusicPlaying',
                currentTrack.title||'Auspoty', currentTrack.artist||'', videoId||'');
        } catch(e) {}
        _startBgKeepAlive();
    } else if (ytPlayer && ytPlayer.loadVideoById) {
        // Web/PWA: pakai ytPlayer biasa
        ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
    }"""

content = content[:idx] + new_block + content[end_idx:]

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ playMusic() fixed!")

# Verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    v = f.read()
print(f"  APK Flutter block: {'✓' if 'APK Flutter: kirim ke MediaPlayer native' in v else '✗'}")
print(f"  flutter_inappwebview.callHandler in playMusic: {'✓' if 'callHandler' in v[v.find('Putar audio'):v.find('Putar audio')+500] else '✗'}")
