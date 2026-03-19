package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaSession
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * MusicPlayerService — arsitektur self-contained.
 *
 * KUNCI: Service fetch stream URL sendiri via HTTP (tidak bergantung Flutter engine).
 * Flutter hanya kirim videoId + metadata. Service yang handle sisanya.
 * Dengan begitu, saat Flutter engine mati (app di-background/swipe),
 * ExoPlayer tetap jalan karena sudah punya URL dan tidak butuh Flutter lagi.
 */
class MusicPlayerService : MediaLibraryService() {

    companion object {
        const val CHANNEL_ID = "auspoty_player"
        const val NOTIF_ID   = 42
        const val API_BASE   = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app"

        // Flutter channel untuk callback (onCompleted, onNext, onPrev)
        var flutterChannel: MethodChannel? = null
        var instance: MusicPlayerService? = null
    }

    private lateinit var player: ExoPlayer
    private lateinit var mediaSession: MediaLibrarySession
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // Metadata lagu saat ini (untuk notifikasi)
    private var currentTitle  = "Auspoty"
    private var currentArtist = ""

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession = mediaSession

    override fun onBind(intent: Intent?): IBinder? = super.onBind(intent) ?: binder

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        // WakeLock — CPU tetap aktif saat layar mati / background
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::PlayerWakeLock")
        wakeLock?.setReferenceCounted(false)

        // ExoPlayer dengan audio focus otomatis
        player = ExoPlayer.Builder(this).build().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus= */ true
            )
            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == Player.STATE_ENDED) {
                        scope.launch {
                            flutterChannel?.invokeMethod("onCompleted", null)
                        }
                    }
                }
            })
        }

        // MediaLibrarySession — register ke Android sebagai media player proper
        mediaSession = MediaLibrarySession.Builder(
            this, player,
            object : MediaLibrarySession.Callback {
                override fun onGetLibraryRoot(
                    session: MediaLibrarySession,
                    browser: MediaSession.ControllerInfo,
                    params: LibraryParams?
                ): ListenableFuture<LibraryResult<MediaItem>> =
                    Futures.immediateFuture(
                        LibraryResult.ofItem(
                            MediaItem.Builder().setMediaId("root").build(), params
                        )
                    )
            }
        )
            .setSessionActivity(
                PendingIntent.getActivity(
                    this, 0,
                    Intent(this, MainActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    },
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            )
            .build()

        // Langsung start foreground saat onCreate
        startForegroundCompat(buildNotification("Auspoty", "Siap memutar musik"))
    }

    /**
     * FUNGSI UTAMA: Fetch stream URL dari Vercel API di Kotlin (bukan Flutter),
     * lalu langsung play. Tidak butuh Flutter engine sama sekali setelah ini.
     */
    fun playByVideoId(videoId: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist

        // Update notifikasi dengan info lagu
        startForegroundCompat(buildNotification(currentTitle, currentArtist))

        // Fetch URL di background thread, play di main thread
        scope.launch(Dispatchers.IO) {
            try {
                val streamUrl = fetchStreamUrl(videoId)
                if (streamUrl != null) {
                    withContext(Dispatchers.Main) {
                        playDirectUrl(streamUrl, title, artist, thumbUrl)
                    }
                }
            } catch (e: Exception) {
                // Gagal fetch — tidak crash, cukup log
                android.util.Log.e("MusicPlayerService", "fetchStreamUrl error: ${e.message}")
            }
        }
    }

    /**
     * Fetch stream URL dari Vercel API menggunakan HttpURLConnection (pure Kotlin, no OkHttp needed).
     * Dipanggil dari background thread.
     */
    private fun fetchStreamUrl(videoId: String): String? {
        return try {
            val url = URL("$API_BASE/api/stream")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.doOutput = true
            conn.connectTimeout = 30_000
            conn.readTimeout = 30_000

            val body = """{"videoId":"$videoId"}"""
            conn.outputStream.use { it.write(body.toByteArray()) }

            val responseCode = conn.responseCode
            if (responseCode == 200) {
                val response = conn.inputStream.bufferedReader().readText()
                val json = JSONObject(response)
                if (json.optString("status") == "success") {
                    json.optString("url").takeIf { it.isNotEmpty() }
                } else null
            } else null
        } catch (e: Exception) {
            android.util.Log.e("MusicPlayerService", "HTTP error: ${e.message}")
            null
        }
    }

    /**
     * Play URL langsung (sudah punya URL, tidak perlu fetch lagi).
     * Dipanggil dari Flutter jika URL sudah tersedia.
     */
    fun playDirectUrl(url: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist

        val mediaItem = MediaItem.Builder()
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

        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()

        // WakeLock max 6 jam
        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)

        // Update notifikasi
        startForegroundCompat(buildNotification(currentTitle, currentArtist))
    }

    fun pause()  { player.pause() }
    fun resume() { player.play() }
    fun stop()   { player.stop(); player.clearMediaItems() }
    fun seekTo(posMs: Long) { player.seekTo(posMs) }
    fun isPlaying()       = player.isPlaying
    fun currentPosition() = player.currentPosition
    fun duration()        = if (player.duration == C.TIME_UNSET) 0L else player.duration

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        return START_STICKY
    }

    /**
     * Pattern Metrolist yang benar:
     * - Jika musik sedang playing → JANGAN stop, biarkan jalan
     * - Jika tidak playing → stop service
     */
    override fun onTaskRemoved(rootIntent: Intent?) {
        if (!player.isPlaying) {
            stopSelf()
        }
        // Tidak call super — supaya Android tidak otomatis stop
    }

    override fun onDestroy() {
        scope.cancel()
        mediaSession.release()
        player.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
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
            .setContentText(text)
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
            val ch = NotificationChannel(CHANNEL_ID, "Auspoty Music", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Kontrol musik Auspoty"
                setSound(null, null)
                enableVibration(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(ch)
        }
    }
}
