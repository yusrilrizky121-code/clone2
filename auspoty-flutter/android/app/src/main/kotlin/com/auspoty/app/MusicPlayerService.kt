package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID   = "auspoty_player"
        const val NOTIF_ID     = 42
        const val API_BASE     = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app"
        const val TAG          = "MusicPlayerService"

        const val ACTION_PLAY   = "com.auspoty.app.PLAY"
        const val ACTION_PAUSE  = "com.auspoty.app.PAUSE"
        const val ACTION_RESUME = "com.auspoty.app.RESUME"
        const val ACTION_STOP   = "com.auspoty.app.STOP"
        const val ACTION_SEEK   = "com.auspoty.app.SEEK"

        const val EXTRA_VIDEO_ID  = "videoId"
        const val EXTRA_TITLE     = "title"
        const val EXTRA_ARTIST    = "artist"
        const val EXTRA_THUMBNAIL = "thumbnail"
        const val EXTRA_SEEK_MS   = "seekMs"

        // Flutter channel — hanya dipakai saat app di-foreground
        var flutterChannel: MethodChannel? = null
        var instance: MusicPlayerService? = null
    }

    private lateinit var player: ExoPlayer
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var currentTitle  = "Auspoty"
    private var currentArtist = ""
    private var currentVideoId = ""

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()

    override fun onBind(intent: Intent?): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::PlayerWakeLock")
        wakeLock?.setReferenceCounted(false)

        player = ExoPlayer.Builder(this).build().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.CONTENT_TYPE_MUSIC)
                    .build(),
                true
            )
            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == Player.STATE_ENDED) {
                        // Hanya callback ke Flutter jika channel tersedia (app di-foreground)
                        val ch = flutterChannel
                        if (ch != null) {
                            scope.launch { ch.invokeMethod("onCompleted", null) }
                        }
                        // Lepas wakelock saat selesai
                        if (wakeLock?.isHeld == true) {
                            try { wakeLock?.release() } catch (_: Exception) {}
                        }
                    }
                }
            })
        }

        startForegroundCompat(buildNotification("Auspoty", "Siap memutar musik"))
        Log.d(TAG, "Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "onStartCommand action=${intent?.action}")
        when (intent?.action) {
            ACTION_PLAY -> {
                val videoId  = intent.getStringExtra(EXTRA_VIDEO_ID)  ?: return START_STICKY
                val title    = intent.getStringExtra(EXTRA_TITLE)     ?: ""
                val artist   = intent.getStringExtra(EXTRA_ARTIST)    ?: ""
                val thumbUrl = intent.getStringExtra(EXTRA_THUMBNAIL) ?: ""
                currentVideoId = videoId
                playByVideoId(videoId, title, artist, thumbUrl)
            }
            ACTION_PAUSE  -> {
                player.pause()
                updateNotification(currentTitle, currentArtist)
            }
            ACTION_RESUME -> {
                player.play()
                updateNotification(currentTitle, currentArtist)
            }
            ACTION_STOP   -> {
                player.stop()
                player.clearMediaItems()
                if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
            ACTION_SEEK   -> {
                val ms = intent.getLongExtra(EXTRA_SEEK_MS, -1L)
                if (ms >= 0) player.seekTo(ms)
            }
            else -> {
                // Service di-restart oleh Android (START_STICKY) — tidak ada action
                // Biarkan saja, ExoPlayer masih punya state
                Log.d(TAG, "Service restarted by Android (no action)")
            }
        }
        return START_STICKY
    }

    private fun playByVideoId(videoId: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist
        startForegroundCompat(buildNotification(currentTitle, "Memuat..."))

        scope.launch(Dispatchers.IO) {
            try {
                Log.d(TAG, "Fetching stream URL: $videoId")
                val streamUrl = fetchStreamUrl(videoId)
                withContext(Dispatchers.Main) {
                    if (streamUrl != null) {
                        playUrl(streamUrl, title, artist, thumbUrl)
                    } else {
                        Log.e(TAG, "Stream URL null for $videoId")
                        updateNotification(currentTitle, "Gagal memuat audio")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "playByVideoId error: ${e.message}")
            }
        }
    }

    private fun fetchStreamUrl(videoId: String): String? {
        return try {
            val url  = URL("$API_BASE/api/stream")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Accept", "application/json")
            conn.doOutput       = true
            conn.connectTimeout = 30_000
            conn.readTimeout    = 60_000

            val body = """{"videoId":"$videoId"}"""
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }

            val code = conn.responseCode
            Log.d(TAG, "API response: $code")
            if (code == 200) {
                val text = conn.inputStream.bufferedReader(Charsets.UTF_8).readText()
                val json = JSONObject(text)
                if (json.optString("status") == "success") {
                    json.optString("url").takeIf { it.isNotEmpty() }
                } else {
                    Log.e(TAG, "API error: ${json.optString("message")}")
                    null
                }
            } else {
                Log.e(TAG, "HTTP $code")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "fetchStreamUrl: ${e.message}")
            null
        }
    }

    fun playUrl(url: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist

        val item = MediaItem.Builder()
            .setUri(url)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(currentTitle)
                    .setArtist(currentArtist)
                    .setArtworkUri(
                        if (thumbUrl.isNotEmpty()) android.net.Uri.parse(thumbUrl) else null
                    )
                    .build()
            )
            .build()

        player.setMediaItem(item)
        player.prepare()
        player.play()

        // Acquire wakelock — CPU tetap aktif saat layar mati
        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)
        startForegroundCompat(buildNotification(currentTitle, currentArtist))
        Log.d(TAG, "Playing: $currentTitle")
    }

    // Akses langsung dari MainActivity (saat bound)
    fun pausePlayer()    = player.pause()
    fun resumePlayer()   = player.play()
    fun isPlaying()      = player.isPlaying
    fun getPosition()    = player.currentPosition
    fun getDuration()    = if (player.duration == C.TIME_UNSET) 0L else player.duration
    fun seekTo(ms: Long) = player.seekTo(ms)

    /**
     * KRITIS: stopWithTask="false" di manifest + override ini
     * memastikan service tidak mati saat app di-swipe dari recents.
     */
    override fun onTaskRemoved(rootIntent: Intent?) {
        Log.d(TAG, "onTaskRemoved — isPlaying=${player.isPlaying}")
        if (player.isPlaying) {
            // Musik sedang jalan — jangan stop, restart jika perlu
            val restartIntent = Intent(applicationContext, MusicPlayerService::class.java)
            val pi = PendingIntent.getService(
                applicationContext, 1, restartIntent,
                PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
            )
            val am = getSystemService(ALARM_SERVICE) as android.app.AlarmManager
            am.set(android.app.AlarmManager.ELAPSED_REALTIME, 1000, pi)
        } else {
            stopSelf()
        }
        // Tidak call super
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        scope.cancel()
        player.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }

    private fun updateNotification(title: String, text: String) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification(title, text))
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    private fun buildNotification(title: String, text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text.ifEmpty { "Sedang memutar" })
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                CHANNEL_ID, "Auspoty Music", NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Kontrol musik Auspoty"
                setSound(null, null)
                enableVibration(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(ch)
        }
    }
}
