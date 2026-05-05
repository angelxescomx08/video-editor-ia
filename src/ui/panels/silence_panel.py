import streamlit as st

from src.domain.models import Segment, SidebarConfig
from src.services.silence_service import SilenceService
from src.ui.widgets.silence_results_widget import render_silence_results


def render_silence_panel(silence_service: SilenceService, config: SidebarConfig) -> None:
    st.caption(f"Umbral: {config['noise_pct']}% · Mínimo: {config['min_silence']}s · Buffer: {config['buffer']}s")

    video_path: str | None = st.session_state.video_path
    if video_path is None:
        st.info("Carga un video primero.")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        btn_detect = st.button("🎙️ Detectar Silencios", use_container_width=True)

    segs: list[Segment] | None = st.session_state.silence_segments
    if segs is not None:
        render_silence_results(segs, col2)

    if btn_detect:
        _run_detection(video_path, silence_service, config)


def _run_detection(video_path: str, silence_service: SilenceService, config: SidebarConfig) -> None:
    status_ph = st.empty()
    bar = st.progress(0, text="Analizando audio…")

    status_ph.info("⏳ Analizando audio… esto puede tardar 1-2 minutos.")
    try:
        segs = silence_service.detect(
            video_path,
            noise_threshold_pct=float(config["noise_pct"]),
            min_silence_dur=float(config["min_silence"]),
            buffer=float(config["buffer"]),
            progress_ph=status_ph,
            on_progress=lambda v: bar.progress(v, text=f"Analizando audio… {int(v * 100)}%"),
        )
        st.session_state.silence_segments = segs
        bar.progress(1.0, text="Completado")
        status_ph.success(f"✅ Detectados {len(segs)} segmentos a conservar.")
    except Exception as e:
        status_ph.error(f"❌ Error: {e}")
    st.rerun()
