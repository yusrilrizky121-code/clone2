import yt_dlp

video_id = 'dQw4w9WgXcQ'

# Try with player_skip to avoid JS player (faster + bypass some blocks)
# Also try with different http headers to mimic real Android app
configs = [
    {
        'name': 'tv_embedded + skip_js',
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded'],
                'player_skip': ['webpage', 'configs'],
            }
        },
    },
    {
        'name': 'android_music + skip_js',
        'extractor_args': {
            'youtube': {
                'player_client': ['android_music'],
                'player_skip': ['webpage', 'configs'],
            }
        },
    },
    {
        'name': 'ios',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
            }
        },
    },
]

for cfg in configs:
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'socket_timeout': 10,
            'extractor_args': cfg['extractor_args'],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + video_id, download=False)
        
        formats = info.get('formats', [])
        audio = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') not in ('none', None) and f.get('url')]
        print('OK ' + cfg['name'] + ': ' + str(len(audio)) + ' audio formats')
        if audio:
            print('  URL: ' + audio[0]['url'][:80])
        break
    except Exception as e:
        print('FAIL ' + cfg['name'] + ': ' + str(e)[:120])
