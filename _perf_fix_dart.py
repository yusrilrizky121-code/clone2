with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: useHybridComposition false (faster rendering, less memory)
content = content.replace('useHybridComposition: true,', 'useHybridComposition: false,')

# Fix 2: Use LOAD_CACHE_ELSE_NETWORK (cache CSS/JS, don't re-download every time)
content = content.replace('cacheMode: CacheMode.LOAD_DEFAULT,', 'cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,')

# Fix 3: Disable zoom controls (already false, just ensure)
# Fix 4: Add hardware acceleration hint via rendering mode
# Fix 5: Reduce overscroll mode
old_settings_end = '                userAgent: \'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36\','
new_settings_end = '''                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                overScrollMode: OverScrollMode.NEVER,
                scrollBarStyle: ScrollBarStyle.SCROLLBARS_INSIDE_OVERLAY,
                disableHorizontalScroll: false,
                disableVerticalScroll: false,
                hardwareAcceleration: true,'''

if old_settings_end in content:
    content = content.replace(old_settings_end, new_settings_end)
    print("Added hardware acceleration + overscroll settings")
else:
    print("WARNING: userAgent line not found exactly, skipping extra settings")

with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print("Dart fixed")
print("useHybridComposition: false =", 'useHybridComposition: false' in content)
print("LOAD_CACHE_ELSE_NETWORK =", 'LOAD_CACHE_ELSE_NETWORK' in content)
