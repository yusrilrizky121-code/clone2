import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

audio_handler = r'''import 'dart:async';
import 'package:audio_service/audio_service.dart';
import 'package:audio_session/audio_session.dart';
import 'package:just_audio/just_audio.dart';

class AuspotyAudioHandler extends BaseAudioHandler with SeekHandler {
  late final AudioPlayer audioPlayer;

  void Function()? onSkipToNext;
  void Function()? onSkipToPrevious;
  void Function()? onPlayPauseToggle;

  AuspotyAudioHandler() {
    audioPlayer = AudioPlayer(
      audioLoadConfiguration: const AudioLoadConfiguration(
        androidLoadControl: AndroidLoadControl(
          maxBufferDuration: Duration(seconds: 60),
          bufferForPlaybackDuration: Duration(milliseconds: 500),
          bufferForPlaybackAfterRebufferDuration: Duration(seconds: 3),
        ),
      ),
    );

    audioPlayer.playbackEventStream.listen((_) => _updatePlaybackState(),
        onError: (e) {});

    audioPlayer.processingStateStream.listen((state) {
      if (state == ProcessingState.completed) onSkipToNext?.call();
      _updatePlaybackState();
    });

    audioPlayer.setAndroidAudioAttributes(
      const AndroidAudioAttributes(
        contentType: AndroidAudioContentType.music,
        usage: AndroidAudioUsage.media,
      ),
    );

    _initAudioSession();
  }

  Future<void> _initAudioSession() async {
    try {
      final session = await AudioSession.instance;
      await session.configure(const AudioSessionConfiguration.music());
      await audioPlayer.setLoopMode(LoopMode.off);
    } catch (_) {}
  }

  // Headers yang dibutuhkan YouTube — sama persis dengan yang API return
  static const _ytHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
  };

  Future<void> playFromUrl(String url, MediaItem item, {Map<String, String>? headers}) async {
    try {
      mediaItem.add(item);
      _emitLoadingState();

      // Stop dulu kalau sedang play
      if (audioPlayer.playing) await audioPlayer.stop();

      final effectiveHeaders = headers ?? _ytHeaders;

      await audioPlayer.setAudioSource(
        AudioSource.uri(
          Uri.parse(url),
          headers: effectiveHeaders,
          tag: item,
        ),
      );
      await audioPlayer.play();

      // Update durasi setelah loaded
      audioPlayer.durationStream.firstWhere((d) => d != null).then((dur) {
        if (dur != null) mediaItem.add(item.copyWith(duration: dur));
      }).catchError((_) {});
    } catch (e) {
      // ignore
    }
  }

  void _emitLoadingState() {
    playbackState.add(PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        MediaControl.pause,
        MediaControl.skipToNext,
      ],
      androidCompactActionIndices: const [0, 1, 2],
      processingState: AudioProcessingState.loading,
      playing: true,
    ));
  }

  void _updatePlaybackState() {
    final isPlaying = audioPlayer.playing;
    playbackState.add(PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        if (isPlaying) MediaControl.pause else MediaControl.play,
        MediaControl.skipToNext,
      ],
      systemActions: const {MediaAction.seek},
      androidCompactActionIndices: const [0, 1, 2],
      processingState: const {
        ProcessingState.idle: AudioProcessingState.idle,
        ProcessingState.loading: AudioProcessingState.loading,
        ProcessingState.buffering: AudioProcessingState.buffering,
        ProcessingState.ready: AudioProcessingState.ready,
        ProcessingState.completed: AudioProcessingState.completed,
      }[audioPlayer.processingState]!,
      playing: isPlaying,
      updatePosition: audioPlayer.position,
      bufferedPosition: audioPlayer.bufferedPosition,
      speed: audioPlayer.speed,
    ));
  }

  @override Future<void> play() => audioPlayer.play();
  @override Future<void> pause() => audioPlayer.pause();
  @override Future<void> stop() async { await audioPlayer.stop(); await super.stop(); }
  @override Future<void> seek(Duration position) => audioPlayer.seek(position);
  @override Future<void> skipToNext() async => onSkipToNext?.call();
  @override Future<void> skipToPrevious() async => onSkipToPrevious?.call();

  int get durationSeconds => audioPlayer.duration?.inSeconds ?? 0;
  Stream<Duration> get positionStream => audioPlayer.positionStream;
  bool get isPlaying => audioPlayer.playing;
}
'''

with open(r'auspoty-flutter\lib\audio_handler.dart', 'w', encoding='utf-8') as f:
    f.write(audio_handler)
print("audio_handler.dart written")
