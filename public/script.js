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
const HOME_QUERIES_BY_LANG = {
    Indonesia: [
        { id: 'rowAnyar',   query: 'lagu indonesia terbaru 2025' },
        { id: 'rowGembira', query: 'lagu semangat gembira indonesia' },
        { id: 'rowCharts',  query: 'top hits indonesia 2025' },
        { id: 'rowGalau',   query: 'lagu galau sedih indonesia' },
        { id: 'rowTiktok',  query: 'viral tiktok indonesia 2025' },
        { id: 'rowHits',    query: 'lagu hits hari ini indonesia' },
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
        { id: 'rowAnyar',   query: 'top global songs 2025' },
        { id: 'rowGembira', query: 'happy pop songs 2025' },
        { id: 'rowCharts',  query: 'billboard hot 100 2025' },
        { id: 'rowGalau',   query: 'sad songs 2025' },
        { id: 'rowTiktok',  query: 'viral tiktok global 2025' },
        { id: 'rowHits',    query: 'trending songs worldwide 2025' },
    ],
    'Amerika Serikat': [
        { id: 'rowAnyar',   query: 'new american songs 2025' },
        { id: 'rowGembira', query: 'upbeat american pop 2025' },
        { id: 'rowCharts',  query: 'us top charts 2025' },
        { id: 'rowGalau',   query: 'sad american songs 2025' },
        { id: 'rowTiktok',  query: 'viral tiktok usa 2025' },
        { id: 'rowHits',    query: 'us trending songs today' },
    ],
    Jepang: [
        { id: 'rowAnyar',   query: 'japanese new songs 2025' },
        { id: 'rowGembira', query: 'japanese happy songs 2025' },
        { id: 'rowCharts',  query: 'japan oricon chart 2025' },
        { id: 'rowGalau',   query: 'japanese sad songs 2025' },
        { id: 'rowTiktok',  query: 'japan viral tiktok 2025' },
        { id: 'rowHits',    query: 'japanese trending today' },
    ],
    Korea: [
        { id: 'rowAnyar',   query: 'kpop new songs 2025' },
        { id: 'rowGembira', query: 'kpop happy songs 2025' },
        { id: 'rowCharts',  query: 'kpop melon chart 2025' },
        { id: 'rowGalau',   query: 'kpop sad songs 2025' },
        { id: 'rowTiktok',  query: 'kpop viral tiktok 2025' },
        { id: 'rowHits',    query: 'kpop trending today' },
    ],
};
const SECTION_TITLES_BY_LANG = {
    Indonesia: ['Sering kamu dengarkan','Rilis Anyar','Gembira & Semangat','Tangga Lagu Populer','Galau Terpopuler','Viral TikTok','Artis Terpopuler','Hit Hari Ini'],
    English:   ['Recently Played','New Releases','Happy & Energetic','Top Charts','Sad Songs','Viral TikTok','Popular Artists','Hits Today'],
    Japanese:  ['最近再生','新着リリース','元気な曲','人気チャート','悲しい曲','バイラルTikTok','人気アーティスト','今日のヒット'],
    Korean:    ['최근 재생','신규 발매','신나는 노래','인기 차트','슬픈 노래','바이럴 틱톡','인기 아티스트','오늘의 히트'],
};
function getHomeQueries() {
    const s = getSettings();
    const region = s.region || 'Indonesia';
    const lang = s.language || 'Indonesia';
    // Region override dulu, kalau ada
    if (HOME_QUERIES_BY_REGION && HOME_QUERIES_BY_REGION[region]) {
        return HOME_QUERIES_BY_REGION[region];
    }
    return HOME_QUERIES_BY_LANG[lang] || HOME_QUERIES_BY_LANG.Indonesia;
}
function applyLanguageTitles() {
    const lang = getSettings().language || 'Indonesia';
    const titles = SECTION_TITLES_BY_LANG[lang] || SECTION_TITLES_BY_LANG.Indonesia;
    const titleEls = document.querySelectorAll('.section-title');
    const titleMap = ['Sering','Rilis','Gembira','Tangga','Galau','Viral','Artis','Hit'];
    titleEls.forEach((el, i) => { if (titles[i]) el.innerText = titles[i]; });
}

function applyUILanguage() {
    const lang = getSettings().language || 'Indonesia';
    const t = UI_STRINGS[lang] || UI_STRINGS.Indonesia;
    function setText(id, val) { const el = document.getElementById(id); if (el) el.innerText = val; }
    function setAttr(id, attr, val) { const el = document.getElementById(id); if (el) el.setAttribute(attr, val); }
    function setQueryAll(sel, val) { document.querySelectorAll(sel).forEach(el => { if (el.innerText.trim()) el.innerText = val; }); }

    // Nav items
    const navItems = document.querySelectorAll('.nav-item');
    if (navItems[0]) navItems[0].childNodes[navItems[0].childNodes.length-1].textContent = t.navHome;
    if (navItems[1]) navItems[1].childNodes[navItems[1].childNodes.length-1].textContent = t.navSearch;
    if (navItems[2]) navItems[2].childNodes[navItems[2].childNodes.length-1].textContent = t.navLibrary;
    if (navItems[3]) navItems[3].childNodes[navItems[3].childNodes.length-1].textContent = t.navSettings;

    // Search
    setAttr('searchInput', 'placeholder', t.searchPlaceholder);
    const searchH1 = document.querySelector('#view-search .search-header-container h1');
    if (searchH1) searchH1.innerText = t.searchTitle;
    const browseTitle = document.querySelector('#searchCategoriesUI .section-title');
    if (browseTitle) browseTitle.innerText = t.searchBrowse;

    // Library
    const libTitle = document.querySelector('.lib-title');
    if (libTitle) libTitle.innerText = t.libTitle;

    // Settings header
    const settH1 = document.querySelector('#view-settings .settings-header h1');
    if (settH1) settH1.innerText = t.settingsTitle;

    // Settings group labels
    const groupLabels = document.querySelectorAll('.settings-group-label');
    const labelKeys = ['settingsDisplay','settingsLangRegion','settingsPlayback','settingsNotif','settingsStorage','settingsAbout'];
    groupLabels.forEach((el, i) => { if (labelKeys[i] && t[labelKeys[i]]) el.innerText = t[labelKeys[i]]; });

    // Settings item titles (by order in settings groups)
    const allSettingsTitles = document.querySelectorAll('.settings-item-title');
    const titleMap = [
        null, // login/logout - skip
        null,
        t.settingsTheme,
        t.settingsDark,
        t.settingsQuality,
        t.settingsFontSize,
        t.settingsLang,
        t.settingsRegion,
        t.settingsAutoplay,
        t.settingsCrossfade,
        t.settingsNormalize,
        t.settingsLyricsSync,
        t.settingsNotifSong,
        t.settingsNotifRelease,
        t.settingsClearCache,
        t.settingsClearLiked,
        t.settingsDeveloper,
        t.settingsVersion,
    ];
    // Lebih aman: cari by ID atau data attribute
    // Gunakan querySelector dengan text matching
    const settingsItemMap = {
        'Tema Warna': t.settingsTheme, 'Color Theme': t.settingsTheme, 'カラーテーマ': t.settingsTheme, '색상 테마': t.settingsTheme,
        'Mode Gelap': t.settingsDark, 'Dark Mode': t.settingsDark, 'ダークモード': t.settingsDark, '다크 모드': t.settingsDark,
        'Kualitas Audio': t.settingsQuality, 'Audio Quality': t.settingsQuality, '音質': t.settingsQuality, '음질': t.settingsQuality,
        'Ukuran Teks': t.settingsFontSize, 'Text Size': t.settingsFontSize, '文字サイズ': t.settingsFontSize, '텍스트 크기': t.settingsFontSize,
        'Bahasa Aplikasi': t.settingsLang, 'App Language': t.settingsLang, 'アプリの言語': t.settingsLang, '앱 언어': t.settingsLang,
        'Wilayah Konten': t.settingsRegion, 'Content Region': t.settingsRegion, 'コンテンツ地域': t.settingsRegion, '콘텐츠 지역': t.settingsRegion,
        'Putar Otomatis': t.settingsAutoplay, 'Autoplay': t.settingsAutoplay, '自動再生': t.settingsAutoplay, '자동 재생': t.settingsAutoplay,
        'Crossfade': t.settingsCrossfade, 'クロスフェード': t.settingsCrossfade, '크로스페이드': t.settingsCrossfade,
        'Normalisasi Volume': t.settingsNormalize, 'Volume Normalization': t.settingsNormalize, '音量正規化': t.settingsNormalize, '볼륨 정규화': t.settingsNormalize,
        'Sinkronisasi Lirik': t.settingsLyricsSync, 'Lyrics Sync': t.settingsLyricsSync, '歌詞同期': t.settingsLyricsSync, '가사 동기화': t.settingsLyricsSync,
        'Notifikasi Lagu': t.settingsNotifSong, 'Now Playing Notification': t.settingsNotifSong, '再生中の通知': t.settingsNotifSong, '재생 중 알림': t.settingsNotifSong,
        'Rilis Baru': t.settingsNotifRelease, 'New Releases': t.settingsNotifRelease, '新着リリース': t.settingsNotifRelease, '새 릴리스': t.settingsNotifRelease,
        'Hapus Cache': t.settingsClearCache, 'Clear Cache': t.settingsClearCache, 'キャッシュを削除': t.settingsClearCache, '캐시 지우기': t.settingsClearCache,
        'Hapus Lagu Disukai': t.settingsClearLiked, 'Clear Liked Songs': t.settingsClearLiked, 'お気に入りを削除': t.settingsClearLiked, '좋아요 삭제': t.settingsClearLiked,
        'Developer': t.settingsDeveloper,
        'Versi Aplikasi': t.settingsVersion, 'App Version': t.settingsVersion, 'アプリバージョン': t.settingsVersion, '앱 버전': t.settingsVersion,
        'Masuk dengan Google': t.loginGoogle, 'Sign in with Google': t.loginGoogle, 'Googleでサインイン': t.loginGoogle, 'Google로 로그인': t.loginGoogle,
    };
    document.querySelectorAll('.settings-item-title').forEach(el => {
        const txt = el.innerText.trim();
        if (settingsItemMap[txt]) el.innerText = settingsItemMap[txt];
    });

    // Login/logout sub text
    setText('googleLoginText', t.loginGoogle);
    setText('googleLoginSub', t.loginSub);

    // Home pills
    const pills = document.querySelectorAll('#view-home .pill');
    if (pills[0]) pills[0].innerText = t.homePillAll;
    if (pills[1]) pills[1].innerText = t.homePillMusic;
    if (pills[2]) pills[2].innerText = t.homePillPodcast;
}
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
    applyLanguageTitles();
    applyUILanguage();
    for (const row of getHomeQueries()) {
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

    // Tema warna — update --accent, --accent2, --spotify-green sekaligus
    const themes = {
        green:  { a: '#a78bfa', b: '#f472b6', g: '#a78bfa' },
        blue:   { a: '#38bdf8', b: '#818cf8', g: '#38bdf8' },
        red:    { a: '#f87171', b: '#fb923c', g: '#f87171' },
        purple: { a: '#c084fc', b: '#e879f9', g: '#c084fc' },
        orange: { a: '#fb923c', b: '#fbbf24', g: '#fb923c' },
    };
    const t = themes[s.theme] || themes.green;
    document.documentElement.style.setProperty('--accent', t.a);
    document.documentElement.style.setProperty('--accent2', t.b);
    document.documentElement.style.setProperty('--spotify-green', t.g);
    document.documentElement.style.setProperty('--spotify-green-dark', t.g);

    // Font size via body class
    document.body.classList.remove('font-small','font-normal','font-large','font-xlarge');
    const fsMap = { small:'font-small', normal:'font-normal', large:'font-large', xlarge:'font-xlarge' };
    document.body.classList.add(fsMap[s.fontSize] || 'font-normal');

    const themeNames = { green: 'Ungu-Pink (Default)', blue: 'Biru-Indigo', red: 'Merah-Oranye', purple: 'Ungu-Magenta', orange: 'Oranye-Kuning' };
    const el = document.getElementById('themeLabel'); if (el) el.innerText = themeNames[s.theme] || 'Ungu-Pink (Default)';
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
    const pav = document.getElementById('settingsAvatar'); if (pav && !pav.querySelector('img')) pav.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
    estimateCacheSize();
    applyUILanguage();
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
        { label: 'Ungu-Pink (Default)', value: 'green' },
        { label: 'Biru-Indigo', value: 'blue' },
        { label: 'Merah-Oranye', value: 'red' },
        { label: 'Ungu-Magenta', value: 'purple' },
        { label: 'Oranye-Kuning', value: 'orange' },
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
    ], s.language || 'Indonesia', (val) => { saveSettings({ language: val }); applyAllSettings(); loadHomeData(); });
}
function openRegionPicker() {
    const s = getSettings();
    openPicker('Wilayah Konten', [
        { label: 'Indonesia', value: 'Indonesia' },
        { label: 'Global', value: 'Global' },
        { label: 'Amerika Serikat', value: 'Amerika Serikat' },
        { label: 'Jepang', value: 'Jepang' },
        { label: 'Korea', value: 'Korea' },
    ], s.region || 'Indonesia', (val) => { saveSettings({ region: val }); applyAllSettings(); loadHomeData(); });
}

// EDIT PROFILE
function openEditProfile() {
    var s = getSettings();
    var user = getGoogleUser();
    var nameInput = document.getElementById('editProfileName');
    if (nameInput) nameInput.value = s.profileName || (user ? user.name : '');
    var av = document.getElementById('editProfileAvatar');
    var customPhoto = localStorage.getItem('auspotyCustomPhoto');
    if (av) {
        var photoSrc = customPhoto || (user ? user.picture : null);
        if (photoSrc) {
            av.innerHTML = '<img src="' + photoSrc + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">';
        } else {
            av.innerHTML = '';
            av.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
        }
    }
    var modal = document.getElementById('editProfileModal');
    if (modal) { modal.style.display = 'flex'; }
}
function closeEditProfile() { document.getElementById('editProfileModal').style.display = 'none'; }
function saveProfile() {
    const name = document.getElementById('editProfileName').value.trim() || 'Pengguna Auspoty';
    saveSettings({ profileName: name });
    applyAllSettings();
    updateProfileUI();
    closeEditProfile();
    showToast('Profil disimpan!');
}

function previewProfilePhoto(event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        var dataUrl = e.target.result;
        localStorage.setItem('auspotyCustomPhoto', dataUrl);
        var av = document.getElementById('editProfileAvatar');
        if (av) av.innerHTML = '<img src="' + dataUrl + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">';
        updateProfileUI();
        showToast('Foto profil diperbarui!');
    };
    reader.readAsDataURL(file);
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

// REPEAT & PREV/NEXT
let isRepeat = false;
let songHistory = [];
function toggleRepeat() {
    isRepeat = !isRepeat;
    const btn = document.getElementById('repeatBtn');
    if (btn) btn.style.fill = isRepeat ? 'var(--accent)' : 'var(--text-sub)';
    showToast(isRepeat ? 'Ulangi lagu: Aktif' : 'Ulangi lagu: Nonaktif');
}
function playPrevSong() {
    if (songHistory.length < 2) { showToast('Tidak ada lagu sebelumnya'); return; }
    songHistory.pop();
    const prev = songHistory[songHistory.length - 1];
    if (prev) playMusic(prev.videoId, makeTrackData(prev));
}
function playNextSong() { playNextSimilarSong(); }

// COMMENTS
function openCommentsModal() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    document.getElementById('commentsModal').style.display = 'flex';
    document.getElementById('commentTrackName').innerText = currentTrack.title + ' — ' + currentTrack.artist;
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
        const q = window._fsQuery(window._fsCollection(db_fs,'comments'),window._fsWhere('videoId','==',videoId));
        const snap = await window._fsGetDocs(q);
        if (snap.empty) { list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Belum ada komentar. Jadilah yang pertama!</div>'; return; }
        const docs = snap.docs.map(d=>d.data()).sort((a,b)=>(b.createdAt?.seconds||0)-(a.createdAt?.seconds||0));
        list.innerHTML = docs.map(d => {
            const time = d.createdAt ? new Date(d.createdAt.seconds*1000).toLocaleDateString('id-ID',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
            const isAdmin = d.email === 'yusrilrizky149@gmail.com';
            const badge = isAdmin ? '<span style="background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;font-size:10px;font-weight:800;padding:2px 7px;border-radius:8px;margin-left:6px;letter-spacing:.5px;">ADMIN</span>' : '<span style="background:rgba(255,255,255,0.1);color:var(--text-sub);font-size:10px;font-weight:600;padding:2px 7px;border-radius:8px;margin-left:6px;">Pengguna</span>';
            return '<div style="display:flex;gap:10px;align-items:flex-start;"><div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;overflow:hidden;">'+(d.picture?'<img src="'+d.picture+'" style="width:100%;height:100%;object-fit:cover;">':d.name.charAt(0).toUpperCase())+'</div><div style="flex:1;background:'+(isAdmin?'rgba(245,158,11,0.08)':'rgba(255,255,255,0.06)')+';border-radius:12px;padding:10px 14px;border:'+(isAdmin?'1px solid rgba(245,158,11,0.3)':'1px solid transparent')+'"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;"><div style="display:flex;align-items:center;"><span style="font-size:13px;font-weight:700;color:'+(isAdmin?'#f59e0b':'var(--accent)')+';">'+d.name+'</span>'+badge+'</div><span style="font-size:11px;color:var(--text-sub);">'+time+'</span></div><p style="font-size:14px;color:white;line-height:1.5;margin:0;">'+d.text+'</p></div></div>';
        }).join('');
    } catch(e) { list.innerHTML = '<div style="color:#ff5252;text-align:center;padding:20px;font-size:13px;">Gagal: '+e.message+'</div>'; }
}
async function submitComment() {
    const user = getGoogleUser();
    if (!user) { showToast('Login dulu untuk berkomentar'); return; }
    if (!currentTrack) return;
    const input = document.getElementById('commentInput');
    const text = input.value.trim();
    if (!text) { showToast('Komentar tidak boleh kosong'); return; }
    try {
        await window._fsAddDoc(window._fsCollection(window._firestoreDB,'comments'),{videoId:currentTrack.videoId,name:user.name,email:user.email,picture:user.picture||'',text:text,createdAt:window._fsTimestamp()});
        input.value = '';
        showToast('Komentar terkirim!');
        loadComments(currentTrack.videoId);
    } catch(e) { showToast('Gagal kirim: '+e.message); }
}

// DOWNLOAD
function downloadMusic() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    window.open('https://id.ytmp3.mobi/v1/#' + currentTrack.videoId, '_blank');
    showToast('Halaman download dibuka. Klik Konversi lalu Unduh MP3');
}

// INIT
applyAllSettings();
loadHomeData();
renderSearchCategories();
function updateProfileUI() {
    const user = getGoogleUser();
    const s = getSettings();
    const loginBtn = document.getElementById('googleLoginBtn');
    const logoutBtn = document.getElementById('googleLogoutBtn');
    if (user) {
        const av = document.getElementById('settingsAvatar');
        if (av) { if (user.picture) { av.innerHTML = '<img src="'+user.picture+'" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">'; } else { av.innerText = user.name.charAt(0).toUpperCase(); } }
        const pname = document.getElementById('settingsProfileName'); if (pname) pname.innerText = user.name;
        const psub = document.getElementById('settingsProfileSub'); if (psub) psub.innerText = user.email;
        const logoutSub = document.getElementById('googleLogoutSub'); if (logoutSub) logoutSub.innerText = user.email;
        const homeAv = document.querySelector('.app-avatar');
        if (homeAv) { if (user.picture) { homeAv.innerHTML = '<img src="'+user.picture+'" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">'; } else { homeAv.innerText = user.name.charAt(0).toUpperCase(); } }
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'block';
    } else {
        const av = document.getElementById('settingsAvatar'); if (av) av.innerText = (s.profileName||'A').charAt(0).toUpperCase();
        const pname = document.getElementById('settingsProfileName'); if (pname) pname.innerText = s.profileName||'Pengguna Auspoty';
        const psub = document.getElementById('settingsProfileSub'); if (psub) psub.innerText = 'Auspoty Premium';
        if (loginBtn) loginBtn.style.display = 'block';
        if (logoutBtn) logoutBtn.style.display = 'none';
    }
}
function loginWithGoogle() { if (typeof window._firebaseSignIn==='function') window._firebaseSignIn(); }
function logoutFromGoogle() { if (typeof window._firebaseSignOut==='function') window._firebaseSignOut(); }
function getGoogleUser() { try { return JSON.parse(localStorage.getItem('auspotyGoogleUser')||'null'); } catch(e) { return null; } }
function previewProfilePhoto(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => { const av = document.getElementById('editProfileAvatar'); if (av) av.innerHTML = '<img src="'+e.target.result+'" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">'; localStorage.setItem('auspotyProfilePhoto', e.target.result); };
    reader.readAsDataURL(file);
}
function openEditProfile() {
    const s = getSettings(); const user = getGoogleUser();
    document.getElementById('editProfileName').value = user ? user.name : (s.profileName||'');
    const av = document.getElementById('editProfileAvatar');
    const photo = localStorage.getItem('auspotyProfilePhoto');
    const pic = (user&&user.picture) ? user.picture : photo;
    if (av) { if (pic) { av.innerHTML = '<img src="'+pic+'" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">'; } else { av.innerText = (user?user.name:(s.profileName||'A')).charAt(0).toUpperCase(); } }
    document.getElementById('editProfileModal').style.display = 'flex';
}
function closeEditProfile() { document.getElementById('editProfileModal').style.display = 'none'; }
function saveProfile() { const name = document.getElementById('editProfileName').value.trim()||'Pengguna Auspoty'; saveSettings({profileName:name}); applyAllSettings(); closeEditProfile(); showToast('Profil disimpan!'); }
function closeLoginModal() { document.getElementById('loginModal').style.display = 'none'; }
