import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Cari dan replace seluruh fungsi togglePlay dengan regex
# Cari dari "function togglePlay" sampai sebelum "function updatePlayPauseBtn"
pattern = r'function togglePlay\(\) \{.*?\}\n\nfunction updatePlayPauseBtn'
match = re.search(pattern, content, re.DOTALL)
if match:
    print('Found togglePlay block, length:', len(match.group()))
    new_func = """function togglePlay() {
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
}

function updatePlayPauseBtn"""
    content = content[:match.start()] + new_func + content[match.end():]
    print('OK: replaced')
else:
    print('ERROR: pattern not found')
    idx = content.find('function togglePlay')
    print(repr(content[idx:idx+600]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
