from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def _load_audio_streaming_mono(file_path: str, target_sr: int | None) -> tuple[np.ndarray, int, int, float, str, str, int]:
    info = sf.info(file_path)
    raw_sr = info.samplerate
    channels = info.channels
    duration = info.frames / raw_sr if raw_sr else 0.0
    subtype = info.subtype
    audio_format = info.format

    if target_sr is None or target_sr >= raw_sr:
        blocks = []
        with sf.SoundFile(file_path) as handle:
            for block in handle.blocks(blocksize=262_144, dtype="float32", always_2d=True):
                blocks.append(block.mean(axis=1))
        mono = np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.float32)
        return mono.astype(np.float32), raw_sr, channels, duration, subtype, audio_format, len(mono)

    gcd = int(np.gcd(raw_sr, target_sr))
    up = target_sr // gcd
    down = raw_sr // gcd
    blocks = []
    with sf.SoundFile(file_path) as handle:
        for block in handle.blocks(blocksize=262_144, dtype="float32", always_2d=True):
            mono_block = block.mean(axis=1)
            resampled = resample_poly(mono_block, up, down).astype(np.float32)
            blocks.append(resampled)
    mono = np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.float32)
    return mono.astype(np.float32), target_sr, channels, duration, subtype, audio_format, len(mono)


def load_audio(file_path: str, target_sr: int | None = None) -> dict[str, Any]:
    path = Path(file_path)
    try:
        info = sf.info(file_path)
        raw_sr = info.samplerate
        mono, sample_rate, channels, duration, subtype, audio_format, frame_count = _load_audio_streaming_mono(
            file_path,
            target_sr,
        )
    except Exception:
        mono, sample_rate = librosa.load(file_path, sr=target_sr, mono=True)
        info = sf.info(file_path)
        raw_sr = info.samplerate
        channels = info.channels
        duration = info.frames / raw_sr if raw_sr else (len(mono) / sample_rate if sample_rate else 0.0)
        subtype = info.subtype
        audio_format = info.format
        frame_count = len(mono)

    peak_amplitude = float(np.max(np.abs(mono))) if len(mono) else 0.0
    rms_energy = float(np.sqrt(np.mean(np.square(mono)))) if len(mono) else 0.0
    waveform = mono / max(peak_amplitude, 1e-9)

    return {
        "file_path": str(path),
        "file_name": path.name,
        "duration": duration,
        "sample_rate": sample_rate,
        "original_sample_rate": raw_sr,
        "channels": channels,
        "waveform": waveform.astype(np.float32),
        "peak_amplitude": peak_amplitude,
        "rms_energy": rms_energy,
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
        peak = float(np.max(np.abs(preview))) if len(preview) else 0.0
        preview = preview / max(peak, 1e-9)

    return {
        "file_path": str(path),
        "file_name": path.name,
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "frames": total_frames,
        "waveform": preview.astype(np.float32),
        "peak_amplitude": peak if total_frames > 0 else 0.0,
        "rms_energy": float(np.sqrt(np.mean(np.square(preview)))) if len(preview) else 0.0,
        "subtype": info.subtype,
        "format": info.format,
    }
