import os, re, shutil
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ============================================================
# 1. Fix script.js — replace old startProgressBar
# ============================================================
with open('public/script.js', encoding='utf-8') as f:
    js = f.read()

old_pb = '''function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const _modal = document.getElementById('playerModal');
        const _mini = document.getElementById('miniPlayer');
        if ((!_modal || _modal.style.display === 'none' || _modal.style.display === '') && (!_mini || _mini.style.display === 'none' || _mini.style.display === '')) return;
        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (dur > 0) {
            const pct = (cur / dur) * 100;
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            const thumb = document.getElementById('progressThumb');
            const mf = document.getElementById('miniProgressFill');
            if (bar) bar.value = pct;
            if (fill) fill.style.width = pct + '%';
            if (thumb) thumb.style.left = pct + '%';
            if (mf) mf.style.width = pct + '%';
            _updateWaveform(pct);
            const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);
            const tt = document.getElementById('totalTime'); if (tt) tt.innerText = formatTime(dur);
        }
    }, 1000);
}'''

new_pb = '''function startProgressBar() {
    stopProgressBar();
    // Cache DOM refs once — avoid repeated getElementById in hot loop
    var _bar = document.getElementById('progressBar');
    var _fill = document.getElementById('progressFill');
    var _mf = document.getElementById('miniProgressFill');
    var _ct = document.getElementById('currentTime');
    var _tt = document.getElementById('totalTime');
    var _modal = document.getElementById('playerModal');
    var _mini = document.getElementById('miniPlayer');
    var _lastPct = -1;
    progressInterval = setInterval(function() {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        if (_isScrolling) return;
        var modalVis = _modal && _modal.style.display === 'flex';
        var miniVis = _mini && _mini.style.display === 'flex';
        if (!modalVis && !miniVis) return;
        var cur = ytPlayer.getCurrentTime();
        var dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (dur <= 0) return;
        var pct = (cur / dur) * 100;
        if (Math.abs(pct - _lastPct) < 0.3) return;
        _lastPct = pct;
        var pctStr = pct.toFixed(1) + '%';
        if (_bar) _bar.value = pct;
        if (_fill) _fill.style.width = pctStr;
        if (_mf) _mf.style.width = pctStr;
        if (modalVis) {
            if (_ct) _ct.innerText = formatTime(cur);
            if (_tt) _tt.innerText = formatTime(dur);
        }
    }, 1000);
}'''

if old_pb in js:
    js = js.replace(old_pb, new_pb)
    print("startProgressBar replaced")
else:
    print("WARNING: old startProgressBar not found exactly, trying partial match")
    # Try to find and replace by function boundaries
    start = js.find('function startProgressBar()')
    end = js.find('\nfunction stopProgressBar()')
    if start != -1 and end != -1:
        js = js[:start] + new_pb + '\n' + js[end:]
        print("startProgressBar replaced via boundary match")
    else:
        print("ERROR: could not find startProgressBar")

# ============================================================
# 2. Fix downloadMusic — ensure APK bridge is used
# ============================================================
old_dl_start = js.find('// DOWNLOAD\nfunction downloadMusic()')
if old_dl_start != -1:
    # Find end of function
    brace_count = 0
    i = js.find('{', old_dl_start)
    while i < len(js):
        if js[i] == '{': brace_count += 1
        elif js[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                old_dl_end = i + 1
                break
        i += 1
    old_dl = js[old_dl_start:old_dl_end]
    print(f"\nCurrent downloadMusic:\n{old_dl[:300]}")
    
    new_dl = '''// DOWNLOAD
function downloadMusic() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    // APK mode: delegate to Flutter native downloader
    if (window.flutter_inappwebview) {
        showToast('Mengunduh... tunggu sebentar');
        try {
            window.flutter_inappwebview.callHandler('downloadTrack', currentTrack.videoId, currentTrack.title || 'lagu');
        } catch(e) { showToast('Download gagal, coba lagi'); }
        return;
    }
    // Web/PWA fallback
    showToast('Memulai unduhan...');
    apiFetch('/api/download?video_id=' + currentTrack.videoId + '&title=' + encodeURIComponent(currentTrack.title))
        .then(function(res) {
            if (!res.ok) throw new Error('failed');
            return res.blob();
        }).then(function(blob) {
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url; a.download = (currentTrack.title || 'music') + '.mp3';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
            showToast('Unduhan selesai!');
        }).catch(function() { showToast('Gagal mengunduh'); });
}'''
    js = js[:old_dl_start] + new_dl + js[old_dl_end:]
    print("downloadMusic replaced")
else:
    print("downloadMusic not found")

# ============================================================
# 3. Write back
# ============================================================
with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("\nscript.js written")

# ============================================================
# 4. Sync to assets/web/
# ============================================================
for fname in ['style.css', 'script.js', 'index.html']:
    src = f'public/{fname}'
    dst = f'auspoty-flutter/assets/web/{fname}'
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Synced {fname}")

print("\nAll done!")
