import 'dart:async';
import 'dart:convert';
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

// Simple local file server for serving downloaded audio to WebView
HttpServer? _fileServer;
String? _servedFilePath;
int _fileServerPort = 8765;

Future<void> _startFileServer() async {
  if (_fileServer != null) return;
  try {
    _fileServer = await HttpServer.bind(InternetAddress.loopbackIPv4, _fileServerPort);
    _fileServer!.listen((req) async {
      if (req.method == 'OPTIONS') {
        req.response.headers.set('Access-Control-Allow-Origin', '*');
        req.response.statusCode = 200;
        await req.response.close();
        return;
      }
      final path = _servedFilePath;
      if (path == null) { req.response.statusCode = 404; await req.response.close(); return; }
      final f = File(path);
      if (!await f.exists()) { req.response.statusCode = 404; await req.response.close(); return; }
      final ext  = path.split('.').last.toLowerCase();
      final mime = ext == 'webm' ? 'audio/webm' : ext == 'mp3' ? 'audio/mpeg' : 'audio/mp4';
      final bytes = await f.readAsBytes();
      final total = bytes.length;
      req.response.headers.set('Content-Type', mime);
      req.response.headers.set('Accept-Ranges', 'bytes');
      req.response.headers.set('Access-Control-Allow-Origin', '*');
      // Support range requests so audio seeking works
      final rangeHeader = req.headers.value('range');
      if (rangeHeader != null && rangeHeader.startsWith('bytes=')) {
        final parts = rangeHeader.substring(6).split('-');
        final start = int.tryParse(parts[0]) ?? 0;
        final end   = (parts.length > 1 && parts[1].isNotEmpty)
            ? (int.tryParse(parts[1]) ?? (total - 1))
            : (total - 1);
        final chunk = bytes.sublist(start, end + 1);
        req.response.statusCode = 206;
        req.response.headers.set('Content-Range', 'bytes $start-$end/$total');
        req.response.headers.set('Content-Length', chunk.length.toString());
        req.response.add(chunk);
      } else {
        req.response.statusCode = 200;
        req.response.headers.set('Content-Length', total.toString());
        req.response.add(bytes);
      }
      await req.response.close();
    });
  } catch (_) { _fileServer = null; }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _startFileServer();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Colors.transparent,
    systemNavigationBarDividerColor: Colors.transparent,
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
      // Override document.hidden so YouTube IFrame doesn't pause in background
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          if(window.__bgHidden) return;
          window.__bgHidden = true;
          try {
            Object.defineProperty(document,'hidden',{get:function(){return false;},configurable:true});
            Object.defineProperty(document,'visibilityState',{get:function(){return 'visible';},configurable:true});
            Object.defineProperty(document,'webkitHidden',{get:function(){return false;},configurable:true});
            var _oa=document.addEventListener.bind(document);
            document.addEventListener=function(t,fn,o){
              if(t==='visibilitychange'||t==='webkitvisibilitychange') return;
              _oa(t,fn,o);
            };
          } catch(e){}
        })();
      """);
    }
    if (state == AppLifecycleState.resumed) {
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          window.__bgHidden=false;
          try{delete document.hidden;delete document.visibilityState;delete document.webkitHidden;}catch(e){}
        })();
      """);
      _startProgressTimer();
    }
  }

  Future<dynamic> _onNativeCall(MethodCall call) async {
    switch (call.method) {
      case 'onPlayPause':
        // Toggle play/pause di JS (untuk update UI)
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

  // Progress handled by JS setInterval
  void _startProgressTimer() {}

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
    final t2 = title.replaceAll("'", "\\'");
    try {
      _wvc?.evaluateJavascript(source: "showToast('Mengonversi lagu... tunggu sebentar');");
      if (Platform.isAndroid) {
        final s = await Permission.storage.request();
        if (!s.isGranted) await Permission.manageExternalStorage.request();
      }

      // Step 1: Call our API which uses ytmp3.mobi to get MP3 download URL
      final apiRes = await http.get(
        Uri.parse('$_base/api/download?video_id=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0'},
      ).timeout(const Duration(seconds: 58));
      if (apiRes.statusCode != 200) throw Exception('API error ${apiRes.statusCode}');
      final apiJson = json.decode(apiRes.body) as Map<String, dynamic>;
      if (apiJson['status'] != 'success') throw Exception(apiJson['message']?.toString() ?? 'failed');

      final dlUrl   = apiJson['url'] as String;
      final apiTitle = (apiJson['title'] as String?) ?? title;
      final ext      = (apiJson['ext'] as String?) ?? 'mp3';

      // Step 2: Download MP3 bytes in background (no browser, no Chrome)
      _wvc?.evaluateJavascript(source: "showToast('Mengunduh MP3...');");
      final dlReq = http.Request('GET', Uri.parse(dlUrl));
      dlReq.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120';
      dlReq.headers['Referer'] = 'https://id.ytmp3.mobi/';
      final dlStream = await http.Client().send(dlReq).timeout(const Duration(seconds: 120));
      if (dlStream.statusCode != 200) throw Exception('Download error ${dlStream.statusCode}');
      final bytes = await dlStream.stream.toBytes().timeout(const Duration(seconds: 120));

      // Step 3: Save file to internal app storage (no external permission needed)
      final appDir = await getApplicationDocumentsDirectory();
      final safe   = apiTitle.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
      final f      = File('${appDir.path}/$safe.$ext');
      await f.writeAsBytes(bytes);

      // Step 4: Store videoId→file mapping in SharedPreferences
      final prefs   = await SharedPreferences.getInstance();
      final mapJson = prefs.getString('downloadedFiles') ?? '{}';
      final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
      fileMap[videoId] = {'filename': safe, 'ext': ext, 'title': apiTitle};
      await prefs.setString('downloadedFiles', json.encode(fileMap));

      // Step 5: Save to IndexedDB so it shows in Koleksi > Lagu Diunduh
      await _wvc?.evaluateJavascript(source: """
        (function(){
          var track = {
            videoId: '$videoId',
            title: '${apiTitle.replaceAll("'", "\\'")}',
            artist: window.currentTrack ? (window.currentTrack.artist || '') : '',
            img: window.currentTrack ? (window.currentTrack.img || '') : ''
          };
          if(typeof saveDownloadedSong==='function') saveDownloadedSong(track);
          showToast('\u2713 Tersimpan: ${t2.length > 30 ? t2.substring(0, 30) : t2}');
        })();
      """);
    } catch (e) {
      final msg   = e.toString();
      final short = msg.length > 60 ? msg.substring(0, 60) : msg;
      _wvc?.evaluateJavascript(source: "showToast('Download gagal: ${short.replaceAll("'", "\\'")}');");
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
                allowBackgroundAudioPlaying: true,
                // TextureView (false) = smoother scroll, GPU composited, better 60fps
                useHybridComposition: false,
                allowFileAccessFromFileURLs: false,
                allowUniversalAccessFromFileURLs: false,
                mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,
                useWideViewPort: false,
                loadWithOverviewMode: false,
                supportZoom: false,
                builtInZoomControls: false,
                displayZoomControls: false,
                cacheMode: CacheMode.LOAD_CACHE_ELSE_NETWORK,
                geolocationEnabled: false,
                safeBrowsingEnabled: false,
                disableDefaultErrorPage: true,
                verticalScrollBarEnabled: false,
                horizontalScrollBarEnabled: false,
                overScrollMode: OverScrollMode.NEVER,
                transparentBackground: false,
                disabledActionModeMenuItems: ActionModeMenuItem.MENU_ITEM_NONE,
                // Renderer priority — foreground = max priority
                rendererPriorityPolicy: RendererPriorityPolicy(
                  rendererRequestedPriority: RendererPriority.RENDERER_PRIORITY_IMPORTANT,
                  waivedWhenNotVisible: false,
                ),
                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
              ),
              onWebViewCreated: (c) {
                _wvc = c;

                // Dipanggil saat lagu mulai play — trigger MediaPlayer native
                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title  = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist = args.length > 1 ? args[1].toString() : '';
                    final imgUrl = args.length > 3 ? args[3].toString() : '';
                    WakelockPlus.enable();
                    try {
                      await _ch.invokeMethod('updateTrack', {
                        'title': title,
                        'artist': artist,
                        'isPlaying': true,
                        'imgUrl': imgUrl,
                      });
                    } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    _progressTimer?.cancel();
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async {
                    try { await _ch.invokeMethod('setPlaying', {'isPlaying': true}); } catch (_) {}
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
                  handlerName: 'playLocalFile',
                  callback: (args) async {
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final img     = args.length > 2 ? args[2].toString() : '';
                    final videoId = args.length > 3 ? args[3].toString() : '';
                    try {
                      // Look up exact filename from SharedPreferences map
                      File? found;
                      String? foundExt;
                      final appDir = await getApplicationDocumentsDirectory();

                      if (videoId.isNotEmpty) {
                        final prefs   = await SharedPreferences.getInstance();
                        final mapJson = prefs.getString('downloadedFiles') ?? '{}';
                        final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
                        if (fileMap.containsKey(videoId)) {
                          final info = fileMap[videoId] as Map<String, dynamic>;
                          final fn   = info['filename']?.toString() ?? '';
                          final ex   = info['ext']?.toString() ?? 'mp3';
                          if (fn.isNotEmpty) {
                            final f = File('${appDir.path}/$fn.$ex');
                            if (await f.exists()) { found = f; foundExt = ex; }
                          }
                        }
                      }
                      // Fallback: search by sanitized title
                      if (found == null) {
                        final safe = title.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
                        for (final ext in ['mp3', 'mp4', 'webm', 'm4a']) {
                          final f = File('${appDir.path}/$safe.$ext');
                          if (await f.exists()) { found = f; foundExt = ext; break; }
                        }
                      }
                      if (found != null) {
                        // Notify native service for notification
                        try {
                          await _ch.invokeMethod('updateTrack', {
                            'title': title, 'artist': artist,
                            'isPlaying': true, 'imgUrl': img,
                          });
                        } catch (_) {}
                        // Point local server to this file, then give WebView a localhost URL
                        _servedFilePath = found.path;
                        final localUrl = 'http://127.0.0.1:$_fileServerPort/audio.$foundExt';
                        await c.evaluateJavascript(source: """
                          (function(){
                            window._localAudioPlaying = true;
                            var au = document.getElementById('bgAudio');
                            if (!au) {
                              au = document.createElement('audio');
                              au.id = 'bgAudio';
                              au.style.display = 'none';
                              document.body.appendChild(au);
                            }
                            // Remove old listeners
                            au.onplay = null; au.onpause = null; au.onended = null;
                            au.src = '${localUrl.replaceAll("'", "\\'")}';
                            au.onplay = function() {
                              isPlaying = true;
                              updatePlayPauseBtn(true);
                              _setArtPlaying(true);
                              startProgressBar();
                            };
                            au.onpause = function() {
                              isPlaying = false;
                              updatePlayPauseBtn(false);
                              _setArtPlaying(false);
                            };
                            au.onended = function() {
                              isPlaying = false;
                              window._localAudioPlaying = false;
                              updatePlayPauseBtn(false);
                              _setArtPlaying(false);
                              stopProgressBar();
                              if (isRepeat) { au.currentTime = 0; au.play(); }
                              else playNextSimilarSong();
                            };
                            au.play().catch(function(e){ console.log('local play err', e); });
                          })();
                        """);
                      } else {
                        // File not found, fallback to stream
                        await c.evaluateJavascript(source: """
                          (function(){
                            window._localAudioPlaying = false;
                            if(window.ytPlayer && window.ytPlayer.loadVideoById && window.currentTrack)
                              window.ytPlayer.loadVideoById(window.currentTrack.videoId);
                          })();
                        """);
                      }
                    } catch (e) {
                      await c.evaluateJavascript(source: """
                        if(window.ytPlayer&&window.ytPlayer.loadVideoById&&window.currentTrack)
                          window.ytPlayer.loadVideoById(window.currentTrack.videoId);
                      """);
                    }
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

              onReceivedError: (c, req, err) async {
                // Saat offline, coba load dari cache
                if (req.isForMainFrame == true) {
                  setState(() => _loading = false);
                  // Restart file server jika mati
                  if (_fileServer == null) await _startFileServer();
                }
              },

              onPermissionRequest: (c, req) async =>
                  PermissionResponse(resources: req.resources, action: PermissionResponseAction.GRANT),

              shouldOverrideUrlLoading: (c, nav) async {
                final url = nav.request.url?.toString() ?? '';
                const ok = ['vercel.app','youtube.com','ytimg.com','googleapis.com',
                  'gstatic.com','firebaseapp.com','firebase.google.com',
                  'accounts.google.com','google.com','googleusercontent.com',
                  '127.0.0.1','localhost'];
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
            align-items:center!important;padding:0!important;background:#0a0a0f!important;
            border-top:1px solid rgba(255,255,255,0.1)!important;z-index:1000!important;
            transform:translateZ(0)!important;}
          .nav-item{display:flex!important;flex-direction:column!important;align-items:center!important;
            justify-content:center!important;gap:3px!important;font-size:10px!important;
            min-width:60px!important;height:60px!important;cursor:pointer!important;color:rgba(255,255,255,0.5)!important;}
          .nav-item.active{color:#a78bfa!important;}
          .nav-item svg{width:22px!important;height:22px!important;fill:currentColor!important;}
          body{padding-bottom:140px!important;}
          .mini-player{bottom:64px!important;will-change:transform!important;}
          .toast-notification.show{bottom:80px!important;}
          *{-webkit-tap-highlight-color:transparent!important;}
          html,body{-webkit-overflow-scrolling:touch!important;scroll-behavior:auto!important;}
          .view-section.active{contain:none!important;}
          img{content-visibility:visible!important;}
          @keyframes slideUpMini{from{opacity:0}to{opacity:1}}
          @keyframes slideUp{from{opacity:0}to{opacity:1}}
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
            // Audio tetap di ytPlayer, native hanya untuk notifikasi
            window._nativeLoading = false;
            window._nativePlaying = false;
            window._nativePaused = false;
            if(window.flutter_inappwebview){
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', '', img||'');
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
          if(bar){ bar.value = pct; bar.style.background='linear-gradient(to right, white '+pct+'%, rgba(255,255,255,0.2) '+pct+'%)'; }
          var fmt = function(s){ var m=Math.floor(s/60),sec=s%60; return m+':'+(sec<10?'0':'')+sec; };
          var ct = document.getElementById('currentTime'); if(ct) ct.innerText = fmt(pos);
          var tt = document.getElementById('totalTime'); if(tt) tt.innerText = fmt(dur);
        };

        // Format waktu helper
        window._fmtTime = function(s) {
          var m = Math.floor(s/60), sec = s%60;
          return m + ':' + (sec<10?'0':'') + sec;
        };

        console.log('[Auspoty] Bridge ready');
      })();
    """);
  }
}
