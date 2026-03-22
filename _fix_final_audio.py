import os
os.chdir(r'C:\Users\Admin\Downloads\Auspoty')

# ── audio_handler.dart ────────────────────────────────────────────────────────
audio_handler = r'''import 'dart:async';
import 'package:audio_service/audio_service.dart';
import 'package:audio_session/audio_session.dart';
import 'package:just_audio/just_audio.dart';

class AuspotyAudioHandler extends BaseAudioHandler with SeekHandler {
  late final AudioPlayer audioPlayer;

  void Function()? onSkipToNext;
  void Function()? onSkipToPrevious;

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
    audioPlayer.playbackEventStream.listen((_) => _updateState(), onError: (_) {});
    audioPlayer.processingStateStream.listen((s) {
      if (s == ProcessingState.completed) onSkipToNext?.call();
      _updateState();
    });
    audioPlayer.setAndroidAudioAttributes(const AndroidAudioAttributes(
      contentType: AndroidAudioContentType.music,
      usage: AndroidAudioUsage.media,
    ));
    _initSession();
  }

  Future<void> _initSession() async {
    try {
      final s = await AudioSession.instance;
      await s.configure(const AudioSessionConfiguration.music());
      await audioPlayer.setLoopMode(LoopMode.off);
    } catch (_) {}
  }

  Future<void> playFromUrl(String url, MediaItem item, {Map<String, String>? headers}) async {
    try {
      mediaItem.add(item);
      _emitLoading();
      if (audioPlayer.playing) await audioPlayer.stop();
      await audioPlayer.setAudioSource(
        AudioSource.uri(Uri.parse(url), headers: headers, tag: item),
      );
      await audioPlayer.play();
      // Update durasi
      final dur = audioPlayer.duration;
      if (dur != null) mediaItem.add(item.copyWith(duration: dur));
    } catch (_) {}
  }

  void _emitLoading() {
    playbackState.add(PlaybackState(
      controls: [MediaControl.skipToPrevious, MediaControl.pause, MediaControl.skipToNext],
      androidCompactActionIndices: const [0, 1, 2],
      processingState: AudioProcessingState.loading,
      playing: true,
    ));
  }

  void _updateState() {
    final playing = audioPlayer.playing;
    playbackState.add(PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        if (playing) MediaControl.pause else MediaControl.play,
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
      playing: playing,
      updatePosition: audioPlayer.position,
      bufferedPosition: audioPlayer.bufferedPosition,
      speed: audioPlayer.speed,
    ));
  }

  @override Future<void> play() => audioPlayer.play();
  @override Future<void> pause() => audioPlayer.pause();
  @override Future<void> stop() async { await audioPlayer.stop(); await super.stop(); }
  @override Future<void> seek(Duration p) => audioPlayer.seek(p);
  @override Future<void> skipToNext() async => onSkipToNext?.call();
  @override Future<void> skipToPrevious() async => onSkipToPrevious?.call();

  int get durationSeconds => audioPlayer.duration?.inSeconds ?? 0;
  Stream<Duration> get positionStream => audioPlayer.positionStream;
  bool get isPlaying => audioPlayer.playing;
}
'''

with open(r'auspoty-flutter\lib\audio_handler.dart', 'w', encoding='utf-8') as f:
    f.write(audio_handler)
print("audio_handler.dart OK")
