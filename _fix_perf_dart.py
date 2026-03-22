with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: useHybridComposition false (biggest scroll lag fix)
content = content.replace('useHybridComposition: true,', 'useHybridComposition: false,')

# Fix 2: Remove _progressTimer entirely - it polls MethodChannel every second for nothing
# (audio is in ytPlayer JS, not native MediaPlayer)
old_timer = '''  /// Update progress bar di JS dari posisi MediaPlayer native
  void _startProgressTimer() {
    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      try {
        final pos = await _ch.invokeMethod<int>('getPosition') ?? 0;
        final dur = await _ch.invokeMethod<int>('getDuration') ?? 0;
        if (dur > 0 && _wvc != null) {
          await _wvc!.evaluateJavascript(source: """
            (function(){
              var pb = document.getElementById('progressBar');
              var ct = document.getElementById('currentTime');
              var tt = document.getElementById('totalTime');
              if(pb) pb.value = $pos;
              if(pb) pb.max = $dur;
              if(ct) ct.innerText = _fmtTime($pos);
              if(tt) tt.innerText = _fmtTime($dur);
            })();
          """);
        }
      } catch (_) {}
    });
  }'''

new_timer = '''  // Progress is handled by JS setInterval in ytPlayer — no native timer needed
  void _startProgressTimer() { /* no-op: JS handles progress */ }'''

if old_timer in content:
    content = content.replace(old_timer, new_timer)
    print("Removed _progressTimer polling")
else:
    print("WARNING: _progressTimer pattern not found, trying partial match")
    idx = content.find('void _startProgressTimer()')
    if idx != -1:
        end = content.find('\n  }', idx) + 4
        content = content[:idx] + '// Progress handled by JS\n  void _startProgressTimer() { /* no-op */ }' + content[end:]
        print("Replaced via partial match")

# Fix 3: cacheMode LOAD_DEFAULT is fine, but add hardware acceleration hint
# Fix 4: Remove allowFileAccessFromFileURLs (not needed, loads from Vercel)
content = content.replace(
    'allowFileAccessFromFileURLs: true,',
    'allowFileAccessFromFileURLs: false,'
)
content = content.replace(
    'allowUniversalAccessFromFileURLs: true,',
    'allowUniversalAccessFromFileURLs: false,'
)

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
c2 = open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8').read()
print("useHybridComposition:", "useHybridComposition: false" in c2)
print("_progressTimer removed:", "_progressTimer = Timer.periodic" not in c2)
