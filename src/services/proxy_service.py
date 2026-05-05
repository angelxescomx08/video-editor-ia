from collections.abc import Callable

from src.services.ffmpeg_service import FFmpegService


class ProxyService:
    def __init__(self, ffmpeg_service: FFmpegService) -> None:
        self._ffmpeg = ffmpeg_service

    def generate(
        self,
        src: str,
        dst: str,
        progress_ph=None,
        on_progress: Callable[[float], None] | None = None,
        total_duration: float = 0.0,
    ) -> tuple[bool, str]:
        args = [
            "-i", src,
            "-c:v", "libx264", "-crf", "28", "-preset", "faster",
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-movflags", "+faststart",
            dst,
        ]
        return self._ffmpeg.run_command(args, progress_ph, on_progress, total_duration)
