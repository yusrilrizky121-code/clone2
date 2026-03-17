js_path = r'C:\Users\Admin\Downloads\Auspoty\public\script.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

# Ganti fungsi loginWithGoogle dan _showLoginModal
import re

old_block = re.compile(
    r'// ===================== GOOGLE LOGIN =====================.*?(?=\n// INIT)',
    re.DOTALL
)

new_block = """// ===================== GOOGLE LOGIN =====================
// Di APK Android: pakai AccountManager (seperti Metrolist) — tanpa Google Console
// Di Web: pakai Google GSI dengan Client ID
const GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID';

function loginWithGoogle() {
    const user = getGoogleUser();
    if (user) {
        if (confirm('Keluar dari akun ' + user.name + '?')) {
            localStorage.removeItem('auspotyGoogleUser');
            updateProfileUI();
            showToast('Berhasil keluar');
        }
        return;
    }
    // Cek apakah running di APK Android dengan AndroidBridge
    if (window.AndroidBridge && window.AndroidBridge.isAndroid()) {
        _showAndroidAccountPicker();
    } else {
        _showLoginModal();
    }
}

// ---- ANDROID: Tampilkan picker akun Google dari HP ----
function _showAndroidAccountPicker() {
    try {
        const accountsJson = window.AndroidBridge.getGoogleAccounts();
        const accounts = JSON.parse(accountsJson);
        if (accounts.length === 0) {
            showToast('Tidak ada akun Google di HP ini');
            return;
        }
        if (accounts.length === 1) {
            // Langsung login jika hanya 1 akun
            window.AndroidBridge.loginWithAccount(accounts[0].email);
            return;
        }
        // Tampilkan modal pilih akun
        _renderAccountPickerModal(accounts);
    } catch(e) {
        showToast('Gagal ambil akun Google');
        console.error(e);
    }
}

function _renderAccountPickerModal(accounts) {
    // Buat modal pilih akun
    let existing = document.getElementById('accountPickerModal');
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = 'accountPickerModal';
    modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.85);display:flex;align-items:flex-end;justify-content:center;';
    let items = accounts.map(function(acc) {
        return '<div onclick="_selectAccount(\\'' + acc.email + '\\')" style="display:flex;align-items:center;gap:14px;padding:16px 20px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,0.07);">' +
            '<div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#1ed760,#17a84a);display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#000;flex-shrink:0;">' + acc.email.charAt(0).toUpperCase() + '</div>' +
            '<div><div style="color:white;font-size:15px;font-weight:600;">' + acc.displayName + '</div><div style="color:rgba(255,255,255,0.5);font-size:13px;">' + acc.email + '</div></div>' +
            '</div>';
    }).join('');
    modal.innerHTML = '<div style="background:#1a1a2e;width:100%;border-radius:20px 20px 0 0;padding-bottom:24px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;padding:20px 20px 12px;">' +
        '<h3 style="color:white;font-size:17px;font-weight:700;margin:0;">Pilih Akun Google</h3>' +
        '<div onclick="_closeAccountPicker()" style="width:30px;height:30px;border-radius:50%;background:rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;cursor:pointer;color:white;font-size:16px;">✕</div>' +
        '</div>' + items + '</div>';
    document.body.appendChild(modal);
}

function _selectAccount(email) {
    _closeAccountPicker();
    if (window.AndroidBridge) {
        window.AndroidBridge.loginWithAccount(email);
    }
}

function _closeAccountPicker() {
    const m = document.getElementById('accountPickerModal');
    if (m) m.remove();
}

// ---- WEB: Tampilkan modal login Google GSI ----
function _showLoginModal() {
    const modal = document.getElementById('loginModal');
    modal.style.display = 'flex';
    if (window.google && window.google.accounts && GOOGLE_CLIENT_ID !== 'YOUR_GOOGLE_CLIENT_ID') {
        try {
            google.accounts.id.initialize({
                client_id: GOOGLE_CLIENT_ID,
                callback: handleGoogleLogin,
                auto_select: false,
                cancel_on_tap_outside: false,
            });
            const btnContainer = document.getElementById('googleSignInBtn');
            if (btnContainer) {
                btnContainer.innerHTML = '';
                google.accounts.id.renderButton(btnContainer, {
                    theme: 'filled_blue', size: 'large', width: 280,
                    text: 'signin_with', shape: 'rectangular',
                });
            }
        } catch(e) { console.error('Google GSI error:', e); }
    }
}

function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
}

function handleGoogleLogin(response) {
    try {
        const parts = response.credential.split('.');
        const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
        const user = {
            name: payload.name || 'Pengguna Google',
            email: payload.email || '',
            picture: payload.picture || '',
            sub: payload.sub || '',
        };
        localStorage.setItem('auspotyGoogleUser', JSON.stringify(user));
        closeLoginModal();
        updateProfileUI();
        showToast('Selamat datang, ' + user.name.split(' ')[0] + '!');
    } catch(e) {
        showToast('Login gagal, coba lagi');
    }
}

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
    print('Login block replaced OK')
else:
    marker = '// ===================== GOOGLE LOGIN ====================='
    init_marker = '\n// INIT'
    start = js.find(marker)
    end = js.find(init_marker)
    if start != -1 and end != -1:
        js = js[:start] + new_block.strip() + '\n' + js[end:]
        print('Login block replaced via manual find OK')
    else:
        print('ERROR: markers not found')

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)
print('script.js saved OK')
