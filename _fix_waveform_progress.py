with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = "            if (mf) mf.style.width = pct + '%';\n            const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);"
new = "            if (mf) mf.style.width = pct + '%';\n            _updateWaveform(pct);\n            const ct = document.getElementById('currentTime'); if (ct) ct.innerText = formatTime(cur);"

if old in content:
    content = content.replace(old, new, 1)
    print("Patched startProgressBar with _updateWaveform")
else:
    print("ERROR: pattern not found")
    # Try to find nearby
    idx = content.find("mf.style.width = pct + '%'")
    print("Found mf.style.width at:", idx)
    print(repr(content[idx-5:idx+200]))

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
