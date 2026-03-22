"""
Patch player screen UI di public/ dan auspoty-apk/assets/
- Ganti playback controls: shuffle | prev | play | next | repeat
- Tambah baris bawah: cast | timer | queue | lyrics | like
- Update CSS
"""
import re

TARGETS = [
    "public/index.html",
    "auspoty-apk/app/src/main/assets/index.html",
]

CSS_TARGETS = [
    "public/style.css",
    "auspoty-apk/app/src/main/assets/style.css",
]

# ── HTML: ganti track-info (hapus ikon yg pindah ke bawah) ──────────────────
OLD_TRACK_INFO = re.compile(
    r'<div class="player-track-info">.*?</div>\s*</div>',
    re.DOTALL
)

NEW_TRACK_INFO = '''\
        <div class="player-track-info">
            <div style="overflow:hidden;flex:1;">
                <div id="playerTitle" class="player-title">Judul Lagu</div>
                <div id="playerArtist" class="player-artist">Artis</div>
            </div>
            <div id="btnBgMode" onclick="toggleBgMode()" title="Mode Latar Belakang" style="width:44px;height:44px;flex-shrink:0;cursor:pointer;display:flex;align-items:center;justify-content:center;border-radius:50%;-webkit-tap-highlight-color:rgba(255,255,255,0.1);touch-action:manipulation;">
                <svg id="btnBgModeIcon" viewBox="0 0 24 24" style="width:26px;height:26px;fill:rgba(255,255,255,0.5);transition:fill 0.2s;pointer-events:none;"><path d="M12 3a9 9 0 0 0-9 9v7c0 1.1.9 2 2 2h1v-8H4v-1a8 8 0 0 1 16 0v1h-2v8h1c1.1 0 2-.9 2-2v-7a9 9 0 0 0-9-9z"/></svg>
            </div>
            <svg id="btnLikeSong" viewBox="0 0 24 24" onclick="toggleLike()" style="width:28px;height:28px;flex-shrink:0;cursor:pointer;fill:rgba(255,255,255,0.5);"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
        </div>'''

# ── HTML: ganti playback-controls + tambah bottom-actions ───────────────────
OLD_CONTROLS = re.compile(
    r'<div class="playback-controls">.*?</div>\s*</div>\s*</div>',
    re.DOTALL
)

NEW_CONTROLS = '''\
        <div class="playback-controls">
            <svg id="shuffleBtn" viewBox="0 0 24 24" onclick="toggleShuffle()" style="fill:var(--text-sub);width:24px;height:24px;cursor:pointer;" title="Acak"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>
            <svg viewBox="0 0 24 24" onclick="playPrevSong()" style="fill:white;width:36px;height:36px;cursor:pointer;"><path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/></svg>
            <div class="play-pause-btn" onclick="togglePlay()" style="width:64px;height:64px;border-radius:50%;background:rgba(167,139,250,0.25);display:flex;justify-content:center;align-items:center;cursor:pointer;">
                <svg id="mainPlayBtn" viewBox="0 0 24 24" style="fill:white;width:32px;height:32px;"><path d="M8 5v14l11-7z"/></svg>
            </div>
            <svg viewBox="0 0 24 24" onclick="playNextSong()" style="fill:white;width:36px;height:36px;cursor:pointer;"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
            <svg id="repeatBtn" viewBox="0 0 24 24" onclick="toggleRepeat()" style="fill:var(--text-sub);width:24px;height:24px;cursor:pointer;" title="Ulangi"><path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/></svg>
        </div>
        <div class="player-bottom-actions">
            <div class="player-action-btn" onclick="openCastMenu()" title="Cast">
                <svg viewBox="0 0 24 24"><path d="M1 18v3h3c0-1.66-1.34-3-3-3zm0-4v2c2.76 0 5 2.24 5 5h2c0-3.87-3.13-7-7-7zm18-7H5c-1.1 0-2 .9-2 2v3h2v-3h14v10h-5v2h5c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm-18 3v2c4.97 0 9 4.03 9 9h2c0-6.08-4.93-11-11-11z"/></svg>
                <span>Cast</span>
            </div>
            <div class="player-action-btn" onclick="openSleepTimer()" title="Timer">
                <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/></svg>
                <span>Timer</span>
            </div>
            <div class="player-action-btn" onclick="openQueueModal()" title="Antrian">
                <svg viewBox="0 0 24 24"><path d="M3 18h13v-2H3v2zm0-5h10v-2H3v2zm0-7v2h13V6H3zm18 9.59L17.42 12 21 8.41 19.59 7l-5 5 5 5L21 15.59z"/></svg>
                <span>Antrian</span>
            </div>
            <div class="player-action-btn" onclick="openLyricsModal()" title="Lirik">
                <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h6v6h6v10H6zm2-7h8v2H8v-2zm0 4h5v2H8v-2z"/></svg>
                <span>Lirik</span>
            </div>
            <div class="player-action-btn" onclick="toggleLike()" title="Suka">
                <svg id="btnLikeSong2" viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                <span>Suka</span>
            </div>
        </div>
    </div>
</div>'''

# ── CSS baru ─────────────────────────────────────────────────────────────────
OLD_CSS = '.playback-controls { display:flex; justify-content:space-between; align-items:center; padding:0 28px 20px; }'
NEW_CSS = '''.playback-controls { display:flex; justify-content:space-between; align-items:center; padding:0 28px 20px; }

/* PLAYER BOTTOM ACTIONS */
.player-bottom-actions { display:flex; justify-content:space-around; align-items:center; padding:12px 16px 36px; border-top:1px solid rgba(255,255,255,0.08); }
.player-action-btn { display:flex; flex-direction:column; align-items:center; gap:6px; cursor:pointer; opacity:0.6; transition:opacity .2s; min-width:48px; }
.player-action-btn:active { opacity:1; }
.player-action-btn svg { fill:white; width:22px; height:22px; }
.player-action-btn span { font-size:10px; color:rgba(255,255,255,0.7); font-weight:500; }'''

def patch_html(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        # Ganti track-info section
        content = re.sub(
            r'<div class="player-track-info">.*?</div>\s*(?=<div class="progress-container">)',
            NEW_TRACK_INFO + '\n        ',
            content, flags=re.DOTALL
        )

        # Ganti playback-controls + tutup wrapper
        content = re.sub(
            r'<div class="playback-controls">.*?</div>\s*</div>\s*</div>(?=\s*<!-- LYRICS)',
            NEW_CONTROLS + '\n',
            content, flags=re.DOTALL
        )

        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] {path}")
        else:
            print(f"[SKIP - no change] {path}")
    except Exception as e:
        print(f"[ERROR] {path}: {e}")

def patch_css(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        if OLD_CSS in content:
            content = content.replace(OLD_CSS, NEW_CSS)
        elif '.player-bottom-actions' not in content:
            # Tambahkan di akhir
            content += '\n' + NEW_CSS

        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK CSS] {path}")
        else:
            print(f"[SKIP CSS] {path}")
    except Exception as e:
        print(f"[ERROR CSS] {path}: {e}")

for p in TARGETS:
    patch_html(p)
for p in CSS_TARGETS:
    patch_css(p)
