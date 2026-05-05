from src.config import MIN_SEGMENT_DURATION
from src.domain.models import Segment


class SegmentCalculator:
    def compute_final(
        self,
        silence_segments: list[Segment] | None,
        gemini_cuts: list[Segment] | None,
        duration: float,
    ) -> list[Segment] | None:
        if silence_segments is None and gemini_cuts is None:
            return None
        base = silence_segments or [Segment(start=0.0, end=duration)]
        return self.subtract_cuts(base, gemini_cuts) if gemini_cuts else base

    def subtract_cuts(
        self,
        keep_segments: list[Segment],
        cuts: list[Segment],
    ) -> list[Segment]:
        result: list[Segment] = []
        for seg in keep_segments:
            remaining: list[tuple[float, float]] = [(seg.start, seg.end)]
            for cut in cuts:
                next_r: list[tuple[float, float]] = []
                for a, b in remaining:
                    if cut.end <= a or cut.start >= b:
                        next_r.append((a, b))
                    else:
                        if cut.start > a:
                            next_r.append((a, cut.start))
                        if cut.end < b:
                            next_r.append((cut.end, b))
                remaining = next_r
            result.extend(
                Segment(start=round(a, 3), end=round(b, 3))
                for a, b in remaining
                if b - a > MIN_SEGMENT_DURATION
            )
        return result
