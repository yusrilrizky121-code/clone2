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

                // Semua command dikirim via Intent — tidak butuh Flutter engine setelah ini
                "playByVideoId" -> {
                    val videoId = call.argument<String>("videoId") ?: ""
                    val title   = call.argument<String>("title")   ?: ""
                    val artist  = call.argument<String>("artist")  ?: ""
                    val thumb   = call.argument<String>("thumbnail") ?: ""
                    startServiceIntent(MusicPlayerService.ACTION_PLAY) {
                        putExtra(MusicPlayerService.EXTRA_VIDEO_ID,  videoId)
                        putExtra(MusicPlayerService.EXTRA_TITLE,     title)
                        putExtra(MusicPlayerService.EXTRA_ARTIST,    artist)
                        putExtra(MusicPlayerService.EXTRA_THUMBNAIL, thumb)
                    }
                    result.success(null)
                }

                "pause"  -> { startServiceIntent(MusicPlayerService.ACTION_PAUSE);  result.success(null) }
                "resume" -> { startServiceIntent(MusicPlayerService.ACTION_RESUME); result.success(null) }
                "stopService" -> { startServiceIntent(MusicPlayerService.ACTION_STOP); result.success(null) }

                "seekTo" -> {
                    val ms = call.argument<Int>("positionMs") ?: 0
                    startServiceIntent(MusicPlayerService.ACTION_SEEK) {
                        putExtra(MusicPlayerService.EXTRA_SEEK_MS, ms.toLong())
                    }
                    result.success(null)
                }

                // Query state — pakai singleton instance (tidak butuh binding)
                "isPlaying"   -> result.success(
                    MusicPlayerService.instance?.isPlaying() ?: false
                )
                "getPosition" -> result.success(
                    (MusicPlayerService.instance?.getPosition() ?: 0L).toInt()
                )
                "getDuration" -> result.success(
                    (MusicPlayerService.instance?.getDuration() ?: 0L).toInt()
                )

                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(false)
        // Start service saat app pertama kali buka
        startServiceIntent(null)
        bindMusicService()
    }

    override fun onResume() {
        super.onResume()
        // Re-set channel saat app kembali ke foreground
        MusicPlayerService.flutterChannel = methodChannel
        if (!serviceBound) bindMusicService()
    }

    override fun onStop() {
        super.onStop()
        // Hapus channel saat app ke background — service tidak akan crash saat callback
        MusicPlayerService.flutterChannel = null
    }

    override fun onDestroy() {
        if (serviceBound) {
            unbindService(serviceConnection)
            serviceBound = false
        }
        super.onDestroy()
    }

    /**
     * Kirim Intent ke service.
     * Ini cara yang benar — tidak bergantung pada Flutter engine atau binding.
     */
    private fun startServiceIntent(action: String?, extras: (Intent.() -> Unit)? = null) {
        val intent = Intent(this, MusicPlayerService::class.java).apply {
            if (action != null) this.action = action
            extras?.invoke(this)
        }
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
