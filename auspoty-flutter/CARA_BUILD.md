# Cara Build & Upload Auspoty ke Play Store

## Syarat
- Flutter SDK 3.x: https://flutter.dev/docs/get-started/install
- Android Studio / JDK 17
- Cek: `flutter doctor`

---

## Langkah 1 — Setup Awal (sekali saja)

```bash
cd auspoty-flutter
python setup_assets.py        # sync web files + generate icon
flutter pub get
dart run flutter_launcher_icons
```

---

## Langkah 2 — Buat Keystore (SEKALI SAJA, simpan baik-baik!)

```bash
keytool -genkey -v \
  -keystore auspoty-keystore.jks \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -alias auspoty
```

Isi pertanyaan:
- First and last name: Yusril
- Organization: Auspoty
- Country: ID
- Password: buat password yang kuat (catat!)

**PENTING: Backup file `auspoty-keystore.jks` — kalau hilang tidak bisa update app di Play Store!**

---

## Langkah 3 — Buat file `android/key.properties`

Buat file `auspoty-flutter/android/key.properties` (jangan di-commit ke git!):

```properties
storePassword=PASSWORD_KEYSTORE_KAMU
keyPassword=PASSWORD_KEY_KAMU
keyAlias=auspoty
storeFile=../../auspoty-keystore.jks
```

Pastikan path `storeFile` relatif dari folder `android/app/`.

---

## Langkah 4 — Build APK (untuk test di HP)

```bash
cd auspoty-flutter
python setup_assets.py
flutter build apk --release
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

Install ke HP:
```bash
adb install build/app/outputs/flutter-apk/app-release.apk
```

---

## Langkah 5 — Build AAB untuk Play Store

```bash
cd auspoty-flutter
python setup_assets.py
flutter build appbundle --release
```

Output: `build/app/outputs/bundle/release/app-release.aab`

---

## Langkah 6 — Upload ke Play Store

1. Buka https://play.google.com/console
2. Buat app baru:
   - Nama: **Auspoty**
   - Bahasa default: Indonesia
   - App atau Game: **App**
   - Gratis atau Berbayar: **Gratis**
3. Isi semua bagian yang wajib:

### Store Listing
- **Judul**: Auspoty - Music & Lyrics
- **Deskripsi singkat**: Streaming musik gratis dengan lirik real-time
- **Deskripsi panjang**:
  ```
  Auspoty adalah aplikasi streaming musik gratis yang memungkinkan kamu 
  mendengarkan jutaan lagu dari seluruh dunia. Fitur unggulan:
  
  🎵 Streaming musik tanpa batas
  📝 Lirik real-time tersinkronisasi
  🔍 Pencarian lagu, artis, dan album
  ❤️ Simpan lagu favorit
  📋 Buat dan kelola playlist
  🌙 Mode gelap
  🎨 Tema warna kustom
  🌏 Konten multi-bahasa (Indonesia, English, Japanese, Korean)
  🔔 Notifikasi lagu yang sedang diputar
  ```
- **Kategori**: Musik & Audio
- **Tag**: musik, streaming, lirik, lagu, playlist

### Screenshot yang dibutuhkan
- Minimal 2 screenshot HP (1080x1920 atau 1080x2340)
- Opsional: tablet screenshot

### Icon
- Icon 512x512 PNG (sudah ada di `assets/icon/icon.png`, resize ke 512x512)

### Feature Graphic
- 1024x500 PNG (banner untuk Play Store)

### Content Rating
- Isi kuesioner → pilih kategori Music
- Rating: Everyone

### Privacy Policy
Wajib ada! Buat halaman sederhana, contoh di GitHub Pages:
```
Auspoty tidak mengumpulkan data pribadi pengguna. 
Data playlist dan preferensi disimpan lokal di perangkat.
Login Google opsional untuk fitur komentar.
```

### Target Audience
- Usia: 13+
- Bukan untuk anak-anak

---

## Update App (versi baru)

1. Naikkan `versionCode` dan `versionName` di `android/app/build.gradle`
2. Jalankan `python setup_assets.py`
3. Build AAB baru: `flutter build appbundle --release`
4. Upload AAB baru di Play Console → Production → Create new release

---

## Troubleshooting

**Error: keystore not found**
→ Pastikan path di `key.properties` benar, relatif dari folder `android/`

**Error: minSdk**
→ Sudah di-set ke 21 (Android 5.0+), cukup untuk 99% device

**Error: duplicate class**
→ Jalankan `flutter clean` lalu `flutter pub get` lagi

**App crash saat buka**
→ Cek `adb logcat` untuk error detail

**Musik tidak bunyi di background**
→ Pastikan permission FOREGROUND_SERVICE sudah granted di settings HP
