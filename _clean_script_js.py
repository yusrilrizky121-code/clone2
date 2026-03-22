"""
Bersihkan script.js dari kode orphan/duplikat yang rusak.
Ambil bagian yang bersih dan tambahkan fungsi yang benar.
"""

content = open('public/script.js', encoding='utf-8').read()
lines = content.split('\n')

# Cari batas-batas fungsi yang rusak
# Strategi: ambil dari awal sampai sebelum playMusic yang pertama,
# lalu tulis ulang playMusic, togglePlay, seekTo yang bersih,
# lalu lanjutkan dari updatePlayPauseBtn dst.

# Cari baris pertama "function playMusic"
play_music_start = None
for i, l in enumerate(lines):
    if l.strip().startswith('function playMusic('):
        play_music_start = i
        break

print(f"playMusic starts at line {play_music_start + 1}")

# Cari baris "function updatePlayPauseBtn"
update_btn_start = None
for i, l in enumerate(lines):
    if l.strip().startswith('function updatePlayPauseBtn('):
        update_btn_start = i
        break

print(f"updatePlayPauseBtn starts at line {update_btn_start + 1}")

# Ambil bagian sebelum playMusic
before = '\n'.join(lines[:play_music_start])

# Ambil bagian dari updatePlayPauseBtn ke akhir
# Tapi skip semua kode orphan antara togglePlay dan updatePlayPauseBtn
after = '\n'.join(lines[update_btn_start:])

# Tulis ulang bagian tengah yang bersih
middle = '''// ============================================================
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
        // APK mode: fetch stream URL lalu kirim ke just_audio Flutter
        _playNativeStream(videoId, currentTrack);
    } else {
        // Web/PWA mode: pakai YouTube IFrame
        if (ytPlayer && ytPlayer.loadVideoById) {
            ytPlayer.loadVideoById(videoId);
        }
        _startBgKeepAlive();
    }

    setTimeout(() => {
        if (currentTrack && _autoQueue.length < 2) prefetchNextSongs(currentTrack.artist, currentTrack.videoId);
    }, 2000);
}

// Fetch stream URL dari API lalu kirim ke Flutter just_audio + notifikasi
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
    if (isPlaying) {
        ytPlayer.pauseVideo();
    } else {
        ytPlayer.playVideo();
    }
}

'''

# Cari baris "function seekTo" di after dan hapus versi lama jika ada duplikat
# Kita akan tambahkan seekTo yang benar setelah stopProgressBar

# Cari posisi stopProgressBar di after
after_lines = after.split('\n')
stop_pb_idx = None
for i, l in enumerate(after_lines):
    if l.strip().startswith('function stopProgressBar'):
        stop_pb_idx = i
        break

# Cari seekTo lama di after
seek_start = None
seek_end = None
for i, l in enumerate(after_lines):
    if l.strip().startswith('function seekTo('):
        seek_start = i
    if seek_start and i > seek_start and l.strip() == '}':
        seek_end = i
        break

print(f"stopProgressBar at after line {stop_pb_idx}")
print(f"seekTo at after lines {seek_start}-{seek_end}")

# Ganti seekTo lama dengan versi yang support APK
new_seek = '''function seekTo(value) {
    if (window.flutter_inappwebview) {
        window.flutter_inappwebview.callHandler('seekAudio', value);
        return;
    }
    if (!ytPlayer) return;
    const dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
    if (dur > 0) ytPlayer.seekTo(value / 100 * dur, true);
}'''

if seek_start is not None and seek_end is not None:
    after_lines[seek_start:seek_end+1] = new_seek.split('\n')
    after = '\n'.join(after_lines)

result = before + '\n' + middle + after

# Hapus kode orphan yang tersisa (sisa dari patch lama)
# Cari dan hapus blok orphan antara togglePlay dan updatePlayPauseBtn
import re

# Hapus blok orphan: kode yang dimulai dengan whitespace + "await window.flutter_inappwebview" tanpa konteks
# Pattern: baris yang dimulai dengan "}" lalu langsung ada kode orphan
# Lebih aman: hapus semua duplikat fungsi

# Hapus duplikat fungsi togglePlay (ambil hanya yang pertama)
def remove_duplicate_functions(text, func_name):
    pattern = rf'(// TOGGLE PLAY\nfunction {func_name}\(.*?\n\}})'
    matches = list(re.finditer(pattern, text, re.DOTALL))
    if len(matches) > 1:
        # Hapus semua kecuali yang pertama
        for m in reversed(matches[1:]):
            text = text[:m.start()] + text[m.end():]
    return text

# Hapus orphan code blocks (kode yang tidak dalam fungsi)
# Cari pola: "}" diikuti langsung kode yang tidak dimulai dengan function/var/let/const/if/for/class/async
lines_result = result.split('\n')
clean_lines = []
i = 0
skip_orphan = False
orphan_depth = 0

while i < len(lines_result):
    l = lines_result[i]
    # Deteksi orphan: baris yang dimulai dengan spaces + "await window.flutter" atau "isPlaying = true" tanpa konteks
    stripped = l.strip()
    # Orphan patterns dari patch lama
    if (stripped.startswith('await window.flutter_inappwebview.callHandler(\'playStream\'') or
        (stripped == 'isPlaying = true;' and i > 0 and lines_result[i-1].strip() == '') or
        stripped.startswith('window.AndroidBridge.playNative(') or
        (stripped.startswith('// Stop ytPlayer') and i > 0 and lines_result[i-1].strip().endswith('}'))):
        # Skip sampai closing brace
        depth = 0
        while i < len(lines_result):
            for c in lines_result[i]:
                if c == '{': depth += 1
                elif c == '}': depth -= 1
            if depth <= 0 and lines_result[i].strip() in ['}', '};', '}       ', '}       // Stop ytPlayer jika sedang jalan']:
                i += 1
                break
            i += 1
        continue
    clean_lines.append(l)
    i += 1

result = '\n'.join(clean_lines)

open('public/script.js', 'w', encoding='utf-8').write(result)
print("Done! script.js cleaned.")
print(f"Total lines: {len(result.split(chr(10)))}")
