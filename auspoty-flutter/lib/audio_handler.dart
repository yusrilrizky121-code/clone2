import 'package:audio_service/audio_service.dart';
import 'package:just_audio/just_audio.dart';

/// AudioHandler yang jalan di Android foreground service
/// Audio tetap jalan saat app di-background atau screen off
class AuspotyAudioHandler extends BaseAudioHandler with SeekHandler {
  final _player = AudioPlayer();

  // Callbacks ke Flutter UI / WebView
  Function()? onSkipToNext;
  Function()? onSkipToPrevious;
  Function()? onCompleted;

  AuspotyAudioHandler() {
    // Forward player state ke audio_service stream
    _player.playbackEventStream.map(_transformEvent).pipe(playbackState);

    // Saat lagu selesai
    _player.processingStateStream.listen((state) {
      if (state == ProcessingState.completed) {
        onCompleted?.call();
      }
    });
  }

  PlaybackState _transformEvent(PlaybackEvent event) {
    return PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        _player.playing ? MediaControl.pause : MediaControl.play,
        MediaControl.skipToNext,
      ],
      systemActions: const {
        MediaAction.seek,
      },
      androidCompactActionIndices: const [0, 1, 2],
      processingState: const {
        ProcessingState.idle: AudioProcessingState.idle,
        ProcessingState.loading: AudioProcessingState.loading,
        ProcessingState.buffering: AudioProcessingState.buffering,
        ProcessingState.ready: AudioProcessingState.ready,
        ProcessingState.completed: AudioProcessingState.completed,
      }[_player.processingState]!,
      playing: _player.playing,
      updatePosition: _player.position,
      bufferedPosition: _player.bufferedPosition,
      speed: _player.speed,
      queueIndex: 0,
    );
  }

  /// Play dari URL langsung
  Future<void> playFromUrl(String url, MediaItem item) async {
    mediaItem.add(item);
    await _player.stop();
    await _player.setUrl(url);
    await _player.play();
  }

  @override
  Future<void> play() => _player.play();

  @override
  Future<void> pause() => _player.pause();

  @override
  Future<void> stop() async {
    await _player.stop();
    await super.stop();
  }

  @override
  Future<void> seek(Duration position) => _player.seek(position);

  @override
  Future<void> skipToNext() async {
    onSkipToNext?.call();
  }

  @override
  Future<void> skipToPrevious() async {
    onSkipToPrevious?.call();
  }

  Duration get position => _player.position;
  Duration? get duration => _player.duration;
  bool get isPlaying => _player.playing;

  Stream<Duration> get positionStream => _player.positionStream;
  Stream<ProcessingState> get processingStateStream => _player.processingStateStream;
}
