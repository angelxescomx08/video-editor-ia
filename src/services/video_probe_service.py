import ffmpeg as ffmpeg_lib

from src.domain.models import VideoInfo


class VideoProbeService:
    def probe(self, path: str) -> VideoInfo:
        probe = ffmpeg_lib.probe(path)
        vs = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
        audio_s = next((s for s in probe["streams"] if s["codec_type"] == "audio"), {})
        fps_raw = vs.get("r_frame_rate", "30/1").split("/")
        fps = round(int(fps_raw[0]) / max(int(fps_raw[1]), 1), 2)
        return VideoInfo(
            duration=float(probe["format"].get("duration", 0)),
            size=int(probe["format"].get("size", 0)),
            width=int(vs.get("width", 0)),
            height=int(vs.get("height", 0)),
            fps=fps,
            vcodec=vs.get("codec_name", "—"),
            acodec=audio_s.get("codec_name", "—"),
        )
