import re

with open('public/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace _setArtRotation(true) with _setArtPlaying(true)
content = content.replace('_setArtRotation(true);', '_setArtPlaying(true);')
content = content.replace('_setArtRotation(false);', '_setArtPlaying(false);')

# Fix 2: Add waveform + art functions before the LAST DOMContentLoaded block
# Find the last DOMContentLoaded
last_idx = content.rfind("document.addEventListener('DOMContentLoaded'")
if last_idx == -1:
    print("ERROR: DOMContentLoaded not found")
    exit(1)

namida_code = '''
// ============================================================
// NAMIDA UI — Album art scale & waveform seekbar
// ============================================================
function _setArtPlaying(playing) {
    var w = document.getElementById('playerArtWrapper');
    if (!w) return;
    if (playing) w.classList.add('playing');
    else w.classList.remove('playing');
}

var WAVEFORM_BARS = 48;
var _waveHeights = [];
function _initWaveform() {
    var c = document.getElementById('waveformContainer');
    if (!c) return;
    c.querySelectorAll('.waveform-bar').forEach(function(b) { b.remove(); });
    _waveHeights = [];
    var input = c.querySelector('.progress-bar');
    for (var i = 0; i < WAVEFORM_BARS; i++) {
        var h = 20 + Math.abs(Math.sin(i * 0.7 + 1.3) * 55) + Math.abs(Math.sin(i * 1.9) * 20);
        _waveHeights.push(Math.round(h));
        var bar = document.createElement('div');
        bar.className = 'waveform-bar';
        bar.style.height = h + '%';
        c.insertBefore(bar, input);
    }
}
function _updateWaveform(pct) {
    var c = document.getElementById('waveformContainer');
    if (!c) return;
    var bars = c.querySelectorAll('.waveform-bar');
    var activeIdx = Math.floor(pct / 100 * WAVEFORM_BARS);
    bars.forEach(function(bar, i) {
        bar.classList.remove('played', 'active');
        if (i < activeIdx) bar.classList.add('played');
        else if (i === activeIdx) bar.classList.add('active');
    });
}

'''

content = content[:last_idx] + namida_code + content[last_idx:]

with open('public/script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Fixed _setArtRotation and added waveform functions.")

# Verify
with open('public/script.js', 'r', encoding='utf-8') as f:
    c2 = f.read()
print("_setArtRotation remaining:", c2.count('_setArtRotation'))
print("_setArtPlaying count:", c2.count('_setArtPlaying'))
print("_initWaveform count:", c2.count('_initWaveform'))
print("_updateWaveform count:", c2.count('_updateWaveform'))
