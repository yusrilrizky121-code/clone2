#!/usr/bin/env python3
"""
Solusi tuntas background audio:
- Fetch audio URL dari /api/stream (yt-dlp)
- Putar via Android MediaPlayer native di MusicPlayerService
- YouTube IFrame tetap dipakai untuk UI (progress bar, thumbnail)
- Saat background: audio dari MediaPlayer tetap jalan
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ── 1. MusicPlayerService.kt — tambah MediaPlayer ────────────────────────────
service_kt = '''package com.auspoty.app

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
        var onPositionUpdate: ((Int, Int) -> Unit)? = null  // position, duration in seconds

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
    private var isPlaying     = false
    private var isNativePlaying = false  // true = MediaPlayer aktif

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

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Dipanggil dari JS onMusicPlaying via Flutter bridge.
     * Fetch audio URL dari /api/stream dan putar via MediaPlayer.
     */
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

        // Fetch stream URL di background thread
        Thread {
            try {
                Log.d(TAG, "Fetching stream URL for $videoId")
                val streamUrl = fetchStreamUrl(videoId)
                Log.d(TAG, "Got stream URL, starting MediaPlayer")
                startMediaPlayer(streamUrl)
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
        mediaPlayer?.stop()
        mediaPlayer?.release()
        mediaPlayer = null
        isPlaying = false
        isNativePlaying = false
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "MediaPlayer stopped")
    }

    fun updateTrackInfo(title: String, artist: String, playing: Boolean) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist.ifEmpty { "Auspoty Music" }
        isPlaying     = playing
        if (playing) acquireWakeLock()
        updateMediaSessionMeta()
        updatePlaybackState()
        refreshNotif()
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

    // ── MediaPlayer ───────────────────────────────────────────────────────────

    private fun fetchStreamUrl(videoId: String): String {
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
        return json.getString("url")
    }

    private fun startMediaPlayer(streamUrl: String) {
        // Harus di main thread untuk MediaPlayer
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
                    setDataSource(streamUrl)
                    setOnPreparedListener { player ->
                        player.start()
                        isNativePlaying = true
                        isPlaying = true
                        updatePlaybackState()
                        refreshNotif()
                        Log.d(TAG, "MediaPlayer started, duration=${player.duration/1000}s")
                    }
                    setOnCompletionListener {
                        isNativePlaying = false
                        isPlaying = false
                        onNext?.invoke()
                        Log.d(TAG, "MediaPlayer completed, calling onNext")
                    }
                    setOnErrorListener { _, what, extra ->
                        Log.e(TAG, "MediaPlayer error: what=$what extra=$extra")
                        isNativePlaying = false
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

    // ── MediaSession ──────────────────────────────────────────────────────────

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
        mediaSession?.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
                .build()
        )
    }

    private fun updatePlaybackState() {
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
    }

    // ── Notification ─────────────────────────────────────────────────────────

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
'''

open('auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MusicPlayerService.kt', 'w', encoding='utf-8').write(service_kt)
print("✓ MusicPlayerService.kt written, lines:", len(service_kt.split('\n')))

# ── 2. MainActivity.kt — tambah playNative/pauseNative/resumeNative channel ──
main_kt = '''package com.auspoty.app

import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object { const val CHANNEL = "com.auspoty.app/music" }

    private var service: MusicPlayerService? = null
    private var bound = false
    private var channel: MethodChannel? = null

    private val conn = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            service = (binder as MusicPlayerService.LocalBinder).getService()
            bound = true
            setupServiceCallbacks()
        }
        override fun onServiceDisconnected(name: ComponentName?) { bound = false; service = null }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                "playNative" -> {
                    val videoId = call.argument<String>("videoId") ?: ""
                    val title   = call.argument<String>("title")   ?: ""
                    val artist  = call.argument<String>("artist")  ?: ""
                    service?.playNative(videoId, title, artist)
                    result.success(null)
                }
                "pauseNative" -> { service?.pauseNative(); result.success(null) }
                "resumeNative" -> { service?.resumeNative(); result.success(null) }
                "stopNative" -> { service?.stopNative(); result.success(null) }
                "updateTrack" -> {
                    val title   = call.argument<String>("title")      ?: ""
                    val artist  = call.argument<String>("artist")     ?: ""
                    val playing = call.argument<Boolean>("isPlaying") ?: true
                    service?.updateTrackInfo(title, artist, playing)
                    result.success(null)
                }
                "setPlaying" -> {
                    val playing = call.argument<Boolean>("isPlaying") ?: false
                    service?.setPlaying(playing)
                    result.success(null)
                }
                "getPosition" -> result.success(service?.getPosition() ?: 0)
                "getDuration" -> result.success(service?.getDuration() ?: 0)
                "seekTo" -> {
                    val pos = call.argument<Int>("position") ?: 0
                    service?.seekTo(pos)
                    result.success(null)
                }
                "keepAlive" -> { service?.keepAlive(); result.success(null) }
                else -> result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startServiceSafe(Intent(this, MusicPlayerService::class.java))
        bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
    }

    override fun onResume() {
        super.onResume()
        if (!bound) bindService(Intent(this, MusicPlayerService::class.java), conn, BIND_AUTO_CREATE)
        setupServiceCallbacks()
    }

    override fun onDestroy() {
        if (bound) { unbindService(conn); bound = false }
        super.onDestroy()
    }

    private fun setupServiceCallbacks() {
        MusicPlayerService.onPlayPause = {
            runOnUiThread { channel?.invokeMethod("onPlayPause", null) }
        }
        MusicPlayerService.onNext = {
            runOnUiThread { channel?.invokeMethod("onNext", null) }
        }
        MusicPlayerService.onPrev = {
            runOnUiThread { channel?.invokeMethod("onPrev", null) }
        }
    }

    private fun startServiceSafe(intent: Intent) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent)
            else startService(intent)
        } catch (e: Exception) { android.util.Log.e("MainActivity", "startService: ${e.message}") }
    }
}
'''

open('auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MainActivity.kt', 'w', encoding='utf-8').write(main_kt)
print("✓ MainActivity.kt written, lines:", len(main_kt.split('\n')))
print("playNative:", 'playNative' in main_kt)
print("pauseNative:", 'pauseNative' in main_kt)
