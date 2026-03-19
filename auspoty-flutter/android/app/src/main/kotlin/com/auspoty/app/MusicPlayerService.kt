package com.auspoty.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Pure foreground service — TIDAK ada ExoPlayer.
 * Tujuan: jaga proses Flutter + WebView tetap hidup saat app di-background.
 * Musik diputar oleh ytPlayer di dalam WebView (sudah terbukti bisa play).
 * WakeLock mencegah CPU sleep saat layar mati.
 */
class MusicPlayerService : Service() {

    companion object {
        const val CHANNEL_ID = "auspoty_player"
        const val NOTIF_ID   = 42
        const val TAG        = "MusicPlayerService"

        const val ACTION_UPDATE_NOTIF = "com.auspoty.app.UPDATE_NOTIF"
        const val EXTRA_TITLE         = "title"
        const val EXTRA_ARTIST        = "artist"
        const val EXTRA_PLAYING       = "playing"
    }

    private var wakeLock: PowerManager.WakeLock? = null
    private var currentTitle  = "Auspoty"
    private var currentArtist = "Sedang memutar musik"

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        // WakeLock — CPU tetap aktif saat layar mati
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        @Suppress("DEPRECATION")
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Auspoty::WakeLock")
        wakeLock?.setReferenceCounted(false)
        wakeLock?.acquire(6 * 60 * 60 * 1000L) // max 6 jam

        startForegroundCompat(buildNotification(currentTitle, currentArtist))
        Log.d(TAG, "Service started — keeping process alive for background audio")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_UPDATE_NOTIF -> {
                val title   = intent.getStringExtra(EXTRA_TITLE)   ?: currentTitle
                val artist  = intent.getStringExtra(EXTRA_ARTIST)  ?: currentArtist
                val playing = intent.getBooleanExtra(EXTRA_PLAYING, true)
                currentTitle  = title
                currentArtist = if (playing) artist else "Dijeda"
                updateNotification(currentTitle, currentArtist)
                // Pastikan wakelock aktif saat musik playing
                if (playing && wakeLock?.isHeld == false) {
                    wakeLock?.acquire(6 * 60 * 60 * 1000L)
                }
            }
        }
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Jangan stop service saat app di-swipe dari recents
        // Service tetap jalan → WebView tetap hidup → musik tetap bunyi
        Log.d(TAG, "onTaskRemoved — service tetap jalan")
        // Tidak call super, tidak stopSelf
    }

    override fun onDestroy() {
        Log.d(TAG, "Service destroyed")
        if (wakeLock?.isHeld == true) {
            try { wakeLock?.release() } catch (_: Exception) {}
        }
        super.onDestroy()
    }

    private fun updateNotification(title: String, text: String) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, buildNotification(title, text))
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
            val ch = NotificationChannel(
                CHANNEL_ID, "Auspoty Music", NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Background audio Auspoty"
                setSound(null, null)
                enableVibration(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(ch)
        }
    }
}
