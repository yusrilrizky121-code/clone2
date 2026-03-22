"""
Generate PNG launcher icons untuk semua density.
Pakai Pillow jika ada, fallback ke struct untuk buat PNG minimal.
"""
import os
import struct
import zlib

def make_png(size, bg_color, fg_color):
    """Buat PNG sederhana: background + lingkaran + segitiga play"""
    w = h = size
    # Buat pixel array RGBA
    pixels = []
    cx, cy = w // 2, h // 2
    r_outer = int(w * 0.45)
    
    for y in range(h):
        row = []
        for x in range(w):
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5
            
            if dist <= r_outer:
                # Dalam lingkaran — cek apakah dalam segitiga play
                # Segitiga: dari (cx - r*0.3, cy - r*0.4) ke (cx + r*0.4, cy) ke (cx - r*0.3, cy + r*0.4)
                r = r_outer
                p1x, p1y = cx - int(r*0.28), cy - int(r*0.38)
                p2x, p2y = cx + int(r*0.38), cy
                p3x, p3y = cx - int(r*0.28), cy + int(r*0.38)
                
                # Point in triangle test
                def sign(ax,ay,bx,by,px,py):
                    return (px-bx)*(ay-by) - (ax-bx)*(py-by)
                
                d1 = sign(p1x,p1y,p2x,p2y,x,y)
                d2 = sign(p2x,p2y,p3x,p3y,x,y)
                d3 = sign(p3x,p3y,p1x,p1y,x,y)
                
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                in_triangle = not (has_neg and has_pos)
                
                if in_triangle:
                    row.extend(fg_color)
                else:
                    row.extend(bg_color)
            else:
                row.extend(bg_color)
        pixels.append(row)
    
    # Encode PNG
    def png_chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)
    
    # IHDR
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    
    # IDAT - raw image data
    raw = b''
    for row in pixels:
        raw += b'\x00'  # filter type none
        for i in range(0, len(row), 4):
            raw += bytes(row[i:i+3])  # RGB only (drop alpha)
    
    # Re-encode as RGBA for proper transparency
    raw2 = b''
    for row in pixels:
        raw2 += b'\x00'
        for i in range(0, len(row), 4):
            raw2 += bytes(row[i:i+4])
    
    ihdr2 = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)  # RGBA
    compressed = zlib.compress(raw2, 9)
    
    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', ihdr2)
    png += png_chunk(b'IDAT', compressed)
    png += png_chunk(b'IEND', b'')
    return png

# Warna: background hitam, foreground hijau Spotify
BG = (18, 18, 18, 255)    # #121212
FG = (30, 215, 96, 255)   # #1ed760

sizes = {
    'mipmap-mdpi':    48,
    'mipmap-hdpi':    72,
    'mipmap-xhdpi':   96,
    'mipmap-xxhdpi':  144,
    'mipmap-xxxhdpi': 192,
}

base = os.path.join(os.path.dirname(__file__), 'app', 'src', 'main', 'res')

for folder, size in sizes.items():
    path = os.path.join(base, folder)
    os.makedirs(path, exist_ok=True)
    
    png_data = make_png(size, BG, FG)
    
    for name in ['ic_launcher.png', 'ic_launcher_round.png']:
        fpath = os.path.join(path, name)
        with open(fpath, 'wb') as f:
            f.write(png_data)
        print(f"Created: {folder}/{name} ({size}x{size})")

print("Done!")
