from src.config import EXPORT_AUDIO_BITRATE, EXPORT_HQ_CRF, EXPORT_HQ_PRESET
from src.domain.models import Segment
from src.services.ffmpeg_service import FFmpegService
from src.services.filter_builder import FilterBuilder


class ExportService:
    def __init__(self, ffmpeg_service: FFmpegService, filter_builder: FilterBuilder) -> None:
        self._ffmpeg = ffmpeg_service
        self._filter = filter_builder

    def export(
        self,
        src: str,
        dst: str,
        segments: list[Segment],
        reduce_quality: bool,
        crf_value: int,
        progress_ph=None,
    ) -> tuple[bool, str]:
        if not segments:
            return False, "No hay segmentos para exportar."

        vcodec = (
            ["-c:v", "libx264", "-crf", str(crf_value), "-preset", "faster"]
            if reduce_quality
            else ["-c:v", "libx264", "-crf", str(EXPORT_HQ_CRF), "-preset", EXPORT_HQ_PRESET]
        )
        args = [
            "-i", src,
            "-filter_complex", self._filter.build(segments),
            "-map", "[vout]", "-map", "[aout]",
            *vcodec,
            "-c:a", "aac", "-b:a", EXPORT_AUDIO_BITRATE,
            "-movflags", "+faststart",
            dst,
        ]
        return self._ffmpeg.run_command(args, progress_ph)
