// PWA
let deferredPrompt;
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
}
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault(); deferredPrompt = e;
    const btn = document.getElementById('installAppBtn');
    if (btn) { btn.style.display = 'flex'; btn.addEventListener('click', async () => { deferredPrompt.prompt(); const { outcome } = await deferredPrompt.userChoice; if (outcome === 'accepted') btn.style.display = 'none'; deferredPrompt = null; }); }
});

// INDEXEDDB
let db;
const dbReq = indexedDB.open('AuspotyDB', 3);
dbReq.onupgradeneeded = (e) => {
    db = e.target.result;
    if (!db.objectStoreNames.contains('playlists')) db.createObjectStore('playlists', { keyPath: 'id' });
    if (!db.objectStoreNames.contains('liked_songs')) db.createObjectStore('liked_songs', { keyPath: 'videoId' });
    if (!db.objectStoreNames.contains('downloaded_songs')) db.createObjectStore('downloaded_songs', { keyPath: 'videoId' });
    if (!db.objectStoreNames.contains('subscribed_songs')) db.createObjectStore('subscribed_songs', { keyPath: 'videoId' });
};
dbReq.onsuccess = (e) => { db = e.target.result; renderLibraryUI(); };

// STATE
let isRepeat = false;
let songHistory = [];
let isPlaying = false;
let currentTrack = null;
let progressInterval = null;

// YOUTUBE PLAYER (fallback web/PWA)
let ytPlayer;
function onYouTubeIframeAPIReady() {
    ytPlayer = new YT.Player('youtube-player', {
        height: '0', width: '0',
        playerVars: { playsinline: 1, rel: 0 },
        events: { onReady: () => {}, onStateChange: onPlayerStateChange }
    });
}
function onPlayerStateChange(event) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (event.data == YT.PlayerState.PLAYING) {
        // Pastikan flag offline di-reset saat YT mulai play
        window._localAudioPlaying = false;
        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        _setArtPlaying(true);
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        if (!window.flutter_inappwebview) _startBgKeepAlive();
    } else if (event.data == YT.PlayerState.PAUSED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        _setArtPlaying(false);
        stopProgressBar();
    } else if (event.data == YT.PlayerState.ENDED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
        if (isRepeat && ytPlayer) { ytPlayer.seekTo(0); ytPlayer.playVideo(); }
        else { playNextSimilarSong(); }
    }
}

// API FETCH
const API_BASE = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';
async function apiFetch(path) {
    try { const r = await fetch(path); if (r.ok) return r; } catch(e) {}
    return fetch(API_BASE + path);
}

// MEDIA SESSION
function updateMediaSession() {
    if ('mediaSession' in navigator && currentTrack) {
        navigator.mediaSession.metadata = new MediaMetadata({
            title: currentTrack.title, artist: currentTrack.artist,
            artwork: [{ src: currentTrack.img, sizes: '512x512', type: 'image/png' }]
        });
        navigator.mediaSession.setActionHandler('play', togglePlay);
        navigator.mediaSession.setActionHandler('pause', togglePlay);
        navigator.mediaSession.setActionHandler('nexttrack', playNextSimilarSong);
    }
}

// AUTO QUEUE
let _autoQueue = [];
async function prefetchNextSongs(artist, currentVideoId) {
    try {
        const res = await apiFetch('/api/search?query=' + encodeURIComponent(artist + ' official audio'));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const filtered = result.data.filter(t => t.videoId !== currentVideoId);
            _autoQueue = filtered.slice(0, 3).map(t => ({
                videoId: t.videoId, title: t.title, artist: t.artist || 'Unknown',
                img: getHighResImage(t.thumbnail || t.img || '')
            }));
        }
    } catch(e) {}
}
async function playNextSimilarSong() {
    if (_autoQueue.length > 0) {
        const next = _autoQueue.shift();
        prefetchNextSongs(next.artist, next.videoId);
        playMusic(next.videoId, makeTrackData(next));
        return;
    }
    if (!currentTrack) return;
    try {
        const res = await apiFetch('/api/search?query=' + encodeURIComponent(currentTrack.artist + ' official audio'));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const related = result.data.filter(t => t.videoId !== currentTrack.videoId);
            if (related.length > 0) {
                const next = related[Math.floor(Math.random() * related.length)];
                playMusic(next.videoId, makeTrackData(next));
            }
        }
    } catch(e) {}
}
function getHighResImage(url) {
    if (!url) return 'https://via.placeholder.com/300x300?text=music';
    return url.replace(/=w\d+-h\d+/, '=w300-h300').replace(/w\d+_h\d+/, 'w300_h300');
}

// ============================================================
// PLAY MUSIC — fungsi utama
// Background audio dijaga oleh foreground service Android
// ============================================================
function playMusic(videoId, encodedData) {
    currentTrack = JSON.parse(decodeURIComponent(encodedData));
    window.currentTrack = currentTrack;
    // Stop local audio if playing
    if (window._localAudioPlaying && window.flutter_inappwebview) {
        try { window.flutter_inappwebview.callHandler('stopLocalPlayer'); } catch(e) {}
    }
    // Reset downloaded mode saat main lagu streaming — WAJIB sebelum startProgressBar
    window._localAudioPlaying = false;
    window._isDownloadedView = false;
    // Pastikan icon di daftar unduhan kembali ke "play"
    _refreshDownloadedIcons(false);

    if (!songHistory.length || songHistory[songHistory.length-1].videoId !== currentTrack.videoId) {
        songHistory.push(Object.assign({}, currentTrack));
        if (songHistory.length > 50) songHistory.shift();
    }
    try {
        const hist = JSON.parse(localStorage.getItem('auspotyHistory') || '[]');
        const filtered = hist.filter(t => t.videoId !== currentTrack.videoId);
        filtered.unshift(currentTrack);
        localStorage.setItem('auspotyHistory', JSON.stringify(filtered.slice(0, 50)));
    } catch(e) {}

    checkIfLiked(currentTrack.videoId);
    checkIfSubscribed(currentTrack.videoId);
    updateMediaSession();

    var _mp = document.getElementById('miniPlayer');
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
    var _tt = document.getElementById('totalTime'); if (_tt) _tt.innerText = '0:00';

    // Putar audio via ytPlayer (baik di web maupun APK)
    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
    }
    _startBgKeepAlive();
    // Kirim info ke native service untuk notifikasi saja (tidak intercept audio)
    if (window.flutter_inappwebview) {
        try {
            window.flutter_inappwebview.callHandler('onMusicPlaying',
                currentTrack.title||'Auspoty', currentTrack.artist||'', '', currentTrack.img||'');
        } catch(e) {}
    }

    setTimeout(() => {
        if (currentTrack && _autoQueue.length < 2) prefetchNextSongs(currentTrack.artist, currentTrack.videoId);
    }, 2000);
}

// TOGGLE PLAY
function togglePlay() {
    // Jika ada lagu offline aktif (downloaded), selalu delegate ke native
    if (window._localAudioPlaying) {
        if (window.flutter_inappwebview) {
            try { window.flutter_inappwebview.callHandler('toggleLocalPlay'); } catch(e) {}
        }
        return;
    }
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        isPlaying = false;
        updatePlayPauseBtn(false);
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        isPlaying = true;
        updatePlayPauseBtn(true);
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
}

function updatePlayPauseBtn(playing) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (mainBtn) mainBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
    if (miniBtn) miniBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
    isPlaying = playing;
    _refreshDownloadedIcons(playing);
}

function expandPlayer() { document.getElementById('playerModal').style.display = 'flex'; }
function minimizePlayer() { document.getElementById('playerModal').style.display = 'none'; }

function startProgressBar() {
    stopProgressBar();
    var _bar  = document.getElementById('progressBar');
    var _fill = document.getElementById('progressFill');
    var _mf   = document.getElementById('miniProgressFill');
    var _ct   = document.getElementById('currentTime');
    var _tt   = document.getElementById('totalTime');
    var _lastPct = -1;

    var _intervalId = setInterval(function() {
        // Mode offline: progress diupdate dari Dart timer — skip di sini
        if (window._localAudioPlaying) return;
        if (!ytPlayer) return;
        var cur = 0, dur = 0;
        try {
            if (typeof ytPlayer.getCurrentTime !== 'function') return;
            cur = ytPlayer.getCurrentTime() || 0;
            dur = (typeof ytPlayer.getDuration === 'function') ? (ytPlayer.getDuration() || 0) : 0;
        } catch(e) { return; }
        if (dur <= 0) return;
        var pct = Math.min((cur / dur) * 100, 100);
        if (Math.abs(pct - _lastPct) < 0.05) return;
        _lastPct = pct;
        var pctStr = pct.toFixed(1) + '%';
        if (_bar)  _bar.value = pct;
        if (_fill) _fill.style.width = pctStr;
        if (_mf)   _mf.style.width   = pctStr;
        if (_ct) _ct.innerText = formatTime(cur);
        if (_tt) _tt.innerText = formatTime(dur);
    }, 500);

    progressInterval = { cancel: function() { clearInterval(_intervalId); } };
}
function stopProgressBar() {
    if (progressInterval && progressInterval.cancel) {
        progressInterval.cancel();
    } else if (progressInterval && progressInterval._raf) {
        cancelAnimationFrame(progressInterval._raf);
    } else {
        clearInterval(progressInterval);
    }
    progressInterval = null;
}
function seekTo(value) {
    // Saat lagu offline aktif, delegate seek ke Dart
    if (window._localAudioPlaying) {
        if (window.flutter_inappwebview) {
            try { window.flutter_inappwebview.callHandler('seekLocalTo', value); } catch(e) {}
        }
        return;
    }
    var au = document.getElementById('bgAudio');
    if (au && !isNaN(au.duration) && au.duration > 0) {
        au.currentTime = value / 100 * au.duration;
        return;
    }
    if (!ytPlayer) return;
    const dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
    if (dur > 0) ytPlayer.seekTo(value / 100 * dur, true);
}
function formatTime(sec) {
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
}

// REPEAT / PREV / NEXT
function toggleRepeat() {
    isRepeat = !isRepeat;
    const btn = document.getElementById('btnRepeat');
    if (btn) btn.style.color = isRepeat ? 'var(--accent)' : 'rgba(255,255,255,0.7)';
    showToast(isRepeat ? 'Ulangi aktif' : 'Ulangi nonaktif');
}
function playPrevSong() {
    if (window._isDownloadedView) { playPrevDownloadedSong(); return; }
    if (songHistory.length < 2) { showToast('Tidak ada lagu sebelumnya'); return; }
    songHistory.pop();
    const prev = songHistory[songHistory.length - 1];
    if (prev) playMusic(prev.videoId, makeTrackData(prev));
}
function playNextSong() {
    if (window._isDownloadedView) { playNextDownloadedSong(); return; }
    playNextSimilarSong();
}

// LYRICS
let lyricsLines = [], lyricsScrollInterval = null, currentHighlightIdx = -1, lyricsType = 'plain';
async function openLyricsModal() {
    if (!currentTrack) return;
    const modal = document.getElementById('lyricsModal');
    const lbody = document.getElementById('lyricsBody');
    document.getElementById('lyricsTrackImg').src = currentTrack.img;
    document.getElementById('lyricsTrackTitle').innerText = currentTrack.title;
    document.getElementById('lyricsTrackArtist').innerText = currentTrack.artist;
    document.getElementById('lyricsBg').style.backgroundImage = "url('" + currentTrack.img + "')";
    modal.style.display = 'flex';
    lbody.scrollTop = 0;
    lbody.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Menarik lirik...</div>';
    stopLyricsScroll(); lyricsLines = []; currentHighlightIdx = -1;
    document.getElementById('playerModal').style.display = 'none';
    try {
        const res = await apiFetch('/api/lyrics?video_id=' + currentTrack.videoId);
        const result = await res.json();
        if (result.status === 'success' && result.data && result.data.lines && result.data.lines.length > 0) {
            lyricsLines = result.data.lines; lyricsType = result.data.type || 'plain';
            let html = '<div style="height:40px"></div>';
            lyricsLines.forEach((line, i) => { html += '<div class="lyric-line" id="lyric-line-' + i + '">' + (line.text || '') + '</div>'; });
            html += '<div style="height:45vh"></div>';
            lbody.innerHTML = html; lbody.scrollTop = 0; startLyricsScroll();
        } else {
            lbody.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Lirik belum tersedia.</div>';
        }
    } catch(e) {
        lbody.innerHTML = '<div style="color:#ff5252;font-size:16px;text-align:center;margin-top:40px;">Gagal memuat lirik.</div>';
    }
}
function startLyricsScroll() {
    stopLyricsScroll();
    var _lb = document.getElementById('lyricsBody');
    var _lastIdx = -1;
    var _lastTick = 0;
    var _rafId = null;
    var _active = true;

    function _tick(now) {
        if (!_active) return;
        _rafId = requestAnimationFrame(_tick);
        // throttle to ~2fps — enough for lyrics sync
        if (now - _lastTick < 480) return;
        _lastTick = now;
        if (_isScrolling) return;
        var cur = 0, dur = 0;
        var _au = window._localAudioPlaying ? document.getElementById('bgAudio') : null;
        if (_au && !isNaN(_au.duration) && _au.duration > 0) {
            cur = _au.currentTime; dur = _au.duration;
        } else if (ytPlayer && ytPlayer.getCurrentTime) {
            cur = ytPlayer.getCurrentTime();
            dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        }
        if (!dur || lyricsLines.length === 0) return;
        var idx = 0;
        if (lyricsType === 'synced') {
            for (var i = 0; i < lyricsLines.length; i++) {
                if (lyricsLines[i].time !== null && lyricsLines[i].time <= cur) idx = i;
            }
        } else {
            idx = Math.min(Math.floor((cur / dur) * lyricsLines.length), lyricsLines.length - 1);
        }
        if (idx === _lastIdx) return;
        if (_lastIdx >= 0) {
            var old = document.getElementById('lyric-line-' + _lastIdx);
            if (old) old.className = 'lyric-line lyric-past';
        }
        var active = document.getElementById('lyric-line-' + idx);
        if (active) {
            active.className = 'lyric-line lyric-active';
            if (idx > _lastIdx + 1) {
                for (var j = _lastIdx + 1; j < idx; j++) {
                    var el = document.getElementById('lyric-line-' + j);
                    if (el) el.className = 'lyric-line lyric-past';
                }
            }
            if (_lb) {
                var target = active.offsetTop - (_lb.clientHeight / 2) + (active.offsetHeight / 2);
                _lb.scrollTop = target;
            }
        }
        _lastIdx = idx;
        currentHighlightIdx = idx;
    }
    _rafId = requestAnimationFrame(_tick);
    lyricsScrollInterval = {
        cancel: function() { _active = false; if (_rafId) cancelAnimationFrame(_rafId); _rafId = null; }
    };
}
function stopLyricsScroll() {
    if (lyricsScrollInterval && lyricsScrollInterval.cancel) {
        lyricsScrollInterval.cancel();
    } else if (lyricsScrollInterval && lyricsScrollInterval._rafId) {
        cancelAnimationFrame(lyricsScrollInterval._rafId);
    } else {
        clearInterval(lyricsScrollInterval);
    }
    lyricsScrollInterval = null;
}
function closeLyricsToPlayer() { stopLyricsScroll(); document.getElementById('lyricsModal').style.display = 'none'; document.getElementById('playerModal').style.display = 'flex'; }
function closeLyrics() { stopLyricsScroll(); document.getElementById('lyricsModal').style.display = 'none'; }

// TOAST
function showToast(msg) {
    const t = document.getElementById('customToast'); if (!t) return;
    t.innerText = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// VIEW SWITCHING
function switchView(name) {
    document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
    const target = document.getElementById('view-' + name);
    if (target) target.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navMap = { home: 0, search: 1, library: 2, settings: 3 };
    const navItems = document.querySelectorAll('.nav-item');
    if (navMap[name] !== undefined && navItems[navMap[name]]) navItems[navMap[name]].classList.add('active');
    window.scrollTo(0, 0);
}

// FILTER HOME (Semua / Musik / Podcast pills)
var _homeFilter = 'all';
function filterHome(type, el) {
    _homeFilter = type;
    document.querySelectorAll('.home-header .pill').forEach(p => p.classList.remove('active'));
    if (el) el.classList.add('active');
    var recentSec = document.querySelector('#view-home .section-container:first-of-type');
    if (type === 'podcast') {
        // Load podcast content
        var recentEl = document.getElementById('recentList');
        if (recentEl) {
            recentEl.innerHTML = '<div style="color:var(--text-sub);padding:8px;font-size:13px;">Memuat podcast...</div>';
            apiFetch('/api/search?query=podcast+indonesia+terpopuler').then(r => r.json()).then(result => {
                if (result.status === 'success' && result.data.length > 0)
                    recentEl.innerHTML = result.data.slice(0, 8).map(renderVItem).join('');
                else recentEl.innerHTML = '<div style="color:var(--text-sub);padding:8px;">Tidak ada podcast.</div>';
            }).catch(() => { recentEl.innerHTML = '<div style="color:var(--text-sub);padding:8px;">Gagal memuat.</div>'; });
        }
    } else {
        // Reload normal home
        loadHomeData();
    }
}

// RENDER HELPERS
function makeTrackData(t) {
    const img = getHighResImage(t.thumbnail || t.img || '');
    return encodeURIComponent(JSON.stringify({ videoId: t.videoId, title: t.title, artist: t.artist || 'Unknown', img }));
}
window._trackCache = {};
function _cacheTrack(t) {
    if (!t || !t.videoId) return;
    window._trackCache[t.videoId] = { videoId: t.videoId, title: t.title || '', artist: t.artist || 'Unknown', img: getHighResImage(t.thumbnail || t.img || '') };
}
function playMusicById(videoId) {
    // Jika sedang di view unduhan, cari lagu tersebut di koleksi unduhan
    if (window._isDownloadedView && window._playlistTracks) {
        const t = window._playlistTracks.find(track => track.videoId === videoId);
        if (t) {
            playDownloadedSong(t.videoId, t.title || '', t.artist || '', getHighResImage(t.thumbnail || t.img || ''));
            return;
        }
    }
    const t = window._trackCache[videoId];
    if (t) playMusic(t.videoId, makeTrackData(t));
}
// Khusus untuk lagu yang sudah diunduh — langsung panggil playLocalFile
// tanpa butuh _trackCache atau koneksi internet
function playDownloadedSong(videoId, title, artist, img) {
    // Stop local player if already playing one, to be sure
    if (window._localAudioPlaying && window.flutter_inappwebview) {
        try { window.flutter_inappwebview.callHandler('stopLocalPlayer'); } catch(e) {}
    }
    // Stop ytPlayer dulu agar tidak bentrok
    try { if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo(); } catch(e) {}
    window._localAudioPlaying = true;
    isPlaying = true;
    // Pastikan daftar unduhan ikut update icon saat mode offline dipakai
    // meskipun user memulai playback dari view selain "Lagu Diunduh".
    if (window._playlistTracks && Array.isArray(window._playlistTracks)) {
        window._isDownloadedView = true;
    }
    currentTrack = { videoId: videoId, title: title, artist: artist, img: img };
    window.currentTrack = currentTrack;
    // Set index di _playlistTracks supaya next/prev bisa jalan
    if (window._playlistTracks && window._isDownloadedView) {
        window._downloadedQueueIndex = window._playlistTracks.findIndex(t => t.videoId === videoId);
    }
    updatePlayPauseBtn(true);
    var _mp = document.getElementById('miniPlayer');
    var _mpi = document.getElementById('miniPlayerImg');
    var _mpt = document.getElementById('miniPlayerTitle');
    var _mpa = document.getElementById('miniPlayerArtist');
    if (_mp) _mp.style.display = 'flex';
    if (_mpi) _mpi.src = img;
    if (_mpt) _mpt.innerText = title;
    if (_mpa) _mpa.innerText = artist;
    var _pa = document.getElementById('playerArt');
    var _pt2 = document.getElementById('playerTitle');
    var _par = document.getElementById('playerArtist');
    var _pbg = document.getElementById('playerBg');
    if (_pa) _pa.src = img;
    if (_pt2) _pt2.innerText = title;
    if (_par) _par.innerText = artist;
    if (_pbg) _pbg.style.backgroundImage = "url('" + img + "')";
    var _bar = document.getElementById('progressBar');
    var _pf = document.getElementById('progressFill');
    var _mf = document.getElementById('miniProgressFill');
    if (_bar) _bar.value = 0;
    if (_pf) _pf.style.width = '0%';
    if (_mf) _mf.style.width = '0%';
    var _ct = document.getElementById('currentTime'); if (_ct) _ct.innerText = '0:00';
    var _tt = document.getElementById('totalTime'); if (_tt) _tt.innerText = '0:00';
    checkIfLiked(videoId);
    checkIfSubscribed(videoId);
    updateMediaSession();
    // Update media session next/prev untuk downloaded queue
    if ('mediaSession' in navigator) {
        navigator.mediaSession.setActionHandler('nexttrack', playNextDownloadedSong);
        navigator.mediaSession.setActionHandler('previoustrack', playPrevDownloadedSong);
    }
    // JANGAN panggil startProgressBar() di sini — progress diupdate dari Dart timer
    // startProgressBar() hanya untuk ytPlayer (streaming)
    if (window.flutter_inappwebview) {
        try {
            window.flutter_inappwebview.callHandler('playLocalFile', title, artist, img, videoId);
        } catch(e) { showToast('Gagal memutar: ' + e); }
    } else {
        showToast('Fitur offline hanya tersedia di aplikasi APK');
    }
}

function playNextDownloadedSong() {
    if (!window._isDownloadedView || !window._playlistTracks) { playNextSimilarSong(); return; }
    const tracks = window._playlistTracks;
    let idx = (window._downloadedQueueIndex !== undefined) ? window._downloadedQueueIndex : -1;
    idx = (idx + 1) % tracks.length;
    window._downloadedQueueIndex = idx;
    const t = tracks[idx];
    if (t) playDownloadedSong(t.videoId, t.title || '', t.artist || '', getHighResImage(t.thumbnail || t.img || ''));
}

function playPrevDownloadedSong() {
    if (!window._isDownloadedView || !window._playlistTracks) { playPrevSong(); return; }
    const tracks = window._playlistTracks;
    let idx = (window._downloadedQueueIndex !== undefined) ? window._downloadedQueueIndex : 0;
    idx = (idx - 1 + tracks.length) % tracks.length;
    window._downloadedQueueIndex = idx;
    const t = tracks[idx];
    if (t) playDownloadedSong(t.videoId, t.title || '', t.artist || '', getHighResImage(t.thumbnail || t.img || ''));
}

function renderVItem(t) {
    _cacheTrack(t);
    return '<div class="v-item" onclick="playMusicById(\'' + t.videoId + '\')">' +
        '<img loading="lazy" class="v-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '">' +
        '<div class="v-info"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div></div>';
}
function renderDownloadedVItem(t) {
    _cacheTrack(t);
    var vid = t.videoId;
    var ttl = (t.title || '').replace(/'/g, "\\'");
    var art = (t.artist || '').replace(/'/g, "\\'");
    var img = getHighResImage(t.thumbnail || t.img || '');
    var imgEsc = img.replace(/'/g, "\\'");
    var isActive = window.currentTrack && window.currentTrack.videoId === vid;
    var isNowPlaying = isActive && window._localAudioPlaying && isPlaying;
    var iconPath = isNowPlaying
        ? 'M6 19h4V5H6v14zm8-14v14h4V5h-4z'
        : 'M8 5v14l11-7z';
    var iconColor = isActive ? 'var(--accent)' : 'rgba(255,255,255,0.5)';
    return '<div class="v-item" id="dl-item-' + vid + '">' +
        '<img loading="lazy" class="v-img" src="' + img + '" onclick="playDownloadedSong(\'' + vid + '\',\'' + ttl + '\',\'' + art + '\',\'' + imgEsc + '\')">' +
        '<div class="v-info" onclick="playDownloadedSong(\'' + vid + '\',\'' + ttl + '\',\'' + art + '\',\'' + imgEsc + '\')"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div>' +
        '<div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">' +
        '<svg id="dl-playbtn-' + vid + '" onclick="event.stopPropagation();_dlToggle(\'' + vid + '\',\'' + ttl + '\',\'' + art + '\',\'' + imgEsc + '\')" viewBox="0 0 24 24" style="fill:' + iconColor + ';width:24px;height:24px;cursor:pointer;"><path d="' + iconPath + '"/></svg>' +
        '<svg onclick="event.stopPropagation();deleteDownloadedSong(\'' + vid + '\')" viewBox="0 0 24 24" style="fill:rgba(255,255,255,0.35);width:20px;height:20px;cursor:pointer;"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>' +
        '</div></div>';
}

// Toggle play/pause untuk item di daftar unduhan
function _dlToggle(vid, ttl, art, img) {
    if (window.currentTrack && window.currentTrack.videoId === vid && window._localAudioPlaying) {
        // Lagu ini sedang aktif — toggle play/pause
        togglePlay();
    } else {
        // Lagu berbeda atau belum diputar — play lagu ini
        playDownloadedSong(vid, ttl, art, img);
    }
}

// Update semua icon di daftar unduhan setelah state berubah
function _refreshDownloadedIcons(nowPlaying) {
    if (!window._playlistTracks) return;
    // Gunakan parameter nowPlaying jika ada, fallback ke global isPlaying
    var playing = (nowPlaying !== undefined) ? nowPlaying : isPlaying;
    var playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    window._playlistTracks.forEach(function(t) {
        var el = document.getElementById('dl-playbtn-' + t.videoId);
        if (!el) return;
        var isActive = window.currentTrack && window.currentTrack.videoId === t.videoId;
        // isNowPlaying: lagu ini aktif DAN sedang playing (cek isPlaying, bukan _localAudioPlaying)
        var isNowPlaying = isActive && playing;
        el.style.fill = isActive ? 'var(--accent)' : 'rgba(255,255,255,0.5)';
        var pathEl = el.querySelector('path');
        if (pathEl) pathEl.setAttribute('d', isNowPlaying ? pausePath : playPath);
    });
}
function renderHCard(t) {
    _cacheTrack(t);
    return '<div class="h-card" onclick="playMusicById(\'' + t.videoId + '\')">' +
        '<img loading="lazy" class="h-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '">' +
        '<div class="h-title">' + (t.title || '') + '</div></div>';
}
function renderArtistCard(name) {
    return '<div class="artist-card" onclick="openArtist(\'' + encodeURIComponent(name) + '\')">' +
        '<div class="artist-avatar">' + name.charAt(0) + '</div><div class="artist-name">' + name + '</div></div>';
}

// HOME DATA
const HOME_QUERIES_BY_LANG = {
    Indonesia: [
        { id: 'rowAnyar',   query: 'lagu indonesia terbaru 2025' },
        { id: 'rowGembira', query: 'lagu semangat gembira indonesia' },
        { id: 'rowCharts',  query: 'top hits indonesia 2025' },
        { id: 'rowGalau',   query: 'lagu galau sedih indonesia' },
        { id: 'rowTiktok',  query: 'viral tiktok indonesia 2025' },
        { id: 'rowHits',    query: 'lagu trending indonesia hari ini' },
    ],
    English: [
        { id: 'rowAnyar',   query: 'new english songs 2025' },
        { id: 'rowGembira', query: 'happy upbeat english songs' },
        { id: 'rowCharts',  query: 'top hits billboard 2025' },
        { id: 'rowGalau',   query: 'sad english songs' },
        { id: 'rowTiktok',  query: 'viral tiktok songs 2025' },
        { id: 'rowHits',    query: 'trending songs today' },
    ],
    Japanese: [
        { id: 'rowAnyar',   query: 'japanese new songs 2025' },
        { id: 'rowGembira', query: 'japanese happy songs' },
        { id: 'rowCharts',  query: 'japan top hits 2025' },
        { id: 'rowGalau',   query: 'japanese sad songs' },
        { id: 'rowTiktok',  query: 'japan viral tiktok 2025' },
        { id: 'rowHits',    query: 'japanese trending songs' },
    ],
    Korean: [
        { id: 'rowAnyar',   query: 'kpop new songs 2025' },
        { id: 'rowGembira', query: 'kpop happy songs' },
        { id: 'rowCharts',  query: 'kpop top hits 2025' },
        { id: 'rowGalau',   query: 'kpop sad songs' },
        { id: 'rowTiktok',  query: 'kpop viral tiktok 2025' },
        { id: 'rowHits',    query: 'kpop trending today' },
    ],
};
const HOME_QUERIES_BY_REGION = {
    Indonesia: null,
    Global: [
        { id: 'rowAnyar', query: 'top global songs 2025' }, { id: 'rowGembira', query: 'happy pop songs 2025' },
        { id: 'rowCharts', query: 'billboard hot 100 2025' }, { id: 'rowGalau', query: 'sad songs 2025' },
        { id: 'rowTiktok', query: 'viral tiktok global 2025' }, { id: 'rowHits', query: 'trending songs worldwide 2025' },
    ],
    'Amerika Serikat': [
        { id: 'rowAnyar', query: 'new american songs 2025' }, { id: 'rowGembira', query: 'upbeat american pop 2025' },
        { id: 'rowCharts', query: 'us top charts 2025' }, { id: 'rowGalau', query: 'sad american songs 2025' },
        { id: 'rowTiktok', query: 'viral tiktok usa 2025' }, { id: 'rowHits', query: 'us trending songs today' },
    ],
    Jepang: [
        { id: 'rowAnyar', query: 'japanese new songs 2025' }, { id: 'rowGembira', query: 'japanese happy songs 2025' },
        { id: 'rowCharts', query: 'japan oricon chart 2025' }, { id: 'rowGalau', query: 'japanese sad songs 2025' },
        { id: 'rowTiktok', query: 'japan viral tiktok 2025' }, { id: 'rowHits', query: 'japanese trending today' },
    ],
    Korea: [
        { id: 'rowAnyar', query: 'kpop new songs 2025' }, { id: 'rowGembira', query: 'kpop happy songs 2025' },
        { id: 'rowCharts', query: 'kpop melon chart 2025' }, { id: 'rowGalau', query: 'kpop sad songs 2025' },
        { id: 'rowTiktok', query: 'kpop viral tiktok 2025' }, { id: 'rowHits', query: 'kpop trending today' },
    ],
};
const SECTION_TITLES_BY_LANG = {
    Indonesia: ['Sering kamu dengarkan','Rilis Anyar','Gembira & Semangat','Tangga Lagu Populer','Galau Terpopuler','Viral TikTok','Artis Terpopuler','Hit Hari Ini'],
    English:   ['Recently Played','New Releases','Happy & Energetic','Top Charts','Sad Songs','Viral TikTok','Popular Artists','Hits Today'],
    Japanese:  ['\u6700\u8fd1\u518d\u751f','\u65b0\u7740\u30ea\u30ea\u30fc\u30b9','\u5143\u6c17\u306a\u66f2','\u4eba\u6c17\u30c1\u30e3\u30fc\u30c8','\u60b2\u3057\u3044\u66f2','\u30d0\u30a4\u30e9\u30ebTikTok','\u4eba\u6c17\u30a2\u30fc\u30c6\u30a3\u30b9\u30c8','\u4eca\u65e5\u306e\u30d2\u30c3\u30c8'],
    Korean:    ['\uc2ec\uadfc \uc7ac\uc0dd','\uc2e0\uaddc \ubc1c\ub9e4','\uc2e0\ub098\ub294 \ub178\ub798','\uc778\uae30 \ucc28\ud2b8','\uc2ac\ud508 \ub178\ub798','\ubc14\uc774\ub7f4 \ud2f1\ud1a1','\uc778\uae30 \uc544\ud2f0\uc2a4\ud2b8','\uc624\ub298\uc758 \ud788\ud2b8'],
};
const ARTISTS = ['Dewa 19','Sheila On 7','Raisa','Tulus','Rizky Febian','Tiara Andini','Mahalini','Juicy Luicy'];

function getHomeQueries() {
    const s = getSettings();
    const region = s.region || 'Indonesia';
    const lang = s.language || 'Indonesia';
    if (HOME_QUERIES_BY_REGION[region]) return HOME_QUERIES_BY_REGION[region];
    return HOME_QUERIES_BY_LANG[lang] || HOME_QUERIES_BY_LANG.Indonesia;
}
function applyLanguageTitles() {
    const lang = getSettings().language || 'Indonesia';
    const titles = SECTION_TITLES_BY_LANG[lang] || SECTION_TITLES_BY_LANG.Indonesia;
    document.querySelectorAll('.section-title').forEach((el, i) => { if (titles[i]) el.innerText = titles[i]; });
}
async function loadHomeData() {
    const recentEl = document.getElementById('recentList');
    const recentSec = recentEl ? recentEl.closest('.section-container') : null;
    if (recentEl) {
        // Show from localStorage history — no API call needed
        const history = JSON.parse(localStorage.getItem('auspotyHistory') || '[]');
        if (history.length > 0) {
            recentEl.innerHTML = history.slice(0, 5).map(renderVItem).join('');
            if (recentSec) recentSec.style.display = '';
        } else {
            if (recentSec) recentSec.style.display = 'none';
        }
    }
    const artistEl = document.getElementById('rowArtists');
    if (artistEl) artistEl.innerHTML = ARTISTS.map(renderArtistCard).join('');
    applyLanguageTitles();
    // Lazy load: 2 rows at a time to avoid hammering API and blocking main thread
    const rows = getHomeQueries();
    // Hide rows not in active query list
    const allRowIds = ['rowAnyar','rowGembira','rowCharts','rowGalau','rowTiktok','rowHits'];
    const activeIds = rows.map(r => r.id);
    allRowIds.forEach(id => {
        if (!activeIds.includes(id)) {
            const el = document.getElementById(id);
            const sec = el ? el.closest('.section-container') : null;
            if (sec) sec.style.display = 'none';
        }
    });
    async function loadRow(row) {
        const el = document.getElementById(row.id); if (!el) return;
        const sec = el.closest('.section-container');
        el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Memuat...</div>';
        try {
            const res = await apiFetch('/api/search?query=' + encodeURIComponent(row.query));
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) {
                el.innerHTML = result.data.slice(0, 5).map(renderHCard).join('');
                if (sec) sec.style.display = '';
            } else {
                el.innerHTML = '';
                if (sec) sec.style.display = 'none';
            }
        } catch(e) {
            el.innerHTML = '';
            if (sec) sec.style.display = 'none';
        }
    }
    // Load first 2 rows immediately, rest after 800ms delay
    for (let i = 0; i < rows.length; i++) {
        if (i < 2) { loadRow(rows[i]); }
        else { setTimeout(() => loadRow(rows[i]), 1200 + (i - 2) * 600); }
    }
}

// SEARCH
const CATEGORIES = [
    { title: 'Pop Indonesia', color: '#8d67ab', query: 'pop indonesia' },
    { title: 'Rock',          color: '#c84b31', query: 'rock indonesia' },
    { title: 'Galau',         color: '#477d95', query: 'lagu galau' },
    { title: 'Viral TikTok',  color: '#e8115b', query: 'viral tiktok' },
    { title: 'Dangdut',       color: '#739c18', query: 'dangdut terpopuler' },
    { title: 'Hip-Hop',       color: '#1e3264', query: 'hip hop indonesia' },
    { title: 'Religi',        color: '#2d6a4f', query: 'lagu religi islami' },
    { title: 'Nostalgia',     color: '#e1118c', query: 'lagu nostalgia 90an' },
];
function renderSearchCategories() {
    const grid = document.getElementById('categoryGrid'); if (!grid) return;
    grid.innerHTML = CATEGORIES.map(c =>
        '<div class="category-card" style="background:' + c.color + ';" onclick="searchByCategory(\'' + encodeURIComponent(c.query) + '\')">' +
        '<div class="category-title">' + c.title + '</div></div>'
    ).join('');
}
function searchByCategory(encodedQuery) {
    const q = decodeURIComponent(encodedQuery);
    document.getElementById('searchInput').value = q;
    doSearch(q);
}

// ============================================================
// SCROLL PERFORMANCE — pause JS work during scroll
// ============================================================
var _isScrolling = false;
var _scrollTimer = null;
function _onScrollStart() {
    _isScrolling = true;
    clearTimeout(_scrollTimer);
    _scrollTimer = setTimeout(function() { _isScrolling = false; }, 250);
}
document.addEventListener('scroll', _onScrollStart, { passive: true });
document.addEventListener('touchmove', _onScrollStart, { passive: true });

document.addEventListener('DOMContentLoaded', function() {
    const inp = document.getElementById('searchInput');
    if (inp) {
        let searchTimer;
        inp.addEventListener('input', function() {
            const q = this.value.trim();
            if (!q) { 
                document.getElementById('searchCategoriesUI').style.display = 'block'; 
                document.getElementById('searchResultsUI').style.display = 'none'; 
                document.getElementById('userSearchResultsUI').style.display = 'none';
                return; 
            }
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                if (_searchTab === 'music') doSearch(q);
                else doUserSearch(q);
            }, 500);
        });
    }
});

let _searchTab = 'music';
function switchSearchTab(tab) {
    _searchTab = tab;
    document.getElementById('searchTabMusic').classList.toggle('active', tab === 'music');
    document.getElementById('searchTabUsers').classList.toggle('active', tab === 'users');
    const q = document.getElementById('searchInput').value.trim();
    if (q) {
        if (tab === 'music') doSearch(q);
        else doUserSearch(q);
    }
}

// =========================
// USER CACHE (for performance)
// =========================
let _usersCache = null;
let _usersCacheLoaded = false;
async function _ensureUsersCache() {
    if (_usersCacheLoaded && Array.isArray(_usersCache)) return _usersCache;
    try {
        const db_fs = window._firestoreDB;
        if (!db_fs) return [];
        const snap = await window._fsGetDocs(window._fsCollection(db_fs, 'users'));
        _usersCache = snap.docs.map(d => d.data()).filter(u => !!u && !!u.email);
        _usersCacheLoaded = true;
    } catch (e) {
        _usersCache = [];
        _usersCacheLoaded = false;
    }
    return _usersCache || [];
}

async function doUserSearch(q) {
    document.getElementById('searchCategoriesUI').style.display = 'none';
    document.getElementById('searchResultsUI').style.display = 'none';
    document.getElementById('userSearchResultsUI').style.display = 'block';
    const el = document.getElementById('userSearchResults');
    el.innerHTML = '<div style="color:var(--text-sub);padding:16px;text-align:center;">Mencari pengguna...</div>';
    try {
        const users = await _ensureUsersCache();
        // Support @username search — strip @ prefix
        const rawQ = (q || '').trim();
        const isTagSearch = rawQ.startsWith('@');
        const ql = isTagSearch ? rawQ.slice(1).toLowerCase() : rawQ.toLowerCase();
        const usersFiltered = users.filter(u => {
            if (isTagSearch) {
                return (u.username || '').toLowerCase().includes(ql);
            }
            return (u.name || '').toLowerCase().includes(ql) ||
                   (u.email || '').toLowerCase().includes(ql) ||
                   (u.username || '').toLowerCase().includes(ql);
        });
        
        // Limit to reduce UI jank on large datasets
        const usersTop = usersFiltered.slice(0, 40);
        if (usersTop.length > 0) {
            el.innerHTML = usersTop.map(u => 
                '<div class="v-item" onclick="viewUserProfile(\'' + u.email + '\')">' +
                '<div style="width:48px;height:48px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:white;overflow:hidden;flex-shrink:0;">' + 
                (u.picture ? '<img src="' + u.picture + '" style="width:100%;height:100%;object-fit:cover;">' : (u.name||'?').charAt(0).toUpperCase()) + '</div>' +
                '<div class="v-info"><div class="v-title">' + (u.name||'') + (u.username ? ' <span style="color:var(--accent);font-size:12px;">@' + u.username + '</span>' : '') + '</div><div class="v-sub">' + u.email + '</div></div></div>'
            ).join('');
        } else {
            el.innerHTML = '<div style="color:var(--text-sub);padding:16px;text-align:center;">Tidak ada pengguna ditemukan untuk "' + q + '"</div>';
        }
    } catch(e) { el.innerHTML = '<div style="color:#ff5252;padding:16px;text-align:center;">Gagal mencari.</div>'; }
}

async function viewUserProfile(email) {
    if (!email) return;
    // Tutup modal pencarian jika terbuka
    const searchModal = document.getElementById('searchUsersModal');
    if (searchModal) searchModal.style.display = 'none';
    
    switchView('user-profile');
    
    const nameEl = document.getElementById('upvName');
    const emailEl = document.getElementById('upvEmail');
    const avatarEl = document.getElementById('upvAvatar');
    const followersEl = document.getElementById('upvFollowers');
    const followingEl = document.getElementById('upvFollowing');
    const actEl = document.getElementById('upvActivity');
    const btnFollow = document.getElementById('btnFollowUser');
    const btnMsg = document.getElementById('btnMessageUser');
    
    if (nameEl) nameEl.innerText = 'Memuat...';
    if (emailEl) emailEl.innerText = email;
    if (avatarEl) { avatarEl.innerHTML = ''; avatarEl.innerText = email.charAt(0).toUpperCase(); }
    if (followersEl) followersEl.innerText = '0';
    if (followingEl) followingEl.innerText = '0';
    if (actEl) actEl.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Memuat...</div>';
    if (btnFollow) btnFollow.style.display = 'none';
    if (btnMsg) btnMsg.style.display = 'none';
    
    // Tunggu Firestore siap max 3 detik
    for (let i = 0; i < 10 && !window._firestoreDB; i++) {
        await new Promise(r => setTimeout(r, 300));
    }
    
    const db_fs = window._firestoreDB;
    if (!db_fs) {
        if (nameEl) nameEl.innerText = email.split('@')[0];
        if (actEl) actEl.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Belum ada aktivitas.</div>';
        window._viewingUser = { email, name: email.split('@')[0] };
        return;
    }
    
    try {
        // Coba getDoc langsung (email = doc ID) — lebih cepat, tidak butuh index
        let u = null;
        try {
            const docSnap = await window._fsGetDoc(window._fsDoc(db_fs, 'users', email));
            if (docSnap.exists()) u = docSnap.data();
        } catch(e1) {}
        
        // Fallback: query by email field
        if (!u) {
            try {
                const snap = await window._fsGetDocs(
                    window._fsQuery(window._fsCollection(db_fs, 'users'), window._fsWhere('email', '==', email))
                );
                if (!snap.empty) u = snap.docs[0].data();
            } catch(e2) {}
        }
        
        if (!u) u = { email, name: email.split('@')[0], picture: '', followers: [], following: [], username: '' };
        
        const displayName = u.name || email.split('@')[0];
        if (nameEl) nameEl.innerText = displayName;
        if (emailEl) emailEl.innerText = u.username ? '@' + u.username : email;
        
        if (avatarEl) {
            if (u.picture) avatarEl.innerHTML = '<img src="' + u.picture + '" style="width:100%;height:100%;object-fit:cover;">';
            else { avatarEl.innerHTML = ''; avatarEl.innerText = displayName.charAt(0).toUpperCase(); }
        }
        
        if (followersEl) followersEl.innerText = (u.followers || []).length;
        if (followingEl) followingEl.innerText = (u.following || []).length;
        
        const currentUser = getGoogleUser();
        const isFollowing = currentUser && (u.followers || []).includes(currentUser.email);
        const isOtherUser = currentUser && currentUser.email !== email;
        
        if (btnFollow) {
            btnFollow.style.display = isOtherUser ? 'inline-block' : 'none';
            btnFollow.innerText = isFollowing ? 'Diikuti' : 'Ikuti';
            btnFollow.style.background = isFollowing ? 'rgba(255,255,255,0.1)' : 'white';
            btnFollow.style.color = isFollowing ? 'white' : 'black';
        }
        if (btnMsg) btnMsg.style.display = isOtherUser ? 'inline-block' : 'none';
        
        window._viewingUser = u;
        _loadUserActivity(email, u);
        
    } catch(e) {
        console.error('viewUserProfile error:', e);
        const dn = email.split('@')[0];
        if (nameEl) nameEl.innerText = dn;
        if (avatarEl) { avatarEl.innerHTML = ''; avatarEl.innerText = dn.charAt(0).toUpperCase(); }
        if (actEl) actEl.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Belum ada aktivitas.</div>';
        window._viewingUser = { email, name: dn };
    }
}

async function _loadUserActivity(email, userData) {
    const actEl = document.getElementById('upvActivity');
    if (!actEl) return;
    try {
        const db_fs = window._firestoreDB;
        if (!db_fs) { actEl.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Belum ada aktivitas publik.</div>'; return; }
        
        // Ambil komentar terbaru user
        const qComments = window._fsQuery(
            window._fsCollection(db_fs, 'comments'),
            window._fsWhere('email', '==', email)
        );
        const snap = await window._fsGetDocs(qComments);
        const comments = snap.docs.map(d => d.data()).sort((a, b) => {
            const ta = a.createdAt ? a.createdAt.seconds : 0;
            const tb = b.createdAt ? b.createdAt.seconds : 0;
            return tb - ta;
        }).slice(0, 3);
        
        // Ambil history & liked dari userData Firestore
        const history = userData.recentHistory || [];
        const likedSongs = userData.likedSongs || [];
        
        let html = '';
        
        if (history.length > 0) {
            html += '<div style="font-size:11px;color:var(--text-sub);text-transform:uppercase;letter-spacing:1px;padding:12px 16px 6px;font-weight:700;">Lagu Terakhir Diputar</div>';
            html += history.slice(0, 3).map(t =>
                '<div class="v-item" onclick="playMusicById(\'' + (t.videoId||'') + '\')" style="cursor:pointer;">' +
                '<img loading="lazy" class="v-img" src="' + (t.img || 'https://via.placeholder.com/48x48?text=music') + '">' +
                '<div class="v-info"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div></div>'
            ).join('');
        }
        
        if (likedSongs.length > 0) {
            html += '<div style="font-size:11px;color:var(--text-sub);text-transform:uppercase;letter-spacing:1px;padding:12px 16px 6px;font-weight:700;">Lagu yang Disukai</div>';
            html += likedSongs.slice(0, 3).map(t =>
                '<div class="v-item" onclick="playMusicById(\'' + (t.videoId||'') + '\')" style="cursor:pointer;">' +
                '<img loading="lazy" class="v-img" src="' + (t.img || 'https://via.placeholder.com/48x48?text=music') + '">' +
                '<div class="v-info"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div></div>'
            ).join('');
        }
        
        if (comments.length > 0) {
            html += '<div style="font-size:11px;color:var(--text-sub);text-transform:uppercase;letter-spacing:1px;padding:12px 16px 6px;font-weight:700;">Komentar Terbaru</div>';
            html += comments.map(c =>
                '<div style="padding:10px 16px;border-bottom:1px solid rgba(255,255,255,0.05);">' +
                '<div style="font-size:13px;color:white;line-height:1.5;">' + (c.text || '') + '</div>' +
                '<div style="font-size:11px;color:var(--text-sub);margin-top:4px;">' + (c.createdAt ? new Date(c.createdAt.seconds * 1000).toLocaleDateString('id-ID') : '') + '</div>' +
                '</div>'
            ).join('');
        }
        
        if (!html) html = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Belum ada aktivitas publik.</div>';
        actEl.innerHTML = html;
    } catch(e) {
        console.error('_loadUserActivity error:', e);
        if (actEl) actEl.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;text-align:center;">Belum ada aktivitas publik.</div>';
    }
}

async function toggleFollowUser() {
    const currentUser = getGoogleUser(); if (!currentUser) { showToast('Login dulu untuk mengikuti'); return; }
    const targetUser = window._viewingUser; if (!targetUser) return;
    if (currentUser.email === targetUser.email) { showToast('Tidak bisa mengikuti diri sendiri'); return; }
    
    try {
        const db_fs = window._firestoreDB;
        if (!db_fs) return;

        // Resolve doc refs from query (don't assume docId == email)
        const qTarget = window._fsQuery(
            window._fsCollection(db_fs, 'users'),
            window._fsWhere('email', '==', targetUser.email)
        );
        const qCurrent = window._fsQuery(
            window._fsCollection(db_fs, 'users'),
            window._fsWhere('email', '==', currentUser.email)
        );

        const [snapTarget, snapCurrent] = await Promise.all([
            window._fsGetDocs(qTarget),
            window._fsGetDocs(qCurrent)
        ]);

        if (snapTarget.empty || snapCurrent.empty) {
            showToast('User tidak ditemukan di database');
            return;
        }

        const targetDoc = snapTarget.docs[0];
        const currentDoc = snapCurrent.docs[0];

        // 1) Update target user's followers
        let followers = targetDoc.data().followers || [];
        if (followers.includes(currentUser.email)) {
            followers = followers.filter(e => e !== currentUser.email);
        } else {
            followers.push(currentUser.email);
        }
        await window._fsSetDoc(targetDoc.ref, { followers: followers }, { merge: true });

        // 2) Update current user's following
        let following = currentDoc.data().following || [];
        if (following.includes(targetUser.email)) {
            following = following.filter(e => e !== targetUser.email);
        } else {
            following.push(targetUser.email);
        }
        await window._fsSetDoc(currentDoc.ref, { following: following }, { merge: true });

        // refresh cache for future searches (avoid stale data confusion)
        _usersCacheLoaded = false;
        _usersCache = null;

        viewUserProfile(targetUser.email);
    } catch(e) { showToast('Gagal mengikuti'); }
}

// MESSAGING
let _chatInterval = null;
function openChatWithUser() {
    const targetUser = window._viewingUser; if (!targetUser) return;
    const currentUser = getGoogleUser(); if (!currentUser) { showToast('Login dulu untuk berkirim pesan'); return; }
    
    _dmTarget = { email: targetUser.email, name: targetUser.name || targetUser.email.split('@')[0] };
    switchView('chat');
    const chatName = document.getElementById('chatName');
    const chatAvatar = document.getElementById('chatAvatar');
    if (chatName) chatName.innerText = _dmTarget.name;
    if (chatAvatar) {
        if (targetUser.picture) chatAvatar.innerHTML = '<img src="' + targetUser.picture + '" style="width:100%;height:100%;object-fit:cover;">';
        else { chatAvatar.innerHTML = ''; chatAvatar.innerText = _dmTarget.name.charAt(0).toUpperCase(); }
    }
    loadDMMessages();
    if (_chatInterval) clearInterval(_chatInterval);
    _chatInterval = setInterval(() => loadDMMessages(), 5000);
}

async function loadChatMessages(otherEmail) {
    // Alias untuk kompatibilitas — delegate ke loadDMMessages
    if (otherEmail && (!_dmTarget || _dmTarget.email !== otherEmail)) {
        _dmTarget = { email: otherEmail, name: otherEmail.split('@')[0] };
    }
    loadDMMessages();
}

async function sendChatMessage() {
    await sendDM();
}

// SUBSCRIBE SONG
function checkIfSubscribed(videoId) {
    if (!db) return;
    const tx = db.transaction('subscribed_songs', 'readonly');
    tx.objectStore('subscribed_songs').get(videoId).onsuccess = (e) => {
        const subbed = !!e.target.result;
        const btn = document.getElementById('btnSubscribe');
        if (btn) {
            btn.querySelector('svg').style.fill = subbed ? 'var(--spotify-green)' : 'rgba(255,255,255,0.7)';
        }
    };
}

function toggleSubscribe() {
    if (!currentTrack || !db) return;
    const tx = db.transaction('subscribed_songs', 'readwrite');
    const store = tx.objectStore('subscribed_songs');
    store.get(currentTrack.videoId).onsuccess = (e) => {
        if (e.target.result) {
            store.delete(currentTrack.videoId); showToast('Berhenti subscribe lagu');
        } else {
            store.put(currentTrack); showToast('Subscribe lagu ini!');
        }
        checkIfSubscribed(currentTrack.videoId);
        renderLibraryUI();
    };
}

// Update renderLibraryUI to show Subscribed section
function openSubscribedSongs() {
    if (!db) return;
    const tx = db.transaction('subscribed_songs', 'readonly');
    tx.objectStore('subscribed_songs').getAll().onsuccess = (e) => {
        const tracks = e.target.result || [];
        document.getElementById('playlistNameDisplay').innerText = 'Lagu di Subscribe';
        document.getElementById('playlistStatsDisplay').innerText = tracks.length + ' lagu';
        document.getElementById('playlistImageDisplay').src = tracks.length > 0 ? (tracks[0].img || '') : 'https://via.placeholder.com/220x220?text=music';
        window._playlistTracks = tracks;
        document.getElementById('playlistTracksContainer').innerHTML = tracks.length > 0 ? tracks.map(renderVItem).join('') : '<div style="color:var(--text-sub);padding:16px;">Belum ada lagu yang di subscribe.</div>';
        switchView('playlist');
    };
}
async function doSearch(q) {
    document.getElementById('searchCategoriesUI').style.display = 'none';
    document.getElementById('searchResultsUI').style.display = 'block';
    const el = document.getElementById('searchResults');
    el.innerHTML = '<div style="color:var(--text-sub);padding:16px;text-align:center;">Mencari...</div>';
    try {
        const res = await apiFetch('/api/search?query=' + encodeURIComponent(q));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) el.innerHTML = result.data.map(renderVItem).join('');
        else el.innerHTML = '<div style="color:var(--text-sub);padding:16px;text-align:center;">Tidak ada hasil untuk "' + q + '"</div>';
    } catch(e) { el.innerHTML = '<div style="color:#ff5252;padding:16px;text-align:center;">Gagal mencari.</div>'; }
}

// ARTIST
async function openArtist(encodedName) {
    const name = decodeURIComponent(encodedName);
    document.getElementById('artistNameDisplay').innerText = name;
    document.getElementById('artistTracksContainer').innerHTML = '<div style="color:var(--text-sub);padding:16px;">Memuat...</div>';
    switchView('artist');
    try {
        const res = await apiFetch('/api/search?query=' + encodeURIComponent(name));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            window._artistTracks = result.data;
            document.getElementById('artistTracksContainer').innerHTML = result.data.map(renderVItem).join('');
        }
    } catch(e) {}
}
function playFirstArtistTrack() {
    if (window._artistTracks && window._artistTracks.length > 0) playMusic(window._artistTracks[0].videoId, makeTrackData(window._artistTracks[0]));
}

// LIKE
function checkIfLiked(videoId) {
    if (!db) return;
    const tx = db.transaction('liked_songs', 'readonly');
    tx.objectStore('liked_songs').get(videoId).onsuccess = (e) => {
        const liked = !!e.target.result;
        const btn = document.getElementById('btnLikeSong'); if (btn) btn.style.fill = liked ? 'var(--spotify-green)' : 'white';
        const btn2 = document.getElementById('btnLikeLyric'); if (btn2) btn2.style.fill = liked ? 'var(--spotify-green)' : 'var(--text-sub)';
    };
}
function toggleLike() {
    if (!currentTrack || !db) return;
    const tx = db.transaction('liked_songs', 'readwrite');
    const store = tx.objectStore('liked_songs');
    store.get(currentTrack.videoId).onsuccess = (e) => {
        if (e.target.result) {
            store.delete(currentTrack.videoId); showToast('Dihapus dari Disukai');
            const btn = document.getElementById('btnLikeSong'); if (btn) btn.style.fill = 'white';
            const btn2 = document.getElementById('btnLikeLyric'); if (btn2) btn2.style.fill = 'var(--text-sub)';
        } else {
            store.put(currentTrack); showToast('Ditambahkan ke Disukai');
            const btn = document.getElementById('btnLikeSong'); if (btn) btn.style.fill = 'var(--spotify-green)';
            const btn2 = document.getElementById('btnLikeLyric'); if (btn2) btn2.style.fill = 'var(--spotify-green)';
        }
        renderLibraryUI();
        // Sync liked songs ke Firestore untuk aktivitas profil
        _syncLikedSongsToFirestore();
    };
}

function _syncLikedSongsToFirestore() {
    const user = getGoogleUser();
    if (!user || !db || !window._firestoreDB) return;
    const tx = db.transaction('liked_songs', 'readonly');
    tx.objectStore('liked_songs').getAll().onsuccess = async (e) => {
        const liked = (e.target.result || []).slice(0, 20); // max 20
        try {
            await window._fsSetDoc(
                window._fsDoc(window._firestoreDB, 'users', user.email),
                { likedSongs: liked },
                { merge: true }
            );
        } catch(err) { /* silent */ }
    };
}

// LIBRARY
function renderLibraryUI() {
    const container = document.getElementById('libraryContainer'); if (!container || !db) return;
    const tx = db.transaction(['liked_songs', 'playlists', 'downloaded_songs', 'subscribed_songs'], 'readonly');
    let liked = [], playlists = [], downloaded = [], subscribed = [];
    tx.objectStore('liked_songs').getAll().onsuccess = (e) => { liked = e.target.result || []; };
    tx.objectStore('playlists').getAll().onsuccess = (e) => { playlists = e.target.result || []; };
    tx.objectStore('downloaded_songs').getAll().onsuccess = (e) => { downloaded = e.target.result || []; };
    tx.objectStore('subscribed_songs').getAll().onsuccess = (e) => { subscribed = e.target.result || []; };
    tx.oncomplete = () => {
        const history = JSON.parse(localStorage.getItem('auspotyHistory') || '[]');
        let html = '';
        html += '<div class="lib-item" onclick="openLikedSongs()"><div class="lib-item-img liked"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Lagu yang Disukai</div><div class="lib-item-sub">Playlist \u00b7 ' + liked.length + ' lagu</div></div></div>';
        html += '<div class="lib-item" onclick="openSubscribedSongs()"><div class="lib-item-img" style="background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Lagu di Subscribe</div><div class="lib-item-sub">Koleksi \u00b7 ' + subscribed.length + ' lagu</div></div></div>';
        html += '<div class="lib-item" onclick="openHistoryView()"><div class="lib-item-img" style="background:linear-gradient(135deg,#1e3264,#477d95);display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Riwayat Diputar</div><div class="lib-item-sub">Koleksi \u00b7 ' + history.length + ' lagu</div></div></div>';
        html += '<div class="lib-item" onclick="openDownloadedSongs()"><div class="lib-item-img" style="background:linear-gradient(135deg,#2d6a4f,#739c18);display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Lagu Diunduh</div><div class="lib-item-sub">Koleksi \u00b7 ' + downloaded.length + ' lagu</div></div></div>';
        playlists.forEach(pl => {
            html += '<div class="lib-item" onclick="openPlaylist(\'' + pl.id + '\')"><img class="lib-item-img" src="' + (pl.img || 'https://via.placeholder.com/64x64?text=music') + '" style="border-radius:4px;"><div class="lib-item-info"><div class="lib-item-title">' + pl.name + '</div><div class="lib-item-sub">Playlist \u00b7 ' + (pl.tracks ? pl.tracks.length : 0) + ' lagu</div></div></div>';
        });
        container.innerHTML = html;
    };
}
function openLikedSongs() {
    if (!db) return;
    const tx = db.transaction('liked_songs', 'readonly');
    tx.objectStore('liked_songs').getAll().onsuccess = (e) => {
        const tracks = e.target.result || [];
        document.getElementById('playlistNameDisplay').innerText = 'Lagu yang Disukai';
        document.getElementById('playlistStatsDisplay').innerText = tracks.length + ' lagu';
        document.getElementById('playlistImageDisplay').src = tracks.length > 0 ? (tracks[0].img || '') : 'https://via.placeholder.com/220x220?text=music';
        window._playlistTracks = tracks;
        document.getElementById('playlistTracksContainer').innerHTML = tracks.length > 0 ? tracks.map(renderVItem).join('') : '<div style="color:var(--text-sub);padding:16px;">Belum ada lagu disukai.</div>';
        switchView('playlist');
    };
}
function openHistoryView() {
    const history = JSON.parse(localStorage.getItem('auspotyHistory') || '[]');
    document.getElementById('playlistNameDisplay').innerText = 'Riwayat Diputar';
    document.getElementById('playlistStatsDisplay').innerText = history.length + ' lagu';
    document.getElementById('playlistImageDisplay').src = history.length > 0 ? (history[0].img || '') : 'https://via.placeholder.com/220x220?text=music';
    window._playlistTracks = history;
    document.getElementById('playlistTracksContainer').innerHTML = history.length > 0 ? history.map(renderVItem).join('') : '<div style="color:var(--text-sub);padding:16px;">Belum ada riwayat.</div>';
    switchView('playlist');
}
function openDownloadedSongs() {
    if (!db) return;
    const tx = db.transaction('downloaded_songs', 'readonly');
    tx.objectStore('downloaded_songs').getAll().onsuccess = (e) => {
        const tracks = e.target.result || [];
        document.getElementById('playlistNameDisplay').innerText = 'Lagu Diunduh';
        document.getElementById('playlistStatsDisplay').innerText = tracks.length + ' lagu';
        document.getElementById('playlistImageDisplay').src = tracks.length > 0 ? (tracks[0].img || '') : 'https://via.placeholder.com/220x220?text=music';
        window._playlistTracks = tracks;
        window._isDownloadedView = true;
        document.getElementById('playlistTracksContainer').innerHTML = tracks.length > 0
            ? tracks.map(t => renderDownloadedVItem(t)).join('')
            : '<div style="color:var(--text-sub);padding:16px;">Belum ada lagu diunduh.<br><small>Tekan ikon unduh saat memutar lagu.</small></div>';
        switchView('playlist');
    };
}
function saveDownloadedSong(track) {
    if (!db || !track || !track.videoId) return;
    const tx = db.transaction('downloaded_songs', 'readwrite');
    tx.objectStore('downloaded_songs').put({
        videoId: track.videoId,
        title: track.title || '',
        artist: track.artist || '',
        img: track.img || '',
        downloadedAt: Date.now()
    });
    tx.oncomplete = () => renderLibraryUI();
}
function deleteDownloadedSong(videoId) {
    if (!db) return;
    const tx = db.transaction('downloaded_songs', 'readwrite');
    tx.objectStore('downloaded_songs').delete(videoId);
    tx.oncomplete = () => { showToast('Dihapus dari unduhan'); openDownloadedSongs(); };
}
function openPlaylist(id) {
    if (!db) return;
    const tx = db.transaction('playlists', 'readonly');
    tx.objectStore('playlists').get(id).onsuccess = (e) => {
        const pl = e.target.result; if (!pl) return;
        document.getElementById('playlistNameDisplay').innerText = pl.name;
        document.getElementById('playlistStatsDisplay').innerText = (pl.tracks ? pl.tracks.length : 0) + ' lagu';
        document.getElementById('playlistImageDisplay').src = pl.img || 'https://via.placeholder.com/220x220?text=music';
        window._playlistTracks = pl.tracks || [];
        document.getElementById('playlistTracksContainer').innerHTML = (pl.tracks && pl.tracks.length > 0) ? pl.tracks.map(renderVItem).join('') : '<div style="color:var(--text-sub);padding:16px;">Playlist kosong.</div>';
        switchView('playlist');
    };
}
function playFirstPlaylistTrack() {
    if (window._playlistTracks && window._playlistTracks.length > 0) playMusic(window._playlistTracks[0].videoId, makeTrackData(window._playlistTracks[0]));
}
function openCreatePlaylist() { document.getElementById('createPlaylistModal').style.display = 'block'; }
function closeCreatePlaylist() { document.getElementById('createPlaylistModal').style.display = 'none'; }
function previewImage(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => { document.getElementById('cpPreview').src = e.target.result; };
    reader.readAsDataURL(file);
}
function saveNewPlaylist() {
    const name = document.getElementById('cpName').value.trim() || 'Playlist Baru';
    const img = document.getElementById('cpPreview').src;
    if (!db) return;
    const pl = { id: Date.now().toString(), name, img, tracks: [] };
    const tx = db.transaction('playlists', 'readwrite');
    tx.objectStore('playlists').put(pl);
    tx.oncomplete = () => { closeCreatePlaylist(); renderLibraryUI(); showToast('Playlist dibuat!'); };
}
function openAddToPlaylistModal() {
    if (!currentTrack || !db) return;
    document.getElementById('addToPlaylistModal').style.display = 'flex';
    const tx = db.transaction('playlists', 'readonly');
    tx.objectStore('playlists').getAll().onsuccess = (e) => {
        const playlists = e.target.result || [];
        const list = document.getElementById('addToPlaylistList');
        if (playlists.length === 0) { list.innerHTML = '<div style="color:var(--text-sub);padding:16px;">Belum ada playlist.</div>'; }
        else { list.innerHTML = playlists.map(pl => '<div class="v-item" onclick="addTrackToPlaylist(\'' + pl.id + '\')"><img loading="lazy" class="v-img" src="' + (pl.img || 'https://via.placeholder.com/48x48?text=music') + '"><div class="v-info"><div class="v-title">' + pl.name + '</div><div class="v-sub">' + (pl.tracks ? pl.tracks.length : 0) + ' lagu</div></div></div>').join(''); }
    };
}
function closeAddToPlaylistModal() { document.getElementById('addToPlaylistModal').style.display = 'none'; }
function addTrackToPlaylist(id) {
    if (!currentTrack || !db) return;
    const tx = db.transaction('playlists', 'readwrite');
    const store = tx.objectStore('playlists');
    store.get(id).onsuccess = (e) => {
        const pl = e.target.result; if (!pl) return;
        if (!pl.tracks) pl.tracks = [];
        if (!pl.tracks.find(t => t.videoId === currentTrack.videoId)) {
            pl.tracks.push(currentTrack); store.put(pl);
            tx.oncomplete = () => { closeAddToPlaylistModal(); showToast('Ditambahkan ke ' + pl.name); renderLibraryUI(); };
        } else { closeAddToPlaylistModal(); showToast('Sudah ada di playlist ini'); }
    };
}

// SETTINGS
function getSettings() { try { return JSON.parse(localStorage.getItem('auspotySettings') || '{}'); } catch(e) { return {}; } }
function saveSettings(obj) { const s = Object.assign(getSettings(), obj); localStorage.setItem('auspotySettings', JSON.stringify(s)); }
function applyAllSettings() {
    const s = getSettings();
    if (s.darkMode === false) document.body.classList.add('light-mode'); else document.body.classList.remove('light-mode');
    const themes = { green: { a: '#a78bfa', b: '#f472b6', g: '#a78bfa' }, blue: { a: '#38bdf8', b: '#818cf8', g: '#38bdf8' }, red: { a: '#f87171', b: '#fb923c', g: '#f87171' }, purple: { a: '#c084fc', b: '#e879f9', g: '#c084fc' }, orange: { a: '#fb923c', b: '#fbbf24', g: '#fb923c' } };
    const t = themes[s.theme] || themes.green;
    document.documentElement.style.setProperty('--accent', t.a);
    document.documentElement.style.setProperty('--accent2', t.b);
    document.documentElement.style.setProperty('--spotify-green', t.g);
    document.documentElement.style.setProperty('--spotify-green-dark', t.g);
    document.body.classList.remove('font-small', 'font-normal', 'font-large', 'font-xlarge');
    document.body.classList.add(({ small: 'font-small', normal: 'font-normal', large: 'font-large', xlarge: 'font-xlarge' })[s.fontSize] || 'font-normal');
    const themeNames = { green: 'Ungu-Pink (Default)', blue: 'Biru-Indigo', red: 'Merah-Oranye', purple: 'Ungu-Magenta', orange: 'Oranye-Kuning' };
    const el = document.getElementById('themeLabel'); if (el) el.innerText = themeNames[s.theme] || 'Ungu-Pink (Default)';
    const ql = document.getElementById('qualityLabel'); if (ql) ql.innerText = s.quality || 'Auto';
    const fl = document.getElementById('fontSizeLabel'); if (fl) fl.innerText = ({ small: 'Kecil', normal: 'Normal', large: 'Besar', xlarge: 'Sangat Besar' })[s.fontSize] || 'Normal';
    const ll = document.getElementById('langLabel'); if (ll) ll.innerText = s.language || 'Indonesia';
    const rl = document.getElementById('regionLabel'); if (rl) rl.innerText = s.region || 'Indonesia';
    setToggle('darkModeToggle', s.darkMode !== false); setToggle('autoplayToggle', s.autoplay !== false);
    setToggle('crossfadeToggle', !!s.crossfade); setToggle('normalizeToggle', !!s.normalize);
    setToggle('lyricsSyncToggle', s.lyricsSync !== false); setToggle('notifNowPlayingToggle', s.notifNowPlaying !== false);
    setToggle('notifNewReleaseToggle', !!s.notifNewRelease);
    estimateCacheSize();
}
function setToggle(id, active) { const el = document.getElementById(id); if (!el) return; if (active) el.classList.add('active'); else el.classList.remove('active'); }
function toggleDarkMode() { const s = getSettings(); s.darkMode = s.darkMode === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleAutoplay() { const s = getSettings(); s.autoplay = s.autoplay === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleCrossfade() { const s = getSettings(); s.crossfade = !s.crossfade; saveSettings(s); applyAllSettings(); }
function toggleNormalize() { const s = getSettings(); s.normalize = !s.normalize; saveSettings(s); applyAllSettings(); }
function toggleLyricsSync() { const s = getSettings(); s.lyricsSync = s.lyricsSync === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleNotif(key) { const s = getSettings(); const k = 'notif' + key.charAt(0).toUpperCase() + key.slice(1); s[k] = !s[k]; saveSettings(s); applyAllSettings(); }

let pickerCallback = null;
function openPicker(title, options, currentVal, cb) {
    pickerCallback = cb;
    document.getElementById('pickerTitle').innerText = title;
    document.getElementById('pickerOptions').innerHTML = options.map(o =>
        '<div class="picker-option' + (o.value === currentVal ? ' selected' : '') + '" onclick="selectPickerOption(\'' + o.value + '\')">' +
        o.label + (o.value === currentVal ? '<svg class="picker-check" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>' : '') + '</div>'
    ).join('');
    document.getElementById('pickerOverlay').classList.add('open');
    document.getElementById('pickerModal').classList.add('open');
}
function selectPickerOption(val) { if (pickerCallback) pickerCallback(val); closePicker(); }
function closePicker() { document.getElementById('pickerOverlay').classList.remove('open'); document.getElementById('pickerModal').classList.remove('open'); pickerCallback = null; }
function openThemePicker() { const s = getSettings(); openPicker('Tema Warna', [{ label: 'Ungu-Pink (Default)', value: 'green' }, { label: 'Biru', value: 'blue' }, { label: 'Merah', value: 'red' }, { label: 'Ungu', value: 'purple' }, { label: 'Oranye', value: 'orange' }], s.theme || 'green', (val) => { saveSettings({ theme: val }); applyAllSettings(); }); }
function openQualityPicker() { const s = getSettings(); openPicker('Kualitas Audio', [{ label: 'Auto', value: 'Auto' }, { label: 'Rendah - 64 kbps', value: 'Rendah 64kbps' }, { label: 'Sedang - 128 kbps', value: 'Sedang 128kbps' }, { label: 'Tinggi - 256 kbps', value: 'Tinggi 256kbps' }, { label: 'Sangat Tinggi - 320 kbps', value: 'Sangat Tinggi 320kbps' }], s.quality || 'Auto', (val) => { saveSettings({ quality: val }); applyAllSettings(); }); }
function openFontSizePicker() { const s = getSettings(); openPicker('Ukuran Teks', [{ label: 'Kecil', value: 'small' }, { label: 'Normal', value: 'normal' }, { label: 'Besar', value: 'large' }, { label: 'Sangat Besar', value: 'xlarge' }], s.fontSize || 'normal', (val) => { saveSettings({ fontSize: val }); applyAllSettings(); }); }
function openLanguagePicker() { const s = getSettings(); openPicker('Bahasa Aplikasi', [{ label: 'Indonesia', value: 'Indonesia' }, { label: 'English', value: 'English' }, { label: 'Japanese', value: 'Japanese' }, { label: 'Korean', value: 'Korean' }], s.language || 'Indonesia', (val) => { saveSettings({ language: val }); applyAllSettings(); loadHomeData(); }); }
function openRegionPicker() { const s = getSettings(); openPicker('Wilayah Konten', [{ label: 'Indonesia', value: 'Indonesia' }, { label: 'Global', value: 'Global' }, { label: 'Amerika Serikat', value: 'Amerika Serikat' }, { label: 'Jepang', value: 'Jepang' }, { label: 'Korea', value: 'Korea' }], s.region || 'Indonesia', (val) => { saveSettings({ region: val }); applyAllSettings(); loadHomeData(); }); }

// EDIT PROFILE
function openEditProfile() {
    const s = getSettings();
    document.getElementById('editProfileName').value = s.profileName || '';
    const av = document.getElementById('editProfileAvatar');
    const savedPhoto = localStorage.getItem('auspotyProfilePhoto');
    if (savedPhoto) av.innerHTML = '<img src="' + savedPhoto + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
    else av.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
    // Load username jika ada
    const usernameInput = document.getElementById('editProfileUsername');
    if (usernameInput) {
        const user = getGoogleUser();
        if (user && window._firestoreDB) {
            window._fsGetDoc(window._fsDoc(window._firestoreDB, 'users', user.email)).then(snap => {
                if (snap.exists()) usernameInput.value = snap.data().username || '';
            }).catch(() => {});
        }
    }
    document.getElementById('editProfileModal').style.display = 'flex';
}
function closeEditProfile() { document.getElementById('editProfileModal').style.display = 'none'; }
async function saveProfile() {
    const name = document.getElementById('editProfileName').value.trim() || 'Pengguna Auspoty';
    saveSettings({ profileName: name }); applyAllSettings(); updateProfileUI();
    // Simpan username jika diisi
    const usernameInput = document.getElementById('editProfileUsername');
    if (usernameInput && usernameInput.value.trim().length >= 3) {
        await saveUsername(usernameInput.value.trim());
    }
    closeEditProfile(); showToast('Profil disimpan!');
}
function triggerPhotoUpload() {
    if (window.flutter_inappwebview) {
        try { window.flutter_inappwebview.callHandler('pickProfilePhoto'); return; } catch(e) {}
    }
    document.getElementById('profilePhotoInput').click();
}
function applyProfilePhoto(base64) {
    localStorage.setItem('auspotyProfilePhoto', base64);
    // Update avatar di modal edit profil juga (biar langsung kelihatan)
    const av = document.getElementById('editProfileAvatar');
    if (av && base64) {
        av.innerHTML = '<img src="' + base64 + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
    }
    updateProfileUI();
    showToast('Foto profil diperbarui!');
}
function handleProfilePhotoChange(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        applyProfilePhoto(e.target.result);
    };
    reader.readAsDataURL(file);
}

// CACHE
function estimateCacheSize() {
    const el = document.getElementById('cacheSize'); if (!el) return;
    if ('storage' in navigator && 'estimate' in navigator.storage) {
        navigator.storage.estimate().then(({ usage }) => { el.innerText = (usage / (1024 * 1024)).toFixed(1) + ' MB digunakan'; }).catch(() => { el.innerText = 'Tidak dapat dihitung'; });
    } else { el.innerText = 'Tidak tersedia'; }
}
function clearCache() {
    if ('caches' in window) { caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))).then(() => { showToast('Cache berhasil dihapus!'); estimateCacheSize(); }); }
    else { showToast('Tidak ada cache untuk dihapus'); }
}
function clearLikedSongs() {
    if (!db) return;
    if (!confirm('Hapus semua lagu yang disukai?')) return;
    const tx = db.transaction('liked_songs', 'readwrite');
    tx.objectStore('liked_songs').clear();
    tx.oncomplete = () => { showToast('Lagu disukai dihapus!'); renderLibraryUI(); };
}

// DOWNLOAD
function downloadMusic() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    if (window.flutter_inappwebview) {
        showToast('Mengonversi lagu... tunggu sebentar');
        try {
            window.flutter_inappwebview.callHandler('downloadTrack',
                currentTrack.videoId,
                currentTrack.title || 'lagu',
                currentTrack.artist || '',
                currentTrack.img || currentTrack.thumbnail || ''
            );
        } catch(e) { showToast('Download gagal, coba lagi'); }
        return;
    }
    // Web/PWA: not supported
    showToast('Download hanya tersedia di aplikasi APK');
}

// GOOGLE AUTH
function getGoogleUser() { try { return JSON.parse(localStorage.getItem('auspotyGoogleUser') || 'null'); } catch(e) { return null; } }
function loginWithGoogle() {
    if (window.flutter_inappwebview) {
        try { window.flutter_inappwebview.callHandler('openGoogleLogin'); return; } catch(e) {}
    }
    if (window.AndroidBridge && typeof window.AndroidBridge.openGoogleLogin === 'function') window.AndroidBridge.openGoogleLogin();
    else if (typeof window._firebaseSignIn === 'function') window._firebaseSignIn();
    else showToast('Login Google belum tersedia');
}
function logoutFromGoogle() {
    if (window.AndroidBridge && typeof window.AndroidBridge.logout === 'function') window.AndroidBridge.logout();
    else if (typeof window._firebaseSignOut === 'function') window._firebaseSignOut();
    else { localStorage.removeItem('auspotyGoogleUser'); updateProfileUI(); }
}
function updateGoogleLoginUI() { updateProfileUI(); }
function updateProfileUI() {
    const user = getGoogleUser(); const s = getSettings();
    const name = user ? user.name : (s.profileName || 'Pengguna Auspoty');
    const manualPic = localStorage.getItem('auspotyProfilePhoto');
    const pic = manualPic || (user ? user.picture : '');
    
    // Sync to Firestore users collection
    if (user && user.email && window._firestoreDB) {
        window._fsSetDoc(window._fsDoc(window._firestoreDB, 'users', user.email), {
            name: name,
            email: user.email,
            picture: pic,
            lastSeen: window._fsTimestamp()
        }, { merge: true }).catch(e => console.error('Sync profile error:', e));
    }

    const pname = document.getElementById('settingsProfileName'); if (pname) pname.innerText = name;
    const psub = document.getElementById('settingsProfileSub'); if (psub) psub.innerText = user ? user.email : 'Auspoty Premium';
    const pav = document.getElementById('settingsAvatar');
    if (pav) { if (pic) pav.innerHTML = '<img src="' + pic + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'; else { pav.innerHTML = ''; pav.innerText = name.charAt(0).toUpperCase(); } }
    const hav = document.querySelector('.app-avatar');
    if (hav) { if (pic) hav.innerHTML = '<img src="' + pic + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'; else { hav.innerHTML = ''; hav.innerText = name.charAt(0).toUpperCase(); } }
    const loginBtn = document.getElementById('googleLoginBtn'); if (loginBtn) loginBtn.style.display = user ? 'none' : 'block';
    const logoutBtn = document.getElementById('googleLogoutBtn'); if (logoutBtn) logoutBtn.style.display = user ? 'block' : 'none';
    const logoutSub = document.getElementById('googleLogoutSub'); if (logoutSub && user) logoutSub.innerText = user.email;
    // Tampilkan/sembunyikan tombol admin
    if (typeof updateAdminUI === 'function') updateAdminUI();
}

// COMMENTS
function openCommentsModal() {
    if (!currentTrack) return;
    document.getElementById('commentsModal').style.display = 'flex';
    document.getElementById('commentTrackName').innerText = currentTrack.title + ' \u2014 ' + currentTrack.artist;
    const user = getGoogleUser();
    document.getElementById('commentInputArea').style.display = user ? 'block' : 'none';
    document.getElementById('commentLoginPrompt').style.display = user ? 'none' : 'block';
    loadComments(currentTrack.videoId);
}
function closeCommentsModal() { document.getElementById('commentsModal').style.display = 'none'; }
async function loadComments(videoId) {
    const list = document.getElementById('commentsList');
    list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Memuat komentar...</div>';
    try {
        const db_fs = window._firestoreDB;
        if (!db_fs) { list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Firestore belum aktif.</div>'; return; }
        const q = window._fsQuery(window._fsCollection(db_fs, 'comments'), window._fsWhere('videoId', '==', videoId));
        const snap = await window._fsGetDocs(q);
        if (snap.empty) { list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Belum ada komentar. Jadilah yang pertama!</div>'; return; }
        
        const currentUser = getGoogleUser();
        const docs = snap.docs.map(doc => {
            const data = doc.data();
            data.id = doc.id;
            return data;
        });
        
        // Pisahkan parent comments dan replies
        const parents = docs.filter(d => !d.parentId).sort((a, b) => (b.createdAt ? b.createdAt.seconds : 0) - (a.createdAt ? a.createdAt.seconds : 0));
        const replies = docs.filter(d => d.parentId);

        list.innerHTML = parents.map(d => renderCommentItem(d, replies, currentUser)).join('');
    } catch(e) { list.innerHTML = '<div style="color:#ff5252;text-align:center;padding:20px;font-size:13px;">Gagal memuat: ' + e.message + '</div>'; }
}

function renderCommentItem(d, allReplies, currentUser, isReply = false) {
    const isAdmin = d.email === 'yusrilrizky149@gmail.com';
    const isOwner = currentUser && currentUser.email === d.email;
    const canDelete = isOwner || (currentUser && currentUser.email === 'yusrilrizky149@gmail.com');
    
    const badge = isAdmin ? '<span style="background:linear-gradient(135deg,#a78bfa,#f472b6);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:6px;">ADMIN</span>' : '<span style="background:rgba(255,255,255,0.1);color:var(--text-sub);font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;margin-left:6px;">Pengguna</span>';
    const time = d.createdAt ? new Date(d.createdAt.seconds * 1000).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
    
    const likes = d.likes || [];
    const isLiked = currentUser && likes.includes(currentUser.email);
    const likeColor = isLiked ? 'var(--accent)' : 'var(--text-sub)';
    
    let html = '<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:12px;' + (isReply ? 'margin-left:40px;scale:0.95;transform-origin:left;' : '') + '">' +
        '<div onclick="viewUserProfile(\'' + d.email + '\')" style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;overflow:hidden;cursor:pointer;">' + 
        (d.picture ? '<img src="' + d.picture + '" style="width:100%;height:100%;object-fit:cover;">' : d.name.charAt(0).toUpperCase()) + '</div>' +
        '<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:12px;padding:10px 14px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;flex-wrap:wrap;gap:4px;">' +
        '<span onclick="viewUserProfile(\'' + d.email + '\')" style="font-size:13px;font-weight:700;color:var(--accent);cursor:pointer;">' + d.name + badge + '</span>' +
        '<span style="font-size:11px;color:var(--text-sub);">' + time + '</span></div>' +
        '<p style="font-size:14px;color:white;line-height:1.5;margin:0;">' + d.text + '</p>' +
        '<div style="display:flex;gap:16px;margin-top:8px;align-items:center;">' +
        '<div onclick="toggleLikeComment(\'' + d.id + '\')" style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:12px;color:' + likeColor + ';">' +
        '<svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:' + likeColor + ';"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>' + (likes.length || 0) + '</div>' +
        (!isReply ? '<div onclick="replyToComment(\'' + d.id + '\', \'' + d.name + '\')" style="font-size:12px;color:var(--text-sub);cursor:pointer;">Balas</div>' : '') +
        (canDelete ? '<div onclick="deleteComment(\'' + d.id + '\')" style="font-size:12px;color:#ff5252;cursor:pointer;margin-left:auto;">Hapus</div>' : '') +
        '</div></div></div>';
    
    // Render replies
    if (!isReply) {
        const itemReplies = allReplies.filter(r => r.parentId === d.id).sort((a, b) => (a.createdAt ? a.createdAt.seconds : 0) - (b.createdAt ? b.createdAt.seconds : 0));
        html += itemReplies.map(r => renderCommentItem(r, [], currentUser, true)).join('');
    }
    
    return html;
}

let _replyingTo = null;
function replyToComment(id, name) {
    _replyingTo = { id, name };
    const input = document.getElementById('commentInput');
    input.placeholder = 'Membalas ' + name + '...';
    input.focus();
    const banner = document.getElementById('replyBanner');
    const bannerText = document.getElementById('replyBannerText');
    if (banner) { banner.style.display = 'flex'; }
    if (bannerText) bannerText.innerText = 'Membalas ' + name;
}
function cancelReply() {
    _replyingTo = null;
    const input = document.getElementById('commentInput');
    if (input) input.placeholder = 'Tulis komentar...';
    const banner = document.getElementById('replyBanner');
    if (banner) banner.style.display = 'none';
}

async function deleteComment(id) {
    if (!confirm('Hapus komentar ini?')) return;
    try {
        await window._fsDeleteDoc(window._fsDoc(window._firestoreDB, 'comments', id));
        showToast('Komentar dihapus');
        loadComments(currentTrack.videoId);
    } catch(e) { showToast('Gagal hapus: ' + e.message); }
}

async function toggleLikeComment(id) {
    const user = getGoogleUser(); if (!user) { showToast('Login dulu untuk memberi Like'); return; }
    if (!window._firestoreDB) { showToast('Firestore belum siap'); return; }
    try {
        const docRef = window._fsDoc(window._firestoreDB, 'comments', id);
        const docSnap = await window._fsGetDoc(docRef);
        if (!docSnap.exists()) { showToast('Komentar tidak ditemukan'); return; }
        const data = docSnap.data();
        let likes = Array.isArray(data.likes) ? [...data.likes] : [];
        const alreadyLiked = likes.includes(user.email);
        if (alreadyLiked) {
            likes = likes.filter(e => e !== user.email);
        } else {
            likes.push(user.email);
        }
        try {
            if (typeof window._fsUpdateDoc === 'function') {
                await window._fsUpdateDoc(docRef, { likes });
            } else {
                await window._fsSetDoc(docRef, { likes }, { merge: true });
            }
        } catch(e2) {
            await window._fsSetDoc(docRef, { likes }, { merge: true });
        }
        if (currentTrack) loadComments(currentTrack.videoId);
    } catch(e) {
        showToast('Gagal like: ' + (e.message || String(e)));
        console.error('toggleLikeComment:', e);
    }
}

async function submitComment() {
    const user = getGoogleUser(); if (!user) { showToast('Login dulu untuk berkomentar'); return; }
    if (!currentTrack) return;
    const input = document.getElementById('commentInput'); const text = input.value.trim();
    if (!text) { showToast('Komentar tidak boleh kosong'); return; }
    try {
        const commentData = { 
            videoId: currentTrack.videoId, 
            name: user.name, 
            email: user.email, 
            picture: user.picture || '', 
            text: text, 
            createdAt: window._fsTimestamp(),
            likes: []
        };
        if (_replyingTo) {
            commentData.parentId = _replyingTo.id;
            _replyingTo = null;
            input.placeholder = 'Tulis komentar...';
            const banner = document.getElementById('replyBanner');
            if (banner) banner.style.display = 'none';
        }
        await window._fsAddDoc(window._fsCollection(window._firestoreDB, 'comments'), commentData);
        input.value = ''; showToast('Komentar terkirim!'); loadComments(currentTrack.videoId);
    } catch(e) { showToast('Gagal kirim: ' + e.message); }
}

// INIT

// ============================================================
// NAMIDA UI — Album art scale & waveform seekbar
// ============================================================
function _setArtPlaying(playing) {
    var w = document.getElementById('playerArtWrapper');
    if (!w) return;
    if (playing) w.classList.add('playing');
    else w.classList.remove('playing');
}

var WAVEFORM_BARS = 48;
var _waveHeights = [];
function _initWaveform() {
    var c = document.getElementById('waveformContainer');
    if (!c) return;
    c.querySelectorAll('.waveform-bar').forEach(function(b) { b.remove(); });
    _waveHeights = [];
    var input = c.querySelector('.progress-bar');
    for (var i = 0; i < WAVEFORM_BARS; i++) {
        var h = 20 + Math.abs(Math.sin(i * 0.7 + 1.3) * 55) + Math.abs(Math.sin(i * 1.9) * 20);
        _waveHeights.push(Math.round(h));
        var bar = document.createElement('div');
        bar.className = 'waveform-bar';
        bar.style.height = h + '%';
        c.insertBefore(bar, input);
    }
}
function _updateWaveform(pct) {
    // waveform bars are hidden (display:none) — skip DOM work
}

document.addEventListener('DOMContentLoaded', function() {
    applyAllSettings(); renderSearchCategories();
    // Cek auth state — tampilkan login screen jika belum login
    _checkAuthAndInit();
});

// ============================================================
// AUTH SCREEN — Login / Register
// ============================================================
function _checkAuthAndInit() {
    const user = getGoogleUser();
    if (user && user.email) {
        // Sudah login — langsung masuk app
        _hideAuthScreen();
        updateProfileUI();
        loadHomeData();
    } else {
        // Belum login — tampilkan auth screen
        _showAuthScreen();
    }
}

function _showAuthScreen() {
    const s = document.getElementById('authScreen');
    if (s) s.style.display = 'block';
}

function _hideAuthScreen() {
    const s = document.getElementById('authScreen');
    if (s) s.style.display = 'none';
}

function authSwitchTab(tab) {
    const isLogin = tab === 'login';
    document.getElementById('formLogin').style.display = isLogin ? 'block' : 'none';
    document.getElementById('formRegister').style.display = isLogin ? 'none' : 'block';
    const tl = document.getElementById('tabLogin');
    const tr = document.getElementById('tabRegister');
    if (tl) { tl.style.background = isLogin ? 'white' : 'transparent'; tl.style.color = isLogin ? '#0a0a0f' : 'rgba(255,255,255,0.6)'; }
    if (tr) { tr.style.background = isLogin ? 'transparent' : 'white'; tr.style.color = isLogin ? 'rgba(255,255,255,0.6)' : '#0a0a0f'; }
    authClearErr();
}

function authClearErr() {
    const e = document.getElementById('authError');
    if (e) e.style.display = 'none';
}

function _authShowErr(msg) {
    const e = document.getElementById('authError');
    if (e) { e.innerText = msg; e.style.display = 'block'; }
}

function _authSetLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.style.opacity = loading ? '0.6' : '1';
}

function _authSuccess(userData) {
    localStorage.setItem('auspotyGoogleUser', JSON.stringify(userData));
    _hideAuthScreen();
    updateProfileUI();
    loadHomeData();
    if (typeof syncUserProfile === 'function') syncUserProfile();
    showToast('Selamat datang, ' + (userData.name || '').split(' ')[0] + '!');
}

async function doLogin() {
    const email = (document.getElementById('loginEmail').value || '').trim();
    const pass = document.getElementById('loginPassword').value || '';
    if (!email || !pass) { _authShowErr('Email dan password wajib diisi'); return; }
    _authSetLoading('btnLogin', true);
    authClearErr();
    try {
        if (typeof window._authLogin === 'function') {
            const userData = await window._authLogin(email, pass);
            _authSuccess(userData);
        } else {
            // Fallback: cek di Firestore manual
            _authShowErr('Auth belum siap, coba lagi');
        }
    } catch(e) {
        const msg = e.code === 'auth/user-not-found' ? 'Email tidak terdaftar' :
                    e.code === 'auth/wrong-password' ? 'Password salah' :
                    e.code === 'auth/invalid-email' ? 'Format email tidak valid' :
                    e.code === 'auth/invalid-credential' ? 'Email atau password salah' :
                    'Login gagal: ' + (e.message || e.code || String(e));
        _authShowErr(msg);
    } finally { _authSetLoading('btnLogin', false); }
}

async function doRegister() {
    const name = (document.getElementById('regName').value || '').trim();
    const email = (document.getElementById('regEmail').value || '').trim();
    const pass = document.getElementById('regPassword').value || '';
    if (!name) { _authShowErr('Nama wajib diisi'); return; }
    if (!email) { _authShowErr('Email wajib diisi'); return; }
    if (pass.length < 6) { _authShowErr('Password minimal 6 karakter'); return; }
    _authSetLoading('btnRegister', true);
    authClearErr();
    try {
        if (typeof window._authRegister === 'function') {
            const userData = await window._authRegister(name, email, pass);
            _authSuccess(userData);
        } else {
            _authShowErr('Auth belum siap, coba lagi');
        }
    } catch(e) {
        const msg = e.code === 'auth/email-already-in-use' ? 'Email sudah terdaftar, silakan masuk' :
                    e.code === 'auth/invalid-email' ? 'Format email tidak valid' :
                    e.code === 'auth/weak-password' ? 'Password terlalu lemah' :
                    'Daftar gagal: ' + (e.message || e.code || String(e));
        _authShowErr(msg);
    } finally { _authSetLoading('btnRegister', false); }
}

function doGoogleAuth() {
    authClearErr();
    if (window.flutter_inappwebview) {
        try { window.flutter_inappwebview.callHandler('openGoogleLogin'); return; } catch(e) {}
    }
    if (typeof window._firebaseSignIn === 'function') window._firebaseSignIn();
    else _authShowErr('Login Google belum tersedia');
}

// Override logoutFromGoogle agar kembali ke auth screen
const _origLogout = typeof logoutFromGoogle === 'function' ? logoutFromGoogle : null;
window.logoutFromGoogle = function() {
    if (_origLogout) _origLogout();
    else {
        if (typeof window._firebaseSignOut === 'function') window._firebaseSignOut();
        else localStorage.removeItem('auspotyGoogleUser');
    }
    setTimeout(() => {
        if (!getGoogleUser()) _showAuthScreen();
    }, 500);
};


// ============================================================
// BACKGROUND MODE — jaga musik tetap jalan saat keluar APK
// ============================================================
let _bgModeActive = false;

// ── BACKGROUND KEEP-ALIVE ────────────────────────────────────────────────────
// Re-apply visibility block setiap 5 detik saat musik jalan di Flutter APK
let _bgKeepAliveInterval = null;

function _applyVisibilityBlock() {
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
}

function _startBgKeepAlive() {
    _applyVisibilityBlock();
    if (window.flutter_inappwebview) return; // Flutter handles keepalive
    if (_bgKeepAliveInterval) clearInterval(_bgKeepAliveInterval);
    _bgKeepAliveInterval = setInterval(_applyVisibilityBlock, 5000);
}

function _stopBgKeepAlive() {
    if (_bgKeepAliveInterval) { clearInterval(_bgKeepAliveInterval); _bgKeepAliveInterval = null; }
}


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

// ============================================================
// ADMIN ANNOUNCEMENT — hanya untuk yusrilrizky149@gmail.com
// ============================================================
const ADMIN_EMAIL = 'yusrilrizky149@gmail.com';

function isAdmin() {
    const user = getGoogleUser();
    return user && user.email === ADMIN_EMAIL;
}

function openAnnouncementPanel() {
    if (!isAdmin()) { showToast('Hanya admin yang bisa mengakses fitur ini'); return; }
    const modal = document.getElementById('announcementModal');
    if (modal) modal.style.display = 'flex';
}

function closeAnnouncementPanel() {
    const modal = document.getElementById('announcementModal');
    if (modal) modal.style.display = 'none';
}

// Tulis announcement via Firestore REST API — langsung pakai API key, tidak butuh auth token
const _FS_ANN_URL = 'https://firestore.googleapis.com/v1/projects/auspoty-web/databases/(default)/documents/announcements/current?key=AIzaSyAYJEVXTS17vEX4J6_ymevMiJUnWV-Xf8Q';

async function _writeAnnouncementREST(fields) {
    const res = await fetch(_FS_ANN_URL, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields })
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error?.message || 'HTTP ' + res.status);
    }
    return res.json();
}

async function sendAnnouncement() {
    if (!isAdmin()) { showToast('Unauthorized'); return; }
    const title   = document.getElementById('annTitle').value.trim();
    const message = document.getElementById('annMessage').value.trim();
    const type    = document.getElementById('annType').value;
    if (!title || !message) { showToast('Judul dan pesan wajib diisi'); return; }
    const btn = document.getElementById('annSendBtn');
    if (btn) { btn.disabled = true; btn.innerText = 'Mengirim...'; }
    try {
        await _writeAnnouncementREST({
            status:  { stringValue: 'success' },
            id:      { stringValue: Date.now().toString() },
            title:   { stringValue: title },
            message: { stringValue: message },
            type:    { stringValue: type }
        });
        showToast('Pengumuman berhasil dikirim ke semua pengguna!');
        closeAnnouncementPanel();
        document.getElementById('annTitle').value = '';
        document.getElementById('annMessage').value = '';
    } catch(e) {
        showToast('Gagal kirim: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerText = 'Kirim Pengumuman'; }
    }
}

async function clearAnnouncement() {
    if (!isAdmin()) return;
    try {
        await _writeAnnouncementREST({
            status:  { stringValue: 'none' },
            id:      { stringValue: '' },
            title:   { stringValue: '' },
            message: { stringValue: '' },
            type:    { stringValue: 'info' }
        });
        showToast('Pengumuman dihapus');
    } catch(e) { showToast('Gagal hapus: ' + e.message); }
}

// Tampilkan tombol admin di settings jika login sebagai admin
function updateAdminUI() {
    const btn = document.getElementById('adminAnnouncementBtn');
    if (!btn) return;
    btn.style.display = isAdmin() ? 'block' : 'none';
}

// ============================================================
// SOCIAL FEATURES — Profil, Follow, Cari Pengguna, Pesan Pribadi
// ============================================================

// Simpan/update profil pengguna ke Firestore saat login
async function syncUserProfile() {
    const user = getGoogleUser();
    if (!user || !window._firestoreDB) return;
    try {
        const ref = window._fsDoc(window._firestoreDB, 'users', user.email);
        const existing = await window._fsGetDoc(ref);
        const existingData = existing.exists() ? existing.data() : {};
        // Ambil history lokal untuk disimpan ke profil (aktivitas publik)
        const localHistory = JSON.parse(localStorage.getItem('auspotyHistory') || '[]').slice(0, 5);
        await window._fsSetDoc(ref, {
            email: user.email,
            name: user.name,
            picture: user.picture || '',
            updatedAt: window._fsTimestamp(),
            username: existingData.username || '',
            recentHistory: localHistory
        }, { merge: true });
        _usersCacheLoaded = false;
        _usersCache = null;
    } catch(e) { console.error('syncUserProfile error:', e); }
}

// Lihat profil pengguna lain — gunakan view user-profile yang sudah ada
// (fungsi viewUserProfile sudah didefinisikan di atas, ini hanya alias)
function closeUserProfile() {
    document.getElementById('userProfileModal').style.display = 'none';
}

// Follow / Unfollow (versi modal — alias ke toggleFollowUser)
async function toggleFollow(targetEmail) {
    window._viewingUser = window._viewingUser || { email: targetEmail };
    await toggleFollowUser();
}

// Cari pengguna
function openSearchUsers() {
    document.getElementById('searchUsersModal').style.display = 'flex';
    document.getElementById('searchUserInput').focus();
}
function closeSearchUsers() {
    document.getElementById('searchUsersModal').style.display = 'none';
}
async function searchUsers() {
    const rawQ = document.getElementById('searchUserInput').value.trim();
    const results = document.getElementById('searchUserResults');
    if (!rawQ) { results.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:16px;">Masukkan nama atau @username untuk dicari</div>'; return; }
    results.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:16px;">Mencari...</div>';
    try {
        const users = await _ensureUsersCache();
        const isTagSearch = rawQ.startsWith('@');
        const ql = isTagSearch ? rawQ.slice(1).toLowerCase() : rawQ.toLowerCase();
        const usersFiltered = users.filter(u => {
            if (isTagSearch) return (u.username || '').toLowerCase().includes(ql);
            return (u.name || '').toLowerCase().includes(ql) ||
                   (u.username || '').toLowerCase().includes(ql) ||
                   (u.email || '').toLowerCase().includes(ql);
        });
        const usersTop = usersFiltered.slice(0, 40);
        if (!usersTop.length) { results.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:16px;">Tidak ada pengguna ditemukan</div>'; return; }
        results.innerHTML = usersTop.map(u =>
            '<div onclick="viewUserProfile(\'' + u.email + '\')" style="display:flex;align-items:center;gap:12px;padding:12px;border-radius:12px;background:rgba(255,255,255,0.05);margin-bottom:8px;cursor:pointer;">' +
            '<div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;color:#fff;overflow:hidden;flex-shrink:0;">' +
            (u.picture ? '<img src="' + u.picture + '" style="width:100%;height:100%;object-fit:cover;">' : (u.name||'?').charAt(0).toUpperCase()) +
            '</div>' +
            '<div><div style="font-size:14px;font-weight:700;color:white;">' + (u.name||'') + (u.username ? ' <span style="color:var(--accent);font-size:12px;">@' + u.username + '</span>' : '') + '</div>' +
            '<div style="font-size:12px;color:var(--text-sub);">' + u.email + '</div></div>' +
            '</div>'
        ).join('');
    } catch(e) { results.innerHTML = '<div style="color:#ff5252;text-align:center;padding:16px;">Gagal: ' + e.message + '</div>'; }
}

// Pesan Pribadi (DM)
let _dmTarget = null;
function openDM(email, name) {
    _dmTarget = { email, name };
    document.getElementById('dmTitle').innerText = name;
    document.getElementById('dmSubtitle').innerText = email;
    document.getElementById('dmModal').style.display = 'flex';
    document.getElementById('userProfileModal').style.display = 'none';
    loadDMMessages();
}
function closeDM() {
    document.getElementById('dmModal').style.display = 'none';
    _dmTarget = null;
}

function _getDMId(a, b) {
    return [a, b].sort().join('__');
}

async function loadDMMessages() {
    if (!_dmTarget) return;
    const me = getGoogleUser();
    if (!me) return;
    const container = document.getElementById('dmMessages');
    container.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:16px;font-size:13px;">Memuat pesan...</div>';
    try {
        const convId = _getDMId(me.email, _dmTarget.email);
        const q = window._fsQuery(
            window._fsCollection(window._firestoreDB, 'messages'),
            window._fsWhere('convId', '==', convId)
        );
        const snap = await window._fsGetDocs(q);
        if (snap.empty) { container.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:16px;font-size:13px;">Belum ada pesan. Mulai percakapan!</div>'; return; }
        // Sort di client untuk hindari Firestore index requirement
        const msgs = snap.docs.map(d => d.data()).sort((a, b) => (a.createdAt ? a.createdAt.seconds : 0) - (b.createdAt ? b.createdAt.seconds : 0));
        container.innerHTML = msgs.map(msg => {
            const isMine = msg.from === me.email;
            const time = msg.createdAt ? new Date(msg.createdAt.seconds * 1000).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) : '';
            return '<div style="display:flex;justify-content:' + (isMine ? 'flex-end' : 'flex-start') + ';margin-bottom:8px;">' +
                '<div style="max-width:75%;background:' + (isMine ? 'linear-gradient(135deg,var(--accent),var(--accent2))' : 'rgba(255,255,255,0.1)') + ';border-radius:' + (isMine ? '16px 16px 4px 16px' : '16px 16px 16px 4px') + ';padding:10px 14px;">' +
                '<p style="font-size:14px;color:white;margin:0 0 4px;">' + msg.text + '</p>' +
                '<span style="font-size:10px;color:rgba(255,255,255,0.5);">' + time + '</span>' +
                '</div></div>';
        }).join('');
        container.scrollTop = container.scrollHeight;
    } catch(e) { container.innerHTML = '<div style="color:#ff5252;text-align:center;padding:16px;font-size:13px;">Gagal: ' + e.message + '</div>'; }
}

async function sendDM() {
    const me = getGoogleUser();
    if (!me || !_dmTarget) return;
    const input = document.getElementById('dmInput');
    const text = input.value.trim();
    if (!text) return;
    try {
        const convId = _getDMId(me.email, _dmTarget.email);
        await window._fsAddDoc(window._fsCollection(window._firestoreDB, 'messages'), {
            convId, from: me.email, to: _dmTarget.email,
            text, createdAt: window._fsTimestamp()
        });
        input.value = '';
        loadDMMessages();
    } catch(e) { showToast('Gagal kirim: ' + e.message); }
}

// Sync profil saat login
const _origUpdateProfileUI = typeof updateProfileUI === 'function' ? updateProfileUI : null;
if (_origUpdateProfileUI) {
    window.updateProfileUI = function() {
        _origUpdateProfileUI();
        syncUserProfile();
    };
}

// ============================================================
// ONLINE / OFFLINE DETECTION — auto refresh saat kembali online
// ============================================================
let _wasOffline = false;
window.addEventListener('online', function() {
    if (_wasOffline) {
        _wasOffline = false;
        showToast('Kembali online! Memuat ulang...');
        setTimeout(function() {
            loadHomeData();
            // Reload ytPlayer jika ada lagu yang sedang diputar
            if (currentTrack && !window._localAudioPlaying && ytPlayer && ytPlayer.loadVideoById) {
                ytPlayer.loadVideoById(currentTrack.videoId);
            }
        }, 1000);
    }
});
window.addEventListener('offline', function() {
    _wasOffline = true;
    showToast('Koneksi terputus. Mode offline aktif.');
});
function openDMView(email, name) {
    // Tutup modal profil jika ada
    const profileModal = document.getElementById('userProfileModal');
    if (profileModal) profileModal.style.display = 'none';
    // Set target dan buka chat view
    _dmTarget = { email, name };
    const chatName = document.getElementById('chatName');
    const chatAvatar = document.getElementById('chatAvatar');
    if (chatName) chatName.innerText = name;
    if (chatAvatar) {
        chatAvatar.innerHTML = '';
        chatAvatar.innerText = name.charAt(0).toUpperCase();
    }
    switchView('chat');
    loadDMMessages();
    if (_chatInterval) clearInterval(_chatInterval);
    _chatInterval = setInterval(() => loadDMMessages(), 5000);
}

// Set username (@tag) pengguna
async function saveUsername(username) {
    const user = getGoogleUser();
    if (!user) { showToast('Login dulu'); return; }
    const clean = username.replace(/[^a-zA-Z0-9_]/g, '').toLowerCase();
    if (clean.length < 3) { showToast('Username minimal 3 karakter'); return; }
    try {
        // Cek apakah username sudah dipakai
        const snap = await window._fsGetDocs(window._fsQuery(window._fsCollection(window._firestoreDB, 'users'), window._fsWhere('username', '==', clean)));
        if (!snap.empty && snap.docs[0].data().email !== user.email) { showToast('Username sudah dipakai'); return; }
        await window._fsSetDoc(window._fsDoc(window._firestoreDB, 'users', user.email), { username: clean }, { merge: true });
        _usersCacheLoaded = false; _usersCache = null;
        showToast('@' + clean + ' berhasil disimpan!');
    } catch(e) { showToast('Gagal simpan username: ' + e.message); }
}
