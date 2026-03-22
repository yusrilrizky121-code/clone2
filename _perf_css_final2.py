import re

css = open('public/style.css', encoding='utf-8').read()

# 1. Fix contain on view-section - 'contain:layout style' blocks scroll optimization
# Change to just 'contain:style' which is safer
css = css.replace('contain:layout style;', 'contain:style;')

# 2. Add passive scroll optimization hint via CSS
# Add scroll-behavior: auto (not smooth - smooth scroll is expensive)
# Add touch-action: manipulation to interactive elements to skip 300ms tap delay
touch_action = """
/* ===== TOUCH PERFORMANCE ===== */
a, button, .nav-item, .v-item, .lib-item, .h-card, .pill,
.category-card, .ctrl-btn, .ctrl-play, .settings-item,
.picker-option, .mini-player, .back-btn, .player-header-btn {
    touch-action: manipulation;
}
"""
css = css.rstrip() + '\n' + touch_action

# 3. Remove the expensive player art wrapper transition box-shadow part
css = re.sub(
    r'transition:transform \.3s cubic-bezier\(\.34,1\.56,\.64,1\), box-s[^;]+;',
    'transition:transform .3s ease;',
    css
)

# 4. Simplify player art playing state - remove box-shadow change (triggers repaint)
css = re.sub(
    r'\.player-art-wrapper\.playing \{[^}]+\}',
    '.player-art-wrapper.playing { transform:scale(1.04); }',
    css
)

# 5. Remove animation from slideUpMini (mini player) - replace with simpler
# Actually keep it but make it shorter
css = css.replace(
    '@keyframes slideUpMini { from{transform:translateY(120%);opacity:0} to{transform:translateY(0);opacity:1} }',
    '@keyframes slideUpMini { from{transform:translateY(100%)} to{transform:translateY(0)} }'
)

# 6. Remove opacity from slideUp animation (opacity change triggers composite)
css = css.replace(
    '@keyframes slideUpMini { from{transform:translateY(100%)} to{transform:translateY(0)} }',
    '@keyframes slideUpMini { from{transform:translateY(100%)} to{transform:translateY(0)} }'
)

open('public/style.css', 'w', encoding='utf-8').write(css)
print('CSS2 done, lines:', css.count('\n'))
