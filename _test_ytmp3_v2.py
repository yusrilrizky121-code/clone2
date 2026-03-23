import urllib.request, urllib.parse, json, http.cookiejar

video_id = 'dQw4w9WgXcQ'

# Need to get a session first by visiting the main page
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://id.ytmp3.mobi/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'id-ID,id;q=0.9',
    'Origin': 'https://id.ytmp3.mobi',
}

# Visit main page first to get cookies
req0 = urllib.request.Request('https://id.ytmp3.mobi/', headers=headers)
try:
    with opener.open(req0, timeout=10) as r:
        print('main page status:', r.status)
except Exception as e:
    print('main page err:', e)

# Now try convert API
url1 = 'https://id.ytmp3.mobi/v1/convert?id=' + video_id + '&format=mp3'
req1 = urllib.request.Request(url1, headers=headers)
try:
    with opener.open(req1, timeout=15) as r:
        raw = r.read()
        print('convert raw:', raw[:400])
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read()[:200])
except Exception as e:
    print('err:', e)
