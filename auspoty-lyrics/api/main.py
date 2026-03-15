from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from mangum import Mangum

app = FastAPI(title="SANN404 FORUM Music API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

yt = YTMusic()

@app.get("/api/search")
async def search_music(query: str):
    try:
        results = yt.search(query, filter="songs")
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts")
async def get_charts():
    try:
        results = yt.get_charts()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lyrics")
async def get_lyrics(video_id: str):
    try:
        watch_playlist = yt.get_watch_playlist(videoId=video_id)
        lyrics_id = watch_playlist.get("lyrics")
        if not lyrics_id:
            return {"status": "error", "message": "Lirik tidak ditemukan"}
        lyrics = yt.get_lyrics(lyrics_id)
        return {"status": "success", "data": lyrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/album")
async def get_album_info(browse_id: str):
    try:
        results = yt.get_album(browse_id)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Vercel serverless handler
handler = Mangum(app)
