import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        query = params.get('query', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not query:
            self.wfile.write(json.dumps({"status": "error", "message": "query required", "data": []}).encode())
            return

        try:
            from ytmusicapi import YTMusic
            yt = YTMusic()
            results = yt.search(query, filter="songs", limit=12)
            data = []
            for item in results:
                if 'videoId' in item:
                    data.append({
                        "videoId": item['videoId'],
                        "title": item.get('title', 'Unknown'),
                        "artist": item.get('artists', [{'name': 'Unknown'}])[0]['name'] if item.get('artists') else 'Unknown',
                        "thumbnail": item['thumbnails'][-1]['url'] if item.get('thumbnails') else ''
                    })
            self.wfile.write(json.dumps({"status": "success", "data": data}).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"status": "error", "message": str(e), "data": []}).encode())
