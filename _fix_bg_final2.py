#!/usr/bin/env python3
"""
Iterasi fix background audio - pendekatan baru:
1. script.js: tambah interval yang re-apply visibilitychange block setiap 5 detik saat musik jalan
2. script.js: pastikan onMusicPlaying dipanggil dengan benar di semua titik
3. main.dart: ganti reflection onPause dengan pendekatan WidgetsBindingObserver yang sudah ada
"""
import re

# ─── FIX script.js ───────────────────────────────────────────────────────────
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')
js_path = 'public/script.js'
js = open(js_path, 'r', encoding='utf-8').read()

# Cek kondisi saat ini
print("=== script.js status ===")
print("onMusicPlaying calls:", js.count("callHandler('onMusicPlaying'"))
print("onMusicPaused calls:", js.count("callHandler('onMusicPaused'"))
print("toggleBgMode:", 'function toggleBgMode' in js)
print("Lines:", len(js.split('\n')))

# Tambahkan fungsi _startBgKeepAlive yang jaga visibilitychange tetap blocked
# dan re-apply setiap 5 detik saat musik jalan
bg_keepalive_js = """
// ── BACKGROUND KEEP-ALIVE ────────────────────────────────────────────────────
// Re-apply visibility block setiap 5 detik saat musik jalan di Flutter APK
let _bgKeepAliveInterval = null;

function _applyVisibilityBlock() {
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
}

function _startBgKeepAlive() {
    _applyVisibilityBlock();
    if (_bgKeepAliveInterval) clearInterval(_bgKeepAliveInterval);
    _bgKeepAliveInterval = setInterval(_applyVisibilityBlock, 5000);
}

function _stopBgKeepAlive() {
    if (_bgKeepAliveInterval) { clearInterval(_bgKeepAliveInterval); _bgKeepAliveInterval = null; }
}
"""

# Tambahkan setelah deklarasi _bgModeActive
if '_startBgKeepAlive' not in js:
    js = js.replace(
        'let _bgModeActive = false;',
        'let _bgModeActive = false;\n' + bg_keepalive_js
    )
    print("✓ Added _startBgKeepAlive")
else:
    print("- _startBgKeepAlive already exists")

# Panggil _startBgKeepAlive saat onMusicPlaying
# Cari di onPlayerStateChange PLAYING state
old_playing_block = "        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}"
new_playing_block = """        try { if (window.flutter_inappwebview && currentTrack) { window.flutter_inappwebview.callHandler('onMusicPlaying', currentTrack.title||'Auspoty', currentTrack.artist||''); } } catch(e) {}
        _startBgKeepAlive();"""

if old_playing_block in js and '_startBgKeepAlive();' not in js:
    js = js.replace(old_playing_block, new_playing_block, 1)
    print("✓ Added _startBgKeepAlive call in PLAYING state")

# Panggil _stopBgKeepAlive saat onMusicPaused
old_paused_block = "        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}"
new_paused_block = """        try { if (window.flutter_inappwebview) { window.flutter_inappwebview.callHandler('onMusicPaused'); } } catch(e) {}
        _stopBgKeepAlive();"""

if old_paused_block in js and '_stopBgKeepAlive' not in js:
    js = js.replace(old_paused_block, new_paused_block, 1)
    print("✓ Added _stopBgKeepAlive call in PAUSED state")

# Juga panggil _startBgKeepAlive di playMusic saat loadVideoById
old_load = """    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title||'Auspoty', currentTrack.artist||'');
            }
        } catch(e) {}
    }"""
new_load = """    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
        try {
            if (window.flutter_inappwebview && currentTrack) {
                window.flutter_inappwebview.callHandler('onMusicPlaying',
                    currentTrack.title||'Auspoty', currentTrack.artist||'');
            }
        } catch(e) {}
    }"""

if old_load in js:
    js = js.replace(old_load, new_load)
    print("✓ Added _startBgKeepAlive in playMusic")
else:
    print("⚠ playMusic loadVideoById block not found exactly")

open(js_path, 'w', encoding='utf-8').write(js)
print("✓ Saved script.js, lines:", len(js.split('\n')))

# ─── FIX main.dart — ganti reflection dengan pendekatan bersih ───────────────
dart_path = 'auspoty-flutter/lib/main.dart'
dart = open(dart_path, 'r', encoding='utf-8').read()

print("\n=== main.dart status ===")
print("WidgetsBindingObserver:", 'WidgetsBindingObserver' in dart)
print("didChangeAppLifecycleState:", 'didChangeAppLifecycleState' in dart)
print("_musicPlaying:", '_musicPlaying' in dart)
print("Lines:", len(dart.split('\n')))

# main.dart sudah punya WidgetsBindingObserver - tidak perlu ubah
# Tapi perlu pastikan MainActivity.kt tidak pakai reflection yang bisa crash

# ─── FIX MainActivity.kt — hapus reflection, pakai pendekatan sederhana ─────
kt_path = 'auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MainActivity.kt'
kt = open(kt_path, 'r', encoding='utf-8').read()

print("\n=== MainActivity.kt status ===")
print("onPause override:", 'override fun onPause' in kt)
print("reflection:", 'getDeclaredMethod' in kt)
print("Lines:", len(kt.split('\n')))

# Ganti reflection dengan pendekatan yang lebih aman:
# Pakai FlutterActivity.onUserLeaveHint() untuk detect background
# dan jangan override onPause sama sekali — biarkan Flutter handle
# tapi inject JS dari Dart side via WidgetsBindingObserver

old_onpause = '''    override fun onPause() {
        if (musicPlaying) {
            // Panggil Activity.onPause() langsung, skip FlutterActivity.onPause()
            // FlutterActivity.onPause() → flutterView.onPause() → suspend engine → YouTube stop
            try {
                val method = android.app.Activity::class.java.getDeclaredMethod("onPause")
                method.isAccessible = true
                method.invoke(this)
            } catch (e: Exception) {
                // Fallback: tetap panggil super tapi pastikan service jalan
                super.onPause()
            }
            service?.keepAlive()
        } else {
            super.onPause()
        }
    }'''

new_onpause = '''    override fun onPause() {
        // Selalu panggil super — jangan skip Flutter engine pause
        // Background audio dijaga oleh:
        // 1. MusicPlayerService foreground service (wakelock)
        // 2. visibilitychange block di JS (inject dari Dart WidgetsBindingObserver)
        // 3. _startBgKeepAlive interval di script.js
        super.onPause()
        if (musicPlaying) {
            service?.keepAlive()
        }
    }

    override fun onUserLeaveHint() {
        // Dipanggil saat user tekan Home/Recent — bukan Back
        super.onUserLeaveHint()
        if (musicPlaying) {
            service?.keepAlive()
            android.util.Log.d("MainActivity", "onUserLeaveHint — music playing, keepAlive")
        }
    }'''

if old_onpause in kt:
    kt = kt.replace(old_onpause, new_onpause)
    print("✓ Replaced onPause (removed reflection)")
else:
    # Coba cari dengan regex
    m = re.search(r'override fun onPause\(\) \{.*?\}', kt, re.DOTALL)
    if m:
        print("Found onPause via regex:", repr(m.group()[:100]))
        kt = kt[:m.start()] + new_onpause + kt[m.end():]
        print("✓ Replaced onPause via regex")
    else:
        print("⚠ onPause not found")

open(kt_path, 'w', encoding='utf-8').write(kt)
print("✓ Saved MainActivity.kt, lines:", len(kt.split('\n')))
print("reflection removed:", 'getDeclaredMethod' not in kt)
print("onUserLeaveHint:", 'onUserLeaveHint' in kt)
