"""
Fix script.js untuk APK mode:
1. onPlayerStateChange - hapus callHandler dari sini (sudah dihandle di playMusic)
2. Pastikan di APK mode, ytPlayer events tidak double-trigger native
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Hapus callHandler dari onPlayerStateChange PLAYING event
# Line 46: try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', ...); } } catch(e) {}
old_playing_handler = "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||'', currentTrack.videoId||''); } } catch(e) {}\n        _startBgKeepAlive();"
new_playing_handler = "        // APK mode: onMusicPlaying sudah dipanggil dari playMusic(), tidak perlu di sini\n        if (!window.flutter_inappwebview) _startBgKeepAlive();"

if old_playing_handler in content:
    content = content.replace(old_playing_handler, new_playing_handler)
    print("✓ Removed duplicate onMusicPlaying from onPlayerStateChange")
else:
    # Try without the _startBgKeepAlive part
    old2 = "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||'', currentTrack.videoId||''); } } catch(e) {}"
    if old2 in content:
        content = content.replace(old2, "        // APK mode: onMusicPlaying sudah dipanggil dari playMusic()")
        print("✓ Removed duplicate onMusicPlaying (v2)")
    else:
        print("✗ Pattern not found, searching...")
        idx = content.find("callHandler('onMusicPlaying'")
        while idx >= 0:
            print(f"  Found at {idx}: {repr(content[max(0,idx-50):idx+100])}")
            idx = content.find("callHandler('onMusicPlaying'", idx+1)

# Fix 2: onPlayerStateChange PAUSED - di APK mode jangan trigger onMusicPaused dari ytPlayer
# karena ytPlayer di-mute, bukan di-pause
old_paused = "        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}"
new_paused = "        // APK mode: pause dihandle via AndroidBridge.pauseNative()"

if old_paused in content:
    content = content.replace(old_paused, new_paused)
    print("✓ Removed onMusicPaused from onPlayerStateChange PAUSED")
else:
    print("✗ onMusicPaused pattern not found in onPlayerStateChange")

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerifying...")
with open('public/script.js', 'r', encoding='utf-8') as f:
    v = f.read()

# Count callHandler occurrences
import re
handlers = re.findall(r"callHandler\('(\w+)'", v)
print(f"  callHandler calls: {handlers}")

# Check playMusic has the APK block
idx = v.find('Putar audio')
if idx >= 0:
    print(f"  playMusic APK block: ✓")
    print(f"  Block preview: {repr(v[idx:idx+200])}")
else:
    print("  playMusic APK block: ✗")
