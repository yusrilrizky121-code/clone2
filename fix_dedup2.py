"""
Hapus duplikat fungsi di akhir file script.js
Strategi: cari kemunculan kedua 'let isShuffle = false;' dan hapus dari situ sampai akhir blok
"""
import re

FILES = [
    "public/script.js",
    "auspoty-apk/app/src/main/assets/script.js",
]

for path in FILES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    marker = 'let isShuffle = false;'
    first = content.find(marker)
    second = content.find(marker, first + 1)

    if second != -1:
        # Potong dari kemunculan kedua ke depan, tapi simpan sisa setelah blok duplikat
        # Cari akhir blok duplikat: setelah openQueueModal
        tail_start = content.find('openQueueModal', second)
        if tail_start != -1:
            # Cari akhir baris openQueueModal
            line_end = content.find('\n', tail_start)
            if line_end == -1:
                line_end = len(content)
            # Potong: ambil sampai sebelum kemunculan kedua, lalu lanjut setelah baris openQueueModal
            new_content = content[:second].rstrip() + content[line_end:]
        else:
            new_content = content[:second].rstrip()

        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[FIXED] {path}")
    else:
        print(f"[OK - no dup] {path}")
