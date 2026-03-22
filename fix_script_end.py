import os, re

base = r'C:\Users\Admin\Downloads\Auspoty'
js_path = os.path.join(base, 'public', 'script.js')

with open(js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Cari posisi clearLikedSongs selesai
marker = "traryUI(); };"
pos = content.find(marker)
if pos == -1:
    print("ERROR: marker tidak ketemu")
    exit(1)

end_pos = content.find('\n}', pos) + 2
clean = content[:end_pos]

clean += '''

// REPEAT & PREV/NEXT
let isRepeat = false;
let songHistory = [];

function toggleRepeat() {
    isRepeat = !isRepeat;
    const btn = document.getElementById('repeatBtn');
    if (btn) btn.style.fill = isRepeat ? 'var(--accent)' : 'var(--text-sub)';
    showToast(isRepeat ? 'Ulangi lagu: Aktif' : 'Ulangi lagu: Nonaktif');
}
function playPrevSong() {
    if (songHistory.length < 2) { showToast('Tidak ada lagu sebelumnya'); return; }
    songHistory.pop();
    const prev = songHistory[songHistory.length - 1];
    if (prev) playMusic(prev.videoId, makeTrackData(prev));
}
function playNextSong() { playNextSimilarSong(); }

// COMMENTS
function openCommentsModal() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    const modal = document.getElementById('commentsModal');
    modal.style.display = 'flex';
    document.getElementById('commentTrackName').innerText = currentTrack.title + ' \u2014 ' + currentTrack.artist;
    const user = getGoogleUser();
    document.getElementById('commentInputArea').style.display = user ? 'block' : 'none';
    document.getElementById('commentLoginPrompt').style.display = user ? 'none' : 'block';
    loadComments(currentTrack.videoId);
}
function closeCommentsModal() { document.getElementById('commentsModal').style.display = 'none'; }

async function loadComments(videoId) {
    const list = document.getElementById('commentsList');
    list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Memuat komentar...</div>';
    try {
        const db_fs = window._firestoreDB;
        if (!db_fs) { list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Firestore belum aktif.</div>'; return; }
        const q = window._fsQuery(
            window._fsCollection(db_fs, 'comments'),
            window._fsWhere('videoId', '==', videoId),
            window._fsOrderBy('createdAt', 'desc')
        );
        const snap = await window._fsGetDocs(q);
        if (snap.empty) { list.innerHTML = '<div style="color:var(--text-sub);text-align:center;padding:20px;font-size:13px;">Belum ada komentar. Jadilah yang pertama!</div>'; return; }
        list.innerHTML = snap.docs.map(doc => {
            const d = doc.data();
            const time = d.createdAt ? new Date(d.createdAt.seconds * 1000).toLocaleDateString('id-ID', { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' }) : '';
            return '<div style="display:flex;gap:10px;align-items:flex-start;">' +
                '<div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;overflow:hidden;">' +
                (d.picture ? '<img src="'+d.picture+'" style="width:100%;height:100%;object-fit:cover;">' : d.name.charAt(0).toUpperCase()) + '</div>' +
                '<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:12px;padding:10px 14px;">' +
                '<div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="font-size:13px;font-weight:700;color:var(--accent);">' + d.name + '</span><span style="font-size:11px;color:var(--text-sub);">' + time + '</span></div>' +
                '<p style="font-size:14px;color:white;line-height:1.5;margin:0;">' + d.text + '</p></div></div>';
        }).join('');
    } catch(e) {
        list.innerHTML = '<div style="color:#ff5252;text-align:center;padding:20px;font-size:13px;">Gagal memuat: ' + e.message + '</div>';
    }
}

async function submitComment() {
    const user = getGoogleUser();
    if (!user) { showToast('Login dulu untuk berkomentar'); return; }
    if (!currentTrack) return;
    const input = document.getElementById('commentInput');
    const text = input.value.trim();
    if (!text) { showToast('Komentar tidak boleh kosong'); return; }
    try {
        await window._fsAddDoc(window._fsCollection(window._firestoreDB, 'comments'), {
            videoId: currentTrack.videoId,
            name: user.name,
            email: user.email,
            picture: user.picture || '',
            text: text,
            createdAt: window._fsTimestamp()
        });
        input.value = '';
        showToast('Komentar terkirim!');
        loadComments(currentTrack.videoId);
    } catch(e) { showToast('Gagal kirim: ' + e.message); }
}

// DOWNLOAD
function downloadMusic() {
    if (!currentTrack) { showToast('Putar lagu dulu!'); return; }
    const dlUrl = 'https://id.ytmp3.mobi/v1/#' + currentTrack.videoId;
    window.open(dlUrl, '_blank');
    showToast('Halaman download dibuka. Klik Konversi lalu Unduh MP3');
}

// INIT
applyAllSettings();
loadHomeData();
renderSearchCategories();
function updateProfileUI() {
    const user = getGoogleUser();
    const s = getSettings();
    const loginBtn = document.getElementById('googleLoginBtn');
    const logoutBtn = document.getElementById('googleLogoutBtn');
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
        const logoutSub = document.getElementById('googleLogoutSub');
        if (logoutSub) logoutSub.innerText = user.email;
        const homeAv = document.querySelector('.app-avatar');
        if (homeAv) {
            if (user.picture) {
                homeAv.innerHTML = '<img src="' + user.picture + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
            } else {
                homeAv.innerText = user.name.charAt(0).toUpperCase();
            }
        }
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'block';
    } else {
        const av = document.getElementById('settingsAvatar');
        if (av) av.innerText = (s.profileName || 'A').charAt(0).toUpperCase();
        const pname = document.getElementById('settingsProfileName');
        if (pname) pname.innerText = s.profileName || 'Pengguna Auspoty';
        const psub = document.getElementById('settingsProfileSub');
        if (psub) psub.innerText = 'Auspoty Premium';
        if (loginBtn) loginBtn.style.display = 'block';
        if (logoutBtn) logoutBtn.style.display = 'none';
    }
}
function loginWithGoogle() {
    if (typeof window._firebaseSignIn === 'function') w
}
functmGoogle() {
 ut();
}
function getGoogleUser() {
    try { return JSON.parse(localS} catch(e) { return null; }
}
fhoto(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const av = document.getElemenitProfileAvatar');
        if (av) av.innerHTML = '<img src="' + e.target.res>';
        localStorage.setItem('auspotyProfilePhoto', e.target.result);
    };
    reader.readAsDataURL(file);
}
function openEditProfile() {
    const s = getSettings();
    const user = getGoogleUser();
 '');
    const av = document.getEileAvatar');
    const photo = localStora;
    const pic = (user && user.picure) ? user.picture : photo;
    if (av) {
        if (pic) {
            av.innerHTML = '<img src="' + pic + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
        } else {
            aase();
        }
    }
    document.getlay = 'flex';
}
function e'; }
function saveProfile() {
    const name = document.getElementById('editProfileName').value.trim(uspoty';
 ; showToast('Profil disimpan!');
}
function closeLoginModal
'''

wg='utf-8') as f:
    f.write(clean)

ines()))
