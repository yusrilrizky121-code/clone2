content = open('public/script.js', encoding='utf-8').read()
lines = content.split('\n')
for i, l in enumerate(lines):
    if 'playStream' in l or '_playNativeStream' in l or 'flutter_inappwebview' in l:
        print(f'{i+1}: {l[:120]}')
