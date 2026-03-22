"""
Rebuild bagian core script.js yang rusak:
- Ambil bagian sebelum playMusic (bersih)
- Tulis ulang playMusic, _playNativeStream, togglePlay, updatePlayPauseBtn, 
  expandPlayer, minimizePlayer, startProgressBar, stopProgressBar, seekTo, formatTime
- Lanjutkan dari toggleRepeat ke akhir
"""

content = open('public/script.js', encoding='utf-8').read()
lines = content.split('\n')

# Cari baris pertama "function playMusic"
play_music_start = None
for i, l in enumerate(lines):
    if l.strip().startswith('function playMusic('):
        play_music_start = i
        break

# Cari baris "function toggleRepeat"
toggle_repeat_start = None
for i, l in enumerate(lines):
    if l.strip().startswith('function toggleRepeat('):
        toggle_repeat_start = i
        break

print(f"playMusic: line {play_music_start+1}")
print(f"toggleRepeat: line {toggle_repeat_start+1}")

before = '\n'.join(lines[:play_music_start])
after  = '\n'.join(lines[toggle_repeat_start:])

core = '''// ============================================================
// PLAY MUSIC — fungsi utama
// APK mode: stream via just_audio Flutter (background + notifikasi)
// Web/PWA mode: stream via YouTube IFrame
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
    document.getElementById('currentTime').innerText = '0:00';
    document.getElementById('totalTime').innerText = '0:00';

    if (window.flutter_inappwebview) {
        _playNativeStream(videoId, currentTrack);
    } else {
        if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);
        _startBgKeepAlive();
    }

    setTimeout(() => {
        if (currentTrack && _autoQueue.length < 2) prefetchNextSongs(currentTrack.artist, currentTrack.videoId);
    }, 2000);
}

// Fetch stream URL dari API lalu kirim ke Flutter just_audio + notifikasi media
async function _playNativeStream(videoId, track) {
    window._nativeLoading = true;
    window._nativePlaying = false;
    isPlaying = false;
    updatePlayPauseBtn(false);
    if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo();
    try {
        const res = await apiFetch('/api/stream?video_id=' + videoId);
        const data = await res.json();
        if (!data.url) throw new Error('no url');
        await window.flutter_inappwebview.callHandler('playStream',
            data.url,
            track.title || 'Auspoty',
            track.artist || '',
            track.img || ''
        );
        window._nativeLoading = false;
        window._nativePlaying = true;
        isPlaying = true;
        updatePlayPauseBtn(true);
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
    } catch(e) {
        window._nativeLoading = false;
        showToast('Gagal memuat audio, coba lagi');
        updatePlayPauseBtn(false);
    }
}

// TOGGLE PLAY
function togglePlay() {
    if (window.flutter_inappwebview) {
        if (isPlaying) {
            window.flutter_inappwebview.callHandler('pauseAudio');
            isPlaying = false;
            window._nativePlaying = false;
            updatePlayPauseBtn(false);
            if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
        } else {
            window.flutter_inappwebview.callHandler('resumeAudio');
            isPlaying = true;
            window._nativePlaying = true;
            updatePlayPauseBtn(true);
            if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        }
        return;
    }
    if (!ytPlayer) return;
    if (isPlaying) { ytPlayer.pauseVideo(); } else { ytPlayer.playVideo(); }
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
        if (window.flutter_inappwebview) return; // APK: progress dihandle Flutter timer
        if (ytPlayer && ytPlayer.getCurrentTime && ytPlayer.getDuration) {
            const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration();
            if (dur > 0) {
                const pct = (cur / dur) * 100;
                const bar = document.getElementById('progressBar');
                if (bar) { bar.value = pct; bar.style.background = 'linear-gradient(to right, white ' + pct + '%, rgba(255,255,255,0.2) ' + pct + '%)'; }
                const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);
                const tt = document.getElementById('totalTime'); if (tt) tt.innerText = formatTime(dur);
            }
        }
    }, 1000);
}
function stopProgressBar() { clearInterval(progressInterval); }

function seekTo(value) {
    if (window.flutter_inappwebview) {
        window.flutter_inappwebview.callHandler('seekAudio', value);
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

'''

result = before + '\n' + core + after
open('public/script.js', 'w', encoding='utf-8').write(result)
print("Done!")
print(f"Total lines: {len(result.split(chr(10)))}")

# Verifikasi
c = open('public/script.js', encoding='utf-8').read()
checks = ['_playNativeStream', "callHandler('playStream'", "callHandler('pauseAudio'", 
          "callHandler('seekAudio'", 'function togglePlay', 'function seekTo',
          'function updatePlayPauseBtn', 'function startProgressBar']
for ch in checks:
    print(f"{'OK' if ch in c else 'MISSING'}: {ch}")
