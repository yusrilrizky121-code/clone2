#!/usr/bin/env python3
import urllib.request, json, time
os_import = __import__('os')
os_import.chdir(r'C:\Users\Admin\Downloads\Auspoty')

print("Testing /api/stream endpoint...")
url = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/stream?videoId=dQw4w9WgXcQ'
try:
    req = urllib.request.urlopen(url, timeout=30)
    data = json.loads(req.read())
    print('status:', data.get('status'))
    print('url prefix:', data.get('url','')[:100])
    print('title:', data.get('title','')[:60])
    print('duration:', data.get('duration'))
    print('mimeType:', data.get('mimeType'))
    print('\n✓ /api/stream WORKS!')
except Exception as e:
    print('ERROR:', e)
    print('✗ /api/stream still broken')
