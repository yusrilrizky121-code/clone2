with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: useHybridComposition true -> false (faster on most Android)
content = content.replace('useHybridComposition: true,', 'useHybridComposition: false,')

# Fix 2: LOAD_NO_CACHE -> LOAD_CACHE_ELSE_NETWORK (cache CSS/JS, faster reload)
content = content.replace(
    '                // LOAD_NO_CACHE: selalu ambil fresh dari server, tidak pakai cache lama\n                cacheMode: CacheMode.LOAD_NO_CACHE,',
    '                // Cache CSS/JS untuk load lebih cepat\n                cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,'
)

# Fix 3: Add hardware acceleration + overscroll settings after userAgent line
old_ua = "                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',"
new_ua = """                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                overScrollMode: OverScrollMode.NEVER,
                hardwareAcceleration: true,"""

content = content.replace(old_ua, new_ua)

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
c2 = open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8').read()
print("useHybridComposition: false =", 'useHybridComposition: false' in c2)
print("LOAD_CACHE_ELSE_NETWORK =", 'LOAD_CACHE_ELSE_NETWORK' in c2)
print("hardwareAcceleration =", 'hardwareAcceleration' in c2)
print("overScrollMode =", 'overScrollMode' in c2)
