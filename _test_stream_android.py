#!/usr/bin/env python3
"""Test apakah stream URL bisa diakses langsung (simulasi Android MediaPlayer)"""
import urllib.request, json, time
import os; os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

print("Step 1: Fetch stream URL...")
api = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/stream?videoId=dQw4w9WgXcQ'
try:
    req = urllib.request.urlopen(api, timeout=30)
    data = json.loads(req.read())
    stream_url = data.get('url','')
    print('Got URL:', stream_url[:80])
    print('MimeType:', data.get('mimeType'))
    
    print("\nStep 2: Try to access stream URL directly (no extra headers)...")
    # Android MediaPlayer akses URL tanpa header tambahan
    req2 = urllib.request.Request(stream_url)
    # Jangan tambah header apapun - simulasi MediaPlayer
    try:
        resp = urllib.request.urlopen(req2, timeout=10)
        print('HTTP Status:', resp.status)
        # Baca sedikit data
        chunk = resp.read(1024)
        print('Got', len(chunk), 'bytes - URL ACCESSIBLE!')
    except urllib.error.HTTPError as e:
        print('HTTP Error:', e.code, e.reason)
        print('This URL requires special headers - MediaPlayer will fail!')
    except Exception as e:
        print('Error:', e)
        
    print("\nStep 3: Try with referer header...")
    req3 = urllib.request.Request(stream_url)
    req3.add_header('Referer', 'https://www.youtube.com/')
    req3.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36')
    try:
        resp3 = urllib.request.urlopen(req3, timeout=10)
        print('HTTP Status with headers:', resp3.status)
        chunk3 = resp3.read(1024)
        print('Got', len(chunk3), 'bytes with headers!')
    except Exception as e:
        print('Error with headers:', e)
        
except Exception as e:
    print('API Error:', e)
