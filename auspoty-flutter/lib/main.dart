import 'dart:async';
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

// MethodChannel ke MusicPlayerService (ExoPlayer native Kotlin)
const _playerChannel = MethodChannel('com.auspoty.app/music');

// KeepAlive — WebView tidak di-dispose
final _webViewKeepAlive = InAppWebViewKeepAlive();

bool _nativeMode = false;

const _apiBase = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';

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
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Auspoty',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFa78bfa),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const AuspotyWebView(),
    );
  }
}

class AuspotyWebView extends StatefulWidget {
  const AuspotyWebView({super.key});

  @override
  State<AuspotyWebView> createState() => _AuspotyWebViewState();
}

class _AuspotyWebViewState extends State<AuspotyWebView> {
  InAppWebViewController? _webViewController;
  bool _isLoading = true;
  Timer? _progressTimer;
  DateTime? _lastBackPress;

  @override
  void dispose() {
    _progressTimer?.cancel();
    super.dispose();
  }

  void _startProgressTimer() {
    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      if (!_nativeMode) return;
      try {
        final pos = await _playerChannel.invokeMethod<int>('getPosition') ?? 0;
        final dur = await _playerChannel.invokeMethod<int>('getDuration') ?? 0;
        if (dur > 0) {
          _webViewController?.evaluateJavascript(source: '''
            (function(){
              var pos=$pos, dur=$dur, pct=(pos/dur)*100;
              var el=document.getElementById('progressBar');
              if(el) el.style.background='linear-gradient(to right,white '+pct+'%,rgba(255,255,255,0.2) '+pct+'%)';
              var ct=document.getElementById('currentTime');
              if(ct) ct.innerText=Math.floor(pos/1000/60)+':'+(Math.floor(pos/1000)%60<10?'0':'')+Math.floor(pos/1000)%60;
              var tt=document.getElementById('totalTime');
              if(tt) tt.innerText=Math.floor(dur/1000/60)+':'+(Math.floor(dur/1000)%60<10?'0':'')+Math.floor(dur/1000)%60;
            })()
          ''');
        }
      } catch (_) {}
    });
  }

  Future<bool> _handleBackPress() async {
    if (_webViewController == null) return true;
    final result = await _webViewController!.evaluateJavascript(source: '''
      (function(){
        var modals=['playerModal','lyricsModal','editProfileModal','createPlaylistModal','addToPlaylistModal','commentsModal','pickerModal'];
        for(var i=0;i<modals.length;i++){
          var el=document.getElementById(modals[i]);
          if(el&&el.style.display!=='none'&&el.style.display!=='') return 'modal:'+modals[i];
        }
        var active=document.querySelector('.view-section.active');
        return active?active.id:'view-home';
      })()
    ''');
    final viewStr = (result ?? 'view-home').replaceAll('"', '').trim();

    if (viewStr.startsWith('modal:')) {
      final modalId = viewStr.split(':')[1];
      await _webViewController!.evaluateJavascript(source: '''
        (function(){
          var el=document.getElementById('$modalId');
          if(el) el.style.display='none';
          if('$modalId'==='lyricsModal'){
            if(typeof closeLyricsToPlayer==='function') closeLyricsToPlayer();
            else if(typeof closeLyrics==='function') closeLyrics();
          }
        })()
      ''');
      return false;
    }

    if (!['view-home','view-search','view-library','view-settings'].contains(viewStr)) {
      await _webViewController!.evaluateJavascript(
          source: "if(typeof switchView==='function') switchView('home');");
      return false;
    }

    final now = DateTime.now();
    if (_lastBackPress == null || now.difference(_lastBackPress!) > const Duration(seconds: 2)) {
      _lastBackPress = now;
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

  Future<void> _downloadMp3(String videoId, String title) async {
    if (Platform.isAndroid) await Permission.storage.request();
    try {
      final apiResp = await http.post(
        Uri.parse('$_apiBase/api/download'),
        headers: {'Content-Type': 'application/json'},
        body: '{"videoId":"$videoId"}',
      ).timeout(const Duration(seconds: 60));
      if (apiResp.statusCode != 200) throw Exception('API error');
      final urlMatch = RegExp(r'"url"\s*:\s*"([^"]+)"').firstMatch(apiResp.body);
      final titleMatch = RegExp(r'"title"\s*:\s*"([^"]+)"').firstMatch(apiResp.body);
      if (urlMatch == null) throw Exception('URL tidak ditemukan');
      final mp3Url = urlMatch.group(1)!.replaceAll(r'\/', '/');
      final mp3Title = titleMatch?.group(1) ?? title;
      final dlResp = await http.get(Uri.parse(mp3Url)).timeout(const Duration(seconds: 120));
      if (dlResp.statusCode != 200) throw Exception('Download gagal');
      final dir = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final file = File('${base}Download/${title.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_')}.mp3');
      await file.parent.create(recursive: true);
      await file.writeAsBytes(dlResp.bodyBytes);
      _webViewController?.evaluateJavascript(source: "showToast('Download selesai: $mp3Title');");
    } catch (_) {
      _webViewController?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final shouldExit = await _handleBackPress();
        if (shouldExit && mounted) SystemNavigator.pop();
      },
      child: Scaffold(
        backgroundColor: const Color(0xFF0a0a0f),
        resizeToAvoidBottomInset: false,
        body: SafeArea(
          top: true,
          bottom: true,
          child: Stack(
            children: [
              InAppWebView(
                keepAlive: _webViewKeepAlive,
                initialUrlRequest: URLRequest(url: WebUri(_apiBase)),
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
                  hardwareAcceleration: true,
                  userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                ),
                onWebViewCreated: (controller) {
                  _webViewController = controller;

                  // Terima callback dari Kotlin (next/prev/completed)
                  _playerChannel.setMethodCallHandler((call) async {
                    switch (call.method) {
                      case 'onNext':
                        controller.evaluateJavascript(
                            source: "if(typeof playNextSimilarSong==='function') playNextSimilarSong();");
                        break;
                      case 'onPrev':
                        controller.evaluateJavascript(
                            source: "if(typeof playPrevSong==='function') playPrevSong();");
                        break;
                      case 'onCompleted':
                        _nativeMode = false;
                        controller.evaluateJavascript(source: '''
                          window._nativePlaying=false;
                          if(typeof isRepeat!=='undefined'&&isRepeat){
                            if(window.currentTrack&&window.currentTrack.videoId){
                              window.flutter_inappwebview.callHandler('playNative',
                                window.currentTrack.videoId,
                                window.currentTrack.title||'',
                                window.currentTrack.artist||'',
                                window.currentTrack.img||'');
                            }
                          } else if(typeof playNextSimilarSong==='function'){
                            playNextSimilarSong();
                          }
                        ''');
                        break;
                    }
                  });

                  // ============================================================
                  // playNative: KIRIM videoId ke service, service fetch URL sendiri
                  // Ini kunci background audio — tidak bergantung Flutter engine
                  // ============================================================
                  controller.addJavaScriptHandler(
                    handlerName: 'playNative',
                    callback: (args) async {
                      final videoId   = args.isNotEmpty ? args[0].toString() : '';
                      final title     = args.length > 1 ? args[1].toString() : '';
                      final artist    = args.length > 2 ? args[2].toString() : '';
                      final thumbnail = args.length > 3 ? args[3].toString() : '';
                      if (videoId.isEmpty) return;

                      controller.evaluateJavascript(source: "window._nativeLoading=true;");

                      try {
                        // Kirim videoId ke service — service yang fetch URL sendiri
                        await _playerChannel.invokeMethod('playByVideoId', {
                          'videoId': videoId,
                          'title': title,
                          'artist': artist,
                          'thumbnail': thumbnail,
                        });
                        _nativeMode = true;
                        WakelockPlus.enable();
                        _startProgressTimer();
                        controller.evaluateJavascript(source: '''
                          window._nativeLoading=false;
                          window._nativePlaying=true;
                          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
                        ''');
                      } catch (_) {
                        _nativeMode = false;
                        controller.evaluateJavascript(source: '''
                          window._nativeLoading=false;
                          window._nativePlaying=false;
                          if(typeof ytPlayer!=='undefined'&&ytPlayer) ytPlayer.loadVideoById('$videoId');
                        ''');
                      }
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'nativePause',
                    callback: (args) async {
                      if (_nativeMode) await _playerChannel.invokeMethod('pause');
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'nativeResume',
                    callback: (args) async {
                      if (_nativeMode) await _playerChannel.invokeMethod('resume');
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'nativeSeek',
                    callback: (args) async {
                      if (_nativeMode && args.isNotEmpty) {
                        final pct = double.tryParse(args[0].toString()) ?? 0;
                        final dur = await _playerChannel.invokeMethod<int>('getDuration') ?? 0;
                        if (dur > 0) {
                          await _playerChannel.invokeMethod('seekTo', {
                            'positionMs': (pct / 100 * dur).round(),
                          });
                        }
                      }
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'isAndroid',
                    callback: (args) => true,
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'downloadTrack',
                    callback: (args) async {
                      final videoId = args.isNotEmpty ? args[0].toString() : '';
                      final title   = args.length > 1 ? args[1].toString() : 'lagu';
                      if (videoId.isNotEmpty) _downloadMp3(videoId, title);
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'openDownload',
                    callback: (args) async {
                      final url = args.isNotEmpty ? args[0].toString() : '';
                      if (url.isNotEmpty) {
                        final uri = Uri.parse(url);
                        if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'getAccountName',
                    callback: (args) async {
                      final prefs = await SharedPreferences.getInstance();
                      return prefs.getString('accountName') ?? '';
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'openGoogleLogin',
                    callback: (args) async {
                      await controller.loadUrl(urlRequest: URLRequest(url: WebUri('$_apiBase/login.html')));
                    },
                  );
                },

                onLoadStart: (controller, url) => setState(() => _isLoading = true),

                onLoadStop: (controller, url) async {
                  setState(() => _isLoading = false);
                  final urlStr = url?.toString() ?? '';

                  if (urlStr.contains('userData=')) {
                    final uri = Uri.parse(urlStr);
                    final userData = uri.queryParameters['userData'];
                    if (userData != null && userData.isNotEmpty) {
                      await controller.evaluateJavascript(source: '''
                        (function(){
                          try {
                            var raw=decodeURIComponent("${Uri.encodeComponent(userData)}");
                            localStorage.setItem('auspotyGoogleUser',raw);
                            var parsed=JSON.parse(raw);
                            if(typeof updateProfileUI==='function') updateProfileUI();
                            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
                            if(typeof showToast==='function') showToast('Selamat datang, '+(parsed.name||'').split(' ')[0]+'!');
                            history.replaceState(null,'','/');
                          } catch(e){ console.error('userData inject error:',e); }
                        })()
                      ''');
                    }
                  }

                  if (urlStr.contains('vercel.app') || urlStr.contains('clone2') || urlStr.isEmpty) {
                    await _injectAll(controller);
                  }
                },

                onCreateWindow: (controller, createWindowAction) async {
                  final url = createWindowAction.request.url?.toString() ?? '';
                  if (url.isNotEmpty && url != 'about:blank') {
                    final uri = Uri.parse(url);
                    if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                  return true;
                },

                onProgressChanged: (controller, progress) {
                  if (progress == 100) setState(() => _isLoading = false);
                },

                onPermissionRequest: (controller, request) async {
                  return PermissionResponse(resources: request.resources, action: PermissionResponseAction.GRANT);
                },

                shouldOverrideUrlLoading: (controller, navigationAction) async {
                  final url = navigationAction.request.url?.toString() ?? '';
                  final allowed = ['vercel.app','youtube.com','ytimg.com','googleapis.com',
                    'gstatic.com','firebaseapp.com','firebase.google.com',
                    'accounts.google.com','google.com','googleusercontent.com'];
                  for (final d in allowed) { if (url.contains(d)) return NavigationActionPolicy.ALLOW; }
                  if (url.startsWith('about:') || url.startsWith('blob:') || url.startsWith('data:')) {
                    return NavigationActionPolicy.ALLOW;
                  }
                  if (url.startsWith('http') && navigationAction.isForMainFrame) {
                    final uri = Uri.parse(url);
                    if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
                    return NavigationActionPolicy.CANCEL;
                  }
                  return NavigationActionPolicy.ALLOW;
                },
              ),

              if (_isLoading)
                Container(
                  color: const Color(0xFF0a0a0f),
                  child: const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.music_note, color: Color(0xFFa78bfa), size: 64),
                        SizedBox(height: 16),
                        Text('Auspoty', style: TextStyle(color: Colors.white, fontSize: 28,
                            fontWeight: FontWeight.bold, letterSpacing: 2)),
                        SizedBox(height: 24),
                        CircularProgressIndicator(color: Color(0xFFa78bfa), strokeWidth: 2),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _injectAll(InAppWebViewController controller) async {
    await controller.evaluateJavascript(source: r'''
      (function(){
        var id='__auspoty_fix__', old=document.getElementById(id);
        if(old) old.remove();
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
    ''');

    await controller.evaluateJavascript(source: '''
      (function(){
        window.AndroidBridge = {
          isAndroid: function(){ return true; },
          openDownload: function(videoId,title){ window.flutter_inappwebview.callHandler('downloadTrack',videoId,title||''); },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          },
          playNative: function(videoId,title,artist,thumbnail){
            window.flutter_inappwebview.callHandler('playNative',videoId,title||'',artist||'',thumbnail||'');
          },
          pauseNative: function(){ window.flutter_inappwebview.callHandler('nativePause'); },
          resumeNative: function(){ window.flutter_inappwebview.callHandler('nativeResume'); },
          seekNative: function(pct){ window.flutter_inappwebview.callHandler('nativeSeek',pct); }
        };

        window._nativePlaying=false;
        window._nativeLoading=false;

        var _origTogglePlay=window.togglePlay;
        window.togglePlay=function(){
          if(window._nativePlaying||window._nativeLoading){
            if(window._nativePlaying){
              window.AndroidBridge.pauseNative();
              window._nativePlaying=false;
              if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(false);
            } else {
              window.AndroidBridge.resumeNative();
              window._nativePlaying=true;
              if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
            }
          } else if(typeof _origTogglePlay==='function'){ _origTogglePlay(); }
        };

        var _origSeekTo=window.seekTo;
        window.seekTo=function(value){
          if(window._nativePlaying||window._nativeLoading){
            window.AndroidBridge.seekNative(value);
          } else if(typeof _origSeekTo==='function'){ _origSeekTo(value); }
        };

        console.log('[Auspoty] Bridge v7.0 self-contained ready');
      })();
    ''');
  }
}
