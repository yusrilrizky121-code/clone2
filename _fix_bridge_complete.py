"""
Fix complete: AndroidBridge + callbacks + progress update
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

DART_PATH = r'auspoty-flutter\lib\main.dart'

with open(DART_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix AndroidBridge - tambah playNative, pauseNative, resumeNative + callbacks
old_bridge = """        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          openDownload: function(vid, t){
            window.flutter_inappwebview.callHandler('downloadTrack', vid, t||'');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          }
        };"""

new_bridge = """        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          playNative: function(videoId, title, artist, img){
            try { if(window.ytPlayer && window.ytPlayer.mute) window.ytPlayer.mute(); } catch(e){}
            window._nativeLoading = true;
            window._nativePlaying = false;
            window._nativePaused = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', videoId||'');
            }
          },
          pauseNative: function(){
            window._nativePlaying = false;
            window._nativePaused = true;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused');
          },
          resumeNative: function(){
            window._nativePlaying = true;
            window._nativePaused = false;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicResumed');
          },
          openDownload: function(vid, t){
            window.flutter_inappwebview.callHandler('downloadTrack', vid, t||'');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          }
        };

        window._onNativePlaybackStarted = function(){
          window._nativeLoading = false;
          window._nativePlaying = true;
          window._nativePaused = false;
          isPlaying = true;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
        };
        window._onNativePlaybackPaused = function(){
          window._nativePlaying = false;
          window._nativePaused = true;
          isPlaying = false;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(false);
        };
        window._updateNativeProgress = function(pos, dur){
          if(dur <= 0) return;
          var pct = (pos/dur)*100;
          var bar = document.getElementById('progressBar');
          if(bar){ bar.value = pct; bar.style.background='linear-gradient(to right, white '+pct+'%, rgba(255,255,255,0.2) '+pct+'%)'; }
          var fmt = function(s){ var m=Math.floor(s/60),sec=s%60; return m+':'+(sec<10?'0':'')+sec; };
          var ct = document.getElementById('currentTime'); if(ct) ct.innerText = fmt(pos);
          var tt = document.getElementById('totalTime'); if(tt) tt.innerText = fmt(dur);
        };"""

if old_bridge in content:
    content = content.replace(old_bridge, new_bridge)
    print("✓ AndroidBridge updated with playNative/pauseNative/resumeNative + callbacks")
else:
    print("✗ AndroidBridge pattern not found!")
    # Try to find it
    idx = content.find('window.AndroidBridge')
    if idx >= 0:
        print(f"Found at: {repr(content[idx:idx+200])}")

with open(DART_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerifying...")
with open(DART_PATH, 'r', encoding='utf-8') as f:
    v = f.read()
print(f"  playNative in bridge: {'✓' if 'playNative: function' in v else '✗'}")
print(f"  _onNativePlaybackStarted: {'✓' if '_onNativePlaybackStarted' in v else '✗'}")
print(f"  _updateNativeProgress: {'✓' if '_updateNativeProgress' in v else '✗'}")
