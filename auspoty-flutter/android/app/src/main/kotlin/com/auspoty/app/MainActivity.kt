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

    // Flag: jika true, jangan pause WebView saat Activity pause
    @Volatile var bgModeActive = false

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
                "updateTrack" -> {
                    val title   = call.argument<String>("title")      ?: ""
                    val artist  = call.argument<String>("artist")     ?: ""
                    val playing = call.argument<Boolean>("isPlaying") ?: true
                    bgModeActive = true
                    svc?.updateTrackInfo(title, artist, playing)
                    result.success(null)
                }
                "setPlaying" -> {
                    val playing = call.argument<Boolean>("isPlaying") ?: false
                    if (!playing) bgModeActive = false
                    svc?.setPlaying(playing)
                    result.success(null)
                }
                "keepAlive" -> {
                    // Dipanggil saat app masuk background dengan bgMode aktif
                    // Pastikan service tetap jalan dan wakelock aktif
                    svc?.keepAlive()
                    result.success(null)
                }
                "stopService" -> {
                    bgModeActive = false
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

    /**
     * KUNCI UTAMA: Override onPause agar WebView tidak di-pause saat bgMode aktif.
     * Secara default FlutterActivity memanggil webView.onPause() di sini,
     * yang menyebabkan YouTube IFrame berhenti.
     */
    override fun onPause() {
        if (bgModeActive) {
            // Skip super.onPause() untuk Flutter engine agar WebView tidak di-pause
            // Tapi tetap panggil Activity.onPause() untuk lifecycle yang benar
            android.app.Activity::class.java.getMethod("onPause").invoke(this)
        } else {
            super.onPause()
        }
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
