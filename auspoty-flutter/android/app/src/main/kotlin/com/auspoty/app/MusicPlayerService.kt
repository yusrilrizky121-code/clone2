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
import android.net.Uri
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
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_music"
        const val NOTIF_ID   = 77
        const val TAG        = "MusicPlayerService"
        const val API_BASE   = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app"

        const val ACTION_PLAY_PAUSE = "com.auspoty.app.PLAY_PAUSE"
        const val ACTION_NEXT       = "com.auspoty.app.NEXT"
        const val ACTION_PREV       = "com.auspoty.app.PREV"
        const val ACTION_PLAY       = "com.auspoty.app.PLAY"
        const val ACTION_STOP       = "com.auspoty.app.STOP"

        const val EXTRA_VIDEO_ID  = "videoId"
        const val EXTRA_TITLE     = "title"
        const val EXTRA_ARTIST    = "artist"
        const val EXTRA_THUMBNAIL = "thumbnail"

        // Callback ke MainActivity saat tombol notifikasi ditekan
        var onPlayPause: (() -> Unit)? = null
        var onNext: (() -> Unit)? = null
        var onPrev: (() -> Unit)? = null
        // Callback saat lagu selesai
        var onCompleted: (() -> Unit)? = null

        var instance: MusicPlayerService? = null
    }

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()
    override fun onBind(intent: Intent?): IBinder = binder

    private lateinit var player: ExoPlayer
    private var mediaSession: MediaSessionCompat? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var currentTitle     = "Auspoty"
    private var currentArtist    = ""
    private var currentVideoId   = ""
    private var isPlaying        = false
    private var isLoading        = false

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
        setupExoPlayer()
        setupMediaSession()
        setupWakeLock()
        registerNotifReceiver()
        startForegroundCompat(buildNotification())
        Log.d(TAG, "Service created")
    }

    private fun setupExoPlayer() {
        player = ExoPlayer.Builder(this).build().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus= */ true
            )
            addListener(object : Player.Listener {
                override fun onIsPlayingChanged(playing: Boolean) {
                    isPlaying = playing
                    updateMediaSession()
                    updateNotification()
                }
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == Player.STATE_ENDED) {
                        isPlaying = false
                        updateMediaSession()
                        updateNotification()
                        onCompleted?.invoke()
                    }
                    if (state == Player.STATE_READY) {
                        isLoading = false
                        updateNotification()
                    }
                }
            })
        }
    }

    private fun setupMediaSession() {
        mediaSession = MediaSessionCompat(this, "AuspotySession").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay()             { resumePlayer() }
                override fun onPause()            { pausePlayer() }
                override fun onSkipToNext()       { onNext?.invoke() }
                override fun onSkipToPrevious()   { onPrev?.invoke() }
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
            ACTION_PLAY -> {
                val videoId   = intent.getStringExtra(EXTRA_VIDEO_ID)  ?: return START_STICKY
                val title     = intent.getStringExtra(EXTRA_TITLE)     ?: ""
                val artist    = intent.getStringExtra(EXTRA_ARTIST)    ?: ""
                val thumbnail = intent.getStringExtra(EXTRA_THUMBNAIL) ?: ""
                playTrack(videoId, title, artist, thumbnail)
            }
            ACTION_PLAY_PAUSE -> togglePlayPause()
            ACTION_NEXT       -> onNext?.invoke()
            ACTION_PREV       -> onPrev?.invoke()
            ACTION_STOP       -> { stopPlayer(); stopSelf() }
        }
        return START_STICKY
    }

    // ---- Public API (dipanggil dari MainActivity via binding) ----

    fun playTrack(videoId: String, title: String, artist: String, thumbnail: String) {
        currentVideoId = videoId
        currentTitle   = title.ifEmpty { "Auspoty" }
        currentArtist  = artist
        isLoading      = true
        updateNotification()

        // Acquire wakelock saat mulai play
        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)

        scope.launch {
            try {
                Log.d(TAG, "Fetching stream URL for $videoId")
                val streamUrl = withContext(Dispatchers.IO) { fetchStreamUrl(videoId) }
                if (streamUrl != null) {
                    Log.d(TAG, "Got stream URL, playing...")
                    player.setMediaItem(MediaItem.fromUri(streamUrl))
                    player.prepare()
                    player.play()
                    updateMediaSessionMeta()
                } else {
                    Log.e(TAG, "Stream URL null for $videoId")
                    isLoading = false
                    updateNotification()
                }
            } catch (e: Exception) {
                Log.e(TAG, "playTrack error: ${e.message}")
                isLoading = false
                updateNotification()
            }
        }
    }

    fun pausePlayer() {
        player.pause()
    }

    fun resumePlayer() {
        player.play()
    }

    fun togglePlayPause() {
        if (player.isPlaying) pausePlayer() else resumePlayer()
    }

    fun stopPlayer() {
        player.stop()
        player.clearMediaItems()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
    }

    fun seekTo(posMs: Long) = player.seekTo(posMs)
    fun getPosition(): Long = player.currentPosition
    fun getDuration(): Long = if (player.duration == C.TIME_UNSET) 0L else player.duration
    fun isCurrentlyPlaying() = player.isPlaying

    // ---- Stream URL fetch ----

    private fun fetchStreamUrl(videoId: String): String? {
        return try {
            val conn = (URL("$API_BASE/api/stream").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 30_000
                readTimeout    = 60_000
            }
            conn.outputStream.use { it.write("""{"videoId":"$videoId"}""".toByteArray()) }
            if (conn.responseCode == 200) {
                val json = JSONObject(conn.inputStream.bufferedReader().readText())
                if (json.optString("status") == "success") json.optString("url").takeIf { it.isNotEmpty() }
                else null
            } else null
        } catch (e: Exception) {
            Log.e(TAG, "fetchStreamUrl: ${e.message}")
            null
        }
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
        val state = when {
            isLoading  -> PlaybackStateCompat.STATE_BUFFERING
            isPlaying  -> PlaybackStateCompat.STATE_PLAYING
            else       -> PlaybackStateCompat.STATE_PAUSED
        }
        mediaSession?.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setState(state, player.currentPosition, 1f)
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

        val playPauseIcon = if (isPlaying) android.R.drawable.ic_media_pause
                            else android.R.drawable.ic_media_play
        val playPauseLabel = if (isPlaying) "Jeda" else "Putar"

        val subtitle = when {
            isLoading -> "Memuat..."
            isPlaying -> currentArtist.ifEmpty { "Sedang diputar" }
            else      -> currentArtist.ifEmpty { "Dijeda" }
        }

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
        Log.d(TAG, "onTaskRemoved — service tetap jalan, isPlaying=$isPlaying")
        // Tidak stop — musik tetap jalan
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        scope.cancel()
        try { unregisterReceiver(notifReceiver) } catch (_: Exception) {}
        mediaSession?.release()
        player.release()
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
        instance = null
        super.onDestroy()
    }
}
