"""
Setup script untuk Auspoty Flutter:
1. Generate icon PNG (gradient ungu-pink dengan huruf A)
2. Copy web assets dari public/ ke assets/web/
3. Patch script.js agar apiFetch pakai URL absolut (file:// tidak bisa relative)

Jalankan: python setup_assets.py
"""
import os
import shutil
import struct
import zlib

# ============================================================
# 1. Generate icon PNG 1024x1024
# ============================================================
def create_gradient_icon():
    size = 1024
    r1, g1, b1 = 0xa7, 0x8b, 0xfa  # ungu
    r2, g2, b2 = 0xf4, 0x72, 0xb6  # pink

    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            t = (x + y) / (2 * size)
            cx, cy = size // 2, size // 2
            radius = size * 0.45
            corner_r = size * 0.22
            dx = abs(x - cx) - (radius - corner_r)
            dy = abs(y - cy) - (radius - corner_r)
            in_shape = False
            if dx <= 0 and abs(y - cy) <= radius:
                in_shape = True
            elif dy <= 0 and abs(x - cx) <= radius:
                in_shape = True
            elif dx > 0 and dy > 0:
                in_shape = (dx*dx + dy*dy) ** 0.5 <= corner_r

            if in_shape:
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                lx = x - cx
                ly = y - cy
                aw, ah = 320, 400
                ax = lx + aw // 2
                ay = ly + ah // 2
                in_letter = False
                if 0 <= ax <= aw and 0 <= ay <= ah:
                    stroke = 45
                    expected_left = int((ax / aw) * ah * 0.5)
                    expected_right = int(((aw - ax) / aw) * ah * 0.5)
                    if abs(ay - (ah - expected_left * 2)) < stroke and ax < aw // 2 + stroke:
                        in_letter = True
                    if abs(ay - (ah - expected_right * 2)) < stroke and ax > aw // 2 - stroke:
                        in_letter = True
                    if abs(ay - ah // 2) < stroke // 2 and aw // 4 < ax < aw * 3 // 4:
                        in_letter = True
                if in_letter:
                    row.extend([255, 255, 255, 255])
                else:
                    row.extend([r, g, b, 255])
            else:
                row.extend([0, 0, 0, 0])
        pixels.append(bytes(row))
    return _encode_png(size, size, pixels)

def _encode_png(width, height, rows):
    def make_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = make_chunk(b'IHDR', ihdr_data)
    raw = b''
    for row in rows:
        raw += b'\x00' + row
    compressed = zlib.compress(raw, 9)
    idat = make_chunk(b'IDAT', compressed)
    iend = make_chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

os.makedirs('assets/icon', exist_ok=True)
os.makedirs('assets/web', exist_ok=True)

print('Generating icon...')
icon_data = create_gradient_icon()
with open('assets/icon/icon.png', 'wb') as f:
    f.write(icon_data)
print(f'OK: assets/icon/icon.png ({len(icon_data)} bytes)')
shutil.copy('assets/icon/icon.png', 'assets/icon/icon_fg.png')
print('OK: assets/icon/icon_fg.png')

# ============================================================
# 2. Copy web assets dari ../public/
# ============================================================
print('\nCopying web assets...')
src_dir = '../public'
dst_dir = 'assets/web'

if os.path.exists(src_dir):
    for fname in ['index.html', 'style.css', 'script.js', 'sw.js']:
        src = os.path.join(src_dir, fname)
        dst = os.path.join(dst_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f'OK: {fname}')
        else:
            print(f'SKIP: {fname} not found')
    manifest = os.path.join(src_dir, 'manifest.json')
    if os.path.exists(manifest):
        shutil.copy2(manifest, os.path.join(dst_dir, 'manifest.json'))
        print('OK: manifest.json')
else:
    print(f'WARN: {src_dir} not found')

# ============================================================
# 3. Patch script.js — apiFetch pakai URL absolut untuk file://
# ============================================================
script_path = os.path.join(dst_dir, 'script.js')
if os.path.exists(script_path):
    with open(script_path, 'r', encoding='utf-8') as f:
        js = f.read()

    BASE_URL = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app'

    old_api = """async function apiFetch(path) {
    const BASE = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';
    // Coba relative URL dulu (untuk web/PWA), fallback ke Vercel
    try {
        const r = await fetch(path);
        if (r.ok) return r;
    } catch(e) {}
    return fetch(BASE + path);
}"""

    new_api = f"""async function apiFetch(path) {{
    // Flutter WebView load dari file://, selalu pakai URL absolut
    const BASE = '{BASE_URL}';
    const url = path.startsWith('http') ? path : BASE + path;
    try {{
        const r = await fetch(url);
        if (r.ok) return r;
    }} catch(e) {{}}
    // Fallback ke deployment cadangan
    try {{
        const r2 = await fetch('https://clone2-rho.vercel.app' + (path.startsWith('http') ? '' : path));
        if (r2.ok) return r2;
    }} catch(e) {{}}
    return fetch(url);
}}"""

    if old_api in js:
        js = js.replace(old_api, new_api)
        print('\nOK: apiFetch patched (absolute URL)')
    else:
        # Fallback patch
        js = js.replace(
            "const r = await fetch(path);",
            f"const _BASE='{BASE_URL}'; const r = await fetch(path.startsWith('http')?path:_BASE+path);"
        )
        print('\nOK: apiFetch partial patch applied')

    # Patch sw.js registration — tidak perlu di APK
    js = js.replace(
        "navigator.serviceWorker.register('/sw.js')",
        "navigator.serviceWorker.register('/sw.js').catch(()=>{})"
    )

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(js)
    print('OK: script.js saved')

print('\n=== SETUP DONE ===')
print('Langkah selanjutnya:')
print('1. flutter pub get')
print('2. dart run flutter_launcher_icons')
print('3. Buat keystore: keytool -genkey -v -keystore auspoty-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias auspoty')
print('4. Buat file key.properties (lihat CARA_BUILD.md)')
print('5. flutter build appbundle --release')
