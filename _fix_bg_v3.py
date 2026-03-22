with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# ---- 1. Fix playMusic block ----
old_play = """    // *** KUNCI BACKGROUND AUDIO ***
    // Cek AndroidBridge.playNative (tersedia di APK Flutter)
    if (window.AndroidBridge && typeof window.AndroidBridge.playNative === 'function') {
        // Stop ytPlayer jika sedang jalan
        if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo();
        window._nativePlaying = false;
        window._nativeLoading = true;
        isPlaying = true;
        updatePlayPauseBtn(true);
        // Kirim ke ExoPlayer native — service fetch URL sendiri, tidak butuh Flutter engine
        window.AndroidBridge.playNative(
            videoId,
            currentTrack.title || '',
            currentTrack.artist || '',
            currentTrack.img || ''
        );
    } else {
        // Fallback: web/PWA pakai ytPlayer
        window._nativePlaying = false;
        window._nativeLoading = false;
        if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);
    }"""

new_play = """    // Putar via ytPlayer — background audio dijaga oleh foreground service
    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);"""

if old_play in content:
    content = content.replace(old_play, new_play, 1)
    print("OK: playMusic block fixed")
else:
    print("WARN: playMusic block not found, trying alternate...")
    # Try with different line endings
    old_play2 = old_play.replace('\n', '\r\n')
    if old_play2 in content:
        content = content.replace(old_play2, new_play, 1)
        print("OK: playMusic block fixed (CRLF)")
    else:
        print("FAIL: playMusic block not found")

# ---- 2. Fix togglePlay ----
old_toggle = """// ============================================================
// TOGGLE PLAY — cek native mode dulu
// ============================================================
function togglePlay() {
    if (window._nativePlaying || window._nativeLoading) {
        if (window._nativePlaying) {
            // Pause native
            if (window.AndroidBridge && typeof window.AndroidBridge.pauseNative === 'function') {
                window.AndroidBridge.pauseNative();
            }
            window._nativePlaying = false;
            isPlaying = false;
            updatePlayPauseBtn(false);
        } else if (window._nativeLoading) {
            // Masih loading, abaikan
        }
    } else if (window._nativePaused) {
        // Resume native
        if (window.AndroidBridge && typeof window.AndroidBridge.resumeNative === 'function') {
            window.AndroidBridge.resumeNative();
        }
        window._nativePlaying = true;
        window._nativePaused = false;
        isPlaying = true;
        updatePlayPauseBtn(true);
    } else {
        // Web/PWA mode
        if (!ytPlayer) return;
        if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }
    }
}"""

new_toggle = """function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }
}"""

if old_toggle in content:
    content = content.replace(old_toggle, new_toggle, 1)
    print("OK: togglePlay fixed")
else:
    print("WARN: togglePlay not found exact, trying partial...")
    # Find and replace just the function body
    import re
    m = re.search(r'function togglePlay\(\) \{.*?\n\}', content, re.DOTALL)
    if m:
        content = content[:m.start()] + new_toggle + content[m.end():]
        print("OK: togglePlay fixed (regex)")
    else:
        print("FAIL: togglePlay not found")

# ---- 3. Fix startProgressBar - hapus check native ----
old_check = "        if (window._nativePlaying || window._nativeLoading) return; // native mode: progress dihandle Flutter\n"
if old_check in content:
    content = content.replace(old_check, '', 1)
    print("OK: startProgressBar native check removed")
else:
    print("INFO: startProgressBar check already removed or not found")

# ---- 4. Fix seekTo ----
old_seek = """function seekTo(value) {
    if (window._nativePlaying || window._nativeLoading) {
        if (window.AndroidBridge && typeof window.AndroidBridge.seekNative === 'function') {
            window.AndroidBridge.seekNative(value);
        }
        return;
    }
    if (ytPlayer && ytPlayer.getDuration) {
        ytPlayer.seekTo((value / 100) * ytPlayer.getDuration(), true);
        const bar = document.getElementById('progressBar');
        if (bar) bar.style.background = 'linear-gradient(to right, white ' + value + '%, rgba(255,255,255,0.2) ' + value + '%)';
    }
}"""

new_seek = """function seekTo(value) {
    if (ytPlayer && ytPlayer.getDuration) {
        ytPlayer.seekTo((value / 100) * ytPlayer.getDuration(), true);
        const bar = document.getElementById('progressBar');
        if (bar) bar.style.background = 'linear-gradient(to right, white ' + value + '%, rgba(255,255,255,0.2) ' + value + '%)';
    }
}"""

if old_seek in content:
    content = content.replace(old_seek, new_seek, 1)
    print("OK: seekTo fixed")
else:
    print("INFO: seekTo already fixed or not found")

# ---- 5. Hapus native state vars ----
for old in [
    'window._nativePlaying = false;\nwindow._nativeLoading = false;\nwindow._nativePaused = false;\n',
    'window._nativePlaying = false;\nwindow._nativeLoading = false;\n',
]:
    if old in content:
        content = content.replace(old, '', 1)
        print("OK: native state vars removed")
        break

# ---- 6. Fix startProgressBar - ada versi lain ----
old_check2 = "        if (window._nativePlaying) return;\n"
if old_check2 in content:
    content = content.replace(old_check2, '', 1)
    print("OK: startProgressBar check2 removed")

# ---- 7. Fix comment di playMusic ----
content = content.replace(
    '// Di APK Android: AndroidBridge.playNative -> ExoPlayer native (background-safe)\n'
    '// Di web/PWA: ytPlayer (YouTube IFrame)\n',
    '// Background audio dijaga oleh foreground service Android\n'
)

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Final verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    result = f.read()

print("\n=== FINAL VERIFY ===")
print(f"_nativePlaying: {result.count('_nativePlaying')}")
print(f"_nativeLoading: {result.count('_nativeLoading')}")
print(f"_nativePaused: {result.count('_nativePaused')}")
print(f"playNative: {result.count('playNative')}")
print(f"pauseNative: {result.count('pauseNative')}")
print(f"seekNative: {result.count('seekNative')}")
print(f"onMusicPlaying: {result.count('onMusicPlaying')}")
print(f"onMusicPaused: {result.count('onMusicPaused')}")
print(f"loadVideoById: {result.count('loadVideoById')}")
