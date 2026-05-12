from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bpm_light_mapper.app.models.segment import Segment


@dataclass
class TempoMapParameters:
    window_seconds: float = 12.0
    hop_seconds: float = 2.0
    min_bpm_change: float = 3.0
    min_segment_seconds: float = 8.0
    onset_sensitivity: float = 1.0
    bpm_min: float = 60.0
    bpm_max: float = 180.0


def _window_confidence(onset_env: np.ndarray, beat_times: np.ndarray, bpm: float) -> float:
    if len(onset_env) == 0 or len(beat_times) < 3 or bpm <= 0:
        return 0.0
    energy = float(np.mean(onset_env) / max(np.max(onset_env), 1e-9))
    intervals = np.diff(beat_times)
    expected = 60.0 / bpm
    jitter = float(np.std(intervals) / max(expected, 1e-9))
    regularity = max(0.0, 1.0 - jitter)
    return float(np.clip(0.6 * regularity + 0.4 * energy, 0.0, 1.0))


def _estimate_local_bpm_from_beats(
    beat_times: np.ndarray,
    bpm_min: float,
    bpm_max: float,
) -> float | None:
    if len(beat_times) < 4:
        return None
    intervals = np.diff(beat_times)
    if len(intervals) == 0:
        return None
    median_interval = float(np.median(intervals))
    if median_interval <= 0:
        return None
    bpm = 60.0 / median_interval
    while bpm < bpm_min and bpm > 0:
        bpm *= 2.0
    while bpm > bpm_max:
        bpm /= 2.0
    return float(np.clip(bpm, bpm_min, bpm_max))


def generate_tempo_map(
    waveform: np.ndarray,
    sample_rate: int,
    beat_times: np.ndarray,
    onset_envelope: np.ndarray,
    params: TempoMapParameters,
    progress_callback=None,
    should_cancel=None,
) -> list[Segment]:
    duration = len(waveform) / sample_rate
    if duration <= 0:
        return []

    hop_length = max(1, int(round((len(waveform) / sample_rate) / max(len(onset_envelope), 1) * sample_rate)))
    times = np.arange(len(onset_envelope), dtype=float) * hop_length / sample_rate
    windows: list[dict] = []
    total_windows = max(1, int(np.ceil(duration / max(params.hop_seconds, 1e-9))))
    window_index = 0
    start = 0.0
    while start < duration:
        if should_cancel is not None and should_cancel():
            return []
        end = min(duration, start + params.window_seconds)
        mask = (times >= start) & (times < end)
        beat_mask = (beat_times >= start) & (beat_times < end)
        local_beats = beat_times[beat_mask]
        if mask.sum() >= 4 and len(local_beats) >= 4:
            local_env = onset_envelope[mask]
            bpm = _estimate_local_bpm_from_beats(local_beats, params.bpm_min, params.bpm_max)
            if bpm is None:
                start += params.hop_seconds
                window_index += 1
                continue
            confidence = _window_confidence(local_env, local_beats, bpm)
            windows.append(
                {
                    "start": start,
                    "end": end,
                    "bpm": bpm,
                    "confidence": confidence,
                    "beats": local_beats.tolist(),
                }
            )
        window_index += 1
        if progress_callback is not None and window_index % 10 == 0:
            progress_callback(f"segmentando zonas... ventana {window_index}/{total_windows}")
        start += params.hop_seconds

    if not windows:
        return []

    smoothed_bpms = np.array([window["bpm"] for window in windows], dtype=float)
    if len(smoothed_bpms) >= 3:
        smoothed_bpms = np.convolve(smoothed_bpms, np.ones(3) / 3, mode="same")

    segments: list[Segment] = []
    current = {
        "start": windows[0]["start"],
        "end": windows[0]["end"],
        "bpms": [float(smoothed_bpms[0])],
        "conf": [windows[0]["confidence"]],
        "beats": list(windows[0]["beats"]),
    }

    for idx, window in enumerate(windows[1:], start=1):
        bpm = float(smoothed_bpms[idx])
        current_bpm = float(np.median(current["bpms"]))
        can_split = abs(bpm - current_bpm) >= params.min_bpm_change
        long_enough = (current["end"] - current["start"]) >= params.min_segment_seconds
        if can_split and long_enough:
            segments.append(
                Segment(
                    start=current["start"],
                    end=current["end"],
                    bpm=float(np.median(current["bpms"])),
                    confidence=float(np.mean(current["conf"])),
                    beats=sorted(set(current["beats"])),
                )
            )
            current = {
                "start": window["start"],
                "end": window["end"],
                "bpms": [bpm],
                "conf": [window["confidence"]],
                "beats": list(window["beats"]),
            }
        else:
            current["end"] = window["end"]
            current["bpms"].append(bpm)
            current["conf"].append(window["confidence"])
            current["beats"].extend(window["beats"])

    segments.append(
        Segment(
            start=current["start"],
            end=current["end"],
            bpm=float(np.median(current["bpms"])),
            confidence=float(np.mean(current["conf"])),
            beats=sorted(set(current["beats"])),
        )
    )

    merged: list[Segment] = []
    for segment in segments:
        if merged and segment.duration < params.min_segment_seconds:
            prev = merged[-1]
            prev.end = segment.end
            prev.bpm = float(np.median([prev.bpm, segment.bpm]))
            prev.confidence = float(np.mean([prev.confidence, segment.confidence]))
            prev.beats = sorted(set(prev.beats + segment.beats))
        else:
            merged.append(segment)

    return merged
