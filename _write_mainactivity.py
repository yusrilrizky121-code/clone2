#!/usr/bin/env python3
"""Tulis ulang MainActivity.kt dengan pendekatan yang benar."""

content = '''package com.auspoty.app

import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Bundle
import android.os.IBinder
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

    @Volatile private var musicPlaying = false

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
            when (call.method) {
                "updateTrack" -> {
                    val title   = call.argument<String>("title")      ?: ""
                    val artist  = call.argument<String>("artist")     ?: ""
                    val playing = call.argument<Boolean>("isPlaying") ?: true
                    musicPlaying = playing
                    service?.updateTrackInfo(title, artist, playing)
                    result.success(null)
                }
                "setPlaying" -> {
                    val playing = call.argument<Boolean>("isPlaying") ?: false
                    musicPlaying = playing
                    service?.setPlaying(playing)
                    result.success(null)
                }
                "keepAlive" -> {
                    service?.keepAlive()
                    result.success(null)
                }
                "stopService" -> {
                    musicPlaying = false
                    service?.setPlaying(false)
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startServiceSafe(Intent(this, MusicPlayerService::class.java))
        bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
    }

    /**
     * KUNCI UTAMA: Saat musik jalan, kita TIDAK memanggil super.onPause()
     * yang akan suspend Flutter engine dan pause WebView/YouTube IFrame.
     *
     * Pendekatan: override onPause() dan hanya panggil Activity.onPause()
     * dari Android framework langsung (bukan FlutterActivity.onPause()).
     *
     * Ini mencegah YouTube IFrame berhenti karena WebView tidak di-suspend.
     */
    override fun onPause() {
        if (musicPlaying) {
            // Panggil Activity.onPause() langsung, skip FlutterActivity.onPause()
            // FlutterActivity.onPause() → flutterView.onPause() → suspend engine → YouTube stop
            try {
                val method = android.app.Activity::class.java.getDeclaredMethod("onPause")
                method.isAccessible = true
                method.invoke(this)
            } catch (e: Exception) {
                // Fallback: tetap panggil super tapi pastikan service jalan
                super.onPause()
            }
            service?.keepAlive()
        } else {
            super.onPause()
        }
    }

    override fun onResume() {
        super.onResume()
        if (!bound) {
            bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
        }
        setupServiceCallbacks()
        if (musicPlaying) service?.setPlaying(true)
    }

    override fun onDestroy() {
        if (bound) { unbindService(conn); bound = false }
        super.onDestroy()
    }

    private fun setupServiceCallbacks() {
        MusicPlayerService.onPlayPause = {
            runOnUiThread {
                musicPlaying = !musicPlaying
                service?.setPlaying(musicPlaying)
                channel?.invokeMethod("onPlayPause", null)
            }
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
'''

path = 'auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MainActivity.kt'
open(path, 'w', encoding='utf-8').write(content)
print("Wrote MainActivity.kt, lines:", len(content.split('\n')))
print("onPause override:", 'override fun onPause' in content)
print("musicPlaying check:", 'if (musicPlaying)' in content)
print("Activity.onPause reflection:", 'android.app.Activity' in content)
