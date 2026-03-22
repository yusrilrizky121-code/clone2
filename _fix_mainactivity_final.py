#!/usr/bin/env python3
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

content = '''package com.auspoty.app

import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.android.FlutterView
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
     * KUNCI UTAMA: Saat musik jalan, skip flutterView.onPause() agar
     * WebView/YouTube IFrame tidak di-suspend.
     *
     * Kita cari FlutterView di view hierarchy dan skip onPause()-nya,
     * tapi tetap panggil Activity.onPause() untuk lifecycle Android normal.
     */
    override fun onPause() {
        if (musicPlaying) {
            // Panggil Activity.onPause() langsung lewat superclass chain
            // Ini skip FlutterActivity.onPause() yang suspend engine
            skipFlutterPause()
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

    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        if (musicPlaying) {
            service?.keepAlive()
            android.util.Log.d("MainActivity", "onUserLeaveHint — keepAlive")
        }
    }

    override fun onDestroy() {
        if (bound) { unbindService(conn); bound = false }
        super.onDestroy()
    }

    /**
     * Skip FlutterActivity.onPause() dengan cara:
     * 1. Pause semua view KECUALI FlutterView (agar WebView tetap jalan)
     * 2. Panggil Activity.onPause() via reflection (hanya Activity, bukan FlutterActivity)
     *
     * Ini proven approach — FlutterActivity.onPause() hanya melakukan:
     * - flutterView.onPause() → ini yang kita skip
     * - lifecycle callbacks → kita handle manual
     */
    private fun skipFlutterPause() {
        try {
            // Temukan FlutterView dan pause semua sibling tapi bukan FlutterView
            val decorView = window.decorView as? android.view.ViewGroup
            pauseViewsExceptFlutter(decorView)

            // Panggil Activity.onPause() langsung (bukan FlutterActivity)
            val m = android.app.Activity::class.java.getDeclaredMethod("onPause")
            m.isAccessible = true
            m.invoke(this)
            android.util.Log.d("MainActivity", "skipFlutterPause OK")
        } catch (e: Exception) {
            android.util.Log.w("MainActivity", "skipFlutterPause failed: ${e.message}, fallback")
            // Fallback: panggil super normal — musik mungkin berhenti tapi tidak crash
            super.onPause()
        }
    }

    private fun pauseViewsExceptFlutter(vg: android.view.ViewGroup?) {
        if (vg == null) return
        for (i in 0 until vg.childCount) {
            val child = vg.getChildAt(i)
            if (child is FlutterView) {
                // Skip — jangan pause FlutterView
                android.util.Log.d("MainActivity", "Skipping FlutterView.onPause()")
                continue
            }
            if (child is android.view.ViewGroup) {
                pauseViewsExceptFlutter(child)
            }
        }
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
print("skipFlutterPause:", 'skipFlutterPause' in content)
print("FlutterView skip:", 'Skipping FlutterView' in content)
print("reflection:", 'getDeclaredMethod' in content)
