import concurrent.futures
import tempfile
from collections.abc import Callable
from pathlib import Path

from src.config import PROXY_AUDIO_BITRATE, PROXY_CRF, PROXY_PRESET
from src.services.ffmpeg_service import FFmpegService
from src.services.progress_monitor import read_avg_progress
from src.services.video_concat import VideoConcat

_CHUNKS_PER_WORKER = 4


class ParallelProxyGenerator:
    """
    Divide el video en n_workers × _CHUNKS_PER_WORKER chunks,
    los encodea en paralelo y une con stream copy.
    """

    def __init__(self, ffmpeg_service: FFmpegService, concat: VideoConcat) -> None:
        self._ffmpeg = ffmpeg_service
        self._concat = concat

    def generate(
        self,
        src: str,
        dst: str,
        total_duration: float,
        n_workers: int = 1,
        on_progress: Callable[[float], None] | None = None,
    ) -> tuple[bool, str]:
        n_chunks = n_workers * _CHUNKS_PER_WORKER
        chunk_dur = total_duration / n_chunks
        ranges = [
            (i * chunk_dur, min((i + 1) * chunk_dur, total_duration))
            for i in range(n_chunks)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            temp_files, error_log = self._encode_parallel(
                src, ranges, tmp, n_workers, chunk_dur, on_progress
            )
            if error_log:
                return False, error_log
            return self._concat.concat(temp_files, dst, on_progress)

    def _encode_one(
        self, src: str, start: float, end: float, dst: str, progress_file: Path
    ) -> tuple[bool, str]:
        args = [
            "-ss", str(start), "-to", str(end), "-i", src,
            "-c:v", "libx264", "-crf", str(PROXY_CRF), "-preset", PROXY_PRESET,
            "-c:a", "libmp3lame", "-b:a", PROXY_AUDIO_BITRATE,
            "-avoid_negative_ts", "make_zero",
            "-progress", progress_file.as_posix(),
            dst,
        ]
        return self._ffmpeg.run_command(args)

    def _encode_parallel(
        self,
        src: str,
        ranges: list[tuple[float, float]],
        tmp_dir: str,
        n_workers: int,
        chunk_dur: float,
        on_progress: Callable[[float], None] | None,
    ) -> tuple[list[str], str]:
        tmp = Path(tmp_dir)
        out_paths = [tmp / f"chunk_{i:04d}.mp4" for i in range(len(ranges))]
        prog_paths = [tmp / f"prog_{i:04d}.txt" for i in range(len(ranges))]
        prog_info = [(p, chunk_dur) for p in prog_paths]

        error_log = ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [
                executor.submit(self._encode_one, src, start, end, str(out), prog)
                for (start, end), out, prog in zip(ranges, out_paths, prog_paths)
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
