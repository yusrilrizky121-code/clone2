content = open('auspoty-flutter/lib/main.dart', encoding='utf-8').read()

old = "                cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,\n                userAgent:"
new = """                cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,
                geolocationEnabled: false,
                safeBrowsingEnabled: false,
                disableDefaultErrorPage: true,
                verticalScrollBarEnabled: false,
                horizontalScrollBarEnabled: false,
                overScrollMode: OverScrollMode.NEVER,
                userAgent:"""

content = content.replace(old, new)
open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8').write(content)
print('Done')
print('overScrollMode in file:', 'overScrollMode' in content)
