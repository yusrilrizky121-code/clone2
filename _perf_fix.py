# ============================================================
# PERFORMANCE FIX — CSS, JS lazy load, Flutter WebView
# ============================================================

# ---- 1. CSS FIXES ----
with open('public/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Remove background-attachment: fixed (kills GPU accel on Android WebView)
css = css.replace('    background-attachment: fixed;\n', '')

# Remove heavy radial-gradient background on body (repaint every scroll)
old_bg = '''    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(124,58,237,0.25) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 10%, rgba(244,114,182,0.15) 0%, transparent 50%),
        radial-gradient(ellipse 50% 60% at 50% 100%, rgba(56,189,248,0.1) 0%, transparent 60%);'''
new_bg = '    background-image: none;'
css = css.replace(old_bg, new_bg)

# Replace all backdrop-filter:blur(X) with lighter version or remove on non-critical elements
# Keep only on bottom-nav and player (critical), reduce others
css = css.replace('backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);', 'backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);')
css = css.replace('backdrop-filter:blur(30px); -webkit-backdrop-filter:blur(30px);', 'backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);')
css = css.replace('backdrop-filter:blur(40px); -webkit-backdrop-filter:blur(40px);', 'backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);')
css = css.replace('backdrop-filter:blur(10px);', 'backdrop-filter:blur(6px);')
css = css.replace('backdrop-filter:blur(20px);', 'backdrop-filter:blur(8px);')
css = css.replace('backdrop-filter:blur(30px);', 'backdrop-filter:blur(12px);')
css = css.replace('backdrop-filter:blur(40px);', 'backdrop-filter:blur(16px);')

# v-item: remove backdrop-filter (most items on screen = most expensive)
css = css.replace(
    '.v-item { display:grid; grid-template-columns:52px 1fr 24px; gap:12px; align-items:center; cursor:pointer; padding:10px 12px; border-radius:14px; background:var(--glass); border:1px solid var(--glass-border); backdrop-filter:blur(6px); transition:all .2s; }',
    '.v-item { display:grid; grid-template-columns:52px 1fr 24px; gap:12px; align-items:center; cursor:pointer; padding:10px 12px; border-radius:14px; background:rgba(255,255,255,0.07); border:1px solid var(--glass-border); transition:background .15s; }'
)

# lib-item: remove backdrop-filter
css = css.replace(
    '.lib-item { display:flex; align-items:center; gap:14px; cursor:pointer; padding:10px 12px; border-radius:14px; background:var(--glass); border:1px solid var(--glass-border); backdrop-filter:blur(6px); transition:all .2s; }',
    '.lib-item { display:flex; align-items:center; gap:14px; cursor:pointer; padding:10px 12px; border-radius:14px; background:rgba(255,255,255,0.07); border:1px solid var(--glass-border); transition:background .15s; }'
)

# pill: remove backdrop-filter
css = css.replace('border:1px solid var(--glass-border); backdrop-filter:blur(6px); transition:all .2s; }', 'border:1px solid var(--glass-border); transition:background .15s; }')

# Player bg blur: reduce from 80px to 40px
css = css.replace('filter:blur(80px) brightness(.18) saturate(3);', 'filter:blur(40px) brightness(.2) saturate(2);')

# section-title: remove gradient text (expensive on Android)
css = css.replace(
    '.section-title { font-size:20px; font-weight:700; margin:0 20px 16px; letter-spacing:-.3px; background:linear-gradient(90deg,#fff,rgba(255,255,255,0.7)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }',
    '.section-title { font-size:20px; font-weight:700; margin:0 20px 16px; letter-spacing:-.3px; color:#fff; }'
)

# Add will-change and contain for scroll performance
perf_css = '''
/* ============================================================
   PERFORMANCE — GPU hints for smooth scroll on low-end devices
   ============================================================ */
.horizontal-scroll { -webkit-overflow-scrolling:touch; will-change:scroll-position; }
.view-section { contain:layout style; }
.v-item, .lib-item, .h-card { contain:layout style paint; }
.mini-player { will-change:transform; }
.modal-overlay { will-change:transform; }
img { content-visibility:auto; }
'''
css += perf_css

with open('public/style.css', 'w', encoding='utf-8') as f:
    f.write(css)
print("CSS fixed")

# ---- 2. JS FIXES — lazy load home rows ----
with open('public/script.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace loadHomeData to load rows lazily (2 at a time, not all at once)
old_load = '''    for (const row of getHomeQueries()) {
        const el = document.getElementById(row.id); if (!el) continue;
        el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Memuat...</div>';
        try {
            const res = await apiFetch('/api/search?query=' + encodeURIComponent(row.query));
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) el.innerHTML = result.data.slice(0, 10).map(renderHCard).join('');
            else el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Tidak ada hasil.</div>';
        } catch(e) { el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Gagal memuat.</div>'; }
    }'''

new_load = '''    // Lazy load: 2 rows at a time to avoid hammering API and blocking main thread
    const rows = getHomeQueries();
    async function loadRow(row) {
        const el = document.getElementById(row.id); if (!el) return;
        el.innerHTML = '<div style="color:var(--text-sub);padding:8px 0;font-size:13px;">Memuat...</div>';
        try {
            const res = await apiFetch('/api/search?query=' + encodeURIComponent(row.query));
            const result = await res.json();
            if (result.status === 'success' && result.data.length > 0) el.innerHTML = result.data.slice(0, 8).map(renderHCard).join('');
            else el.innerHTML = '';
        } catch(e) { el.innerHTML = ''; }
    }
    // Load first 2 rows immediately, rest after 800ms delay
    for (let i = 0; i < rows.length; i++) {
        if (i < 2) { loadRow(rows[i]); }
        else { setTimeout(() => loadRow(rows[i]), 800 + (i - 2) * 400); }
    }'''

if old_load in js:
    js = js.replace(old_load, new_load)
    print("JS lazy load patched")
else:
    print("WARNING: loadHomeData loop not found, skipping")

# Reduce image quality requests (use smaller thumbnails)
js = js.replace(
    "return url.replace(/=w\\d+-h\\d+/, '=w500-h500').replace(/w\\d+_h\\d+/, 'w500_h500');",
    "return url.replace(/=w\\d+-h\\d+/, '=w300-h300').replace(/w\\d+_h\\d+/, 'w300_h300');"
)

# Reduce progress bar interval from 500ms to 1000ms (less CPU)
js = js.replace('    }, 500);\n}\nfunction stopProgressBar', '    }, 1000);\n}\nfunction stopProgressBar')

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("JS fixed")

print("\nAll performance fixes applied!")
