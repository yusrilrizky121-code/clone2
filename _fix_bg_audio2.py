with open('public/script.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Convert to list of strings, normalize to LF for processing
content = ''.join(lines)

# ---- PATCH 1: Hapus native state vars ----
content = content.replace(
    '// Native audio state (ExoPlayer via Flutter MethodChannel)\n'
    'window._nativePlaying = false;\n'
    'window._nativeLoading = false;\n',
    ''
)

# ---- PATCH 2: Hapus check native di onPlayerStateChange ----
content = content.replace(
    '    // Jika native mode aktif, abaikan event ytPlayer\n'
    '    if (window._nativePlaying || window._nativeLoading) return;\n',
    ''
)

# ---- PATCH 3: Tambah flutter callback di PLAYING state ----
content = content.replace(
    "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n",
    "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n"
    "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}\n",
    1
)

# ---- PATCH 4: Tambah flutter callback di PAUSED state ----
content = content.replace(
    "        stopProgressBar();\n"
    "    } else if (event.data == YT.PlayerState.ENDED)",
    "        stopProgressBar();\n"
    "        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}\n"
    "    } else if (event.data == YT.PlayerState.ENDED)",
    1
)

# ---- PATCH 5: Fix playMusic - hapus blok AndroidBridge.playNative ----
old_play_block = (
    "    // *** KUNCI BACKGROUND AUDIO ***\n"
    "    // Cek AndroidBridge.playNative (tersedia di APK Flutter)\n"
    "    if (window.AndroidBridge && typeof window.AndroidBridge.playNative === 'function') {\n"
    "        // Stop ytPlayer jika sedang jalan\n"
    "        if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo();\n"
    "        window._nativePlaying = false;\n"
    "        window._nativeLoading = true;\n"
    "        isPlaying = true;\n"
    "        updatePlayPauseBtn(true);\n"
    "        // Kirim ke ExoPlayer native — service fetch URL sendiri, tidak butuh Flutter engine\n"
    "        window.AndroidBridge.playNative(\n"
    "            videoId,\n"
    "            currentTrack.title || '',\n"
    "            currentTrack.artist || '',\n"
    "            currentTrack.img || ''\n"
    "        );\n"
    "    } else {\n"
    "        // Fallback: web/PWA pakai ytPlayer\n"
    "        window._nativePlaying = false;\n"
    "        window._nativeLoading = false;\n"
    "        if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);\n"
    "    }\n"
)
new_play_block = (
    "    // Putar via ytPlayer — background audio dijaga oleh foreground service\n"
    "    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);\n"
)
content = content.replace(old_play_block, new_play_block, 1)

# ---- PATCH 6: Fix togglePlay - hapus semua logika native ----
old_toggle = (
    "function togglePlay() {\n"
    "    if (window._nativePlaying || window._nativeLoading) {\n"
    "        if (window._nativePlaying) {\n"
    "            // Pause native\n"
    "            if (window.AndroidBridge && typeof window.AndroidBridge.pauseNative === 'function') {\n"
    "                window.AndroidBridge.pauseNative();\n"
    "            }\n"
    "            window._nativePlaying = false;\n"
    "            isPlaying = false;\n"
    "            updatePlayPauseBtn(false);\n"
    "        } else if (window._nativeLoading) {\n"
    "            // Masih loading, abaikan\n"
    "        }\n"
    "    } else if (window._nativePaused) {\n"
    "        // Resume native\n"
    "        if (window.AndroidBridge && typeof window.AndroidBridge.resumeNative === 'function') {\n"
    "            window.AndroidBridge.resumeNative();\n"
    "        }\n"
    "        window._nativePlaying = true;\n"
    "        window._nativePaused = false;\n"
    "        isPlaying = true;\n"
    "        updatePlayPauseBtn(true);\n"
    "    } else {\n"
    "        // Web/PWA mode\n"
    "        if (!ytPlayer) return;\n"
    "        if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }\n"
    "    }\n"
    "}\n"
)
new_toggle = (
    "function togglePlay() {\n"
    "    if (!ytPlayer) return;\n"
    "    if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }\n"
    "}\n"
)
content = content.replace(old_toggle, new_toggle, 1)

# ---- PATCH 7: Fix startProgressBar - hapus check native ----
content = content.replace(
    "        if (window._nativePlaying || window._nativeLoading) return; // native mode: progress dihandle Flutter\n",
    ""
)

# ---- PATCH 8: Fix seekTo - hapus check native ----
old_seek = (
    "function seekTo(value) {\n"
    "    if (window._nativePlaying || window._nativeLoading) {\n"
    "        if (window.AndroidBridge && typeof window.AndroidBridge.seekNative === 'function') {\n"
    "            window.AndroidBridge.seekNative(value);\n"
    "        }\n"
    "        return;\n"
    "    }\n"
    "    if (!ytPlayer) return;\n"
)
new_seek = (
    "function seekTo(value) {\n"
    "    if (!ytPlayer) return;\n"
)
content = content.replace(old_seek, new_seek, 1)

# ---- PATCH 9: Fix comment di playMusic ----
content = content.replace(
    "// ============================================================\n"
    "// PLAY MUSIC — fungsi utama\n"
    "// Di APK Android: pakai AndroidBridge.playNative → ExoPlayer native\n"
    "// Di web/PWA: pakai ytPlayer (YouTube IFrame)\n"
    "// ============================================================\n",
    "// ============================================================\n"
    "// PLAY MUSIC — fungsi utama (ytPlayer)\n"
    "// Background audio dijaga oleh foreground service di Android\n"
    "// ============================================================\n"
)

# ---- PATCH 10: Fix comment di togglePlay ----
content = content.replace(
    "// ============================================================\n"
    "// TOGGLE PLAY — cek native mode dulu\n"
    "// ============================================================\n",
    ""
)

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    result = f.read()

checks = [
    ('_nativePlaying' not in result or result.count('_nativePlaying') == 0, '_nativePlaying removed'),
    ('_nativeLoading' not in result or result.count('_nativeLoading') == 0, '_nativeLoading removed'),
    ('playNative' not in result, 'playNative removed'),
    ('pauseNative' not in result, 'pauseNative removed'),
    ('onMusicPlaying' in result, 'onMusicPlaying callback added'),
    ('onMusicPaused' in result, 'onMusicPaused callback added'),
    ('loadVideoById' in result, 'ytPlayer.loadVideoById present'),
]

for ok, msg in checks:
    print(f"{'OK' if ok else 'FAIL'}: {msg}")
