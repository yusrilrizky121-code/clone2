import urllib.request, urllib.parse, json

# Test cobalt API v7
video_id = 'dQw4w9WgXcQ'
yt_url = 'https://www.youtube.com/watch?v=' + video_id

# cobalt.tools public API
endpoints = [
    'https://api.cobalt.tools',
    'https://cobalt.api.timelessnesses.me',
]

for ep in endpoints:
    try:
        payload = json.dumps({
            'url': yt_url,
            'downloadMode': 'audio',
            'audioFormat': 'mp3',
        }).encode()
        req = urllib.request.Request(
            ep,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0',
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        print('OK ' + ep + ': status=' + data.get('status','') + ' url=' + str(data.get('url',''))[:80])
    except Exception as e:
        print('FAIL ' + ep + ': ' + str(e)[:100])
