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
import androidx.media3.session.DefaultMediaNotificationProvider
import androidx.media3.session.LibraryResult
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaSession
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*

/**
 * MusicPlayerService — Media3 MediaLibraryService
 * Pattern Metrolist: onTaskRemoved hanya stop jika tidak playing
 * DefaultMediaNotificationProvider = notifikasi media proper di lock screen
 */
class MusicPlayerService : MediaLibraryService() {

    companion object {
        const val CHANNEL_ID = "auspoty_player"
        const val NOTIF_ID   = 42

        var flutterChannel: MethodChannel? = null
        var instance: MusicPlayerService? = null
    }

    private lateinit var player: ExoPlayer
    private lateinit var mediaSession: MediaLibrarySession
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession = mediaSession

    override fun onBind(intent: Intent?): IBinder? {
        val superBind = super.onBind(intent)
        return superBind ?: binder
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        // WakeLock — CPU tetap aktif saat background
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::PlayerWakeLock")
        wakeLock?.setReferenceCounted(false)

        // ExoPlayer dengan audio focus
        val audioAttr = AudioAttributes.Builder()
            .setUsage(C.USAGE_MEDIA)
            .setContentType(C.CONTENT_TYPE_MUSIC)
            .build()

        player = ExoPlayer.Builder(this).build().apply {
            setAudioAttributes(audioAttr, /* handleAudioFocus= */ true)
            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == Player.STATE_ENDED) {
                        scope.launch { flutterChannel?.invokeMethod("onCompleted", null) }
                    }
                }
            })
        }

        // DefaultMediaNotificationProvider — ini kunci agar Android tahu
        // service ini adalah media player aktif dan tidak di-kill
        setMediaNotificationProvider(
            DefaultMediaNotificationProvider.Builder(this)
                .setNotificationId(NOTIF_ID)
                .setChannelId(CHANNEL_ID)
                .setChannelName(R.string.app_name)
                .build()
        )

        // MediaLibrarySession
        mediaSession = MediaLibrarySession.Builder(
            this, player,
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

        // Start foreground awal dengan notifikasi minimal
        val notification = buildInitialNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIF_ID, notification)
        }
    }

    fun playUrl(url: String, title: String, artist: String, thumbUrl: String) {
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
        super.onStartCommand(intent, flags, startId)
        return START_STICKY
    }

    /**
     * Pattern Metrolist: hanya stop jika tidak sedang playing.
     * Jika musik sedang jalan, biarkan service tetap hidup.
     */
    override fun onTaskRemoved(rootIntent: Intent?) {
        if (!player.isPlaying) {
            stopSelf()
        }
        // Jika playing — tidak stop, musik tetap jalan di background
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
