import re

css = open('public/style.css', encoding='utf-8').read()

# 1. Remove ALL remaining transitions (every transition fires on scroll touch)
# Keep only: toggle thumb, mini-player progress fill, player art wrapper
lines = css.split('\n')
out = []
for line in lines:
    stripped = line.strip()
    # Remove transition lines except for specific safe ones
    if stripped.startswith('transition:') or stripped.startswith('transition :'):
        # Keep only these specific transitions
        keep = [
            'transition:transform .25s',   # toggle thumb
            'transition:background .25s',  # toggle bg
            'transition:width .3s linear', # progress fill
            'transition:transform .3s',    # art wrapper scale
            'transition:background-image', # player bg
        ]
        if any(k in stripped for k in keep):
            out.append(line)
        # else: skip (remove)
    else:
        out.append(line)
css = '\n'.join(out)

# 2. Add overscroll-behavior: none to body (prevents scroll chaining lag)
css = css.replace(
    '    -webkit-font-smoothing: antialiased;\n    font-size: var(--base-font-size);',
    '    -webkit-font-smoothing: antialiased;\n    font-size: var(--base-font-size);\n    overscroll-behavior: none;'
)

# 3. Add touch-action: pan-y to scroll containers (hint browser for scroll optimization)
css = css.replace(
    '.horizontal-scroll { display:flex; overflow-x:auto;',
    '.horizontal-scroll { display:flex; overflow-x:auto; touch-action:pan-x;'
)

# 4. Remove :active transform scale from list items (causes layout recalc on tap)
css = re.sub(r'\.v-item:active \{[^}]+\}', '.v-item:active { background:var(--bg-highlight); }', css)
css = re.sub(r'\.lib-item:active \{[^}]+\}', '.lib-item:active { background:var(--bg-highlight); }', css)
css = re.sub(r'\.h-card:active \{[^}]+\}', '', css)
css = re.sub(r'\.category-card:active \{[^}]+\}', '', css)
css = re.sub(r'\.play-pause-btn:active \{[^}]+\}', '', css)
css = re.sub(r'\.ctrl-btn:active \{[^}]+\}', '', css)
css = re.sub(r'\.settings-profile-card:active \{[^}]+\}', '', css)
css = re.sub(r'\.settings-item:active \{[^}]+\}', '', css)
css = re.sub(r'\.picker-option:active \{[^}]+\}', '', css)
css = re.sub(r'\.dev-cta-btn:active \{[^}]+\}', '', css)

# 5. Remove box-shadow from player art wrapper (expensive during scale animation)
css = re.sub(r'\s*box-shadow:0 16px 40px[^;]+;', '', css)

# 6. Simplify mini-player animation (slideUpMini is fine, but remove will-change from it)
# will-change:transform on mini-player is actually good, keep it

# 7. Remove opacity transition from nav-item
css = css.replace('transition:color .2s;', '')

# 8. Add image-rendering optimization
css = css.replace(
    'img {\n    content-visibility: auto;\n    decoding: async;\n}',
    'img {\n    content-visibility: auto;\n    decoding: async;\n    image-rendering: auto;\n}'
)

open('public/style.css', 'w', encoding='utf-8').write(css)
print('CSS done, lines:', css.count('\n'))

# Verify
import re as re2
remaining_trans = re2.findall(r'transition:[^;]+', css)
print('Remaining transitions:', len(remaining_trans))
for t in remaining_trans:
    print(' -', t[:60])
