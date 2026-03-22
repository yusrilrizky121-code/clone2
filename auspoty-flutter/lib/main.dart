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

  /// Update progress bar di JS dari posisi MediaPlayer native
  void _startProgressTimer() {
    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      try {
        final pos = await _ch.invokeMethod<int>('getPosition') ?? 0;
        final dur = await _ch.invokeMethod<int>('getDuration') ?? 0;
        if (dur > 0 && _wvc != null) {
          await _wvc!.evaluateJavascript(source: """
            (function(){
              var pb = document.getElementById('progressBar');
              var ct = document.getElementById('currentTime');
              var tt = document.getElementById('totalTime');
              if(pb) pb.value = $pos;
              if(pb) pb.max = $dur;
              if(ct) ct.innerText = _fmtTime($pos);
              if(tt) tt.innerText = _fmtTime($dur);
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
    try {
      final t2 = title.replaceAll("'", "\\'");
      _wvc?.evaluateJavascript(source: "showToast('Mengunduh... tunggu 30-60 detik');");
      if (Platform.isAndroid) await Permission.storage.request();

      // Step 1: POST ke API untuk dapat URL mp3
      final apiRes = await http.post(
        Uri.parse('$_base/api/download'),
        headers: {'Content-Type': 'application/json'},
        body: '{"videoId":"$videoId"}',
      ).timeout(const Duration(seconds: 90));

      if (apiRes.statusCode != 200) throw Exception('API ${apiRes.statusCode}');
      final apiJson = json.decode(apiRes.body) as Map<String, dynamic>;
      if (apiJson['status'] != 'success') throw Exception(apiJson['message']?.toString() ?? 'failed');

      final mp3Url   = apiJson['url'] as String;
      final mp3Title = (apiJson['title'] as String?) ?? title;

      // Step 2: Download file MP3
      final dl = await http.get(Uri.parse(mp3Url)).timeout(const Duration(seconds: 120));
      if (dl.statusCode != 200) throw Exception('DL ${dl.statusCode}');

      // Step 3: Simpan ke folder Download
      final dir  = await getExternalStorageDirectory();
      final base = dir?.path.replaceAll(RegExp(r'Android.*'), '') ?? '/storage/emulated/0/';
      final safe = mp3Title.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
      final f    = File('${base}Download/$safe.mp3');
      await f.parent.create(recursive: true);
      await f.writeAsBytes(dl.bodyBytes);

      _wvc?.evaluateJavascript(source: "showToast('\u2713 Download selesai: $t2');");
    } catch (e) {
      _wvc?.evaluateJavascript(source: "showToast('Download gagal, coba lagi');");
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
