#!/usr/bin/env python3
import os, re
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# Cek script.js
js = open('public/script.js','r',encoding='utf-8').read()
print("=== script.js ===")
print("Balance:", js.count('{') - js.count('}'))
for m in re.finditer(r"callHandler\('onMusicPlaying'[^;]+", js):
    print("CALL:", m.group()[:150])

# Cek main.dart
dart = open('auspoty-flutter/lib/main.dart','r',encoding='utf-8').read()
print("\n=== main.dart ===")
print("playNative:", 'playNative' in dart)
print("args[2] videoId:", 'args[2]' in dart)
idx = dart.find('onMusicPlaying')
print("onMusicPlaying context:", dart[idx:idx+300])

# Cek MusicPlayerService
svc = open('auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MusicPlayerService.kt','r',encoding='utf-8').read()
print("\n=== MusicPlayerService.kt ===")
print("MediaPlayer:", 'MediaPlayer' in svc)
print("fetchStreamUrl:", 'fetchStreamUrl' in svc)
print("fun playNative:", 'fun playNative' in svc)
print("HttpURLConnection:", 'HttpURLConnection' in svc)

# Cek MainActivity
main = open('auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MainActivity.kt','r',encoding='utf-8').read()
print("\n=== MainActivity.kt ===")
print("playNative channel:", '"playNative"' in main)
print("pauseNative channel:", '"pauseNative"' in main)

# Cek APK timestamp
import os.path, datetime
apk = 'Auspoty-v3.0.apk'
if os.path.exists(apk):
    mtime = os.path.getmtime(apk)
    print("\nAPK last modified:", datetime.datetime.fromtimestamp(mtime))
    print("APK size:", round(os.path.getsize(apk)/1024/1024, 2), "MB")
