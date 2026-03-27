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
import 'package:open_filex/open_filex.dart';

const _ch = MethodChannel('com.auspoty.app/music');
final _keepAlive = InAppWebViewKeepAlive();
const _base = 'https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app';

// (unused legacy constants — kept for reference)
const _localHost = 'localfile.internal';
final Map<String, String> _localFileMap = {};

// Versi app saat ini — harus sama dengan versionName di build.gradle
const _appVersion = '9.4.1';
const _githubReleasesApi = 'https://api.github.com/repos/yusrilrizky121-code/Auspoty/releases/latest';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
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
  bool _updateChecked = false;
  DateTime? _lastBack;
  Timer? _progressTimer;
  Timer? _onlineCheckTimer;

  // just_audio player untuk playback file lokal (offline)
  final AudioPlayer _localPlayer = AudioPlayer();
  bool _localPlaying = false;
  Timer? _localProgressTimer;
  StreamSubscription? _localPlayerSub;

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
    _localProgressTimer?.cancel();
    _localPlayerSub?.cancel();
    _onlineCheckTimer?.cancel();
    _localPlayer.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _progressTimer?.cancel();
      try { _ch.invokeMethod('keepAlive'); } catch (_) {}
      WakelockPlus.enable();
      // Set user offline saat app ke background
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          if(window.__bgHidden) return;
          window.__bgHidden = true;
          // Set offline di Firestore
          var me = typeof getGoogleUser==='function' ? getGoogleUser() : null;
          if(me && window._firestoreDB && window._fsSetDoc && window._fsDoc) {
            try {
              window._fsSetDoc(window._fsDoc(window._firestoreDB,'users',me.email),
                {online:false},{merge:true}).catch(function(){});
            } catch(e){}
          }
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
    if (state == AppLifecycleState.detached) {
      // App benar-benar ditutup — set offline
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          var me = typeof getGoogleUser==='function' ? getGoogleUser() : null;
          if(me && window._firestoreDB && window._fsSetDoc && window._fsDoc) {
            try {
              window._fsSetDoc(window._fsDoc(window._firestoreDB,'users',me.email),
                {online:false},{merge:true}).catch(function(){});
            } catch(e){}
          }
        })();
      """);
    }
    if (state == AppLifecycleState.resumed) {
      _wvc?.evaluateJavascript(source: r"""
        (function(){
          window.__bgHidden=false;
          try{delete document.hidden;delete document.visibilityState;delete document.webkitHidden;}catch(e){}
          // Set online kembali saat app dibuka
          var me = typeof getGoogleUser==='function' ? getGoogleUser() : null;
          if(me && window._firestoreDB && window._fsSetDoc && window._fsDoc && window._fsTimestamp) {
            try {
              window._fsSetDoc(window._fsDoc(window._firestoreDB,'users',me.email),
                {online:true,lastSeen:window._fsTimestamp()},{merge:true}).catch(function(){});
            } catch(e){}
          }
        })();
      """);
      _startProgressTimer();
      _checkAnnouncement();
    }
  }

  Future<dynamic> _onNativeCall(MethodCall call) async {
    switch (call.method) {
      case 'onPlayPause':
        if (_localPlaying || _localPlayer.processingState != ProcessingState.idle) {
          // Offline: toggle via just_audio
          if (_localPlayer.playing) {
            await _localPlayer.pause();
            _localPlaying = false;
            try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
            await _wvc?.evaluateJavascript(source:
              "(function(){isPlaying=false;window._localAudioPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);if(typeof _setArtPlaying==='function')_setArtPlaying(false);})();");
          } else {
            await _localPlayer.play();
            _localPlaying = true;
            try { await _ch.invokeMethod('setPlaying', {'isPlaying': true}); } catch (_) {}
            await _wvc?.evaluateJavascript(source:
              "(function(){isPlaying=true;window._localAudioPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(true);if(typeof _setArtPlaying==='function')_setArtPlaying(true);})();");
          }
        } else {
          await _wvc?.evaluateJavascript(
              source: "(function(){ if(typeof togglePlay==='function') togglePlay(); })();");
        }
        break;
      case 'onNext':
        // Jika sedang memutar file offline (downloaded), next harus ikut antrean downloaded.
        _stopLocalPlayer(injectJs: false);
        await _wvc?.evaluateJavascript(source: r"""
          (function(){
            try{
              if(window._isDownloadedView && typeof playNextDownloadedSong==='function') playNextDownloadedSong();
              else if(typeof playNextSimilarSong==='function') playNextSimilarSong();
            }catch(e){}
          })();
        """);
        break;
      case 'onPrev':
        _stopLocalPlayer(injectJs: false);
        await _wvc?.evaluateJavascript(source: r"""
          (function(){
            try{
              if(window._isDownloadedView && typeof playPrevDownloadedSong==='function') playPrevDownloadedSong();
              else if(typeof playPrevSong==='function') playPrevSong();
            }catch(e){}
          })();
        """);
        break;
    }
  }

  void _startProgressTimer() {}

  // Cek koneksi internet secara periodik saat offline — auto reload saat kembali online
  void _startOnlineCheck() {
    _onlineCheckTimer?.cancel();
    _onlineCheckTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      if (!_isOffline) { _onlineCheckTimer?.cancel(); return; }
      try {
        final res = await http.get(Uri.parse('$_base/api/search?query=test'))
            .timeout(const Duration(seconds: 4));
        if (res.statusCode == 200 && mounted) {
          _onlineCheckTimer?.cancel();
          setState(() { _isOffline = false; _loading = true; });
          // Inject JS untuk trigger online event di WebView
          await _wvc?.evaluateJavascript(source:
            "(function(){ window._wasOffline=true; if(typeof _onBackOnline==='function') _onBackOnline(); })();");
          _wvc?.reload();
        }
      } catch (_) {}
    });
  }

  // Cek update dari GitHub Releases
  Future<void> _checkForUpdate() async {
    if (_updateChecked) return;
    _updateChecked = true;
    try {
      final res = await http.get(
        Uri.parse(_githubReleasesApi),
        headers: {'User-Agent': 'AuspotyApp/$_appVersion', 'Accept': 'application/vnd.github.v3+json'},
      ).timeout(const Duration(seconds: 15));
      if (res.statusCode != 200) return;
      final data = json.decode(res.body) as Map<String, dynamic>;
      final latestTag = (data['tag_name'] as String? ?? '').replaceAll('v', '').trim();
      if (latestTag.isEmpty || latestTag == _appVersion) return;

      // Bandingkan versi
      if (!_isNewerVersion(latestTag, _appVersion)) return;

      // Cari APK asset arm64
      final assets = (data['assets'] as List? ?? []);
      String? apkUrl;
      for (final a in assets) {
        final name = (a['name'] as String? ?? '').toLowerCase();
        if (name.endsWith('.apk') && (name.contains('arm64') || name.contains('release'))) {
          apkUrl = a['browser_download_url'] as String?;
          break;
        }
      }
      // Fallback: ambil APK pertama
      if (apkUrl == null) {
        for (final a in assets) {
          if ((a['name'] as String? ?? '').toLowerCase().endsWith('.apk')) {
            apkUrl = a['browser_download_url'] as String?;
            break;
          }
        }
      }
      if (apkUrl == null) return;

      final releaseNotes = (data['body'] as String? ?? '').trim();
      if (!mounted) return;

      // Tampilkan dialog update
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => _UpdateDialog(
          currentVersion: _appVersion,
          newVersion: latestTag,
          releaseNotes: releaseNotes,
          apkUrl: apkUrl!,
          onDownload: () => _downloadAndInstallApk(apkUrl!, latestTag),
        ),
      );
    } catch (e) {
      debugPrint('checkForUpdate error: $e');
    }
  }

  bool _isNewerVersion(String latest, String current) {
    try {
      final l = latest.split('.').map(int.parse).toList();
      final c = current.split('.').map(int.parse).toList();
      while (l.length < 3) l.add(0);
      while (c.length < 3) c.add(0);
      for (int i = 0; i < 3; i++) {
        if (l[i] > c[i]) return true;
        if (l[i] < c[i]) return false;
      }
      return false;
    } catch (_) { return false; }
  }

  Future<void> _downloadAndInstallApk(String url, String version) async {
    if (!mounted) return;
    Navigator.of(context, rootNavigator: true).pop(); // tutup dialog

    // Tampilkan progress dialog
    double progress = 0;
    final progressNotifier = ValueNotifier<double>(0);
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => ValueListenableBuilder<double>(
        valueListenable: progressNotifier,
        builder: (ctx, val, _) => AlertDialog(
          backgroundColor: const Color(0xFF1a1a2e),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Mengunduh Update', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            LinearProgressIndicator(
              value: val > 0 ? val : null,
              backgroundColor: Colors.white12,
              color: const Color(0xFFa78bfa),
            ),
            const SizedBox(height: 12),
            Text(val > 0 ? '${(val * 100).toStringAsFixed(0)}%' : 'Menghubungkan...',
              style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ]),
        ),
      ),
    );

    try {
      final dir = await getExternalStorageDirectory() ?? await getApplicationDocumentsDirectory();
      final apkPath = '${dir.path}/auspoty-v$version.apk';
      final file = File(apkPath);

      // Download dengan progress
      final client = http.Client();
      final req = http.Request('GET', Uri.parse(url));
      req.headers['User-Agent'] = 'AuspotyApp/$_appVersion';
      final streamRes = await client.send(req).timeout(const Duration(minutes: 5));
      final total = streamRes.contentLength ?? 0;
      int received = 0;
      final sink = file.openWrite();
      await for (final chunk in streamRes.stream) {
        sink.add(chunk);
        received += chunk.length;
        if (total > 0) {
          progress = received / total;
          progressNotifier.value = progress;
        }
      }
      await sink.close();
      client.close();

      if (!mounted) return;
      Navigator.of(context, rootNavigator: true).pop(); // tutup progress

      // Install APK via intent
      await _installApk(apkPath);
    } catch (e) {
      if (mounted) {
        Navigator.of(context, rootNavigator: true).pop();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Gagal download: ${e.toString().substring(0, e.toString().length.clamp(0, 60))}'),
          backgroundColor: Colors.red.shade800,
          behavior: SnackBarBehavior.floating,
        ));
      }
    }
  }

  Future<void> _installApk(String path) async {
    try {
      final result = await OpenFilex.open(path, type: 'application/vnd.android.package-archive');
      if (result.type != ResultType.done) {
        await launchUrl(
          Uri.parse('https://github.com/yusrilrizky121-code/Auspoty/releases/latest'),
          mode: LaunchMode.externalApplication,
        );
      }
    } catch (_) {
      await launchUrl(
        Uri.parse('https://github.com/yusrilrizky121-code/Auspoty/releases/latest'),
        mode: LaunchMode.externalApplication,
      );
    }
  }

  // ── Playback file lokal via just_audio (native) ─────────────────────────────
  void _stopLocalPlayer({bool injectJs = true}) {
    _localPlaying = false;
    _localProgressTimer?.cancel();
    _localProgressTimer = null;
    _localPlayerSub?.cancel();
    _localPlayerSub = null;
    try { _localPlayer.stop(); } catch (_) {}
    if (injectJs) {
      _wvc?.evaluateJavascript(source:
        "(function(){window._localAudioPlaying=false;isPlaying=false;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);if(typeof _setArtPlaying==='function')_setArtPlaying(false);})();");
    }
  }

  Future<void> _playLocalFileDart(
    InAppWebViewController c,
    String videoId, String title, String artist, String img,
  ) async {
    final appDir = await getApplicationDocumentsDirectory();
    File? found;

    if (videoId.isNotEmpty) {
      // 1. SharedPreferences
      try {
        final prefs   = await SharedPreferences.getInstance();
        final mapJson = prefs.getString('downloadedFiles') ?? '{}';
        final fileMap = Map<String, dynamic>.from(json.decode(mapJson));
        if (fileMap.containsKey(videoId)) {
          final info      = fileMap[videoId] as Map<String, dynamic>;
          final savedPath = info['path']?.toString() ?? '';
          final fn        = info['filename']?.toString() ?? videoId;
          final ex        = info['ext']?.toString() ?? 'mp3';
          for (final candidate in [
            if (savedPath.isNotEmpty) File(savedPath),
            File('${appDir.path}/$fn.$ex'),
            File('${appDir.path}/$videoId.$ex'),
          ]) {
            if (await candidate.exists()) { found = candidate; break; }
          }
        }
      } catch (_) {}

      if (found == null) {
        for (final ext in ['mp3', 'mp4', 'm4a', 'webm', 'opus']) {
          final f = File('${appDir.path}/$videoId.$ext');
          if (await f.exists()) { found = f; break; }
        }
      }

      if (found == null) {
        try {
          for (final f in Directory(appDir.path).listSync().whereType<File>()) {
            if (f.path.contains(videoId)) { found = f; break; }
          }
        } catch (_) {}
      }
    }

    if (found == null) {
      await c.evaluateJavascript(source:
        "if(typeof showToast==='function') showToast('File tidak ditemukan, unduh dulu');");
      return;
    }

    _stopLocalPlayer(injectJs: false);

    try {
      await _localPlayer.setFilePath(found.path);
    } catch (e) {
      debugPrint('setFilePath error: $e');
      await c.evaluateJavascript(source:
        "if(typeof showToast==='function') showToast('Format audio tidak didukung');");
      return;
    }
    await _localPlayer.play();
    _localPlaying = true;

    WakelockPlus.enable();
    try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true, 'imgUrl': img}); } catch (_) {}

    final safeTitle  = title.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
    final safeArtist = artist.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
    final safeImg    = img.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
    final safeVid    = videoId.replaceAll('\\', '\\\\').replaceAll("'", "\\'");

    await c.evaluateJavascript(source: """
      (function(){
        try{if(typeof ytPlayer!=='undefined'&&ytPlayer&&ytPlayer.stopVideo)ytPlayer.stopVideo();}catch(e){}
        window._localAudioPlaying = true;
        isPlaying = true;
        window.currentTrack = {videoId:'$safeVid',title:'$safeTitle',artist:'$safeArtist',img:'$safeImg'};
        if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(true);
        if(typeof _setArtPlaying==='function') _setArtPlaying(true);
        if(typeof stopProgressBar==='function') stopProgressBar();
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

    // Progress timer dari Dart → inject ke WebView setiap 1 detik (hemat RAM)
    _localProgressTimer?.cancel();
    _localProgressTimer = Timer.periodic(const Duration(milliseconds: 1000), (_) async {
      // Cek dari player langsung, bukan dari _localPlaying flag
      final pos = _localPlayer.position.inMilliseconds;
      final dur = _localPlayer.duration?.inMilliseconds ?? 0;
      if (dur <= 0) return;
      final pct = (pos / dur * 100).clamp(0.0, 100.0);
      final posSec = pos ~/ 1000;
      final durSec = dur ~/ 1000;
      String fmt(int s) => '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
      try {
        await _wvc?.evaluateJavascript(source: """
          (function(){
            var pct=${pct.toStringAsFixed(1)};
            var bar=document.getElementById('progressBar');
            if(bar) bar.value=pct;
            var pf=document.getElementById('progressFill');if(pf)pf.style.width=pct+'%';
            var mf=document.getElementById('miniProgressFill');if(mf)mf.style.width=pct+'%';
            var ct=document.getElementById('currentTime');if(ct)ct.innerText='${fmt(posSec)}';
            var tt=document.getElementById('totalTime');if(tt)tt.innerText='${fmt(durSec)}';
          })();
        """);
      } catch (_) {}
    });

    // Selesai putar
    _localPlayerSub?.cancel();
    _localPlayerSub = _localPlayer.playerStateStream.listen((state) async {
      if (state.processingState == ProcessingState.completed) {
        _localPlaying = false;
        _localProgressTimer?.cancel();
        try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
        try {
          await _wvc?.evaluateJavascript(source: """
            (function(){
              isPlaying=false; window._localAudioPlaying=false;
              if(typeof updatePlayPauseBtn==='function') updatePlayPauseBtn(false);
              if(typeof _setArtPlaying==='function') _setArtPlaying(false);
              if(typeof isRepeat!=='undefined'&&isRepeat){
                window.flutter_inappwebview.callHandler('playLocalFile','$safeTitle','$safeArtist','$safeImg','$safeVid');
              } else {
                if(window._isDownloadedView && typeof playNextDownloadedSong==='function') playNextDownloadedSong();
                else if(typeof playNextSimilarSong==='function') playNextSimilarSong();
              }
            })();
          """);
        } catch (_) {}
      }
    });
  }

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
        // Gunakan id atau fallback ke hash title+message
        final annKey = id.isNotEmpty ? id : '$title|$message';
        if (annKey.isEmpty || (title.isEmpty && message.isEmpty)) return;
        // Cek apakah sudah pernah ditampilkan
        final prefs = await SharedPreferences.getInstance();
        final shown = prefs.getString('lastAnnouncementId') ?? '';
        if (shown == annKey) return;
        await prefs.setString('lastAnnouncementId', annKey);
        // Hanya tandai sebagai sudah dilihat — AnnouncementWorker yang handle notifikasi status bar
        // Ini mencegah notifikasi ganda (Worker + Dart keduanya kirim notif)
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
    try {
      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('⏳ Mengonversi lagu...');");

      final ytHeaders = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Referer': 'https://id.ytmp3.mobi/',
        'Origin': 'https://id.ytmp3.mobi',
        'Accept': 'application/json, */*',
      };

      String downloadUrl = '';
      String apiTitle = title;

      // Coba beberapa endpoint ytmp3.mobi
      final endpoints = [
        'https://a.ymcdn.org/api/v1/init?p=y&23=1llum1n471',
        'https://d.ymcdn.org/api/v1/init?p=y&23=1llum1n471',
        'https://b.ymcdn.org/api/v1/init?p=y&23=1llum1n471',
      ];

      for (final baseEndpoint in endpoints) {
        try {
          final rnd1 = DateTime.now().millisecondsSinceEpoch / 1000.0;
          final initRes = await http.get(
            Uri.parse('$baseEndpoint&_=$rnd1'),
            headers: ytHeaders,
          ).timeout(const Duration(seconds: 15));
          if (initRes.statusCode != 200) continue;
          final initJson = json.decode(initRes.body) as Map<String, dynamic>;
          if ((initJson['error'] ?? 0) != 0) continue;
          final convertUrl = initJson['convertURL'] as String? ?? '';
          if (convertUrl.isEmpty) continue;

          final rnd2 = DateTime.now().millisecondsSinceEpoch / 1000.0;
          final convRes = await http.get(
            Uri.parse('$convertUrl&v=$videoId&f=mp3&_=$rnd2'),
            headers: ytHeaders,
          ).timeout(const Duration(seconds: 20));
          if (convRes.statusCode != 200) continue;
          final convJson = json.decode(convRes.body) as Map<String, dynamic>;
          if ((convJson['error'] ?? 0) != 0) continue;

          final progressUrl = convJson['progressURL'] as String? ?? '';
          downloadUrl = convJson['downloadURL'] as String? ?? '';
          apiTitle = convJson['title'] as String? ?? title;

          // Poll progress
          if (progressUrl.isNotEmpty) {
            for (int i = 0; i < 40; i++) {
              await Future.delayed(const Duration(milliseconds: 1500));
              final rnd3 = DateTime.now().millisecondsSinceEpoch / 1000.0;
              try {
                final progRes = await http.get(
                  Uri.parse('$progressUrl&_=$rnd3'),
                  headers: ytHeaders,
                ).timeout(const Duration(seconds: 10));
                if (progRes.statusCode != 200) continue;
                final progJson = json.decode(progRes.body) as Map<String, dynamic>;
                if ((progJson['error'] ?? 0) != 0) break;
                final progress = (progJson['progress'] as num?)?.toInt() ?? 0;
                if (progress >= 3) {
                  downloadUrl = progJson['downloadURL'] as String? ?? downloadUrl;
                  apiTitle = progJson['title'] as String? ?? apiTitle;
                  break;
                }
              } catch (_) { continue; }
            }
          }

          if (downloadUrl.isNotEmpty) break;
        } catch (_) { continue; }
      }

      if (downloadUrl.isEmpty) throw Exception('Gagal mendapatkan URL download dari ytmp3.mobi');

      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('⬇️ Mengunduh...');");

      // Download file
      final client = http.Client();
      final req = http.Request('GET', Uri.parse(downloadUrl));
      req.headers.addAll({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120',
        'Referer': 'https://id.ytmp3.mobi/',
      });
      final streamedRes = await client.send(req).timeout(const Duration(seconds: 90));
      if (streamedRes.statusCode != 200) {
        client.close();
        throw Exception('Download HTTP ${streamedRes.statusCode}');
      }

      // Baca semua bytes dulu
      final bytes = await streamedRes.stream.toBytes();
      client.close();

      if (bytes.length < 1000) throw Exception('File terlalu kecil, mungkin gagal');

      final safeFilename = videoId.replaceAll(RegExp(r'[^\w]'), '_');

      // ── LOKASI 1: App documents (untuk diputar di dalam app) ──────────────
      final appDir = await getApplicationDocumentsDirectory();
      final appFile = File('${appDir.path}/$safeFilename.mp3');
      await appFile.writeAsBytes(bytes);

      // ── LOKASI 2: Folder Auspoty di penyimpanan eksternal ─────────────────
      String? externalPath;
      try {
        final extDir = await getExternalStorageDirectory();
        if (extDir != null) {
          // Naik ke root storage, buat folder Auspoty/Music
          // extDir biasanya: /storage/emulated/0/Android/data/com.auspoty.app/files
          // Kita mau: /storage/emulated/0/Auspoty
          final parts = extDir.path.split('/');
          // Cari index 'emulated' atau ambil sampai /storage/emulated/0
          int rootIdx = parts.indexOf('Android');
          if (rootIdx > 0) {
            final rootPath = parts.sublist(0, rootIdx).join('/');
            final auspotyDir = Directory('$rootPath/Auspoty');
            if (!await auspotyDir.exists()) await auspotyDir.create(recursive: true);
            final extFile = File('${auspotyDir.path}/$safeFilename.mp3');
            await extFile.writeAsBytes(bytes);
            externalPath = extFile.path;
          }
        }
      } catch (_) { /* external storage tidak tersedia */ }

      // Ambil artist+img dari WebView jika kosong
      String resolvedArtist = artist;
      String resolvedImg = img;
      if (resolvedArtist.isEmpty || resolvedImg.isEmpty) {
        try {
          final metaResult = await _wvc?.evaluateJavascript(source:
            "(function(){ var ct=window.currentTrack||{}; return JSON.stringify({artist:ct.artist||'',img:ct.img||ct.thumbnail||''}); })();");
          final meta = json.decode(metaResult?.toString() ?? '{}') as Map<String, dynamic>;
          if (resolvedArtist.isEmpty) resolvedArtist = meta['artist']?.toString() ?? '';
          if (resolvedImg.isEmpty) resolvedImg = meta['img']?.toString() ?? '';
        } catch (_) {}
      }

      // Simpan metadata ke SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      final mapJson = prefs.getString('downloadedFiles') ?? '{}';
      final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
      fileMap[videoId] = {
        'filename': safeFilename,
        'ext': 'mp3',
        'title': apiTitle,
        'artist': resolvedArtist,
        'img': resolvedImg,
        'path': appFile.path,
        'externalPath': externalPath ?? '',
      };
      await prefs.setString('downloadedFiles', json.encode(fileMap));

      // Beritahu JS agar simpan ke IndexedDB
      final safeTitle = apiTitle.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
      final safeArtist = resolvedArtist.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
      final safeImg = resolvedImg.replaceAll('\\', '\\\\').replaceAll("'", "\\'");
      final shortTitle = apiTitle.length > 30 ? apiTitle.substring(0, 30) : apiTitle;
      final extMsg = externalPath != null ? ' & folder Auspoty' : '';
      await _wvc?.evaluateJavascript(source: """
        (function(){
          var track={videoId:'$videoId',title:'$safeTitle',artist:'$safeArtist',img:'$safeImg'};
          if(typeof saveDownloadedSong==='function') saveDownloadedSong(track);
          if(typeof showToast==='function') showToast('✓ Tersimpan di koleksi$extMsg: ${shortTitle.replaceAll("'", "\\'")}');
        })();
      """);
    } catch (e) {
      final msg = e.toString();
      final short = msg.length > 70 ? msg.substring(0, 70) : msg;
      _wvc?.evaluateJavascript(source: "if(typeof showToast==='function') showToast('Download gagal: ${short.replaceAll("'", "\\'")}');");
    }
  }
  // Buka offline player sheet — baca SharedPreferences langsung
  Future<void> _openOfflinePlayer() async {
    final prefs   = await SharedPreferences.getInstance();
    final mapJson = prefs.getString('downloadedFiles') ?? '{}';
    final Map<String, dynamic> fileMap = Map<String, dynamic>.from(json.decode(mapJson));
    if (!mounted) return;

    final appDir = await getApplicationDocumentsDirectory();
    final songs = <Map<String, dynamic>>[];

    // Jika SharedPreferences kosong, coba scan langsung dari appDir
    if (fileMap.isEmpty) {
      try {
        final dir = Directory(appDir.path);
        final files = dir.listSync().whereType<File>().where((f) {
          final name = f.path.split('/').last.toLowerCase();
          return name.endsWith('.mp3') || name.endsWith('.mp4') ||
                 name.endsWith('.webm') || name.endsWith('.m4a');
        }).toList();
        if (files.isEmpty) {
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Belum ada lagu diunduh'),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ));
          return;
        }
        for (final f in files) {
          final name = f.path.split('/').last;
          final ext  = name.split('.').last;
          final vid  = name.replaceAll('.$ext', '');
          songs.add({
            'videoId': vid, 'title': vid, 'artist': '', 'img': '',
            'filename': vid, 'ext': ext, 'path': f.path,
          });
        }
      } catch (_) {}
    } else {
      for (final entry in fileMap.entries) {
        final videoId = entry.key;
        final val = entry.value;
        if (val is! Map) continue;
        final fn  = val['filename']?.toString() ?? videoId;
        final ext = val['ext']?.toString() ?? 'mp3';

        // Cari file dengan urutan prioritas
        String? filePath;
        final savedPath = val['path']?.toString() ?? '';

        // 1. Path tersimpan langsung
        if (savedPath.isNotEmpty && await File(savedPath).exists()) {
          filePath = savedPath;
        }
        // 2. appDir + filename.ext
        if (filePath == null) {
          final f = File('${appDir.path}/$fn.$ext');
          if (await f.exists()) filePath = f.path;
        }
        // 3. appDir + videoId.ext
        if (filePath == null) {
          final f = File('${appDir.path}/$videoId.$ext');
          if (await f.exists()) filePath = f.path;
        }
        // 4. Coba semua ekstensi umum
        if (filePath == null) {
          for (final e in ['mp3', 'mp4', 'webm', 'm4a']) {
            final f = File('${appDir.path}/$videoId.$e');
            if (await f.exists()) { filePath = f.path; break; }
          }
        }
        // 5. Scan seluruh appDir cari file yang namanya mengandung videoId
        if (filePath == null) {
          try {
            final dir = Directory(appDir.path);
            for (final f in dir.listSync().whereType<File>()) {
              if (f.path.contains(videoId)) { filePath = f.path; break; }
            }
          } catch (_) {}
        }

        if (filePath == null) continue; // benar-benar tidak ada

        // Update path di prefs jika berubah
        if (filePath != savedPath) {
          fileMap[videoId] = Map<String, dynamic>.from(val)..['path'] = filePath;
        }

        songs.add({
          'videoId':  videoId,
          'title':    val['title']?.toString()  ?? 'Unknown',
          'artist':   val['artist']?.toString() ?? '',
          'img':      val['img']?.toString()    ?? '',
          'filename': fn,
          'ext':      filePath.split('.').last,
          'path':     filePath,
        });
      }
      // Simpan path yang sudah diupdate
      await prefs.setString('downloadedFiles', json.encode(fileMap));
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

  // Dipanggil dari _OfflinePlayerSheet
  Future<void> _playOfflineSong(Map<String, dynamic> song) async {
    final title  = song['title']   as String? ?? '';
    final artist = song['artist']  as String? ?? '';
    final img    = song['img']     as String? ?? '';
    final vid    = song['videoId'] as String? ?? '';
    // Gunakan _playLocalFileDart — handle audio via just_audio
    // Jika offline (_wvc tidak bisa inject JS), tetap play audio saja
    if (_wvc != null) {
      await _playLocalFileDart(_wvc!, vid, title, artist, img);
    } else {
      // Fallback: play audio langsung tanpa WebView UI update
      await _playAudioOnly(vid, title, artist, img);
    }
  }

  Future<void> _playAudioOnly(String videoId, String title, String artist, String img) async {
    final appDir = await getApplicationDocumentsDirectory();
    File? found;
    try {
      final prefs   = await SharedPreferences.getInstance();
      final mapJson = prefs.getString('downloadedFiles') ?? '{}';
      final fileMap = Map<String, dynamic>.from(json.decode(mapJson));
      if (fileMap.containsKey(videoId)) {
        final info      = fileMap[videoId] as Map<String, dynamic>;
        final savedPath = info['path']?.toString() ?? '';
        final fn        = info['filename']?.toString() ?? videoId;
        final ex        = info['ext']?.toString() ?? 'mp3';
        for (final candidate in [
          if (savedPath.isNotEmpty) File(savedPath),
          File('${appDir.path}/$fn.$ex'),
          File('${appDir.path}/$videoId.$ex'),
        ]) {
          if (await candidate.exists()) { found = candidate; break; }
        }
      }
    } catch (_) {}
    if (found == null) {
      for (final ext in ['mp3', 'mp4', 'm4a', 'webm']) {
        final f = File('${appDir.path}/$videoId.$ext');
        if (await f.exists()) { found = f; break; }
      }
    }
    if (found == null) return;
    _stopLocalPlayer();
    try {
      await _localPlayer.setFilePath(found.path);
      await _localPlayer.play();
      WakelockPlus.enable();
      try { await _ch.invokeMethod('updateTrack', {'title': title, 'artist': artist, 'isPlaying': true, 'imgUrl': img}); } catch (_) {}
    } catch (e) {
      debugPrint('_playAudioOnly error: $e');
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
                allowFileAccessFromFileURLs: true,
                allowUniversalAccessFromFileURLs: true,
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
                useShouldInterceptRequest: true,
                // Performa: matikan fitur yang tidak perlu
                disableContextMenu: true,
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
                    // Stop local just_audio player jika sedang putar offline
                    _stopLocalPlayer();
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
                    await _playLocalFileDart(c, videoId, title, artist, img);
                  },
                );
                c.addJavaScriptHandler(
                  handlerName: 'toggleLocalPlay',
                  callback: (args) async {
                    if (_localPlayer.playing) {
                      await _localPlayer.pause();
                      _localPlaying = false;
                      try { await _ch.invokeMethod('setPlaying', {'isPlaying': false}); } catch (_) {}
                      await c.evaluateJavascript(source:
                        "(function(){isPlaying=false;window._localAudioPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(false);if(typeof _setArtPlaying==='function')_setArtPlaying(false);})();");
                    } else {
                      await _localPlayer.play();
                      _localPlaying = true;
                      try { await _ch.invokeMethod('setPlaying', {'isPlaying': true}); } catch (_) {}
                      await c.evaluateJavascript(source:
                        "(function(){isPlaying=true;window._localAudioPlaying=true;if(typeof updatePlayPauseBtn==='function')updatePlayPauseBtn(true);if(typeof _setArtPlaying==='function')_setArtPlaying(true);})();");
                    }
                  },
                );
                c.addJavaScriptHandler(
                  handlerName: 'seekLocalTo',
                  callback: (args) async {
                    final pct = args.isNotEmpty ? (double.tryParse(args[0].toString()) ?? 0.0) : 0.0;
                    final dur = _localPlayer.duration?.inMilliseconds ?? 0;
                    if (dur > 0) {
                      final pos = Duration(milliseconds: (pct / 100 * dur).round());
                      await _localPlayer.seek(pos);
                    }
                  },
                );
                c.addJavaScriptHandler(
                  handlerName: 'stopLocalPlayer',
                  callback: (args) async {
                    _stopLocalPlayer();
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
                  handlerName: 'checkForUpdate',
                  callback: (args) async {
                    // Reset flag agar bisa cek ulang meski sudah pernah cek
                    _updateChecked = false;
                    await _checkForUpdate();
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
                  handlerName: 'openExternalLogin',
                  callback: (args) async {
                    // Buka login.html di browser eksternal (Chrome) supaya OAuth redirect bisa jalan
                    final loginUrl = Uri.parse('$_base/login.html');
                    try {
                      await launchUrl(loginUrl, mode: LaunchMode.externalApplication);
                    } catch (_) {}
                  },
                );
                c.addJavaScriptHandler(
                  handlerName: 'pickProfilePhoto',
                  callback: (args) async {
                    try {
                      final picker = ImagePicker();
                      final picked = await picker.pickImage(
                        source: ImageSource.gallery,
                        maxWidth: 256,
                        maxHeight: 256,
                        imageQuality: 40,
                      );
                      if (picked == null) return;
                      final bytes = await picked.readAsBytes();
                      final b64 = base64Encode(bytes);
                      const chunkSize = 10000;
                      final total = b64.length;
                      await c.evaluateJavascript(source: "window._b64chunks=[];");
                      for (var i = 0; i < total; i += chunkSize) {
                        final end = (i + chunkSize < total) ? i + chunkSize : total;
                        final chunk = b64.substring(i, end);
                        await c.evaluateJavascript(source: "window._b64chunks.push('$chunk');");
                      }
                      await c.evaluateJavascript(source: """
                        (function(){
                          var full='data:image/jpeg;base64,'+window._b64chunks.join('');
                          window._b64chunks=null;
                          if(typeof applyProfilePhoto==='function') applyProfilePhoto(full);
                        })();
                      """);
                    } catch (e) {
                      debugPrint('pickProfilePhoto error: \$e');
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
                  _checkForUpdate();
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
                          window._manualAuth = true;
                          window._homeLoaded = false;
                          var p=JSON.parse(raw);
                          if(typeof _hideAuthScreen==='function') _hideAuthScreen();
                          if(typeof updateProfileUI==='function') updateProfileUI();
                          if(typeof loadHomeData==='function') loadHomeData();
                          if(typeof showToast==='function') showToast('Selamat datang, '+(p.name||'').split(' ')[0]+'!');
                          if(typeof _startOnlineStatus==='function') setTimeout(_startOnlineStatus, 1000);
                        } catch(e){}
                      })()
                    """);
                    // Kembali ke halaman utama setelah simpan user data
                    await c.loadUrl(urlRequest: URLRequest(url: WebUri('$_base/')));
                  }
                }
                if (urlStr.contains('vercel.app') || urlStr.contains('clone2') || urlStr.isEmpty || urlStr.contains(_localHost)) {
                  await _inject(c);
                }
                // Inject juga setelah login redirect (userData di URL) — sudah di-handle di atas
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
                  _startOnlineCheck();
                }
              },
              onPermissionRequest: (c, req) async =>
                  PermissionResponse(resources: req.resources, action: PermissionResponseAction.GRANT),
              shouldInterceptRequest: (c, req) async {
                if (req.url.host == _localHost) {
                  final path = req.url.path;
                  final filename = path.split('/').last;
                  final dotIdx = filename.lastIndexOf('.');
                  final videoId = dotIdx > 0 ? filename.substring(0, dotIdx) : filename;
                  final ext = dotIdx > 0 ? filename.substring(dotIdx + 1).toLowerCase() : 'mp3';
                  final filePath = _localFileMap[videoId];
                  if (filePath != null) {
                    try {
                      final file = File(filePath);
                      if (await file.exists()) {
                        final fileSize = await file.length();
                        final mime = ext == 'mp3' ? 'audio/mpeg'
                                   : ext == 'webm' ? 'audio/webm'
                                   : ext == 'opus' ? 'audio/ogg'
                                   : 'audio/mp4';

                        // Handle Range requests for audio seeking
                        final rangeHeader = req.headers?['Range'] ?? req.headers?['range'];
                        if (rangeHeader != null && rangeHeader.startsWith('bytes=')) {
                          final rangePart = rangeHeader.substring(6);
                          final parts = rangePart.split('-');
                          final start = int.tryParse(parts[0]) ?? 0;
                          final end = parts.length > 1 && parts[1].isNotEmpty
                              ? (int.tryParse(parts[1]) ?? (fileSize - 1))
                              : (fileSize - 1);
                          final length = end - start + 1;
                          final raf = await file.open();
                          await raf.setPosition(start);
                          final chunk = await raf.read(length);
                          await raf.close();
                          return WebResourceResponse(
                            contentType: mime,
                            data: chunk,
                            statusCode: 206,
                            reasonPhrase: 'Partial Content',
                            headers: {
                              'Content-Range': 'bytes $start-$end/$fileSize',
                              'Content-Length': length.toString(),
                              'Accept-Ranges': 'bytes',
                              'Access-Control-Allow-Origin': '*',
                              'Content-Type': mime,
                            },
                          );
                        }

                        // Full file response
                        final bytes = await file.readAsBytes();
                        return WebResourceResponse(
                          contentType: mime,
                          data: bytes,
                          statusCode: 200,
                          reasonPhrase: 'OK',
                          headers: {
                            'Content-Length': fileSize.toString(),
                            'Accept-Ranges': 'bytes',
                            'Access-Control-Allow-Origin': '*',
                            'Content-Type': mime,
                          },
                        );
                      }
                    } catch (e) {
                      debugPrint('shouldInterceptRequest error: $e');
                    }
                  }
                  return WebResourceResponse(statusCode: 404, reasonPhrase: 'Not Found', headers: {});
                }
                return null;
              },
              shouldOverrideUrlLoading: (c, nav) async {
                final url = nav.request.url?.toString() ?? '';
                if (nav.request.url?.host == _localHost) return NavigationActionPolicy.ALLOW;
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

        // Fallback untuk halaman web yang belum punya handler foto profil.
        // Dart akan memanggil applyProfilePhoto(dataUrl) setelah user pilih gambar.
        if(typeof window.applyProfilePhoto!=='function'){
          window.applyProfilePhoto=function(base64){
            try{
              if(base64) localStorage.setItem('auspotyProfilePhoto', base64);
              // Update beberapa elemen umum jika ada
              var av=document.getElementById('editProfileAvatar');
              if(av && base64) av.innerHTML='<img src=\"'+base64+'\" style=\"width:100%;height:100%;border-radius:50%;object-fit:cover;\">';
              if(typeof updateProfileUI==='function') updateProfileUI();
              if(typeof showToast==='function') showToast('Foto profil diperbarui!');
            }catch(e){}
          };
        }

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
  Map<String, dynamic>? _currentSong;

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _play(Map<String, dynamic> song) async {
    setState(() {
      _playingId = song['videoId'] as String;
      _currentSong = song;
    });
    // Delegasikan ke parent — _playLocalFileDart yang handle audio + UI
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
            Container(
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
                const Icon(Icons.equalizer, color: Color(0xFFa78bfa), size: 24),
              ]),
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

// ─── Update Dialog ────────────────────────────────────────────────────────────
class _UpdateDialog extends StatelessWidget {
  final String currentVersion;
  final String newVersion;
  final String releaseNotes;
  final String apkUrl;
  final VoidCallback onDownload;

  const _UpdateDialog({
    required this.currentVersion,
    required this.newVersion,
    required this.releaseNotes,
    required this.apkUrl,
    required this.onDownload,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF1a1a2e),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Row(children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFFa78bfa).withOpacity(0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.system_update, color: Color(0xFFa78bfa), size: 24),
        ),
        const SizedBox(width: 12),
        const Expanded(
          child: Text('Update Tersedia', style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold)),
        ),
      ]),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _versionChip(currentVersion, Colors.white24, Colors.white54),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Icon(Icons.arrow_forward, color: Color(0xFFa78bfa), size: 18),
          ),
          _versionChip(newVersion, const Color(0xFFa78bfa).withOpacity(0.2), const Color(0xFFa78bfa)),
        ]),
        if (releaseNotes.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('Yang baru:', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Container(
            constraints: const BoxConstraints(maxHeight: 120),
            child: SingleChildScrollView(
              child: Text(
                releaseNotes.length > 300 ? '${releaseNotes.substring(0, 300)}...' : releaseNotes,
                style: const TextStyle(color: Colors.white54, fontSize: 12, height: 1.5),
              ),
            ),
          ),
        ],
        const SizedBox(height: 8),
      ]),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context, rootNavigator: true).pop(),
          child: const Text('Nanti', style: TextStyle(color: Colors.white38)),
        ),
        ElevatedButton.icon(
          onPressed: onDownload,
          icon: const Icon(Icons.download, size: 18),
          label: const Text('Update Sekarang', style: TextStyle(fontWeight: FontWeight.bold)),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFa78bfa),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          ),
        ),
      ],
    );
  }

  Widget _versionChip(String version, Color bg, Color fg) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
    child: Text('v$version', style: TextStyle(color: fg, fontSize: 13, fontWeight: FontWeight.bold)),
  );
}
