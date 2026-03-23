import urllib.request, json

# Test stream endpoint - ini yang dipakai untuk play lagu
url = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/stream?videoId=dQw4w9WgXcQ'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=65) as r:
        data = json.loads(r.read())
        print('SUCCESS:', json.dumps(data)[:300])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print('HTTP', e.code, ':', body[:300])
except Exception as e:
    print('Error:', e)

# Also test search
url2 = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/search?query=rick+astley'
req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req2, timeout=30) as r:
        data2 = json.loads(r.read())
        print('SEARCH:', data2.get('status'), 'count:', len(data2.get('data',[])))
except Exception as e:
    print('Search error:', e)
