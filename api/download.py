from http.server import BaseHTTPRequestHandler
import json, urllib.request, urllib.error, urllib.parse, re

# Use pytubefix to extract direct audio stream URL from YouTube
# Flutter then downloads directly from YouTube CDN (no server-side download)

def get_audio_stream_url(video_id):
    """Extract direct audio stream URL using pytubefix."""
    try:
        from pytubefix import YouTube
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        title = yt.title or video_id
        # Get best audio stream (webm/mp4 audio only)
        stream = yt.streams.filter(only_audio=True).order_by('abr').last()
        if not stream:
            stream = yt.streams.filter(progressive=False).order_by('abr').last()
        if not stream:
            raise Exception('No audio stream found')
        url = stream.url
        ext = 'mp4'  # YouTube audio streams are usually mp4/webm
        if 'mime_type' in dir(stream):
            mt = stream.mime_type or ''
            if 'webm' in mt:
                ext = 'webm'
        return url, title, ext
    except ImportError:
        pass

    # Fallback: use yt-dlp if pytubefix not available
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            url = info.get('url') or info.get('formats', [{}])[-1].get('url', '')
            title = info.get('title', video_id)
            ext = info.get('ext', 'mp4')
            if not url:
                raise Exception('No URL in yt-dlp info')
            return url, title, ext
    except Exception as e:
        raise Exception(f'yt-dlp failed: {e}')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get('video_id', params.get('videoId', ['']))[0].strip()
        if not video_id:
            self._json(400, {'status': 'error', 'message': 'video_id required'})
            return
        try:
            url, title, ext = get_audio_stream_url(video_id)
            self._json(200, {
                'status': 'success',
                'url': url,
                'title': title,
                'ext': ext,
            })
        except Exception as e:
            self._json(500, {'status': 'error', 'message': str(e)[:300]})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            video_id = body.get('videoId', body.get('video_id', '')).strip()
            if not video_id:
                self._json(400, {'status': 'error', 'message': 'videoId required'})
                return
            url, title, ext = get_audio_stream_url(video_id)
            self._json(200, {'status': 'success', 'url': url, 'title': title, 'ext': ext})
        except Exception as e:
            self._json(500, {'status': 'error', 'message': str(e)[:300]})

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
