with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Hapus native state vars
content = content.replace(
    '// Native audio state (ExoPlayer via Flutter MethodChannel)\r\nwindow._nativePlaying = false;\r\nwindow._nativeLoading = false;\r\n',
    ''
)
# juga coba LF only
content = content.replace(
    '// Native audio state (ExoPlayer via Flutter MethodChannel)\nwindow._nativePlaying = false;\nwindow._nativeLoading = false;\n',
    ''
)

# 2. Hapus check native di onPlayerStateChange
content = content.replace(
    '    // Jika native mode aktif, abaikan event ytPlayer\r\n    if (window._nativePlaying || window._nativeLoading) return;\r\n',
    ''
)
content = content.replace(
    '    // Jika native mode aktif, abaikan event ytPlayer\n    if (window._nativePlaying || window._nativeLoading) return;\n',
    ''
)

# 3. Tambah flutter callback di PLAYING state (setelah mediaSession line)
old1 = "if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';"
new1 = "if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}"
content = content.replace(old1, new1, 1)

# 4. Tambah flutter callback di PAUSED state (setelah stopProgressBar() di blok PAUSED)
# Cari pola: stopProgressBar();\n    } else if (event.data == YT.PlayerState.ENDED)
old2_crlf = "        stopProgressBar();\r\n    } else if (event.data == YT.PlayerState.ENDED)"
new2_crlf = "        stopProgressBar();\r\n        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}\r\n    } else if (event.data == YT.PlayerState.ENDED)"
content = content.replace(old2_crlf, new2_crlf, 1)

old2_lf = "        stopProgressBar();\n    } else if (event.data == YT.PlayerState.ENDED)"
new2_lf = "        stopProgressBar();\n        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}\n    } else if (event.data == YT.PlayerState.ENDED)"
content = content.replace(old2_lf, new2_lf, 1)

# 5. Fix playMusic — hapus semua logika AndroidBridge.playNative, kembalikan ke ytPlayer murni
# Cari blok "// *** KUNCI BACKGROUND AUDIO ***" sampai akhir fungsi playMusic
import re

# Replace seluruh blok if/else AndroidBridge di playMusic
old_block = r"""    // \*\*\* KUNCI BACKGROUND AUDIO \*\*\*
    // Cek AndroidBridge\.playNative \(tersedia di APK Flutter\)
    if \(window\.AndroidBridge && typeof window\.AndroidBridge\.playNative === 'function'\) \{
        // Stop ytPlayer jika sedang jalan
        if \(ytPlayer && ytPlayer\.stopVideo\) ytPlayer\.stopVideo\(\);
        window\._nativePlaying = false;
        window\._nativeLoading = true;
        isPlaying = true;
        updatePlayPauseBtn\(true\);
        // Kirim ke ExoPlayer native — service fetch URL sendiri, tidak butuh Flutter engine
        window\.AndroidBridge\.playNative\(
            videoId,
            currentTrack\.title \|\| '',
            currentTrack\.artist \|\| '',
            currentTrack\.img \|\| ''
        \);
    \} else \{
        // Fallback: web/PWA pakai ytPlayer
        window\._nativePlaying = false;
        window\._nativeLoading = false;
        if \(ytPlayer && ytPlayer\.loadVideoById\) ytPlayer\.loadVideoById\(videoId\);
    \}"""

new_block = """    // Putar via ytPlayer — background audio dijaga oleh foreground service
    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);"""

content = re.sub(old_block, new_block, content, flags=re.DOTALL)

# 6. Fix togglePlay — hapus semua logika native, kembalikan ke ytPlayer murni
old_toggle = r"""function togglePlay\(\) \{
    if \(window\._nativePlaying \|\| window\._nativeLoading\) \{
        if \(window\._nativePlaying\) \{
            // Pause native
            if \(window\.AndroidBridge && typeof window\.AndroidBridge\.pauseNative === 'function'\) \{
                window\.AndroidBridge\.pauseNative\(\);
            \}
            window\._nativePlaying = false;
            isPlaying = false;
            updatePlayPauseBtn\(false\);
        \} else if \(window\._nativeLoading\) \{
            // Masih loading, abaikan
        \}
    \} else if \(window\._nativePaused\) \{
        // Resume native
        if \(window\.AndroidBridge && typeof window\.AndroidBridge\.resumeNative === 'function'\) \{
            window\.AndroidBridge\.resumeNative\(\);
        \}
        window\._nativePlaying = true;
        window\._nativePaused = false;
        isPlaying = true;
        updatePlayPauseBtn\(true\);
    \} else \{
        // Web/PWA mode
        if \(!ytPlayer\) return;
        if \(isPlaying\) \{ ytPlayer\.pauseVideo\(\); \} else \{ ytPlayer\.playVideo\(\); \}
    \}
\}"""

new_toggle = """function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }
}"""

content = re.sub(old_toggle, new_toggle, content, flags=re.DOTALL)

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done! script.js fixed.')
