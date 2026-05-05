import os
import tkinter as tk
from tkinter import filedialog

import streamlit as st

from src.services.video_probe_service import VideoProbeService
from src.ui.widgets.video_info_widget import render_video_info

_VIDEO_FILETYPES = [
    ("Videos", "*.mp4 *.avi *.mov *.mkv *.webm *.m4v *.flv *.wmv"),
    ("Todos los archivos", "*.*"),
]


def render_load_panel(probe_service: VideoProbeService) -> None:
    st.markdown('<div class="card"><div class="card-title">📁 Cargar Video</div>', unsafe_allow_html=True)
    st.caption("Selecciona el archivo de video. No hay límite de tamaño — la app trabaja directamente con el archivo en disco.")

    col_picker, col_path, col_btn = st.columns([1, 4, 1])
    with col_picker:
        btn_browse = st.button("📂 Explorar", use_container_width=True)
    with col_path:
        input_path: str = st.text_input(
            "Ruta del video",
            value=st.session_state.get("_input_path", ""),
            placeholder=r"C:\Users\TuUsuario\Videos\grabacion.mkv",
            label_visibility="collapsed",
        )
    with col_btn:
        btn_load = st.button("Cargar", use_container_width=True)

    if btn_browse:
        selected = _open_file_dialog()
        if selected:
            st.session_state["_input_path"] = selected
            st.rerun()

    path_to_load = input_path.strip().strip('"')
    if btn_load and path_to_load:
        _handle_load(path_to_load, probe_service)

    if st.session_state.video_path and st.session_state.video_info:
        render_video_info(st.session_state.video_path, st.session_state.video_info)

    st.markdown("</div>", unsafe_allow_html=True)


def _open_file_dialog() -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Seleccionar video",
        filetypes=_VIDEO_FILETYPES,
    )
    root.destroy()
    return path or None


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
