import streamlit as st

from src.domain.models import VideoInfo
from src.utils.formatters import fmt_duration, fmt_size


def render_video_info(video_path: str, info: VideoInfo) -> None:
    st.markdown(f"`{video_path}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Duración", fmt_duration(info.duration))
    c2.metric("Resolución", f"{info.width}×{info.height}")
    c3.metric("FPS", info.fps)
    c4.metric("Tamaño", fmt_size(video_path))
    st.markdown(
        f'<span class="pill">🎞 {info.vcodec}</span>'
        f'<span class="pill">🎵 {info.acodec}</span>',
        unsafe_allow_html=True,
    )
