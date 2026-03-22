#!/usr/bin/env python3
"""Patch script.js and main.dart for background audio + rotating art fix."""
import re

# ─── PATCH script.js ────────────────────────────────────────────────────────

with open('public/script.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Fix onYouTubeIframeAPIReady — ensure closing brace is correct
# The HEAD version has the closing brace of YT.Player missing before onPlayerStateChange
old_yt_init = """    ytPlayer = new YT.Player('youtube-player', {
        height: '0', width: '0',
        events: { onReady: () => {}, onStateChange: onPlayerStateChange }
    });
}"""
new_yt_init = """    ytPlayer = new YT.Player('youtube-player', {
        height: '0', width: '0',
        playerVars: { playsinline: 1, rel: 0 },
        events: { onReady: () => {}, onStateChange: onPlayerStateChange }
    });
}"""
if old_yt_init in js:
    js = js.replace(old_yt_init, new_yt_init)
    print("✓ Fixed YT.Player init")
else:
    print("⚠ YT.Player init not found, skipping")

# 2. Add _setArtRotation call in onPlayerStateChange PLAYING state
old_playing = """        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        startProgressBar();"""
new_playing = """        isPlaying = true;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + pausePath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + pausePath + '"/>';
        _setArtRotation(true);
        startProgressBar();"""
if old_playing in js:
    js = js.replace(old_playing, new_playing)
    print("✓ Added _setArtRotation(true) on PLAYING")
else:
    print("⚠ PLAYING block not found")

# 3. Add _setArtRotation(false) in PAUSED state
old_paused = """        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();
        // APK mode: pause dihandle via AndroidBridge.pauseNative()"""
new_paused = """        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        _setArtRotation(false);
        stopProgressBar();"""
if old_paused in js:
    js = js.replace(old_paused, new_paused)
    print("✓ Added _setArtRotation(false) on PAUSED")
else:
    print("⚠ PAUSED block not found, trying alt...")
    old_paused2 = """        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        stopProgressBar();"""
    # Only replace first occurrence (PAUSED state, not ENDED)
    if old_paused2 in js:
        js = js.replace(old_paused2, """        isPlaying = false;
        if (mainBtn) mainBtn.innerHTML = '<path d="' + playPath + '"/>';
        if (miniBtn) miniBtn.innerHTML = '<path d="' + playPath + '"/>';
        _setArtRotation(false);
        stopProgressBar();""", 1)
        print("✓ Added _setArtRotation(false) on PAUSED (alt)")

# 4. Fix startProgressBar to update progressFill, progressThumb, miniProgressFill
old_progress = """function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
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
}"""
new_progress = """function startProgressBar() {
    stopProgressBar();
    progressInterval = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
        if (dur > 0) {
            const pct = (cur / dur) * 100;
            const bar = document.getElementById('progressBar');
            const fill = document.getElementById('progressFill');
            const thumb = document.getElementById('progressThumb');
            const mf = document.getElementById('miniProgressFill');
            if (bar) bar.value = pct;
            if (fill) fill.style.width = pct + '%';
            if (thumb) thumb.style.left = pct + '%';
            if (mf) mf.style.width = pct + '%';
            const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);
            const tt = document.getElementById('totalTime'); if (tt) tt.innerText = formatTime(dur);
        }
    }, 500);
}"""
if old_progress in js:
    js = js.replace(old_progress, new_progress)
    print("✓ Fixed startProgressBar with fill/thumb/mini updates")
else:
    print("⚠ startProgressBar not found exactly")

# 5. Add _setArtRotation function after updatePlayPauseBtn
old_upb = """function updatePlayPauseBtn(playing) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (mainBtn) mainBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
    if (miniBtn) miniBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
}"""
new_upb = """function updatePlayPauseBtn(playing) {
    const playPath = 'M8 5v14l11-7z', pausePath = 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
    const mainBtn = document.getElementById('mainPlayBtn'), miniBtn = document.getElementById('miniPlayBtn');
    if (mainBtn) mainBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
    if (miniBtn) miniBtn.innerHTML = '<path d="' + (playing ? pausePath : playPath) + '"/>';
}

// Rotating album art — Namida style
function _setArtRotation(playing) {
    const art = document.getElementById('playerArt');
    if (!art) return;
    if (playing) {
        art.classList.remove('paused');
        art.classList.add('playing');
    } else {
        art.classList.remove('playing');
        art.classList.add('paused');
    }
}"""
if '_setArtRotation' not in js:
    if old_upb in js:
        js = js.replace(old_upb, new_upb)
        print("✓ Added _setArtRotation function")
    else:
        print("⚠ updatePlayPauseBtn not found, appending _setArtRotation")
        js += "\n\nfunction _setArtRotation(playing) {\n    const art = document.getElementById('playerArt');\n    if (!art) return;\n    if (playing) { art.classList.remove('paused'); art.classList.add('playing'); }\n    else { art.classList.remove('playing'); art.classList.add('paused'); }\n}\n"
else:
    print("✓ _setArtRotation already exists")

# 6. Reset progress on playMusic
old_reset = """    document.getElementById('progressBar').value = 0;
    document.getElementById('currentTime').innerText = '0:00';
    document.getElementById('totalTime').innerText = '0:00';"""
new_reset = """    document.getElementById('progressBar').value = 0;
    const _pf = document.getElementById('progressFill'); if (_pf) _pf.style.width = '0%';
    const _pt = document.getElementById('progressThumb'); if (_pt) _pt.style.left = '0%';
    const _mf = document.getElementById('miniProgressFill'); if (_mf) _mf.style.width = '0%';
    document.getElementById('currentTime').innerText = '0:00';
    document.getElementById('totalTime').innerText = '0:00';"""
if old_reset in js and 'progressFill' not in js.split(old_reset)[0][-200:]:
    js = js.replace(old_reset, new_reset, 1)
    print("✓ Added progressFill reset in playMusic")
else:
    print("⚠ progress reset block not found or already patched")

with open('public/script.js', 'w', encoding='utf-8', newline='\n') as f:
    f.write(js)
print("✓ script.js written")

# ─── PATCH main.dart ────────────────────────────────────────────────────────

with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    dart = f.read()

# 1. Add allowBackgroundAudioPlaying + useHybridComposition
old_settings = """                mediaPlaybackRequiresUserGesture: false,
                allowsInlineMediaPlayback: true,
                mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,"""
new_settings = """                mediaPlaybackRequiresUserGesture: false,
                allowsInlineMediaPlayback: true,
                allowBackgroundAudioPlaying: true,
                useHybridComposition: true,
                allowFileAccessFromFileURLs: true,
                allowUniversalAccessFromFileURLs: true,
                mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,"""
if 'allowBackgroundAudioPlaying' not in dart:
    if old_settings in dart:
        dart = dart.replace(old_settings, new_settings)
        print("✓ Added allowBackgroundAudioPlaying to WebView settings")
    else:
        print("⚠ WebView settings block not found")
else:
    print("✓ allowBackgroundAudioPlaying already present")

# 2. Override document.hidden on paused
old_paused_dart = """    if (state == AppLifecycleState.paused) {
      // Saat background: MediaPlayer tetap jalan di service
      // Hentikan progress timer (tidak perlu update UI saat background)
      _progressTimer?.cancel();
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
    }
    if (state == AppLifecycleState.resumed) {
      // Saat kembali ke foreground: restart progress timer
      _startProgressTimer();
    }"""
new_paused_dart = """    if (state == AppLifecycleState.paused) {
      _progressTimer?.cancel();
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
      // Override document.hidden so YouTube IFrame doesn't pause in background
      _wvc?.evaluateJavascript(source: r\"\"\"
        (function(){
          if(window.__bgHidden) return;
          window.__bgHidden = true;
          try {
            Object.defineProperty(document,'hidden',{get:function(){return false;},configurable:true});
            Object.defineProperty(document,'visibilityState',{get:function(){return 'visible';},configurable:true});
            Object.defineProperty(document,'webkitHidden',{get:function(){return false;},configurable:true});
            var _oa=document.addEventListener.bind(document);
            document.addEventListener=function(t,fn,o){
              if(t==='visibilitychange'||t==='webkitvisibilitychange') return;
              _oa(t,fn,o);
            };
          } catch(e){}
        })();
      \"\"\");
    }
    if (state == AppLifecycleState.resumed) {
      _wvc?.evaluateJavascript(source: r\"\"\"
        (function(){
          window.__bgHidden=false;
          try{delete document.hidden;delete document.visibilityState;delete document.webkitHidden;}catch(e){}
        })();
      \"\"\");
      _startProgressTimer();
    }"""
if '__bgHidden' not in dart:
    if old_paused_dart in dart:
        dart = dart.replace(old_paused_dart, new_paused_dart)
        print("✓ Added document.hidden override in didChangeAppLifecycleState")
    else:
        print("⚠ lifecycle paused block not found exactly, trying partial match...")
        # Try to find and replace just the paused block
        pattern = r'if \(state == AppLifecycleState\.paused\) \{[^}]+\}'
        match = re.search(pattern, dart, re.DOTALL)
        if match:
            print(f"  Found paused block at {match.start()}-{match.end()}")
        else:
            print("  Could not find paused block")
else:
    print("✓ document.hidden override already present")

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8', newline='\n') as f:
    f.write(dart)
print("✓ main.dart written")

print("\nAll patches applied!")
