with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find _startProgressTimer function boundaries
start_line = None
end_line = None
for i, l in enumerate(lines):
    if 'void _startProgressTimer()' in l:
        start_line = i
        print(f"Found _startProgressTimer at line {i+1}")
        break

if start_line is not None:
    # Find the closing brace by counting braces
    brace_count = 0
    for i in range(start_line, len(lines)):
        for ch in lines[i]:
            if ch == '{': brace_count += 1
            elif ch == '}': brace_count -= 1
        if brace_count == 0 and i > start_line:
            end_line = i
            print(f"Function ends at line {i+1}")
            break

    if end_line is not None:
        # Replace the function with a no-op
        new_func = ['  // Progress handled by JS setInterval — no native polling needed\n',
                    '  void _startProgressTimer() {}\n']
        lines = lines[:start_line] + new_func + lines[end_line+1:]
        print(f"Replaced _startProgressTimer (was lines {start_line+1}-{end_line+1})")

# Also apply the download fix (re-apply since we restored from git)
# Check if download function needs updating
content = ''.join(lines)

# Fix download: change GET to POST with proper JSON parsing
old_dl = '''  Future<void> _download(String videoId, String title) async {
    if (Platform.isAndroid) await Permission.storage.request();
    try {
      final r = await http.post(Uri.parse('$_base/api/download'),
          headers: {'Content-Type': 'application/json'},
          body: '{"videoId":"$videoId"}').timeout(const Duration(seconds: 60));
      if (r.statusCode != 200) throw Exception();
      final um = RegExp(r'"url"\\s*:\\s*"([^"]+)"').firstMatch(r.body);
      final tm = RegExp(r'"title"\\s*:\\s*"([^"]+)"').firstMatch(r.body);
      if (um == null) throw Exception();
      final url = um.group(1)!.replaceAll(r'\\/', '/');
      final t2  = tm?.group(1) ?? title;
      final dl  = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 120));
      if (dl.statusCode != 200) throw Exception();
      final dir  = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final f    = File('${base}Download/${title.replaceAll(RegExp(r'[\\\\/:*?"<>|]'), '_')}.mp3');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(dl.bodyBytes);
      _wvc?.evaluateJavascript(source: "showToast('Download selesai: $t2');");
    } catch (_) {
      _wvc?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
    }
  }'''

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

if old_dl in content:
    content = content.replace(old_dl, new_dl)
    print("Updated _download function")
else:
    print("Download function already updated or pattern mismatch - skipping")

# Add dart:convert import if missing
if "dart:convert" not in content:
    content = content.replace("import 'dart:async';", "import 'dart:async';\nimport 'dart:convert';", 1)
    print("Added dart:convert import")

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

final_lines = open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8').readlines()
print(f"Final lines: {len(final_lines)}")
print("Has build method:", any('Widget build(BuildContext context)' in l for l in final_lines))
print("_startProgressTimer is no-op:", any('void _startProgressTimer() {}' in l for l in final_lines))
