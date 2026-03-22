import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# Baca main.dart yang ada, ganti bagian _playNative dan ThemeData
content = open(r'auspoty-flutter\lib\main.dart', 'r', encoding='utf-8').read()

# Fix 1: ThemeData issue
old_theme = '''        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFFa78bfa), brightness: Brightness.dark),
          useMaterial3: true,
        ),'''
new_theme = '''        theme: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(primary: Color(0xFFa78bfa)),
        ),'''

if old_theme in content:
    content = content.replace(old_theme, new_theme)
    print("ThemeData fixed")
else:
    print("ThemeData already ok or different format")

# Fix 2: _playNative — pass headers dari API response ke playFromUrl
old_play = '''  /// Fetch stream URL dari API lalu putar via just_audio
  Future<void> _playNative(String videoId, String title, String artist) async {
    try {
      final resp = await http.get(
        Uri.parse('$_base/api/stream?videoId=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36'},
      ).timeout(const Duration(seconds: 25));

      if (resp.statusCode != 200) return;

      final urlMatch = RegExp(r\'"url"\\s*:\\s*"([^"]+)"\').firstMatch(resp.body);
      if (urlMatch == null) return;
      final streamUrl = urlMatch.group(1)!.replaceAll(r\'\\\/\', \'/\');

      final item = MediaItem(
        id: videoId,
        title: title.isEmpty ? \'Auspoty\' : title,
        artist: artist.isEmpty ? \'Auspoty Music\' : artist,
      );

      await _audioHandler.playFromUrl(streamUrl, item);

      // Beritahu JS playback sudah mulai
      _wvc?.evaluateJavascript(source: """
        (function(){
          window._nativePlaying = true;
          window._nativeLoading = false;
          if(typeof updatePlayPauseBtn===\'function\') updatePlayPauseBtn(true);
        })();
      """);
    } catch (_) {}
  }'''

# Tulis ulang _playNative yang benar
new_play = r'''  /// Fetch stream URL dari API lalu putar via just_audio
  Future<void> _playNative(String videoId, String title, String artist) async {
    try {
      final resp = await http.get(
        Uri.parse('$_base/api/stream?videoId=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
      ).timeout(const Duration(seconds: 25));

      if (resp.statusCode != 200) return;

      // Parse JSON response
      final body = resp.body;
      final urlMatch = RegExp(r'"url"\s*:\s*"([^"]+)"').firstMatch(body);
      if (urlMatch == null) return;
      final streamUrl = urlMatch.group(1)!.replaceAll(r'\/', '/');

      // Ambil headers dari API response
      final Map<String, String> streamHeaders = {};
      final headersMatch = RegExp(r'"headers"\s*:\s*\{([^}]+)\}').firstMatch(body);
      if (headersMatch != null) {
        final hBody = headersMatch.group(1)!;
        final pairs = RegExp(r'"([^"]+)"\s*:\s*"([^"]+)"').allMatches(hBody);
        for (final m in pairs) {
          streamHeaders[m.group(1)!] = m.group(2)!;
        }
      }
      // Fallback headers kalau kosong
      if (streamHeaders.isEmpty) {
        streamHeaders['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36';
        streamHeaders['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8';
        streamHeaders['Accept-Language'] = 'en-us,en;q=0.5';
        streamHeaders['Sec-Fetch-Mode'] = 'navigate';
      }

      final item = MediaItem(
        id: videoId,
        title: title.isEmpty ? 'Auspoty' : title,
        artist: artist.isEmpty ? 'Auspoty Music' : artist,
      );

      await _audioHandler.playFromUrl(streamUrl, item, headers: streamHeaders);

      // Beritahu JS playback sudah mulai
      _wvc?.evaluateJavascript(source: """
        (function(){
          window._nativePlaying = true;
          window._nativeLoading = false;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
        })();
      """);
    } catch (_) {}
  }'''

# Cari dan ganti _playNative
import re
pattern = r'  /// Fetch stream URL dari API lalu putar via just_audio\n  Future<void> _playNative.*?catch \(_\) \{\}\n  \}'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_play + content[match.end():]
    print("_playNative replaced")
else:
    print("_playNative pattern not found, appending before last closing brace")
    # Fallback: cari posisi sebelum closing brace terakhir
    idx = content.rfind('\n}')
    content = content[:idx] + '\n' + new_play + content[idx:]

with open(r'auspoty-flutter\lib\main.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print("main.dart updated")
