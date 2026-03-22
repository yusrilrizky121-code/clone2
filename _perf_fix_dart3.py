with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

# Show exact bytes around cacheMode
idx = content.find('cacheMode')
print("cacheMode found at:", idx)
if idx != -1:
    print(repr(content[idx-100:idx+200]))
