#!/usr/bin/env python3
"""Tulis ulang main.dart dengan fix background audio yang benar."""

content = r'''import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;

const _ch = MethodChannel('com.auspoty.app/music');
final _keepAlive = InAppWebViewKeepAlive();
const _base = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(0xFF0a0a0f),
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  runApp(const AuspotyApp());
}

class AuspotyApp extends StatelessWidget {
  const AuspotyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Auspoty',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFFa78bfa), brightness: Brightness.dark),
          useMaterial3: true,
        ),
        home: const AuspotyWebView(),
      );
}

class AuspotyWebView extends StatefulWidget {
  const AuspotyWebView({super.key});
  @override
  State<AuspotyWebView> createState() => _AuspotyWebViewState();
}

class _AuspotyWebViewState extends State<AuspotyWebView>
    with WidgetsBindingObserver {
  InAppWebViewController? _wvc;
  bool _loading = true;
  DateTime? _lastBack;
  bool _musicPlaying = false;
  Timer? _keepAliveTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ch.setMethodCallHandler(_onNativeCall);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _keepAliveTimer?.cancel();
    super.dispose();
  }

  /// Saat app masuk background, jika musik jalan:
  /// - Inject JS untuk block visibilitychange
  /// - Kirim keepAlive ke service
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _musicPlaying) {
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          try {
            Object.defineProperty(document, 'hidden', {
              get: function(){ return false; }, configurable: true
            });
            Object.defineProperty(document, 'visibilityState', {
              get: function(){ return 'visible'; }, configurable: true
            });
          } catch(e){}
          // Force ytPlayer tetap play jika ada
          try {
            if (window.ytPlayer && typeof window.ytPlayer.getPlayerState === 'function') {
              var st = window.ytPlayer.getPlayerState();
              if (st === 2) { // PAUSED
                setTimeout(function(){ window.ytPlayer.playVideo(); }, 500);
              }
            }
          } catch(e){}
        })();
      """);
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
    }
    if (state == AppLifecycleState.resumed) {
      _keepAliveTimer?.cancel();
    }
  }

  Future<dynamic> _onNativeCall(MethodCall call) async {
    switch (call.method) {
      case 'onPlayPause':
        await _wvc?.evaluateJavascript(
            source: "(function(){ if(typeof togglePlay==='function') togglePlay(); })();");
        break;
      case 'onNext':
        await _wvc?.evaluateJavascript(
            source: "if(typeof playNextSimilarSong==='function') playNextSimilarSong();");
        break;
      case 'onPrev':
        await _wvc?.evaluateJavascript(
            source: "if(typeof playPrevSong==='function') playPrevSong();");
        break;
    }
  }

  Future<bool> _onBack() async {
    if (_wvc == null) return true;
    final r = await _wvc!.evaluateJavascript(source: """
      (function(){
        var m=['playerModal','lyricsModal','editProfileModal','createPlaylistModal',
               'addToPlaylistModal','commentsModal','pickerModal'];
        for(var i=0;i<m.length;i++){
          var e=document.getElementById(m[i]);
          if(e&&e.style.display!==''&&e.style.display!=='none') return 'modal:'+m[i];
        }
        var a=document.querySelector('.view-section.active');
        return a?a.id:'view-home';
      })()
    """);
    final s = (r ?? 'view-home').replaceAll('"', '').trim();
    if (s.startsWith('modal:')) {
      final id = s.split(':')[1];
      await _wvc!.evaluateJavascript(source: """
        (function(){
          var e=document.getElementById('$id');
          if(e) e.style.display='none';
          if('$id'==='lyricsModal'){
            if(typeof closeLyricsToPlayer==='function') closeLyricsToPlayer();
            else if(typeof closeLyrics==='function') closeLyrics();
          }
        })()
      """);
      return false;
    }
    if (!['view-home','view-search','view-library','view-settings'].contains(s)) {
      await _wvc!.evaluateJavascript(
          source: "if(typeof switchView==='function') switchView('home');");
      return false;
    }
    final now = DateTime.now();
    if (_lastBack == null || now.difference(_lastBack!) > const Duration(seconds: 2)) {
      _lastBack = now;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Tekan sekali lagi untuk keluar'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ));
      }
      return false;
    }
    return true;
  }

  Future<void> _download(String videoId, String title) async {
    if (Platform.isAndroid) await Permission.storage.request();
    try {
      final r = await http.post(Uri.parse('$_base/api/download'),
          headers: {'Content-Type': 'application/json'},
          body: '{"videoId":"$videoId"}').timeout(const Duration(seconds: 60));
      if (r.statusCode != 200) throw Exception();
      final um = RegExp(r'"url"\s*:\s*"([^"]+)"').firstMatch(r.body);
      final tm = RegExp(r'"title"\s*:\s*"([^"]+)"').firstMatch(r.body);
      if (um == null) throw Exception();
      final url = um.group(1)!.replaceAll(r'\/', '/');
      final t2  = tm?.group(1) ?? title;
      final dl  = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 120));
      if (dl.statusCode != 200) throw Exception();
      final dir  = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final f    = File('${base}Download/${title.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_')}.mp3');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(dl.bodyBytes);
      _wvc?.evaluateJavascript(source: "showToast('Download selesai: $t2');");
    } catch (_) {
      _wvc?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _onBack() && mounted) SystemNavigator.pop();
      },
      child: Scaffold(
        backgroundColor: const Color(0xFF0a0a0f),
        resizeToAvoidBottomInset: false,
        body: SafeArea(
          top: true, bottom: true,
          child: Stack(children: [
            InAppWebView(
              keepAlive: _keepAlive,
              initialUrlRequest: URLRequest(url: WebUri(_base)),
              initialSettings: InAppWebViewSettings(
                javaScriptEnabled: true,
                domStorageEnabled: true,
                databaseEnabled: true,
                mediaPlaybackRequiresUserGesture: false,
                mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,
                useWideViewPort: true,
                loadWithOverviewMode: true,
                supportZoom: false,
                builtInZoomControls: false,
                displayZoomControls: false,
                cacheMode: CacheMode.LOAD_DEFAULT,
                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
              ),
              onWebViewCreated: (c) {
                _wvc = c;

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title  = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist = args.length > 1 ? args[1].toString() : '';
                    _musicPlaying = true;
                    WakelockPlus.enable();
                    // Start periodic keepAlive setiap 30 detik
                    _keepAliveTimer?.cancel();
                    _keepAliveTimer = Timer.periodic(const Duration(seconds: 30), (_) {
                      if (_musicPlaying) {
                        try { _ch.invokeMethod('keepAlive'); } catch (_) {}
                      }
                    });
                    try {
                      await _ch.invokeMethod('updateTrack',
                          {'title': title, 'artist': artist, 'isPlaying': true});
                    } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    _musicPlaying = false;
                    _keepAliveTimer?.cancel();
                    try {
                      await _ch.invokeMethod('setPlaying', {'isPlaying': false});
                    } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'setBgMode',
                  callback: (args) async {
                    final on = args.isNotEmpty &&
                        (args[0] == true || args[0].toString() == 'true');
                    try {
                      await _ch.invokeMethod('updateTrack',
                          {'title': 'Auspoty', 'artist': 'Auspoty Music', 'isPlaying': on});
                      if (on) WakelockPlus.enable();
                    } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'isAndroid',
                  callback: (args) => true,
                );

                c.addJavaScriptHandler(
                  handlerName: 'downloadTrack',
                  callback: (args) async {
                    final vid   = args.isNotEmpty ? args[0].toString() : '';
                    final title = args.length > 1 ? args[1].toString() : 'lagu';
                    if (vid.isNotEmpty) _download(vid, title);
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'openDownload',
                  callback: (args) async {
                    final url = args.isNotEmpty ? args[0].toString() : '';
                    if (url.isNotEmpty) {
                      final uri = Uri.parse(url);
                      if (await canLaunchUrl(uri)) {
                        await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    }
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'getAccountName',
                  callback: (args) async {
                    final p = await SharedPreferences.getInstance();
                    return p.getString('accountName') ?? '';
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'openGoogleLogin',
                  callback: (args) async {
                    await c.loadUrl(
                        urlRequest: URLRequest(url: WebUri('$_base/login.html')));
                  },
                );
              },

              onLoadStart: (c, url) => setState(() => _loading = true),

              onLoadStop: (c, url) async {
                setState(() => _loading = false);
                final urlStr = url?.toString() ?? '';
                if (urlStr.contains('userData=')) {
                  final uri = Uri.parse(urlStr);
                  final ud  = uri.queryParameters['userData'];
                  if (ud != null && ud.isNotEmpty) {
                    await c.evaluateJavascript(source: """
                      (function(){
                        try {
                          var raw=decodeURIComponent("${Uri.encodeComponent(ud)}");
                          localStorage.setItem('auspotyGoogleUser',raw);
                          var p=JSON.parse(raw);
                          if(typeof updateProfileUI==='function') updateProfileUI();
                          if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
                          if(typeof showToast==='function') showToast('Selamat datang, '+(p.name||'').split(' ')[0]+'!');
                          history.replaceState(null,'','/');
                        } catch(e){}
                      })()
                    """);
                  }
                }
                if (urlStr.contains('vercel.app') || urlStr.contains('clone2') || urlStr.isEmpty) {
                  await _inject(c);
                }
              },

              onCreateWindow: (c, action) async {
                final url = action.request.url?.toString() ?? '';
                if (url.isNotEmpty && url != 'about:blank') {
                  final uri = Uri.parse(url);
                  if (await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                }
                return true;
              },

              onProgressChanged: (c, p) {
                if (p == 100) setState(() => _loading = false);
              },

              onPermissionRequest: (c, req) async => PermissionResponse(
                  resources: req.resources, action: PermissionResponseAction.GRANT),

              shouldOverrideUrlLoading: (c, nav) async {
                final url = nav.request.url?.toString() ?? '';
                const ok = ['vercel.app','youtube.com','ytimg.com','googleapis.com',
                  'gstatic.com','firebaseapp.com','firebase.google.com',
                  'accounts.google.com','google.com','googleusercontent.com'];
                for (final d in ok) { if (url.contains(d)) return NavigationActionPolicy.ALLOW; }
                if (url.startsWith('about:') || url.startsWith('blob:') || url.startsWith('data:')) {
                  return NavigationActionPolicy.ALLOW;
                }
                if (url.startsWith('http') && nav.isForMainFrame) {
                  final uri = Uri.parse(url);
                  if (await canLaunchUrl(uri)) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                  return NavigationActionPolicy.CANCEL;
                }
                return NavigationActionPolicy.ALLOW;
              },
            ),

            if (_loading)
              Container(
                color: const Color(0xFF0a0a0f),
                child: const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.music_note, color: Color(0xFFa78bfa), size: 64),
                      SizedBox(height: 16),
                      Text('Auspoty',
                          style: TextStyle(color: Colors.white, fontSize: 28,
                              fontWeight: FontWeight.bold, letterSpacing: 2)),
                      SizedBox(height: 24),
                      CircularProgressIndicator(color: Color(0xFFa78bfa), strokeWidth: 2),
                    ],
                  ),
                ),
              ),
          ]),
        ),
      ),
    );
  }

  Future<void> _inject(InAppWebViewController c) async {
    await c.evaluateJavascript(source: r"""
      (function(){
        var id='__af__', o=document.getElementById(id); if(o) o.remove();
        var s=document.createElement('style'); s.id=id;
        s.textContent=`
          .bottom-nav{position:fixed!important;bottom:0!important;left:0!important;right:0!important;
            height:60px!important;display:flex!important;justify-content:space-around!important;
            align-items:center!important;padding:0!important;background:rgba(10,10,15,0.95)!important;
            backdrop-filter:blur(30px)!important;border-top:1px solid rgba(255,255,255,0.1)!important;z-index:1000!important;}
          .nav-item{display:flex!important;flex-direction:column!important;align-items:center!important;
            justify-content:center!important;gap:3px!important;font-size:10px!important;
            min-width:60px!important;height:60px!important;cursor:pointer!important;color:rgba(255,255,255,0.5)!important;}
          .nav-item.active{color:#a78bfa!important;}
          .nav-item svg{width:22px!important;height:22px!important;fill:currentColor!important;}
          body{padding-bottom:160px!important;}
          .mini-player{bottom:68px!important;}
          .toast-notification.show{bottom:80px!important;}
        `;
        document.head.appendChild(s);
      })();
    """);

    await c.evaluateJavascript(source: r"""
      (function(){
        if(window.__auspotyBridgeReady) return;
        window.__auspotyBridgeReady = true;

        // Block visibilitychange agar YouTube tidak pause saat background
        document.addEventListener('visibilitychange', function(e){
          e.stopImmediatePropagation();
          e.preventDefault();
        }, true);

        // Override document.hidden dan visibilityState
        try {
          Object.defineProperty(document, 'hidden', {
            get: function(){ return false; }, configurable: true
          });
          Object.defineProperty(document, 'visibilityState', {
            get: function(){ return 'visible'; }, configurable: true
          });
        } catch(e){}

        // AndroidBridge untuk download
        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          openDownload: function(vid, t){
            window.flutter_inappwebview.callHandler('downloadTrack', vid, t||'');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          }
        };

        console.log('[Auspoty] Bridge ready');
      })();
    """);
  }
}
'''

path = 'auspoty-flutter/lib/main.dart'
open(path, 'w', encoding='utf-8').write(content)
lines = content.split('\n')
print("Wrote main.dart, lines:", len(lines))
print("WidgetsBindingObserver:", 'WidgetsBindingObserver' in content)
print("didChangeAppLifecycleState:", 'didChangeAppLifecycleState' in content)
print("onMusicPlaying handler:", 'onMusicPlaying' in content)
print("onMusicPaused handler:", 'onMusicPaused' in content)
print("keepAliveTimer:", '_keepAliveTimer' in content)
print("_musicPlaying flag:", '_musicPlaying' in content)
print("visibilitychange block:", 'visibilitychange' in content)
