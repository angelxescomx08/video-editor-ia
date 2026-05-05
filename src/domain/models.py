from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Segment:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class VideoInfo:
    duration: float
    size: int
    width: int
    height: int
    fps: float
    vcodec: str
    acodec: str


class SidebarConfig(TypedDict):
    noise_pct: float
    min_silence: float
    buffer: float
    reduce_quality: bool
    crf_value: int
    n_workers: int
