"""Hapus blok duplikat fungsi yang ditambahkan di akhir file"""
import re

FILES = [
    "public/script.js",
    "auspoty-apk/app/src/main/assets/script.js",
]

# Fungsi yang mungkin duplikat di akhir file
DUP_PATTERN = re.compile(
    r'\r?\nlet isShuffle = false;\r?\nfunction toggleShuffle\(\).*?openQueueModal\(\)[^\n]*\n',
    re.DOTALL
)

for path in FILES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    matches = list(DUP_PATTERN.finditer(content))
    if len(matches) > 1:
        # Hapus semua kecuali yang pertama
        # Cari posisi match pertama, hapus sisanya
        first_end = matches[0].end()
        # Hapus semua match setelah yang pertama
        new_content = content[:first_end]
        last_match_end = matches[-1].end()
        new_content += content[last_match_end:]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[FIXED] {path} - removed {len(matches)-1} duplicate(s)")
    else:
        print(f"[OK] {path} - no duplicates")
