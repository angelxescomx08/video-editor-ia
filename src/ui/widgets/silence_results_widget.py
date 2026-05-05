import streamlit as st

from src.domain.models import Segment, VideoInfo
from src.utils.formatters import fmt_duration


def render_silence_results(segs: list[Segment], result_col) -> None:
    info: VideoInfo | None = st.session_state.video_info
    total_kept = sum(s.duration for s in segs)
    total_dur = info.duration if info else 0.0
    removed = total_dur - total_kept

    with result_col:
        st.success(
            f"✅ {len(segs)} segmentos · "
            f"Conservado: {fmt_duration(total_kept)} · "
            f"Removido: {fmt_duration(removed)} ({100 * removed / max(total_dur, 1):.1f}%)"
        )

    with st.expander(f"Ver segmentos ({len(segs)})", expanded=False):
        st.dataframe(
            [{"#": i + 1, "Inicio": fmt_duration(s.start), "Fin": fmt_duration(s.end), "Duración": f"{s.duration:.2f}s"}
             for i, s in enumerate(segs)],
            use_container_width=True,
            hide_index=True,
        )
