import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

with open('public/script.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Cari semua callHandler onMusicPlaying
import re
for m in re.finditer(r"callHandler\('onMusicPlaying'[^;]+;", js, re.DOTALL):
    print("FOUND:", repr(m.group()))
    print()
