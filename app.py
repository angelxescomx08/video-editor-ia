import streamlit as st

st.set_page_config(
    page_title="Video Editor IA",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.domain.models import SidebarConfig
from src.services.audio_analyzer import AudioAnalyzer
from src.services.export_service import ExportService
from src.services.ffmpeg_service import FFmpegService
from src.services.filter_builder import FilterBuilder
from src.services.parser_service import CutsParserService
from src.services.proxy_service import ProxyService
from src.services.segment_calculator import SegmentCalculator
from src.services.silence_detector import SilenceDetector
from src.services.silence_service import SilenceService
from src.services.video_probe_service import VideoProbeService
from src.ui.panels.export_panel import render_export_panel
from src.ui.panels.gemini_panel import render_gemini_panel
from src.ui.panels.load_panel import render_load_panel
from src.ui.panels.proxy_panel import render_proxy_panel
from src.ui.panels.silence_panel import render_silence_panel
from src.ui.sidebar import render_sidebar
from src.ui.styles import CSS


def _check_dependencies() -> None:
    errors: list[str] = []
    try:
        import ffmpeg  # noqa: F401
    except ImportError:
        errors.append("ffmpeg-python  →  pip install ffmpeg-python")
    try:
        from moviepy import VideoFileClip  # noqa: F401
    except ImportError:
        errors.append("moviepy  →  pip install moviepy")
    try:
        import numpy  # noqa: F401
    except ImportError:
        errors.append("numpy  →  pip install numpy")
    if errors:
        st.error("**Dependencias faltantes:**\n\n" + "\n".join(f"- `{e}`" for e in errors))
        st.stop()


def _init_session_state() -> None:
    defaults: dict = {
        "video_path": None, "proxy_path": None, "video_info": None,
        "silence_segments": None, "gemini_cuts": None,
        "log_proxy": "", "log_export": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _build_services() -> tuple[
    VideoProbeService, ProxyService, SilenceService,
    CutsParserService, SegmentCalculator, ExportService,
]:
    ffmpeg_service = FFmpegService()
    return (
        VideoProbeService(),
        ProxyService(ffmpeg_service),
        SilenceService(AudioAnalyzer(), SilenceDetector()),
        CutsParserService(),
        SegmentCalculator(),
        ExportService(ffmpeg_service, FilterBuilder()),
    )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    _check_dependencies()
    _init_session_state()

    probe_svc, proxy_svc, silence_svc, parser_svc, calculator, export_svc = _build_services()
    config: SidebarConfig = render_sidebar()

    st.markdown("# 🎬 Video Editor IA")
    st.markdown("Automatiza el flujo de edición para YouTube — silencios + muletillas con IA.")
    st.markdown("---")

    render_load_panel(probe_svc)

    tab_proxy, tab_silence, tab_gemini, tab_export = st.tabs([
        "⚡ Proxy para Gemini",
        "🔇 Silencios",
        "🤖 Cortes de Gemini",
        "🎬 Exportar",
    ])

    with tab_proxy:
        render_proxy_panel(proxy_svc)
    with tab_silence:
        render_silence_panel(silence_svc, config)
    with tab_gemini:
        render_gemini_panel(parser_svc)
    with tab_export:
        render_export_panel(export_svc, calculator, config)

    st.markdown("---")
    st.caption("Video Editor IA · FFmpeg + MoviePy + Streamlit · Solo uso local")


main()
