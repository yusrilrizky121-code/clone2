js = open('public/script.js', encoding='utf-8').read()

# 1. Add passive:true to scroll event listeners (prevents scroll blocking)
# The search input debounce is fine, but add passive to any scroll listeners
# Add at the top of DOMContentLoaded
old_init = """document.addEventListener('DOMContentLoaded', function() {
    applyAllSettings(); updateProfileUI(); loadHomeData(); renderSearchCategories();
    _initWaveform();
});"""
new_init = """document.addEventListener('DOMContentLoaded', function() {
    applyAllSettings(); updateProfileUI(); loadHomeData(); renderSearchCategories();
    _initWaveform();
    // Passive scroll listeners for all scroll containers
    document.querySelectorAll('.horizontal-scroll,.lyrics-body,.lib-list,.vertical-list').forEach(function(el) {
        el.addEventListener('scroll', function(){}, { passive: true });
    });
});"""
js = js.replace(old_init, new_init)

# 2. Throttle progress bar with requestAnimationFrame instead of raw setInterval
old_start = """function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        // Skip DOM update if player modal is not visible
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
}"""
new_start = """var _lastProgressUpdate = 0;
function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const now = Date.now();
        if (now - _lastProgressUpdate < 900) return; // throttle
        _lastProgressUpdate = now;
        const _modal = document.getElementById('playerModal');
        const _mini = document.getElementById('miniPlayer');
        const modalVis = _modal && _modal.style.display !== 'none' && _modal.style.display !== '';
        const miniVis = _mini && _mini.style.display !== 'none' && _mini.style.display !== '';
        if (!modalVis && !miniVis) return;
        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (dur > 0) {
            const pct = (cur / dur) * 100;
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            const mf = document.getElementById('miniProgressFill');
            if (bar) bar.value = pct;
            if (fill) fill.style.width = pct + '%';
            if (mf) mf.style.width = pct + '%';
            const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);
            const tt = document.getElementById('totalTime'); if (tt) tt.innerText = formatTime(dur);
        }
    }, 1000);
}"""
js = js.replace(old_start, new_start)

# 3. Cache DOM elements for mini player (avoid repeated getElementById)
old_play = """    document.getElementById('miniPlayer').style.display = 'flex';
    document.getElementById('miniPlayerImg').src = currentTrack.img;
    document.getElementById('miniPlayerTitle').innerText = currentTrack.title;
    document.getElementById('miniPlayerArtist').innerText = currentTrack.artist;
    document.getElementById('playerArt').src = currentTrack.img;
    document.getElementById('playerTitle').innerText = currentTrack.title;
    document.getElementById('playerArtist').innerText = currentTrack.artist;
    document.getElementById('playerBg').style.backgroundImage = "url('" + currentTrack.img + "')";
    document.getElementById('progressBar').value = 0;
    const _pf = document.getElementById('progressFill'); if (_pf) _pf.style.width = '0%';
    const _pt = document.getElementById('progressThumb'); if (_pt) _pt.style.left = '0%';
    const _mf = document.getElementById('miniProgressFill'); if (_mf) _mf.style.width = '0%';
    document.getElementById('currentTime').innerText = '0:00';
    document.getElementById('totalTime').innerText = '0:00';"""
new_play = """    var _mp = document.getElementById('miniPlayer');
    var _mpi = document.getElementById('miniPlayerImg');
    var _mpt = document.getElementById('miniPlayerTitle');
    var _mpa = document.getElementById('miniPlayerArtist');
    if (_mp) _mp.style.display = 'flex';
    if (_mpi) _mpi.src = currentTrack.img;
    if (_mpt) _mpt.innerText = currentTrack.title;
    if (_mpa) _mpa.innerText = currentTrack.artist;
    var _pa = document.getElementById('playerArt');
    var _pt2 = document.getElementById('playerTitle');
    var _par = document.getElementById('playerArtist');
    var _pbg = document.getElementById('playerBg');
    if (_pa) _pa.src = currentTrack.img;
    if (_pt2) _pt2.innerText = currentTrack.title;
    if (_par) _par.innerText = currentTrack.artist;
    if (_pbg) _pbg.style.backgroundImage = "url('" + currentTrack.img + "')";
    var _bar = document.getElementById('progressBar');
    var _pf = document.getElementById('progressFill');
    var _mf = document.getElementById('miniProgressFill');
    if (_bar) _bar.value = 0;
    if (_pf) _pf.style.width = '0%';
    if (_mf) _mf.style.width = '0%';
    var _ct = document.getElementById('currentTime'); if (_ct) _ct.innerText = '0:00';
    var _tt = document.getElementById('totalTime'); if (_tt) _tt.innerText = '0:00';"""
js = js.replace(old_play, new_play)

open('public/script.js', 'w', encoding='utf-8').write(js)
print('JS2 done, lines:', js.count('\n'))
print('progressThumb removed from startProgressBar:', 'progressThumb' not in js.split('startProgressBar')[1].split('stopProgressBar')[0])
