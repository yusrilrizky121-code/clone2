"""
Ganti login Google di web dengan Firebase Authentication.
Firebase Console (console.firebase.google.com) BERBEDA dari Google Cloud Console.
Setup Firebase cuma 5 menit dan gratis selamanya untuk auth.

Cara setup (sekali saja):
1. Buka https://console.firebase.google.com
2. Klik "Add project" → beri nama → Continue
3. Klik "Authentication" → "Get started" → pilih "Google" → Enable → Save
4. Klik ikon gear (Project settings) → scroll ke "Your apps" → klik "</>  Web"
5. Register app → copy firebaseConfig
6. Ganti FIREBASE_CONFIG di bawah ini
"""

import re

html_path = r'C:\Users\Admin\Downloads\Auspoty\public\index.html'
js_path = r'C:\Users\Admin\Downloads\Auspoty\public\script.js'

# ---- Patch index.html ----
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Hapus GSI script lama
html = re.sub(r'\s*<script src="https://accounts\.google\.com/gsi/client"[^>]*></script>', '', html)

# Tambah Firebase SDK di <head>
firebase_scripts = '''    <!-- Firebase Auth SDK -->
    <script type="module">
      import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
      import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged }
        from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js';

      // =====================================================
      // GANTI CONFIG INI dengan config dari Firebase Console
      // console.firebase.google.com → Project Settings → Your apps → Web
      // =====================================================
      const firebaseConfig = {
        apiKey: "FIREBASE_API_KEY",
        authDomain: "FIREBASE_AUTH_DOMAIN",
        projectId: "FIREBASE_PROJECT_ID",
        appId: "FIREBASE_APP_ID"
      };

      const app = initializeApp(firebaseConfig);
      const auth = getAuth(app);
      const provider = new GoogleAuthProvider();

      // Expose ke window supaya bisa dipanggil dari script.js
      window._firebaseAuth = auth;
      window._firebaseProvider = provider;
      window._firebaseSignIn = async function() {
        try {
          const result = await signInWithPopup(auth, provider);
          const user = result.user;
          const userData = {
            name: user.displayName || 'Pengguna Google',
            email: user.email || '',
            picture: user.photoURL || '',
            sub: user.uid || '',
          };
          localStorage.setItem('auspotyGoogleUser', JSON.stringify(userData));
          if (typeof updateProfileUI === 'function') updateProfileUI();
          if (typeof showToast === 'function') showToast('Selamat datang, ' + userData.name.split(' ')[0] + '!');
          const modal = document.getElementById('loginModal');
          if (modal) modal.style.display = 'none';
        } catch(e) {
          console.error('Firebase login error:', e);
          if (typeof showToast === 'function') showToast('Login gagal: ' + (e.message || 'coba lagi'));
        }
      };
      window._firebaseSignOut = async function() {
        try {
          await signOut(auth);
          localStorage.removeItem('auspotyGoogleUser');
          if (typeof updateProfileUI === 'function') updateProfileUI();
          if (typeof showToast === 'function') showToast('Berhasil keluar');
        } catch(e) {}
      };
      // Cek status login saat load
      onAuthStateChanged(auth, (user) => {
        if (user) {
          const userData = {
            name: user.displayName || 'Pengguna Google',
            email: user.email || '',
            picture: user.photoURL || '',
            sub: user.uid || '',
          };
          localStorage.setItem('auspotyGoogleUser', JSON.stringify(userData));
          if (typeof updateProfileUI === 'function') updateProfileUI();
        }
      });
    </script>'''

# Sisipkan sebelum </head>
html = html.replace('</head>', firebase_scripts + '\n</head>')

# Ganti loginModal dengan versi Firebase
old_modal_pattern = re.compile(r'<!-- GOOGLE LOGIN MODAL -->.*?(?=</body>)', re.DOTALL)

new_modal = '''<!-- GOOGLE LOGIN MODAL -->
<div id="loginModal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.9);align-items:center;justify-content:center;">
    <div style="background:#1a1a2e;border-radius:20px;padding:32px 24px 28px;width:90%;max-width:360px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.8);position:relative;">
        <button onclick="closeLoginModal()" style="position:absolute;top:14px;right:14px;background:rgba(255,255,255,0.1);border:none;color:white;width:30px;height:30px;border-radius:50%;font-size:16px;cursor:pointer;">✕</button>
        <div style="font-size:44px;margin-bottom:10px;">🎵</div>
        <h2 style="color:white;font-size:22px;font-weight:700;margin-bottom:6px;">Masuk ke Auspoty</h2>
        <p style="color:rgba(255,255,255,0.55);font-size:13px;margin-bottom:24px;line-height:1.5;">Login untuk menyimpan playlist<br>dan lagu favorit kamu</p>
        <button onclick="loginWithGoogle()" style="display:flex;align-items:center;justify-content:center;gap:12px;width:100%;background:white;color:#333;border:none;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;margin-bottom:12px;">
            <svg viewBox="0 0 48 48" style="width:22px;height:22px;flex-shrink:0;">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Masuk dengan Google
        </button>
        <button onclick="closeLoginModal()" style="background:transparent;border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.5);padding:10px 28px;border-radius:20px;font-size:13px;cursor:pointer;width:100%;">Nanti saja</button>
    </div>
</div>

'''

if old_modal_pattern.search(html):
    html = old_modal_pattern.sub(new_modal, html)
    print('loginModal replaced OK')
else:
    # Sisipkan sebelum </body>
    html = html.replace('</body>', new_modal + '</body>')
    print('loginModal inserted before </body>')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('index.html saved OK')

# ---- Patch script.js ----
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

old_block = re.compile(
    r'// ===================== GOOGLE LOGIN =====================.*?(?=\n// INIT)',
    re.DOTALL
)

new_block = """// ===================== GOOGLE LOGIN =====================
// Login Google via Firebase Auth — tidak butuh Google Cloud Console
// Setup: console.firebase.google.com → Authentication → Google → Enable
// Lalu ganti FIREBASE_CONFIG di index.html

function loginWithGoogle() {
    const user = getGoogleUser();
    if (user) {
        if (confirm('Keluar dari akun ' + user.name + '?')) {
            if (window._firebaseSignOut) {
                window._firebaseSignOut();
            } else {
                localStorage.removeItem('auspotyGoogleUser');
                updateProfileUI();
                showToast('Berhasil keluar');
            }
        }
        return;
    }
    // Cek apakah Firebase sudah dikonfigurasi
    if (window._firebaseSignIn) {
        // Cek apakah config sudah diisi (bukan placeholder)
        if (typeof firebaseConfig !== 'undefined' && firebaseConfig.apiKey === 'FIREBASE_API_KEY') {
            _showFirebaseSetupInfo();
            return;
        }
        window._firebaseSignIn();
    } else {
        // Firebase belum load, tampilkan modal
        document.getElementById('loginModal').style.display = 'flex';
    }
}

function _showFirebaseSetupInfo() {
    document.getElementById('loginModal').style.display = 'flex';
}

function closeLoginModal() {
    const m = document.getElementById('loginModal');
    if (m) m.style.display = 'none';
}

function handleGoogleLogin(response) {}

function getGoogleUser() {
    try { return JSON.parse(localStorage.getItem('auspotyGoogleUser') || 'null'); } catch(e) { return null; }
}

function updateProfileUI() {
    const user = getGoogleUser();
    const s = getSettings();
    if (user) {
        const av = document.getElementById('settingsAvatar');
        if (av) {
            if (user.picture) {
                av.innerHTML = '<img src="' + user.picture + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
            } else {
                av.innerText = user.name.charAt(0).toUpperCase();
            }
        }
        const pname = document.getElementById('settingsProfileName');
        if (pname) pname.innerText = user.name;
        const psub = document.getElementById('settingsProfileSub');
        if (psub) psub.innerText = user.email;
        const loginText = document.getElementById('googleLoginText');
        if (loginText) loginText.innerText = 'Keluar dari Google';
        const loginSub = document.getElementById('googleLoginSub');
        if (loginSub) loginSub.innerText = user.email;
        const homeAv = document.querySelector('.app-avatar');
        if (homeAv) {
            if (user.picture) {
                homeAv.innerHTML = '<img src="' + user.picture + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
            } else {
                homeAv.innerText = user.name.charAt(0).toUpperCase();
            }
        }
    } else {
        const av = document.getElementById('settingsAvatar');
        if (av) av.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
        const pname = document.getElementById('settingsProfileName');
        if (pname) pname.innerText = s.profileName || 'Pengguna Auspoty';
        const psub = document.getElementById('settingsProfileSub');
        if (psub) psub.innerText = 'Auspoty Premium';
        const loginText = document.getElementById('googleLoginText');
        if (loginText) loginText.innerText = 'Masuk dengan Google';
        const loginSub = document.getElementById('googleLoginSub');
        if (loginSub) loginSub.innerText = 'Sinkronkan data kamu';
    }
}

"""

if old_block.search(js):
    js = old_block.sub(new_block.strip(), js)
    print('script.js login block replaced OK')
else:
    marker = '// ===================== GOOGLE LOGIN ====================='
    init_marker = '\n// INIT'
    start = js.find(marker)
    end = js.find(init_marker)
    if start != -1 and end != -1:
        js = js[:start] + new_block.strip() + '\n' + js[end:]
        print('script.js replaced via manual find OK')
    else:
        print('ERROR: marker not found')

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)
print('script.js saved OK')
