import urllib.request, json

video_id = 'dQw4w9WgXcQ'
instances = [
    'https://yewtu.be',
    'https://invidious.nerdvpn.de',
    'https://inv.nadeko.net',
]

for base in instances:
    try:
        url = base + '/api/v1/videos/' + video_id + '?fields=title,adaptiveFormats'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        audio = [f for f in data.get('adaptiveFormats', []) if f.get('type','').startswith('audio/') and f.get('url')]
        print('OK ' + base + ': ' + str(len(audio)) + ' audio, title=' + data.get('title','')[:40])
        if audio:
            print('  bitrate=' + str(audio[0].get('bitrate',0)) + ' url=' + audio[0]['url'][:60])
    except Exception as e:
        print('FAIL ' + base + ': ' + str(e)[:100])
