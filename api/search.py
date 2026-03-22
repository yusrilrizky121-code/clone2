import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get('query', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not query:
            self.wfile.write(json.dumps({"status": "error", "message": "query required", "data": []}).encode())
            return

        try:
            url = "https://music.youtube.com/youtubei/v1/search?prettyPrint=false"
            payload = json.dumps({
                "query": query,
                "params": "EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D",
                "context": {
                    "client": {
                        "clientName": "WEB_REMIX",
                        "clientVersion": "1.20240101.01.00",
                        "hl": "id",
                        "gl": "ID"
                    }
                }
            }).encode()

            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://music.youtube.com",
                "Referer": "https://music.youtube.com/"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode())

            data = []
            tabs = raw.get("contents", {}).get("tabbedSearchResultsRenderer", {}).get("tabs", [])
            for tab in tabs:
                sections = tab.get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [])
                for section in sections:
                    items = section.get("musicShelfRenderer", {}).get("contents", [])
                    for item in items:
                        r2 = item.get("musicResponsiveListItemRenderer", {})
                        overlay = r2.get("overlay", {}).get("musicItemThumbnailOverlayRenderer", {})
                        nav = overlay.get("content", {}).get("musicPlayButtonRenderer", {}).get("playNavigationEndpoint", {})
                        vid = nav.get("watchEndpoint", {}).get("videoId", "")
                        if not vid:
                            continue
                        flex = r2.get("flexColumns", [])
                        title = ""
                        artist = ""
                        if flex:
                            runs = flex[0].get("musicResponsiveListItemFlexColumnRenderer", {}).get("text", {}).get("runs", [])
                            title = runs[0].get("text", "") if runs else ""
                        if len(flex) > 1:
                            runs2 = flex[1].get("musicResponsiveListItemFlexColumnRenderer", {}).get("text", {}).get("runs", [])
                            artist = runs2[0].get("text", "") if runs2 else ""
                        thumbs = r2.get("thumbnail", {}).get("musicThumbnailRenderer", {}).get("thumbnail", {}).get("thumbnails", [])
                        thumb = thumbs[-1].get("url", "") if thumbs else ""
                        data.append({"videoId": vid, "title": title, "artist": artist, "thumbnail": thumb})
                        if len(data) >= 12:
                            break
                    if len(data) >= 12:
                        break
                if len(data) >= 12:
                    break

            if data:
                self.wfile.write(json.dumps({"status": "success", "data": data}).encode())
            else:
                self.wfile.write(json.dumps({"status": "error", "message": "no results", "data": []}).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"status": "error", "message": str(e), "data": []}).encode())
