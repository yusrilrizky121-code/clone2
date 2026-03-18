import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;

const _musicChannel = MethodChannel('com.auspoty.app/music');

final FlutterLocalNotificationsPlugin _notif = FlutterLocalNotificationsPlugin();

// Callback untuk aksi notifikasi (play/pause dari notifikasi)
@pragma('vm:entry-point')
void notificationTapBackground(NotificationResponse response) {}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  const AndroidInitializationSettings androidInit =
      AndroidInitializationSettings('@mipmap/ic_launcher');
  await _notif.initialize(
    const InitializationSettings(android: androidInit),
    onDidReceiveNotificationResponse: (response) {
      // Aksi dari notifikasi — diteruskan ke WebView via channel
      _handleNotifAction(response.actionId);
    },
    onDidReceiveBackgroundNotificationResponse: notificationTapBackground,
  );

  // Buat notification channel untuk musik
  const AndroidNotificationChannel musicChannel = AndroidNotificationChannel(
    'auspoty_music',
    'Musik Sedang Diputar',
    description: 'Kontrol musik Auspoty',
    importance: Importance.low,
    playSound: false,
    enableVibration: false,
  );
  await _notif
      .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
      ?.createNotificationChannel(musicChannel);

  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(0xFF0a0a0f),
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  runApp(const AuspotyApp());
}

// Global reference ke WebView controller untuk aksi notifikasi
InAppWebViewController? _globalWebController;
bool _globalIsPlaying = false;

void _handleNotifAction(String? actionId) {
  if (_globalWebController == null) return;
  switch (actionId) {
    case 'play_pause':
      if (_globalIsPlaying) {
        _globalWebController!.evaluateJavascript(
            source: "if(typeof ytPlayer!=='undefined'&&ytPlayer) ytPlayer.pauseVideo();");
      } else {
        _globalWebController!.evaluateJavascript(
            source: "if(typeof ytPlayer!=='undefined'&&ytPlayer) ytPlayer.playVideo();");
      }
      break;
    case 'next':
      _globalWebController!.evaluateJavascript(
          source: "if(typeof playNextSimilarSong==='function') playNextSimilarSong();");
      break;
    case 'prev':
      _globalWebController!.evaluateJavascript(
          source: "if(typeof playPrevSong==='function') playPrevSong(); else if(typeof songHistory!=='undefined'&&songHistory.length>1){ var t=songHistory[songHistory.length-2]; if(t) playMusicById(t.videoId); }");
      break;
  }
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
  bool _wasInBackground = false;
  Timer? _keepAliveTimer;
  DateTime? _lastBackPress;

  String _nowTitle = 'Auspoty';
  String _nowArtist = '';

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
    if (state == AppLifecycleState.paused) {
      _wasInBackground = true;
      _musicChannel.invokeMethod('keepWebViewAlive').catchError((_) {});
    }
    if (state == AppLifecycleState.resumed && _wasInBackground) {
      _wasInBackground = false;
      _webViewController?.evaluateJavascript(source: '''
        (function(){
          if(window._keepAliveCtx && window._keepAliveCtx.state === 'suspended'){
            window._keepAliveCtx.resume();
          }
          if(typeof ytPlayer !== 'undefined' && ytPlayer && typeof ytPlayer.getPlayerState === 'function'){
            var s = ytPlayer.getPlayerState();
            if(s === 2 && typeof isPlaying !== 'undefined' && isPlaying) ytPlayer.playVideo();
          }
        })()
      ''');
    }
  }

  void _startKeepAlive() {
    _keepAliveTimer?.cancel();
    _keepAliveTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      _webViewController?.evaluateJavascript(source: '''
        (function(){
          if(window._keepAliveCtx && window._keepAliveCtx.state === 'suspended'){
            window._keepAliveCtx.resume();
          }
          if(typeof ytPlayer !== 'undefined' && ytPlayer && typeof ytPlayer.getPlayerState === 'function'){
            var s = ytPlayer.getPlayerState();
            if(s === 0 && !window._bgEndedHandling){
              window._bgEndedHandling = true;
              if(typeof isRepeat !== 'undefined' && isRepeat){
                ytPlayer.seekTo(0); ytPlayer.playVideo();
                setTimeout(function(){ window._bgEndedHandling = false; }, 3000);
              } else if(typeof playNextSimilarSong === 'function'){
                playNextSimilarSong();
                setTimeout(function(){ window._bgEndedHandling = false; }, 5000);
              }
            } else if(s === 1 || s === 3){
              window._bgEndedHandling = false;
            } else if(s === 2 && typeof isPlaying !== 'undefined' && isPlaying){
              ytPlayer.playVideo();
            }
          }
        })()
      ''');
    });
  }

  // Tampilkan notifikasi dengan tombol prev/play-pause/next
  Future<void> _showMusicNotification(String title, String artist, bool playing) async {
    final playPauseIcon = playing
        ? '@android:drawable/ic_media_pause'
        : '@android:drawable/ic_media_play';
    final playPauseLabel = playing ? 'Pause' : 'Play';

    final androidDetails = AndroidNotificationDetails(
      'auspoty_music',
      'Musik Sedang Diputar',
      channelDescription: 'Kontrol musik Auspoty',
      importance: Importance.low,
      priority: Priority.low,
      ongoing: true,
      playSound: false,
      enableVibration: false,
      icon: '@mipmap/ic_launcher',
      styleInformation: const MediaStyleInformation(
        htmlFormatContent: false,
        htmlFormatTitle: false,
      ),
      actions: [
        AndroidNotificationAction(
          'prev',
          'Sebelumnya',
          icon: DrawableResourceAndroidBitmap('@android:drawable/ic_media_previous'),
          showsUserInterface: false,
          cancelNotification: false,
        ),
        AndroidNotificationAction(
          'play_pause',
          playPauseLabel,
          icon: DrawableResourceAndroidBitmap(playPauseIcon),
          showsUserInterface: false,
          cancelNotification: false,
        ),
        AndroidNotificationAction(
          'next',
          'Berikutnya',
          icon: DrawableResourceAndroidBitmap('@android:drawable/ic_media_next'),
          showsUserInterface: false,
          cancelNotification: false,
        ),
      ],
    );

    await _notif.show(
      1,
      title,
      artist,
      NotificationDetails(android: androidDetails),
    );
  }

  // Download MP3 langsung ke storage tanpa buka browser
  Future<void> _downloadMp3(String videoId, String title) async {
    // Minta izin storage
    if (Platform.isAndroid) {
      final status = await Permission.storage.request();
      if (!status.isGranted) {
        // Android 13+ tidak perlu storage permission untuk Downloads folder
        // Lanjut saja
      }
    }

    // Tampilkan notifikasi progress download
    await _notif.show(
      2,
      'Mengunduh...',
      title,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'auspoty_download',
          'Download Musik',
          channelDescription: 'Progress download lagu',
          importance: Importance.low,
          priority: Priority.low,
          ongoing: true,
          playSound: false,
          enableVibration: false,
          showProgress: true,
          maxProgress: 100,
          progress: 0,
          icon: '@mipmap/ic_launcher',
        ),
      ),
    );

    try {
      // Panggil API download untuk dapat URL MP3
      final apiUrl = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/download';
      final apiResp = await http.post(
        Uri.parse(apiUrl),
        headers: {'Content-Type': 'application/json'},
        body: '{"videoId":"$videoId"}',
      ).timeout(const Duration(seconds: 60));

      if (apiResp.statusCode != 200) {
        throw Exception('API error ${apiResp.statusCode}');
      }

      final body = apiResp.body;
      // Parse JSON manual (hindari import dart:convert yang berat)
      final urlMatch = RegExp(r'"url"\s*:\s*"([^"]+)"').firstMatch(body);
      final titleMatch = RegExp(r'"title"\s*:\s*"([^"]+)"').firstMatch(body);
      if (urlMatch == null) throw Exception('URL tidak ditemukan');

      final mp3Url = urlMatch.group(1)!.replaceAll(r'\/', '/');
      final mp3Title = titleMatch?.group(1) ?? title;

      // Update notifikasi progress
      await _notif.show(
        2,
        'Mengunduh...',
        mp3Title,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'auspoty_download',
            'Download Musik',
            importance: Importance.low,
            priority: Priority.low,
            ongoing: true,
            playSound: false,
            enableVibration: false,
            showProgress: true,
            maxProgress: 100,
            progress: 50,
            icon: '@mipmap/ic_launcher',
          ),
        ),
      );

      // Download file MP3
      final dlResp = await http.get(Uri.parse(mp3Url)).timeout(const Duration(seconds: 120));
      if (dlResp.statusCode != 200) throw Exception('Download gagal ${dlResp.statusCode}');

      // Simpan ke Downloads folder
      final dir = await getExternalStorageDirectory();
      final downloadsPath = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final savePath = '${downloadsPath}Download/${_sanitizeFilename(mp3Title)}.mp3';
      final file = File(savePath);
      await file.parent.create(recursive: true);
      await file.writeAsBytes(dlResp.bodyBytes);

      // Notifikasi selesai
      await _notif.cancel(2);
      await _notif.show(
        3,
        'Download selesai',
        mp3Title,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'auspoty_download',
            'Download Musik',
            importance: Importance.defaultImportance,
            priority: Priority.defaultPriority,
            playSound: true,
            icon: '@mipmap/ic_launcher',
          ),
        ),
      );

      // Beritahu WebView
      _webViewController?.evaluateJavascript(
          source: "showToast('Download selesai: $mp3Title');");

    } catch (e) {
      await _notif.cancel(2);
      await _notif.show(
        3,
        'Download gagal',
        e.toString().length > 60 ? e.toString().substring(0, 60) : e.toString(),
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'auspoty_download',
            'Download Musik',
            importance: Importance.defaultImportance,
            priority: Priority.defaultPriority,
            icon: '@mipmap/ic_launcher',
          ),
        ),
      );
      _webViewController?.evaluateJavascript(
          source: "showToast('Download gagal, coba lagi');");
    }
  }

  String _sanitizeFilename(String name) {
    return name.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_').trim();
  }

  Future<bool> _handleBackPress() async {
    if (_webViewController == null) return true;
    final result = await _webViewController!.evaluateJavascript(source: '''
      (function(){
        var modals = ['playerModal','lyricsModal','editProfileModal','createPlaylistModal','addToPlaylistModal','commentsModal','pickerModal'];
        for(var i = 0; i < modals.length; i++){
          var el = document.getElementById(modals[i]);
          if(el && el.style.display !== 'none' && el.style.display !== '') return 'modal:' + modals[i];
        }
        var active = document.querySelector('.view-section.active');
        return active ? active.id : 'view-home';
      })()
    ''');
    final viewStr = (result ?? 'view-home').replaceAll('"', '').trim();

    if (viewStr.startsWith('modal:')) {
      final modalId = viewStr.split(':')[1];
      await _webViewController!.evaluateJavascript(source: '''
        (function(){
          var el = document.getElementById('$modalId');
          if(el) el.style.display = 'none';
          if('$modalId' === 'lyricsModal'){
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
          source: "if(typeof switchView === 'function') switchView('home');");
      return false;
    }

    final now = DateTime.now();
    if (_lastBackPress == null ||
        now.difference(_lastBackPress!) > const Duration(seconds: 2)) {
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
                  userAgent:
                      'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                ),
                onWebViewCreated: (controller) {
                  _webViewController = controller;
                  _globalWebController = controller;

                  controller.addJavaScriptHandler(
                    handlerName: 'onMusicPlay',
                    callback: (args) {
                      final title = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                      final artist = args.length > 1 ? args[1].toString() : '';
                      _nowTitle = title;
                      _nowArtist = artist;
                      _globalIsPlaying = true;
                      WakelockPlus.enable();
                      _showMusicNotification(title, artist, true);
                      _startKeepAlive();
                      _musicChannel.invokeMethod('startMusicService', {
                        'title': title,
                        'artist': artist,
                      }).catchError((_) {});
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'onMusicPause',
                    callback: (args) {
                      _globalIsPlaying = false;
                      WakelockPlus.disable();
                      _showMusicNotification(_nowTitle, _nowArtist, false);
                    },
                  );

                  controller.addJavaScriptHandler(
                    handlerName: 'isAndroid',
                    callback: (args) => true,
                  );

                  // Download langsung ke storage — tidak buka browser
                  controller.addJavaScriptHandler(
                    handlerName: 'downloadTrack',
                    callback: (args) async {
                      final videoId = args.isNotEmpty ? args[0].toString() : '';
                      final title = args.length > 1 ? args[1].toString() : 'lagu';
                      if (videoId.isNotEmpty) {
                        _downloadMp3(videoId, title);
                      }
                    },
                  );

                  // Fallback openDownload (buka browser) — tetap ada untuk web
                  controller.addJavaScriptHandler(
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
                      // Buka login.html di Chrome — Chrome bisa handle Google popup
                      const loginUrl = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/login.html';
                      final uri = Uri.parse(loginUrl);
                      if (await canLaunchUrl(uri)) {
                        await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                  );
                },

                onLoadStart: (controller, url) {
                  setState(() => _isLoading = true);
                },

                onLoadStop: (controller, url) async {
                  setState(() => _isLoading = false);
                  final urlStr = url?.toString() ?? '';
                  if (urlStr.contains('vercel.app') || urlStr.contains('clone2') || urlStr.isEmpty) {
                    await _injectAll(controller);
                  }
                },
                onCreateWindow: (controller, createWindowAction) async {
                  // Handle popup dari signInWithPopup Firebase
                  final url = createWindowAction.request.url?.toString() ?? '';
                  if (url.isNotEmpty && url != 'about:blank') {
                    final uri = Uri.parse(url);
                    if (await canLaunchUrl(uri)) {
                      await launchUrl(uri, mode: LaunchMode.externalApplication);
                    }
                  }
                  return true;
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

                  final allowedInWebView = [
                    'vercel.app', 'youtube.com', 'ytimg.com',
                    'googleapis.com', 'gstatic.com', 'firebaseapp.com',
                    'firebase.google.com', 'accounts.google.com',
                    'google.com', 'googleusercontent.com',
                  ];

                  for (final domain in allowedInWebView) {
                    if (url.contains(domain)) return NavigationActionPolicy.ALLOW;
                  }

                  if (url.startsWith('about:') || url.startsWith('blob:') || url.startsWith('data:')) {
                    return NavigationActionPolicy.ALLOW;
                  }

                  if (url.startsWith('http') && navigationAction.isForMainFrame) {
                    final uri = Uri.parse(url);
                    if (await canLaunchUrl(uri)) {
                      await launchUrl(uri, mode: LaunchMode.externalApplication);
                    }
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
                        Text('Auspoty',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 28,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 2)),
                        SizedBox(height: 24),
                        CircularProgressIndicator(
                            color: Color(0xFFa78bfa), strokeWidth: 2),
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
    // CSS fix nav bar
    await controller.evaluateJavascript(source: r'''
      (function(){
        var id = '__auspoty_fix__';
        var old = document.getElementById(id);
        if(old) old.remove();
        var s = document.createElement('style');
        s.id = id;
        s.textContent = `
          .bottom-nav {
            position: fixed !important; bottom: 0 !important;
            left: 0 !important; right: 0 !important;
            height: 60px !important; display: flex !important;
            justify-content: space-around !important; align-items: center !important;
            padding: 0 !important; background: rgba(10,10,15,0.95) !important;
            backdrop-filter: blur(30px) !important;
            border-top: 1px solid rgba(255,255,255,0.1) !important;
            z-index: 1000 !important;
          }
          .nav-item {
            display: flex !important; flex-direction: column !important;
            align-items: center !important; justify-content: center !important;
            gap: 3px !important; font-size: 10px !important;
            min-width: 60px !important; height: 60px !important;
            cursor: pointer !important; color: rgba(255,255,255,0.5) !important;
          }
          .nav-item.active { color: #a78bfa !important; }
          .nav-item svg { width: 22px !important; height: 22px !important; fill: currentColor !important; }
          body { padding-bottom: 160px !important; }
          .mini-player { bottom: 68px !important; }
          .toast-notification.show { bottom: 80px !important; }
        `;
        document.head.appendChild(s);
      })();
    ''');

    // AndroidBridge + AudioContext keep-alive
    await controller.evaluateJavascript(source: '''
      (function(){
        window.AndroidBridge = {
          onMusicPlay: function(t, a){
            window.flutter_inappwebview.callHandler('onMusicPlay', t, a);
          },
          onMusicPause: function(){
            window.flutter_inappwebview.callHandler('onMusicPause');
          },
          isAndroid: function(){ return true; },
          // Download langsung ke storage — panggil handler downloadTrack
          openDownload: function(videoId, title){
            window.flutter_inappwebview.callHandler('downloadTrack', videoId, title || '');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI === 'function') updateProfileUI();
            if(typeof updateGoogleLoginUI === 'function') updateGoogleLoginUI();
          }
        };

        // AudioContext keep-alive
        if(!window._auspotyKeepAlive){
          window._auspotyKeepAlive = true;
          try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            gain.gain.value = 0.00001;
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            window._keepAliveCtx = ctx;
          } catch(e) {}
        }

        console.log('[Auspoty] Bridge v3.2 ready');
      })();
    ''');
  }
}
