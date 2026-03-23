import urllib.request, json

# Get the actual error message from Vercel
url = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/download?video_id=dQw4w9WgXcQ'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=65) as r:
        data = json.loads(r.read())
        print('SUCCESS:', json.dumps(data)[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print('HTTP', e.code, ':', body[:500])
except Exception as e:
    print('Error:', e)
