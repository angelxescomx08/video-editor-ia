from pathlib import Path

import streamlit as st

from src.domain.models import Segment, SidebarConfig
from src.services.export_service import ExportService
from src.services.segment_calculator import SegmentCalculator
from src.ui.widgets.export_summary_widget import render_export_summary
from src.utils.formatters import fmt_size


def render_export_panel(
    export_service: ExportService,
    calculator: SegmentCalculator,
    config: SidebarConfig,
) -> None:
    video_path: str | None = st.session_state.video_path
    if video_path is None:
        st.info("Carga un video primero.")
        return

    from src.domain.models import VideoInfo
    info: VideoInfo | None = st.session_state.video_info
    duration = info.duration if info else 0.0
    final_segs = calculator.compute_final(
        st.session_state.silence_segments,
        st.session_state.gemini_cuts,
        duration,
    )

    render_export_summary(final_segs, config)

    col1, col2 = st.columns([1, 3])
    with col1:
        btn_export = st.button(
            "🎬 Exportar Video", disabled=not final_segs,
            use_container_width=True, type="primary",
        )

    if st.session_state.log_export:
        with st.expander("Log FFmpeg", expanded=False):
            st.code(st.session_state.log_export, language=None)

    if btn_export and final_segs:
        _run_export(video_path, final_segs, export_service, config, col2)


def _run_export(
    src: str,
    segments: list[Segment],
    export_service: ExportService,
    config: SidebarConfig,
    result_col,
) -> None:
    crf = config["crf_value"]
    suffix = f"_editado_crf{crf}" if config["reduce_quality"] else "_editado_hq"
    dst = str(Path(src).parent / (Path(src).stem + suffix + ".mp4"))
    log_ph = st.empty()
    progress_ph = st.empty()
    progress_ph.info(f"⏳ Exportando {len(segments)} segmentos…")
    ok, log = export_service.export(src, dst, segments, config["reduce_quality"], crf, log_ph)
    st.session_state.log_export = log
    if ok:
        progress_ph.success(f"✅ Exportado: `{Path(dst).name}` · {fmt_size(dst)}")
        with result_col:
            st.download_button(
                "⬇️ Descargar Video Final", data=open(dst, "rb"),
                file_name=Path(dst).name, mime="video/mp4", use_container_width=True,
            )
    else:
        progress_ph.error("❌ Error durante la exportación. Ver log.")
    st.rerun()
