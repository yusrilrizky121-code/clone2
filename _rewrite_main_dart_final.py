"""
Rewrite main.dart completely - clean version with all fixes
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

DART_PATH = r'auspoty-flutter\lib\main.dart'

content = r"""import 'dart:async';
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
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFa78bfa), brightness: Brightness.dark),
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

class _AuspotyWebViewState extends State<AuspotyWebView> with WidgetsBindingObserver {
  InAppWebViewController? _wvc;
  bool _loading = true;
  DateTime? _lastBack;
  Timer? _progressTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ch.setMethodCallHandler(_onNativeCall);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _progressTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _progressTimer?.cancel();
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
    }
    if (state == AppLifecycleState.resumed) {
      _startProgressTimer();
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

  String _fmtTime(int s) {
    final m = s ~/ 60;
    final sec = s % 60;
    return '$m:${sec.toString().padLeft(2, '0')}';
  }

  void _startProgressTimer() {
    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      try {
        final pos = await _ch.invokeMethod<int>('getPosition') ?? 0;
        final dur = await _ch.invokeMethod<int>('getDuration') ?? 0;
        if (dur > 0 && _wvc != null) {
          final posStr = _fmtTime(pos);
          final durStr = _fmtTime(dur);
          final pct = (pos / dur * 100).toStringAsFixed(2);
          await _wvc!.evaluateJavascript(source:
            "if(typeof window._updateNativeProgress==='function') window._updateNativeProgress($pos,$dur);"
          );
          // Fallback jika _updateNativeProgress belum ada
          await _wvc!.evaluateJavascript(source: """
            (function(){
              var pb=document.getElementById('progressBar');
              var ct=document.getElementById('currentTime');
              var tt=document.getElementById('totalTime');
              if(pb){pb.value=$pct;pb.style.background='linear-gradient(to right,white $pct%,rgba(255,255,255,0.2) $pct%)';}
              if(ct)ct.innerText='$posStr';
              if(tt)tt.innerText='$durStr';
            })();
          """);
        }
      } catch (_) {}
    });
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
      await _wvc!.evaluateJavascript(source: "if(typeof switchView==='function') switchView('home');");
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
                allowsInlineMediaPlayback: true,
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
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final videoId = args.length > 2 ? args[2].toString() : '';
                    WakelockPlus.enable();
                    if (videoId.isNotEmpty) {
                      try {
                        await _ch.invokeMethod('playNative', {
                          'videoId': videoId,
                          'title': title,
                          'artist': artist,
                        });
                        _startProgressTimer();
                        // Notify JS that native playback started
                        await c.evaluateJavascript(source:
                          "if(typeof window._onNativePlaybackStarted==='function') window._onNativePlaybackStarted();"
                        );
                      } catch (e) {
                        try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true}); } catch (_) {}
                      }
                    } else {
                      try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true}); } catch (_) {}
                    }
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    _progressTimer?.cancel();
                    try { await _ch.invokeMethod('pauseNative'); } catch (_) {}
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async {
                    try { await _ch.invokeMethod('resumeNative'); } catch (_) {}
                    _startProgressTimer();
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'setBgMode',
                  callback: (args) async {
                    final on = args.isNotEmpty && (args[0] == true || args[0].toString() == 'true');
                    try { await _ch.invokeMethod('updateTrack', {'title': 'Auspoty', 'artist': 'Auspoty Music', 'isPlaying': on}); } catch (_) {}
                    if (on) WakelockPlus.enable();
                  },
                );

                c.addJavaScriptHandler(handlerName: 'isAndroid', callback: (args) => true);

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
                      if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
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
                    await c.loadUrl(urlRequest: URLRequest(url: WebUri('$_base/login.html')));
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
                    final encoded = Uri.encodeComponent(ud);
                    await c.evaluateJavascript(source: """
                      (function(){
                        try {
                          var raw=decodeURIComponent("$encoded");
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
                  if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
                return true;
              },

              onProgressChanged: (c, p) { if (p == 100) setState(() => _loading = false); },

              onPermissionRequest: (c, req) async =>
                  PermissionResponse(resources: req.resources, action: PermissionResponseAction.GRANT),

              shouldOverrideUrlLoading: (c, nav) async {
                final url = nav.request.url?.toString() ?? '';
                const ok = ['vercel.app','youtube.com','ytimg.com','googleapis.com',
                  'gstatic.com','firebaseapp.com','firebase.google.com',
                  'accounts.google.com','google.com','googleusercontent.com'];
                for (final d in ok) { if (url.contains(d)) return NavigationActionPolicy.ALLOW; }
                if (url.startsWith('about:') || url.startsWith('blob:') || url.startsWith('data:')) return NavigationActionPolicy.ALLOW;
                if (url.startsWith('http') && nav.isForMainFrame) {
                  final uri = Uri.parse(url);
                  if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
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
                      Text('Auspoty', style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold, letterSpacing: 2)),
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
    // CSS fix untuk bottom nav
    await c.evaluateJavascript(source: r"""
      (function(){
        var id='__af__', o=document.getElementById(id); if(o) o.remove();
        var s=document.createElement('style'); s.id=id;
        s.textContent='.bottom-nav{position:fixed!important;bottom:0!important;left:0!important;right:0!important;height:60px!important;display:flex!important;justify-content:space-around!important;align-items:center!important;padding:0!important;background:rgba(10,10,15,0.95)!important;backdrop-filter:blur(30px)!important;border-top:1px solid rgba(255,255,255,0.1)!important;z-index:1000!important;}.nav-item{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:3px!important;font-size:10px!important;min-width:60px!important;height:60px!important;cursor:pointer!important;color:rgba(255,255,255,0.5)!important;}.nav-item.active{color:#a78bfa!important;}.nav-item svg{width:22px!important;height:22px!important;fill:currentColor!important;}body{padding-bottom:160px!important;}.mini-player{bottom:68px!important;}.toast-notification.show{bottom:80px!important;}';
        document.head.appendChild(s);
      })();
    """);

    // AndroidBridge + callbacks
    await c.evaluateJavascript(source: r"""
      (function(){
        if(window.__auspotyBridgeReady) return;
        window.__auspotyBridgeReady = true;

        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          playNative: function(videoId, title, artist, img){
            try { if(window.ytPlayer && window.ytPlayer.mute) window.ytPlayer.mute(); } catch(e){}
            window._nativeLoading = true;
            window._nativePlaying = false;
            window._nativePaused = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', videoId||'');
            }
          },
          pauseNative: function(){
            window._nativePlaying = false;
            window._nativePaused = true;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused');
          },
          resumeNative: function(){
            window._nativePlaying = true;
            window._nativePaused = false;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicResumed');
          },
          openDownload: function(vid, t){
            window.flutter_inappwebview.callHandler('downloadTrack', vid, t||'');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          }
        };

        window._onNativePlaybackStarted = function(){
          window._nativeLoading = false;
          window._nativePlaying = true;
          window._nativePaused = false;
          isPlaying = true;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
        };
        window._onNativePlaybackPaused = function(){
          window._nativePlaying = false;
          window._nativePaused = true;
          isPlaying = false;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(false);
        };
        window._updateNativeProgress = function(pos, dur){
          if(dur <= 0) return;
          var pct = (pos/dur)*100;
          var bar = document.getElementById('progressBar');
          if(bar){ bar.value = pct; bar.style.background='linear-gradient(to right,white '+pct+'%,rgba(255,255,255,0.2) '+pct+'%)'; }
          var fmt = function(s){ var m=Math.floor(s/60),sec=s%60; return m+':'+(sec<10?'0':'')+sec; };
          var ct = document.getElementById('currentTime'); if(ct) ct.innerText = fmt(pos);
          var tt = document.getElementById('totalTime'); if(tt) tt.innerText = fmt(dur);
        };

        // Block visibilitychange
        document.addEventListener('visibilitychange', function(e){
          e.stopImmediatePropagation();
          e.preventDefault();
        }, true);
        try {
          Object.defineProperty(document, 'hidden', { get: function(){ return false; }, configurable: true });
          Object.defineProperty(document, 'visibilityState', { get: function(){ return 'visible'; }, configurable: true });
        } catch(e){}

        console.log('[Auspoty] Bridge ready');
      })();
    """);
  }
}
"""

with open(DART_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ main.dart rewritten!")
print(f"  Lines: {len(content.splitlines())}")

# Verify
with open(DART_PATH, 'r', encoding='utf-8') as f:
    v = f.read()
checks = [
    ('playNative in AndroidBridge', 'playNative: function'),
    ('pauseNative in AndroidBridge', 'pauseNative: function'),
    ('resumeNative in AndroidBridge', 'resumeNative: function'),
    ('_onNativePlaybackStarted', '_onNativePlaybackStarted'),
    ('_updateNativeProgress', '_updateNativeProgress'),
    ('_startProgressTimer', '_startProgressTimer'),
    ('_fmtTime', '_fmtTime'),
    ('onMusicPlaying handler', "handlerName: 'onMusicPlaying'"),
    ('playNative channel call', "invokeMethod('playNative'"),
]
for name, pattern in checks:
    print(f"  {'✓' if pattern in v else '✗'} {name}")
