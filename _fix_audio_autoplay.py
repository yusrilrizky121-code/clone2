#!/usr/bin/env python3
"""
Fix: suara tidak keluar karena _applyVisibilityBlock memanggil ytPlayer.playVideo()
yang diblokir autoplay policy WebView.

Solusi:
1. Hapus ytPlayer.playVideo() dari _applyVisibilityBlock — jangan force play
2. Biarkan YouTube IFrame handle sendiri via visibilityState = 'visible'
3. Pastikan mediaPlaybackRequiresUserGesture = false sudah di main.dart (sudah ada)
"""
import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

js = open('public/script.js', 'r', encoding='utf-8').read()

print("Lines before:", len(js.split('\n')))
print("Balance before:", js.count('{') - js.count('}'))

# Ganti _applyVisibilityBlock — hapus bagian ytPlayer.playVideo()
old_apply = """function _applyVisibilityBlock() {
    try {
        Object.defineProperty(document, 'hidden', {
            get: function(){ return false; }, configurable: true
        });
        Object.defineProperty(document, 'visibilityState', {
            get: function(){ return 'visible'; }, configurable: true
        });
    } catch(e) {}
    // Jika ytPlayer pause karena visibility, resume
    try {
        if (window.ytPlayer && typeof window.ytPlayer.getPlayerState === 'function') {
            if (window.ytPlayer.getPlayerState() === 2 && isPlaying) {
                window.ytPlayer.playVideo();
            }
        }
    } catch(e) {}
}"""

new_apply = """function _applyVisibilityBlock() {
    // Hanya override visibility — JANGAN panggil playVideo() langsung
    // karena WebView blokir autoplay tanpa user gesture
    try {
        Object.defineProperty(document, 'hidden', {
            get: function(){ return false; }, configurable: true
        });
        Object.defineProperty(document, 'visibilityState', {
            get: function(){ return 'visible'; }, configurable: true
        });
    } catch(e) {}
}"""

if old_apply in js:
    js = js.replace(old_apply, new_apply)
    print("✓ Fixed _applyVisibilityBlock (removed ytPlayer.playVideo)")
else:
    # Cari dengan regex lebih fleksibel
    m = re.search(
        r'function _applyVisibilityBlock\(\) \{.*?\}',
        js, re.DOTALL
    )
    if m:
        js = js[:m.start()] + new_apply + js[m.end():]
        print("✓ Fixed _applyVisibilityBlock via regex")
    else:
        print("⚠ _applyVisibilityBlock not found")

# Verifikasi balance
opens = js.count('{')
closes = js.count('}')
print(f"Balance after: {opens} - {closes} = {opens - closes}")

open('public/script.js', 'w', encoding='utf-8').write(js)
print("✓ Saved, lines:", len(js.split('\n')))

# Verifikasi tidak ada ytPlayer.playVideo di keepalive
if 'ytPlayer.playVideo' in js[js.find('_applyVisibilityBlock'):js.find('_applyVisibilityBlock')+300]:
    print("⚠ ytPlayer.playVideo masih ada di _applyVisibilityBlock!")
else:
    print("✓ ytPlayer.playVideo sudah dihapus dari keepalive")
