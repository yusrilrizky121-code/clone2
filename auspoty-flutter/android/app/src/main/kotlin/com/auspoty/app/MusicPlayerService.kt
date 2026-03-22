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
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
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
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_music"
        const val NOTIF_ID   = 77
        const val TAG        = "MusicPlayerService"

        const val ACTION_PLAY_PAUSE = "com.auspoty.app.PLAY_PAUSE"
        const val ACTION_NEXT       = "com.auspoty.app.NEXT"
        const val ACTION_PREV       = "com.auspoty.app.PREV"

        const val API_BASE = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app"

        var onPlayPause: (() -> Unit)? = null
        var onNext: (() -> Unit)? = null
        var onPrev: (() -> Unit)? = null
        var onPositionUpdate: ((Int, Int) -> Unit)? = null

        var instance: MusicPlayerService? = null
    }

    inner class LocalBinder : Binder() {
        fun getService() = this@MusicPlayerService
    }
    private val binder = LocalBinder()
    override fun onBind(intent: Intent?): IBinder = binder

    private var mediaSession: MediaSessionCompat? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var notifManager: NotificationManager? = null
    private var mediaPlayer: MediaPlayer? = null
    private var audioManager: AudioManager? = null
    private var audioFocusRequest: AudioFocusRequest? = null

    private var currentTitle  = "Auspoty"
    private var currentArtist = "Auspoty Music"
    private var currentVideoId = ""
    private var currentImgUrl = ""
    private var isPlaying     = false
    private var isNativePlaying = false
    private var currentArt: android.graphics.Bitmap? = null

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_PLAY_PAUSE -> {
                    if (isNativePlaying) toggleNativePlayPause()
                    else onPlayPause?.invoke()
                }
                ACTION_NEXT -> onNext?.invoke()
                ACTION_PREV -> onPrev?.invoke()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        notifManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        createChannel()
        setupMediaSession()
        setupWakeLock()
        registerReceiver()
        startForegroundCompat(buildNotif())
        Log.d(TAG, "Service created")
    }

    fun playNative(videoId: String, title: String, artist: String) {
        currentVideoId = videoId
        currentTitle   = title.ifEmpty { "Auspoty" }
        currentArtist  = artist.ifEmpty { "Auspoty Music" }
        isPlaying      = true
        isNativePlaying = false

        updateMediaSessionMeta()
        updatePlaybackState()
        refreshNotif()
        acquireWakeLock()

        Thread {
            try {
                Log.d(TAG, "Fetching stream URL for $videoId")
                val (streamUrl, headers) = fetchStreamUrl(videoId)
                Log.d(TAG, "Got stream URL, starting MediaPlayer")
                startMediaPlayer(streamUrl, headers)
            } catch (e: Exception) {
                Log.e(TAG, "playNative failed: ${e.message}")
                isNativePlaying = false
            }
        }.start()
    }

    fun pauseNative() {
        if (mediaPlayer?.isPlaying == true) {
            mediaPlayer?.pause()
            isPlaying = false
            isNativePlaying = false
            stopPositionUpdater()
            updatePlaybackState()
            refreshNotif()
            Log.d(TAG, "MediaPlayer paused")
        }
    }

    fun resumeNative() {
        if (mediaPlayer != null && !mediaPlayer!!.isPlaying) {
            requestAudioFocus()
            mediaPlayer?.start()
            isPlaying = true
            isNativePlaying = true
            updatePlaybackState()
            refreshNotif()
            Log.d(TAG, "MediaPlayer resumed")
        }
    }

    fun stopNative() {
        stopPositionUpdater()
        mediaPlayer?.stop()
        mediaPlayer?.release()
        mediaPlayer = null
        isPlaying = false
        isNativePlaying = false
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "MediaPlayer stopped")
    }

    fun updateTrackInfo(title: String, artist: String, playing: Boolean, imgUrl: String = "") {
        currentTitle   = title.ifEmpty { "Auspoty" }
        currentArtist  = artist.ifEmpty { "Auspoty Music" }
        isPlaying      = playing
        Log.d(TAG, "updateTrackInfo: title=$title, imgUrl=$imgUrl")
        if (playing) acquireWakeLock()
        if (imgUrl.isNotEmpty() && imgUrl != currentImgUrl) {
            currentImgUrl = imgUrl
            currentArt = null
            updateMediaSessionMeta()
            updatePlaybackState()
            refreshNotif()
            Thread {
                val bmp = fetchBitmap(imgUrl)
                if (bmp != null) {
                    currentArt = bmp
                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                        updateMediaSessionMeta()
                        refreshNotif()
                    }
                }
            }.start()
        } else {
            updateMediaSessionMeta()
            updatePlaybackState()
            refreshNotif()
        }
    }

    fun setPlaying(playing: Boolean) {
        isPlaying = playing
        if (playing) acquireWakeLock() else releaseWakeLock()
        updatePlaybackState()
        refreshNotif()
    }

    fun keepAlive() {
        acquireWakeLock()
    }

    fun getPosition(): Int = try { mediaPlayer?.currentPosition?.div(1000) ?: 0 } catch (e: Exception) { 0 }
    fun getDuration(): Int = try { mediaPlayer?.duration?.div(1000) ?: 0 } catch (e: Exception) { 0 }
    fun seekTo(seconds: Int) { try { mediaPlayer?.seekTo(seconds * 1000) } catch (e: Exception) {} }

    private fun fetchStreamUrl(videoId: String): Pair<String, Map<String, String>> {
        val url = URL("$API_BASE/api/stream?videoId=$videoId")
        val conn = url.openConnection() as HttpURLConnection
        conn.connectTimeout = 15000
        conn.readTimeout = 15000
        conn.requestMethod = "GET"
        val code = conn.responseCode
        if (code != 200) throw Exception("HTTP $code")
        val body = conn.inputStream.bufferedReader().readText()
        val json = JSONObject(body)
        if (json.getString("status") != "success") throw Exception(json.optString("message"))
        val streamUrl = json.getString("url")
        val apiHeaders = mutableMapOf(
            "User-Agent" to "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer" to "https://www.youtube.com/",
            "Origin" to "https://www.youtube.com"
        )
        try {
            val headersObj = json.optJSONObject("headers")
            if (headersObj != null) {
                val keys = headersObj.keys()
                while (keys.hasNext()) {
                    val k = keys.next()
                    apiHeaders[k] = headersObj.getString(k)
                }
            }
        } catch (e: Exception) { /* ignore */ }
        return Pair(streamUrl, apiHeaders)
    }

    private fun startMediaPlayer(streamUrl: String, streamHeaders: Map<String, String> = emptyMap()) {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            try {
                mediaPlayer?.release()
                mediaPlayer = null

                requestAudioFocus()

                val mp = MediaPlayer().apply {
                    setAudioAttributes(
                        AudioAttributes.Builder()
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .build()
                    )
                    setWakeMode(applicationContext, PowerManager.PARTIAL_WAKE_LOCK)
                    val uri = android.net.Uri.parse(streamUrl)
                    val headers = mutableMapOf(
                        "User-Agent" to "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                        "Referer" to "https://www.youtube.com/",
                        "Origin" to "https://www.youtube.com"
                    )
                    headers.putAll(streamHeaders)
                    setDataSource(applicationContext, uri, headers)
                    setOnPreparedListener { player ->
                        player.start()
                        this@MusicPlayerService.isNativePlaying = true
                        this@MusicPlayerService.isPlaying = true
                        updatePlaybackState()
                        refreshNotif()
                        Log.d(TAG, "MediaPlayer started, duration=${player.duration/1000}s")
                        startPositionUpdater()
                    }
                    setOnCompletionListener {
                        this@MusicPlayerService.isNativePlaying = false
                        this@MusicPlayerService.isPlaying = false
                        onNext?.invoke()
                        Log.d(TAG, "MediaPlayer completed, calling onNext")
                    }
                    setOnErrorListener { _, what, extra ->
                        Log.e(TAG, "MediaPlayer error: what=$what extra=$extra")
                        this@MusicPlayerService.isNativePlaying = false
                        false
                    }
                    prepareAsync()
                }
                mediaPlayer = mp
                Log.d(TAG, "MediaPlayer prepareAsync called")
            } catch (e: Exception) {
                Log.e(TAG, "startMediaPlayer error: ${e.message}")
            }
        }
    }

    private var positionHandler: android.os.Handler? = null
    private var positionRunnable: Runnable? = null

    private fun startPositionUpdater() {
        stopPositionUpdater()
        positionHandler = android.os.Handler(android.os.Looper.getMainLooper())
        positionRunnable = object : Runnable {
            override fun run() {
                if (isNativePlaying && mediaPlayer != null) {
                    try {
                        updatePlaybackState()
                        val pos = mediaPlayer?.currentPosition?.div(1000) ?: 0
                        val dur = mediaPlayer?.duration?.div(1000) ?: 0
                        onPositionUpdate?.invoke(pos, dur)
                    } catch (e: Exception) {}
                    positionHandler?.postDelayed(this, 1000)
                }
            }
        }
        positionHandler?.postDelayed(positionRunnable!!, 1000)
        Log.d(TAG, "Position updater started")
    }

    private fun stopPositionUpdater() {
        positionRunnable?.let { positionHandler?.removeCallbacks(it) }
        positionHandler = null
        positionRunnable = null
    }

    private fun requestAudioFocus() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            audioFocusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setOnAudioFocusChangeListener { focus ->
                    when (focus) {
                        AudioManager.AUDIOFOCUS_LOSS -> pauseNative()
                        AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> pauseNative()
                        AudioManager.AUDIOFOCUS_GAIN -> resumeNative()
                    }
                }
                .build()
            audioManager?.requestAudioFocus(audioFocusRequest!!)
        } else {
            @Suppress("DEPRECATION")
            audioManager?.requestAudioFocus(null, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN)
        }
    }

    private fun setupMediaSession() {
        mediaSession = MediaSessionCompat(this, "AuspotySession").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay()           { if (isNativePlaying) resumeNative() else onPlayPause?.invoke() }
                override fun onPause()          { if (isNativePlaying) pauseNative() else onPlayPause?.invoke() }
                override fun onSkipToNext()     { onNext?.invoke() }
                override fun onSkipToPrevious() { onPrev?.invoke() }
            })
            isActive = true
        }
    }

    private fun updateMediaSessionMeta() {
        val builder = MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
            .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_TITLE, currentTitle)
            .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_SUBTITLE, currentArtist)
        if (currentImgUrl.isNotEmpty()) {
            builder.putString(MediaMetadataCompat.METADATA_KEY_ART_URI, currentImgUrl)
            builder.putString(MediaMetadataCompat.METADATA_KEY_ALBUM_ART_URI, currentImgUrl)
        }
        if (currentArt != null) {
            builder.putBitmap(MediaMetadataCompat.METADATA_KEY_ART, currentArt)
            builder.putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, currentArt)
        }
        mediaSession?.setMetadata(builder.build())
    }

    private fun updatePlaybackState() {
        val state = if (isPlaying) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED
        val pos = try { mediaPlayer?.currentPosition?.toLong() ?: PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN } catch (e: Exception) { PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN }
        val speed = if (isPlaying) 1f else 0f
        mediaSession?.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setState(state, pos, speed)
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY_PAUSE or
                    PlaybackStateCompat.ACTION_SKIP_TO_NEXT or
                    PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS or
                    PlaybackStateCompat.ACTION_SEEK_TO
                )
                .build()
        )
    }

    private fun fetchBitmap(url: String): android.graphics.Bitmap? {
        Log.d(TAG, "fetchBitmap: trying URL=$url")
        return try {
            var finalUrl = url
            repeat(3) {
                val conn = java.net.URL(finalUrl).openConnection() as java.net.HttpURLConnection
                conn.instanceFollowRedirects = false
                conn.connectTimeout = 8000
                conn.readTimeout = 8000
                conn.setRequestProperty("User-Agent", "Mozilla/5.0")
                conn.connect()
                val code = conn.responseCode
                if (code in 300..399) {
                    finalUrl = conn.getHeaderField("Location") ?: return null
                    conn.disconnect()
                    return@repeat
                }
                Log.d(TAG, "fetchBitmap: HTTP $code, url=$finalUrl")
                if (code != 200) return null
                val bmp = android.graphics.BitmapFactory.decodeStream(conn.inputStream)
                Log.d(TAG, "fetchBitmap: bitmap=${bmp != null}, size=${bmp?.width}x${bmp?.height}")
                return bmp
            }
            null
        } catch (e: Exception) {
            Log.e(TAG, "fetchBitmap failed: ${e.message}")
            null
        }
    }

    private fun refreshNotif() {
        notifManager?.notify(NOTIF_ID, buildNotif())
    }

    private fun pi(action: String, code: Int): PendingIntent =
        PendingIntent.getBroadcast(
            this, code,
            Intent(action).setPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    private fun buildNotif(): Notification {
        val openPi = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val playIcon  = if (isPlaying) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play
        val playLabel = if (isPlaying) "Jeda" else "Putar"

        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(currentTitle)
            .setContentText(currentArtist)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setLargeIcon(currentArt)
            .setContentIntent(openPi)
            .setOngoing(true)
            .setSilent(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setCategory(NotificationCompat.CATEGORY_TRANSPORT)
            .addAction(android.R.drawable.ic_media_previous, "Sebelumnya", pi(ACTION_PREV, 1))
            .addAction(playIcon, playLabel, pi(ACTION_PLAY_PAUSE, 2))
            .addAction(android.R.drawable.ic_media_next, "Berikutnya", pi(ACTION_NEXT, 3))

        mediaSession?.sessionToken?.let { token ->
            builder.setStyle(MediaStyle().setMediaSession(token).setShowActionsInCompactView(0, 1, 2))
        }
        return builder.build()
    }

    private fun startForegroundCompat(notif: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
        } else {
            startForeground(NOTIF_ID, notif)
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "Auspoty Music", NotificationManager.IMPORTANCE_LOW).apply {
                setSound(null, null); enableVibration(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            notifManager?.createNotificationChannel(ch)
        }
    }

    private fun setupWakeLock() {
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::WakeLock")
        wakeLock?.setReferenceCounted(false)
    }

    private fun registerReceiver() {
        val filter = IntentFilter().apply { addAction(ACTION_PLAY_PAUSE); addAction(ACTION_NEXT); addAction(ACTION_PREV) }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(receiver, filter)
        }
    }

    private fun acquireWakeLock() { if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L) }
    private fun releaseWakeLock() { if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {} }

    private fun toggleNativePlayPause() {
        if (mediaPlayer?.isPlaying == true) pauseNative() else resumeNative()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY_PAUSE -> if (isNativePlaying || mediaPlayer != null) toggleNativePlayPause() else onPlayPause?.invoke()
            ACTION_NEXT -> onNext?.invoke()
            ACTION_PREV -> onPrev?.invoke()
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) { Log.d(TAG, "onTaskRemoved — tetap jalan") }

    override fun onDestroy() {
        try { unregisterReceiver(receiver) } catch (_: Exception) {}
        mediaPlayer?.release(); mediaPlayer = null
        mediaSession?.release()
        releaseWakeLock()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            audioFocusRequest?.let { audioManager?.abandonAudioFocusRequest(it) }
        }
        instance = null
        super.onDestroy()
    }
}
