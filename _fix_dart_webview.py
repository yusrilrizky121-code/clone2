#!/usr/bin/env python3
import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

dart = open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8').read()

# 1. Tambah allowsInlineMediaPlayback di InAppWebViewSettings
old_settings = "                mediaPlaybackRequiresUserGesture: false,"
new_settings = """                mediaPlaybackRequiresUserGesture: false,
                allowsInlineMediaPlayback: true,
                allowsAirPlayForMediaPlayback: true,"""

if 'allowsInlineMediaPlayback' not in dart:
    dart = dart.replace(old_settings, new_settings)
    print("✓ Added allowsInlineMediaPlayback")
else:
    print("- allowsInlineMediaPlayback already exists")

# 2. Fix didChangeAppLifecycleState — lebih agresif block visibility
old_lifecycle = """  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _musicPlaying) {
      _wvc?.evaluateJavascript(source: r\"\"\"
        (function(){
          try {
            Object.defineProperty(document, 'hidden', {
              get: function(){ return false; }, configurable: true
            });
            Object.defineProperty(document, 'visibilityState', {
              get: function(){ return 'visible'; }, configurable: true
            });
          } catch(e){}
          // Force ytPlayer tetap play jika ada
          try {
            if (window.ytPlayer && typeof window.ytPlayer.getPlayerState === 'function') {
              var st = window.ytPlayer.getPlayerState();
              if (st === 2) { // PAUSED
                setTimeout(function(){ window.ytPlayer.playVideo(); }, 500);
              }
            }
          } catch(e){}
        })();
      \"\"\");
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
    }
    if (state == AppLifecycleState.resumed) {
      _keepAliveTimer?.cancel();
    }
  }"""

new_lifecycle = """  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _musicPlaying) {
      // Inject visibility block — JANGAN paksa playVideo() karena autoplay policy
      _wvc?.evaluateJavascript(source: r\"\"\"
        (function(){
          try {
            Object.defineProperty(document, 'hidden', {
              get: function(){ return false; }, configurable: true
            });
            Object.defineProperty(document, 'visibilityState', {
              get: function(){ return 'visible'; }, configurable: true
            });
          } catch(e){}
        })();
      \"\"\");
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
    }
    if (state == AppLifecycleState.resumed) {
      _keepAliveTimer?.cancel();
    }
  }"""

if old_lifecycle in dart:
    dart = dart.replace(old_lifecycle, new_lifecycle)
    print("✓ Fixed didChangeAppLifecycleState (removed force playVideo)")
else:
    print("- didChangeAppLifecycleState exact match not found, skipping")

open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8').write(dart)
print("✓ Saved main.dart, lines:", len(dart.split('\n')))
print("allowsInlineMediaPlayback:", 'allowsInlineMediaPlayback' in dart)
