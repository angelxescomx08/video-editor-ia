from src.config import MIN_SEGMENT_DURATION
from src.domain.models import Segment


class SilenceDetector:
    """Convierte una lista de RMS en segmentos a conservar."""

    def detect(
        self,
        rms_list: list[float],
        chunk_dur: float,
        threshold: float,
        min_silence_dur: float,
        buffer: float,
        duration: float,
    ) -> list[Segment]:
        intervals = self._group_silent_chunks(rms_list, chunk_dur, threshold, min_silence_dur)
        return self._build_keep_segments(intervals, buffer, duration)

    def _group_silent_chunks(
        self,
        rms_list: list[float],
        chunk_dur: float,
        threshold: float,
        min_silence_dur: float,
    ) -> list[tuple[float, float]]:
        intervals: list[tuple[float, float]] = []
        in_silence = False
        s_start = 0.0
        for i, rms in enumerate(rms_list):
            t = i * chunk_dur
            if rms < threshold and not in_silence:
                in_silence, s_start = True, t
            elif rms >= threshold and in_silence:
                in_silence = False
                if t - s_start >= min_silence_dur:
                    intervals.append((s_start, t))
        if in_silence:
            s_end = len(rms_list) * chunk_dur
            if s_end - s_start >= min_silence_dur:
                intervals.append((s_start, s_end))
        return intervals

    def _build_keep_segments(
        self,
        intervals: list[tuple[float, float]],
        buffer: float,
        duration: float,
    ) -> list[Segment]:
        keep: list[Segment] = []
        prev_end = 0.0
        for s_start, s_end in intervals:
            seg_end = min(s_start + buffer, s_end - buffer)
            if seg_end > prev_end + MIN_SEGMENT_DURATION:
                keep.append(Segment(start=round(prev_end, 3), end=round(seg_end, 3)))
            prev_end = max(s_end - buffer, seg_end)
        if prev_end < duration - 0.1:
            keep.append(Segment(start=round(prev_end, 3), end=round(duration, 3)))
        return keep if keep else [Segment(start=0.0, end=duration)]
