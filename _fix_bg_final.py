with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# ---- 1. Hapus native state vars ----
content = content.replace(
    'window._nativePlaying = false;\n'
    'window._nativeLoading = false;\n'
    'window._nativePaused = false;\n',
    ''
)

# ---- 2. Hapus check native di onPlayerStateChange (jika masih ada) ----
for old in [
    '    if (window._nativePlaying || window._nativeLoading) return;\n',
    '    // Jika native mode aktif, abaikan event ytPlayer\n    if (window._nativePlaying || window._nativeLoading) return;\n',
]:
    content = content.replace(old, '')

# ---- 3. Tambah flutter callback di PLAYING state (hanya jika belum ada) ----
if 'onMusicPlaying' not in content:
    content = content.replace(
        "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n",
        "        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';\n"
        "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}\n",
        1
    )

# ---- 4. Tambah flutter callback di PAUSED state (hanya jika belum ada) ----
if 'onMusicPaused' not in content:
    content = content.replace(
        "        stopProgressBar();\n"
        "    } else if (event.data == YT.PlayerState.ENDED)",
        "        stopProgressBar();\n"
        "        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}\n"
        "    } else if (event.data == YT.PlayerState.ENDED)",
        1
    )

# ---- 5. Fix playMusic - cari blok if AndroidBridge.playNative dan replace ----
import re

# Cari dari "// *** KUNCI" atau "// Di APK Android" sampai sebelum "// Pre-fetch"
# Ganti seluruh blok if/else yang berisi playNative
pattern_play = re.compile(
    r'    // (?:\*\*\* KUNCI BACKGROUND AUDIO \*\*\*|Di APK Android.*?)\n'
    r'.*?'
    r'(?=    // Pre-fetch lagu berikutnya)',
    re.DOTALL
)
new_play = (
    "    // Putar via ytPlayer — background audio dijaga oleh foreground service\n"
    "    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);\n\n"
)
content = pattern_play.sub(new_play, content, count=1)

# ---- 6. Fix togglePlay ----
pattern_toggle = re.compile(
    r'function togglePlay\(\) \{.*?\n\}',
    re.DOTALL
)
new_toggle = (
    "function togglePlay() {\n"
    "    if (!ytPlayer) return;\n"
    "    if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }\n"
    "}"
)
content = pattern_toggle.sub(new_toggle, content, count=1)

# ---- 7. Fix seekTo - hapus check native ----
pattern_seek = re.compile(
    r'function seekTo\(value\) \{.*?(?=    if \(!ytPlayer\) return;)',
    re.DOTALL
)
# Simpler: just replace the whole seekTo
pattern_seek2 = re.compile(
    r'function seekTo\(value\) \{.*?\n\}',
    re.DOTALL
)
new_seek = (
    "function seekTo(value) {\n"
    "    if (!ytPlayer) return;\n"
    "    const dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;\n"
    "    if (dur > 0) ytPlayer.seekTo(value / 100 * dur, true);\n"
    "}"
)
content = pattern_seek2.sub(new_seek, content, count=1)

# ---- 8. Fix startProgressBar - hapus check native ----
content = content.replace(
    "        if (window._nativePlaying || window._nativeLoading) return; // native mode: progress dihandle Flutter\n",
    ""
)
content = content.replace(
    "        if (window._nativePlaying) return;\n",
    ""
)

# ---- 9. Hapus sisa referensi native ----
for old in [
    'window._nativePlaying = true;\n',
    'window._nativePlaying = false;\n',
    'window._nativeLoading = true;\n',
    'window._nativeLoading = false;\n',
    'window._nativePaused = true;\n',
    'window._nativePaused = false;\n',
]:
    content = content.replace(old, '')

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    result = f.read()

native_count = result.count('_nativePlaying') + result.count('_nativeLoading') + result.count('_nativePaused')
print(f"Native refs remaining: {native_count}")
print(f"playNative refs: {result.count('playNative')}")
print(f"pauseNative refs: {result.count('pauseNative')}")
print(f"onMusicPlaying: {result.count('onMusicPlaying')}")
print(f"onMusicPaused: {result.count('onMusicPaused')}")
print(f"loadVideoById: {result.count('loadVideoById')}")
print(f"togglePlay function:")
idx = result.find('function togglePlay')
print(repr(result[idx:idx+150]))
print(f"\nplayMusic ytPlayer call:")
idx2 = result.find('loadVideoById(videoId)')
print(repr(result[max(0,idx2-100):idx2+80]))
