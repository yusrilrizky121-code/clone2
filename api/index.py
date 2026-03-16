import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from ytmusicapi import YTMusic
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()

def format_results(search_results):
    cleaned = []
    for item in search_results:
        if 'videoId' in item:
            cleaned.append({
                "videoId": item['videoId'],
                "title": item.get('title', 'Unknown Title'),
                "artist": item.get('artists', [{'name': 'Unknown Artist'}])[0]['name'] if 'artists' in item else 'Unknown Artist',
                "thumbnail": item['thumbnails'][-1]['url'] if 'thumbnails' in item else ''
            })
    return cleaned

@app.get("/api/search")
def search_music(query: str):
    try:
        results = ytmusic.search(query, filter="songs", limit=12)
        return {"status": "success", "data": format_results(results)}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/lyrics")
def get_lyrics(video_id: str):
    try:
        watch = ytmusic.get_watch_playlist(videoId=video_id)
        lyrics_id = watch.get("lyrics")
        if not lyrics_id:
            return {"status": "error", "message": "Lirik tidak ditemukan"}
        lyrics = ytmusic.get_lyrics(lyrics_id)
        return {"status": "success", "data": lyrics}
    except Exception as e:
        return {"status": "error", "message": str(e)}

handler = Mangum(app)
