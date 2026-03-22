"""
Fix playMusic() di script.js:
- Saat di APK Flutter: jangan load ytPlayer, langsung kirim ke native
- Saat di web/PWA: pakai ytPlayer biasa
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact block
old_block = """    // Putar via ytPlayer \u2014 background audio dijaga oleh foreground service
    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',  
                    currentTrack.title||'Auspoty', currentTrack.artist||'', videoId||'');
            }
        } catch(e) {}
    }"""

new_block = """    // Putar audio
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

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✓ playMusic() fixed - APK mode now skips ytPlayer")
else:
    print("✗ Block not found, trying alternative search...")
    idx = content.find('Putar via ytPlayer')
    if idx >= 0:
        # Find the end of this if block
        end_idx = content.find('\n    }', idx)
        end_idx2 = content.find('\n    }\n\n    // Pre-fetch', idx)
        print(f"Found at {idx}, end at {end_idx2}")
        print(repr(content[idx:end_idx2+6]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Also fix togglePlay - saat APK mode, toggle harus via flutter handler
with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_toggle = """// TOGGLE PLAY
function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
}"""

new_toggle = """// TOGGLE PLAY
function togglePlay() {
    if (window.flutter_inappwebview) {
        // APK mode: toggle via native
        if (isPlaying) {
            isPlaying = false;
            updatePlayPauseBtn(false);
            try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
        } else {
            isPlaying = true;
            updatePlayPauseBtn(true);
            try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
        }
        return;
    }
    // Web/PWA mode
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
    } else {
        ytPlayer.playVideo();
    }
}"""

if old_toggle in content:
    content = content.replace(old_toggle, new_toggle)
    print("✓ togglePlay() fixed - APK mode uses flutter handler")
else:
    print("✗ togglePlay pattern not found, checking...")
    idx = content.find('function togglePlay')
    if idx >= 0:
        print(repr(content[idx:idx+300]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerifying...")
with open('public/script.js', 'r', encoding='utf-8') as f:
    v = f.read()
print(f"  APK mode in playMusic: {'✓' if 'window.flutter_inappwebview' in v and 'APK Flutter' in v else '✗'}")
print(f"  togglePlay APK mode: {'✓' if 'APK mode: toggle via native' in v else '✗'}")
