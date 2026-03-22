"""Append toggleBgMode function to script.js"""

bgmode_code = """

// ============================================================
// BACKGROUND MODE — jaga musik tetap jalan saat keluar APK
// ============================================================
let _bgModeActive = false;

function toggleBgMode() {
    _bgModeActive = !_bgModeActive;
    const icon = document.getElementById('btnBgModeIcon');
    if (icon) {
        icon.style.fill = _bgModeActive ? 'var(--spotify-green, #1db954)' : 'rgba(255,255,255,0.5)';
    }
    showToast(_bgModeActive ? 'Mode latar belakang aktif' : 'Mode latar belakang nonaktif');
    try {
        if (window.flutter_inappwebview) {
            window.flutter_inappwebview.callHandler('setBgMode', _bgModeActive);
        }
    } catch(e) {}
}

function _stopBgPause() {
    if (_bgModeActive && typeof ytPlayer !== 'undefined' && ytPlayer && ytPlayer.getPlayerState) {
        const state = ytPlayer.getPlayerState();
        if (state === 2 || state === -1) {
            setTimeout(function() { try { ytPlayer.playVideo(); } catch(e) {} }, 300);
        }
    }
}
window._stopBgPause = _stopBgPause;
"""

with open("public/script.js", "r", encoding="utf-8") as f:
    content = f.read()

if "toggleBgMode" in content:
    print("toggleBgMode sudah ada, skip.")
else:
    with open("public/script.js", "a", encoding="utf-8") as f:
        f.write(bgmode_code)
    print("toggleBgMode berhasil ditambahkan.")

# Verifikasi
with open("public/script.js", "r", encoding="utf-8") as f:
    content2 = f.read()
print("toggleBgMode ada:", "toggleBgMode" in content2)
print("_stopBgPause ada:", "_stopBgPause" in content2)
