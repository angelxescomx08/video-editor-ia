from pathlib import Path


def read_avg_progress(progress_files: list[tuple[Path, float]]) -> float:
    """Promedia el avance (0-1) de todos los archivos de progreso de FFmpeg."""
    ratios = [_read_ratio(path, dur) for path, dur in progress_files]
    return sum(ratios) / len(ratios) if ratios else 0.0


def _read_ratio(path: Path, duration_s: float) -> float:
    if not path.exists() or duration_s <= 0:
        return 0.0
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in reversed(lines):
            if line.startswith("out_time="):
                h, m, s = line.split("=", 1)[1].strip().split(":")
                elapsed = int(h) * 3600 + int(m) * 60 + float(s)
                return min(elapsed / duration_s, 1.0)
    except Exception:
        pass
    return 0.0
