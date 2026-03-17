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

// YOUTUBE PLAYER
let ytPlayer, isPlaying = false, currentTrack = null, progressInterval;
function onYouTubeIframeAPIReady() {
    ytPlayer = new YT.Player('youtube-player', { height: '0', width: '0', events: { onReady: () => {}, onStateChange: onPlayerStateChange } });
}
function onPlayerStateChange(event) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
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
        const res = await fetch('/api/search?query=' + encodeURIComponent(currentTrack.artist + ' official audio'));
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
function getHighResImage(url) {
    if (!url) return 'https://via.placeholder.com/300x300?text=music';
    return url.replace(/=w\d+-h\d+/, '=w500-h500').replace(/w\d+_h\d+/, 'w500_h500');
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
    document.getElementById('currentTime').innerText = '0:00';
    document.getElementById('totalTime').innerText = '0:00';
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
        const res = await fetch('/api/lyrics?video_id=' + currentTrack.videoId);
        const result = await res.json();
        if (result.status === 'success' && result.data && result.data.lines && result.data.lines.length > 0) {
            lyricsLines = result.data.lines; lyricsType = result.data.type || 'plain';
            let html = '<div style="height:40px"></div>';
            lyricsLines.forEach((line, i) => { html += '<div class="lyric-line" id="lyric-line-' + i + '">' + (line.text || '') + '</div>'; });
            html += '<div style="height:45vh"></div>';
            lbody.innerHTML = html;
            lbody.scrollTop = 0;
            startLyricsScroll();
        } else {
            lbody.innerHTML = '<div style="color:rgba(255,255,255,0.5);font-size:16px;text-align:center;margin-top:40px;">Lirik belum tersedia.</div>';
        }
    } catch (e) {
        lbody.innerHTML = '<div style="color:#ff5252;font-size:16px;text-align:center;margin-top:40px;">Gagal memuat lirik.</div>';
    }
}
function startLyricsScroll() {
    stopLyricsScroll();
    lyricsScrollInterval = setInterval(function() {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        var cur = ytPlayer.getCurrentTime();
        var dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
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
            if (lb) {
                var targetScroll = activeLine.offsetTop - (lb.clientHeight / 2) + (activeLine.offsetHeight / 2);
                lb.scrollTop = targetScroll;
            }
        }
    }, 300);
}
function stopLyricsScroll() { clearInterval(lyricsScrollInterval); lyricsScrollInterval = null; }
function closeLyricsToPlayer() {
    stopLyricsScroll();
    document.getElementById('lyricsModal').style.display = 'none';
    document.getElementById('playerModal').style.display = 'flex';
}
function closeLyrics() {
    stopLyricsScroll();
    document.getElementById('lyricsModal').style.display = 'none';
}

// TOAST
function showToast(msg) {
    const t = document.getElementById('customToast');
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
function renderVItem(t) {
    const d = makeTrackData(t);
    return '<div class="v-item" onclick="playMusic(\'' + t.videoId + '\',\'' + d + '\')">'+
        '<img class="v-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '" onerror="this.src=\'https://via.placeholder.com/48x48?text=music\'">'+
        '<div class="v-info"><div class="v-title">' + (t.title || '') + '</div><div class="v-sub">' + (t.artist || '') + '</div></div>'+
        '<svg class="dots-icon" viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>'+
        '</div>';
}
function renderHCard(t) {
    const d = makeTrackData(t);
    return '<div class="h-card" onclick="playMusic(\'' + t.videoId + '\',\'' + d + '\')">'+
        '<img class="h-img" src="' + getHighResImage(t.thumbnail || t.img || '') + '" onerror="this.src=\'https://via.placeholder.com/140x140?text=music\'">'+
        '<div class="h-title">' + (t.title || '') + '</div>'+
        '<div class="h-sub">' + (t.artist || '') + '</div></div>';
}
function renderArtistCard(name) {
    return '<div class="h-card" onclick="openArtist(\'' + encodeURIComponent(name) + '\')">'+
        '<div class="h-img artist-img" style="background:linear-gradient(135deg,#333,#555);display:flex;align-items:center;justify-content:center;font-size:40px;">' + name.charAt(0).toUpperCase() + '</div>'+
        '<div class="h-title" style="text-align:center;">' + name + '</div>'+
        '<div class="h-sub" style="text-align:center;">Artis</div></div>';
}

// HOME DATA
const HOME_QUERIES = [
    { id: 'rowAnyar',   query: 'lagu indonesia terbaru 2025' },
    { id: 'rowGembira', query: 'lagu semangat gembira indonesia' },
    { id: 'rowCharts',  query: 'top hits indonesia 2025' },
    { id: 'rowGalau',   query: 'lagu galau sedih indonesia' },
    { id: 'rowTiktok',  query: 'viral tiktok indonesia 2025' },
    { id: 'rowHits',    query: 'lagu hits hari ini indonesia' },
];
const ARTISTS = ['Dewa 19','Sheila On 7','Raisa','Tulus','Rizky Febian','Tiara Andini','Mahalini','Juicy Luicy'];
async function loadHomeData() {
    const recentEl = document.getElementById('recentList');
    if (recentEl) {
        try {
            const res = await fetch('/api/search?query=lagu+populer+indonesia');
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) {
                recentEl.innerHTML = result.data.slice(0, 6).map(renderVItem).join('');
            }
        } catch(e) { recentEl.innerHTML = '<div style="color:var(--text-sub);padding:8px;">Gagal memuat.</div>'; }
    }
    const artistEl = document.getElementById('rowArtists');
    if (artistEl) artistEl.innerHTML = ARTISTS.map(renderArtistCard).join('');
    for (const row of HOME_QUERIES) {
        const el = document.getElementById(row.id);
        if (!el) continue;
        el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Memuat...</div>';
        try {
            const res = await fetch('/api/search?query=' + encodeURIComponent(row.query));
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) {
                el.innerHTML = result.data.slice(0, 10).map(renderHCard).join('');
            } else {
                el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Tidak ada hasil.</div>';
            }
        } catch(e) { el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Gagal memuat.</div>'; }
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
    const grid = document.getElementById('categoryGrid');
    if (!grid) return;
    grid.innerHTML = CATEGORIES.map(c =>
        '<div class="category-card" style="background:' + c.color + ';" onclick="searchByCategory(\'' + encodeURIComponent(c.query) + '\')">'+
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
            clearTimeout(searchTimer);
            const q = this.value.trim();
            if (!q) {
                document.getElementById('searchCategoriesUI').style.display = 'block';
                document.getElementById('searchResultsUI').style.display = 'none';
                return;
            }
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
        const res = await fetch('/api/search?query=' + encodeURIComponent(q));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            el.innerHTML = result.data.map(renderVItem).join('');
        } else {
            el.innerHTML = '<div style="color:var(--text-sub);padding:16px;text-align:center;">Tidak ada hasil untuk "' + q + '"</div>';
        }
    } catch(e) { el.innerHTML = '<div style="color:#ff5252;padding:16px;text-align:center;">Gagal mencari.</div>'; }
}

// ARTIST
async function openArtist(encodedName) {
    const name = decodeURIComponent(encodedName);
    document.getElementById('artistNameDisplay').innerText = name;
    document.getElementById('artistTracksContainer').innerHTML = '<div style="color:var(--text-sub);padding:16px;">Memuat...</div>';
    switchView('artist');
    try {
        const res = await fetch('/api/search?query=' + encodeURIComponent(name));
        const result = await res.json();
        if (result.status === 'success' && result.data.length > 0) {
            window._artistTracks = result.data;
            document.getElementById('artistTracksContainer').innerHTML = result.data.slice(0, 10).map(renderVItem).join('');
        }
    } catch(e) {}
}
function playFirstArtistTrack() {
    if (window._artistTracks && window._artistTracks.length > 0) {
        const t = window._artistTracks[0];
        playMusic(t.videoId, makeTrackData(t));
    }
}

// LIKE
function checkIfLiked(videoId) {
    if (!db) return;
    const tx = db.transaction('liked_songs', 'readonly');
    tx.objectStore('liked_songs').get(videoId).onsuccess = (e) => {
        const liked = !!e.target.result;
        const btn = document.getElementById('btnLikeSong');
        const btn2 = document.getElementById('btnLikeLyric');
        if (btn) btn.style.fill = liked ? 'var(--spotify-green)' : 'white';
        if (btn2) btn2.style.fill = liked ? 'var(--spotify-green)' : 'var(--text-sub)';
    };
}
function toggleLike() {
    if (!currentTrack || !db) return;
    const tx = db.transaction('liked_songs', 'readwrite');
    const store = tx.objectStore('liked_songs');
    store.get(currentTrack.videoId).onsuccess = (e) => {
        if (e.target.result) {
            store.delete(currentTrack.videoId);
            showToast('Dihapus dari Disukai');
            const btn = document.getElementById('btnLikeSong');
            const btn2 = document.getElementById('btnLikeLyric');
            if (btn) btn.style.fill = 'white';
            if (btn2) btn2.style.fill = 'var(--text-sub)';
        } else {
            store.put(currentTrack);
            showToast('Ditambahkan ke Disukai');
            const btn = document.getElementById('btnLikeSong');
            const btn2 = document.getElementById('btnLikeLyric');
            if (btn) btn.style.fill = 'var(--spotify-green)';
            if (btn2) btn2.style.fill = 'var(--spotify-green)';
        }
        renderLibraryUI();
    };
}

// LIBRARY
function renderLibraryUI() {
    const container = document.getElementById('libraryContainer');
    if (!container || !db) return;
    const tx = db.transaction(['liked_songs', 'playlists'], 'readonly');
    let liked = [], playlists = [];
    tx.objectStore('liked_songs').getAll().onsuccess = (e) => { liked = e.target.result || []; };
    tx.objectStore('playlists').getAll().onsuccess = (e) => { playlists = e.target.result || []; };
    tx.oncomplete = () => {
        let html = '';
        html += '<div class="lib-item" onclick="openLikedSongs()">'+
            '<div class="lib-item-img liked"><svg viewBox="0 0 24 24" style="fill:white;width:28px;height:28px;"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg></div>'+
            '<div class="lib-item-info"><div class="lib-item-title">Lagu yang Disukai</div><div class="lib-item-sub">Playlist · ' + liked.length + ' lagu</div></div></div>';
        playlists.forEach(pl => {
            html += '<div class="lib-item" onclick="openPlaylist(\'' + pl.id + '\')">'+
                '<img class="lib-item-img" src="' + (pl.img || 'https://via.placeholder.com/64x64?text=music') + '" style="border-radius:4px;">'+
                '<div class="lib-item-info"><div class="lib-item-title">' + pl.name + '</div><div class="lib-item-sub">Playlist · ' + (pl.tracks ? pl.tracks.length : 0) + ' lagu</div></div></div>';
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
function openPlaylist(id) {
    if (!db) return;
    const tx = db.transaction('playlists', 'readonly');
    tx.objectStore('playlists').get(id).onsuccess = (e) => {
        const pl = e.target.result;
        if (!pl) return;
        document.getElementById('playlistNameDisplay').innerText = pl.name;
        document.getElementById('playlistStatsDisplay').innerText = (pl.tracks ? pl.tracks.length : 0) + ' lagu';
        document.getElementById('playlistImageDisplay').src = pl.img || 'https://via.placeholder.com/220x220?text=music';
        window._playlistTracks = pl.tracks || [];
        document.getElementById('playlistTracksContainer').innerHTML = (pl.tracks && pl.tracks.length > 0) ? pl.tracks.map(renderVItem).join('') : '<div style="color:var(--text-sub);padding:16px;">Playlist kosong.</div>';
        switchView('playlist');
    };
}
function playFirstPlaylistTrack() {
    if (window._playlistTracks && window._playlistTracks.length > 0) {
        const t = window._playlistTracks[0];
        playMusic(t.videoId, makeTrackData(t));
    }
}

// CREATE PLAYLIST
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

// ADD TO PLAYLIST
function openAddToPlaylistModal() {
    if (!currentTrack || !db) return;
    document.getElementById('addToPlaylistModal').style.display = 'flex';
    const tx = db.transaction('playlists', 'readonly');
    tx.objectStore('playlists').getAll().onsuccess = (e) => {
        const playlists = e.target.result || [];
        const list = document.getElementById('addToPlaylistList');
        if (playlists.length === 0) {
            list.innerHTML = '<div style="color:var(--text-sub);padding:16px;">Belum ada playlist.</div>';
        } else {
            list.innerHTML = playlists.map(pl =>
                '<div class="v-item" onclick="addTrackToPlaylist(\'' + pl.id + '\')">'+
                '<img class="v-img" src="' + (pl.img || 'https://via.placeholder.com/48x48?text=music') + '">'+
                '<div class="v-info"><div class="v-title">' + pl.name + '</div><div class="v-sub">' + (pl.tracks ? pl.tracks.length : 0) + ' lagu</div></div></div>'
            ).join('');
        }
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
function getSettings() {
    try { return JSON.parse(localStorage.getItem('auspotySettings') || '{}'); } catch(e) { return {}; }
}
function saveSettings(obj) {
    const s = Object.assign(getSettings(), obj);
    localStorage.setItem('auspotySettings', JSON.stringify(s));
}
function applyAllSettings() {
    const s = getSettings();
    if (s.darkMode === false) document.body.classList.add('light-mode');
    else document.body.classList.remove('light-mode');
    const themes = { green: '#1ed760', blue: '#2196f3', red: '#e8115b', purple: '#8d67ab', orange: '#ff9800' };
    const color = themes[s.theme] || themes.green;
    document.documentElement.style.setProperty('--spotify-green', color);
    document.documentElement.style.setProperty('--spotify-green-dark', color);
    const sizes = { small: '14px', normal: '16px', large: '18px', xlarge: '20px' };
    document.documentElement.style.setProperty('--base-font-size', sizes[s.fontSize] || '16px');
    const themeNames = { green: 'Hijau (Default)', blue: 'Biru', red: 'Merah', purple: 'Ungu', orange: 'Oranye' };
    const el = document.getElementById('themeLabel'); if (el) el.innerText = themeNames[s.theme] || 'Hijau (Default)';
    const ql = document.getElementById('qualityLabel'); if (ql) ql.innerText = s.quality || 'Auto';
    const fl = document.getElementById('fontSizeLabel'); if (fl) fl.innerText = ({ small:'Kecil', normal:'Normal', large:'Besar', xlarge:'Sangat Besar' })[s.fontSize] || 'Normal';
    const ll = document.getElementById('langLabel'); if (ll) ll.innerText = s.language || 'Indonesia';
    const rl = document.getElementById('regionLabel'); if (rl) rl.innerText = s.region || 'Indonesia';
    setToggle('darkModeToggle', s.darkMode !== false);
    setToggle('autoplayToggle', s.autoplay !== false);
    setToggle('crossfadeToggle', !!s.crossfade);
    setToggle('normalizeToggle', !!s.normalize);
    setToggle('lyricsSyncToggle', s.lyricsSync !== false);
    setToggle('notifNowPlayingToggle', s.notifNowPlaying !== false);
    setToggle('notifNewReleaseToggle', !!s.notifNewRelease);
    const pname = document.getElementById('settingsProfileName'); if (pname) pname.innerText = s.profileName || 'Pengguna Auspoty';
    const pav = document.getElementById('settingsAvatar'); if (pav) pav.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
    estimateCacheSize();
}
function setToggle(id, active) {
    const el = document.getElementById(id); if (!el) return;
    if (active) el.classList.add('active'); else el.classList.remove('active');
}
function toggleDarkMode() { const s = getSettings(); s.darkMode = s.darkMode === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleAutoplay() { const s = getSettings(); s.autoplay = s.autoplay === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleCrossfade() { const s = getSettings(); s.crossfade = !s.crossfade; saveSettings(s); applyAllSettings(); }
function toggleNormalize() { const s = getSettings(); s.normalize = !s.normalize; saveSettings(s); applyAllSettings(); }
function toggleLyricsSync() { const s = getSettings(); s.lyricsSync = s.lyricsSync === false ? true : false; saveSettings(s); applyAllSettings(); }
function toggleNotif(key) {
    const s = getSettings();
    const k = 'notif' + key.charAt(0).toUpperCase() + key.slice(1);
    s[k] = !s[k]; saveSettings(s); applyAllSettings();
}

// PICKER
let pickerCallback = null;
function openPicker(title, options, currentVal, cb) {
    pickerCallback = cb;
    document.getElementById('pickerTitle').innerText = title;
    document.getElementById('pickerOptions').innerHTML = options.map(o =>
        '<div class="picker-option' + (o.value === currentVal ? ' selected' : '') + '" onclick="selectPickerOption(\'' + o.value + '\')">'+
        o.label + (o.value === currentVal ? '<svg class="picker-check" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>' : '') + '</div>'
    ).join('');
    document.getElementById('pickerOverlay').classList.add('open');
    document.getElementById('pickerModal').classList.add('open');
}
function selectPickerOption(val) { if (pickerCallback) pickerCallback(val); closePicker(); }
function closePicker() {
    document.getElementById('pickerOverlay').classList.remove('open');
    document.getElementById('pickerModal').classList.remove('open');
    pickerCallback = null;
}
function openThemePicker() {
    const s = getSettings();
    openPicker('Tema Warna', [
        { label: 'Hijau (Default)', value: 'green' },
        { label: 'Biru', value: 'blue' },
        { label: 'Merah', value: 'red' },
        { label: 'Ungu', value: 'purple' },
        { label: 'Oranye', value: 'orange' },
    ], s.theme || 'green', (val) => { saveSettings({ theme: val }); applyAllSettings(); });
}
function openQualityPicker() {
    const s = getSettings();
    openPicker('Kualitas Audio', [
        { label: 'Auto', value: 'Auto' },
        { label: 'Rendah - 64 kbps', value: 'Rendah 64kbps' },
        { label: 'Sedang - 128 kbps', value: 'Sedang 128kbps' },
        { label: 'Tinggi - 256 kbps', value: 'Tinggi 256kbps' },
        { label: 'Sangat Tinggi - 320 kbps', value: 'Sangat Tinggi 320kbps' },
    ], s.quality || 'Auto', (val) => { saveSettings({ quality: val }); applyAllSettings(); });
}
function openFontSizePicker() {
    const s = getSettings();
    openPicker('Ukuran Teks', [
        { label: 'Kecil', value: 'small' },
        { label: 'Normal', value: 'normal' },
        { label: 'Besar', value: 'large' },
        { label: 'Sangat Besar', value: 'xlarge' },
    ], s.fontSize || 'normal', (val) => { saveSettings({ fontSize: val }); applyAllSettings(); });
}
function openLanguagePicker() {
    const s = getSettings();
    openPicker('Bahasa Aplikasi', [
        { label: 'Indonesia', value: 'Indonesia' },
        { label: 'English', value: 'English' },
        { label: 'Japanese', value: 'Japanese' },
        { label: 'Korean', value: 'Korean' },
    ], s.language || 'Indonesia', (val) => { saveSettings({ language: val }); applyAllSettings(); });
}
function openRegionPicker() {
    const s = getSettings();
    openPicker('Wilayah Konten', [
        { label: 'Indonesia', value: 'Indonesia' },
        { label: 'Global', value: 'Global' },
        { label: 'Amerika Serikat', value: 'Amerika Serikat' },
        { label: 'Jepang', value: 'Jepang' },
        { label: 'Korea', value: 'Korea' },
    ], s.region || 'Indonesia', (val) => { saveSettings({ region: val }); applyAllSettings(); });
}

// EDIT PROFILE
function openEditProfile() {
    const s = getSettings();
    document.getElementById('editProfileName').value = s.profileName || '';
    document.getElementById('editProfileAvatar').innerText = (s.profileName || 'A').charAt(0).toUpperCase();
    document.getElementById('editProfileModal').style.display = 'flex';
}
function closeEditProfile() { document.getElementById('editProfileModal').style.display = 'none'; }
function saveProfile() {
    const name = document.getElementById('editProfileName').value.trim() || 'Pengguna Auspoty';
    saveSettings({ profileName: name }); applyAllSettings(); closeEditProfile(); showToast('Profil disimpan!');
}

// CACHE
function estimateCacheSize() {
    const el = document.getElementById('cacheSize'); if (!el) return;
    if ('storage' in navigator && 'estimate' in navigator.storage) {
        navigator.storage.estimate().then(({ usage }) => {
            el.innerText = (usage / (1024 * 1024)).toFixed(1) + ' MB digunakan';
        }).catch(() => { el.innerText = 'Tidak dapat dihitung'; });
    } else { el.innerText = 'Tidak tersedia'; }
}
function clearCache() {
    if ('caches' in window) {
        caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))).then(() => { showToast('Cache berhasil dihapus!'); estimateCacheSize(); });
    } else { showToast('Tidak ada cache untuk dihapus'); }
}
function clearLikedSongs() {
    if (!db) return;
    if (!confirm('Hapus semua lagu yang disukai?')) return;
    const tx = db.transaction('liked_songs', 'readwrite');
    tx.objectStore('liked_songs').clear();
    tx.oncomplete = () => { showToast('Lagu disukai dihapus!'); renderLibraryUI(); };
}


// DOWNLOAD
async function downloadMusic() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    const btn = document.getElementById('downloadBtn');
    const btnMini = document.getElementById('downloadBtnMini');
    [btn, btnMini].forEach(b => { if (b) { b.style.opacity = '0.4'; b.style.pointerEvents = 'none'; } });
    showToast('Menyiapkan MP3... tunggu sebentar');
    try {
        const API = (typeof API_BASE !== 'undefined') ? API_BASE : '';
        const res = await fetch(API + '/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ videoId: currentTrack.videoId, title: currentTrack.title })
        });
        const result = await res.json();
        if (result.status === 'success' && result.url) {
            const a = document.createElement('a');
            a.href = result.url;
            a.download = (result.title || currentTrack.title).replace(/[\/:*?"<>|]/g, '_') + '.mp3';
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => document.body.removeChild(a), 1000);
            showToast('Download MP3 dimulai!');
        } else {
            showToast('Gagal: ' + (result.message || 'Coba lagi'));
        }
    } catch (e) {
        showToast('Gagal koneksi ke server');
    } finally {
        [btn, btnMini].forEach(b => { if (b) { b.style.opacity = '1'; b.style.pointerEvents = ''; } });
    }
}



// ===================== GOOGLE LOGIN =====================
// Login Google via Firebase Auth — tidak butuh Google Cloud Console
// Setup: console.firebase.google.com → Authentication → Google → Enable
// Lalu ganti FIREBASE_CONFIG di index.html

function loginWithGoogle() {
    const user = getGoogleUser();
    if (user) return;
    if (window._firebaseSignIn) {
        window._firebaseSignIn();
    } else {
        document.getElementById('loginModal').style.display = 'flex';
    }
}

function _showFirebaseSetupInfo() {
    document.getElementById('loginModal').style.display = 'flex';
}

function closeLoginModal() {
    const m = document.getElementById('loginModal');
    if (m) m.style.display = 'none';
}

function handleGoogleLogin(response) {}

function getGoogleUser() {
    try { return JSON.parse(localStorage.getItem('auspotyGoogleUser') || 'null'); } catch(e) { return null; }
}

function updateProfileUI() {
    const user = getGoogleUser();
    const s = getSettings();
    const loginBtn = document.getElementById('googleLoginBtn');
    const logoutBtn = document.getElementById('googleLogoutBtn');
    if (user) {
        const av = document.getElementById('settingsAvatar');
        if (av) {
            if (user.picture) {
                av.innerHTML = '<img src="' + user.picture + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
            } else {
                av.innerText = user.name.charAt(0).toUpperCase();
            }
        }
        const pname = document.getElementById('settingsProfileName');
        if (pname) pname.innerText = user.name;
        const psub = document.getElementById('settingsProfileSub');
        if (psub) psub.innerText = user.email;
        const logoutSub = document.getElementById('googleLogoutSub');
        if (logoutSub) logoutSub.innerText = user.email;
        const homeAv = document.querySelector('.app-avatar');
        if (homeAv) {
            if (user.picture) {
                homeAv.innerHTML = '<img src="' + user.picture + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
            } else {
                homeAv.innerText = user.name.charAt(0).toUpperCase();
            }
        }
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'block';
    } else {
        const av = document.getElementById('settingsAvatar');
        if (av) av.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
        const pname = document.getElementById('settingsProfileName');
        if (pname) pname.innerText = s.profileName || 'Pengguna Auspoty';
        const psub = document.getElementById('settingsProfileSub');
        if (psub) psub.innerText = 'Auspoty Premium';
        if (loginBtn) loginBtn.style.display = 'block';
        if (logoutBtn) logoutBtn.style.display = 'none';
    }
}

function logoutFromGoogle() {
    if (!confirm('Keluar dari akun Google?')) return;
    if (window._firebaseSignOut) {
        window._firebaseSignOut();
    } else {
        localStorage.removeItem('auspotyGoogleUser');
        updateProfileUI();
        showToast('Berhasil keluar');
    }
}
// INIT
applyAllSettings();
updateProfileUI();
loadHomeData();
renderSearchCategories();
