with open('public/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Add performance CSS at the top after * reset
perf_css = '''
/* ===== PERFORMANCE: GPU acceleration for scroll ===== */
.horizontal-scroll,
.lyrics-body,
.lib-list,
.vertical-list,
.view-section {
    -webkit-overflow-scrolling: touch;
    transform: translateZ(0);
}
img {
    content-visibility: auto;
    decoding: async;
}
/* Disable expensive transitions on low-end */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; }
}
'''

# Insert after the * reset block
insert_after = '-webkit-tap-highlight-color:transparent; }\n'
if insert_after in content:
    content = content.replace(insert_after, insert_after + perf_css, 1)
    print("Added performance CSS")
else:
    # fallback: prepend after :root block
    idx = content.find('body {')
    content = content[:idx] + perf_css + content[idx:]
    print("Added performance CSS (fallback)")

# Also fix background-attachment: fixed (causes repaint on every scroll frame)
content = content.replace('background-attachment: fixed;', '/* background-attachment removed for perf */')

with open('public/style.css', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
