import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:audio_service/audio_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'audio_handler.dart';

final _keepAlive = InAppWebViewKeepAlive();
const _base = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';

late AuspotyAudioHandler _audioHandler;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(0xFF0a0a0f),
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  // Fix: AudioServiceConfig tidak boleh const karena Color bukan const
  _audioHandler = await AudioService.init(
    builder: () => AuspotyAudioHandler(),
    config: AudioServiceConfig(
      androidNotificationChannelId: 'com.auspoty.app.audio',
      androidNotificationChannelName: 'Auspoty Music',
      androidNotificationOngoing: true,
      androidStopForegroundOnPause: false,
      notificationColor: const Color(0xFFa78bfa),
      androidNotificationIcon: 'mipmap/ic_launcher',
    ),
  );

  runApp(const AuspotyApp());
}

class AuspotyApp extends StatelessWidget {
  const AuspotyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Auspoty',
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(primary: Color(0xFFa78bfa)),
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
  StreamSubscription? _posSub;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _audioHandler.onSkipToNext = () => _wvc?.evaluateJavascript(
        source: "if(typeof playNextSimilarSong==='function') playNextSimilarSong();");
    _audioHandler.onSkipToPrevious = () => _wvc?.evaluateJavascript(
        source: "if(typeof playPrevSong==='function') playPrevSong();");

    // Update progress bar di JS setiap detik
    _posSub = _audioHandler.positionStream.listen((pos) {
      final dur = _audioHandler.durationSeconds;
      if (dur > 0 && _wvc != null) {
        final s = pos.inSeconds;
        _wvc!.evaluateJavascript(source:
          "if(typeof window._updateNativeProgress==='function') window._updateNativeProgress($s,$dur);");
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _posSub?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.paused) WakelockPlus.enable();
  }

  Future<void> _playNative(String videoId, String title, String artist) async {
    try {
      // Fetch stream URL dari API
      final resp = await http.get(
        Uri.parse('$_base/api/stream?videoId=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
      ).timeout(const Duration(seconds: 30));

      if (resp.statusCode != 200) return;

      // Parse JSON dengan dart:convert (lebih reliable dari regex)
      final Map<String, dynamic> data = jsonDecode(resp.body);
      if (data['status'] != 'success') return;

      final streamUrl = (data['url'] as String).replaceAll(r'\/', '/');
      final rawHeaders = data['headers'] as Map<String, dynamic>? ?? {};
      final streamHeaders = rawHeaders.map((k, v) => MapEntry(k, v.toString()));

      // Fallback headers
      if (streamHeaders.isEmpty) {
        streamHeaders['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36';
        streamHeaders['Accept'] = '*/*';
        streamHeaders['Accept-Language'] = 'en-us,en;q=0.5';
      }

      final item = MediaItem(
        id: videoId,
        title: title.isEmpty ? 'Auspoty' : title,
        artist: artist.isEmpty ? 'Auspoty Music' : artist,
      );

      await _audioHandler.playFromUrl(streamUrl, item, headers: streamHeaders);

      // Update UI JS
      _wvc?.evaluateJavascript(source: """
        window._nativePlaying = true;
        window._nativeLoading = false;
        if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
      """);
    } catch (_) {}
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
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Tekan sekali lagi untuk keluar'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ));
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
                    final title   = args.isNotEmpty ? args[0].toString() : '';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final videoId = args.length > 2 ? args[2].toString() : '';
                    WakelockPlus.enable();
                    if (videoId.isNotEmpty) await _playNative(videoId, title, artist);
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async => _audioHandler.pause(),
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async => _audioHandler.play(),
                );

                c.addJavaScriptHandler(
                  handlerName: 'setBgMode',
                  callback: (args) async {
                    final on = args.isNotEmpty && (args[0] == true || args[0].toString() == 'true');
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
                  callback: (args) async =>
                    c.loadUrl(urlRequest: URLRequest(url: WebUri('$_base/login.html'))),
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

        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          playNative: function(videoId, title, artist, img){
            try { if(window.ytPlayer && window.ytPlayer.mute) window.ytPlayer.mute(); } catch(e){}
            window._nativeLoading = true;
            window._nativePlaying = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', videoId||'');
            }
          },
          pauseNative: function(){
            window._nativePlaying = false;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused');
          },
          resumeNative: function(){
            window._nativePlaying = true;
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

        window._updateNativeProgress = function(pos, dur){
          if(dur <= 0) return;
          var bar = document.getElementById('progressBar');
          if(bar){ bar.value = pos; bar.max = dur; }
          var fmt = function(s){ var m=Math.floor(s/60),sec=s%60; return m+':'+(sec<10?'0':'')+sec; };
          var ct = document.getElementById('currentTime'); if(ct) ct.innerText = fmt(pos);
          var tt = document.getElementById('totalTime'); if(tt) tt.innerText = fmt(dur);
        };

        window._fmtTime = function(s) {
          var m = Math.floor(s/60), sec = s%60;
          return m + ':' + (sec<10?'0':'') + sec;
        };

        console.log('[Auspoty] Bridge ready');
      })();
    """);
  }
}
