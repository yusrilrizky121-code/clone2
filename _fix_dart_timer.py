with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the _startProgressTimer that polls MethodChannel every second
# (audio is in JS ytPlayer, not native - this just wastes CPU)
old = '''  void _startProgressTimer() {
    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      try {
        final pos = await _ch.invokeMethod<int>('getPosition') ?? 0;
        final dur = await _ch.invokeMethod<int>('getDuration') ?? 0;
        if (dur > 0 && _wvc != null) {
          await _wvc!.evaluateJavascript(source: """
            (function(){
              var pb=document.getElementById('progressBar');
              var ct=document.getElementById('currentTime');
              var tt=document.getElementById('totalTime');
              if(pb){pb.value=$pos;pb.max=$dur;}
              if(ct) ct.innerText=_fmtTime($pos);
              if(tt) tt.innerText=_fmtTime($dur);
            })();
          """);
        }
      } catch (_) {}
    });
  }'''

new = '''  // Progress is handled by JS setInterval in ytPlayer — no native polling needed
  void _startProgressTimer() {}'''

if old in content:
    content = content.replace(old, new)
    print("Removed _startProgressTimer polling")
else:
    print("Pattern not found - checking...")
    idx = content.find('void _startProgressTimer()')
    print("Found at:", idx)
    if idx != -1:
        # Find the closing brace
        brace_count = 0
        i = content.find('{', idx)
        start = idx
        while i < len(content):
            if content[i] == '{': brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
            i += 1
        content = content[:start] + '  // Progress handled by JS\n  void _startProgressTimer() {}' + content[end:]
        print("Replaced via brace matching")

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
