import urllib.request, json

# Test Piped API instances
PIPED = [
    'https://pipedapi.kavin.rocks',
    'https://pipedapi.adminforge.de',
    'https://piped-api.garudalinux.org',
    'https://api.piped.yt',
    'https://pipedapi.tokhmi.xyz',
]

video_id = 'dQw4w9WgXcQ'
for base in PIPED:
    try:
        url = base + '/streams/' + video_id
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        streams = data.get('audioStreams', [])
        title = data.get('title', '')[:40]
        print('OK ' + base + ': ' + str(len(streams)) + ' audio streams, title=' + title)
        if streams:
            print('  URL prefix: ' + streams[0].get('url','')[:80])
        break
    except Exception as e:
        print('FAIL ' + base + ': ' + str(e)[:80])
