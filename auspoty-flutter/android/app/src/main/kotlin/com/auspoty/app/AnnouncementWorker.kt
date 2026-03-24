package com.auspoty.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

class AnnouncementWorker(
    private val ctx: Context,
    params: WorkerParameters
) : CoroutineWorker(ctx, params) {

    companion object {
        const val TAG          = "AnnouncementWorker"
        const val CHANNEL_ID   = "auspoty_announce"
        const val NOTIF_ID     = 9001
        const val PREFS_NAME   = "auspoty_announce_prefs"
        const val KEY_LAST_ID  = "lastAnnouncementId"
        const val API_URL      = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/announcement"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Checking announcements...")
            val json = fetchAnnouncement() ?: return@withContext Result.success()

            val status  = json.optString("status", "none")
            if (status != "success") return@withContext Result.success()

            val id      = json.optString("id", "")
            val title   = json.optString("title", "Auspoty")
            val message = json.optString("message", "")
            val type    = json.optString("type", "info")

            if (message.isEmpty() && title.isEmpty()) return@withContext Result.success()

            // Cek apakah sudah pernah ditampilkan
            val prefs   = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val annKey  = if (id.isNotEmpty()) id else "$title|$message"
            val lastId  = prefs.getString(KEY_LAST_ID, "") ?: ""
            if (lastId == annKey) return@withContext Result.success()

            // Simpan id agar tidak muncul lagi
            prefs.edit().putString(KEY_LAST_ID, annKey).apply()

            // Tampilkan notifikasi
            showNotification(title.ifEmpty { "Auspoty" }, message.ifEmpty { title }, type)
            Log.d(TAG, "Announcement shown: $title")
        } catch (e: Exception) {
            Log.e(TAG, "Error: ${e.message}")
        }
        Result.success()
    }

    private fun fetchAnnouncement(): JSONObject? {
        return try {
            val conn = URL(API_URL).openConnection() as HttpsURLConnection
            conn.connectTimeout = 15_000
            conn.readTimeout    = 15_000
            conn.setRequestProperty("User-Agent", "AuspotyApp/1.0")
            val body = conn.inputStream.bufferedReader().readText()
            conn.disconnect()
            JSONObject(body)
        } catch (e: Exception) {
            Log.e(TAG, "Fetch error: ${e.message}")
            null
        }
    }

    private fun showNotification(title: String, message: String, type: String) {
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Buat channel kalau belum ada
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                CHANNEL_ID,
                "Pengumuman Auspoty",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifikasi pengumuman dari Auspoty"
                enableVibration(true)
            }
            nm.createNotificationChannel(ch)
        }

        val openIntent = PendingIntent.getActivity(
            ctx, NOTIF_ID,
            Intent(ctx, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val icon = when (type) {
            "update"  -> android.R.drawable.stat_sys_download_done
            "warning" -> android.R.drawable.ic_dialog_alert
            "promo"   -> android.R.drawable.ic_menu_info_details
            else      -> android.R.drawable.ic_dialog_info
        }

        val notif = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setSmallIcon(icon)
            .setContentIntent(openIntent)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .build()

        nm.notify(NOTIF_ID, notif)
    }
}
