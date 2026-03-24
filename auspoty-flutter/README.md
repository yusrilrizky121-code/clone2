<div align="center">

<img src="assets/icon/icon.png" width="120" alt="Auspoty Logo" />

# Auspoty

**Aplikasi streaming musik gratis berbasis YouTube Music**

[![Version](https://img.shields.io/badge/version-8.1.0-a78bfa?style=flat-square)](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Android-green?style=flat-square&logo=android)](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

[⬇️ Download APK Terbaru](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)

</div>

---

## ✨ Fitur Utama

- 🎵 **Streaming musik** dari YouTube Music — jutaan lagu gratis
- 🔍 **Pencarian** lagu, artis, album, dan playlist
- 📥 **Download lagu** untuk diputar offline
- 🎧 **Background playback** — musik tetap jalan saat layar mati
- 🔔 **Notifikasi pengumuman** dari Admin langsung ke status bar
- 🖼️ **Foto profil** kustom dari galeri HP
- 🌙 **Dark mode** penuh
- 🔄 **Auto-update** — app otomatis cek dan download versi terbaru
- 📋 **Antrian lagu** dan mode repeat
- 🎤 **Lirik lagu** real-time

## 📱 Screenshot

> Streaming musik, download offline, notifikasi latar belakang, dan banyak lagi.

## 📦 Download & Install

1. Buka halaman [Releases](https://github.com/yusrilrizky121-code/Auspoty/releases/latest)
2. Download file `Auspoty-v*.apk`
3. Aktifkan **"Instal dari sumber tidak dikenal"** di pengaturan HP
4. Install APK

> Atau buka app → Pengaturan → **Periksa Pembaruan** untuk update otomatis

## 🔧 Persyaratan

- Android 5.0 (Lollipop) ke atas
- Koneksi internet untuk streaming
- ~20 MB ruang penyimpanan

## 🚀 Changelog

### v8.1.0
- ✅ Fitur auto-update otomatis dari GitHub Releases
- ✅ Notifikasi latar belakang tetap jalan saat app ditutup (BootReceiver)
- ✅ Judul notifikasi Admin dengan teks kustom
- ✅ Ganti foto profil dari galeri HP (native image picker)
- ✅ Battery exemption agar WorkManager tidak dibunuh sistem

### v8.0.0
- ✅ WorkManager background polling pengumuman (seperti Spotify)
- ✅ Notifikasi status bar dari email Admin
- ✅ Panel Admin untuk kirim pengumuman
- ✅ Fix konflik audio downloaded vs streaming

### v7.x
- ✅ Download lagu offline
- ✅ Background audio playback
- ✅ Google Login
- ✅ Lirik real-time

## 🛠️ Build dari Source

```bash
git clone https://github.com/yusrilrizky121-code/Auspoty.git
cd Auspoty
flutter pub get
flutter build apk --release --target-platform android-arm64 --split-per-abi
```

## 📄 Lisensi

MIT License — bebas digunakan dan dimodifikasi.

---

<div align="center">
Dibuat dengan ❤️ oleh <a href="https://github.com/yusrilrizky121-code">yusrilrizky121</a>
</div>
