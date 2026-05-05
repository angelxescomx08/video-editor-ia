import streamlit as st

from src.domain.models import Segment, SidebarConfig, VideoInfo
from src.utils.formatters import fmt_duration


def render_export_summary(final_segs: list[Segment] | None, config: SidebarConfig) -> None:
    if not final_segs:
        st.warning("Detecta silencios (tab **Silencios**) o carga cortes de Gemini (tab **Gemini**) para poder exportar.")
        return

    info: VideoInfo | None = st.session_state.video_info
    total_dur = info.duration if info else 0.0
    total_kept = sum(s.duration for s in final_segs)
    removed_pct = 100 * (total_dur - total_kept) / max(total_dur, 1)
    crf = config["crf_value"]
    quality = f"CRF {crf} (comprimido)" if config["reduce_quality"] else "CRF 18 (alta calidad)"

    st.info(
        f"**{len(final_segs)} segmentos** · "
        f"Duración final: **{fmt_duration(total_kept)}** · "
        f"Reducción: **{removed_pct:.1f}%** | {quality}"
    )
