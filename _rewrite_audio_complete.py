import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ── 1. main.dart ─────────────────────────────────────────────────────────────
main_dart = r'''import 'dart:async';
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
import 'package:audio_service/audio_service.dart';
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

  _audioHandler = await AudioService.init(
    builder: () => AuspotyAudioHandler(),
    config: const AudioServiceConfig(
      androidNotificationChannelId: 'com.auspoty.app.audio',
      androidNotificationChannelName: 'Auspoty Music',
      androidNotificationOngoing: true,
      androidStopForegroundOnPause: false,
      notificationColor: Color(0xFFa78bfa),
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
  StreamSubscription? _positionSub;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // Callback next/prev dari notifikasi
    _audioHandler.onSkipToNext = () {
      _wvc?.evaluateJavascript(source: "if(typeof playNextSimilarSong==='function') playNextSimilarSong();");
    };
    _audioHandler.onSkipToPrevious = () {
      _wvc?.evaluateJavascript(source: "if(typeof playPrevSong==='function') playPrevSong();");
    };
    _audioHandler.onPlayPauseToggle = () {
      _wvc?.evaluateJavascript(source: "(function(){ if(typeof togglePlay==='function') togglePlay(); })();");
    };

    // Update progress bar di JS setiap detik
    _positionSub = _audioHandler.positionStream.listen((pos) {
      final dur = _audioHandler.durationSeconds;
      if (dur > 0 && _wvc != null) {
        final posS = pos.inSeconds;
        _wvc!.evaluateJavascript(source: """
          (function(){
            if(typeof window._updateNativeProgress==='function') window._updateNativeProgress($posS, $dur);
          })();
        """);
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _positionSub?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      WakelockPlus.enable();
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

                // JS memanggil ini saat lagu mulai play
                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final videoId = args.length > 2 ? args[2].toString() : '';
                    WakelockPlus.enable();
                    if (videoId.isNotEmpty) {
                      await _playNative(videoId, title, artist);
                    }
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicPaused',
                  callback: (args) async {
                    await _audioHandler.pause();
                  },
                );

                c.addJavaScriptHandler(
                  handlerName: 'onMusicResumed',
                  callback: (args) async {
                    await _audioHandler.play();
                  },
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

  /// Fetch stream URL dari API lalu putar via just_audio (background-safe)
  Future<void> _playNative(String videoId, String title, String artist) async {
    try {
      final resp = await http.get(
        Uri.parse('$_base/api/stream?videoId=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36'},
      ).timeout(const Duration(seconds: 20));

      if (resp.statusCode != 200) return;
      final body = resp.body;
      final urlMatch = RegExp(r'"url"\s*:\s*"([^"]+)"').firstMatch(body);
      if (urlMatch == null) return;
      final streamUrl = urlMatch.group(1)!.replaceAll(r'\/', '/');

      final item = MediaItem(
        id: videoId,
        title: title.isEmpty ? 'Auspoty' : title,
        artist: artist.isEmpty ? 'Auspoty Music' : artist,
      );

      await _audioHandler.playFromUrl(streamUrl, item);

      // Beritahu JS bahwa playback sudah mulai
      _wvc?.evaluateJavascript(source: """
        (function(){
          window._nativePlaying = true;
          window._nativeLoading = false;
          if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
        })();
      """);
    } catch (e) {
      // ignore
    }
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

        // Update progress bar dari native
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
'''

# ── 2. audio_handler.dart ────────────────────────────────────────────────────
audio_handler = r'''import 'package:audio_service/audio_service.dart';
import 'package:just_audio/just_audio.dart';

class AuspotyAudioHandler extends BaseAudioHandler with SeekHandler {
  final _player = AudioPlayer();

  // Callbacks untuk next/prev/playpause dari notifikasi
  void Function()? onSkipToNext;
  void Function()? onSkipToPrevious;
  void Function()? onPlayPauseToggle;

  AuspotyAudioHandler() {
    _player.playbackEventStream.map(_transformEvent).pipe(playbackState);

    _player.processingStateStream.listen((state) {
      if (state == ProcessingState.completed) {
        onSkipToNext?.call();
      }
    });
  }

  Future<void> playFromUrl(String url, MediaItem item) async {
    mediaItem.add(item);
    try {
      await _player.setAudioSource(
        AudioSource.uri(
          Uri.parse(url),
          headers: {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://www.youtube.com/',
          },
        ),
      );
      await _player.play();
    } catch (_) {}
  }

  @override
  Future<void> play() => _player.play();

  @override
  Future<void> pause() => _player.pause();

  @override
  Future<void> stop() async {
    await _player.stop();
    await super.stop();
  }

  @override
  Future<void> seek(Duration position) => _player.seek(position);

  @override
  Future<void> skipToNext() async => onSkipToNext?.call();

  @override
  Future<void> skipToPrevious() async => onSkipToPrevious?.call();

  int get durationSeconds => _player.duration?.inSeconds ?? 0;
  Stream<Duration> get positionStream => _player.positionStream;
  bool get isPlaying => _player.playing;

  PlaybackState _transformEvent(PlaybackEvent event) {
    return PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        if (_player.playing) MediaControl.pause else MediaControl.play,
        MediaControl.skipToNext,
      ],
      systemActions: const {
        MediaAction.seek,
      },
      androidCompactActionIndices: const [0, 1, 2],
      processingState: const {
        ProcessingState.idle: AudioProcessingState.idle,
        ProcessingState.loading: AudioProcessingState.loading,
        ProcessingState.buffering: AudioProcessingState.buffering,
        ProcessingState.ready: AudioProcessingState.ready,
        ProcessingState.completed: AudioProcessingState.completed,
      }[_player.processingState]!,
      playing: _player.playing,
      updatePosition: _player.position,
      bufferedPosition: _player.bufferedPosition,
      speed: _player.speed,
    );
  }
}
'''

# ── 3. AndroidManifest.xml ───────────────────────────────────────────────────
manifest = r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />

    <application
        android:label="Auspoty"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="false"
        android:usesCleartextTraffic="false"
        android:allowAudioPlaybackCapture="true"
        android:hardwareAccelerated="true"
        android:networkSecurityConfig="@xml/network_security_config">

        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:hardwareAccelerated="true"
            android:screenOrientation="portrait"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

        <!-- audio_service background service -->
        <service
            android:name="com.ryanheise.audioservice.AudioService"
            android:exported="false"
            android:foregroundServiceType="mediaPlayback"
            android:stopWithTask="false">
            <intent-filter>
                <action android:name="android.media.browse.MediaBrowserService" />
            </intent-filter>
        </service>

        <!-- audio_service receiver -->
        <receiver
            android:name="com.ryanheise.audioservice.MediaButtonReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MEDIA_BUTTON" />
            </intent-filter>
        </receiver>

        <!-- MusicPlayerService tetap ada untuk backward compat -->
        <service
            android:name=".MusicPlayerService"
            android:exported="false"
            android:stopWithTask="false"
            android:foregroundServiceType="mediaPlayback" />

    </application>

</manifest>
'''

# Write files
with open(r'auspoty-flutter\lib\main.dart', 'w', encoding='utf-8') as f:
    f.write(main_dart)
print("main.dart written")

with open(r'auspoty-flutter\lib\audio_handler.dart', 'w', encoding='utf-8') as f:
    f.write(audio_handler)
print("audio_handler.dart written")

with open(r'auspoty-flutter\android\app\src\main\AndroidManifest.xml', 'w', encoding='utf-8') as f:
    f.write(manifest)
print("AndroidManifest.xml written")

print("All files written successfully!")
