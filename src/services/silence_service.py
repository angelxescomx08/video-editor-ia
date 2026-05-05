from collections.abc import Callable

from src.domain.models import Segment
from src.services.audio_analyzer import AudioAnalyzer
from src.services.silence_detector import SilenceDetector


class SilenceService:
    def __init__(self, analyzer: AudioAnalyzer, detector: SilenceDetector) -> None:
        self._analyzer = analyzer
        self._detector = detector

    def detect(
        self,
        video_path: str,
        noise_threshold_pct: float = 25.0,
        min_silence_dur: float = 0.7,
        buffer: float = 0.2,
        progress_ph=None,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[Segment]:
        rms_list, chunk_dur, duration = self._analyzer.extract_rms(
            video_path, progress_ph, on_progress
        )
        if not rms_list:
            return [Segment(start=0.0, end=duration)]
        return self._detector.detect(
            rms_list=rms_list,
            chunk_dur=chunk_dur,
            threshold=noise_threshold_pct / 100.0,
            min_silence_dur=min_silence_dur,
            buffer=buffer,
            duration=duration,
        )
