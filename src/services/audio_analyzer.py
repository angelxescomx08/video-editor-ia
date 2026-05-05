import numpy as np
from moviepy import VideoFileClip

from src.config import AUDIO_CHUNK_MS, AUDIO_SAMPLE_RATE


class AudioAnalyzer:
    """Extrae audio de un video y devuelve la lista de RMS por chunk."""

    def extract_rms(
        self,
        video_path: str,
        progress_ph=None,
    ) -> tuple[list[float], float, float]:
        """Devuelve (rms_list, chunk_dur, duration). rms_list vacía si no hay audio."""
        if progress_ph:
            progress_ph.info("Cargando clip y extrayendo audio…")

        clip = VideoFileClip(video_path)
        duration = clip.duration

        if clip.audio is None:
            clip.close()
            return [], 0.0, duration

        chunk_size = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)

        if progress_ph:
            progress_ph.info("Analizando niveles de audio…")

        try:
            raw = clip.audio.to_soundarray(fps=AUDIO_SAMPLE_RATE, nbytes=2)
        except Exception:
            clip.close()
            return [], 0.0, duration
        finally:
            clip.close()

        audio = raw.mean(axis=1) if raw.ndim > 1 else raw
        max_amp = np.abs(audio).max()
        if max_amp == 0:
            return [], 0.0, duration

        norm = np.abs(audio) / max_amp
        n = len(norm) // chunk_size
        rms_list = [
            float(np.sqrt(np.mean(norm[i * chunk_size:(i + 1) * chunk_size] ** 2)))
            for i in range(n)
        ]
        return rms_list, chunk_size / AUDIO_SAMPLE_RATE, duration
