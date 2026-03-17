var API_BASE = 'https://clone2-iyrr-git-master-yusrilrizky121-codes-projects.vercel.app';
// ===================== PWA =====================
let deferredPrompt;
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
}
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault(); deferredPrompt = e;
    const btn = document.getElementById('installAppBtn');
    if (btn) { btn.style.display = 'flex'; btn.addEventListener('click', async () => { deferredPrompt.prompt(); const { outcome } = await deferredPrompt.userChoice; if (outcome === 'accepted') btn.style.display = 'none'; deferredPrompt = null; }); }
});

// ===================== INDEXEDDB =====================
let db;
const dbReq = indexedDB.open("AuspotyDB", 1);
dbReq.onupgradeneeded = (e) => {
    db = e.target.result;
    if (!db.objectStoreNames.contains('playlists')) db.createObjectStore('playlists', { keyPath: 'id' });
    if (!db.objectStoreNames.contains('liked_songs')) db.createObjectStore('liked_songs', { keyPath: 'videoId' });
};
dbReq.onsuccess = (e) => { db = e.target.result; renderLibraryUI(); };

// ===================== YOUTUBE PLAYER =====================
let ytPlayer, isPlaying = false, currentTrack = null, progressInterval;
function onYouTubeIframeAPIReady() {
    ytPlayer = new YT.Player('youtube-player', { height: '0', width: '0', events: { onReady: () => {}, onStateChange: onPlayerStateChange } });
}
function onPlayerStateChange(event) {
    const playPath = "M8 5v14l11-7z", pausePath = "M6 19h4V5H6v14zm8-14v14h4V5h-4z";
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (event.data == YT.PlayerState.PLAYING) {
        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        startProgressBar();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
    } else if (event.data == YT.PlayerState.PAUSED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
    } else if (event.data == YT.PlayerState.ENDED) {
        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar(); playNextSimilarSong();
    }
}
function updateMediaSession() {
    if ('mediaSession' in navigator && currentTrack) {
        navigator.mediaSession.metadata = new MediaMetadata({ title: currentTrack.title, artist: currentTrack.artist, artwork: [{ src: currentTrack.img, sizes: '512x512', type: 'image/png' }] });
        navigator.mediaSession.setActionHandler('play', togglePlay);
        navigator.mediaSession.setActionHandler('pause', togglePlay);
        navigator.mediaSession.setActionHandler('nexttrack', playNextSimilarSong);
    }
}
async function playNextSimilarSong() {
    if (!currentTrack) return;
    try {
        const res = await fetch(API_BASE + '/api/search?query=' + encodeURIComponent(currentTrack.artist + ' official audio'));
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
    checkIfLiked(currentTrack.videoId); updateMediaSession();
    document.getElementById('miniPlayer').style.display = 'flex';
    document.getElementById('miniPlayerImg').src = currentTrack.img;
    document.getElementById('miniPlayerTitle').innerText = currentTrack.title;
    document.getElementById('miniPlayerArtist').innerText = currentTrack.artist;
    document.getElementById('playerArt').src = currentTrack.img;
    document.getElementById('playerTitle').innerText = currentTrack.title;
    document.getElementById('playerArtist').innerText = currentTrack.artist;
    document.getElementById('playerBg').style.backgroundImage = "url('" + currentTrack.img + "')";
    document.getElementById('progressBar').value = 0;
    document.getElementById('currentTime').innerText = "0:00";
    document.getElementById('totalTime').innerText = "0:00";
    if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);
}
function togglePlay() { if (!ytPlayer) return; isPlaying ? ytPlayer.pauseVideo() : ytPlayer.playVideo(); }
function expandPlayer() { document.getElementById('playerModal').style.display = 'flex'; }
function minimizePlayer() { document.getElementById('playerModal').style.display = 'none'; }
function formatTime(s) { const m = Math.floor(s / 60), sec = Math.floor(s % 60); return m + ':' + (sec < 10 ? '0' : '') + sec; }
function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (ytPlayer && ytPlayer.getCurrentTime && ytPlayer.getDuration) {
            const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration();
            if (dur > 0) {
                const pct = (cur / dur) * 100;
                const bar = document.getElementById('progressBar');
                bar.value = pct;
                bar.style.background = 'linear-gradient(to right, white ' + pct + '%, rgba(255,255,255,0.2) ' + pct + '%)';
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
        document.getElementById('progressBar').style.background = 'linear-gradient(to right, white ' + value + '%, rgba(255,255,255,0.2) ' + value + '%)';
    }
}

// ===================== LYRICS =====================
let lyricsLines = [], lyricsScrollInterval = null, currentHighlightIdx = -1, lyricsType = 'plain';
async function openLyricsModal() {
    if (!currentTrack) return;
    const modal = document.getElementById('lyricsModal'), body = document.getElementById('lyricsBody');
    document.getElementById('lyricsTrackImg').src = currentTrack.img;
    document.getElementById('lyricsTrackTitle').innerText = currentTrack.title;
    document.getElementById('lyricsTrackArtist').innerText = currentTrack.artist;
    document.getElementById('lyricsBg').style.backgroundImage = "url('" + currentTrack.img + "')";
    modal.style.display = 'flex';
    body.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Menarik lirik...</div>';
    stopLyricsScroll(); lyricsLines = []; currentHighlightIdx = -1;
    try {
        const res = await fetch(API_BASE + '/api/lyrics?video_id=' + currentTrack.videoId);
        const result = await res.json();
        if (result.status === 'success' && result.data && result.data.lines && result.data.lines.length > 0) {
            lyricsLines = result.data.lines; lyricsType = result.data.type || 'plain';
            let html = '<div style="height:45vh"></div>';
            lyricsLines.forEach((line, i) => { html += '<div class="lyric-line" id="lyric-line-' + i + '">' + line.text + '</div>'; });
            html += '<div style="height:45vh"></div>';
            body.innerHTML = html;
            startLyricsScroll(body);
        } else {
            body.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Lirik belum tersedia.</div>';
        }
    } catch (e) {
        body.innerHTML = '<div style="color:#ff5252;font-size:16px;text-align:center;margin-top:40px;">Gagal memuat lirik.</div>';
    }
}
function startLyricsScroll() {
    stopLyricsScroll();
    lyricsScrollInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (!dur || lyricsLines.length === 0) return;
        let idx = 0;
        if (lyricsType === 'synced') {
            for (let i = 0; i < lyricsLines.length; i++) { if (lyricsLines[i].time !== null && lyricsLines[i].time <= cur) idx = i; }
        } else {
            idx = Math.min(Math.floor((cur / dur) * lyricsLines.length), lyricsLines.length - 1);
        }
        if (idx === currentHighlightIdx) return;
        currentHighlightIdx = idx;
        lyricsLines.forEach((_, i) => {
            const el = document.getElementById('lyric-line-' + i);
            if (el) el.className = 'lyric-line' + (i === idx ? ' lyric-active' : (i < idx ? ' lyric-past' : ''));
        });
        const activeLine = document.getElementById('lyric-line-' + idx);
        if (activeLine) activeLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
}
function stopLyricsScroll() { if (lyricsScrollInterval) { clearInterval(lyricsScrollInterval); lyricsScrollInterval = null; } }
function closeLyricsToPlayer() {
    document.getElementById('lyricsModal').style.display = 'none';
    document.getElementById('lyricsBody').innerHTML = '';
    stopLyricsScroll();
    lyricsLines = []; currentHighlightIdx = -1;
    document.getElementById('playerModal').style.display = 'flex';
}
function closeLyrics() { document.getElementById('lyricsModal').style.display = 'none'; document.getElementById('lyricsBody').innerHTML = ''; stopLyricsScroll(); lyricsLines = []; currentHighlightIdx = -1; }

// ===================== BACKGROUND AUDIO =====================
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (ytPlayer && ytPlayer.getPlayerState && ytPlayer.getPlayerState() === YT.PlayerState.PLAYING) sessionStorage.setItem('wasPlaying', 'true');
    } else {
        if (sessionStorage.getItem('wasPlaying') === 'true') { sessionStorage.removeItem('wasPlaying'); if (ytPlayer && ytPlayer.getPlayerState && ytPlayer.getPlayerState() !== YT.PlayerState.PLAYING) ytPlayer.playVideo(); }
    }
});

// ===================== TOAST =====================
let toastTimeout;
function showToast(msg) {
    const t = document.getElementById('customToast');
    if (!t) return;
    t.innerText = msg; t.classList.add('show');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => t.classList.remove('show'), 3000);
}

// ===================== NAVIGASI =====================
function switchView(name) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    const view = document.getElementById('view-' + name);
    if (view) view.classList.add('active');
    document.querySelectorAll('.bottom-nav .nav-item').forEach(n => n.classList.remove('active'));
    const navIdx = { home: 0, search: 1, library: 2, settings: 3 };
    if (navIdx[name] !== undefined) {
        const items = document.querySelectorAll('.bottom-nav .nav-item');
        if (items[navIdx[name]]) items[navIdx[name]].classList.add('active');
    }
    if (name === 'library') renderLibraryUI();
    if (name === 'settings') renderSettingsUI();
    window.scrollTo(0, 0);
}

// ===================== RENDER HELPERS =====================
const dotsSvg = '<svg class="dots-icon" viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>';
function getHighResImage(url) {
    if (!url) return 'https://placehold.co/140x140/282828/FFFFFF?text=Music';
    if (url.match(/=w\d+-h\d+/)) return url.replace(/=w\d+-h\d+[^&]*/g, '=w512-h512-l90-rj');
    return url;
}
function createListHTML(track) {
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    return '<div class="v-item" onclick="playMusic(\'' + track.videoId + '\',\'' + data + '\')">' +
        '<img src="' + img + '" class="v-img" onerror="this.src=\'https://placehold.co/48x48/282828/FFFFFF?text=Music\'">' +
        '<div class="v-info"><div class="v-title">' + track.title + '</div><div class="v-sub">' + artist + '</div></div>' +
        dotsSvg + '</div>';
}
function createCardHTML(track, isArtist) {
    isArtist = isArtist || false;
    const img = getHighResImage(track.thumbnail || track.img || '');
    const artist = track.artist || 'Unknown';
    const data = encodeURIComponent(JSON.stringify({ videoId: track.videoId, title: track.title, artist, img }));
    const click = isArtist ? 'openArtistView(\'' + track.title + '\')' : 'playMusic(\'' + track.videoId + '\',\'' + data + '\')';
    return '<div class="h-card" onclick="' + click + '">' +
        '<img src="' + img + '" class="h-img' + (isArtist ? ' artist-img' : '') + '" onerror="this.src=\'https://placehold.co/140x140/282828/FFFFFF?text=Music\'">' +
        '<div class="h-title">' + track.title + '</div>' +
        '<div class="h-sub">' + (isArtist ? 'Artis' : artist) + '</div></div>';
}
async function fetchSection(query, id, type, isArtist, limit) {
    isArtist = isArtist || false; limit = limit || 8;
    try {
        const res = await fetch(API_BASE + '/api/search?query=' + encodeURIComponent(query) + '&limit=' + limit);
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = result.data.map(function(t) { return type === 'list' ? createListHTML(t) : createCardHTML(t, isArtist); }).join('');
        }
    } catch (e) {}
}
function loadHomeData() {
    fetchSection('lagu indonesia hits terbaru', 'recentList', 'list', false, 4);
    fetchSection('lagu pop indonesia rilis terbaru', 'rowAnyar', 'card');
    fetchSection('lagu ceria gembira semangat', 'rowGembira', 'card');
    fetchSection('top 50 indonesia playlist', 'rowCharts', 'card');
    fetchSection('lagu galau sedih indonesia', 'rowGalau', 'card');
    fetchSection('lagu fyp tiktok viral', 'rowTiktok', 'card');
    fetchSection('penyanyi pop indonesia hits', 'rowArtists', 'card', true);
    fetchSection('hit terpopuler hari ini', 'rowHits', 'card');
}
function renderSearchCategories() {
    var cats = [
        { title: 'Dibuat Untuk Kamu', color: '#8d67ab', img: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=100&q=80' },
        { title: 'Rilis Baru', color: '#739c18', img: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100&q=80' },
        { title: 'Pop', color: '#477d95', img: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=100&q=80' },
        { title: 'Indie', color: '#e1118c', img: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=100&q=80' },
        { title: 'Musik Indonesia', color: '#e8115b', img: 'https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=100&q=80' },
        { title: 'Tangga Lagu', color: '#8d67ab', img: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=100&q=80' },
        { title: 'K-pop', color: '#e8115b', img: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=100&q=80' },
        { title: 'Viral TikTok', color: '#1e3264', img: 'https://images.unsplash.com/photo-1593697821252-0c9137d9fc45?w=100&q=80' }
    ];
    var grid = document.getElementById('categoryGrid');
    if (grid) grid.innerHTML = cats.map(function(c) { return '<div class="category-card" style="background:' + c.color + ';" onclick="searchByCategory(\'' + c.title + '\')"><div class="category-title">' + c.title + '</div><img src="' + c.img + '" class="category-img"></div>'; }).join('');
}
function searchByCategory(title) {
    document.getElementById('searchInput').value = title;
    document.getElementById('searchInput').dispatchEvent(new Event('input'));
    switchView('search');
}
var searchTimeout;
document.getElementById('searchInput').addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    var q = e.target.value.trim();
    if (!q) { document.getElementById('searchCategoriesUI').style.display = 'block'; document.getElementById('searchResultsUI').style.display = 'none'; return; }
    document.getElementById('searchCategoriesUI').style.display = 'none';
    document.getElementById('searchResultsUI').style.display = 'block';
    searchTimeout = setTimeout(async function() {
        document.getElementById('searchResults').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Mencari...</div>';
        try {
            var res = await fetch(API_BASE + '/api/search?query=' + encodeURIComponent(q));
            var result = await res.json();
            if (result.status === 'success') document.getElementById('searchResults').innerHTML = result.data.map(function(t) { return createListHTML(t); }).join('');
        } catch (e) {}
    }, 600);
});

// ===================== ARTIST =====================
async function openArtistView(name) {
    document.getElementById('artistNameDisplay').innerText = name;
    document.getElementById('artistTracksContainer').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Memuat...</div>';
    switchView('artist');
    try {
        var res = await fetch(API_BASE + '/api/search?query=' + encodeURIComponent(name + ' official audio'));
        var result = await res.json();
        if (result.status === 'success') {
            document.getElementById('artistTracksContainer').innerHTML = result.data.map(function(t) { return createListHTML(t); }).join('');
            if (result.data.length > 0) {
                var f = result.data[0], img = getHighResImage(f.thumbnail || f.img || '');
                var data = encodeURIComponent(JSON.stringify({ videoId: f.videoId, title: f.title, artist: f.artist || 'Unknown', img: img }));
                document.querySelector('.artist-play-btn').setAttribute('onclick', 'playMusic(\'' + f.videoId + '\',\'' + data + '\')');
            }
        }
    } catch (e) {}
}
function playFirstArtistTrack() {}

// ===================== LIKE =====================
function checkIfLiked(videoId) {
    if (!db) return;
    db.transaction('liked_songs', 'readonly').objectStore('liked_songs').get(videoId).onsuccess = function(e) {
        var liked = !!e.target.result;
        ['btnLikeSong', 'btnLikeLyric'].forEach(function(id) { var el = document.getElementById(id); if (el) el.style.fill = liked ? 'var(--spotify-green)' : 'white'; });
    };
}
function toggleLike() {
    if (!currentTrack || !db) return;
    var store = db.transaction('liked_songs', 'readwrite').objectStore('liked_songs');
    store.get(currentTrack.videoId).onsuccess = function(e) {
        if (e.target.result) {
            store.delete(currentTrack.videoId);
            ['btnLikeSong', 'btnLikeLyric'].forEach(function(id) { var el = document.getElementById(id); if (el) el.style.fill = 'white'; });
            showToast('Dihapus dari Lagu Disukai');
        } else {
            store.put(currentTrack);
            ['btnLikeSong', 'btnLikeLyric'].forEach(function(id) { var el = document.getElementById(id); if (el) el.style.fill = 'var(--spotify-green)'; });
            showToast('Ditambahkan ke Lagu Disukai');
        }
        renderLibraryUI();
    };
}

// ===================== LIBRARY =====================
function renderLibraryUI() {
    if (!db) return;
    var container = document.getElementById('libraryContainer');
    if (!container) return;
    db.transaction('liked_songs', 'readonly').objectStore('liked_songs').getAll().onsuccess = function(e) {
        var likedCount = e.target.result.length;
        var html = '<div class="lib-item" onclick="openPlaylistView(\'liked\')">' +
            '<div class="lib-item-img liked"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div>' +
            '<div class="lib-item-info"><div class="lib-item-title">Lagu yang Disukai</div><div class="lib-item-sub">Playlist - ' + likedCount + ' lagu</div></div></div>';
        db.transaction('playlists', 'readonly').objectStore('playlists').getAll().onsuccess = function(e2) {
            e2.target.result.forEach(function(p) {
                html += '<div class="lib-item" onclick="openPlaylistView(\'' + p.id + '\')">' +
                    '<img src="' + (p.img || 'https://via.placeholder.com/64?text=+') + '" class="lib-item-img" onerror="this.src=\'https://via.placeholder.com/64?text=+\'">' +
                    '<div class="lib-item-info"><div class="lib-item-title">' + p.name + '</div><div class="lib-item-sub">Playlist - ' + (p.tracks||[]).length + ' lagu</div></div></div>';
            });
            html += '<div class="lib-item" onclick="openCreatePlaylist()">' +
                '<div class="lib-item-img add-btn-sq"><svg viewBox="0 0 24 24" style="fill:white;width:32px;height:32px;"><path d="M11 11V4h2v7h7v2h-7v7h-2v-7H4v-2h7z"/></svg></div>' +
                '<div class="lib-item-info"><div class="lib-item-title">Buat Playlist Baru</div></div></div>';
            container.innerHTML = html;
        };
    };
}
var currentPlaylistTracks = [];
function openPlaylistView(id) {
    switchView('playlist');
    document.getElementById('playlistTracksContainer').innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;">Memuat...</div>';
    if (id === 'liked') {
        document.getElementById('playlistNameDisplay').innerText = 'Lagu yang Disukai';
        document.getElementById('playlistImageDisplay').src = 'https://via.placeholder.com/220/450af5/ffffff?text=heart';
        db.transaction('liked_songs', 'readonly').objectStore('liked_songs').getAll().onsuccess = function(e) {
            currentPlaylistTracks = e.target.result;
            document.getElementById('playlistStatsDisplay').innerText = currentPlaylistTracks.length + ' lagu';
            renderTracksInPlaylist(currentPlaylistTracks);
        };
    } else {
        db.transaction('playlists', 'readonly').objectStore('playlists').get(id).onsuccess = function(e) {
            var p = e.target.result;
            currentPlaylistTracks = p.tracks || [];
            document.getElementById('playlistNameDisplay').innerText = p.name;
            document.getElementById('playlistImageDisplay').src = p.img || 'https://via.placeholder.com/220/282828/ffffff?text=+';
            document.getElementById('playlistStatsDisplay').innerText = currentPlaylistTracks.length + ' lagu';
            renderTracksInPlaylist(currentPlaylistTracks);
        };
    }
}
function playFirstPlaylistTrack() { if (currentPlaylistTracks.length > 0) { var t = currentPlaylistTracks[0]; playMusic(t.videoId, encodeURIComponent(JSON.stringify(t))); } }
function renderTracksInPlaylist(tracks) {
    var c = document.getElementById('playlistTracksContainer');
    c.innerHTML = tracks.length ? tracks.map(function(t) { return createListHTML(t); }).join('') : '<div style="color:var(--text-sub);text-align:center;padding:20px;">Playlist kosong.</div>';
}
var base64Img = '';
function openCreatePlaylist() { document.getElementById('createPlaylistModal').style.display = 'block'; }
function closeCreatePlaylist() { document.getElementById('createPlaylistModal').style.display = 'none'; document.getElementById('cpName').value = ''; document.getElementById('cpPreview').src = 'https://via.placeholder.com/120x120?text=+'; base64Img = ''; }
function previewImage(e) { var reader = new FileReader(); reader.onloadend = function() { document.getElementById('cpPreview').src = reader.result; base64Img = reader.result; }; if (e.target.files[0]) reader.readAsDataURL(e.target.files[0]); }
function saveNewPlaylist() {
    var name = document.getElementById('cpName').value || 'Playlist baruku';
    var p = { id: Date.now().toString(), name: name, img: base64Img, tracks: [] };
    var tx = db.transaction('playlists', 'readwrite');
    tx.objectStore('playlists').put(p);
    tx.oncomplete = function() { closeCreatePlaylist(); renderLibraryUI(); };
}
function openAddToPlaylistModal() {
    if (!currentTrack || !db) return;
    db.transaction('playlists', 'readonly').objectStore('playlists').getAll().onsuccess = function(e) {
        var html = e.target.result.length
            ? e.target.result.map(function(p) { return '<div class="lib-item" onclick="addTrackToPlaylist(\'' + p.id + '\')" style="margin-bottom:12px;cursor:pointer;"><img src="' + (p.img||'https://via.placeholder.com/50') + '" style="width:50px;height:50px;object-fit:cover;border-radius:4px;"><div style="color:white;font-size:16px;">' + p.name + '</div></div>'; }).join('')
            : '<div style="color:#a7a7a7;text-align:center;">Belum ada playlist.</div>';
        document.getElementById('addToPlaylistList').innerHTML = html;
        document.getElementById('addToPlaylistModal').style.display = 'flex';
    };
}
function closeAddToPlaylistModal() { document.getElementById('addToPlaylistModal').style.display = 'none'; }
function addTrackToPlaylist(id) {
    var store = db.transaction('playlists', 'readwrite').objectStore('playlists');
    store.get(id).onsuccess = function(e) {
        var p = e.target.result;
        if (!p.tracks) p.tracks = [];
        if (!p.tracks.find(function(t) { return t.videoId === currentTrack.videoId; })) { p.tracks.push(currentTrack); store.put(p); showToast('Ditambahkan ke ' + p.name); }
        else showToast('Sudah ada di ' + p.name);
        closeAddToPlaylistModal();
    };
}

// ===================== SETTINGS =====================
var SETTINGS_KEY = 'auspoty_settings';
var defaultSettings = { theme: 'green', darkMode: true, quality: 'auto', fontSize: 'normal', language: 'id', region: 'ID', autoplay: true, crossfade: false, normalize: false, lyricsSync: true, notifNowPlaying: true, notifNewRelease: false };
var themeMap = { green: { name: 'Hijau (Default)', color: '#1ed760', dark: '#1db954' }, blue: { name: 'Biru', color: '#2196f3', dark: '#1976d2' }, purple: { name: 'Ungu', color: '#9c27b0', dark: '#7b1fa2' }, red: { name: 'Merah', color: '#f44336', dark: '#d32f2f' }, orange: { name: 'Oranye', color: '#ff9800', dark: '#f57c00' }, pink: { name: 'Pink', color: '#e91e63', dark: '#c2185b' } };
var qualityOpts = [{ value: 'auto', label: 'Auto (Disarankan)' },{ value: 'low', label: 'Rendah (64 kbps)' },{ value: 'medium', label: 'Sedang (128 kbps)' },{ value: 'high', label: 'Tinggi (256 kbps)' },{ value: 'very_high', label: 'Sangat Tinggi (320 kbps)' }];
var fontOpts = { small: 'Kecil', normal: 'Normal', large: 'Besar', xlarge: 'Sangat Besar' };
var langOpts = { id: 'Indonesia', en: 'English', ja: 'Jepang', ko: 'Korea', zh: 'China' };
var regionOpts = { ID: 'Indonesia', US: 'Amerika Serikat', JP: 'Jepang', KR: 'Korea', GB: 'Inggris' };

function getSettings() {
    try { return Object.assign({}, defaultSettings, JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')); }
    catch(e) { return Object.assign({}, defaultSettings); }
}
function saveSettings(s) { localStorage.setItem(SETTINGS_KEY, JSON.stringify(s)); }

function applyAllSettings() {
    var s = getSettings();
    var t = themeMap[s.theme] || themeMap.green;
    document.documentElement.style.setProperty('--spotify-green', t.color);
    document.documentElement.style.setProperty('--spotify-green-dark', t.dark);
    var fontMap = { small: '13px', normal: '16px', large: '19px', xlarge: '22px' };
    document.documentElement.style.setProperty('--base-font-size', fontMap[s.fontSize] || '16px');
    if (s.darkMode) {
        document.documentElement.style.setProperty('--bg-base', '#121212');
        document.documentElement.style.setProperty('--bg-highlight', '#1a1a1a');
        document.documentElement.style.setProperty('--bg-card', '#181818');
        document.documentElement.style.setProperty('--text-main', '#ffffff');
        document.documentElement.style.setProperty('--text-sub', '#a7a7a7');
    } else {
        document.documentElement.style.setProperty('--bg-base', '#f5f5f5');
        document.documentElement.style.setProperty('--bg-highlight', '#e8e8e8');
        document.documentElement.style.setProperty('--bg-card', '#ffffff');
        document.documentElement.style.setProperty('--text-main', '#121212');
        document.documentElement.style.setProperty('--text-sub', '#535353');
    }
}

function renderSettingsUI() {
    var s = getSettings();
    var profileName = s.profileName || "Pengguna Auspoty";
    var pnEl = document.getElementById("settingsProfileName");
    var avEl = document.getElementById("settingsAvatar");
    if (pnEl) pnEl.innerText = profileName;
    if (avEl) avEl.innerText = profileName.charAt(0).toUpperCase();
    function setLabel(id, val) { var el = document.getElementById(id); if (el) el.innerText = val; }
    setLabel('themeLabel', (themeMap[s.theme] || themeMap.green).name);
    var qFound = qualityOpts.find(function(q) { return q.value === s.quality; }); setLabel('qualityLabel', qFound ? qFound.label : 'Auto (Disarankan)');
    setLabel('fontSizeLabel', fontOpts[s.fontSize] || 'Normal');
    setLabel('langLabel', langOpts[s.language] || 'Indonesia');
    setLabel('regionLabel', regionOpts[s.region] || 'Indonesia');
    function setToggle(id, val) { var el = document.getElementById(id); if (el) { if (val) el.classList.add('active'); else el.classList.remove('active'); } }
    setToggle('darkModeToggle', s.darkMode);
    setToggle('autoplayToggle', s.autoplay);
    setToggle('crossfadeToggle', s.crossfade);
    setToggle('normalizeToggle', s.normalize);
    setToggle('lyricsSyncToggle', s.lyricsSync);
    setToggle('notifNowPlayingToggle', s.notifNowPlaying);
    setToggle('notifNewReleaseToggle', s.notifNewRelease);
    var dmItem = document.getElementById('darkModeToggle');
    if (dmItem) { var sub = dmItem.closest('.settings-item'); if (sub) { var subEl = sub.querySelector('.settings-item-sub'); if (subEl) subEl.innerText = s.darkMode ? 'Aktif saat ini' : 'Nonaktif'; } }
    estimateCacheSize();
}

function toggleDarkMode() {
    var s = getSettings(); s.darkMode = !s.darkMode; saveSettings(s);
    applyAllSettings(); renderSettingsUI();
    showToast(s.darkMode ? 'Mode gelap aktif' : 'Mode terang aktif');
}
function toggleAutoplay() { var s = getSettings(); s.autoplay = !s.autoplay; saveSettings(s); var el = document.getElementById('autoplayToggle'); if (el) { if (s.autoplay) el.classList.add('active'); else el.classList.remove('active'); } showToast(s.autoplay ? 'Putar otomatis aktif' : 'Nonaktif'); }
function toggleCrossfade() { var s = getSettings(); s.crossfade = !s.crossfade; saveSettings(s); var el = document.getElementById('crossfadeToggle'); if (el) { if (s.crossfade) el.classList.add('active'); else el.classList.remove('active'); } showToast(s.crossfade ? 'Crossfade aktif' : 'Nonaktif'); }
function toggleNormalize() { var s = getSettings(); s.normalize = !s.normalize; saveSettings(s); var el = document.getElementById('normalizeToggle'); if (el) { if (s.normalize) el.classList.add('active'); else el.classList.remove('active'); } showToast(s.normalize ? 'Normalisasi aktif' : 'Nonaktif'); }
function toggleLyricsSync() { var s = getSettings(); s.lyricsSync = !s.lyricsSync; saveSettings(s); var el = document.getElementById('lyricsSyncToggle'); if (el) { if (s.lyricsSync) el.classList.add('active'); else el.classList.remove('active'); } showToast(s.lyricsSync ? 'Sinkronisasi lirik aktif' : 'Nonaktif'); }
function toggleNotif(type) {
    var s = getSettings();
    if (type === 'nowPlaying') { s.notifNowPlaying = !s.notifNowPlaying; var el = document.getElementById('notifNowPlayingToggle'); if (el) { if (s.notifNowPlaying) el.classList.add('active'); else el.classList.remove('active'); } showToast(s.notifNowPlaying ? 'Notifikasi lagu aktif' : 'Nonaktif'); }
    if (type === 'newRelease') { s.notifNewRelease = !s.notifNewRelease; var el2 = document.getElementById('notifNewReleaseToggle'); if (el2) { if (s.notifNewRelease) el2.classList.add('active'); else el2.classList.remove('active'); } showToast(s.notifNewRelease ? 'Notifikasi rilis aktif' : 'Nonaktif'); }
    saveSettings(s);
}

// PICKER
var _pickerCb = null;
function openPicker(title, options, currentVal, cb) {
    _pickerCb = cb;
    document.getElementById('pickerTitle').innerText = title;
    var html = '';
    for (var i = 0; i < options.length; i++) {
        var o = options[i];
        var sel = o.value === currentVal;
        html += '<div class="picker-option' + (sel ? ' selected' : '') + '" onclick="selectPickerOption(\'' + o.value + '\',\'' + encodeURIComponent(o.label) + '\')">' +
            '<span>' + o.label + '</span>' +
            (sel ? '<svg viewBox="0 0 24 24" style="width:20px;height:20px;fill:var(--spotify-green);flex-shrink:0;"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>' : '') +
            '</div>';
    }
    document.getElementById('pickerOptions').innerHTML = html;
    document.getElementById('pickerModal').classList.add('open');
    document.getElementById('pickerOverlay').classList.add('open');
}
function selectPickerOption(value, encodedLabel) {
    if (_pickerCb) _pickerCb(value, decodeURIComponent(encodedLabel));
    closePicker();
}
function closePicker() {
    document.getElementById('pickerModal').classList.remove('open');
    document.getElementById('pickerOverlay').classList.remove('open');
    _pickerCb = null;
}

function openThemePicker() {
    var s = getSettings();
    var opts = Object.keys(themeMap).map(function(k) { return { value: k, label: themeMap[k].name }; });
    openPicker('Pilih Tema Warna', opts, s.theme, function(val, label) {
        s.theme = val; saveSettings(s); applyAllSettings();
        var el = document.getElementById('themeLabel'); if (el) el.innerText = label;
        showToast('Tema: ' + label);
    });
}
function openQualityPicker() {
    var s = getSettings();
    var opts = qualityOpts.map(function(q) { return { value: q.value, label: q.label }; });
    openPicker('Kualitas Audio', opts, s.quality, function(val, label) {
        s.quality = val; saveSettings(s);
        var el = document.getElementById('qualityLabel'); if (el) el.innerText = label;
        showToast('Kualitas: ' + label);
    });
}
function openFontSizePicker() {
    var s = getSettings();
    var opts = Object.keys(fontOpts).map(function(k) { return { value: k, label: fontOpts[k] }; });
    openPicker('Ukuran Teks', opts, s.fontSize, function(val, label) {
        s.fontSize = val; saveSettings(s); applyAllSettings();
        var el = document.getElementById('fontSizeLabel'); if (el) el.innerText = label;
        showToast('Ukuran teks: ' + label);
    });
}
function openLanguagePicker() {
    var s = getSettings();
    var opts = Object.keys(langOpts).map(function(k) { return { value: k, label: langOpts[k] }; });
    openPicker('Bahasa Aplikasi', opts, s.language, function(val, label) {
        s.language = val; saveSettings(s);
        var el = document.getElementById('langLabel'); if (el) el.innerText = label;
        showToast('Bahasa: ' + label);
    });
}
function openRegionPicker() {
    var s = getSettings();
    var opts = Object.keys(regionOpts).map(function(k) { return { value: k, label: regionOpts[k] }; });
    openPicker('Wilayah Konten', opts, s.region, function(val, label) {
        s.region = val; saveSettings(s);
        var el = document.getElementById('regionLabel'); if (el) el.innerText = label;
        showToast('Wilayah: ' + label);
    });
}

// PROFILE EDIT
function openEditProfile() {
    var s = getSettings();
    var name = s.profileName || "Pengguna Auspoty";
    var inp = document.getElementById("editProfileName");
    var av = document.getElementById("editProfileAvatar");
    if (inp) inp.value = name;
    if (av) av.innerText = name.charAt(0).toUpperCase();
    var modal = document.getElementById("editProfileModal");
    if (modal) modal.style.display = "flex";
}
function closeEditProfile() {
    var modal = document.getElementById("editProfileModal");
    if (modal) modal.style.display = "none";
}
function saveProfile() {
    var inp = document.getElementById("editProfileName");
    var name = (inp && inp.value.trim()) ? inp.value.trim() : "Pengguna Auspoty";
    var s = getSettings(); s.profileName = name; saveSettings(s);
    var pn = document.getElementById("settingsProfileName"); if (pn) pn.innerText = name;
    var av = document.getElementById("settingsAvatar"); if (av) av.innerText = name.charAt(0).toUpperCase();
    closeEditProfile(); showToast("Profil diperbarui");
}
function clearCache() {
    if (!confirm('Hapus semua cache aplikasi?')) return;
    if ('caches' in window) caches.keys().then(function(keys) { keys.forEach(function(k) { caches.delete(k); }); });
    showToast('Cache berhasil dihapus');
    estimateCacheSize();
}
function clearLikedSongs() {
    if (!db) return;
    if (!confirm('Hapus semua lagu yang disukai?')) return;
    var tx = db.transaction('liked_songs', 'readwrite');
    tx.objectStore('liked_songs').clear();
    tx.oncomplete = function() { showToast('Lagu disukai dihapus'); renderLibraryUI(); };
}
function estimateCacheSize() {
    var el = document.getElementById('cacheSize');
    if (!el) return;
    if ('storage' in navigator && 'estimate' in navigator.storage) {
        navigator.storage.estimate().then(function(est) {
            var kb = Math.round((est.usage || 0) / 1024);
            el.innerText = kb > 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb + ' KB';
        });
    } else { el.innerText = 'Tidak diketahui'; }
}

// ===================== INIT =====================
window.onload = function() {
    applyAllSettings();
    loadHomeData();
    renderSearchCategories();
};



