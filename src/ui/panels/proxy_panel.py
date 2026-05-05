import os
from pathlib import Path

import streamlit as st

from src.domain.models import SidebarConfig, VideoInfo
from src.services.parallel_proxy_generator import ParallelProxyGenerator
from src.services.proxy_service import ProxyService
from src.utils.formatters import fmt_size


def render_proxy_panel(
    proxy_service: ProxyService,
    parallel_proxy: ParallelProxyGenerator,
    config: SidebarConfig,
) -> None:
    st.caption("Crea una versión comprimida (<2 GB) del video para subir a Gemini Advanced.")

    video_path: str | None = st.session_state.video_path
    if video_path is None:
        st.info("Carga un video primero.")
        return

    use_parallel = st.toggle(
        "⚡ Generar en paralelo",
        value=True,
        help="Divide el video en chunks (uno por core) y los encodea simultáneamente. "
             "Si falla, desactívalo.",
    )

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
        _run_proxy(video_path, proxy_service, parallel_proxy, use_parallel, config)


def _run_proxy(
    src: str,
    proxy_service: ProxyService,
    parallel_proxy: ParallelProxyGenerator,
    use_parallel: bool,
    config: SidebarConfig,
) -> None:
    info: VideoInfo | None = st.session_state.video_info
    duration = info.duration if info else 0.0
    dst = str(Path(src).parent / (Path(src).stem + "_proxy.mp4"))

    mode = "paralelo" if use_parallel else "secuencial"
    status_ph = st.empty()
    bar = st.progress(0, text=f"Generando proxy ({mode})…")
    log_ph = st.empty()

    on_progress = lambda v: bar.progress(v, text=f"Generando proxy ({mode})… {int(v * 100)}%")
    status_ph.info(f"⏳ Generando proxy en {mode} ({config['n_workers']} núcleos)…")

    if use_parallel:
        with st.spinner("Encodando chunks en paralelo…"):
            ok, log = parallel_proxy.generate(src, dst, duration, config["n_workers"], on_progress)
    else:
        ok, log = proxy_service.generate(src, dst, progress_ph=log_ph, on_progress=on_progress, total_duration=duration)

    st.session_state.log_proxy = log
    bar.progress(1.0, text="Completado")

    if ok:
        st.session_state.proxy_path = dst
        status_ph.success(f"✅ Proxy generado: {fmt_size(dst)}")
    else:
        status_ph.error("❌ Error generando proxy. Ver log.")
    st.rerun()
