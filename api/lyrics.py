import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import re
import requests
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def parse_lrc(lrc_text):
    """Parse LRC format ke list [{time: float, text: str}]"""
    lines = []
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
    for line in lrc_text.split('\n'):
        m = pattern.match(line.strip())
        if m:
            minutes = int(m.group(1))
            seconds = float(m.group(2))
            text = m.group(3).strip()
            if text:
                lines.append({
                    "time": minutes * 60 + seconds,
                    "text": text
                })
    return lines

def get_synced_lyrics(title, artist, duration=None):
    """Coba ambil synced lyrics dari lrclib.net"""
    try:
        params = {"track_name": title, "artist_name": artist}
        if duration:
            params["duration"] = duration
        r = requests.get(
            "https://lrclib.net/api/get",
            params=params,
            timeout=8,
            headers={"User-Agent": "Auspoty/1.0"}
        )
        if r.status_code == 200:
            data = r.json()
            synced = data.get("syncedLyrics", "")
            plain = data.get("plainLyrics", "")
            if synced:
                return {"type": "synced", "lines": parse_lrc(synced)}
            elif plain:
                lines = [l.strip() for l in plain.split('\n') if l.strip()]
                return {"type": "plain", "lines": [{"time": None, "text": l} for l in lines]}
    except Exception:
        pass
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        video_id = params.get('video_id', [''])[0]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not video_id:
            self.wfile.write(json.dumps({"status": "error", "message": "video_id required"}).encode())
            return

        try:
            from ytmusicapi import YTMusic
            yt = YTMusic()

            # Ambil info lagu dulu untuk dapat title & artist
            watch = yt.get_watch_playlist(videoId=video_id)
            title = ""
            artist = ""
            duration = None
            if watch and watch.get("tracks"):
                track = watch["tracks"][0]
                title = track.get("title", "")
                artists = track.get("artists", [])
                artist = artists[0]["name"] if artists else ""
                duration = track.get("length", None)
                # Convert duration "3:45" ke detik
                if duration and ":" in str(duration):
                    parts = str(duration).split(":")
                    try:
                        duration = int(parts[0]) * 60 + int(parts[1])
                    except:
                        duration = None

            # Coba synced lyrics dari lrclib dulu
            if title:
                synced = get_synced_lyrics(title, artist, duration)
                if synced:
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "data": synced
                    }).encode())
                    return

            # Fallback ke ytmusic lyrics
            lyrics_id = watch.get("lyrics")
            if not lyrics_id:
                self.wfile.write(json.dumps({"status": "error", "message": "Lirik tidak ditemukan"}).encode())
                return
            lyrics_data = yt.get_lyrics(lyrics_id)
            raw = lyrics_data.get("lyrics", "") if lyrics_data else ""
            lines = [l.strip() for l in raw.split('\n') if l.strip()]
            self.wfile.write(json.dumps({
                "status": "success",
                "data": {
                    "type": "plain",
                    "lines": [{"time": None, "text": l} for l in lines]
                }
            }).encode())

        except Exception as e:
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
