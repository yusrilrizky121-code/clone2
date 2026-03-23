from http.server import BaseHTTPRequestHandler
import json, urllib.parse, urllib.request, random, time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
    'Referer': 'https://id.ytmp3.mobi/',
    'Origin': 'https://id.ytmp3.mobi',
}

def _get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

def get_download_url(video_id):
    # Step 1: init — get convertURL with sig
    rnd = random.random()
    init = _get(f'https://a.ymcdn.org/api/v1/init?p=y&23=1llum1n471&_={rnd}')
    if init.get('error', 0) != 0:
        raise Exception('init error: ' + str(init))
    convert_url = init['convertURL']

    # Step 2: convert — submit video_id
    rnd2 = random.random()
    conv = _get(f'{convert_url}&v={video_id}&f=mp3&_={rnd2}')
    if conv.get('error', 0) != 0:
        raise Exception('convert error: ' + str(conv))

    progress_url = conv['progressURL']
    download_url = conv['downloadURL']
    title = conv.get('title', video_id)

    # Step 3: poll progress until ready (progress == 3)
    for _ in range(25):
        time.sleep(1.2)
        rnd3 = random.random()
        prog = _get(f'{progress_url}&_={rnd3}')
        if prog.get('error', 0) != 0:
            raise Exception('progress error: ' + str(prog))
        if prog.get('progress', 0) >= 3:
            final_url = prog.get('downloadURL') or download_url
            return {
                'url': final_url,
                'title': prog.get('title') or title,
                'ext': 'mp3',
                'headers': dict(HEADERS),
            }

    raise Exception('Timeout waiting for conversion')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get('video_id', params.get('videoId', ['']))[0].strip()
        if not video_id:
            self._json(400, {'status': 'error', 'message': 'video_id required'})
            return
        try:
            result = get_download_url(video_id)
            self._json(200, {'status': 'success', **result})
        except Exception as e:
            self._json(500, {'status': 'error', 'message': str(e)[:300]})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
