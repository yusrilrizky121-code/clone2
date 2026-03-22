"""
Patch public/script.js:
- Hapus logika yang stop ytPlayer saat AndroidBridge.playNative dipanggil
- Audio tetap di ytPlayer, native hanya update notifikasi
"""

with open('public/script.js', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

print(f'File size: {len(content)} chars')

# Cari berbagai kemungkinan marker
markers = [
    '// *** KUNCI BACKGROUND AUDIO ***',
    'KUNCI BACKGROUND',
    'stopVideo',
    'nativeLoading = true',
    'AndroidBridge.playNative',
]
for m in markers:
    idx = content.find(m)
    print(f'  "{m}" at: {idx}')

# Coba replace langsung dengan string yang ditemukan
old1 = """    // *** KUNCI BACKGROUND AUDIO ***
    // Cek AndroidBridge.playNative (tersedia di APK Flutter)
    if (window.AndroidBridge && typeof window.AndroidBridge.playNative === 'function') {
        // Stop ytPlayer jika sedang jalan
        if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo();
        window._nativePlaying = false;
        window._nativeLoading = true;
        isPlaying = true;
        updatePlayPauseBtn(true);
        // Kirim ke ExoPlayer native — service fetch URL sendiri, tidak butuh Flutter engine
        window.AndroidBridge.playNative(
            videoId,
            currentTrack.title || '',
            currentTrack.artist || '',
            currentTrack.img || ''
        );
    } else {
        // Fallback: web/PWA pakai ytPlayer
        window._nativePlaying = false;
        window._nativeLoading = false;
        if (ytPlayer && ytPlayer.loadVideoById) ytPlayer.loadVideoById(videoId);
    }"""

new1 = """    // Audio selalu via ytPlayer (web & APK)
    // Di APK: AndroidBridge.playNative hanya update notifikasi, tidak stop ytPlayer
    window._nativePlaying = false;
    window._nativeLoading = false;
    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
    }
    // Kirim info ke notifikasi native (jika di APK)
    if (window.AndroidBridge && typeof window.AndroidBridge.playNative === 'function') {
        window.AndroidBridge.playNative(
            videoId,
            currentTrack.title || '',
            currentTrack.artist || '',
            currentTrack.img || ''
        );
    }"""

if old1 in content:
    content = content.replace(old1, new1)
    print('Replaced with CRLF-style match')
else:
    # Coba dengan \r\n
    old1_crlf = old1.replace('\n', '\r\n')
    if old1_crlf in content:
        new1_crlf = new1.replace('\n', '\r\n')
        content = content.replace(old1_crlf, new1_crlf)
        print('Replaced with CRLF match')
    else:
        print('NOT FOUND - trying line by line approach')
        lines = content.splitlines(keepends=True)
        out = []
        i = 0
        skip_until = None
        in_block = False
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if 'KUNCI BACKGROUND AUDIO' in line:
                in_block = True
                print(f'  Found KUNCI at line {i}')
            if in_block:
                # Skip until we find the closing else block end
                if stripped == '}' and i > 0:
                    # Check if this closes the else block
                    in_block = False
                    # Write new block
                    out.append("""    // Audio selalu via ytPlayer (web & APK)
    // Di APK: AndroidBridge.playNative hanya update notifikasi, tidak stop ytPlayer
    window._nativePlaying = false;
    window._nativeLoading = false;
    if (ytPlayer && ytPlayer.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
    }
    // Kirim info ke notifikasi native (jika di APK)
    if (window.AndroidBridge && typeof window.AndroidBridge.playNative === 'function') {
        window.AndroidBridge.playNative(
            videoId,
            currentTrack.title || '',
            currentTrack.artist || '',
            currentTrack.img || ''
        );
    }
""")
                    print(f'  Block replaced, ended at line {i}')
            else:
                out.append(line)
            i += 1
        content = ''.join(out)

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - file written')
