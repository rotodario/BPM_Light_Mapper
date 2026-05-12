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


def load_audio_preview(file_path: str, max_points: int = 5000) -> dict[str, Any]:
    path = Path(file_path)
    info = sf.info(file_path)
    channels = info.channels
    sample_rate = info.samplerate
    total_frames = info.frames
    duration = total_frames / sample_rate if sample_rate else 0.0

    if total_frames <= 0 or max_points <= 0:
        preview = np.zeros(0, dtype=np.float32)
    else:
        step = max(1, total_frames // max_points)
        chunks: list[np.ndarray] = []
        with sf.SoundFile(file_path) as handle:
            for start in range(0, total_frames, step):
                handle.seek(start)
                frames_to_read = min(step, total_frames - start)
                block = handle.read(frames=frames_to_read, dtype="float32", always_2d=True)
                if len(block) == 0:
                    continue
                mono = block.mean(axis=1)
                chunks.append(np.array([np.max(np.abs(mono))], dtype=np.float32))
        preview = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        peak = max(float(np.max(np.abs(preview))), 1e-9)
        preview = preview / peak

    return {
        "file_path": str(path),
        "file_name": path.name,
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "frames": total_frames,
        "waveform": preview.astype(np.float32),
        "subtype": info.subtype,
        "format": info.format,
    }
