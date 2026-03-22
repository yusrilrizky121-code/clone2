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
const dbReq = indexedDB.open('AuspotyDB', 1);
dbReq.onupgradeneeded = (e) => {
    db = e.target.result;
    if (!db.objectStoreNames.contains('playlists')) db.createObjectStore('playlists', { keyPath: 'id' });
    if (!db.objectStoreNames.contains('liked_songs')) db.createObjectStore('liked_songs', { keyPath: 'videoId' });
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
        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        _setArtPlaying(true);
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        // APK mode: onMusicPlaying sudah dipanggil dari playMusic(), tidak perlu di sini
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
    updateMediaSession();

    document.getElementById('miniPlayer').style.display = 'flex';
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
    document.getElementById('totalTime').innerText = '0:00';

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
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
}

function updatePlayPauseBtn(playing) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (mainBtn) mainBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
    if (miniBtn) miniBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
}

function expandPlayer() { document.getElementById('playerModal').style.display = 'flex'; }
function minimizePlayer() { document.getElementById('playerModal').style.display = 'none'; }

function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
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
}
function stopProgressBar() { clearInterval(progressInterval); }
function seekTo(value) {
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
    if (songHistory.length < 2) { showToast('Tidak ada lagu sebelumnya'); return; }
    songHistory.pop();
    const prev = songHistory[songHistory.length - 1];
    if (prev) playMusic(prev.videoId, makeTrackData(prev));
}
function playNextSong() { playNextSimilarSong(); }

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
    lyricsScrollInterval = setInterval(function() {
        var cur = 0, dur = 0;
        if (ytPlayer && ytPlayer.getCurrentTime) {
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
        if (idx === currentHighlightIdx) return;
        currentHighlightIdx = idx;
        lyricsLines.forEach(function(_, i) {
            var el = document.getElementById('lyric-line-' + i);
            if (el) el.className = 'lyric-line' + (i === idx ? ' lyric-active' : (i < idx ? ' lyric-past' : ''));
        });
        var activeLine = document.getElementById('lyric-line-' + idx);
        if (activeLine) {
            var lb = document.getElementById('lyricsBody');
            if (lb) lb.scrollTop = activeLine.offsetTop - (lb.clientHeight / 2) + (activeLine.offsetHeight / 2);
        }
    }, 300);
}
function stopLyricsScroll() { clearInterval(lyricsScrollInterval); lyricsScrollInterval = null; }
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
    const t = window._trackCache[videoId];
    if (t) playMusic(t.videoId, makeTrackData(t));
}
function renderVItem(t) {
    _cacheTrack(t);
    return '<div class="v-item" onclick="playMusicById(\'' + t.videoId + '\')">' +
        '<img loading="lazy" class="v-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '" onerror="this.src=\'https://via.placeholder.com/48x48?text=music\'">' +
        '<div class="v-info"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div></div>';
}
function renderHCard(t) {
    _cacheTrack(t);
    return '<div class="h-card" onclick="playMusicById(\'' + t.videoId + '\')">' +
        '<img loading="lazy" class="h-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '" onerror="this.src=\'https://via.placeholder.com/140x140?text=music\'">' +
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
    if (recentEl) {
        try {
            const res = await apiFetch('/api/search?query=lagu+populer+indonesia');
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) recentEl.innerHTML = result.data.slice(0, 6).map(renderVItem).join('');
        } catch(e) { recentEl.innerHTML = '<div style="color:var(--text-sub);padding:8px;">Gagal memuat.</div>'; }
    }
    const artistEl = document.getElementById('rowArtists');
    if (artistEl) artistEl.innerHTML = ARTISTS.map(renderArtistCard).join('');
    applyLanguageTitles();
    // Lazy load: 2 rows at a time to avoid hammering API and blocking main thread
    const rows = getHomeQueries();
    async function loadRow(row) {
        const el = document.getElementById(row.id); if (!el) return;
        el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Memuat...</div>';
        try {
            const res = await apiFetch('/api/search?query=' + encodeURIComponent(row.query));
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) el.innerHTML = result.data.slice(0, 8).map(renderHCard).join('');
            else el.innerHTML = '';
        } catch(e) { el.innerHTML = ''; }
    }
    // Load first 2 rows immediately, rest after 800ms delay
    for (let i = 0; i < rows.length; i++) {
        if (i < 2) { loadRow(rows[i]); }
        else { setTimeout(() => loadRow(rows[i]), 800 + (i - 2) * 400); }
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
document.addEventListener('DOMContentLoaded', function() {
    const inp = document.getElementById('searchInput');
    if (inp) {
        let searchTimer;
        inp.addEventListener('input', function() {
            const q = this.value.trim();
            if (!q) { document.getElementById('searchCategoriesUI').style.display = 'block'; document.getElementById('searchResultsUI').style.display = 'none'; return; }
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => doSearch(q), 500);
        });
    }
});
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
    };
}

// LIBRARY
function renderLibraryUI() {
    const container = document.getElementById('libraryContainer'); if (!container || !db) return;
    const tx = db.transaction(['liked_songs', 'playlists'], 'readonly');
    let liked = [], playlists = [];
    tx.objectStore('liked_songs').getAll().onsuccess = (e) => { liked = e.target.result || []; };
    tx.objectStore('playlists').getAll().onsuccess = (e) => { playlists = e.target.result || []; };
    tx.oncomplete = () => {
        const history = JSON.parse(localStorage.getItem('auspotyHistory') || '[]');
        let html = '';
        html += '<div class="lib-item" onclick="openLikedSongs()"><div class="lib-item-img liked"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Lagu yang Disukai</div><div class="lib-item-sub">Playlist \u00b7 ' + liked.length + ' lagu</div></div></div>';
        html += '<div class="lib-item" onclick="openHistoryView()"><div class="lib-item-img" style="background:linear-gradient(135deg,#1e3264,#477d95);display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Riwayat Diputar</div><div class="lib-item-sub">Koleksi \u00b7 ' + history.length + ' lagu</div></div></div>';
        html += '<div class="lib-item" onclick="showToast(\'Fitur unduhan segera hadir!\')"><div class="lib-item-img" style="background:linear-gradient(135deg,#2d6a4f,#739c18);display:flex;align-items:center;justify-content:center;"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg></div><div class="lib-item-info"><div class="lib-item-title">Lagu Diunduh</div><div class="lib-item-sub">Koleksi \u00b7 Segera hadir</div></div></div>';
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
    document.getElementById('editProfileModal').style.display = 'flex';
}
function closeEditProfile() { document.getElementById('editProfileModal').style.display = 'none'; }
function saveProfile() {
    const name = document.getElementById('editProfileName').value.trim() || 'Pengguna Auspoty';
    saveSettings({ profileName: name }); applyAllSettings(); updateProfileUI(); closeEditProfile(); showToast('Profil disimpan!');
}
function triggerPhotoUpload() { document.getElementById('profilePhotoInput').click(); }
function handleProfilePhotoChange(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result;
        localStorage.setItem('auspotyProfilePhoto', base64);
        const av = document.getElementById('editProfileAvatar'); if (av) av.innerHTML = '<img src="' + base64 + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
        const settAv = document.getElementById('settingsAvatar'); if (settAv) settAv.innerHTML = '<img src="' + base64 + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
        const homeAv = document.querySelector('.app-avatar'); if (homeAv) homeAv.innerHTML = '<img src="' + base64 + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
        showToast('Foto profil diperbarui!');
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
    // APK mode: download via Flutter native handler (background, no browser)
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
        .then(function(res) { if (!res.ok) throw new Error('failed'); return res.blob(); })
        .then(function(blob) {
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url; a.download = (currentTrack.title || 'music') + '.mp3';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
            showToast('Unduhan selesai!');
        })
        .catch(function() { showToast('Gagal mengunduh'); });
}

// GOOGLE AUTH
function getGoogleUser() { try { return JSON.parse(localStorage.getItem('auspotyGoogleUser') || 'null'); } catch(e) { return null; } }
function loginWithGoogle() {
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
    const pic  = user ? user.picture : (localStorage.getItem('auspotyProfilePhoto') || '');
    const pname = document.getElementById('settingsProfileName'); if (pname) pname.innerText = name;
    const psub = document.getElementById('settingsProfileSub'); if (psub) psub.innerText = user ? user.email : 'Auspoty Premium';
    const pav = document.getElementById('settingsAvatar');
    if (pav) { if (pic) pav.innerHTML = '<img src="' + pic + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'; else { pav.innerHTML = ''; pav.innerText = name.charAt(0).toUpperCase(); } }
    const hav = document.querySelector('.app-avatar');
    if (hav) { if (pic) hav.innerHTML = '<img src="' + pic + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">'; else { hav.innerHTML = ''; hav.innerText = name.charAt(0).toUpperCase(); } }
    const loginBtn = document.getElementById('googleLoginBtn'); if (loginBtn) loginBtn.style.display = user ? 'none' : 'block';
    const logoutBtn = document.getElementById('googleLogoutBtn'); if (logoutBtn) logoutBtn.style.display = user ? 'block' : 'none';
    const logoutSub = document.getElementById('googleLogoutSub'); if (logoutSub && user) logoutSub.innerText = user.email;
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
        const docs = snap.docs.map(doc => doc.data());
        docs.sort((a, b) => (b.createdAt ? b.createdAt.seconds : 0) - (a.createdAt ? a.createdAt.seconds : 0));
        list.innerHTML = docs.map(d => {
            const isAdmin = d.email === 'yusrilrizky149@gmail.com';
            const badge = isAdmin ? '<span style="background:linear-gradient(135deg,#a78bfa,#f472b6);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:6px;">ADMIN</span>' : '<span style="background:rgba(255,255,255,0.1);color:var(--text-sub);font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;margin-left:6px;">Pengguna</span>';
            const time = d.createdAt ? new Date(d.createdAt.seconds * 1000).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
            return '<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:12px;"><div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;overflow:hidden;">' + (d.picture ? '<img src="' + d.picture + '" style="width:100%;height:100%;object-fit:cover;">' : d.name.charAt(0).toUpperCase()) + '</div><div style="flex:1;background:rgba(255,255,255,0.06);border-radius:12px;padding:10px 14px;"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;flex-wrap:wrap;gap:4px;"><span style="font-size:13px;font-weight:700;color:var(--accent);">' + d.name + badge + '</span><span style="font-size:11px;color:var(--text-sub);">' + time + '</span></div><p style="font-size:14px;color:white;line-height:1.5;margin:0;">' + d.text + '</p></div></div>';
        }).join('');
    } catch(e) { list.innerHTML = '<div style="color:#ff5252;text-align:center;padding:20px;font-size:13px;">Gagal memuat: ' + e.message + '</div>'; }
}
async function submitComment() {
    const user = getGoogleUser(); if (!user) { showToast('Login dulu untuk berkomentar'); return; }
    if (!currentTrack) return;
    const input = document.getElementById('commentInput'); const text = input.value.trim();
    if (!text) { showToast('Komentar tidak boleh kosong'); return; }
    try {
        await window._fsAddDoc(window._fsCollection(window._firestoreDB, 'comments'), { videoId: currentTrack.videoId, name: user.name, email: user.email, picture: user.picture || '', text: text, createdAt: window._fsTimestamp() });
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
    applyAllSettings(); updateProfileUI(); loadHomeData(); renderSearchCategories();
});


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
