from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks


def compute_onset_envelope(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    onset_sensitivity: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    frame_length = max(hop_length * 2, 512)
    if len(waveform) < frame_length:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)

    samples = np.asarray(waveform, dtype=np.float32)
    squared = np.square(samples, dtype=np.float32)
    cumsum = np.concatenate([[0.0], np.cumsum(squared, dtype=np.float64)])
    starts = np.arange(0, len(samples) - frame_length, hop_length)
    energy = (cumsum[starts + frame_length] - cumsum[starts]) / frame_length
    rms = np.sqrt(np.maximum(energy, 0.0))
    log_rms = np.log1p(rms * 100.0)
    envelope = np.diff(log_rms, prepend=log_rms[0])
    envelope = np.maximum(envelope, 0.0)
    if envelope.size:
        envelope = envelope / max(float(np.max(envelope)), 1e-9)
    envelope = np.maximum(envelope * onset_sensitivity, 0.0).astype(np.float32)
    times = (starts / sample_rate).astype(np.float32)
    return envelope, times


def _estimate_tempo_from_onsets(
    onset_envelope: np.ndarray,
    sample_rate: int,
    hop_length: int,
    bpm_min: float = 60.0,
    bpm_max: float = 180.0,
    fallback_bpm: float = 120.0,
) -> float:
    if len(onset_envelope) < 8 or np.max(onset_envelope) <= 1e-9:
        return fallback_bpm
    novelty = onset_envelope.astype(float) - float(np.mean(onset_envelope))
    corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    lag_min = max(1, int(np.floor((60.0 / bpm_max) * sample_rate / hop_length)))
    lag_max = min(len(corr) - 1, int(np.ceil((60.0 / bpm_min) * sample_rate / hop_length)))
    if lag_max <= lag_min:
        return fallback_bpm
    local = corr[lag_min : lag_max + 1]
    if len(local) == 0 or np.max(local) <= 1e-9:
        return fallback_bpm
    lag = lag_min + int(np.argmax(local))
    bpm = 60.0 * sample_rate / (hop_length * lag)
    while bpm < bpm_min:
        bpm *= 2.0
    while bpm > bpm_max:
        bpm /= 2.0
    return float(np.clip(bpm, bpm_min, bpm_max))


def _normalize_bpm(bpm: float, bpm_min: float, bpm_max: float) -> float:
    if bpm <= 0:
        return 0.0
    while bpm < bpm_min:
        bpm *= 2.0
    while bpm > bpm_max:
        bpm /= 2.0
    return float(np.clip(bpm, bpm_min, bpm_max))


def _detect_onset_peaks(
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    sample_rate: int,
    hop_length: int,
    bpm_max: float,
) -> np.ndarray:
    if len(onset_envelope) == 0 or len(onset_times) == 0:
        return np.zeros(0, dtype=float)

    min_period_frames = (60.0 / max(bpm_max, 1.0)) * sample_rate / hop_length
    min_distance = max(1, int(round(min_period_frames * 0.35)))
    active = onset_envelope[onset_envelope > 0]
    if len(active) == 0:
        return np.zeros(0, dtype=float)

    prominence = max(0.03, float(np.percentile(active, 70)) * 0.35)
    height = max(0.02, float(np.percentile(active, 55)) * 0.35)
    peaks, _ = find_peaks(
        onset_envelope,
        distance=min_distance,
        prominence=prominence,
        height=height,
    )
    if len(peaks) < 4:
        peaks, _ = find_peaks(onset_envelope, distance=min_distance, height=height)
    return onset_times[peaks].astype(float)


def _estimate_tempo_from_peak_times(
    peak_times: np.ndarray,
    bpm_min: float,
    bpm_max: float,
    fallback_bpm: float,
) -> float:
    if len(peak_times) < 4:
        return float(np.clip(fallback_bpm, bpm_min, bpm_max))

    candidates: list[float] = []
    weights: list[float] = []
    max_step = min(4, len(peak_times) - 1)
    min_interval = 60.0 / max(bpm_max * 2.0, 1.0)
    max_interval = 60.0 / max(bpm_min / 2.0, 1.0)
    for step in range(1, max_step + 1):
        intervals = peak_times[step:] - peak_times[:-step]
        intervals = intervals[(intervals >= min_interval) & (intervals <= max_interval)]
        for interval in intervals:
            bpm = _normalize_bpm(60.0 / float(interval), bpm_min, bpm_max)
            if bpm > 0:
                candidates.append(bpm)
                weights.append(1.0 / step)

    if not candidates:
        return float(np.clip(fallback_bpm, bpm_min, bpm_max))

    values = np.asarray(candidates, dtype=float)
    weights_arr = np.asarray(weights, dtype=float)
    bins = np.arange(bpm_min, bpm_max + 1.0, 0.5)
    hist, edges = np.histogram(values, bins=bins, weights=weights_arr)
    if len(hist) == 0 or float(np.max(hist)) <= 0:
        return float(np.clip(float(np.median(values)), bpm_min, bpm_max))

    center = float((edges[int(np.argmax(hist))] + edges[int(np.argmax(hist)) + 1]) / 2.0)
    near = values[np.abs(values - center) <= 1.0]
    if len(near) == 0:
        return center
    return float(np.clip(np.median(near), bpm_min, bpm_max))


def _refine_peak_times_from_waveform(
    waveform: np.ndarray,
    sample_rate: int,
    rough_times: np.ndarray,
    hop_length: int,
    bpm_max: float,
) -> np.ndarray:
    if len(rough_times) == 0 or len(waveform) == 0:
        return rough_times.astype(float)

    samples = np.abs(np.asarray(waveform, dtype=np.float32))
    refined: list[float] = []
    for rough_time in rough_times:
        center = int(round(float(rough_time) * sample_rate))
        start = max(0, center - hop_length)
        end = min(len(samples), center + hop_length * 4)
        if end <= start:
            continue
        local_peak = int(np.argmax(samples[start:end]))
        refined.append((start + local_peak) / sample_rate)

    if not refined:
        return rough_times.astype(float)

    refined = sorted(refined)
    min_gap = (60.0 / max(bpm_max, 1.0)) * 0.25
    deduped: list[float] = []
    for peak_time in refined:
        if not deduped or peak_time - deduped[-1] >= min_gap:
            deduped.append(peak_time)
        elif abs(samples[int(min(peak_time * sample_rate, len(samples) - 1))]) > abs(
            samples[int(min(deduped[-1] * sample_rate, len(samples) - 1))]
        ):
            deduped[-1] = peak_time
    return np.asarray(deduped, dtype=float)


def _detect_peak_beats(
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    sample_rate: int,
    hop_length: int,
    bpm: float,
) -> np.ndarray:
    if len(onset_envelope) == 0 or bpm <= 0:
        return np.zeros(0, dtype=float)
    beat_period_frames = max(1, int(round((60.0 / bpm) * sample_rate / hop_length)))
    min_distance = max(1, int(beat_period_frames * 0.55))
    prominence = max(0.05, float(np.percentile(onset_envelope, 75)) * 0.5)
    peaks, _ = find_peaks(onset_envelope, distance=min_distance, prominence=prominence)
    if len(peaks) < 4:
        peaks, _ = find_peaks(onset_envelope, distance=min_distance)
    return onset_times[peaks].astype(float)


def detect_beats(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
    start_bpm: float = 120.0,
    tightness: float = 100.0,
    bpm_min: float = 60.0,
    bpm_max: float = 180.0,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    onset_envelope, onset_times = compute_onset_envelope(
        waveform,
        sample_rate,
        hop_length=hop_length,
    )
    del tightness
    fallback_tempo = _estimate_tempo_from_onsets(
        onset_envelope,
        sample_rate,
        hop_length,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        fallback_bpm=start_bpm,
    )
    beat_times = _detect_onset_peaks(
        onset_envelope,
        onset_times,
        sample_rate,
        hop_length,
        bpm_max,
    )
    beat_times = _refine_peak_times_from_waveform(
        waveform,
        sample_rate,
        beat_times,
        hop_length,
        bpm_max,
    )
    tempo = _estimate_tempo_from_peak_times(beat_times, bpm_min, bpm_max, fallback_tempo)
    if len(beat_times) < 4:
        beat_times = _detect_peak_beats(
            onset_envelope,
            onset_times,
            sample_rate,
            hop_length,
            tempo,
        )
    return float(tempo), beat_times, onset_envelope, onset_times


def beat_consistency_confidence(beat_times: np.ndarray, target_bpm: float) -> float:
    if len(beat_times) < 4 or target_bpm <= 0:
        return 0.0
    intervals = np.diff(beat_times)
    expected = 60.0 / target_bpm
    median_error = np.median(np.abs(intervals - expected))
    jitter_score = max(0.0, 1.0 - (median_error / max(expected, 1e-6)))
    spread_penalty = min(1.0, np.std(intervals) / max(expected, 1e-6))
    return float(np.clip(jitter_score * (1.0 - 0.5 * spread_penalty), 0.0, 1.0))
