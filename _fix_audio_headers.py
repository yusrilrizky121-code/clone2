"""
Fix: MusicPlayerService - tambah headers ke MediaPlayer setDataSource
Root cause: googlevideo.com URL butuh User-Agent & Referer header dari YouTube
"""
import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

SERVICE_PATH = r'auspoty-flutter\android\app\src\main\kotlin\com\auspoty\app\MusicPlayerService.kt'

with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Ganti setDataSource(streamUrl) dengan versi yang pakai headers
old_datasource = '                    setDataSource(streamUrl)'
new_datasource = '''                    val uri = android.net.Uri.parse(streamUrl)
                    val headers = mapOf(
                        "User-Agent" to "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                        "Referer" to "https://www.youtube.com/",
                        "Origin" to "https://www.youtube.com"
                    )
                    setDataSource(applicationContext, uri, headers)'''

if old_datasource in content:
    content = content.replace(old_datasource, new_datasource)
    print("✓ Fixed setDataSource with headers")
else:
    print("✗ setDataSource pattern not found, checking...")
    # Find the actual pattern
    idx = content.find('setDataSource')
    if idx >= 0:
        print(f"Found setDataSource at: {repr(content[idx-50:idx+100])}")

# Fix 2: Update playbackState dengan posisi yang benar (untuk progress bar di notifikasi)
old_state = '''    private fun updatePlaybackState() {
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
    }'''

new_state = '''    private fun updatePlaybackState() {
        val state = if (isPlaying) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED
        val pos = try { mediaPlayer?.currentPosition?.toLong() ?: PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN } catch (e: Exception) { PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN }
        val dur = try { mediaPlayer?.duration?.toLong() ?: 0L } catch (e: Exception) { 0L }
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
        // Update metadata dengan durasi
        if (dur > 0) {
            mediaSession?.setMetadata(
                android.support.v4.media.MediaMetadataCompat.Builder()
                    .putString(android.support.v4.media.MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle)
                    .putString(android.support.v4.media.MediaMetadataCompat.METADATA_KEY_ARTIST, currentArtist)
                    .putLong(android.support.v4.media.MediaMetadataCompat.METADATA_KEY_DURATION, dur)
                    .build()
            )
        }
    }'''

if old_state in content:
    content = content.replace(old_state, new_state)
    print("✓ Fixed updatePlaybackState with position")
else:
    print("✗ updatePlaybackState pattern not found")

# Fix 3: Tambah periodic position update saat MediaPlayer playing
old_prepared = '''                    setOnPreparedListener { player ->
                        player.start()
                        isNativePlaying = true
                        isPlaying = true
                        updatePlaybackState()
                        refreshNotif()
                        Log.d(TAG, "MediaPlayer started, duration=${player.duration/1000}s")
                    }'''

new_prepared = '''                    setOnPreparedListener { player ->
                        player.start()
                        isNativePlaying = true
                        isPlaying = true
                        updatePlaybackState()
                        refreshNotif()
                        Log.d(TAG, "MediaPlayer started, duration=${player.duration/1000}s")
                        // Start periodic position update untuk progress bar di notifikasi
                        startPositionUpdater()
                    }'''

if old_prepared in content:
    content = content.replace(old_prepared, new_prepared)
    print("✓ Fixed onPreparedListener with position updater")
else:
    print("✗ onPreparedListener pattern not found")

# Fix 4: Tambah startPositionUpdater function sebelum requestAudioFocus
old_audio_focus = '    private fun requestAudioFocus() {'
new_position_updater = '''    private var positionHandler: android.os.Handler? = null
    private var positionRunnable: Runnable? = null

    private fun startPositionUpdater() {
        stopPositionUpdater()
        positionHandler = android.os.Handler(android.os.Looper.getMainLooper())
        positionRunnable = object : Runnable {
            override fun run() {
                if (isNativePlaying && mediaPlayer != null) {
                    try {
                        updatePlaybackState()
                        // Kirim posisi ke Flutter via callback
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

    private fun requestAudioFocus() {'''

if old_audio_focus in content:
    content = content.replace(old_audio_focus, new_position_updater)
    print("✓ Added startPositionUpdater function")
else:
    print("✗ requestAudioFocus pattern not found")

# Fix 5: Stop position updater saat pause/stop
old_pause = '''    fun pauseNative() {
        if (mediaPlayer?.isPlaying == true) {
            mediaPlayer?.pause()
            isPlaying = false
            isNativePlaying = false
            updatePlaybackState()
            refreshNotif()
            Log.d(TAG, "MediaPlayer paused")
        }
    }'''

new_pause = '''    fun pauseNative() {
        if (mediaPlayer?.isPlaying == true) {
            mediaPlayer?.pause()
            isPlaying = false
            isNativePlaying = false
            stopPositionUpdater()
            updatePlaybackState()
            refreshNotif()
            Log.d(TAG, "MediaPlayer paused")
        }
    }'''

if old_pause in content:
    content = content.replace(old_pause, new_pause)
    print("✓ Fixed pauseNative with stopPositionUpdater")
else:
    print("✗ pauseNative pattern not found")

old_stop = '''    fun stopNative() {
        mediaPlayer?.stop()
        mediaPlayer?.release()
        mediaPlayer = null
        isPlaying = false
        isNativePlaying = false
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "MediaPlayer stopped")
    }'''

new_stop = '''    fun stopNative() {
        stopPositionUpdater()
        mediaPlayer?.stop()
        mediaPlayer?.release()
        mediaPlayer = null
        isPlaying = false
        isNativePlaying = false
        updatePlaybackState()
        refreshNotif()
        Log.d(TAG, "MediaPlayer stopped")
    }'''

if old_stop in content:
    content = content.replace(old_stop, new_stop)
    print("✓ Fixed stopNative with stopPositionUpdater")
else:
    print("✗ stopNative pattern not found")

with open(SERVICE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ MusicPlayerService.kt updated!")
print("Verifying...")
with open(SERVICE_PATH, 'r', encoding='utf-8') as f:
    verify = f.read()
print(f"  - setDataSource with headers: {'✓' if 'User-Agent' in verify else '✗'}")
print(f"  - startPositionUpdater: {'✓' if 'startPositionUpdater' in verify else '✗'}")
print(f"  - playbackState with position: {'✓' if 'currentPosition?.toLong()' in verify else '✗'}")
