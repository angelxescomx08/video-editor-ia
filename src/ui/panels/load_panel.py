import os

import streamlit as st

from src.services.video_probe_service import VideoProbeService
from src.ui.widgets.video_info_widget import render_video_info


def render_load_panel(probe_service: VideoProbeService) -> None:
    st.markdown('<div class="card"><div class="card-title">📁 Cargar Video</div>', unsafe_allow_html=True)
    st.caption("Pega la ruta completa a tu archivo de video. No hay límite de tamaño.")

    col_path, col_btn = st.columns([5, 1])
    with col_path:
        input_path: str = st.text_input(
            "Ruta del video",
            placeholder=r"C:\Users\TuUsuario\Videos\grabacion.mkv",
            label_visibility="collapsed",
        )
    with col_btn:
        btn_load = st.button("Cargar", use_container_width=True)

    if btn_load and input_path.strip():
        _handle_load(input_path.strip().strip('"'), probe_service)

    if st.session_state.video_path and st.session_state.video_info:
        render_video_info(st.session_state.video_path, st.session_state.video_info)

    st.markdown("</div>", unsafe_allow_html=True)


def _handle_load(video_path: str, probe_service: VideoProbeService) -> None:
    if not os.path.isfile(video_path):
        st.error(f"Archivo no encontrado: `{video_path}`")
        return
    if st.session_state.video_path == video_path:
        return
    st.session_state.update({
        "video_path": video_path, "proxy_path": None,
        "silence_segments": None, "gemini_cuts": None,
        "log_proxy": "", "log_export": "",
    })
    try:
        st.session_state.video_info = probe_service.probe(video_path)
    except Exception as e:
        st.session_state.video_info = None
        st.error(f"No se pudo analizar el video: {e}")
    st.rerun()
