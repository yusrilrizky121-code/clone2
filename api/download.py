from http.server import BaseHTTPRequestHandler
import json, urllib.request, urllib.error, time, random

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
    'Referer': 'https://id.ytmp3.mobi/v1/',
    'Origin': 'https://id.ytmp3.mobi',
}

def ymcdn_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())

def get_mp3_url(video_id):
    rnd = random.random()
    init = ymcdn_get('https://a.ymcdn.org/api/v1/init?p=y&23=1llum1n471&_=' + str(rnd))
    if init.get('error', 0) > 0:
        raise Exception('init error: ' + str(init.get('error')))
    convert_url = init['convertURL']
    conv = ymcdn_get(convert_url + '&v=' + video_id + '&f=mp3&_=' + str(random.random()))
    if conv.get('error', 0) > 0:
        raise Exception('convert error: ' + str(conv.get('error')))
    title = conv.get('title', video_id)
    progress_url = conv['progressURL']
    download_url = conv['downloadURL']
    # Poll up to 25 iterations (25 seconds max — stay under Vercel 30s limit)
    for _ in range(25):
        time.sleep(1)
        prog = ymcdn_get(progress_url + '&_=' + str(random.random()))
        if prog.get('error', 0) > 0:
            raise Exception('progress error: ' + str(prog.get('error')))
        if prog.get('progress', 0) >= 3:
            return prog.get('downloadURL') or download_url, title
    raise Exception('timeout waiting for conversion')

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get('video_id', params.get('videoId', ['']))[0].strip()
        if not video_id:
            self._json(400, {'status': 'error', 'message': 'video_id required'})
            return
        try:
            dl_url, title = get_mp3_url(video_id)
            self._json(200, {'status': 'success', 'url': dl_url, 'title': title, 'ext': 'mp3'})
        except Exception as e:
            self._json(500, {'status': 'error', 'message': str(e)[:200]})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            video_id = body.get('videoId', body.get('video_id', '')).strip()
            if not video_id:
                self._json(400, {'status': 'error', 'message': 'videoId required'})
                return
            dl_url, title = get_mp3_url(video_id)
            self._json(200, {'status': 'success', 'url': dl_url, 'title': title, 'ext': 'mp3'})
        except Exception as e:
            self._json(500, {'status': 'error', 'message': str(e)[:200]})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
