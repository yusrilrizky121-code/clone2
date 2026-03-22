import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix AndroidBridge.playNative di inject JS
old = """          playNative: function(videoId, title, artist, img){
            try { if(window.ytPlayer && window.ytPlayer.mute) window.ytPlayer.mute(); } catch(e){}
            window._nativeLoading = true;
            window._nativePlaying = false;
            window._nativePaused = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', videoId||'');
            }
          },"""

new = """          playNative: function(videoId, title, artist, img){
            // Audio tetap di ytPlayer, native hanya untuk notifikasi
            window._nativeLoading = false;
            window._nativePlaying = false;
            window._nativePaused = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', '', img||'');
            }
          },"""

if old in content:
    content = content.replace(old, new)
    print('OK: playNative inject fixed')
else:
    print('ERROR: not found')
    idx = content.find('playNative: function')
    if idx >= 0:
        print(repr(content[idx:idx+400]))

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
