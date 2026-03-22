#!/usr/bin/env python3
import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

js = open('public/script.js','r',encoding='utf-8').read()

# Ganti seluruh togglePlay yang rusak dengan versi bersih
# Cari dari "// TOGGLE PLAY" sampai "function updatePlayPauseBtn"
old_toggle_section = """// TOGGLE PLAY
function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview && currentTrack) window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } catch(e) {}
    }
} else { ytPlayer.playVideo(); }
}"""

new_toggle_section = """// TOGGLE PLAY
function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview && currentTrack) window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } catch(e) {}
    }
}"""

if old_toggle_section in js:
    js = js.replace(old_toggle_section, new_toggle_section)
    print("✓ Fixed togglePlay via exact match")
else:
    # Pakai regex untuk cari dan ganti seluruh fungsi togglePlay
    m = re.search(r'// TOGGLE PLAY\nfunction togglePlay\(\) \{.*?\n\}(?:\s*else[^\n]+\n)?\}', js, re.DOTALL)
    if m:
        print("Found via regex:", repr(m.group()[:200]))
        js = js[:m.start()] + new_toggle_section + js[m.end():]
        print("✓ Fixed togglePlay via regex")
    else:
        # Manual: hapus line yang bermasalah
        lines = js.split('\n')
        new_lines = []
        skip_next = False
        for i, l in enumerate(lines):
            if l.strip() == '} else { ytPlayer.playVideo(); }':
                print(f"✓ Removed bad line {i+1}: {repr(l)}")
                continue  # skip baris ini
            new_lines.append(l)
        js = '\n'.join(new_lines)
        print("✓ Fixed via line removal")

# Verifikasi balance
opens = js.count('{')
closes = js.count('}')
print(f"Balance: {opens} - {closes} = {opens-closes}")

open('public/script.js','w',encoding='utf-8').write(js)
print("✓ Saved, lines:", len(js.split('\n')))
