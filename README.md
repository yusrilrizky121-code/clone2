<div align="center">

<img src="auspoty-flutter/assets/icon/icon.png" width="120" alt="Auspoty Logo" />

# 🎵 Auspoty

**Aplikasi streaming musik gratis berbasis YouTube Music**

[![Version](https://img.shields.io/badge/version-8.3.1-a78bfa?style=flat-square&logo=github)](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Android-3ddc84?style=flat-square&logo=android&logoColor=white)](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-54c5f8?style=flat-square&logo=flutter&logoColor=white)](https://flutter.dev)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

<br/>

[⬇️ **Download APK Terbaru**](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)

</div>

---

## ✨ Fitur

| Fitur | Keterangan |
|-------|-----------|
| 🎵 Streaming Musik | Jutaan lagu gratis dari YouTube Music |
| 🔍 Pencarian | Cari lagu, artis, album, dan playlist |
| 📥 Download Offline | Simpan lagu untuk diputar tanpa internet |
| 🎧 Background Playback | Musik tetap jalan saat layar mati |
| 🔔 Notifikasi Admin | Pengumuman langsung ke status bar |
| 🖼️ Foto Profil | Ganti foto profil dari galeri HP |
| 🌙 Dark Mode | Tampilan gelap penuh |
| 🔄 Auto-Update | Cek & download versi terbaru otomatis |
| 📋 Antrian Lagu | Queue & mode repeat |
| 🎤 Lirik Real-time | Lirik lagu saat memutar |

---

## 📦 Download & Install

1. Buka halaman **[Releases](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)**
2. Download file `Auspoty-v8.3.1.apk`
3. Aktifkan **"Instal dari sumber tidak dikenal"** di pengaturan HP
4. Install APK

> Atau buka app → Pengaturan → **Periksa Pembaruan** untuk update otomatis

### Persyaratan
- Android 5.0 (Lollipop) ke atas
- Koneksi internet untuk streaming
- ~20 MB ruang penyimpanan

---

## 🚀 Changelog

### v8.3.1 — Terbaru
- ✅ Fix koleksi lagu diunduh: play/pause sekarang berfungsi
- ✅ Fix tombol next/prev di lagu diunduh
- ✅ Auto-next ke lagu berikutnya saat lagu offline selesai
- ✅ Fix pengumuman admin via Firestore (persistent)

### v8.3.0
- ✅ Perbaikan performa streaming & playback
- ✅ Optimasi UI scroll dan animasi
- ✅ Fix background audio saat layar mati
- ✅ Perbaikan antrian lagu dan mode repeat

### v8.1.0
- ✅ Auto-update otomatis dari GitHub Releases
- ✅ Notifikasi latar belakang tetap jalan saat app ditutup (BootReceiver)
- ✅ Judul notifikasi Admin dengan teks kustom
- ✅ Ganti foto profil dari galeri HP (native image picker)
- ✅ Battery exemption agar WorkManager tidak dibunuh sistem

### v8.0.0
- ✅ WorkManager background polling pengumuman
- ✅ Notifikasi status bar dari email Admin
- ✅ Panel Admin untuk kirim pengumuman
- ✅ Fix konflik audio downloaded vs streaming

### v7.x
- ✅ Download lagu offline
- ✅ Background audio playback
- ✅ Google Login
- ✅ Lirik real-time

---

## 🛠️ Build dari Source

```bash
git clone https://github.com/yusrilrizky121-code/Auspoty.git
cd Auspoty/auspoty-flutter
flutter pub get
flutter build apk --release --target-platform android-arm64 --split-per-abi
```

APK output: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk`

---

## 🌐 Web App

Versi web tersedia di: **[auspoty.vercel.app](https://auspoty.vercel.app)**

---

## 📄 Lisensi

MIT License — bebas digunakan dan dimodifikasi.

---

<div align="center">
Dibuat dengan ❤️ oleh <a href="https://github.com/yusrilrizky121-code">yusrilrizky121</a>
</div>
