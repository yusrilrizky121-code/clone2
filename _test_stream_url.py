"""
Test apakah URL dari /api/stream bisa diakses dengan headers Android
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

import urllib.request
import urllib.parse
import json

API_BASE = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app"
TEST_VIDEO_ID = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up (test)

print(f"=== Testing /api/stream for videoId={TEST_VIDEO_ID} ===\n")

# Step 1: Get stream URL from API
try:
    url = f"{API_BASE}/api/stream?videoId={TEST_VIDEO_ID}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
    data = json.loads(body)
    print(f"API Status: {data.get('status')}")
    print(f"Stream URL: {data.get('url', '')[:100]}...")
    print(f"Title: {data.get('title')}")
    print(f"Duration: {data.get('duration')}s")
    print(f"MimeType: {data.get('mimeType')}")
    print(f"Headers from API: {data.get('headers', {})}")
    stream_url = data.get('url', '')
except Exception as e:
    print(f"API Error: {e}")
    stream_url = ''

if not stream_url:
    print("No stream URL, stopping")
    exit(1)

print(f"\n=== Testing stream URL accessibility ===\n")

# Step 2: Test dengan headers Android (seperti yang dipakai MediaPlayer)
headers_android = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": "https://www.youtube.com/",
    "Origin": "https://www.youtube.com",
    "Range": "bytes=0-1023"  # Hanya ambil 1KB untuk test
}

try:
    req2 = urllib.request.Request(stream_url, headers=headers_android)
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        status = resp2.status
        content_type = resp2.headers.get('Content-Type', '')
        content_length = resp2.headers.get('Content-Length', 'unknown')
        data_preview = resp2.read(100)
    print(f"✓ Stream URL accessible!")
    print(f"  HTTP Status: {status}")
    print(f"  Content-Type: {content_type}")
    print(f"  Content-Length: {content_length}")
    print(f"  Data preview (hex): {data_preview[:20].hex()}")
except urllib.error.HTTPError as e:
    print(f"✗ HTTP Error: {e.code} {e.reason}")
    print(f"  Response headers: {dict(e.headers)}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")

# Step 3: Test tanpa headers (seperti MediaPlayer default)
print(f"\n=== Testing WITHOUT headers (default MediaPlayer) ===\n")
try:
    req3 = urllib.request.Request(stream_url)
    req3.add_header("Range", "bytes=0-1023")
    with urllib.request.urlopen(req3, timeout=15) as resp3:
        status3 = resp3.status
        ct3 = resp3.headers.get('Content-Type', '')
    print(f"✓ Accessible without headers! Status: {status3}, CT: {ct3}")
except urllib.error.HTTPError as e:
    print(f"✗ HTTP Error without headers: {e.code} {e.reason}")
except Exception as e:
    print(f"✗ Error without headers: {type(e).__name__}: {e}")
