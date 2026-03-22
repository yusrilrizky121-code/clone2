#!/usr/bin/env python3
import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

js = open('public/script.js', 'r', encoding='utf-8').read()
print("Lines before:", len(js.split('\n')))
print("Balance before:", js.count('{') - js.count('}'))

# 1. onPlayerStateChange PLAYING — tambah videoId sebagai arg ke-3
old1 = "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}"
new1 = "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||'', currentTrack.videoId||''); } } catch(e) {}"

if old1 in js:
    js = js.replace(old1, new1)
    print("✓ Fixed onPlayerStateChange PLAYING — added videoId")
else:
    print("⚠ onPlayerStateChange PLAYING pattern not found")

# 2. playMusic loadVideoById — tambah videoId
old2 = """    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title||'Auspoty', currentTrack.artist||'');
            }
        } catch(e) {}
    }"""
new2 = """    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title||'Auspoty', currentTrack.artist||'', videoId||'');
            }
        } catch(e) {}
    }"""

if old2 in js:
    js = js.replace(old2, new2)
    print("✓ Fixed playMusic — added videoId")
else:
    print("⚠ playMusic pattern not found")

# 3. togglePlay — saat resume, kirim onMusicResumed bukan onMusicPlaying
old3 = """    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview && currentTrack) window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } catch(e) {}
    }
}"""
new3 = """    } else {
        ytPlayer.playVideo();
        try { if (window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
}"""

if old3 in js:
    js = js.replace(old3, new3)
    print("✓ Fixed togglePlay resume — use onMusicResumed")
else:
    print("⚠ togglePlay resume pattern not found")

# Verifikasi
print("Balance after:", js.count('{') - js.count('}'))
open('public/script.js', 'w', encoding='utf-8').write(js)
print("✓ Saved, lines:", len(js.split('\n')))
