with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Tambah fungsi toggleBgMode sebelum // INIT
bg_mode_code = '''
// ============================================================
// BACKGROUND MODE — aktifkan agar musik tetap jalan saat keluar app
// Saat aktif: kirim sinyal ke Flutter untuk jaga service tetap hidup
// ============================================================
window._bgModeActive = false;

function toggleBgMode() {
    window._bgModeActive = !window._bgModeActive;
    const btn = document.getElementById('btnBgMode');
    if (window._bgModeActive) {
        // Aktif — icon berwarna accent
        if (btn) btn.style.fill = 'var(--accent, #a78bfa)';
        showToast('Mode latar belakang aktif 🎵');
        // Beritahu Flutter untuk aktifkan background mode
        try {
            if (window.flutter_inappwebview) {
                window.flutter_inappwebview.callHandler('setBgMode', true,
                    currentTrack ? currentTrack.title || '' : '',
                    currentTrack ? currentTrack.artist || '' : '');
            }
        } catch(e) {}
    } else {
        // Nonaktif
        if (btn) btn.style.fill = 'rgba(255,255,255,0.5)';
        showToast('Mode latar belakang dinonaktifkan');
        try {
            if (window.flutter_inappwebview) {
                window.flutter_inappwebview.callHandler('setBgMode', false, '', '');
            }
        } catch(e) {}
    }
}

// Update icon bgMode saat lagu ganti
function _updateBgModeNotif() {
    if (!window._bgModeActive || !currentTrack) return;
    try {
        if (window.flutter_inappwebview) {
            window.flutter_inappwebview.callHandler('setBgMode', true,
                currentTrack.title || '',
                currentTrack.artist || '');
        }
    } catch(e) {}
}

'''

# Sisipkan sebelum // INIT
old_init = '// INIT\ndocument.addEventListener'
if old_init in content:
    content = content.replace(old_init, bg_mode_code + '// INIT\ndocument.addEventListener', 1)
    print("OK: toggleBgMode added")
else:
    # Append di akhir
    content += bg_mode_code
    print("OK: toggleBgMode appended at end")

# Juga panggil _updateBgModeNotif() di dalam playMusic setelah updateMediaSession()
old_media = 'updateMediaSession();'
new_media = 'updateMediaSession();\n    _updateBgModeNotif();'
# Hanya replace yang pertama (di dalam playMusic)
if old_media in content:
    content = content.replace(old_media, new_media, 1)
    print("OK: _updateBgModeNotif call added in playMusic")

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
