import urllib.request, json

video_id = 'dQw4w9WgXcQ'
yt_url = 'https://www.youtube.com/watch?v=' + video_id

# cobalt v10 API format
payload = json.dumps({
    'url': yt_url,
    'downloadMode': 'audio',
    'audioFormat': 'best',
}).encode()

req = urllib.request.Request(
    'https://api.cobalt.tools',
    data=payload,
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    },
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    print('OK:', json.dumps(data, indent=2)[:300])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print('HTTP Error', e.code, ':', body[:200])
except Exception as e:
    print('Error:', e)
