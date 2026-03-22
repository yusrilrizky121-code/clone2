import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Versi yang ada di disk
old = """    // Putar audio
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

new = """    // Putar audio via ytPlayer (baik di web maupun APK)
    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
    }
    _startBgKeepAlive();
    // Kirim info ke native service untuk notifikasi saja (tidak intercept audio)
    if (window.flutter_inappwebview) {
        try {
            window.flutter_inappwebview.callHandler('onMusicPlaying',
                currentTrack.title||'Auspoty', currentTrack.artist||'', '');
        } catch(e) {}
    }"""

if old in content:
    content = content.replace(old, new)
    print('OK: replaced')
else:
    print('ERROR: not found')
    # debug
    idx = content.find('Putar audio')
    if idx >= 0:
        print('Found "Putar audio" at:', idx)
        print(repr(content[idx:idx+600]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
