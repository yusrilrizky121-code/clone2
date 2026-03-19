package com.auspoty.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.webkit.WebView
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object {
        const val SERVICE_CHANNEL = "com.auspoty.app/service"
    }

    private var serviceChannel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        serviceChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, SERVICE_CHANNEL)
        serviceChannel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                // Dipanggil dari JS via Flutter handler saat lagu mulai/pause
                "updateNotif" -> {
                    val title   = call.argument<String>("title")   ?: "Auspoty"
                    val artist  = call.argument<String>("artist")  ?: ""
                    val playing = call.argument<Boolean>("playing") ?: true
                    val intent  = Intent(this, MusicPlayerService::class.java).apply {
                        action = MusicPlayerService.ACTION_UPDATE_NOTIF
                        putExtra(MusicPlayerService.EXTRA_TITLE,   title)
                        putExtra(MusicPlayerService.EXTRA_ARTIST,  artist)
                        putExtra(MusicPlayerService.EXTRA_PLAYING, playing)
                    }
                    startServiceSafe(intent)
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
        setupNotifCallbacks()
    }

    override fun onResume() {
        super.onResume()
        // Re-setup callbacks saat app kembali ke foreground
        setupNotifCallbacks()
    }

    /**
     * Set callback ke service — saat tombol notifikasi ditekan,
     * forward command ke WebView via MethodChannel ke Flutter/Dart,
     * lalu Dart evaluateJavascript ke WebView.
     */
    private fun setupNotifCallbacks() {
        MusicPlayerService.onPlayPause = {
            runOnUiThread {
                serviceChannel?.invokeMethod("onPlayPause", null)
            }
        }
        MusicPlayerService.onNext = {
            runOnUiThread {
                serviceChannel?.invokeMethod("onNext", null)
            }
        }
        MusicPlayerService.onPrev = {
            runOnUiThread {
                serviceChannel?.invokeMethod("onPrev", null)
            }
        }
    }

    private fun startServiceSafe(intent: Intent) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Exception) {
            android.util.Log.e("MainActivity", "startService error: ${e.message}")
        }
    }
}
