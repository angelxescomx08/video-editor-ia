import concurrent.futures
import tempfile
from collections.abc import Callable
from pathlib import Path

from src.config import EXPORT_AUDIO_BITRATE, EXPORT_HQ_CRF, EXPORT_HQ_PRESET
from src.domain.models import Segment
from src.services.ffmpeg_service import FFmpegService
from src.services.progress_monitor import read_avg_progress
from src.services.video_concat import VideoConcat


class ParallelExporter:
    """Encodea cada segmento en paralelo y los une con stream copy."""

    def __init__(self, ffmpeg_service: FFmpegService, concat: VideoConcat) -> None:
        self._ffmpeg = ffmpeg_service
        self._concat = concat

    def export(
        self,
        src: str,
        dst: str,
        segments: list[Segment],
        reduce_quality: bool,
        crf_value: int,
        n_workers: int = 1,
        on_progress: Callable[[float], None] | None = None,
    ) -> tuple[bool, str]:
        vcodec = (
            ["-c:v", "libx264", "-crf", str(crf_value), "-preset", "faster"]
            if reduce_quality
            else ["-c:v", "libx264", "-crf", str(EXPORT_HQ_CRF), "-preset", EXPORT_HQ_PRESET]
        )
        with tempfile.TemporaryDirectory() as tmp:
            temp_files, error_log = self._encode_parallel(
                src, segments, tmp, vcodec, n_workers, on_progress
            )
            if error_log:
                return False, error_log
            return self._concat.concat(temp_files, dst, on_progress)

    def _encode_one(
        self,
        src: str,
        seg: Segment,
        dst: str,
        vcodec: list[str],
        progress_file: Path,
    ) -> tuple[bool, str]:
        args = [
            "-ss", str(seg.start), "-to", str(seg.end), "-i", src,
            *vcodec,
            "-c:a", "aac", "-b:a", EXPORT_AUDIO_BITRATE,
            "-avoid_negative_ts", "make_zero",
            "-progress", progress_file.as_posix(),
            dst,
        ]
        return self._ffmpeg.run_command(args)

    def _encode_parallel(
        self,
        src: str,
        segments: list[Segment],
        tmp_dir: str,
        vcodec: list[str],
        n_workers: int,
        on_progress: Callable[[float], None] | None,
    ) -> tuple[list[str], str]:
        tmp = Path(tmp_dir)
        out_paths = [tmp / f"seg_{i:04d}.mp4" for i in range(len(segments))]
        prog_paths = [tmp / f"prog_{i:04d}.txt" for i in range(len(segments))]
        prog_info = [(p, seg.duration) for p, seg in zip(prog_paths, segments)]

        error_log = ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [
                executor.submit(self._encode_one, src, seg, str(out), vcodec, prog)
                for seg, out, prog in zip(segments, out_paths, prog_paths)
            ]
            pending = set(futures)
            while pending:
                done, pending = concurrent.futures.wait(pending, timeout=1.0)
                if on_progress:
                    avg = read_avg_progress(prog_info)
                    on_progress(min(avg * 0.85, 0.85))

        for future in futures:
            ok, log = future.result()
            if not ok:
                error_log = log
                break

        return [str(p) for p in out_paths], error_log
