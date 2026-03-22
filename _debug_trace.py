import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

print("=== script.js: playMusic onMusicPlaying call ===")
with open('public/script.js', 'r', encoding='utf-8') as f:
    js = f.read()
idx = js.find("callHandler('onMusicPlaying'")
if idx >= 0:
    print(repr(js[idx:idx+200]))
else:
    print("NOT FOUND in script.js")

print("\n=== main.dart: inject JS playNative ===")
with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    dart = f.read()
idx = dart.find("playNative: function")
if idx >= 0:
    print(repr(dart[idx:idx+400]))
else:
    print("NOT FOUND")

print("\n=== main.dart: onMusicPlaying handler ===")
idx = dart.find("handlerName: 'onMusicPlaying'")
if idx >= 0:
    print(repr(dart[idx:idx+400]))
else:
    print("NOT FOUND")

print("\n=== MusicPlayerService: updateTrackInfo ===")
with open('auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MusicPlayerService.kt', 'r', encoding='utf-8') as f:
    kt = f.read()
idx = kt.find("fun updateTrackInfo")
if idx >= 0:
    print(repr(kt[idx:idx+500]))
else:
    print("NOT FOUND")

print("\n=== MusicPlayerService: fetchBitmap ===")
idx = kt.find("fun fetchBitmap")
if idx >= 0:
    print(repr(kt[idx:idx+400]))
else:
    print("NOT FOUND")

print("\n=== MusicPlayerService: setLargeIcon ===")
idx = kt.find("setLargeIcon")
if idx >= 0:
    print(repr(kt[idx-50:idx+100]))
else:
    print("NOT FOUND - this is the bug!")
