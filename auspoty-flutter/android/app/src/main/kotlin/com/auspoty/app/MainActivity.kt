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

    private var musicService: MusicPlayerService? = null
    private var serviceBound = false
    private var methodChannel: MethodChannel? = null

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            musicService = (binder as MusicPlayerService.LocalBinder).getService()
            serviceBound = true
            MusicPlayerService.flutterChannel = methodChannel
        }
        override fun onServiceDisconnected(name: ComponentName?) {
            serviceBound = false
            musicService = null
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        methodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        methodChannel!!.setMethodCallHandler { call, result ->
            when (call.method) {

                // Flutter kirim videoId → service fetch URL sendiri (self-contained)
                "playByVideoId" -> {
                    val videoId = call.argument<String>("videoId") ?: ""
                    val title   = call.argument<String>("title")   ?: ""
                    val artist  = call.argument<String>("artist")  ?: ""
                    val thumb   = call.argument<String>("thumbnail") ?: ""
                    ensureServiceStarted()
                    doWithService { it.playByVideoId(videoId, title, artist, thumb) }
                    result.success(null)
                }

                // Flutter sudah punya URL → kirim langsung ke service (lebih cepat)
                "playUrl" -> {
                    val url    = call.argument<String>("url")       ?: ""
                    val title  = call.argument<String>("title")     ?: ""
                    val artist = call.argument<String>("artist")    ?: ""
                    val thumb  = call.argument<String>("thumbnail") ?: ""
                    ensureServiceStarted()
                    doWithService { it.playDirectUrl(url, title, artist, thumb) }
                    result.success(null)
                }

                "pause"  -> { doWithService { it.pause() };  result.success(null) }
                "resume" -> { doWithService { it.resume() }; result.success(null) }

                "seekTo" -> {
                    val ms = call.argument<Int>("positionMs") ?: 0
                    doWithService { it.seekTo(ms.toLong()) }
                    result.success(null)
                }

                "isPlaying"   -> result.success(musicService?.isPlaying() ?: false)
                "getPosition" -> result.success(musicService?.currentPosition()?.toInt() ?: 0)
                "getDuration" -> result.success(musicService?.duration()?.toInt() ?: 0)

                "stopService" -> {
                    stopService(Intent(this, MusicPlayerService::class.java))
                    result.success(null)
                }

                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(false)
        ensureServiceStarted()
        bindMusicService()
    }

    override fun onDestroy() {
        if (serviceBound) {
            unbindService(serviceConnection)
            serviceBound = false
        }
        super.onDestroy()
    }

    /**
     * Jalankan aksi pada service.
     * Jika belum bound, bind dulu lalu delay sedikit.
     */
    private fun doWithService(action: (MusicPlayerService) -> Unit) {
        if (serviceBound && musicService != null) {
            action(musicService!!)
        } else {
            bindMusicService()
            android.os.Handler(mainLooper).postDelayed({
                musicService?.let { action(it) }
            }, 500)
        }
    }

    private fun ensureServiceStarted() {
        val intent = Intent(this, MusicPlayerService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun bindMusicService() {
        if (!serviceBound) {
            bindService(
                Intent(this, MusicPlayerService::class.java),
                serviceConnection,
                BIND_AUTO_CREATE
            )
        }
    }
}
