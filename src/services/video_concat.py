import tempfile
from collections.abc import Callable
from pathlib import Path

from src.services.ffmpeg_service import FFmpegService


class VideoConcat:
    """Concatena archivos de video con stream copy usando el concat demuxer de FFmpeg."""

    def __init__(self, ffmpeg_service: FFmpegService) -> None:
        self._ffmpeg = ffmpeg_service

    def concat(
        self,
        temp_files: list[str],
        dst: str,
        on_progress: Callable[[float], None] | None = None,
    ) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.writelines(f"file '{p}'\n" for p in temp_files)
            concat_path = f.name

        args = [
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-c", "copy", "-movflags", "+faststart",
            dst,
        ]
        ok, log = self._ffmpeg.run_command(args)
        Path(concat_path).unlink(missing_ok=True)
        if on_progress:
            on_progress(1.0)
        return ok, log
