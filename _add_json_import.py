with open('auspoty-flutter/lib/main.dart', 'r', encoding='utf-8') as f:
    content = f.read()

if "dart:convert" not in content:
    content = content.replace("import 'dart:async';", "import 'dart:async';\nimport 'dart:convert';", 1)
    with open('auspoty-flutter/lib/main.dart', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added dart:convert import")
else:
    print("dart:convert already present")
