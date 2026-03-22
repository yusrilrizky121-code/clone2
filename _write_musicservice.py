#!/usr/bin/env python3
"""Tulis ulang MusicPlayerService.kt yang robust."""

content = '''package com.auspoty.app

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

class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_music"
        const val NOTIF_ID   = 77
        const val TAG        = "MusicPlayerService"

        const val ACTION_PLAY_PAUSE = "com.auspoty.app.PLAY_PAUSE"
        const val ACTION_NEXT       = "com.auspoty.app.NEXT"
        const val ACTION_PREV       = "com.auspoty.app.PREV"

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
    private var notifManager: NotificationManager? = null

    private var currentTitle  = "Auspoty"
    private var currentArtist = "Auspoty Music"
    private var isPlaying     = false

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            Log.d(TAG, "Received action: ${intent?.action}")
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
        notifManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        createChannel()
        setupMediaSession()
        setupWakeLock()
        registerReceiver()
        startForegroundCompat(buildNotif())
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

    private fun registerReceiver() {
        val filter = IntentFilter().apply {
            addAction(ACTION_PLAY_PAUSE)
            addAction(ACTION_NEXT)
            addAction(ACTION_PREV)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(receiver, filter)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_PLAY_PAUSE -> onPlayPause?.invoke()
            ACTION_NEXT       -> onNext?.invoke()
            ACTION_PREV       -> onPrev?.invoke()
        }
        return START_STICKY
    }

    // ── Public API ────────────────────────────────────────────────────────────

    fun updateTrackInfo(title: String, artist: String, playing: Boolean) {
        currentTitle  = title.ifEmpty { "Auspoty" }
        currentArtist = artist.ifEmpty { "Auspoty Music" }
        isPlaying     = playing
        if (playing) acquireWakeLock()
        updateMediaSessionMeta()
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "updateTrackInfo: $currentTitle | $currentArtist | playing=$isPlaying")
    }

    fun setPlaying(playing: Boolean) {
        isPlaying = playing
        if (playing) acquireWakeLock() else releaseWakeLock()
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "setPlaying: $isPlaying")
    }

    fun keepAlive() {
        acquireWakeLock()
        Log.d(TAG, "keepAlive, wakelock=${wakeLock?.isHeld}")
    }

    // ── MediaSession ──────────────────────────────────────────────────────────

    private fun updateMediaSessionMeta() {
        mediaSession?.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
                .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
                .build()
        )
    }

    private fun updatePlaybackState() {
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

        val playIcon  = if (isPlaying) android.R.drawable.ic_media_pause
                        else android.R.drawable.ic_media_play
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
            builder.setStyle(
                MediaStyle()
                    .setMediaSession(token)
                    .setShowActionsInCompactView(0, 1, 2)
            )
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
            val ch = NotificationChannel(
                CHANNEL_ID, "Auspoty Music", NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Kontrol musik Auspoty"
                setSound(null, null)
                enableVibration(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            notifManager?.createNotificationChannel(ch)
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == false) wakeLock?.acquire(6 * 60 * 60 * 1000L)
    }

    private fun releaseWakeLock() {
        if (wakeLock?.isHeld == true) try { wakeLock?.release() } catch (_: Exception) {}
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        Log.d(TAG, "onTaskRemoved — service tetap jalan")
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        try { unregisterReceiver(receiver) } catch (_: Exception) {}
        mediaSession?.release()
        releaseWakeLock()
        instance = null
        super.onDestroy()
    }
}
'''

path = 'auspoty-flutter/android/app/src/main/kotlin/com/auspoty/app/MusicPlayerService.kt'
open(path, 'w', encoding='utf-8').write(content)
print("Wrote MusicPlayerService.kt, lines:", len(content.split('\n')))
print("updateTrackInfo:", 'fun updateTrackInfo' in content)
print("setPlaying:", 'fun setPlaying' in content)
print("refreshNotif:", 'fun refreshNotif' in content)
print("BroadcastReceiver:", 'BroadcastReceiver' in content)
