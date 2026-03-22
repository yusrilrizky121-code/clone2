with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Tambah tombol background mode setelah tombol like (btnLikeSong)
# Icon: headphones SVG
old = '<svg id="btnLikeSong"'
new = '''<svg id="btnBgMode" viewBox="0 0 24 24" onclick="toggleBgMode()" title="Mode Latar Belakang" style="width:26px;height:26px;flex-shrink:0;cursor:pointer;fill:rgba(255,255,255,0.5);margin-right:12px;transition:fill 0.2s;"><path d="M12 3a9 9 0 0 0-9 9v7c0 1.1.9 2 2 2h1v-8H4v-1a8 8 0 0 1 16 0v1h-2v8h1c1.1 0 2-.9 2-2v-7a9 9 0 0 0-9-9z"/></svg>
            <svg id="btnLikeSong"'''

if old in content:
    content = content.replace(old, new, 1)
    print("OK: background mode button added")
else:
    print("FAIL: btnLikeSong not found")

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
