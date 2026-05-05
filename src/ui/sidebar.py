import os

import streamlit as st

from src.domain.models import SidebarConfig

_CPU_COUNT: int = os.cpu_count() or 1


def render_sidebar() -> SidebarConfig:
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")
        st.markdown("---")

        st.markdown("### 🔇 Detección de Silencios")
        noise_pct: float = st.slider(
            "Umbral de volumen (%)", min_value=5, max_value=60, value=25, step=1,
            help="Nivel de volumen por debajo del cual se considera silencio.",
        )
        min_silence: float = st.slider(
            "Duración mínima de silencio (s)", 0.3, 3.0, 0.7, 0.05,
            help="Silencios más cortos que este valor se ignoran.",
        )
        buffer: float = st.slider(
            "Buffer de zona segura (s)", 0.0, 0.5, 0.2, 0.05,
            help="Margen de audio que se mantiene alrededor de cada silencio.",
        )

        st.markdown("---")
        st.markdown("### 📤 Exportación Final")
        reduce_quality: bool = st.checkbox("Reducir calidad final", value=False)
        if reduce_quality:
            crf_value: int = st.slider(
                "CRF (mayor = más comprimido)", 18, 35, 23, 1,
                help="18 = casi sin pérdida · 28 = buena compresión · 35 = muy comprimido.",
            )
            st.info(f"Exportando con CRF {crf_value}")
        else:
            crf_value = 18
            st.success("Exportando con CRF 18 (alta calidad)")

        st.markdown("---")
        st.markdown("### ⚡ Procesamiento Paralelo")
        n_workers: int = st.slider(
            "Núcleos CPU",
            min_value=1,
            max_value=_CPU_COUNT,
            value=_CPU_COUNT,
            step=1,
            help=f"Núcleos disponibles en este equipo: {_CPU_COUNT}. "
                 "Reduce este valor si notas que el sistema se queda sin recursos.",
        )
        st.caption(f"Usando {n_workers} de {_CPU_COUNT} núcleos disponibles.")

        st.markdown("---")
        st.caption("Video Editor IA v2.0\nFFmpeg + MoviePy + Streamlit")

    return SidebarConfig(
        noise_pct=noise_pct,
        min_silence=min_silence,
        buffer=buffer,
        reduce_quality=reduce_quality,
        crf_value=crf_value,
        n_workers=n_workers,
    )
