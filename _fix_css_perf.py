with open('public/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Remove heavy radial-gradient background on body (very expensive on low-end GPU)
old_body_bg = '''body {
    background-color: var(--bg-base);
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(124,58,237,0.25) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 10%, rgba(244,114,182,0.15) 0%, transparent 50%),
        radial-gradient(ellipse 50% 60% at 50% 100%, rgba(56,189,248,0.1) 0%, transparent 60%);
    background-attachment: fixed;'''

new_body_bg = '''body {
    background-color: var(--bg-base);
    background-image: none;'''

if old_body_bg in content:
    content = content.replace(old_body_bg, new_body_bg)
    print("Removed heavy radial-gradient background")
else:
    print("WARNING: body bg pattern not found")

# Fix 2: Reduce backdrop-filter blur values (blur(80px) is very heavy)
# Player bg blur: 80px -> 40px
content = content.replace('filter:blur(80px) brightness(.18) saturate(3);', 'filter:blur(40px) brightness(.2) saturate(2);')
# Lyrics bg blur
content = content.replace('filter:blur(60px) brightness(.2) saturate(2);', 'filter:blur(30px) brightness(.2) saturate(2);')

# Fix 3: Reduce backdrop-filter on nav/mini-player (blur(30px) -> blur(15px))
content = content.replace('backdrop-filter:blur(30px);', 'backdrop-filter:blur(15px);')
content = content.replace('-webkit-backdrop-filter:blur(30px);', '-webkit-backdrop-filter:blur(15px);')
content = content.replace('backdrop-filter:blur(40px);', 'backdrop-filter:blur(20px);')
content = content.replace('-webkit-backdrop-filter:blur(40px);', '-webkit-backdrop-filter:blur(20px);')
content = content.replace('backdrop-filter:blur(20px);', 'backdrop-filter:blur(12px);')
content = content.replace('-webkit-backdrop-filter:blur(20px);', '-webkit-backdrop-filter:blur(12px);')

# Fix 4: Add will-change and contain to scrollable sections for GPU layer promotion
# Add after .view-section.active
old_view = '.view-section.active { display:block; }'
new_view = '.view-section.active { display:block; contain:layout style; }'
content = content.replace(old_view, new_view)

# Fix 5: Add contain to cards for faster paint
old_vitem = '.v-item { display:grid; grid-template-columns:52px 1fr 24px; gap:12px; align-items:center; cursor:pointer; padding:10px 12px; border-radius:14px; background:var(--glass); border:1px solid var(--glass-border); backdrop-filter:blur(10px); transition:all .2s; }'
new_vitem = '.v-item { display:grid; grid-template-columns:52px 1fr 24px; gap:12px; align-items:center; cursor:pointer; padding:10px 12px; border-radius:14px; background:var(--glass); border:1px solid var(--glass-border); backdrop-filter:blur(6px); transition:background .15s; contain:layout style; }'
content = content.replace(old_vitem, new_vitem)

# Fix 6: Reduce transition on h-card (was 'all .2s' which is expensive)
content = content.replace('.h-card:active { transform:scale(.95); }', '.h-card:active { opacity:.8; }')

# Fix 7: Remove box-shadow animations on mini-player (expensive)
content = content.replace(
    'box-shadow:0 8px 40px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,0.08);',
    'box-shadow:0 4px 20px rgba(0,0,0,.6);'
)

# Fix 8: Simplify player art box-shadow
content = content.replace(
    'box-shadow:0 32px 80px rgba(0,0,0,.85), 0 0 0 1px rgba(255,255,255,0.08);',
    'box-shadow:0 16px 40px rgba(0,0,0,.7);'
)
content = content.replace(
    'box-shadow:0 36px 90px rgba(167,139,250,0.45), 0 0 0 2px rgba(167,139,250,0.25);',
    'box-shadow:0 16px 40px rgba(167,139,250,0.35);'
)

with open('public/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("CSS performance optimizations applied!")
