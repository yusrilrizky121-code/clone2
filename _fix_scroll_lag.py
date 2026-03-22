js = open('public/script.js', encoding='utf-8').read()

# 1. Add scroll-aware interval pausing at the top of DOMContentLoaded
# When user is scrolling, pause all non-critical intervals
scroll_patch = """
// ============================================================
// SCROLL PERFORMANCE — pause JS work during scroll
// ============================================================
var _isScrolling = false;
var _scrollTimer = null;
function _onScrollStart() {
    _isScrolling = true;
    clearTimeout(_scrollTimer);
    _scrollTimer = setTimeout(function() { _isScrolling = false; }, 150);
}
document.addEventListener('scroll', _onScrollStart, { passive: true });
document.addEventListener('touchmove', _onScrollStart, { passive: true });
"""

# 2. Guard progress interval with scroll check
old_prog = """        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const now = Date.now();
        if (now - _lastProgressUpdate < 900) return; // throttle
        _lastProgressUpdate = now;
        const _modal = document.getElementById('playerModal');
        const _mini = document.getElementById('miniPlayer');
        const modalVis = _modal && _modal.style.display !== 'none' && _modal.style.display !== '';
        const miniVis = _mini && _mini.style.display !== 'none' && _mini.style.display !== '';
        if (!modalVis && !miniVis) return;"""
new_prog = """        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        if (_isScrolling) return; // pause during scroll
        const now = Date.now();
        if (now - _lastProgressUpdate < 900) return; // throttle
        _lastProgressUpdate = now;
        const _modal = document.getElementById('playerModal');
        const _mini = document.getElementById('miniPlayer');
        const modalVis = _modal && _modal.style.display !== 'none' && _modal.style.display !== '';
        const miniVis = _mini && _mini.style.display !== 'none' && _mini.style.display !== '';
        if (!modalVis && !miniVis) return;"""
js = js.replace(old_prog, new_prog)

# 3. Guard lyrics scroll interval with scroll check
old_lyrics = """    lyricsScrollInterval = setInterval(function() { // 500ms
        var cur = 0, dur = 0;"""
new_lyrics = """    lyricsScrollInterval = setInterval(function() { // 500ms
        if (_isScrolling) return; // pause during scroll
        var cur = 0, dur = 0;"""
js = js.replace(old_lyrics, new_lyrics)

# 4. Replace lyrics scroll with RAF-based smooth scroll (no layout thrashing)
old_lyric_scroll = """        var activeLine = document.getElementById('lyric-line-' + idx);
        if (activeLine) {
            var lb = document.getElementById('lyricsBody');
            if (lb) lb.scrollTop = activeLine.offsetTop - (lb.clientHeight / 2) + (activeLine.offsetHeight / 2);
        }"""
new_lyric_scroll = """        var activeLine = document.getElementById('lyric-line-' + idx);
        if (activeLine) {
            var lb = document.getElementById('lyricsBody');
            if (lb) {
                var target = activeLine.offsetTop - (lb.clientHeight / 2) + (activeLine.offsetHeight / 2);
                // Smooth scroll without triggering layout thrash
                requestAnimationFrame(function() { lb.scrollTop = target; });
            }
        }"""
js = js.replace(old_lyric_scroll, new_lyric_scroll)

# 5. Add scroll patch before DOMContentLoaded
old_init = "document.addEventListener('DOMContentLoaded', function() {"
js = js.replace(old_init, scroll_patch + "\n" + old_init, 1)

open('public/script.js', 'w', encoding='utf-8').write(js)
print('Done, lines:', js.count('\n'))
print('_isScrolling guard in progress:', '_isScrolling' in js)
