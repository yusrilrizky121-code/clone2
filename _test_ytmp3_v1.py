import urllib.request, json

video_id = 'dQw4w9WgXcQ'

url1 = 'https://id.ytmp3.mobi/v1/convert?id=' + video_id + '&format=mp3'
req = urllib.request.Request(url1, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://id.ytmp3.mobi/'})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        print('raw:', raw[:300])
        try:
            data = json.loads(raw)
            print('json:', json.dumps(data)[:300])
        except:
            print('not json')
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read()[:200])
except Exception as e:
    print('err:', e)
