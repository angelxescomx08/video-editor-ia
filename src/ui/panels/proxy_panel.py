import os
from pathlib import Path

import streamlit as st

from src.services.proxy_service import ProxyService
from src.utils.formatters import fmt_size


def render_proxy_panel(proxy_service: ProxyService) -> None:
    st.caption("Crea una versión comprimida (<2 GB) del video para subir a Gemini Advanced.")

    video_path: str | None = st.session_state.video_path
    if video_path is None:
        st.info("Carga un video primero.")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        btn_proxy = st.button("🚀 Generar Proxy", use_container_width=True)

    proxy_path: str | None = st.session_state.proxy_path
    if proxy_path and os.path.exists(proxy_path):
        with col2:
            st.success(f"✅ Proxy listo: `{Path(proxy_path).name}` · {fmt_size(proxy_path)}")
        st.download_button(
            "⬇️ Descargar Proxy", data=open(proxy_path, "rb"),
            file_name=Path(proxy_path).name, mime="video/mp4", use_container_width=True,
        )

    if st.session_state.log_proxy:
        with st.expander("Log FFmpeg", expanded=False):
            st.code(st.session_state.log_proxy, language=None)

    if btn_proxy:
        _run_proxy(video_path, proxy_service)


def _run_proxy(src: str, proxy_service: ProxyService) -> None:
    dst = str(Path(src).parent / (Path(src).stem + "_proxy.mp4"))
    log_ph = st.empty()
    progress_ph = st.empty()
    progress_ph.info("⏳ Generando proxy… (puede tomar varios minutos)")
    ok, log = proxy_service.generate(src, dst, log_ph)
    st.session_state.log_proxy = log
    if ok:
        st.session_state.proxy_path = dst
        progress_ph.success(f"✅ Proxy generado: {fmt_size(dst)}")
    else:
        progress_ph.error("❌ Error generando proxy. Ver log.")
    st.rerun()
