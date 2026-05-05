from src.domain.models import Segment


class FilterBuilder:
    def build(self, segments: list[Segment]) -> str:
        n = len(segments)
        video_trims = [
            f"[0:v]trim=start={s.start}:end={s.end},setpts=PTS-STARTPTS[v{i}]"
            for i, s in enumerate(segments)
        ]
        audio_trims = [
            f"[0:a]atrim=start={s.start}:end={s.end},asetpts=PTS-STARTPTS[a{i}]"
            for i, s in enumerate(segments)
        ]
        v_inputs = "".join(f"[v{i}]" for i in range(n))
        a_inputs = "".join(f"[a{i}]" for i in range(n))
        return (
            ";".join(video_trims + audio_trims)
            + f";{v_inputs}concat=n={n}:v=1:a=0[vout]"
            + f";{a_inputs}concat=n={n}:v=0:a=1[aout]"
        )
