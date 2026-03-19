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

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // Channel untuk update notifikasi dari JS (via Flutter handler)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, SERVICE_CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
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
        // Start foreground service saat app buka — jaga proses tetap hidup
        startServiceSafe(Intent(this, MusicPlayerService::class.java))
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
