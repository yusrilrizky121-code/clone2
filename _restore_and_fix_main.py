import subprocess

# Get the good version from commit 6284780
result = subprocess.run(['git', 'show', '6284780:auspoty-flutter/lib/main.dart'], capture_output=True)
content = result.stdout.decode('utf-8')
print(f"Restored {len(content.splitlines())} lines from commit 6284780")

# Apply all fixes to this good version:

# Fix 1: Add dart:convert import
if "dart:convert" not in content:
    content = content.replace("import 'dart:async';", "import 'dart:async';\nimport 'dart:convert';", 1)
    print("Added dart:convert")

# Fix 2: useHybridComposition false (scroll performance)
content = content.replace('useHybridComposition: true,', 'useHybridComposition: false,')
print("useHybridComposition: false -", 'useHybridComposition: false' in content)

# Fix 3: allowFileAccessFromFileURLs false (not needed, loads from Vercel)
content = content.replace('allowFileAccessFromFileURLs: true,', 'allowFileAccessFromFileURLs: false,')
content = content.replace('allowUniversalAccessFromFileURLs: true,', 'allowUniversalAccessFromFileURLs: false,')

# Fix 4: cacheMode LOAD_CACHE_ELSE_NETWORK for faster loads
content = content.replace('cacheMode: CacheMode.LOAD_DEFAULT,', 'cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,')
content = content.replace('cacheMode: CacheMode.LOAD_NO_CACHE,', 'cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,')

# Fix 5: Remove _progressTimer polling (no-op since audio is in JS)
import re
# Find and replace the _startProgressTimer function
pattern = r'  /// Update progress bar di JS dari posisi MediaPlayer native\n  void _startProgressTimer\(\) \{.*?\n  \}'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + '  // Progress handled by JS setInterval\n  void _startProgressTimer() {}' + content[match.end():]
    print("Replaced _startProgressTimer with no-op")
else:
    # Try without the comment
    pattern2 = r'  void _startProgressTimer\(\) \{.*?\n  \}'
    match2 = re.search(pattern2, content, re.DOTALL)
    if match2:
        content = content[:match2.start()] + '  // Progress handled by JS setInterval\n  void _startProgressTimer() {}' + content[match2.end():]
        print("Replaced _startProgressTimer (no comment) with no-op")
    else:
        print("WARNING: _startProgressTimer not found")

# Fix 6: Update _download function to use proper API flow
old_dl_start = "  Future<void> _download(String videoId, String title) async {"
dl_idx = content.find(old_dl_start)
if dl_idx != -1:
    # Find end of function
    brace = 0
    i = dl_idx
    while i < len(content):
        if content[i] == '{': brace += 1
        elif content[i] == '}':
            brace -= 1
            if brace == 0:
                dl_end = i + 1
                break
        i += 1
    
    new_dl = '''  Future<void> _download(String videoId, String title) async {
    try {
      final t2 = title.replaceAll("'", "\\\\'");
      _wvc?.evaluateJavascript(source: "showToast('Mengunduh... tunggu 30-60 detik');");
      if (Platform.isAndroid) await Permission.storage.request();
      final apiRes = await http.post(
        Uri.parse('$_base/api/download'),
        headers: {'Content-Type': 'application/json'},
        body: '{"videoId":"$videoId"}',
      ).timeout(const Duration(seconds: 90));
      if (apiRes.statusCode != 200) throw Exception('API \${apiRes.statusCode}');
      final apiJson = json.decode(apiRes.body) as Map<String, dynamic>;
      if (apiJson['status'] != 'success') throw Exception(apiJson['message']?.toString() ?? 'failed');
      final mp3Url   = apiJson['url'] as String;
      final mp3Title = (apiJson['title'] as String?) ?? title;
      final dl = await http.get(Uri.parse(mp3Url)).timeout(const Duration(seconds: 120));
      if (dl.statusCode != 200) throw Exception('DL \${dl.statusCode}');
      final dir  = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final safe = mp3Title.replaceAll(RegExp(r'[\\\\/:*?"<>|]'), '_');
      final f    = File('\${base}Download/\$safe.mp3');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(dl.bodyBytes);
      _wvc?.evaluateJavascript(source: "showToast('\\u2713 Download selesai: \$t2');");
    } catch (e) {
      _wvc?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
    }
  }'''
    content = content[:dl_idx] + new_dl + content[dl_end:]
    print("Updated _download function")

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

final_lines = content.splitlines()
print(f"Final: {len(final_lines)} lines")
print("Has _AuspotyWebViewState.build:", any('Widget build(BuildContext context) {' in l for l in final_lines))
print("Has PopScope:", any('PopScope' in l for l in final_lines))
print("Has InAppWebView:", any('InAppWebView(' in l for l in final_lines))
print("useHybridComposition false:", 'useHybridComposition: false' in content)
print("_startProgressTimer no-op:", 'void _startProgressTimer() {}' in content)
