package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
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
import androidx.media3.session.LibraryResult
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaSession
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*

/**
 * MusicPlayerService — Media3 MediaLibraryService (pattern Metrolist)
 * Pakai androidx.media3 bukan exoplayer2 lama.
 * MediaLibraryService = Android treat kita sebagai media player proper:
 * - Notifikasi media di lock screen & status bar
 * - Kontrol headset/bluetooth
 * - Audio focus benar
 * - Tidak di-kill saat background / swipe dari recents
 */
class MusicPlayerService : MediaLibraryService() {

    companion object {
        const val CHANNEL_ID  = "auspoty_player"
        const val NOTIF_ID    = 42
        const val ACTION_PLAY  = "com.auspoty.app.PLAY"
        const val ACTION_PAUSE = "com.auspoty.app.PAUSE"
        const val ACTION_NEXT  = "com.auspoty.app.NEXT"
        const val ACTION_PREV  = "com.auspoty.app.PREV"
        const val ACTION_STOP  = "com.auspoty.app.STOP"

        var flutterChannel: MethodChannel? = null
        var instance: MusicPlayerService? = null
    }

    private lateinit var player: ExoPlayer
    private lateinit var mediaSession: MediaLibrarySession
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var currentTitle  = "Auspoty"
    private var currentArtist = ""
    private var currentThumb  = ""

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()

    // MediaLibraryService wajib implement ini
    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession = mediaSession

    override fun onBind(intent: Intent?): IBinder? {
        val superBind = super.onBind(intent)
        return if (superBind != null) superBind else binder
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        // WakeLock — CPU tetap aktif
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::PlayerWakeLock")
        wakeLock?.setReferenceCounted(false)

        // ExoPlayer Media3 dengan audio focus
        val audioAttr = AudioAttributes.Builder()
            .setUsage(C.USAGE_MEDIA)
            .setContentType(C.CONTENT_TYPE_MUSIC)
            .build()

        player = ExoPlayer.Builder(this).build().apply {
            setAudioAttributes(audioAttr, true)
            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == Player.STATE_ENDED) {
                        scope.launch { flutterChannel?.invokeMethod("onCompleted", null) }
                    }
                }
                override fun onIsPlayingChanged(isPlaying: Boolean) {
                    // update notifikasi via MediaSession otomatis
                }
            })
        }

        // MediaLibrarySession — ini yang register ke Android sebagai media player proper
        mediaSession = MediaLibrarySession.Builder(this, player,
            object : MediaLibrarySession.Callback {
                override fun onGetLibraryRoot(
                    session: MediaLibrarySession,
                    browser: MediaSession.ControllerInfo,
                    params: MediaLibraryService.LibraryParams?
                ): ListenableFuture<LibraryResult<MediaItem>> {
                    return Futures.immediateFuture(
                        LibraryResult.ofItem(
                            MediaItem.Builder().setMediaId("auspoty_root").build(),
                            params
                        )
                    )
                }
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

        // Start foreground langsung saat onCreate — seperti Metrolist
        val notification = buildInitialNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    fun playUrl(url: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title
        currentArtist = artist
        currentThumb  = thumbUrl

        // Set MediaItem dengan metadata — ini yang bikin notifikasi tampil info lagu
        val mediaItem = MediaItem.Builder()
            .setUri(url)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setArtist(artist)
                    .setArtworkUri(
                        if (thumbUrl.isNotEmpty()) android.net.Uri.parse(thumbUrl) else null
                    )
                    .build()
            )
            .build()

        player.setMediaItem(mediaItem)
        player.prepare()
        player.play()

        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)
    }

    fun pause()  { player.pause() }
    fun resume() { player.play() }
    fun seekTo(posMs: Long) { player.seekTo(posMs) }
    fun isPlaying()       = player.isPlaying
    fun currentPosition() = player.currentPosition
    fun duration()        = if (player.duration == C.TIME_UNSET) 0L else player.duration

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY  -> player.play()
            ACTION_PAUSE -> player.pause()
            ACTION_NEXT  -> scope.launch { flutterChannel?.invokeMethod("onNext", null) }
            ACTION_PREV  -> scope.launch { flutterChannel?.invokeMethod("onPrev", null) }
            ACTION_STOP  -> stopSelf()
        }
        return START_STICKY
    }

    // Seperti Metrolist — onTaskRemoved hanya call super, tidak stop service
    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        // Tidak stop service — biarkan musik tetap jalan
    }

    override fun onDestroy() {
        scope.cancel()
        mediaSession.release()
        player.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }

    private fun buildInitialNotification(): Notification {
        val contentPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Auspoty")
            .setContentText("Siap memutar musik")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(contentPi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
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
