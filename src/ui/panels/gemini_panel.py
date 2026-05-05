import json

import streamlit as st

from src.domain.models import Segment
from src.services.parser_service import CutsParserService


def render_gemini_panel(parser_service: CutsParserService) -> None:
    st.caption(
        'Pega el JSON que Gemini generó con timestamps de muletillas. '
        'Formato: `[{"start": 10.5, "end": 12.3}, ...]`'
    )

    gemini_raw: str = st.text_area(
        "JSON de Gemini",
        height=160,
        placeholder='[\n  {"start": 10.5, "end": 12.3},\n  {"start": 45.0, "end": 47.2}\n]',
        help="También acepta HH:MM:SS, MM:SS o float. Claves en español (inicio/fin) también funcionan.",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        btn_apply = st.button(
            "🔗 Aplicar Cortes",
            disabled=not gemini_raw.strip(),
            use_container_width=True,
        )

    cuts: list[Segment] | None = st.session_state.gemini_cuts
    if cuts is not None:
        with col2:
            st.info(f"✅ {len(cuts)} cortes de Gemini cargados. Ve al tab **Exportar** para procesar.")

    if btn_apply and gemini_raw.strip():
        _apply_cuts(gemini_raw.strip(), parser_service)


def _apply_cuts(raw: str, parser_service: CutsParserService) -> None:
    try:
        cuts = parser_service.parse(raw)
        st.session_state.gemini_cuts = cuts
        st.rerun()
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON inválido: {e}")
    except Exception as e:
        st.error(f"❌ Error procesando JSON: {e}")
