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
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:image_picker/image_picker.dart';

const _ch = MethodChannel('com.auspoty.app/music');
final _keepAlive = InAppWebViewKeepAlive();
const _base = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';

// Local file server for WebView audio
HttpServer? _fileServer;
String? _servedFilePath;
int _fileServerPort = 8765;

Future<void> _startFileServer() async {
  if (_fileServer != null) return;
  // Coba beberapa port kalau 8765 sudah dipakai
  for (final port in [8765, 8766, 8767, 8768]) {
    try {
      _fileServer = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
      _fileServerPort = port;
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
        req.response.headers.set('Cache-Control', 'no-cache');
        final rangeHeader = req.headers.value('range');
        if (rangeHeader != null && rangeHeader.startsWith('bytes=')) {
          final parts = rangeHeader.substring(6).split('-');
          final start = int.tryParse(parts[0]) ?? 0;
          final end   = (parts.length > 1 && parts[1].isNotEmpty)
              ? (int.tryParse(parts[1]) ?? (total - 1)) : (total - 1);
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
      break; // berhasil bind
    } catch (_) { _fileServer = null; }
  }
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
  bool _isOffline = false;
  bool _announcementChecked = false;
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
      // Cek pengumuman baru setiap kali app dibuka kembali
      _checkAnnouncement();
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

  void _startProgressTimer() {}

  // Cek pengumuman dari server saat app load
  Future<void> _checkAnnouncement() async {
    try {
      final res = await http.get(
        Uri.parse('$_base/api/announcement'),
        headers: {'User-Agent': 'AuspotyApp/1.0'},
      ).timeout(const Duration(seconds: 20));
      if (res.statusCode != 200) return;
      final data = json.decode(res.body) as Map<String, dynamic>;
      if (data['status'] == 'success') {
        final id      = data['id']?.toString() ?? '';
        final title   = data['title']?.toString() ?? 'Auspoty';
        final message = data['message']?.toString() ?? '';
        final type    = data['type']?.toString() ?? 'info';
        // Gunakan id atau fallback ke hash title+message
        final annKey = id.isNotEmpty ? id : '$title|$message';
        if (annKey.isEmpty || (title.isEmpty && message.isEmpty)) return;
        // Cek apakah sudah pernah ditampilkan
        final prefs = await SharedPreferences.getInstance();
        final shown = prefs.getString('lastAnnouncementId') ?? '';
        if (shown == annKey) return;
        await prefs.setString('lastAnnouncementId', annKey);
        // Kirim notifikasi via native service (hanya status bar, tanpa toast)
        try {
          await _ch.invokeMethod('sendAnnouncement', {
            'title': title.isNotEmpty ? title : 'Auspoty',
            'message': message.isNotEmpty ? message : title,
            'type': type,
          });
        } catch (_) {}
      }
    } catch (_) {}
  }

  Future<bool> _onBack() async {
    // Kalau sedang di offline screen, kembali ke WebView
    if (_isOffline) {
      setState(() { _isOffline = false; _loading = true; });
      _wvc?.reload();
      return false;
    }
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

  Future<void> _download(String videoId, String title, {String artist = '', String img = ''}) async {
    final t2 = title.replaceAll("'", "\\'");
    try {
      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('Mengonversi lagu... tunggu sebentar');");

      // Step 1: Panggil API download
      final apiRes = await http.get(
        Uri.parse('$_base/api/download?video_id=$videoId'),
        headers: {'User-Agent': 'Mozilla/5.0'},
      ).timeout(const Duration(seconds: 90));

      if (apiRes.statusCode != 200) throw Exception('API error ${apiRes.statusCode}');
      final apiJson = json.decode(apiRes.body) as Map<String, dynamic>;
      if (apiJson['status'] != 'success') throw Exception(apiJson['message']?.toString() ?? 'failed');

      final dlUrl    = apiJson['url'] as String;
      final apiTitle = (apiJson['title'] as String?) ?? title;
      final ext      = (apiJson['ext'] as String?) ?? 'mp3';

      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('Mengunduh file...');");

      // Step 2: Download file dengan streaming
      final client = http.Client();
      final req = http.Request('GET', Uri.parse(dlUrl));
      req.headers.addAll({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
        'Referer': 'https://id.ytmp3.mobi/',
      });
      final streamedRes = await client.send(req).timeout(const Duration(seconds: 30));
      if (streamedRes.statusCode != 200) {
        client.close();
        throw Exception('Download error ${streamedRes.statusCode}');
      }

      // Step 3: Simpan ke app documents directory dengan streaming
      final appDir = await getApplicationDocumentsDirectory();
      final safe   = videoId;
      final f      = File('${appDir.path}/$safe.$ext');
      final sink   = f.openWrite();
      await streamedRes.stream.pipe(sink);
      await sink.close();
      client.close();

      // Verifikasi file tersimpan
      if (!await f.exists() || await f.length() < 1000) {
        throw Exception('File gagal tersimpan atau terlalu kecil');
      }

      // Step 4: Ambil artist+img dari WebView jika kosong
      String resolvedArtist = artist;
      String resolvedImg    = img;
      if (resolvedArtist.isEmpty || resolvedImg.isEmpty) {
        try {
          final metaResult = await _wvc?.evaluateJavascript(source:
            "(function(){ var ct=window.currentTrack||{}; return JSON.stringify({artist:ct.artist||'',img:ct.img||ct.thumbnail||''}); })();");
          final meta = json.decode(metaResult?.toString() ?? '{}') as Map<String, dynamic>;
          if (resolvedArtist.isEmpty) resolvedArtist = meta['artist']?.toString() ?? '';
          if (resolvedImg.isEmpty)    resolvedImg    = meta['img']?.toString()    ?? '';
        } catch (_) {}
      }

      // Step 5: Simpan metadata ke SharedPreferences dengan key = videoId
      final prefs   = await SharedPreferences.getInstance();
      final mapJson = prefs.getString('downloadedFiles') ?? '{}';
      final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
      fileMap[videoId] = {
        'filename': safe,
        'ext': ext,
        'title': apiTitle,
        'artist': resolvedArtist,
        'img': resolvedImg,
        'path': f.path,
      };
      await prefs.setString('downloadedFiles', json.encode(fileMap));

      // Step 6: Beritahu JS agar simpan ke IndexedDB juga
      final safeTitle  = apiTitle.replaceAll("'", "\\'");
      final safeArtist = resolvedArtist.replaceAll("'", "\\'");
      final safeImg    = resolvedImg.replaceAll("'", "\\'");
      await _wvc?.evaluateJavascript(source: """
        (function(){
          var track={videoId:'$videoId',title:'$safeTitle',artist:'$safeArtist',img:'$safeImg'};
          if(typeof saveDownloadedSong==='function') saveDownloadedSong(track);
          if(typeof showToast==='function') showToast('\u2713 Tersimpan: ${t2.length > 30 ? t2.substring(0, 30) : t2}');
        })();
      """);
    } catch (e) {
      final msg   = e.toString();
      final short = msg.length > 60 ? msg.substring(0, 60) : msg;
      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('Download gagal: ${short.replaceAll("'", "\\'")}');");
    }
  }

  // Buka offline player sheet — baca SharedPreferences langsung
  Future<void> _openOfflinePlayer() async {
    final prefs   = await SharedPreferences.getInstance();
    final mapJson = prefs.getString('downloadedFiles') ?? '{}';
    final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
    if (!mounted) return;
    if (fileMap.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Belum ada lagu diunduh'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ));
      return;
    }
    final appDir = await getApplicationDocumentsDirectory();
    final songs = <Map<String, dynamic>>[];
    for (final entry in fileMap.entries) {
      final videoId = entry.key;
      final val = entry.value;
      if (val is! Map) continue;
      // Verifikasi file benar-benar ada
      final fn  = val['filename']?.toString() ?? videoId;
      final ext = val['ext']?.toString() ?? 'mp3';
      // Coba path tersimpan dulu, lalu fallback ke appDir
      String? filePath;
      final savedPath = val['path']?.toString() ?? '';
      if (savedPath.isNotEmpty && await File(savedPath).exists()) {
        filePath = savedPath;
      } else {
        final f = File('${appDir.path}/$fn.$ext');
        if (await f.exists()) filePath = f.path;
        // Fallback: cari dengan videoId sebagai nama file
        if (filePath == null) {
          final f2 = File('${appDir.path}/$videoId.$ext');
          if (await f2.exists()) filePath = f2.path;
        }
      }
      if (filePath == null) continue; // skip file yang tidak ada
      songs.add({
        'videoId':  videoId,
        'title':    val['title']?.toString()    ?? 'Unknown',
        'artist':   val['artist']?.toString()   ?? '',
        'img':      val['img']?.toString()      ?? '',
        'filename': fn,
        'ext':      ext,
        'path':     filePath,
      });
    }
    if (!mounted) return;
    if (songs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('File lagu tidak ditemukan di perangkat'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ));
      return;
    }
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1a1a2e),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _OfflinePlayerSheet(songs: songs, onPlay: _playOfflineSong),
    );
  }

  // Dipanggil dari _OfflinePlayerSheet — hanya dipakai saat ONLINE (WebView aktif)
  // Saat offline, _OfflinePlayerSheet langsung pakai just_audio sendiri
  Future<void> _playOfflineSong(Map<String, dynamic> song) async {
    if (_isOffline) return; // offline: biarkan just_audio di sheet yang handle
    final appDir = await getApplicationDocumentsDirectory();
    final fn  = song['filename'] as String;
    final ext = song['ext'] as String;
    // Coba path tersimpan dulu
    final savedPath = song['path'] as String? ?? '';
    File? f;
    if (savedPath.isNotEmpty && await File(savedPath).exists()) {
      f = File(savedPath);
    } else {
      final candidate = File('${appDir.path}/$fn.$ext');
      if (await candidate.exists()) f = candidate;
    }
    if (f == null) return;
    final title  = song['title']  as String;
    final artist = song['artist'] as String;
    final img    = song['img']    as String;
    final vid    = song['videoId'] as String;
    try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true, 'imgUrl': img}); } catch (_) {}
    _servedFilePath = f.path;
    if (_fileServer == null) await _startFileServer();
    final localUrl = 'http://127.0.0.1:$_fileServerPort/audio.$ext';
    final safeTitle  = title.replaceAll("'", "\\'").replaceAll('"', '\\"');
    final safeArtist = artist.replaceAll("'", "\\'").replaceAll('"', '\\"');
    final safeImg    = img.replaceAll("'", "\\'");
    final safeVid    = vid.replaceAll("'", "\\'");
    await _wvc?.evaluateJavascript(source: """
      (function(){
        try { if(typeof ytPlayer!=='undefined'&&ytPlayer&&ytPlayer.stopVideo) ytPlayer.stopVideo(); } catch(e){}
        window._localAudioPlaying=true;
        isPlaying=false;
        window.currentTrack={videoId:'$safeVid',title:'$safeTitle',artist:'$safeArtist',img:'$safeImg'};
        var au=document.getElementById('bgAudio');
        if(!au){au=document.createElement('audio');au.id='bgAudio';au.style.display='none';document.body.appendChild(au);}
        au.onplay=null;au.onpause=null;au.onended=null;au.onerror=null;
        au.src='$localUrl';
        au.onplay=function(){isPlaying=true;updatePlayPauseBtn(true);_setArtPlaying(true);startProgressBar();};
        au.onpause=function(){isPlaying=false;updatePlayPauseBtn(false);_setArtPlaying(false);};
        au.onerror=function(){if(typeof showToast==='function')showToast('Gagal putar audio offline');window._localAudioPlaying=false;};
        au.onended=function(){isPlaying=false;window._localAudioPlaying=false;updatePlayPauseBtn(false);stopProgressBar();if(isRepeat){au.currentTime=0;au.play();}else playNextSimilarSong();};
        au.load();
        au.play().catch(function(e){console.log('offline play err',e);});
        var mp=document.getElementById('miniPlayer');if(mp)mp.style.display='flex';
        var mpi=document.getElementById('miniPlayerImg');if(mpi)mpi.src='$safeImg';
        var mpt=document.getElementById('miniPlayerTitle');if(mpt)mpt.innerText='$safeTitle';
        var mpa=document.getElementById('miniPlayerArtist');if(mpa)mpa.innerText='$safeArtist';
      })();
    """);
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
            // WebView — selalu ada di background
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
                rendererPriorityPolicy: RendererPriorityPolicy(
                  rendererRequestedPriority: RendererPriority.RENDERER_PRIORITY_IMPORTANT,
                  waivedWhenNotVisible: false,
                ),
                userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
              ),
              onWebViewCreated: (c) {
                _wvc = c;
                c.addJavaScriptHandler(
                  handlerName: 'onMusicPlaying',
                  callback: (args) async {
                    final title  = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist = args.length > 1 ? args[1].toString() : '';
                    final imgUrl = args.length > 3 ? args[3].toString() : '';
                    // Stop bgAudio (offline) dulu sebelum ytPlayer jalan
                    await c.evaluateJavascript(source: """
                      (function(){
                        var au = document.getElementById('bgAudio');
                        if(au) { try { au.pause(); au.src=''; } catch(e){} }
                        window._localAudioPlaying = false;
                      })();
                    """);
                    WakelockPlus.enable();
                    try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true, 'imgUrl': imgUrl}); } catch (_) {}
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
                    final vid    = args.isNotEmpty ? args[0].toString() : '';
                    final title  = args.length > 1 ? args[1].toString() : 'lagu';
                    final artist = args.length > 2 ? args[2].toString() : '';
                    final img    = args.length > 3 ? args[3].toString() : '';
                    if (vid.isNotEmpty) _download(vid, title, artist: artist, img: img);
                  },
                );
                c.addJavaScriptHandler(
                  handlerName: 'openOfflinePlayer',
                  callback: (args) async { await _openOfflinePlayer(); },
                );
                c.addJavaScriptHandler(
                  handlerName: 'playLocalFile',
                  callback: (args) async {
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final artist  = args.length > 1 ? args[1].toString() : '';
                    final img     = args.length > 2 ? args[2].toString() : '';
                    final videoId = args.length > 3 ? args[3].toString() : '';
                    try {
                      // Stop ytPlayer dulu agar tidak bentrok dengan bgAudio
                      await c.evaluateJavascript(source: """
                        (function(){
                          try { if(typeof ytPlayer!=='undefined'&&ytPlayer&&ytPlayer.stopVideo) ytPlayer.stopVideo(); } catch(e){}
                          window._localAudioPlaying = false;
                          isPlaying = false;
                        })();
                      """);
                      // Pastikan file server jalan
                      if (_fileServer == null) await _startFileServer();

                      final appDir = await getApplicationDocumentsDirectory();
                      File? found; String? foundExt;

                      // Cari berdasarkan videoId di SharedPreferences (paling akurat)
                      if (videoId.isNotEmpty) {
                        final prefs   = await SharedPreferences.getInstance();
                        final mapJson = prefs.getString('downloadedFiles') ?? '{}';
                        final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
                        if (fileMap.containsKey(videoId)) {
                          final info = fileMap[videoId] as Map<String, dynamic>;
                          // Coba path langsung dulu
                          final savedPath = info['path']?.toString() ?? '';
                          if (savedPath.isNotEmpty) {
                            final fp = File(savedPath);
                            if (await fp.exists()) { found = fp; foundExt = info['ext']?.toString() ?? 'mp3'; }
                          }
                          // Fallback: cari berdasarkan filename di appDir
                          if (found == null) {
                            final fn = info['filename']?.toString() ?? '';
                            final ex = info['ext']?.toString() ?? 'mp3';
                            if (fn.isNotEmpty) {
                              final f = File('${appDir.path}/$fn.$ex');
                              if (await f.exists()) { found = f; foundExt = ex; }
                            }
                          }
                        }
                        // Fallback: cari file dengan nama = videoId di appDir
                        if (found == null) {
                          for (final ext in ['mp3', 'mp4', 'webm', 'm4a']) {
                            final f = File('${appDir.path}/$videoId.$ext');
                            if (await f.exists()) { found = f; foundExt = ext; break; }
                          }
                        }
                      }

                      if (found == null) {
                        await c.evaluateJavascript(source:
                          "if(typeof showToast==='function') showToast('File tidak ditemukan, unduh dulu');");
                        return;
                      }

                      try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true, 'imgUrl': img}); } catch (_) {}
                      _servedFilePath = found.path;
                      final localUrl = 'http://127.0.0.1:$_fileServerPort/audio.$foundExt';
                      WakelockPlus.enable();
                      final safeTitle  = title.replaceAll("'", "\\'").replaceAll('"', '\\"');
                      final safeArtist = artist.replaceAll("'", "\\'").replaceAll('"', '\\"');
                      final safeImg    = img.replaceAll("'", "\\'");
                      final safeVid    = videoId.replaceAll("'", "\\'");
                      await c.evaluateJavascript(source: """
                        (function(){
                          try { if(typeof ytPlayer!=='undefined'&&ytPlayer&&ytPlayer.stopVideo) ytPlayer.stopVideo(); } catch(e){}
                          window._localAudioPlaying = true;
                          isPlaying = false;
                          window.currentTrack={videoId:'$safeVid',title:'$safeTitle',artist:'$safeArtist',img:'$safeImg'};
                          var au=document.getElementById('bgAudio');
                          if(!au){au=document.createElement('audio');au.id='bgAudio';au.style.display='none';document.body.appendChild(au);}
                          au.onplay=null;au.onpause=null;au.onended=null;au.onerror=null;
                          au.src='$localUrl';
                          au.onplay=function(){isPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(true);if(typeof _setArtPlaying==='function')_setArtPlaying(true);if(typeof startProgressBar==='function')startProgressBar();if(window.flutter_inappwebview)try{window.flutter_inappwebview.callHandler('onMusicPlaying','$safeTitle','$safeArtist','','$safeImg');}catch(e){}};
                          au.onpause=function(){isPlaying=false;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);if(typeof _setArtPlaying==='function')_setArtPlaying(false);};
                          au.onerror=function(){console.log('audio error',au.error&&au.error.code);if(typeof showToast==='function')showToast('Gagal putar audio offline');window._localAudioPlaying=false;};
                          au.onended=function(){isPlaying=false;window._localAudioPlaying=false;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);if(typeof _setArtPlaying==='function')_setArtPlaying(false);if(typeof stopProgressBar==='function')stopProgressBar();if(typeof isRepeat!=='undefined'&&isRepeat){au.currentTime=0;au.play();}else if(typeof playNextSimilarSong==='function')playNextSimilarSong();};
                          au.load();
                          au.play().catch(function(e){console.log('local play err',e);if(typeof showToast==='function')showToast('Gagal putar: '+e.message);});
                          var mp=document.getElementById('miniPlayer');if(mp)mp.style.display='flex';
                          var mpi=document.getElementById('miniPlayerImg');if(mpi)mpi.src='$safeImg';
                          var mpt=document.getElementById('miniPlayerTitle');if(mpt)mpt.innerText='$safeTitle';
                          var mpa=document.getElementById('miniPlayerArtist');if(mpa)mpa.innerText='$safeArtist';
                          var pa=document.getElementById('playerArt');if(pa)pa.src='$safeImg';
                          var pt=document.getElementById('playerTitle');if(pt)pt.innerText='$safeTitle';
                          var par=document.getElementById('playerArtist');if(par)par.innerText='$safeArtist';
                          var pbg=document.getElementById('playerBg');if(pbg)pbg.style.backgroundImage="url('$safeImg')";
                          var bar=document.getElementById('progressBar');if(bar)bar.value=0;
                          var pf=document.getElementById('progressFill');if(pf)pf.style.width='0%';
                          var mf=document.getElementById('miniProgressFill');if(mf)mf.style.width='0%';
                          var ct=document.getElementById('currentTime');if(ct)ct.innerText='0:00';
                          var tt=document.getElementById('totalTime');if(tt)tt.innerText='0:00';
                        })();
                      """);
                    } catch (e) {
                      debugPrint('playLocalFile error: $e');
                      await c.evaluateJavascript(source:
                        "if(typeof showToast==='function') showToast('Gagal memutar file offline');");
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
                  handlerName: 'sendAnnouncement',
                  callback: (args) async {
                    final title   = args.isNotEmpty ? args[0].toString() : 'Auspoty';
                    final message = args.length > 1 ? args[1].toString() : '';
                    final type    = args.length > 2 ? args[2].toString() : 'info';
                    try {
                      await _ch.invokeMethod('sendAnnouncement', {
                        'title': title,
                        'message': message,
                        'type': type,
                      });
                    } catch (e) {
                      debugPrint('sendAnnouncement error: $e');
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
                c.addJavaScriptHandler(
                  handlerName: 'pickProfilePhoto',
                  callback: (args) async {
                    try {
                      final picker = ImagePicker();
                      final picked = await picker.pickImage(
                        source: ImageSource.gallery,
                        maxWidth: 512,
                        maxHeight: 512,
                        imageQuality: 80,
                      );
                      if (picked == null) return;
                      final bytes = await picked.readAsBytes();
                      final base64 = 'data:image/jpeg;base64,${base64Encode(bytes)}';
                      await c.evaluateJavascript(source:
                        "if(typeof applyProfilePhoto==='function') applyProfilePhoto('$base64');");
                    } catch (e) {
                      debugPrint('pickProfilePhoto error: $e');
                    }
                  },
                );
              },
              onLoadStart: (c, url) => setState(() { _loading = true; _isOffline = false; }),
              onLoadStop: (c, url) async {
                setState(() => _loading = false);
                final urlStr = url?.toString() ?? '';
                // Cek pengumuman dari server (sekali per sesi)
                if (!_announcementChecked && (urlStr.contains('vercel.app') || urlStr.contains('clone2'))) {
                  _announcementChecked = true;
                  _checkAnnouncement();
                }
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
                if (req.isForMainFrame == true) {
                  // Halaman utama gagal load = offline
                  setState(() { _loading = false; _isOffline = true; });
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

            // Loading overlay
            if (_loading && !_isOffline)
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

            // Offline screen — muncul saat tidak ada internet
            if (_isOffline)
              _OfflineScreen(
                onOpenDownloads: _openOfflinePlayer,
                onRetry: () {
                  setState(() { _isOffline = false; _loading = true; });
                  _wvc?.reload();
                },
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
            window._nativeLoading=false; window._nativePlaying=false; window._nativePaused=false;
            if(window.flutter_inappwebview)
              window.flutter_inappwebview.callHandler('onMusicPlaying', title||'', artist||'', '', img||'');
          },
          pauseNative: function(){
            window._nativePlaying=false; window._nativePaused=true;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicPaused');
          },
          resumeNative: function(){
            window._nativePlaying=true; window._nativePaused=false;
            if(window.flutter_inappwebview) window.flutter_inappwebview.callHandler('onMusicResumed');
          },
          openDownload: function(vid, t){
            window.flutter_inappwebview.callHandler('downloadTrack', vid, t||'');
          },
          logout: function(){
            localStorage.removeItem('auspotyGoogleUser');
            if(typeof updateProfileUI==='function') updateProfileUI();
            if(typeof updateGoogleLoginUI==='function') updateGoogleLoginUI();
          },
          sendAnnouncement: function(title, message, type){
            if(window.flutter_inappwebview)
              window.flutter_inappwebview.callHandler('sendAnnouncement', title||'Auspoty', message||'', type||'info');
          }
        };
        window._onNativePlaybackStarted=function(){window._nativeLoading=false;window._nativePlaying=true;window._nativePaused=false;isPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(true);};
        window._onNativePlaybackPaused=function(){window._nativePlaying=false;window._nativePaused=true;isPlaying=false;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);};
        window._updateNativeProgress=function(pos,dur){if(dur<=0)return;var pct=(pos/dur)*100;var bar=document.getElementById('progressBar');if(bar){bar.value=pct;bar.style.background='linear-gradient(to right, white '+pct+'%, rgba(255,255,255,0.2) '+pct+'%)';}var fmt=function(s){var m=Math.floor(s/60),sec=s%60;return m+':'+(sec<10?'0':'')+sec;};var ct=document.getElementById('currentTime');if(ct)ct.innerText=fmt(pos);var tt=document.getElementById('totalTime');if(tt)tt.innerText=fmt(dur);};
        window._fmtTime=function(s){var m=Math.floor(s/60),sec=s%60;return m+':'+(sec<10?'0':'')+sec;};
        console.log('[Auspoty] Bridge ready');
      })();
    """);
  }
}

// ─── Offline Screen ──────────────────────────────────────────────────────────
class _OfflineScreen extends StatelessWidget {
  final VoidCallback onOpenDownloads;
  final VoidCallback onRetry;
  const _OfflineScreen({required this.onOpenDownloads, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0a0a0f),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, color: Color(0xFFa78bfa), size: 72),
              const SizedBox(height: 24),
              const Text('Tidak Ada Koneksi',
                style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              const Text('Kamu bisa tetap mendengarkan\nlagu yang sudah diunduh',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white54, fontSize: 15, height: 1.5)),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: onOpenDownloads,
                  icon: const Icon(Icons.download_done, size: 22),
                  label: const Text('Putar Lagu Diunduh', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFa78bfa),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh, size: 20),
                  label: const Text('Coba Lagi', style: TextStyle(fontSize: 15)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: const BorderSide(color: Colors.white24),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Offline Player Bottom Sheet ─────────────────────────────────────────────
class _OfflinePlayerSheet extends StatefulWidget {
  final List<Map<String, dynamic>> songs;
  final Future<void> Function(Map<String, dynamic> song) onPlay;
  const _OfflinePlayerSheet({required this.songs, required this.onPlay});
  @override
  State<_OfflinePlayerSheet> createState() => _OfflinePlayerSheetState();
}

class _OfflinePlayerSheetState extends State<_OfflinePlayerSheet> {
  String? _playingId;
  final AudioPlayer _player = AudioPlayer();
  Map<String, dynamic>? _currentSong;

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _play(Map<String, dynamic> song) async {
    setState(() { _playingId = song['videoId'] as String; _currentSong = song; });
    try {
      // Gunakan path langsung jika tersedia (sudah diverifikasi di _openOfflinePlayer)
      final filePath = song['path'] as String? ?? '';
      if (filePath.isNotEmpty && await File(filePath).exists()) {
        await _player.stop();
        await _player.setFilePath(filePath);
        await _player.play();
      } else {
        // Fallback: cari di appDir
        final appDir = await getApplicationDocumentsDirectory();
        final fn  = song['filename'] as String;
        final ext = song['ext'] as String;
        final f   = File('${appDir.path}/$fn.$ext');
        if (await f.exists()) {
          await _player.stop();
          await _player.setFilePath(f.path);
          await _player.play();
        } else {
          debugPrint('File tidak ditemukan: $filePath');
          return;
        }
      }
    } catch (e) {
      debugPrint('just_audio error: $e');
    }
    // Update WebView UI jika online (tidak masalah jika gagal saat offline)
    await widget.onPlay(song);
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.65,
      maxChildSize: 0.92,
      minChildSize: 0.35,
      builder: (_, sc) => Column(
        children: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10),
            width: 40, height: 4,
            decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(children: [
              const Icon(Icons.download_done, color: Color(0xFFa78bfa), size: 22),
              const SizedBox(width: 8),
              const Text('Lagu Diunduh',
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const Spacer(),
              Text('${widget.songs.length} lagu',
                style: const TextStyle(color: Colors.white54, fontSize: 13)),
            ]),
          ),
          // Mini player bar saat ada lagu yang diputar
          if (_currentSong != null)
            StreamBuilder<PlayerState>(
              stream: _player.playerStateStream,
              builder: (_, snap) {
                final playing = snap.data?.playing ?? false;
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF2d2d4e),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: (_currentSong!['img'] as String).isNotEmpty
                        ? Image.network(_currentSong!['img'] as String, width: 36, height: 36, fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => _artIcon(36))
                        : _artIcon(36),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_currentSong!['title'] as String,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                      Text(_currentSong!['artist'] as String,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white54, fontSize: 11)),
                    ])),
                    IconButton(
                      icon: Icon(playing ? Icons.pause_circle : Icons.play_circle,
                        color: const Color(0xFFa78bfa), size: 32),
                      onPressed: () => playing ? _player.pause() : _player.play(),
                    ),
                  ]),
                );
              },
            ),
          const Divider(color: Colors.white12, height: 1),
          Expanded(
            child: widget.songs.isEmpty
              ? const Center(child: Text('Belum ada lagu diunduh', style: TextStyle(color: Colors.white54)))
              : ListView.builder(
                  controller: sc,
                  itemCount: widget.songs.length,
                  itemBuilder: (_, i) {
                    final s   = widget.songs[i];
                    final vid = s['videoId'] as String;
                    final isActive = _playingId == vid;
                    return ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      leading: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: (s['img'] as String).isNotEmpty
                          ? Image.network(s['img'] as String, width: 52, height: 52, fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => _artIcon(52))
                          : _artIcon(52),
                      ),
                      title: Text(s['title'] as String,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: isActive ? const Color(0xFFa78bfa) : Colors.white,
                          fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                          fontSize: 14,
                        )),
                      subtitle: Text(s['artist'] as String,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white54, fontSize: 12)),
                      trailing: isActive
                        ? const Icon(Icons.equalizer, color: Color(0xFFa78bfa), size: 22)
                        : const Icon(Icons.play_circle_outline, color: Colors.white54, size: 26),
                      onTap: () => _play(s),
                    );
                  },
                ),
          ),
        ],
      ),
    );
  }

  Widget _artIcon(double size) => Container(
    width: size, height: size,
    decoration: BoxDecoration(color: const Color(0xFF2d2d4e), borderRadius: BorderRadius.circular(6)),
    child: const Icon(Icons.music_note, color: Color(0xFFa78bfa), size: 26),
  );
}
