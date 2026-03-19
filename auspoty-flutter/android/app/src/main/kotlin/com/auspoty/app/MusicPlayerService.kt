package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Binder
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.os.PowerManager
import android.support.v4.media.MediaBrowserCompat
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.app.NotificationCompat
import androidx.media.MediaBrowserServiceCompat
import androidx.media.app.NotificationCompat.MediaStyle
import com.google.android.exoplayer2.*
import com.google.android.exoplayer2.audio.AudioAttributes
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*
import java.net.URL

/**
 * MusicPlayerService — extend MediaBrowserServiceCompat (seperti Metrolist/Spotify)
 * Ini yang bikin Android treat kita sebagai media player proper:
 * - Notifikasi media di lock screen
 * - Kontrol dari headset/bluetooth
 * - Audio focus yang benar
 * - Tidak di-kill saat background
 */
class MusicPlayerService : MediaBrowserServiceCompat() {

    companion object {
        const val CHANNEL_ID = "auspoty_player"
        const val NOTIF_ID = 42
        const val ACTION_PLAY   = "com.auspoty.app.PLAY"
        const val ACTION_PAUSE  = "com.auspoty.app.PAUSE"
        const val ACTION_NEXT   = "com.auspoty.app.NEXT"
        const val ACTION_PREV   = "com.auspoty.app.PREV"
        const val ACTION_STOP   = "com.auspoty.app.STOP"

        // Flutter MethodChannel untuk callback ke Dart
        var flutterChannel: MethodChannel? = null
        var instance: MusicPlayerService? = null
    }

    private lateinit var player: SimpleExoPlayer
    private lateinit var mediaSession: MediaSessionCompat
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var currentTitle  = "Auspoty"
    private var currentArtist = ""
    private var currentThumb  = ""
    private var artBitmap: Bitmap? = null

    // Binder untuk MainActivity
    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()

    // MediaBrowserServiceCompat wajib implement ini
    override fun onGetRoot(clientPackageName: String, clientUid: Int, rootHints: Bundle?): BrowserRoot {
        return BrowserRoot("auspoty_root", null)
    }

    override fun onLoadChildren(parentId: String, result: Result<List<MediaBrowserCompat.MediaItem>>) {
        result.sendResult(emptyList())
    }

    override fun onBind(intent: Intent?): IBinder? {
        // MediaBrowserServiceCompat punya onBind sendiri untuk browser clients
        // Kita return binder kita untuk MainActivity binding
        val browserBind = super.onBind(intent)
        return if (intent?.action == SERVICE_INTERFACE) browserBind else binder
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        // WakeLock — CPU tetap aktif saat audio jalan
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::PlayerWakeLock")
        wakeLock?.setReferenceCounted(false)

        // MediaSession — ini yang register ke Android sebagai media player
        mediaSession = MediaSessionCompat(this, "AuspotyPlayer").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay()           { player.play(); updateAll() }
                override fun onPause()          { player.pause(); updateAll() }
                override fun onSkipToNext()     { scope.launch { flutterChannel?.invokeMethod("onNext", null) } }
                override fun onSkipToPrevious() { scope.launch { flutterChannel?.invokeMethod("onPrev", null) } }
                override fun onStop()           { stopSelf() }
                override fun onSeekTo(pos: Long){ player.seekTo(pos); updateAll() }
            })
            isActive = true
        }

        // KRITIS: set sessionToken supaya MediaBrowserServiceCompat bisa dikenali Android
        sessionToken = mediaSession.sessionToken

        // ExoPlayer dengan audio focus handling yang benar
        val audioAttr = AudioAttributes.Builder()
            .setUsage(C.USAGE_MEDIA)
            .setContentType(C.CONTENT_TYPE_MUSIC)
            .build()

        player = SimpleExoPlayer.Builder(this).build().apply {
            setAudioAttributes(audioAttr, /* handleAudioFocus= */ true)
            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    updateAll()
                    if (state == Player.STATE_ENDED) {
                        scope.launch { flutterChannel?.invokeMethod("onCompleted", null) }
                    }
                }
                override fun onIsPlayingChanged(isPlaying: Boolean) { updateAll() }
            })
        }

        // Start foreground langsung saat onCreate
        startForeground(NOTIF_ID, buildNotification())
    }

    fun playUrl(url: String, title: String, artist: String, thumbUrl: String) {
        currentTitle  = title
        currentArtist = artist
        currentThumb  = thumbUrl

        // Load artwork async
        scope.launch(Dispatchers.IO) {
            artBitmap = try { BitmapFactory.decodeStream(URL(thumbUrl).openStream()) } catch (_: Exception) { null }
            withContext(Dispatchers.Main) { updateAll() }
        }

        player.setMediaItem(MediaItem.fromUri(url))
        player.prepare()
        player.play()

        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)
        updateAll()
    }

    fun pause()  { player.pause(); updateAll() }
    fun resume() { player.play();  updateAll() }
    fun seekTo(posMs: Long) { player.seekTo(posMs) }
    fun isPlaying()       = player.isPlaying
    fun currentPosition() = player.currentPosition
    fun duration()        = if (player.duration == C.TIME_UNSET) 0L else player.duration

    private fun updateAll() {
        updateMediaSessionMetadata()
        updatePlaybackState()
        updateNotification()
    }

    private fun updateMediaSessionMetadata() {
        val meta = MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE,  currentTitle)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
            .putLong(MediaMetadataCompat.METADATA_KEY_DURATION, duration())
            .apply { artBitmap?.let { putBitmap(MediaMetadataCompat.METADATA_KEY_ART, it) } }
            .build()
        mediaSession.setMetadata(meta)
    }

    private fun updatePlaybackState() {
        val state = if (player.isPlaying) PlaybackStateCompat.STATE_PLAYING
                    else PlaybackStateCompat.STATE_PAUSED
        mediaSession.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setState(state, player.currentPosition, 1f)
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY or
                    PlaybackStateCompat.ACTION_PAUSE or
                    PlaybackStateCompat.ACTION_SKIP_TO_NEXT or
                    PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS or
                    PlaybackStateCompat.ACTION_SEEK_TO
                ).build()
        )
    }

    private fun updateNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        val notif = buildNotification()
        if (player.isPlaying) {
            startForeground(NOTIF_ID, notif)
        } else {
            // Saat pause: turunkan ke non-foreground tapi notifikasi tetap ada
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_DETACH)
            } else {
                @Suppress("DEPRECATION")
                stopForeground(false)
            }
            nm.notify(NOTIF_ID, notif)
        }
    }

    private fun buildNotification(): Notification {
        val contentPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        fun svcPi(action: String, code: Int) = PendingIntent.getService(
            this, code,
            Intent(this, MusicPlayerService::class.java).apply { this.action = action },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val isPlaying = player.isPlaying

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(currentTitle)
            .setContentText(currentArtist)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setLargeIcon(artBitmap)
            .setContentIntent(contentPi)
            .setOngoing(isPlaying)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .addAction(android.R.drawable.ic_media_previous, "Prev", svcPi(ACTION_PREV, 1))
            .addAction(
                if (isPlaying) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play,
                if (isPlaying) "Pause" else "Play",
                svcPi(if (isPlaying) ACTION_PAUSE else ACTION_PLAY, 2)
            )
            .addAction(android.R.drawable.ic_media_next, "Next", svcPi(ACTION_NEXT, 3))
            .setStyle(
                MediaStyle()
                    .setMediaSession(mediaSession.sessionToken)
                    .setShowActionsInCompactView(0, 1, 2)
            )
            .build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY  -> { player.play();  updateAll() }
            ACTION_PAUSE -> { player.pause(); updateAll() }
            ACTION_NEXT  -> scope.launch { flutterChannel?.invokeMethod("onNext", null) }
            ACTION_PREV  -> scope.launch { flutterChannel?.invokeMethod("onPrev", null) }
            ACTION_STOP  -> stopSelf()
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Tetap jalan saat app di-swipe dari recent apps
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        scope.cancel()
        player.release()
        mediaSession.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
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
