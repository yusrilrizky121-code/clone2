import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

print('File size:', len(content))

# Cari dan replace handler onMusicPlaying
old = """                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final videoId = args.length > 2 ? args[2].toString() : '';
                    WakelockPlus.enable();
                    if (videoId.isNotEmpty) {
                      // Putar via MediaPlayer native (background-safe)
                      try {
                        await _ch.invokeMethod('playNative', {
                          'videoId': videoId,
                          'title': title,
                          'artist': artist,
                        });
                        _startProgressTimer();
                      } catch (e) {
                        // Fallback: update notif saja
                        try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true}); } catch (_) {}
                      }
                    } else {
                      try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true}); } catch (_) {}
                    }
                  },
                );"""

new = """                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title  = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist = args.length > 1 ? args[1].toString() : '';
                    final imgUrl = args.length > 3 ? args[3].toString() : '';
                    WakelockPlus.enable();
                    try {
                      await _ch.invokeMethod('updateTrack', {
                        'title': title,
                        'artist': artist,
                        'isPlaying': true,
                        'imgUrl': imgUrl,
                      });
                    } catch (_) {}
                  },
                );"""

if old in content:
    content = content.replace(old, new)
    print('OK: onMusicPlaying handler replaced')
else:
    print('ERROR: not found, trying partial match...')
    idx = content.find("handlerName: 'onMusicPlaying'")
    if idx >= 0:
        print(repr(content[idx-20:idx+600]))

# Juga fix handler onMusicPaused dan onMusicResumed
old_paused = """                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    _progressTimer?.cancel();
                    try { await _ch.invokeMethod('pauseNative'); } catch (_) {}
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async {
                    try { await _ch.invokeMethod('resumeNative'); } catch (_) {}
                    _startProgressTimer();
                  },
                );"""

new_paused = """                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    _progressTimer?.cancel();
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async {
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': true}); } catch (_) {}
                  },
                );"""

if old_paused in content:
    content = content.replace(old_paused, new_paused)
    print('OK: onMusicPaused/Resumed replaced')
else:
    print('INFO: onMusicPaused pattern not found (may already be correct)')

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
