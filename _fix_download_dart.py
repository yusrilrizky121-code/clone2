with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the _download function
start_marker = "  Future<void> _download(String videoId, String title) async {"
end_marker = "  Future<void> _inject"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: markers not found")
    print("start:", start_idx, "end:", end_idx)
    exit(1)

new_download = '''  Future<void> _download(String videoId, String title) async {
    try {
      final t2 = title.replaceAll("'", "\\\\'");
      _wvc?.evaluateJavascript(source: "showToast('Mengunduh... tunggu 30-60 detik');");
      if (Platform.isAndroid) await Permission.storage.request();

      // Step 1: POST ke API untuk dapat URL mp3
      final apiRes = await http.post(
        Uri.parse('$_base/api/download'),
        headers: {'Content-Type': 'application/json'},
        body: '{"videoId":"$videoId"}',
      ).timeout(const Duration(seconds: 90));

      if (apiRes.statusCode != 200) throw Exception('API ${apiRes.statusCode}');
      final apiJson = json.decode(apiRes.body) as Map<String, dynamic>;
      if (apiJson['status'] != 'success') throw Exception(apiJson['message']?.toString() ?? 'failed');

      final mp3Url   = apiJson['url'] as String;
      final mp3Title = (apiJson['title'] as String?) ?? title;

      // Step 2: Download file MP3
      final dl = await http.get(Uri.parse(mp3Url)).timeout(const Duration(seconds: 120));
      if (dl.statusCode != 200) throw Exception('DL ${dl.statusCode}');

      // Step 3: Simpan ke folder Download
      final dir  = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final safe = mp3Title.replaceAll(RegExp(r'[\\\\/:*?"<>|]'), '_');
      final f    = File('${base}Download/$safe.mp3');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(dl.bodyBytes);

      _wvc?.evaluateJavascript(source: "showToast('\\u2713 Download selesai: $t2');");
    } catch (e) {
      _wvc?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
    }
  }

  '''

content = content[:start_idx] + new_download + content[end_idx:]

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
# Verify json import
if "import 'dart:convert'" in content:
    print("dart:convert already imported")
else:
    print("WARNING: need to add dart:convert import")
