from http.server import BaseHTTPRequestHandler
import json, urllib.parse, urllib.request, time, random

YTMP3_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://id.ytmp3.mobi/',
    'Origin': 'https://id.ytmp3.mobi',
    'Accept': '*/*',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
}

def _get_json(url):
    req = urllib.request.Request(url, headers=YTMP3_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))

def get_download_url(video_id):
    """Gunakan id.ytmp3.mobi/v1/ API"""
    rnd = random.random()

    # Step 1: init — dapatkan convertURL
    init = _get_json(f'https://a.ymcdn.org/api/v1/init?p=y&23=1llum1n471&_={rnd}')
    if init.get('error', 0) != 0:
        raise Exception(f'init error: {init}')
    convert_url = init.get('convertURL', '')
    if not convert_url:
        raise Exception('convertURL kosong dari init')

    # Step 2: convert — kirim video_id
    rnd2 = random.random()
    conv = _get_json(f'{convert_url}&v={video_id}&f=mp3&_={rnd2}')
    if conv.get('error', 0) != 0:
        raise Exception(f'convert error: {conv}')

    progress_url = conv.get('progressURL', '')
    download_url = conv.get('downloadURL', '')
    title = conv.get('title', video_id)

    if not progress_url:
        # Langsung ada download URL
        if download_url:
            return {'url': download_url, 'title': title, 'ext': 'mp3'}
        raise Exception('Tidak ada progressURL maupun downloadURL')

    # Step 3: poll progress sampai selesai (progress >= 3)
    for attempt in range(30):
        time.sleep(1.5)
        rnd3 = random.random()
        try:
            prog = _get_json(f'{progress_url}&_={rnd3}')
        except Exception:
            continue
        if prog.get('error', 0) != 0:
            raise Exception(f'progress error: {prog}')
        p = prog.get('progress', 0)
        if p >= 3:
            final_url = prog.get('downloadURL') or download_url
            final_title = prog.get('title') or title
            if not final_url:
                raise Exception('downloadURL kosong setelah konversi')
            return {'url': final_url, 'title': final_title, 'ext': 'mp3'}

    raise Exception('Timeout menunggu konversi (45 detik)')


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

    def log_message(self, format, *args):
        pass
