with open('public/script.js', 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8').replace('\r\n', '\n')

# ---- Fix onPlayerStateChange ----
old_fn = '''function onPlayerStateChange(event) {
    // Jika native mode aktif, abaikan event ytPlayer
    if (window._nativePlaying || window._nativeLoading) return;
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (event.data == YT.PlayerState.PLAYING) {
        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
    } else if (event.data == YT.PlayerState.PAUSED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
    } else if (event.data == YT.PlayerState.ENDED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
        if (isRepeat && ytPlayer) { ytPlayer.seekTo(0); ytPlayer.playVideo(); }
        else { playNextSimilarSong(); }
    }
}'''

new_fn = '''function onPlayerStateChange(event) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (event.data == YT.PlayerState.PLAYING) {
        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        // Update notifikasi Android
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title || 'Auspoty',
                    currentTrack.artist || '');
            }
        } catch(e) {}
    } else if (event.data == YT.PlayerState.PAUSED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
        // Update notifikasi Android (pause)
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPaused',
                    currentTrack.title || 'Auspoty',
                    currentTrack.artist || '');
            }
        } catch(e) {}
    } else if (event.data == YT.PlayerState.ENDED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
        if (isRepeat && ytPlayer) { ytPlayer.seekTo(0); ytPlayer.playVideo(); }
        else { playNextSimilarSong(); }
    }
}'''

if old_fn in text:
    text = text.replace(old_fn, new_fn, 1)
    print("OK: onPlayerStateChange fixed")
else:
    print("WARN: old_fn not found, trying partial replace...")
    # Just remove the native check line
    text = text.replace(
        '    // Jika native mode aktif, abaikan event ytPlayer\n'
        '    if (window._nativePlaying || window._nativeLoading) return;\n',
        ''
    )
    # Add callbacks if not present
    if 'onMusicPlaying' not in text:
        text = text.replace(
            "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n",
            "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n"
            "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}\n",
            1
        )
    if 'onMusicPaused' not in text:
        # Add after stopProgressBar in PAUSED block
        import re
        text = re.sub(
            r"(    } else if \(event\.data == YT\.PlayerState\.PAUSED\) \{.*?stopProgressBar\(\);)",
            r"\1\n        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPaused', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}",
            text,
            count=1,
            flags=re.DOTALL
        )
    print("OK: partial fix applied")

with open('public/script.js', 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

# Verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    result = f.read()

print(f"_nativePlaying refs: {result.count('_nativePlaying')}")
print(f"_nativeLoading refs: {result.count('_nativeLoading')}")
print(f"onMusicPlaying: {result.count('onMusicPlaying')}")
print(f"onMusicPaused: {result.count('onMusicPaused')}")
