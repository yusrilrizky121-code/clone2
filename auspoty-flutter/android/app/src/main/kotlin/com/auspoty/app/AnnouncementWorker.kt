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
        // Baca langsung dari Firestore REST API — tidak bergantung Vercel serverless
        const val FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/auspoty-web/databases/(default)/documents/announcements/current?key=AIzaSyAYJEVXTS17vEX4J6_ymevMiJUnWV-Xf8Q"
        // Fallback: Vercel API
        const val API_URL_FALLBACK = "https://clone2-git-master-yusrilrizky121-codes-projects.vercel.app/api/announcement"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Checking announcements...")
            val json = fetchAnnouncement() ?: return@withContext Result.retry() // retry jika network gagal

            val status  = json.optString("status", "none")
            if (status != "success") return@withContext Result.success()

            val id      = json.optString("id", "")
            val title   = json.optString("title", "Auspoty")
            val message = json.optString("message", "")
            val type    = json.optString("type", "info")

            if (message.isEmpty() && title.isEmpty()) return@withContext Result.success()

            // Cek apakah sudah pernah ditampilkan (cek kedua prefs)
            val prefs   = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val annKey  = if (id.isNotEmpty()) id else "$title|$message"
            val lastId  = prefs.getString(KEY_LAST_ID, "") ?: ""
            // Juga cek Flutter SharedPreferences (ditulis oleh Dart saat app terbuka)
            val flutterPrefs = ctx.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
            val flutterLastId = flutterPrefs.getString("flutter.lastAnnouncementId", "") ?: ""
            if (lastId == annKey || flutterLastId == annKey) return@withContext Result.success()

            // Simpan id agar tidak muncul lagi
            prefs.edit().putString(KEY_LAST_ID, annKey).apply()
            // Juga tulis ke default SharedPreferences (dipakai oleh Dart/Flutter)
            // agar Dart tidak menganggap ini pengumuman baru
            ctx.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
                .edit().putString("flutter.lastAnnouncementId", annKey).apply()

            // Tampilkan notifikasi — judul selalu "Admin", isi = pesan dari email
            showNotification("Admin", message.ifEmpty { title }, type)
            Log.d(TAG, "Announcement shown: $title")
        } catch (e: Exception) {
            Log.e(TAG, "Error: ${e.message}")
        }
        Result.success()
    }

    private fun fetchAnnouncement(): JSONObject? {
        // Coba Firestore REST API dulu (langsung, persistent)
        val firestoreResult = fetchFromFirestore()
        if (firestoreResult != null) return firestoreResult
        // Fallback ke Vercel API
        return fetchFromVercel()
    }

    private fun fetchFromFirestore(): JSONObject? {
        return try {
            val conn = URL(FIRESTORE_URL).openConnection() as HttpsURLConnection
            conn.connectTimeout = 10_000
            conn.readTimeout    = 10_000
            conn.setRequestProperty("User-Agent", "AuspotyApp/1.0")
            val body = conn.inputStream.bufferedReader().readText()
            conn.disconnect()
            // Parse Firestore document format ke format biasa
            val doc = JSONObject(body)
            val fields = doc.optJSONObject("fields") ?: return JSONObject("""{"status":"none"}""")
            fun strVal(key: String, default: String = ""): String {
                return fields.optJSONObject(key)?.optString("stringValue", default) ?: default
            }
            val status = strVal("status", "none")
            if (status != "success") return JSONObject("""{"status":"none"}""")
            JSONObject().apply {
                put("status",  "success")
                put("id",      strVal("id"))
                put("title",   strVal("title"))
                put("message", strVal("message"))
                put("type",    strVal("type", "info"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Firestore fetch error: ${e.message}")
            null
        }
    }

    private fun fetchFromVercel(): JSONObject? {
        return try {
            val conn = URL(API_URL_FALLBACK).openConnection() as HttpsURLConnection
            conn.connectTimeout = 15_000
            conn.readTimeout    = 15_000
            conn.setRequestProperty("User-Agent", "AuspotyApp/1.0")
            val body = conn.inputStream.bufferedReader().readText()
            conn.disconnect()
            JSONObject(body)
        } catch (e: Exception) {
            Log.e(TAG, "Vercel fetch error: ${e.message}")
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
