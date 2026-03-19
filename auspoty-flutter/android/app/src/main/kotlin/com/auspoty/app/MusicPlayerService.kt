package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ServiceInfo
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.media.app.NotificationCompat.MediaStyle

/**
 * Pure foreground service — tidak ada ExoPlayer.
 * Musik tetap diputar oleh ytPlayer (YouTube IFrame di WebView).
 * Service ini hanya menjaga proses tetap hidup saat app di-background
 * dan menampilkan notifikasi kontrol musik.
 */
class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_music"
        const val NOTIF_ID   = 77
        const val TAG        = "MusicPlayerService"

        const val ACTION_PLAY_PAUSE = "com.auspoty.app.PLAY_PAUSE"
        const val ACTION_NEXT       = "com.auspoty.app.NEXT"
        const val ACTION_PREV       = "com.auspoty.app.PREV"
        const val ACTION_STOP       = "com.auspoty.app.STOP"
        const val ACTION_UPDATE     = "com.auspoty.app.UPDATE"

        const val EXTRA_TITLE     = "title"
        const val EXTRA_ARTIST    = "artist"
        const val EXTRA_IS_PLAYING = "isPlaying"

        // Callbacks ke MainActivity
        var onPlayPause: (() -> Unit)? = null
        var onNext: (() -> Unit)? = null
        var onPrev: (() -> Unit)? = null

        var instance: MusicPlayerService? = null
    }

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()
    override fun onBind(intent: Intent?): IBinder = binder

    private var mediaSession: MediaSessionCompat? = null
    private var wakeLock: PowerManager.WakeLock? = null

    private var currentTitle  = "Auspoty"
    private var currentArtist = ""
    private var isPlaying     = false

    private val notifReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_PLAY_PAUSE -> onPlayPause?.invoke()
                ACTION_NEXT       -> onNext?.invoke()
                ACTION_PREV       -> onPrev?.invoke()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        setupMediaSession()
        setupWakeLock()
        registerNotifReceiver()
        startForegroundCompat(buildNotification())
        Log.d(TAG, "Service created")
    }

    private fun setupMediaSession() {
        mediaSession = MediaSessionCompat(this, "AuspotySession").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay()           { onPlayPause?.invoke() }
                override fun onPause()          { onPlayPause?.invoke() }
                override fun onSkipToNext()     { onNext?.invoke() }
                override fun onSkipToPrevious() { onPrev?.invoke() }
            })
            isActive = true
        }
    }

    private fun setupWakeLock() {
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::WakeLock")
        wakeLock?.setReferenceCounted(false)
    }

    private fun registerNotifReceiver() {
        val filter = IntentFilter().apply {
            addAction(ACTION_PLAY_PAUSE)
            addAction(ACTION_NEXT)
            addAction(ACTION_PREV)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(notifReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(notifReceiver, filter)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_UPDATE -> {
                currentTitle  = intent.getStringExtra(EXTRA_TITLE)  ?: currentTitle
                currentArtist = intent.getStringExtra(EXTRA_ARTIST) ?: currentArtist
                isPlaying     = intent.getBooleanExtra(EXTRA_IS_PLAYING, isPlaying)
                updateNotification()
                updateMediaSession()
            }
            ACTION_PLAY_PAUSE -> onPlayPause?.invoke()
            ACTION_NEXT       -> onNext?.invoke()
            ACTION_PREV       -> onPrev?.invoke()
            ACTION_STOP       -> { releaseWakeLock(); stopSelf() }
        }
        return START_STICKY
    }

    // ---- Public API ----

    fun updateTrackInfo(title: String, artist: String, playing: Boolean) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist
        isPlaying     = playing
        acquireWakeLock()
        updateMediaSessionMeta()
        updateMediaSession()
        updateNotification()
    }

    fun setPlaying(playing: Boolean) {
        isPlaying = playing
        if (playing) acquireWakeLock() else releaseWakeLock()
        updateMediaSession()
        updateNotification()
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)
    }

    private fun releaseWakeLock() {
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
    }

    // ---- MediaSession ----

    private fun updateMediaSessionMeta() {
        mediaSession?.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
                .build()
        )
    }

    private fun updateMediaSession() {
        val state = if (isPlaying) PlaybackStateCompat.STATE_PLAYING
                    else PlaybackStateCompat.STATE_PAUSED
        mediaSession?.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setState(state, PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN, 1f)
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY_PAUSE or
                    PlaybackStateCompat.ACTION_SKIP_TO_NEXT or
                    PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS
                )
                .build()
        )
    }

    // ---- Notification ----

    private fun updateNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification())
    }

    private fun pendingBroadcast(action: String, reqCode: Int): PendingIntent =
        PendingIntent.getBroadcast(
            this, reqCode,
            Intent(action).setPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    private fun buildNotification(): Notification {
        val openPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val prevPi      = pendingBroadcast(ACTION_PREV,       1)
        val playPausePi = pendingBroadcast(ACTION_PLAY_PAUSE, 2)
        val nextPi      = pendingBroadcast(ACTION_NEXT,       3)

        val playPauseIcon  = if (isPlaying) android.R.drawable.ic_media_pause
                             else android.R.drawable.ic_media_play
        val playPauseLabel = if (isPlaying) "Jeda" else "Putar"

        val subtitle = if (currentArtist.isNotEmpty()) currentArtist else "Auspoty Music"

        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(currentTitle)
            .setContentText(subtitle)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(openPi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .addAction(android.R.drawable.ic_media_previous, "Sebelumnya", prevPi)
            .addAction(playPauseIcon, playPauseLabel, playPausePi)
            .addAction(android.R.drawable.ic_media_next, "Berikutnya", nextPi)

        mediaSession?.sessionToken?.let { token ->
            builder.setStyle(
                MediaStyle()
                    .setMediaSession(token)
                    .setShowActionsInCompactView(0, 1, 2)
            )
        }

        return builder.build()
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIF_ID, notification)
        }
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

    override fun onTaskRemoved(rootIntent: Intent?) {
        Log.d(TAG, "onTaskRemoved — service tetap jalan")
        // Tidak stop — biarkan musik tetap jalan
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        try { unregisterReceiver(notifReceiver) } catch (_: Exception) {}
        mediaSession?.release()
        releaseWakeLock()
        instance = null
        super.onDestroy()
    }
}
