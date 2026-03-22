with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the downloadMusic function
import re

old_pattern = r'// DOWNLOAD\nfunction downloadMusic\(\) \{.*?\n\}'
new_code = '''// DOWNLOAD
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
}'''

match = re.search(r'// DOWNLOAD\nfunction downloadMusic\(\) \{.*?\n\}', content, re.DOTALL)
if match:
    content = content[:match.start()] + new_code + content[match.end():]
    print("Replaced downloadMusic function")
else:
    print("Pattern not found, trying manual search...")
    idx = content.find('// DOWNLOAD\nfunction downloadMusic')
    if idx != -1:
        end = content.find('\n}', idx) + 2
        content = content[:idx] + new_code + content[end:]
        print("Replaced via manual search")
    else:
        print("ERROR: downloadMusic not found")

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
c2 = open('public/script.js', 'r', encoding='utf-8').read()
print("ytmp3 remaining:", c2.count('ytmp3'))
print("flutter_inappwebview callHandler downloadTrack:", c2.count("callHandler('downloadTrack'"))
