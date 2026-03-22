content = open('auspoty-flutter/lib/main.dart', encoding='utf-8').read()

old = "      case 'onPrev':\n        await _wvc?.evaluateJavascript(\n            source: \"if(typeof playPrevSong==='function') playPrevSong();\");\n        break;\n    }\n  }"

new = "      case 'onPrev':\n        await _wvc?.evaluateJavascript(\n            source: \"if(typeof playPrevSong==='function') playPrevSong();\");\n        break;\n      case 'onPlaybackStarted':\n        await _wvc?.evaluateJavascript(\n            source: \"if(typeof window._onNativePlaybackStarted==='function') window._onNativePlaybackStarted();\");\n        _startProgressTimer();\n        break;\n    }\n  }"

if old in content:
    print('FOUND, replacing...')
    content = content.replace(old, new, 1)
    open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8').write(content)
    print('Done')
else:
    idx = content.find("case 'onPrev'")
    print('NOT FOUND, snippet:')
    print(repr(content[idx:idx+300]))
