from pathlib import Path

import streamlit as st

from src.domain.models import Segment, SidebarConfig, VideoInfo
from src.services.export_service import ExportService
from src.services.parallel_exporter import ParallelExporter
from src.services.segment_calculator import SegmentCalculator
from src.ui.widgets.export_summary_widget import render_export_summary
from src.utils.formatters import fmt_size


def render_export_panel(
    export_service: ExportService,
    parallel_exporter: ParallelExporter,
    calculator: SegmentCalculator,
    config: SidebarConfig,
) -> None:
    video_path: str | None = st.session_state.video_path
    if video_path is None:
        st.info("Carga un video primero.")
        return

    info: VideoInfo | None = st.session_state.video_info
    duration = info.duration if info else 0.0
    final_segs = calculator.compute_final(
        st.session_state.silence_segments,
        st.session_state.gemini_cuts,
        duration,
    )

    render_export_summary(final_segs, config)

    use_parallel = st.toggle(
        "⚡ Exportar en paralelo",
        value=True,
        help="Encodea cada segmento simultáneamente usando todos los núcleos del CPU. "
             "Más rápido con muchos segmentos. Si falla, desactívalo.",
    )

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
        _run_export(
            video_path, final_segs, export_service, parallel_exporter,
            config, duration, use_parallel, col2,
        )


def _run_export(
    src: str,
    segments: list[Segment],
    export_service: ExportService,
    parallel_exporter: ParallelExporter,
    config: SidebarConfig,
    total_duration: float,
    use_parallel: bool,
    result_col,
) -> None:
    crf = config["crf_value"]
    suffix = f"_editado_crf{crf}" if config["reduce_quality"] else "_editado_hq"
    dst = str(Path(src).parent / (Path(src).stem + suffix + ".mp4"))

    mode = "paralelo" if use_parallel else "secuencial"
    status_ph = st.empty()
    bar = st.progress(0, text=f"Exportando video ({mode})…")
    log_ph = st.empty()

    status_ph.info(f"⏳ Exportando {len(segments)} segmentos en {mode}…")

    on_progress = lambda v: bar.progress(v, text=f"Exportando ({mode})… {int(v * 100)}%")

    if use_parallel:
        with st.spinner("Encodando segmentos en paralelo…"):
            ok, log = parallel_exporter.export(
                src, dst, segments,
                reduce_quality=config["reduce_quality"],
                crf_value=crf,
                n_workers=config["n_workers"],
                on_progress=on_progress,
            )
    else:
        ok, log = export_service.export(
            src, dst, segments,
            reduce_quality=config["reduce_quality"],
            crf_value=crf,
            progress_ph=log_ph,
            on_progress=on_progress,
            total_duration=total_duration,
        )

    st.session_state.log_export = log
    bar.progress(1.0, text="Completado")

    if ok:
        status_ph.success(f"✅ Exportado: `{Path(dst).name}` · {fmt_size(dst)}")
        with result_col:
            st.download_button(
                "⬇️ Descargar Video Final", data=open(dst, "rb"),
                file_name=Path(dst).name, mime="video/mp4", use_container_width=True,
            )
    else:
        status_ph.error("❌ Error durante la exportación. Ver log.")
    st.rerun()
