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
 * Foreground service dengan MediaSession + MediaStyle notification.
 * Tombol prev/play-pause/next di notifikasi → broadcast → MainActivity → WebView.
 * Musik tetap diputar oleh ytPlayer di WebView.
 */
class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_player"
        const val NOTIF_ID   = 42
        const val TAG        = "MusicPlayerService"

        // Actions dari Flutter/MainActivity
        const val ACTION_UPDATE_NOTIF = "com.auspoty.app.UPDATE_NOTIF"
        const val EXTRA_TITLE         = "title"
        const val EXTRA_ARTIST        = "artist"
        const val EXTRA_PLAYING       = "playing"

        // Actions dari tombol notifikasi (broadcast)
        const val ACTION_PLAY_PAUSE = "com.auspoty.app.PLAY_PAUSE"
        const val ACTION_NEXT       = "com.auspoty.app.NEXT"
        const val ACTION_PREV       = "com.auspoty.app.PREV"

        var instance: MusicPlayerService? = null
        // Callback ke MainActivity saat tombol notifikasi ditekan
        var onPlayPause: (() -> Unit)? = null
        var onNext: (() -> Unit)? = null
        var onPrev: (() -> Unit)? = null
    }

    private var wakeLock: PowerManager.WakeLock? = null
    private var mediaSession: MediaSessionCompat? = null
    private var isPlaying = false
    private var currentTitle  = "Auspoty"
    private var currentArtist = "Ketuk untuk membuka"

    private val notifReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_PLAY_PAUSE -> onPlayPause?.invoke()
                ACTION_NEXT       -> onNext?.invoke()
                ACTION_PREV       -> onPrev?.invoke()
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        setupMediaSession()

        // WakeLock — CPU tetap aktif saat layar mati
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::WakeLock")
        wakeLock?.setReferenceCounted(false)
        wakeLock?.acquire(6 * 60 * 60 * 1000L)

        // Register broadcast receiver untuk tombol notifikasi
        val filter = IntentFilter().apply {
            addAction(ACTION_PLAY_PAUSE)
            addAction(ACTION_NEXT)
            addAction(ACTION_PREV)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(notifReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(notifReceiver, filter)
        }

        startForegroundCompat(buildNotification())
        Log.d(TAG, "Service started with MediaSession")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_UPDATE_NOTIF -> {
                val title   = intent.getStringExtra(EXTRA_TITLE)   ?: currentTitle
                val artist  = intent.getStringExtra(EXTRA_ARTIST)  ?: currentArtist
                val playing = intent.getBooleanExtra(EXTRA_PLAYING, true)
                currentTitle  = title
                currentArtist = artist
                isPlaying     = playing
                updateMediaSession()
                updateNotification()
                if (playing && wakeLock?.isHeld == false) {
                    wakeLock?.acquire(6 * 60 * 60 * 1000L)
                }
            }
            // Tombol notifikasi juga bisa masuk via onStartCommand (fallback)
            ACTION_PLAY_PAUSE -> onPlayPause?.invoke()
            ACTION_NEXT       -> onNext?.invoke()
            ACTION_PREV       -> onPrev?.invoke()
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        Log.d(TAG, "onTaskRemoved — service tetap jalan")
        // Tidak stop service — biarkan musik tetap jalan
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        try { unregisterReceiver(notifReceiver) } catch (_: Exception) {}
        mediaSession?.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }

    // ---- MediaSession ----

    private fun setupMediaSession() {
        mediaSession = MediaSessionCompat(this, "AuspotySession").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay()     { onPlayPause?.invoke() }
                override fun onPause()    { onPlayPause?.invoke() }
                override fun onSkipToNext()     { onNext?.invoke() }
                override fun onSkipToPrevious() { onPrev?.invoke() }
            })
            isActive = true
        }
        updateMediaSession()
    }

    private fun updateMediaSession() {
        val state = if (isPlaying) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED
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
        mediaSession?.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
                .build()
        )
    }

    // ---- Notification ----

    fun updateNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification())
    }

    private fun pendingBroadcast(action: String, reqCode: Int): PendingIntent {
        return PendingIntent.getBroadcast(
            this, reqCode,
            Intent(action).setPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    private fun buildNotification(): Notification {
        val openAppPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val prevPi      = pendingBroadcast(ACTION_PREV,       1)
        val playPausePi = pendingBroadcast(ACTION_PLAY_PAUSE, 2)
        val nextPi      = pendingBroadcast(ACTION_NEXT,       3)

        val playPauseIcon = if (isPlaying)
            android.R.drawable.ic_media_pause
        else
            android.R.drawable.ic_media_play

        val playPauseLabel = if (isPlaying) "Jeda" else "Putar"

        val token = mediaSession?.sessionToken

        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(currentTitle)
            .setContentText(currentArtist)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(openAppPi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            // Tombol: Prev | Play/Pause | Next
            .addAction(android.R.drawable.ic_media_previous, "Sebelumnya", prevPi)
            .addAction(playPauseIcon, playPauseLabel, playPausePi)
            .addAction(android.R.drawable.ic_media_next, "Berikutnya", nextPi)

        // MediaStyle — tampilkan tombol di notifikasi & lock screen
        if (token != null) {
            builder.setStyle(
                MediaStyle()
                    .setMediaSession(token)
                    .setShowActionsInCompactView(0, 1, 2) // prev, play/pause, next
                    .setShowCancelButton(false)
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
