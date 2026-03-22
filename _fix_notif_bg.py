#!/usr/bin/env python3
"""
Fix notifikasi tidak update + musik berhenti saat background.
"""
import re

path = 'public/script.js'
content = open(path, 'r', encoding='utf-8').read()
lines = content.split('\n')

# ── 1. Hapus duplikat onMusicPlaying ─────────────────────────────────────────
new_lines = []
prev = None
for l in lines:
    stripped = l.strip()
    if (stripped.startswith("try { if (window.flutter_inappwebview && currentTrack)")
            and "onMusicPlaying" in stripped
            and l == prev):
        continue
    new_lines.append(l)
    prev = l
content = '\n'.join(new_lines)
print("After dedup lines:", len(content.split('\n')))

# ── 2. Fix playMusic — tambah callHandler saat loadVideoById ─────────────────
old2 = "    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);"
new2 = """    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title||'Auspoty', currentTrack.artist||'');
            }
        } catch(e) {}
    }"""
if old2 in content:
    content = content.replace(old2, new2)
    print("✓ Fixed playMusic")
else:
    print("⚠ playMusic pattern not found, trying regex...")
    m = re.search(r'if \(ytPlayer && ytPlayer\.loadVideoById\) ytPlayer\.loadVideoById\(videoId\);', content)
    if m:
        content = content[:m.start()] + new2.strip() + content[m.end():]
        print("✓ Fixed playMusic via regex")
    else:
        print("✗ playMusic not fixed")

# ── 3. Fix togglePlay ─────────────────────────────────────────────────────────
m = re.search(r'function togglePlay\(\) \{[^\}]+\}', content, re.DOTALL)
if m:
    old_t = m.group()
    print("togglePlay found:", repr(old_t[:150]))
    new_t = """function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview && currentTrack) window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } catch(e) {}
    }
}"""
    content = content[:m.start()] + new_t + content[m.end():]
    print("✓ Fixed togglePlay")
else:
    print("⚠ togglePlay not found via regex")

# ── 4. Simpan ─────────────────────────────────────────────────────────────────
open(path, 'w', encoding='utf-8').write(content)
print("✓ Saved script.js")

# Verifikasi
c2 = open(path, 'r', encoding='utf-8').read()
print("Lines:", len(c2.split('\n')))
print("onMusicPlaying calls:", c2.count("callHandler('onMusicPlaying'"))
print("onMusicPaused calls:", c2.count("callHandler('onMusicPaused'"))
