// APK VERSION - API calls ke Vercel
const API_BASE = "https://clone2-iyrr-git-master-yusrilrizky121-codes-projects.vercel.app";

// INDEXEDDB
let db;
const dbReq = indexedDB.open("AuspotyDB", 1);
dbReq.onupgradeneeded = (e) => {
    db = e.target.result;
    if (!db.objectStoreNames.contains('playlists')) db.createObjectStore('playlists', { keyPath: 'id' });
    if (!db.objectStoreNames.contains('liked_songs')) db.createObjectStore('liked_songs', { keyPath: 'videoId' });
};
dbReq.onsuccess = (e) => { db = e.target.result; renderLibraryUI(); };

// YOUTUBE PLAYER
let ytPlayer, isPlaying = false, currentTrack = null, progressInterval;
let nextTrackQueue = [];

function onYouTubeIframeAPIReady() {
    ytPlayer = new YT.Player('youtube-player', {
        height: '0', width: '0',
        events: { onReady: () => {}, onStateChange: onPlayerStateChange }
    });
}

function onPlayerStateChange(event) {
    const playPath = "M8 5v14l11-7z";
    const pausePath = "M6 19h4V5H6v14zm8-14v14h4V5h-4z";
    const mainBtn = document.getElementById('mainPlayBtn');
    const miniBtn = document.getElementById('miniPlayBtn');
    if (event.data == YT.PlayerState.PLAYING) {
        isPlaying = true;
        mainBtn.innerHTML = `<path d="${pausePath}"/>`;
        miniBtn.innerHTML = `<path d="${pausePath}"/>`;
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        // Pre-fetch next songs saat lagu mulai (masih foreground)
        setTimeout(prefetchNextSongs, 3000);
    } else if (event.data == YT.PlayerState.PAUSED) {
        isPlaying = false;
        mainBtn.innerHTML = `<path d="${playPath}"/>`;
        miniBtn.innerHTML = `<path d="${playPath}"/>`;
        stopProgressBar();
    } else if (event.data == YT.PlayerState.ENDED) {
        isPlaying = false;
        mainBtn.innerHTML = `<path d="${playPath}"/>`;
        miniBtn.innerHTML = `<path d="${playPath}"/>`;
        stopProgressBar();
        playNextSimilarSong();
    }
}

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

async function prefetchNextSongs() {
    if (!currentTrack) return;
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(currentTrack.artist + " official audio")}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            nextTrackQueue = result.data
                .filter(t => t.videoId !== currentTrack.videoId)
                .map(t => {
                    const img = getHighResImage(t.thumbnail || t.img || '');
                    return { videoId: t.videoId, title: t.title, artist: t.artist || 'Unknown', img };
                });
        }
    } catch (e) {}
}

async function playNextSimilarSong() {
    if (!currentTrack) return;
    if (nextTrackQueue.length > 0) {
        const next = nextTrackQueue.splice(Math.floor(Math.random() * nextTrackQueue.length), 1)[0];
        playMusic(next.videoId, encodeURIComponent(JSON.stringify(next)));
        setTimeout(prefetchNextSongs, 2000);
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(currentTrack.artist + " official audio")}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const related = result.data.filter(t => t.videoId !== currentTrack.videoId);
            if (related.length > 0) {
                const next = related[Math.floor(Math.random() * related.length)];
                const img = getHighResImage(next.thumbnail || next.img || '');
                playMusic(next.videoId, encodeURIComponent(JSON.stringify({ videoId: next.videoId, title: next.title, artist: next.artist || 'Unknown', img })));
            }
        }
    } catch (e) {}
}

function playMusic(videoId, encodedData) {
    currentTrack = JSON.parse(decodeURIComponent(encodedData));
    checkIfLiked(currentTrack.videoId);
    updateMediaSession();
    document.getElementById('miniPlayer').style.display = 'flex';
    document.getElementById('miniPlayerImg').src = currentTrack.img;
    document.getElementById('miniPlayerTitle').innerText = currentTrack.title;
    document.getElementById('miniPlayerArtist').innerText = currentTrack.artist;
    document.getElementById('playerArt').src = currentTrack.img;
    document.getElementById('playerTitle').innerText = currentTrack.title;
    document.getElementById('playerArtist').innerText = currentTrack.artist;
    document.getElementById('playerBg').style.backgroundImage = `url('${currentTrack.img}')`;
    document.getElementById('progressBar').value = 0;
    document.getElementById('currentTime').innerText = "0:00";
    document.getElementById('totalTime').innerText = "0:00";
    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);
}

function togglePlay() {
    if (!ytPlayer) return;
    isPlaying ? ytPlayer.pauseVideo() : ytPlayer.playVideo();
}

function expandPlayer() { document.getElementById('playerModal').style.display = 'flex'; }
function minimizePlayer() { document.getElementById('playerModal').style.display = 'none'; }

function formatTime(s) {
    const m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
}

function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (ytPlayer && ytPlayer.getCurrentTime && ytPlayer.getDuration) {
            const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration();
            if (dur > 0) {
                const pct = (cur / dur) * 100;
                const bar = document.getElementById('progressBar');
                bar.value = pct;
                bar.style.background = `linear-gradient(to right, white ${pct}%, rgba(255,255,255,0.2) ${pct}%)`;
                document.getElementById('currentTime').innerText = formatTime(cur);
                document.getElementById('totalTime').innerText = formatTime(dur);
            }
        }
    }, 1000);
}

function stopProgressBar() { clearInterval(progressInterval); }

function seekTo(value) {
    if (ytPlayer && ytPlayer.getDuration) {
        ytPlayer.seekTo((value / 100) * ytPlayer.getDuration(), true);
        document.getElementById('progressBar').style.background = `linear-gradient(to right, white ${value}%, rgba(255,255,255,0.2) ${value}%)`;
    }
}

// LYRICS
let lyricsLines = [], lyricsScrollInterval = null, currentHighlightIdx = -1, lyricsType = 'plain';

async function openLyricsModal() {
    if (!currentTrack) return;
    const modal = document.getElementById('lyricsModal');
    const lyricsBody = document.getElementById('lyricsBody');
    document.getElementById('lyricsTrackImg').src = currentTrack.img;
    document.getElementById('lyricsTrackTitle').innerText = currentTrack.title;
    document.getElementById('lyricsTrackArtist').innerText = currentTrack.artist;
    document.getElementById('lyricsBg').style.backgroundImage = `url('${currentTrack.img}')`;
    modal.style.display = 'flex';
    lyricsBody.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Menarik lirik...</div>';
    stopLyricsScroll();
    lyricsLines = []; currentHighlightIdx = -1;
    try {
        const res = await fetch(`${API_BASE}/api/lyrics?video_id=` + currentTrack.videoId);
        const result = await res.json();
        if (result.status === 'success' && result.data && result.data.lines && result.data.lines.length > 0) {
            lyricsLines = result.data.lines;
            lyricsType = result.data.type || 'plain';
            renderLyricsLines(lyricsBody);
            startLyricsScroll(lyricsBody);
        } else {
            lyricsBody.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Lirik belum tersedia untuk lagu ini.</div>';
        }
    } catch (e) {
        lyricsBody.innerHTML = '<div style="color:#ff5252;font-size:16px;text-align:center;margin-top:40px;">Gagal memuat lirik.</div>';
    }
}

function renderLyricsLines(lyricsBody) {
    let html = '<div style="height:45vh"></div>';
    lyricsLines.forEach((line, i) => {
        html += `<div class="lyric-line" id="lyric-line-${i}">${line.text}</div>`;
    });
    html += '<div style="height:45vh"></div>';
    lyricsBody.innerHTML = html;
}

function startLyricsScroll(lyricsBody) {
    stopLyricsScroll();
    lyricsScrollInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const cur = ytPlayer.getCurrentTime();
        const dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (!dur || dur <= 0 || lyricsLines.length === 0) return;
        let idx = 0;
        if (lyricsType === 'synced') {
            for (let i = 0; i < lyricsLines.length; i++) {
                if (lyricsLines[i].time !== null && lyricsLines[i].time <= cur) idx = i;
            }
        } else {
            idx = Math.min(Math.floor((cur / dur) * lyricsLines.length), lyricsLines.length - 1);
        }
        if (idx === currentHighlightIdx) return;
        currentHighlightIdx = idx;
        lyricsLines.forEach((_, i) => {
            const el = document.getElementById(`lyric-line-${i}`);
            if (!el) return;
            el.className = 'lyric-line' + (i === idx ? ' lyric-active' : (i < idx ? ' lyric-past' : ''));
        });
        const activeLine = document.getElementById(`lyric-line-${idx}`);
        if (activeLine) activeLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
}

function stopLyricsScroll() {
    if (lyricsScrollInterval) { clearInterval(lyricsScrollInterval); lyricsScrollInterval = null; }
}

function closeLyrics() {
    document.getElementById('lyricsModal').style.display = 'none';
    document.getElementById('lyricsBody').innerHTML = '';
    stopLyricsScroll(); lyricsLines = []; currentHighlightIdx = -1;
}

// BACKGROUND AUDIO
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        if (ytPlayer && ytPlayer.getPlayerState && ytPlayer.getPlayerState() === YT.PlayerState.PLAYING)
            sessionStorage.setItem('wasPlaying', 'true');
    } else {
        if (sessionStorage.getItem('wasPlaying') === 'true') {
            sessionStorage.removeItem('wasPlaying');
            if (ytPlayer && ytPlayer.getPlayerState && ytPlayer.getPlayerState() !== YT.PlayerState.PLAYING)
                ytPlayer.playVideo();
        }
    }
});

// TOAST
let toastTimeout;
function showToast(msg) {
    const t = document.getElementById('customToast');
    t.innerText = msg;
    t.classList.add('show');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => t.classList.remove('show'), 3000);
}

// NAVIGASI
function switchView(name) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
    document.querySelectorAll('.bottom-nav .nav-item').forEach(n => n.classList.remove('active'));
    const idx = { home: 0, search: 1, library: 2, developer: 3 };
    if (idx[name] !== undefined) document.querySelectorAll('.bottom-nav .nav-item')[idx[name]].classList.add('active');
    if (name === 'library') renderLibraryUI();
    window.scrollTo(0, 0);
}

// RENDER HELPERS
const dotsSvg = '<svg class="dots-icon" viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>';

function getHighResImage(url) {
    if (!url) return 'https://placehold.co/140x140/282828/FFFFFF?text=Music';
    if (url.match(/=w\d+-h\d+/)) return url.replace(/=w\d+-h\d+[^&]*/g, '=w512-h512-l90-rj');
    return url;
}

function createGridHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return `<div class="hg-item" onclick="playMusic('${track.videoId}','${data}')">
        <img src="${img}" class="hg-img" onerror="this.src='https://placehold.co/200x200/282828/FFFFFF?text=Music'">
        <div class="hg-title">${track.title}</div>
        <div class="hg-artist">${artist}</div>
    </div>`;
}

function createListHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return `<div class="v-item" onclick="playMusic('${track.videoId}','${data}')">
        <img src="${img}" class="v-img" onerror="this.src='https://placehold.co/48x48/282828/FFFFFF?text=Music'">
        <div class="v-info"><div class="v-title">${track.title}</div><div class="v-sub">${artist}</div></div>
        ${dotsSvg}
    </div>`;
}

function createCardHTML(track, isArtist = false) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    const click = isArtist ? `openArtistView('${track.title}')` : `playMusic('${track.videoId}','${data}')`;
    return `<div class="h-card" onclick="${click}">
        <img src="${img}" class="h-img${isArtist ? ' artist-img' : ''}" onerror="this.src='https://placehold.co/140x140/282828/FFFFFF?text=Music'">
        <div class="h-title">${track.title}</div>
        <div class="h-sub">${isArtist ? 'Artis' : artist}</div>
    </div>`;
}

function createTrackGridHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return `<div class="tg-item" onclick="playMusic('${track.videoId}','${data}')">
        <img src="${img}" class="tg-img" onerror="this.src='https://placehold.co/46x46/282828/FFFFFF?text=Music'">
        <div class="tg-info"><div class="tg-title">${track.title}</div><div class="tg-artist">${artist}</div></div>
    </div>`;
}

function createCardRowHTML(track, isArtist = false) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    const click = isArtist ? `openArtistView('${track.title}')` : `playMusic('${track.videoId}','${data}')`;
    return `<div class="cr-card" onclick="${click}">
        <img src="${img}" class="cr-img${isArtist ? ' circle' : ''}" onerror="this.src='https://placehold.co/148x148/282828/FFFFFF?text=Music'">
        <div class="cr-title">${track.title}</div>
        <div class="cr-sub">${isArtist ? 'Artis' : artist}</div>
    </div>`;
}

function createRankHTML(track, num) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    const numClass = num === 1 ? 'rank-num gold' : num === 2 ? 'rank-num silver' : num === 3 ? 'rank-num bronze' : 'rank-num';
    return `<div class="rank-item" onclick="playMusic('${track.videoId}','${data}')">
        <div class="${numClass}">${num}</div>
        <img src="${img}" class="rank-img" onerror="this.src='https://placehold.co/52x52/282828/FFFFFF?text=Music'">
        <div class="rank-info"><div class="rank-title">${track.title}</div><div class="rank-artist">${artist}</div></div>
    </div>`;
}

function renderSection(tracks, id, type, isArtist = false) {
    const el = document.getElementById(id);
    if (!el || !tracks || tracks.length === 0) return;
    el.innerHTML = tracks.map(t => type === 'list' ? createListHTML(t) : createCardHTML(t, isArtist)).join('');
}

async function fetchSection(query, id, type, isArtist = false, limit = 8) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) renderSection(result.data, id, type, isArtist);
    } catch (e) {}
}

async function fetchTrackGrid(query, id, limit = 6) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = result.data.map(t => createTrackGridHTML(t)).join('');
        }
    } catch (e) {}
}

async function fetchCardRow(query, id, isArtist = false, limit = 8) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = result.data.map(t => createCardRowHTML(t, isArtist)).join('');
        }
    } catch (e) {}
}

async function fetchRankList(query, id, limit = 5) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = result.data.map((t, i) => createRankHTML(t, i + 1)).join('');
        }
    } catch (e) {}
}

// HERO BANNER
let heroTrack = null;

function playHeroTrack() {
    if (!heroTrack) return;
    const img = getHighResImage(heroTrack.thumbnail || heroTrack.img || '');
    playMusic(heroTrack.videoId, encodeURIComponent(JSON.stringify({ videoId: heroTrack.videoId, title: heroTrack.title, artist: heroTrack.artist || 'Unknown', img })));
}

async function loadHeroBanner() {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=lagu indonesia hits terbaru&limit=10`);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            heroTrack = result.data[Math.floor(Math.random() * Math.min(5, result.data.length))];
            const img = getHighResImage(heroTrack.thumbnail || heroTrack.img || '');
            document.getElementById('heroBg').style.backgroundImage = `url('${img}')`;
            document.getElementById('heroTitle').innerText = heroTrack.title;
            document.getElementById('heroArtist').innerText = heroTrack.artist || 'Unknown';
        }
    } catch (e) {}
}

function renderGenreGrid() {
    const genres = [
        { label: 'Pop', emoji: '🎸', color: '#e8115b', q: 'lagu pop indonesia' },
        { label: 'Indie', emoji: '💿', color: '#477d95', q: 'lagu indie indonesia' },
        { label: 'R&B', emoji: '🎤', color: '#8d67ab', q: 'rnb indonesia hits' },
        { label: 'TikTok', emoji: '🔥', color: '#e1118c', q: 'lagu fyp tiktok viral' },
        { label: 'Galau', emoji: '😢', color: '#1e3264', q: 'lagu galau sedih' },
        { label: 'K-Pop', emoji: '🌏', color: '#739c18', q: 'kpop hits terbaru' },
        { label: 'Dangdut', emoji: '🥁', color: '#c84b31', q: 'dangdut hits indonesia' },
        { label: 'Jazz', emoji: '🎷', color: '#2d6a4f', q: 'jazz indonesia relax' },
        { label: 'Rock', emoji: '🤘', color: '#3d3d3d', q: 'rock indonesia hits' },
    ];
    document.getElementById('genreGrid').innerHTML = genres.map(g =>
        `<div class="gt-card" style="background:${g.color};" onclick="searchByCategory('${g.q}')">
            <span class="gt-emoji">${g.emoji}</span>
            <span class="gt-label">${g.label}</span>
        </div>`
    ).join('');
}

function filterMood(el, query, id) {
    document.querySelectorAll('.chip').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    const list = document.getElementById(id);
    if (list) list.innerHTML = '<div style="color:var(--text-sub);font-size:13px;padding:16px;">Memuat...</div>';
    fetchTrackGrid(query, id, 6);
}

// HOME: Apple Music style sections
async function fetchAndRenderGrid(query, id, limit = 6) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        const el = document.getElementById(id);
        if (result.status === 'success' && result.data.length > 0 && el) {
            el.innerHTML = result.data.map(t => createGridHTML(t)).join('');
        }
    } catch (e) {}
}

async function fetchAndRenderRow(query, id, limit = 8) {
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        const result = await res.json();
        const el = document.getElementById(id);
        if (result.status === 'success' && result.data.length > 0 && el) {
            el.innerHTML = result.data.map(t => createRowHTML(t)).join('');
        }
    } catch (e) {}
}

function createGridHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return `<div class="am-grid-item" onclick="playMusic('${track.videoId}','${data}')">
        <img src="${img}" class="am-grid-img" onerror="this.src='https://placehold.co/300x300/1c1c1e/FFFFFF?text=Music'">
        <div class="am-grid-title">${track.title}</div>
        <div class="am-grid-artist">${artist}</div>
    </div>`;
}

function createRowHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return `<div class="am-row-card" onclick="playMusic('${track.videoId}','${data}')">
        <img src="${img}" class="am-row-img" onerror="this.src='https://placehold.co/140x140/1c1c1e/FFFFFF?text=Music'">
        <div class="am-row-title">${track.title}</div>
        <div class="am-row-artist">${artist}</div>
    </div>`;
}

function loadHomeData() {
    loadHeroBanner();
    fetchAndRenderGrid('lagu indonesia hits terbaru', 'homeGrid1', 6);
    fetchAndRenderRow('hit terpopuler hari ini', 'homeRow1', 8);
    fetchAndRenderGrid('lagu fyp tiktok viral', 'homeGrid2', 6);
    fetchAndRenderRow('lagu galau sedih indonesia', 'homeRow2', 8);
}

// DEAD CODE KEPT FOR COMPAT
function _oldLoadHomeData() {
    const seen = new Set();
    const container = document.getElementById('homeList');
    if (container) container.innerHTML = '<div style="color:var(--text2);text-align:center;padding:32px;font-size:14px;grid-column:1/-1;">Memuat lagu...</div>';
    let allTracks = [], done = 0;
    queries.forEach(q => {
        fetch(`${API_BASE}/api/search?query=${encodeURIComponent(q)}&limit=8`)
            .then(r => r.json())
            .then(result => {
                if (result.status === 'success') {
                    result.data.forEach(t => {
                        if (!seen.has(t.videoId)) { seen.add(t.videoId); allTracks.push(t); }
                    });
                }
            })
            .catch(() => {})
            .finally(() => {
                done++;
                if (done === queries.length && container) {
                    container.innerHTML = allTracks.length
                        ? allTracks.map(t => createGridHTML(t)).join('')
                        : '<div style="color:var(--text2);text-align:center;padding:32px;grid-column:1/-1;">Gagal memuat lagu.</div>';
                }
            });
    });
}

// SEARCH
function renderSearchCategories() {
    const cats = [
        { title: 'Dibuat Untuk Kamu', color: '#8d67ab', img: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=100&q=80' },
        { title: 'Rilis Baru', color: '#739c18', img: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100&q=80' },
        { title: 'Pop', color: '#477d95', img: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=100&q=80' },
        { title: 'Indie', color: '#e1118c', img: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=100&q=80' },
        { title: 'Musik Indonesia', color: '#e8115b', img: 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=100&q=80' },
        { title: 'Tangga Lagu', color: '#8d67ab', img: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=100&q=80' },
        { title: 'K-pop', color: '#e8115b', img: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=100&q=80' },
        { title: 'Viral TikTok', color: '#1e3264', img: 'https://images.unsplash.com/photo-1593697821252-0c9137d9fc45?w=100&q=80' }
    ];
    document.getElementById('categoryGrid').innerHTML = cats.map(c =>
        `<div class="category-card" style="background:${c.color};" onclick="searchByCategory('${c.title}')">
            <div class="category-title">${c.title}</div>
            <img src="${c.img}" class="category-img">
        </div>`
    ).join('');
}

function searchByCategory(title) {
    switchView('search');
    document.getElementById('searchInput').value = title;
    document.getElementById('searchInput').dispatchEvent(new Event('input'));
}

let searchTimeout;
document.getElementById('searchInput').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (!q) {
        document.getElementById('searchCategoriesUI').style.display = 'block';
        document.getElementById('searchResultsUI').style.display = 'none';
        return;
    }
    document.getElementById('searchCategoriesUI').style.display = 'none';
    document.getElementById('searchResultsUI').style.display = 'block';
    searchTimeout = setTimeout(async () => {
        document.getElementById('searchResults').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Mencari...</div>';
        try {
            const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(q)}`);
            const result = await res.json();
            if (result.status === 'success')
                document.getElementById('searchResults').innerHTML = result.data.map(t => createListHTML(t)).join('');
        } catch (e) {}
    }, 600);
});

// ARTIST
async function openArtistView(name) {
    document.getElementById('artistNameDisplay').innerText = name;
    document.getElementById('artistTracksContainer').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Memuat...</div>';
    switchView('artist');
    try {
        const res = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(name + " official audio")}`);
        const result = await res.json();
        if (result.status === 'success') {
            document.getElementById('artistTracksContainer').innerHTML = result.data.map(t => createListHTML(t)).join('');
            if (result.data.length > 0) {
                const f = result.data[0];
                const img = getHighResImage(f.thumbnail || f.img || '');
                const data = encodeURIComponent(JSON.stringify({ videoId: f.videoId, title: f.title, artist: f.artist || 'Unknown', img }));
                document.querySelector('.artist-play-btn').setAttribute('onclick', `playMusic('${f.videoId}','${data}')`);
            }
        }
    } catch (e) {}
}

function playFirstArtistTrack() {}

// LIKE
function checkIfLiked(videoId) {
    if (!db) return;
    const req = db.transaction("liked_songs", "readonly").objectStore("liked_songs").get(videoId);
    req.onsuccess = () => {
        const liked = !!req.result;
        ['btnLikeSong', 'btnLikeLyric'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.fill = liked ? '#1ed760' : 'white';
        });
    };
}

function toggleLike() {
    if (!currentTrack || !db) return;
    const store = db.transaction("liked_songs", "readwrite").objectStore("liked_songs");
    const req = store.get(currentTrack.videoId);
    req.onsuccess = () => {
        if (req.result) {
            store.delete(currentTrack.videoId);
            ['btnLikeSong', 'btnLikeLyric'].forEach(id => { const el = document.getElementById(id); if (el) el.style.fill = 'white'; });
            showToast('Dihapus dari Lagu Disukai');
        } else {
            store.put(currentTrack);
            ['btnLikeSong', 'btnLikeLyric'].forEach(id => { const el = document.getElementById(id); if (el) el.style.fill = '#1ed760'; });
            showToast('Ditambahkan ke Lagu Disukai');
        }
        renderLibraryUI();
    };
}

// LIBRARY
function renderLibraryUI() {
    if (!db) return;
    const container = document.getElementById('libraryContainer');
    const req = db.transaction("liked_songs", "readonly").objectStore("liked_songs").getAll();
    req.onsuccess = () => {
        let html = `<div class="lib-item" onclick="openPlaylistView('liked')">
            <div class="lib-item-img liked"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div>
            <div class="lib-item-info">
                <div class="lib-item-title">Lagu yang Disukai</div>
                <div class="lib-item-sub">Playlist • ${req.result.length} lagu</div>
            </div>
        </div>`;
        const reqP = db.transaction("playlists", "readonly").objectStore("playlists").getAll();
        reqP.onsuccess = () => {
            reqP.result.forEach(p => {
                html += `<div class="lib-item" onclick="openPlaylistView('${p.id}')">
                    <img src="${p.img || 'https://via.placeholder.com/64?text=+'}" class="lib-item-img" onerror="this.src='https://via.placeholder.com/64?text=+'">
                    <div class="lib-item-info">
                        <div class="lib-item-title">${p.name}</div>
                        <div class="lib-item-sub">Playlist • ${(p.tracks || []).length} lagu</div>
                    </div>
                </div>`;
            });
            html += `<div class="lib-item">
                <div class="lib-item-img add-btn add-btn-sq"><svg viewBox="0 0 24 24" style="fill:white;width:32px;height:32px;"><path d="M11 11V4h2v7h7v2h-7v7h-2v-7H4v-2h7z"/></svg></div>
                <div class="lib-item-info"><div class="lib-item-title">Buat Playlist Baru</div></div>
            </div>`;
            container.innerHTML = html;
        };
    };
}

let currentPlaylistTracks = [];

function openPlaylistView(id) {
    switchView('playlist');
    document.getElementById('playlistTracksContainer').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Memuat...</div>';
    if (id === 'liked') {
        document.getElementById('playlistNameDisplay').innerText = "Lagu yang Disukai";
        document.getElementById('playlistImageDisplay').src = "https://via.placeholder.com/200/450af5/ffffff?text=♥";
        const req = db.transaction("liked_songs", "readonly").objectStore("liked_songs").getAll();
        req.onsuccess = () => {
            currentPlaylistTracks = req.result;
            document.getElementById('playlistStatsDisplay').innerText = `${req.result.length} lagu`;
            renderTracksInPlaylist(req.result);
        };
    } else {
        const req = db.transaction("playlists", "readonly").objectStore("playlists").get(id);
        req.onsuccess = () => {
            const p = req.result;
            currentPlaylistTracks = p.tracks || [];
            document.getElementById('playlistNameDisplay').innerText = p.name;
            document.getElementById('playlistImageDisplay').src = p.img || 'https://via.placeholder.com/200/282828/ffffff?text=+';
            document.getElementById('playlistStatsDisplay').innerText = `${currentPlaylistTracks.length} lagu`;
            renderTracksInPlaylist(currentPlaylistTracks);
        };
    }
}

function playFirstPlaylistTrack() {
    if (currentPlaylistTracks.length > 0) {
        const t = currentPlaylistTracks[0];
        playMusic(t.videoId, encodeURIComponent(JSON.stringify(t)));
    }
}

function renderTracksInPlaylist(tracks) {
    const c = document.getElementById('playlistTracksContainer');
    c.innerHTML = tracks.length ? tracks.map(t => createListHTML(t)).join('') : '<div style="color:var(--text-sub);text-align:center;padding:20px;">Playlist kosong.</div>';
}

let base64Img = '';
function openCreatePlaylist() { document.getElementById('createPlaylistModal').style.display = 'block'; }
function closeCreatePlaylist() {
    document.getElementById('createPlaylistModal').style.display = 'none';
    document.getElementById('cpName').value = '';
    document.getElementById('cpPreview').src = 'https://via.placeholder.com/120x120?text=+';
    base64Img = '';
}
function previewImage(e) {
    const reader = new FileReader();
    reader.onloadend = () => { document.getElementById('cpPreview').src = reader.result; base64Img = reader.result; };
    if (e.target.files[0]) reader.readAsDataURL(e.target.files[0]);
}
function saveNewPlaylist() {
    const name = document.getElementById('cpName').value || "Playlist baruku";
    const p = { id: Date.now().toString(), name, img: base64Img, tracks: [] };
    const tx = db.transaction("playlists", "readwrite");
    tx.objectStore("playlists").put(p);
    tx.oncomplete = () => { closeCreatePlaylist(); renderLibraryUI(); };
}

function openAddToPlaylistModal() {
    if (!currentTrack || !db) return;
    const req = db.transaction("playlists", "readonly").objectStore("playlists").getAll();
    req.onsuccess = () => {
        const html = req.result.length
            ? req.result.map(p => `<div class="lib-item" onclick="addTrackToPlaylist('${p.id}')" style="margin-bottom:12px;cursor:pointer;">
                <img src="${p.img || 'https://via.placeholder.com/50'}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;" onerror="this.src='https://via.placeholder.com/50'">
                <div style="color:white;font-size:16px;">${p.name}</div>
            </div>`).join('')
            : '<div style="color:#a7a7a7;text-align:center;">Belum ada playlist. Buat dulu di Koleksi.</div>';
        document.getElementById('addToPlaylistList').innerHTML = html;
        document.getElementById('addToPlaylistModal').style.display = 'flex';
    };
}

function closeAddToPlaylistModal() { document.getElementById('addToPlaylistModal').style.display = 'none'; }

function addTrackToPlaylist(id) {
    const store = db.transaction("playlists", "readwrite").objectStore("playlists");
    const req = store.get(id);
    req.onsuccess = () => {
        const p = req.result;
        if (!p.tracks) p.tracks = [];
        if (!p.tracks.find(t => t.videoId === currentTrack.videoId)) {
            p.tracks.push(currentTrack);
            store.put(p);
            showToast('Ditambahkan ke ' + p.name);
        } else {
            showToast('Sudah ada di ' + p.name);
        }
        closeAddToPlaylistModal();
    };
}

window.onload = () => { loadHomeData(); renderSearchCategories(); };
