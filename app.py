import streamlit as st
import json
import os
import tempfile
import threading
import time
import subprocess
from pathlib import Path

# ─── Page config must be first ───────────────────────────────────────────────
st.set_page_config(
    page_title="Video Editor IA",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Dark mode CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base dark theme */
  .stApp { background-color: #0e1117; color: #fafafa; }
  .stSidebar { background-color: #161b22; }
  .stSidebar .stMarkdown { color: #c9d1d9; }

  /* Cards */
  .card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #58a6ff;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* Progress / status */
  .status-idle    { color: #8b949e; }
  .status-running { color: #f0c040; }
  .status-done    { color: #3fb950; }
  .status-error   { color: #f85149; }

  /* Metric pills */
  .pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
    margin: 2px;
  }

  /* Buttons */
  .stButton > button {
    background: #238636;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: background 0.2s;
  }
  .stButton > button:hover { background: #2ea043; }

  /* File uploader */
  .stFileUploader { border: 2px dashed #30363d; border-radius: 10px; }

  /* Text area */
  .stTextArea textarea {
    background: #0d1117;
    border: 1px solid #30363d;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
  }

  /* Divider */
  hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)


# ─── Imports with graceful errors ────────────────────────────────────────────
_import_errors = []
try:
    import ffmpeg  # ffmpeg-python
except ImportError:
    _import_errors.append("ffmpeg-python  →  pip install ffmpeg-python")

try:
    from moviepy import VideoFileClip, concatenate_videoclips
    _moviepy_ok = True
except ImportError:
    _import_errors.append("moviepy  →  pip install moviepy")
    _moviepy_ok = False

try:
    import numpy as np
    _numpy_ok = True
except ImportError:
    _import_errors.append("numpy  →  pip install numpy")
    _numpy_ok = False

if _import_errors:
    st.error("**Dependencias faltantes:**\n\n" + "\n".join(f"- `{e}`" for e in _import_errors))
    st.stop()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
    except Exception:
        return "—"


def fmt_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run_ffmpeg_cmd(args: list, progress_placeholder=None) -> tuple[bool, str]:
    """Run an ffmpeg command list and stream stderr to a placeholder."""
    cmd = ["ffmpeg", "-y"] + args
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        log_lines = []
        for line in proc.stdout:
            line = line.rstrip()
            log_lines.append(line)
            if progress_placeholder and ("time=" in line or "frame=" in line):
                progress_placeholder.code(line, language=None)
        proc.wait()
        return proc.returncode == 0, "\n".join(log_lines[-20:])
    except FileNotFoundError:
        return False, "FFmpeg no encontrado. Instálalo y asegúrate de que esté en el PATH."


def probe_video(path: str) -> dict:
    try:
        probe = ffmpeg.probe(path)
        vs = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
        audio_s = next((s for s in probe["streams"] if s["codec_type"] == "audio"), {})
        dur = float(probe["format"].get("duration", 0))
        size = int(probe["format"].get("size", 0))
        fps_raw = vs.get("r_frame_rate", "30/1").split("/")
        fps = round(int(fps_raw[0]) / max(int(fps_raw[1]), 1), 2)
        return {
            "duration": dur,
            "size": size,
            "width": int(vs.get("width", 0)),
            "height": int(vs.get("height", 0)),
            "fps": fps,
            "vcodec": vs.get("codec_name", "—"),
            "acodec": audio_s.get("codec_name", "—"),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Core processing functions ────────────────────────────────────────────────

def generate_proxy(src: str, dst: str, progress_ph) -> tuple[bool, str]:
    """Create a compressed proxy file using FFmpeg."""
    args = [
        "-i", src,
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "faster",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        "-movflags", "+faststart",
        dst,
    ]
    return run_ffmpeg_cmd(args, progress_ph)


def detect_silences(
    video_path: str,
    noise_threshold_pct: float = 25.0,
    min_silence_dur: float = 0.7,
    buffer: float = 0.2,
    progress_ph=None,
) -> list[dict]:
    """
    Detect silent segments using MoviePy audio analysis.
    Returns list of {start, end} dicts representing segments TO KEEP.
    """
    if progress_ph:
        progress_ph.info("Cargando clip y extrayendo audio…")

    clip = VideoFileClip(video_path)
    duration = clip.duration

    if clip.audio is None:
        clip.close()
        return [{"start": 0, "end": duration}]

    # Sample audio at 44100 Hz → analyse RMS per chunk
    fps_audio = 44100
    chunk_size = int(fps_audio * 0.05)  # 50 ms chunks

    if progress_ph:
        progress_ph.info("Analizando niveles de audio…")

    try:
        audio_array = clip.audio.to_soundarray(fps=fps_audio, nbytes=2)
    except Exception:
        clip.close()
        return [{"start": 0, "end": duration}]

    if audio_array.ndim > 1:
        audio_array = audio_array.mean(axis=1)

    # Normalise
    max_amp = np.abs(audio_array).max()
    if max_amp == 0:
        clip.close()
        return [{"start": 0, "end": duration}]

    audio_norm = np.abs(audio_array) / max_amp
    threshold = noise_threshold_pct / 100.0

    # Build per-chunk loudness
    n_chunks = len(audio_norm) // chunk_size
    rms_list = []
    for i in range(n_chunks):
        chunk = audio_norm[i * chunk_size: (i + 1) * chunk_size]
        rms_list.append(float(np.sqrt(np.mean(chunk ** 2))))

    chunk_dur = chunk_size / fps_audio

    # Mark silent chunks
    silent_mask = [r < threshold for r in rms_list]

    # Group consecutive silent chunks into silence intervals
    silent_intervals: list[tuple[float, float]] = []
    in_silence = False
    s_start = 0.0
    for i, is_silent in enumerate(silent_mask):
        t = i * chunk_dur
        if is_silent and not in_silence:
            in_silence = True
            s_start = t
        elif not is_silent and in_silence:
            in_silence = False
            s_end = t
            if s_end - s_start >= min_silence_dur:
                silent_intervals.append((s_start, s_end))
    if in_silence:
        s_end = n_chunks * chunk_dur
        if s_end - s_start >= min_silence_dur:
            silent_intervals.append((s_start, s_end))

    clip.close()

    # Convert silences → keep segments (with buffer)
    keep_segments: list[dict] = []
    prev_end = 0.0
    for (s_start, s_end) in silent_intervals:
        seg_start = prev_end
        seg_end = s_start + buffer
        seg_end = min(seg_end, s_end - buffer)
        if seg_end > seg_start + 0.05:
            keep_segments.append({"start": round(seg_start, 3), "end": round(seg_end, 3)})
        prev_end = max(s_end - buffer, seg_end)

    # Add final segment
    if prev_end < duration - 0.1:
        keep_segments.append({"start": round(prev_end, 3), "end": round(duration, 3)})

    return keep_segments if keep_segments else [{"start": 0, "end": duration}]


def parse_gemini_json(raw: str) -> list[dict]:
    """
    Parse Gemini JSON. Expected: list of {start, end} objects (seconds as float or "MM:SS" / "HH:MM:SS").
    Returns list of segments TO REMOVE.
    """
    data = json.loads(raw)
    if isinstance(data, dict) and "segments" in data:
        data = data["segments"]
    if isinstance(data, dict) and "cuts" in data:
        data = data["cuts"]

    def parse_ts(v):
        if isinstance(v, (int, float)):
            return float(v)
        parts = str(v).split(":")
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return float(parts[0])

    result = []
    for item in data:
        if isinstance(item, dict):
            start = parse_ts(item.get("start", item.get("inicio", 0)))
            end = parse_ts(item.get("end", item.get("fin", 0)))
            result.append({"start": start, "end": end})
    return result


def merge_cut_segments(
    keep_segments: list[dict],
    gemini_cuts: list[dict],
    duration: float,
) -> list[dict]:
    """
    Subtract gemini_cuts from keep_segments.
    Both lists use seconds.
    """
    if not gemini_cuts:
        return keep_segments

    result = []
    for seg in keep_segments:
        remaining = [(seg["start"], seg["end"])]
        for cut in gemini_cuts:
            new_remaining = []
            for (a, b) in remaining:
                # No overlap
                if cut["end"] <= a or cut["start"] >= b:
                    new_remaining.append((a, b))
                else:
                    if cut["start"] > a:
                        new_remaining.append((a, cut["start"]))
                    if cut["end"] < b:
                        new_remaining.append((cut["end"], b))
            remaining = new_remaining
        for (a, b) in remaining:
            if b - a > 0.05:
                result.append({"start": round(a, 3), "end": round(b, 3)})
    return result


def export_video(
    src: str,
    dst: str,
    segments: list[dict],
    reduce_quality: bool,
    crf_value: int,
    progress_ph,
) -> tuple[bool, str]:
    """
    Use FFmpeg concat demuxer to join segments without re-encoding video (stream copy).
    If reduce_quality=True, re-encode with given crf.
    """
    if not segments:
        return False, "No hay segmentos para exportar."

    # Write a temporary concat list
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        concat_path = f.name

    # Build filter_complex trim approach for accurate cuts
    # Use select+aselect filter for per-segment trimming
    filter_parts = []
    audio_parts = []
    n = len(segments)

    for i, seg in enumerate(segments):
        filter_parts.append(
            f"[0:v]trim=start={seg['start']}:end={seg['end']},setpts=PTS-STARTPTS[v{i}]"
        )
        audio_parts.append(
            f"[0:a]atrim=start={seg['start']}:end={seg['end']},asetpts=PTS-STARTPTS[a{i}]"
        )

    v_inputs = "".join(f"[v{i}]" for i in range(n))
    a_inputs = "".join(f"[a{i}]" for i in range(n))
    concat_filter = (
        ";".join(filter_parts + audio_parts)
        + f";{v_inputs}concat=n={n}:v=1:a=0[vout]"
        + f";{a_inputs}concat=n={n}:v=0:a=1[aout]"
    )

    if reduce_quality:
        vcodec_args = ["-c:v", "libx264", "-crf", str(crf_value), "-preset", "faster"]
    else:
        vcodec_args = ["-c:v", "libx264", "-crf", "18", "-preset", "slow"]

    args = [
        "-i", src,
        "-filter_complex", concat_filter,
        "-map", "[vout]",
        "-map", "[aout]",
    ] + vcodec_args + [
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        dst,
    ]

    ok, log = run_ffmpeg_cmd(args, progress_ph)
    try:
        os.unlink(concat_path)
    except Exception:
        pass
    return ok, log


# ─── Session state init ───────────────────────────────────────────────────────
defaults = {
    "video_path": None,
    "proxy_path": None,
    "video_info": None,
    "silence_segments": None,
    "gemini_cuts": None,
    "final_segments": None,
    "log_proxy": "",
    "log_silence": "",
    "log_export": "",
    "stage": "idle",  # idle | proxy | silence | export
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")

    st.markdown("### 🔇 Detección de Silencios")
    noise_pct = st.slider(
        "Umbral de volumen (%)", min_value=5, max_value=60, value=25, step=1,
        help="Nivel de volumen por debajo del cual se considera silencio.",
    )
    min_silence = st.slider(
        "Duración mínima de silencio (s)", 0.3, 3.0, 0.7, 0.05,
        help="Silencios más cortos que este valor se ignoran.",
    )
    buffer_s = st.slider(
        "Buffer de zona segura (s)", 0.0, 0.5, 0.2, 0.05,
        help="Margen de audio que se mantiene alrededor de cada silencio para evitar cortes abruptos.",
    )

    st.markdown("---")
    st.markdown("### 📤 Exportación Final")
    reduce_quality = st.checkbox("Reducir calidad final", value=False)
    if reduce_quality:
        crf_value = st.slider(
            "CRF (mayor = más comprimido)", 18, 35, 23, 1,
            help="18 = casi sin pérdida, 28 = buena compresión, 35 = muy comprimido.",
        )
        st.info(f"Exportando con CRF {crf_value} (~compresión media)")
    else:
        crf_value = 18
        st.success("Exportando con CRF 18 (alta calidad)")

    st.markdown("---")
    st.markdown("### ℹ️ Acerca de")
    st.caption("Video Editor IA v1.0\nPowered by FFmpeg + MoviePy")


# ─── Main UI ──────────────────────────────────────────────────────────────────
st.markdown("# 🎬 Video Editor IA")
st.markdown("Automatiza el flujo de edición para YouTube — silencios + muletillas con IA.")
st.markdown("---")

# ── Step 1: Seleccionar video por ruta ────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">📁 Paso 1 · Seleccionar Video</div>', unsafe_allow_html=True)

st.caption("Pega la ruta completa a tu archivo de video. No hay límite de tamaño — la app trabaja directamente con el archivo en disco.")

col_path, col_load = st.columns([5, 1])
with col_path:
    input_path = st.text_input(
        "Ruta del video",
        placeholder=r"C:\Users\TuUsuario\Videos\OBS\grabacion.mkv",
        label_visibility="collapsed",
    )
with col_load:
    btn_load = st.button("Cargar", use_container_width=True)

if btn_load and input_path.strip():
    video_path = input_path.strip().strip('"')  # quita comillas si el usuario las pegó
    if not os.path.isfile(video_path):
        st.error(f"Archivo no encontrado: `{video_path}`")
    elif st.session_state.video_path != video_path:
        st.session_state.video_path = video_path
        st.session_state.proxy_path = None
        st.session_state.silence_segments = None
        st.session_state.final_segments = None
        st.session_state.gemini_cuts = None
        info = probe_video(video_path)
        st.session_state.video_info = info
        st.rerun()

if st.session_state.video_path:
    info = st.session_state.video_info or {}
    st.markdown(f"`{st.session_state.video_path}`")
    if "error" not in info:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Duración", fmt_duration(info.get("duration", 0)))
        c2.metric("Resolución", f"{info.get('width')}×{info.get('height')}")
        c3.metric("FPS", info.get("fps"))
        c4.metric("Tamaño", fmt_size(st.session_state.video_path))
        st.markdown(
            f'<span class="pill">🎞 {info.get("vcodec","—")}</span>'
            f'<span class="pill">🎵 {info.get("acodec","—")}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"No se pudo analizar el video: {info['error']}")

st.markdown("</div>", unsafe_allow_html=True)


# ── Step 2: Proxy ──────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">⚡ Paso 2 · Generar Proxy para Gemini</div>', unsafe_allow_html=True)

st.caption("Crea una versión comprimida (<2 GB) del video para subir a Gemini Advanced. CRF 28, preset faster, audio MP3 128k.")

col_proxy1, col_proxy2 = st.columns([1, 3])
with col_proxy1:
    btn_proxy = st.button(
        "🚀 Preparar para Gemini",
        disabled=(st.session_state.video_path is None),
        use_container_width=True,
    )

if st.session_state.proxy_path and os.path.exists(st.session_state.proxy_path):
    with col_proxy2:
        st.success(f"✅ Proxy listo: `{Path(st.session_state.proxy_path).name}` · {fmt_size(st.session_state.proxy_path)}")
        st.download_button(
            "⬇️ Descargar Proxy",
            data=open(st.session_state.proxy_path, "rb"),
            file_name=Path(st.session_state.proxy_path).name,
            mime="video/mp4",
            use_container_width=True,
        )

proxy_log_ph = st.empty()
if st.session_state.log_proxy:
    with st.expander("Log FFmpeg (proxy)", expanded=False):
        st.code(st.session_state.log_proxy, language=None)

if btn_proxy and st.session_state.video_path:
    src = st.session_state.video_path
    dst = str(Path(src).parent / (Path(src).stem + "_proxy.mp4"))
    st.session_state.stage = "proxy"
    progress_ph = st.empty()
    progress_ph.info("⏳ Generando proxy… (puede tomar varios minutos)")
    ok, log = generate_proxy(src, dst, proxy_log_ph)
    st.session_state.log_proxy = log
    if ok:
        st.session_state.proxy_path = dst
        progress_ph.success(f"✅ Proxy generado: {fmt_size(dst)}")
    else:
        progress_ph.error("❌ Error generando proxy. Ver log.")
    st.session_state.stage = "idle"
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ── Step 3: Silence Detection ──────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">🔇 Paso 3 · Detectar Silencios</div>', unsafe_allow_html=True)

st.caption(f"Umbral: {noise_pct}% · Silencio mínimo: {min_silence}s · Buffer: {buffer_s}s")

col_s1, col_s2 = st.columns([1, 3])
with col_s1:
    btn_silence = st.button(
        "🎙️ Detectar Silencios",
        disabled=(st.session_state.video_path is None),
        use_container_width=True,
    )

silence_status_ph = st.empty()

if st.session_state.silence_segments is not None:
    segs = st.session_state.silence_segments
    total_kept = sum(s["end"] - s["start"] for s in segs)
    info = st.session_state.video_info or {}
    total_dur = info.get("duration", 0)
    removed = total_dur - total_kept
    with col_s2:
        st.success(
            f"✅ {len(segs)} segmentos · "
            f"Conservado: {fmt_duration(total_kept)} · "
            f"Removido: {fmt_duration(removed)} ({100*removed/max(total_dur,1):.1f}%)"
        )
    with st.expander(f"Ver segmentos detectados ({len(segs)})", expanded=False):
        seg_data = [
            {"#": i+1, "Inicio": fmt_duration(s["start"]), "Fin": fmt_duration(s["end"]),
             "Duración": f"{s['end']-s['start']:.2f}s"}
            for i, s in enumerate(segs)
        ]
        st.dataframe(seg_data, use_container_width=True, hide_index=True)

if btn_silence and st.session_state.video_path:
    st.session_state.stage = "silence"
    progress_ph = st.empty()
    progress_ph.info("⏳ Analizando audio… esto puede tardar 1-2 minutos.")
    try:
        segs = detect_silences(
            st.session_state.video_path,
            noise_threshold_pct=float(noise_pct),
            min_silence_dur=float(min_silence),
            buffer=float(buffer_s),
            progress_ph=progress_ph,
        )
        st.session_state.silence_segments = segs
        st.session_state.final_segments = segs  # default before gemini
        progress_ph.success(f"✅ Detectados {len(segs)} segmentos a conservar.")
    except Exception as e:
        progress_ph.error(f"❌ Error: {e}")
    st.session_state.stage = "idle"
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ── Step 4: Gemini JSON ────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">🤖 Paso 4 · Integrar Cortes de Gemini (Opcional)</div>', unsafe_allow_html=True)

st.caption(
    "Pega el JSON que Gemini generó con timestamps de muletillas o errores. "
    "Formato esperado: `[{\"start\": 10.5, \"end\": 12.3}, ...]`"
)

gemini_raw = st.text_area(
    "JSON de Gemini",
    height=160,
    placeholder='[\n  {"start": 10.5, "end": 12.3},\n  {"start": 45.0, "end": 47.2}\n]',
    help="También acepta formato HH:MM:SS, MM:SS o segundos en float.",
)

col_g1, col_g2 = st.columns([1, 3])
with col_g1:
    btn_gemini = st.button(
        "🔗 Combinar Cortes",
        disabled=(st.session_state.silence_segments is None or not gemini_raw.strip()),
        use_container_width=True,
    )

if st.session_state.gemini_cuts is not None:
    with col_g2:
        st.info(f"✅ {len(st.session_state.gemini_cuts)} cortes de Gemini aplicados.")

if btn_gemini and gemini_raw.strip():
    try:
        cuts = parse_gemini_json(gemini_raw.strip())
        st.session_state.gemini_cuts = cuts
        info = st.session_state.video_info or {}
        combined = merge_cut_segments(
            st.session_state.silence_segments,
            cuts,
            info.get("duration", 9999),
        )
        st.session_state.final_segments = combined
        st.success(f"✅ Combinados {len(cuts)} cortes de Gemini → {len(combined)} segmentos finales.")
        st.rerun()
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON inválido: {e}")
    except Exception as e:
        st.error(f"❌ Error procesando JSON: {e}")

st.markdown("</div>", unsafe_allow_html=True)


# ── Step 5: Export ─────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">🎯 Paso 5 · Exportar Video Final</div>', unsafe_allow_html=True)

final_segs = st.session_state.final_segments or st.session_state.silence_segments

if final_segs:
    total_kept = sum(s["end"] - s["start"] for s in final_segs)
    info_v = st.session_state.video_info or {}
    total_dur = info_v.get("duration", 0)
    removed_pct = 100 * (total_dur - total_kept) / max(total_dur, 1)
    st.info(
        f"**{len(final_segs)} segmentos** · "
        f"Duración final estimada: **{fmt_duration(total_kept)}** · "
        f"Reducción: **{removed_pct:.1f}%**  |  "
        f"Calidad: {'CRF ' + str(crf_value) + ' (comprimido)' if reduce_quality else 'CRF 18 (alta calidad)'}"
    )
else:
    st.warning("Primero detecta los silencios (Paso 3) para poder exportar.")

col_e1, col_e2 = st.columns([1, 3])
with col_e1:
    btn_export = st.button(
        "🎬 Exportar Video",
        disabled=(
            st.session_state.video_path is None
            or final_segs is None
        ),
        use_container_width=True,
        type="primary",
    )

export_log_ph = st.empty()
if st.session_state.log_export:
    with st.expander("Log FFmpeg (export)", expanded=False):
        st.code(st.session_state.log_export, language=None)

if btn_export and st.session_state.video_path and final_segs:
    src = st.session_state.video_path
    suffix = f"_editado_crf{crf_value}" if reduce_quality else "_editado_hq"
    dst = str(Path(src).parent / (Path(src).stem + suffix + ".mp4"))
    st.session_state.stage = "export"
    progress_ph = st.empty()
    progress_ph.info(f"⏳ Exportando {len(final_segs)} segmentos… esto puede tardar varios minutos.")
    ok, log = export_video(
        src, dst, final_segs,
        reduce_quality=reduce_quality,
        crf_value=crf_value,
        progress_ph=export_log_ph,
    )
    st.session_state.log_export = log
    if ok:
        progress_ph.success(f"✅ Video exportado: `{Path(dst).name}` · {fmt_size(dst)}")
        st.session_state.export_path = dst
        with col_e2:
            st.download_button(
                "⬇️ Descargar Video Final",
                data=open(dst, "rb"),
                file_name=Path(dst).name,
                mime="video/mp4",
                use_container_width=True,
            )
    else:
        progress_ph.error("❌ Error durante la exportación. Ver log.")
    st.session_state.stage = "idle"
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Video Editor IA · FFmpeg + MoviePy + Streamlit · Solo uso local")
