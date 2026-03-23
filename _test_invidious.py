import urllib.request, json

INVIDIOUS = [
    'https://inv.nadeko.net',
    'https://invidious.nerdvpn.de',
    'https://invidious.privacydev.net',
    'https://yt.cdaut.de',
    'https://invidious.fdn.fr',
]

video_id = 'dQw4w9WgXcQ'
for base in INVIDIOUS:
    try:
        url = base + '/api/v1/videos/' + video_id + '?fields=title,adaptiveFormats,formatStreams'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        formats = data.get('adaptiveFormats', [])
        audio = [f for f in formats if f.get('type','').startswith('audio/') and f.get('url')]
        title = data.get('title', '')[:40]
        print('OK ' + base + ': ' + str(len(audio)) + ' audio formats, title=' + title)
        if audio:
            print('  URL prefix: ' + audio[0]['url'][:80])
        break
    except Exception as e:
        print('FAIL ' + base + ': ' + str(e))
