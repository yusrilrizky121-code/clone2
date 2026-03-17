import re

html_path = r'C:\Users\Admin\Downloads\Auspoty\auspoty-apk\app\src\main\assets\index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Hapus semua sisa modal login — cari dari div yang mengandung googleSignInBtn sampai </div></div>
# Pattern: apapun yang mengandung googleSignInBtn atau closeLoginModal atau Nanti saja
# Hapus dari <div id="loginModal" atau sisa fragment modal sampai </body>

# Cari posisi </body> terakhir yang valid
# Hapus semua yang ada di antara </div> terakhir sebelum </body> dan </body>

# Strategi: potong di </body> pertama, buang semua setelah itu, tambah </body></html> bersih
body_end = html.find('</body>')
if body_end != -1:
    # Ambil konten sampai </body>
    content = html[:body_end]
    
    # Hapus sisa fragment modal login jika ada (div yang mengandung googleSignInBtn / Nanti saja)
    # Cari div pembuka modal yang tersisa
    modal_patterns = [
        re.compile(r'<div[^>]*id=["\']loginModal["\'][^>]*>.*?</div>\s*</div>', re.DOTALL),
        re.compile(r'<div[^>]*>.*?googleSignInBtn.*?</div>\s*</div>', re.DOTALL),
        re.compile(r'<div[^>]*>.*?Nanti saja.*?</div>\s*</div>', re.DOTALL),
    ]
    for pat in modal_patterns:
        content = pat.sub('', content)
    
    # Juga hapus baris yang hanya berisi sisa tag div/button dari modal
    # Hapus fragment: <div ...><button onclick="closeLoginModal()"...>Nanti saja</button></div></div>
    content = re.sub(r'<div[^>]*>\s*<div[^>]*>\s*<button[^>]*closeLoginModal[^>]*>.*?</button>\s*</div>\s*</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<button[^>]*closeLoginModal[^>]*>.*?</button>', '', content, flags=re.DOTALL)
    
    # Bersihkan whitespace berlebih di akhir
    content = content.rstrip()
    
    html = content + '\n</body>\n</html>\n'
    print('HTML cleaned OK')
else:
    print('ERROR: </body> not found')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

# Verifikasi
html2 = open(html_path, encoding='utf-8').read()
print('Nanti saja masih ada:', 'Nanti saja' in html2)
print('loginModal masih ada:', 'loginModal' in html2)
print('closeLoginModal masih ada:', 'closeLoginModal' in html2)
print('</html> count:', html2.count('</html>'))
print('Done!')
