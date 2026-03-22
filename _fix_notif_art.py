import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ── 1. script.js: kirim imgUrl ke onMusicPlaying ─────────────────────────────
with open('public/script.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_js = "window.flutter_inappwebview.callHandler('onMusicPlaying',\n                currentTrack.title||'Auspoty', currentTrack.artist||'', '');"
new_js = "window.flutter_inappwebview.callHandler('onMusicPlaying',\n                currentTrack.title||'Auspoty', currentTrack.artist||'', '', currentTrack.img||'');"

if old_js in js:
    js = js.replace(old_js, new_js)
    print('OK: script.js updated')
else:
    print('ERROR: script.js pattern not found')
    import re
    m = re.search(r"callHandler\('onMusicPlaying'.*?\);", js, re.DOTALL)
    if m: print('Found:', repr(m.group()))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(js)

print('script.js done')
