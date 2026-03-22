import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = """function togglePlay() {
    if (window.flutter_inappwebview) {
        // APK mode: toggle via native
        if (isPlaying) {
            isPlaying = false;
            updatePlayPauseBtn(false);
            try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
        } else {
            isPlaying = true;
            updatePlayPauseBtn(true);
            try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
        }
        return;
    }
    // Web/PWA mode
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
    } """

new = """function togglePlay() {
    // Toggle ytPlayer (baik di web maupun APK)
    if (!ytPlayer) return;
    if (isPlaying) {
        ytPlayer.pauseVideo();
        // Kirim notif ke native
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicPaused'); } catch(e) {}
    } else {
        ytPlayer.playVideo();
        // Kirim notif ke native
        if (window.flutter_inappwebview) try { window.flutter_inappwebview.callHandler('onMusicResumed'); } catch(e) {}
    }
    // dummy untuk lanjut ke baris berikutnya
    if (false) { """

if old in content:
    content = content.replace(old, new)
    print('OK: togglePlay replaced')
else:
    print('ERROR: togglePlay not found')
    idx = content.find('function togglePlay')
    print(repr(content[idx:idx+400]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
