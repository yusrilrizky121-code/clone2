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
        const val CHANNEL = "com.auspoty.app/music"
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
                // Dipanggil dari Dart saat lagu mulai diputar
                "updateTrack" -> {
                    val title   = call.argument<String>("title")     ?: ""
                    val artist  = call.argument<String>("artist")    ?: ""
                    val playing = call.argument<Boolean>("isPlaying") ?: true
                    svc?.updateTrackInfo(title, artist, playing)
                    result.success(null)
                }
                "setPlaying" -> {
                    val playing = call.argument<Boolean>("isPlaying") ?: false
                    svc?.setPlaying(playing)
                    result.success(null)
                }
                "stopService" -> {
                    svc?.setPlaying(false)
                    result.success(null)
                }
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
     * Saat tombol notifikasi ditekan → kirim ke Flutter via MethodChannel
     * → Flutter evaluateJavascript ke WebView → ytPlayer play/pause/next/prev
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
