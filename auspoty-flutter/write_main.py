content = '''import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:just_audio/just_audio.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';

final _player = AudioPlayer();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  await Permission.notification.request();
  runApp(const AuspotyApp());
}

class AuspotyApp extends StatelessWidget {
  const AuspotyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Auspoty',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
      ),
      home: const WebViewScreen(),
    );
  }
}

class WebViewScreen extends StatefulWidget {
  const WebViewScreen({super.key});
  @override
  State<WebViewScreen> createState() => _WebViewScreenState();
}

class _WebViewScreenState extends State<WebViewScreen> {
  InAppWebViewController? _wvc;
  DateTime? _lastBack;

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (_wvc != null && await _wvc!.canGoBack()) {
          _wvc!.goBack();
          return;
        }
        final now = DateTime.now();
        if (_lastBack == null ||
            now.difference(_lastBack!) > const Duration(seconds: 2)) {
          _lastBack = now;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Tekan sekali lagi untuk keluar'),
                duration: Duration(seconds: 2),
              ),
            );
          }
        } else {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        body: SafeArea(
          child: InAppWebView(
            initialFile: 'assets/web/index.html',
            initialSettings: InAppWebViewSettings(
              javaScriptEnabled: true,
              mediaPlaybackRequiresUserGesture: false,
              allowsInlineMediaPlayback: true,
              useHybridComposition: true,
              domStorageEnabled: true,
              databaseEnabled: true,
              cacheEnabled: true,
              allowFileAccessFromFileURLs: true,
              allowUniversalAccessFromFileURLs: true,
              mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,
              transparentBackground: true,
              javaScriptCanOpenWindowsAutomatically: true,
            ),
            onWebViewCreated: (c) {
              _wvc = c;
              _registerHandlers(c);
            },
            onPermissionRequest: (_, req) async => PermissionResponse(
              resources: req.resources,
              action: PermissionResponseAction.GRANT,
            ),
            shouldOverrideUrlLoading: (_, action) async {
              final url = action.request.url.toString();
              if (url.startsWith('http') &&
                  !url.contains('localhost') &&
                  !url.contains('file://')) {
                if (url.contains('accounts.google.com') ||
                    url.contains('ytmp3') ||
                    url.contains('wa.me')) {
                  await launchUrl(Uri.parse(url),
                      mode: LaunchMode.externalApplication);
                  return NavigationActionPolicy.CANCEL;
                }
              }
              return NavigationActionPolicy.ALLOW;
            },
          ),
        ),
      ),
    );
  }

  void _registerHandlers(InAppWebViewController c) {
    c.addJavaScriptHandler(
      handlerName: 'playStream',
      callback: (args) async {
        if (args.isEmpty) return;
        final url = args[0] as String;
        try {
          await _player.stop();
          await _player.setAudioSource(AudioSource.uri(Uri.parse(url)));
          await _player.play();
        } catch (e) {
          debugPrint('playStream error: $e');
        }
      },
    );
    c.addJavaScriptHandler(
      handlerName: 'pauseAudio',
      callback: (_) async => await _player.pause(),
    );
    c.addJavaScriptHandler(
      handlerName: 'resumeAudio',
      callback: (_) async => await _player.play(),
    );
    c.addJavaScriptHandler(
      handlerName: 'seekAudio',
      callback: (args) async {
        if (args.isNotEmpty) {
          final secs = (args[0] as num).toDouble();
          await _player.seek(Duration(milliseconds: (secs * 1000).round()));
        }
      },
    );
    c.addJavaScriptHandler(
      handlerName: 'setBgMode',
      callback: (_) {},
    );
    c.addJavaScriptHandler(
      handlerName: 'openUrl',
      callback: (args) async {
        if (args.isNotEmpty) {
          await launchUrl(Uri.parse(args[0] as String),
              mode: LaunchMode.externalApplication);
        }
      },
    );
  }
}
'''

with open('lib/main.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE - main.dart written")

# Verify
with open('lib/main.dart', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:10], 1):
        print(f"{i}: {line}", end='')
