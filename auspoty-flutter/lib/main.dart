import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:url_launcher/url_launcher.dart';

final FlutterLocalNotificationsPlugin _notif = FlutterLocalNotificationsPlugin();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  const AndroidInitializationSettings androidInit =
      AndroidInitializationSettings('@mipmap/ic_launcher');
  await _notif.initialize(const InitializationSettings(android: androidInit));

  // Status bar transparan, navigation bar tetap ada (tidak edgeToEdge)
  // supaya konten tidak tertutup navigation bar sistem
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

class _AuspotyWebViewState extends State<AuspotyWebView>
    with WidgetsBindingObserver {
  InAppWebViewController? _webViewController;
  bool _isLoading = true;
  Timer? _keepAliveTimer;
  DateTime? _lastBackPress;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _keepAliveTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _webViewController?.evaluateJavascript(source: '''
        (function(){
          if(typeof _bgAudioCtx!=='undefined'&&_bgAudioCtx&&_bgAudioCtx.state==='suspended'){
            _bgAudioCtx.resume();
          }
          if(typeof ytPlayer!=='undefined'&&ytPlayer&&typeof ytPlayer.getPlayerState==='function'){
            var s=ytPlayer.getPlayerState();
            if(s===2&&typeof isPlaying!=='undefined'&&isPlaying){ytPlayer.playVideo();}
          }
        })()
      ''');
    }
  }

  void _startKeepAlive() {
    _keepAliveTimer?.cancel();
    _keepAliveTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _webViewController?.evaluateJavascript(source: '''
        (function(){
          if(typeof ytPlayer!=='undefined'&&ytPlayer&&typeof ytPlayer.getPlayerState==='function'){
            var s=ytPlayer.getPlayerState();
            if(s===0&&!window._bgEndedHandling){
              window._bgEndedHandling=true;
              if(typeof isRepeat!=='undefined'&&isRepeat){
                ytPlayer.seekTo(0);ytPlayer.playVideo();
                setTimeout(function(){window._bgEndedHandling=false;},3000);
              } else if(typeof playNextSimilarSong==='function'){
                playNextSimilarSong();
                setTimeout(function(){window._bgEndedHandling=false;},5000);
              }
            } else if(s===1||s===3){
              window._bgEndedHandling=false;
            } else if(s===2&&typeof isPlaying!=='undefined'&&isPlaying){
              ytPlayer.playVideo();
            }
          }
          if(typeof _bgAudioCtx!=='undefined'&&_bgAudioCtx&&_bgAudioCtx.state==='suspended'){
            _bgAudioCtx.resume();
          }
        })()
      ''');
    });
  }

  void _showNowPlayingNotification(String title, String artist) async {
    const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
      'auspoty_music',
      'Musik Sedang Diputar',
      channelDescription: 'Notifikasi musik Auspoty',
      importance: Importance.low,
      priority: Priority.low,
      ongoing: true,
      playSound: false,
      enableVibration: false,
      icon: '@mipmap/ic_launcher',
    );
    await _notif.show(
      1, title, artist,
      const NotificationDetails(android: androidDetails),
    );
  }

  Future<bool> _handleBackPress() async {
    if (_webViewController == null) return true;

    final result = await _webViewController!.evaluateJavascript(source: '''
      (function(){
        var modals = ['playerModal','lyricsModal','editProfileModal','createPlaylistModal','addToPlaylistModal','commentsModal','pickerModal'];
        for(var i=0;i<modals.length;i++){
          var el = document.getElementById(modals[i]);
          if(el && el.style.display !== 'none' && el.style.display !== '') return 'modal:'+modals[i];
        }
        var active = document.querySelector('.view-section.active');
        var viewId = active ? active.id : 'view-home';
        return viewId;
      })()
    ''');

    final viewStr = (result ?? 'view-home').replaceAll('"', '').trim();

    if (viewStr.startsWith('modal:')) {
      final modalId = viewStr.split(':')[1];
      await _webViewController!.evaluateJavascript(source: '''
        (function(){
          var el = document.getElementById('$modalId');
          if(el) el.style.display = 'none';
          if('$modalId' === 'lyricsModal') {
            if(typeof closeLyricsToPlayer === 'function') closeLyricsToPlayer();
            else if(typeof closeLyrics === 'function') closeLyrics();
          }
        })()
      ''');
      return false;
    }

    final mainViews = ['view-home', 'view-search', 'view-library', 'view-settings'];
    if (!mainViews.contains(viewStr)) {
      await _webViewController!.evaluateJavascript(
        source: "if(typeof switchView==='function') switchView('home');",
      );
      return false;
    }

    final now = DateTime.now();
    if (_lastBackPress == null || now.difference(_lastBackPress!) > const Duration(seconds: 2)) {
      _lastBackPress = now;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Tekan sekali lagi untuk keluar'),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
      return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final shouldExit = await _handleBackPress();
        if (shouldExit && mounted) {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFF0a0a0f),
        resizeToAvoidBottomInset: false,
        // TIDAK pakai SafeArea — biarkan WebView handle sendiri via CSS
        // Tapi kita inject CSS yang benar
        body: Stack(
          children: [
            InAppWebView(
              initialUrlRequest: URLRequest(
                url: WebUri('https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app'),
              ),
              initialSettings: InAppWebViewSettings(
                javaScriptEnabled: true,
                domStorageEnabled: true,
                databaseEnabled: true,
                mediaPlaybackRequiresUserGesture: false,
                allowFileAccessFromFileURLs: false,
                allowUniversalAccessFromFileURLs: false,
                mixedContentMode: MixedContentMode.MIXED_CONTENT_ALWAYS_ALLOW,
                useWideViewPort: true,
                loadWithOverviewMode: true,
                supportZoom: false,
                builtInZoomControls: false,
                displayZoomControls: false,
                cacheMode: CacheMode.LOAD_DEFAULT,
                hardwareAcceleration: true,
                transparentBackground: false,
                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 AuspotyApp/3.0',
              ),
              onWebViewCreated: (controller) {
                _webViewController = controller;

                controller.addJavaScriptHandler(
                  handlerName: 'onMusicPlay',
                  callback: (args) {
                    final title = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist = args.length > 1 ? args[1].toString() : '';
                    WakelockPlus.enable();
                    _showNowPlayingNotification(title, artist);
                    _startKeepAlive();
                  },
                );

                controller.addJavaScriptHandler(
                  handlerName: 'onMusicPause',
                  callback: (args) => WakelockPlus.disable(),
                );

                controller.addJavaScriptHandler(
                  handlerName: 'isAndroid',
                  callback: (args) => true,
                );

                // Download — buka di browser eksternal
                controller.addJavaScriptHandler(
                  handlerName: 'openDownload',
                  callback: (args) async {
                    final url = args.isNotEmpty ? args[0].toString() : '';
                    if (url.isNotEmpty) {
                      final uri = Uri.parse(url);
                      await launchUrl(uri, mode: LaunchMode.externalApplication);
                    }
                  },
                );

                // Login Google — buka browser eksternal untuk pilih akun
                controller.addJavaScriptHandler(
                  handlerName: 'openGoogleLogin',
                  callback: (args) async {
                    // Trigger Firebase signInWithPopup di WebView
                    await _webViewController?.evaluateJavascript(source: '''
                      if(typeof window._firebaseSignIn === 'function') {
                        window._firebaseSignIn();
                      }
                    ''');
                  },
                );

                controller.addJavaScriptHandler(
                  handlerName: 'getAccountName',
                  callback: (args) async {
                    final prefs = await SharedPreferences.getInstance();
                    return prefs.getString('accountName') ?? '';
                  },
                );
              },
              onLoadStart: (controller, url) {
                setState(() => _isLoading = true);
              },
              onLoadStop: (controller, url) async {
                setState(() => _isLoading = false);
                await _injectBridge(controller);
              },
              onProgressChanged: (controller, progress) {
                if (progress == 100) setState(() => _isLoading = false);
              },
              onPermissionRequest: (controller, request) async {
                return PermissionResponse(
                  resources: request.resources,
                  action: PermissionResponseAction.GRANT,
                );
              },
              shouldOverrideUrlLoading: (controller, navigationAction) async {
                final url = navigationAction.request.url?.toString() ?? '';
                if (url.contains('vercel.app') ||
                    url.contains('youtube.com') ||
                    url.contains('ytimg.com') ||
                    url.contains('googleapis.com') ||
                    url.contains('gstatic.com') ||
                    url.contains('firebaseapp.com') ||
                    url.contains('firebase.google.com') ||
                    url.contains('accounts.google.com') ||
                    url.contains('google.com/recaptcha') ||
                    url.startsWith('about:')) {
                  return NavigationActionPolicy.ALLOW;
                }
                if (url.startsWith('http') && navigationAction.isForMainFrame) {
                  final uri = Uri.parse(url);
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
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
                      Text(
                        'Auspoty',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 2,
                        ),
                      ),
                      SizedBox(height: 24),
                      CircularProgressIndicator(
                        color: Color(0xFFa78bfa),
                        strokeWidth: 2,
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _injectBridge(InAppWebViewController controller) async {
    // FIX UTAMA: Inject CSS langsung — override bottom-nav supaya tidak overlap konten
    await controller.evaluateJavascript(source: r'''
      (function(){
        var id = '__flutter_nav_fix__';
        var old = document.getElementById(id);
        if(old) old.remove();
        var s = document.createElement('style');
        s.id = id;
        s.textContent = `
          /* FIX: bottom-nav tidak overlap konten */
          .bottom-nav {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            height: 60px !important;
            min-height: 60px !important;
            display: flex !important;
            justify-content: space-around !important;
            align-items: center !important;
            padding: 0 !important;
            background: rgba(10,10,15,0.95) !important;
            backdrop-filter: blur(30px) !important;
            -webkit-backdrop-filter: blur(30px) !important;
            border-top: 1px solid rgba(255,255,255,0.1) !important;
            z-index: 1000 !important;
          }
          .nav-item {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 3px !important;
            font-size: 10px !important;
            min-width: 60px !important;
            height: 60px !important;
            cursor: pointer !important;
            color: rgba(255,255,255,0.5) !important;
          }
          .nav-item.active { color: #a78bfa !important; }
          .nav-item svg { width: 22px !important; height: 22px !important; fill: currentColor !important; }
          /* FIX: body padding supaya konten tidak tertutup nav */
          body { padding-bottom: 140px !important; }
          /* FIX: mini player di atas nav */
          .mini-player {
            bottom: 68px !important;
          }
          /* FIX: toast di atas nav */
          .toast-notification.show { bottom: 80px !important; }
        `;
        document.head.appendChild(s);
      })();
    ''');

    // Inject AndroidBridge
    await controller.evaluateJavascript(source: '''
      window.AndroidBridge = {
        onMusicPlay: function(title, artist) {
          window.flutter_inappwebview.callHandler('onMusicPlay', title, artist);
        },
        onMusicPause: function() {
          window.flutter_inappwebview.callHandler('onMusicPause');
        },
        isAndroid: function() { return true; },
        openDownload: function(url) {
          window.flutter_inappwebview.callHandler('openDownload', url);
        },
        openGoogleLogin: function() {
          window.flutter_inappwebview.callHandler('openGoogleLogin');
        },
        logout: function() {
          localStorage.removeItem('auspotyGoogleUser');
          if(typeof updateProfileUI==='function') updateProfileUI();
          if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
        }
      };

      // Override downloadMusic
      window.downloadMusic = function() {
        if(!window.currentTrack){
          if(typeof showToast==='function') showToast('Putar lagu dulu!');
          return;
        }
        var url = 'https://id.ytmp3.mobi/v1/#' + window.currentTrack.videoId;
        window.AndroidBridge.openDownload(url);
        if(typeof showToast==='function') showToast('Membuka halaman download...');
      };

      console.log('AndroidBridge injected v3.0');
    ''');
  }
}
