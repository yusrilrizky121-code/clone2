package com.auspoty.app

import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.webkit.WebView
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object {
        const val CHANNEL = "com.auspoty.app/player"
    }

    private var service: MusicPlayerService? = null
    private var bound = false
    private var channel: MethodChannel? = null

    private val conn = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            service = (binder as MusicPlayerService.LocalBinder).getService()
            bound = true
            setupServiceCallbacks()
        }
        override fun onServiceDisconnected(name: ComponentName?) {
            bound = false; service = null
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel!!.setMethodCallHandler { call, result ->
            val svc = service
            when (call.method) {
                // Dipanggil dari Dart saat JS minta play lagu
                "play" -> {
                    val videoId   = call.argument<String>("videoId")   ?: ""
                    val title     = call.argument<String>("title")     ?: ""
                    val artist    = call.argument<String>("artist")    ?: ""
                    val thumbnail = call.argument<String>("thumbnail") ?: ""
                    if (videoId.isNotEmpty()) {
                        startServiceSafe(Intent(this, MusicPlayerService::class.java).apply {
                            action = MusicPlayerService.ACTION_PLAY
                            putExtra(MusicPlayerService.EXTRA_VIDEO_ID,  videoId)
                            putExtra(MusicPlayerService.EXTRA_TITLE,     title)
                            putExtra(MusicPlayerService.EXTRA_ARTIST,    artist)
                            putExtra(MusicPlayerService.EXTRA_THUMBNAIL, thumbnail)
                        })
                    }
                    result.success(null)
                }
                "pause"  -> { svc?.pausePlayer();  result.success(null) }
                "resume" -> { svc?.resumePlayer(); result.success(null) }
                "togglePlayPause" -> { svc?.togglePlayPause(); result.success(null) }
                "stop"   -> { svc?.stopPlayer();   result.success(null) }
                "seekTo" -> {
                    val ms = call.argument<Int>("positionMs") ?: 0
                    svc?.seekTo(ms.toLong())
                    result.success(null)
                }
                "getPosition" -> result.success((svc?.getPosition() ?: 0L).toInt())
                "getDuration" -> result.success((svc?.getDuration() ?: 0L).toInt())
                "isPlaying"   -> result.success(svc?.isCurrentlyPlaying() ?: false)
                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(false)
        startServiceSafe(Intent(this, MusicPlayerService::class.java))
        bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
    }

    override fun onResume() {
        super.onResume()
        if (!bound) bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
        setupServiceCallbacks()
    }

    override fun onDestroy() {
        if (bound) { unbindService(conn); bound = false }
        super.onDestroy()
    }

    /**
     * Set callback ke service — saat tombol notifikasi ditekan,
     * kirim ke Flutter via MethodChannel → Flutter evaluateJavascript ke WebView.
     */
    private fun setupServiceCallbacks() {
        MusicPlayerService.onPlayPause = {
            runOnUiThread { channel?.invokeMethod("onPlayPause", null) }
        }
        MusicPlayerService.onNext = {
            runOnUiThread { channel?.invokeMethod("onNext", null) }
        }
        MusicPlayerService.onPrev = {
            runOnUiThread { channel?.invokeMethod("onPrev", null) }
        }
        MusicPlayerService.onCompleted = {
            runOnUiThread { channel?.invokeMethod("onCompleted", null) }
        }
    }

    private fun startServiceSafe(intent: Intent) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent)
            else startService(intent)
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "startService: ${e.message}")
        }
    }
}
