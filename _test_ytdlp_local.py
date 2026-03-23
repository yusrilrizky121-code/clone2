import yt_dlp, json

video_id = 'dQw4w9WgXcQ'

# Test berbagai kombinasi client
clients_to_test = [
    ['tv_embedded'],
    ['android_music'],
    ['ios'],
    ['mweb'],
    ['android_creator'],
]

for clients in clients_to_test:
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'socket_timeout': 10,
            'extractor_args': {
                'youtube': {
                    'player_client': clients,
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + video_id, download=False)
        
        formats = info.get('formats', [])
        audio = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') not in ('none', None) and f.get('url')]
        print('OK clients=' + str(clients) + ' audio_formats=' + str(len(audio)) + ' title=' + info.get('title','')[:30])
        if audio:
            print('  URL: ' + audio[0]['url'][:80])
        break
    except Exception as e:
        print('FAIL clients=' + str(clients) + ': ' + str(e)[:100])
