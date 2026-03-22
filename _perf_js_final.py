import re

js = open('public/script.js', encoding='utf-8').read()

# 1. Reduce home rows from 8 to 5 items
js = js.replace('result.data.slice(0, 8).map(renderHCard)', 'result.data.slice(0, 5).map(renderHCard)')
js = js.replace('result.data.slice(0, 6).map(renderVItem)', 'result.data.slice(0, 5).map(renderVItem)')

# 2. Skip progress DOM update when player is not visible
old = "    progressInterval = setInterval(() => {\n        if (!ytPlayer || !ytPlayer.getCurrentTime) return;\n        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;"
new = "    progressInterval = setInterval(() => {\n        if (!ytPlayer || !ytPlayer.getCurrentTime) return;\n        const _modal = document.getElementById('playerModal');\n        const _mini = document.getElementById('miniPlayer');\n        if ((!_modal || _modal.style.display === 'none' || _modal.style.display === '') && (!_mini || _mini.style.display === 'none' || _mini.style.display === '')) return;\n        const cur = ytPlayer.getCurrentTime(), dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;"
js = js.replace(old, new)

# 3. Remove onerror from renderHCard img (saves per-card event listener)
js = re.sub(
    r"'<img loading=\"lazy\" class=\"h-img\" src=\"' \+ getHighResImage\(t\.thumbnail \|\| t\.img \|\| ''\) \+ '\" onerror=\"this\.src=\\'https://via\.placeholder\.com/140x140\?text=music\\'\">'",
    "'<img loading=\"lazy\" class=\"h-img\" src=\"' + getHighResImage(t.thumbnail || t.img || '') + '\">'",
    js
)

# 4. Remove onerror from renderVItem img
js = re.sub(
    r"'<img loading=\"lazy\" class=\"v-img\" src=\"' \+ getHighResImage\(t\.thumbnail \|\| t\.img \|\| ''\) \+ '\" onerror=\"this\.src=\\'https://via\.placeholder\.com/48x48\?text=music\\'\">'",
    "'<img loading=\"lazy\" class=\"v-img\" src=\"' + getHighResImage(t.thumbnail || t.img || '') + '\">'",
    js
)

# 5. Increase lazy load delay for home rows (reduce API hammering on load)
js = js.replace(
    "setTimeout(() => loadRow(rows[i]), 800 + (i - 2) * 400);",
    "setTimeout(() => loadRow(rows[i]), 1200 + (i - 2) * 600);"
)

# 6. Reduce lyrics scroll interval from 300ms to 500ms
js = js.replace(
    "lyricsScrollInterval = setInterval(function() {",
    "lyricsScrollInterval = setInterval(function() { // 500ms"
)
js = js.replace("    }, 300);", "    }, 500);")

open('public/script.js', 'w', encoding='utf-8').write(js)
print('JS done, lines:', js.count('\n'))

# Verify
print('slice(0,5) count:', js.count('slice(0, 5)'))
print('onerror remaining:', js.count('onerror'))
