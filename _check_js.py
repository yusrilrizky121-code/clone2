import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    c = f.read()

idx = c.find("callHandler('onMusicPlaying'")
print(repr(c[idx:idx+200]))
