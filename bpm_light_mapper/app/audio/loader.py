from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf


def load_audio(file_path: str, target_sr: int | None = None) -> dict[str, Any]:
    path = Path(file_path)
    try:
        info = sf.info(file_path)
        raw, raw_sr = sf.read(file_path, always_2d=True)
        channels = raw.shape[1]
        duration = len(raw) / raw_sr if raw_sr else 0.0
        mono_source = raw.mean(axis=1).astype(np.float32)
        frame_count = len(raw)
        subtype = info.subtype
        audio_format = info.format
    except Exception:
        mono_source, raw_sr = librosa.load(file_path, sr=None, mono=True)
        channels = 1
        duration = len(mono_source) / raw_sr if raw_sr else 0.0
        frame_count = len(mono_source)
        subtype = "unknown"
        audio_format = path.suffix.lower().lstrip(".") or "unknown"

    if target_sr is not None and raw_sr != target_sr:
        mono = librosa.resample(mono_source, orig_sr=raw_sr, target_sr=target_sr)
        sample_rate = target_sr
    else:
        mono = mono_source
        sample_rate = raw_sr

    waveform = mono / max(np.max(np.abs(mono)), 1e-9)

    return {
        "file_path": str(path),
        "file_name": path.name,
        "duration": duration,
        "sample_rate": sample_rate,
        "original_sample_rate": raw_sr,
        "channels": channels,
        "waveform": waveform.astype(np.float32),
        "frames": frame_count,
        "subtype": subtype,
        "format": audio_format,
    }
