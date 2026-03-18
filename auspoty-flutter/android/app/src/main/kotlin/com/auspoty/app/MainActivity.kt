package com.auspoty.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.webkit.WebView
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.FlutterEngineCache
import io.flutter.embedding.engine.dart.DartExecutor
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object {
        const val ENGINE_ID = "auspoty_engine"
        const val CHANNEL = "com.auspoty.app/music"
    }

    override fun provideFlutterEngine(context: android.content.Context): FlutterEngine? {
        // Gunakan cached engine supaya tidak di-destroy saat activity lifecycle
        if (FlutterEngineCache.getInstance().contains(ENGINE_ID)) {
            return FlutterEngineCache.getInstance().get(ENGINE_ID)
        }
        val engine = FlutterEngine(context)
        engine.dartExecutor.executeDartEntrypoint(DartExecutor.DartEntrypoint.createDefault())
        FlutterEngineCache.getInstance().put(ENGINE_ID, engine)
        return engine
    }

    override fun shouldDestroyEngineWithHost(): Boolean {
        // KRITIS: Jangan destroy engine saat activity di-destroy
        // Engine tetap hidup di background
        return false
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "startMusicService" -> {
                    val title = call.argument<String>("title") ?: "Auspoty"
                    val artist = call.argument<String>("artist") ?: ""
                    startMusicService(title, artist)
                    result.success(null)
                }
                "stopMusicService" -> {
                    stopService(Intent(this, MusicForegroundService::class.java))
                    result.success(null)
                }
                "keepWebViewAlive" -> {
                    result.success(null)
                }
                "resumeEngine" -> {
                    // Dipanggil dari Flutter saat app ke background
                    // Kirim signal resumed supaya engine tidak pause WebView
                    flutterEngine.lifecycleChannel.appIsResumed()
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(false)
        startMusicService("Auspoty", "Siap memutar musik")
    }

    override fun onPause() {
        // Skip FlutterActivity.onPause() yang pause engine
        // Langsung panggil Activity.onPause()
        try {
            val method = android.app.Activity::class.java.getDeclaredMethod("onPause")
            method.isAccessible = true
            method.invoke(this)
        } catch (e: Exception) {
            super.onPause()
        }
        // Paksa engine tetap dalam state "resumed"
        flutterEngine?.lifecycleChannel?.appIsResumed()
    }

    override fun onStop() {
        // Skip FlutterActivity.onStop() yang pause engine
        try {
            val method = android.app.Activity::class.java.getDeclaredMethod("onStop")
            method.isAccessible = true
            method.invoke(this)
        } catch (e: Exception) {
            super.onStop()
        }
        // Paksa engine tetap dalam state "resumed"
        flutterEngine?.lifecycleChannel?.appIsResumed()
    }

    override fun onResume() {
        super.onResume()
        flutterEngine?.lifecycleChannel?.appIsResumed()
    }

    override fun onStart() {
        super.onStart()
    }

    override fun onDestroy() {
        // Jangan panggil super.onDestroy() yang akan destroy engine
        // Hanya stop service
        stopService(Intent(this, MusicForegroundService::class.java))
        try {
            val method = android.app.Activity::class.java.getDeclaredMethod("onDestroy")
            method.isAccessible = true
            method.invoke(this)
        } catch (e: Exception) {
            // ignore
        }
    }

    private fun startMusicService(title: String, artist: String) {
        val intent = Intent(this, MusicForegroundService::class.java).apply {
            putExtra("title", title)
            putExtra("artist", artist)
            action = "START"
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }
}
