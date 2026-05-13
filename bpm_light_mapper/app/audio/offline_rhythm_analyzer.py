from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.signal import find_peaks

from bpm_light_mapper.app.models.tempo_candidate import TempoCandidate


@dataclass
class OfflineRhythmResult:
    bpm: float
    beat_times: np.ndarray
    onset_envelope: np.ndarray
    onset_times: np.ndarray
    tempo_candidates: list[TempoCandidate]
    confidence: float
    downbeat_time: Optional[float]
    diagnostic_summary: str
    warnings: list[str]


@dataclass
class _CandidateScore:
    bpm: float
    alignment: float
    onset_alignment: float
    accent: float
    interval_stability: float
    tempogram_score: float
    confidence: float
    offset: float


def analyze_offline_rhythm(
    waveform: np.ndarray,
    sample_rate: int,
    hop_length: int,
    start_bpm: float,
    tightness: float,
    bpm_min: float,
    bpm_max: float,
) -> OfflineRhythmResult:
    samples = _prepare_waveform(waveform)
    if samples.size < max(2048, hop_length * 8):
        onset_envelope = np.zeros(0, dtype=np.float32)
        onset_times = np.zeros(0, dtype=np.float32)
        return OfflineRhythmResult(
            bpm=float(np.clip(start_bpm, bpm_min, bpm_max)),
            beat_times=np.zeros(0, dtype=float),
            onset_envelope=onset_envelope,
            onset_times=onset_times,
            tempo_candidates=[],
            confidence=0.0,
            downbeat_time=None,
            diagnostic_summary="Audio demasiado corto para una estimacion offline fiable.",
            warnings=["Audio demasiado corto para analisis ritmico robusto."],
        )

    onset_envelope, onset_times = _combined_musical_onset_envelope(samples, sample_rate, hop_length)
    duration = samples.size / sample_rate
    raw_candidates = _tempo_candidates_from_tempogram(
        onset_envelope,
        sample_rate,
        hop_length,
        start_bpm=start_bpm,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
    )
    scores = [
        _score_candidate(candidate, onset_envelope, onset_times, duration, bpm_min, bpm_max)
        for candidate in raw_candidates
        if candidate > 0.0
    ]
    scores = [score for score in scores if score.confidence > 0.0]
    if not scores:
        scores = [_score_candidate(float(np.clip(start_bpm, bpm_min, bpm_max)), onset_envelope, onset_times, duration, bpm_min, bpm_max)]

    scores.sort(key=lambda item: item.confidence, reverse=True)
    chosen = _choose_musical_candidate(scores, bpm_min, bpm_max)
    beat_times = _track_beats_for_candidate(onset_envelope, onset_times, duration, chosen.bpm, chosen.offset, tightness)
    if len(beat_times) < 4:
        beat_times = _grid_from_offset(chosen.offset, duration, chosen.bpm)
    beat_times = _trim_and_sort_beats(beat_times, duration)
    confidence = _final_confidence(chosen, beat_times)
    tempo_candidates = _tempo_candidate_models(chosen, scores, bpm_min, bpm_max)
    warnings = _warnings_for_result(confidence, tempo_candidates)
    diagnostic_summary = _diagnostic_summary(chosen, tempo_candidates, confidence, len(beat_times))
    return OfflineRhythmResult(
        bpm=chosen.bpm,
        beat_times=beat_times,
        onset_envelope=onset_envelope.astype(np.float32),
        onset_times=onset_times.astype(np.float32),
        tempo_candidates=tempo_candidates,
        confidence=confidence,
        downbeat_time=float(beat_times[0]) if len(beat_times) else None,
        diagnostic_summary=diagnostic_summary,
        warnings=warnings,
    )


def _prepare_waveform(waveform: np.ndarray) -> np.ndarray:
    samples = np.asarray(waveform, dtype=np.float32)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = samples - float(np.mean(samples)) if samples.size else samples
    peak = max(float(np.max(np.abs(samples))) if samples.size else 0.0, 1e-9)
    return (samples / peak).astype(np.float32)


def _combined_musical_onset_envelope(
    samples: np.ndarray,
    sample_rate: int,
    hop_length: int,
) -> tuple[np.ndarray, np.ndarray]:
    n_fft = 2048
    if samples.size < n_fft:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
    frames = _frame_audio(samples, n_fft, hop_length)
    window = np.hanning(n_fft).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(frames * window[None, :], axis=1)).astype(np.float32)
    log_spectrum = np.log1p(spectrum * 20.0)
    flux = np.diff(log_spectrum, axis=0, prepend=log_spectrum[:1])
    flux = np.maximum(flux, 0.0)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    full = _band_flux(flux, freqs, 30.0, min(sample_rate / 2.0, 12000.0))
    low = _band_flux(flux, freqs, 35.0, 180.0)
    mid = _band_flux(flux, freqs, 180.0, 2600.0)
    high = _band_flux(flux, freqs, 2600.0, min(sample_rate / 2.0, 12000.0))
    broadband_transient = _normalize_env(np.maximum(full - _moving_average(full, 9), 0.0))
    envelopes = [_normalize_env(env) for env in [full, broadband_transient, low, mid, high]]
    min_len = min(len(env) for env in envelopes)
    if min_len <= 0:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
    full, transient, low, mid, high = [env[:min_len] for env in envelopes]
    combined = (0.18 * full) + (0.32 * transient) + (0.25 * low) + (0.18 * mid) + (0.07 * high)
    combined = np.maximum(combined - np.percentile(combined, 18), 0.0)
    combined = _normalize_env(combined).astype(np.float32)
    times = (np.arange(min_len, dtype=np.float32) * hop_length / sample_rate).astype(np.float32)
    return combined, times


def _frame_audio(samples: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    frame_count = 1 + max(0, (samples.size - frame_length) // hop_length)
    shape = (frame_count, frame_length)
    strides = (samples.strides[0] * hop_length, samples.strides[0])
    return np.lib.stride_tricks.as_strided(samples, shape=shape, strides=strides)


def _band_flux(flux: np.ndarray, freqs: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    mask = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(mask):
        return np.zeros(flux.shape[0], dtype=float)
    values = flux[:, mask]
    return np.mean(values, axis=1).astype(float)


def _moving_average(values: np.ndarray, window_size: int) -> np.ndarray:
    if len(values) == 0 or window_size <= 1:
        return values.astype(float)
    kernel = np.ones(window_size, dtype=float) / window_size
    return np.convolve(values.astype(float), kernel, mode="same")


def _normalize_env(envelope: np.ndarray) -> np.ndarray:
    values = np.asarray(envelope, dtype=float)
    if values.size == 0:
        return values
    values = np.maximum(values, 0.0)
    high = float(np.percentile(values, 98))
    if high <= 1e-9:
        return np.zeros_like(values)
    return np.clip(values / high, 0.0, 1.0)


def _tempo_candidates_from_tempogram(
    onset_envelope: np.ndarray,
    sample_rate: int,
    hop_length: int,
    start_bpm: float,
    bpm_min: float,
    bpm_max: float,
) -> list[float]:
    if len(onset_envelope) < 8 or float(np.max(onset_envelope)) <= 1e-9:
        return [float(np.clip(start_bpm, bpm_min, bpm_max))]
    novelty = onset_envelope.astype(float) - float(np.mean(onset_envelope))
    corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    lag_min = max(1, int(np.floor((60.0 / (bpm_max * 2.0)) * sample_rate / hop_length)))
    lag_max = min(len(corr) - 1, int(np.ceil((60.0 / max(bpm_min / 2.0, 1.0)) * sample_rate / hop_length)))
    if lag_max <= lag_min:
        return [float(np.clip(start_bpm, bpm_min, bpm_max))]

    local = np.asarray(corr[lag_min : lag_max + 1], dtype=float)
    local = np.maximum(local, 0.0)
    if local.size == 0 or float(np.max(local)) <= 1e-9:
        return [float(np.clip(start_bpm, bpm_min, bpm_max))]

    peaks, _ = find_peaks(local, distance=2, prominence=float(np.max(local)) * 0.04)
    if len(peaks) == 0:
        peaks = np.array([int(np.argmax(local))])
    ranked = sorted(peaks, key=lambda idx: local[int(idx)], reverse=True)[:12]
    candidates = [float(np.clip(start_bpm, bpm_min, bpm_max))]
    for peak_idx in ranked:
        lag = lag_min + int(peak_idx)
        refined_lag = _refine_autocorr_lag(corr, lag)
        bpm = 60.0 * sample_rate / (hop_length * refined_lag)
        for related in (bpm, bpm / 2.0, bpm * 2.0):
            normalized = _normalize_bpm(related, bpm_min, bpm_max)
            if normalized > 0:
                candidates.append(normalized)
    return _dedupe_bpms(candidates)


def _refine_autocorr_lag(corr: np.ndarray, lag: int) -> float:
    if lag <= 0 or lag >= len(corr) - 1:
        return float(lag)
    left = float(corr[lag - 1])
    center = float(corr[lag])
    right = float(corr[lag + 1])
    denom = left - (2.0 * center) + right
    if abs(denom) <= 1e-12:
        return float(lag)
    offset = 0.5 * (left - right) / denom
    return float(lag + np.clip(offset, -0.5, 0.5))


def _score_candidate(
    bpm: float,
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    duration: float,
    bpm_min: float,
    bpm_max: float,
) -> _CandidateScore:
    bpm = _normalize_bpm(bpm, bpm_min, bpm_max)
    if bpm <= 0.0 or len(onset_envelope) == 0 or len(onset_times) == 0:
        return _CandidateScore(bpm, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    period = 60.0 / bpm
    strong_times, strong_values = _strong_onsets(onset_envelope, onset_times, bpm)
    if len(strong_times) == 0:
        return _CandidateScore(bpm, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    offsets = np.mod(strong_times[: min(40, len(strong_times))], period)
    best_offset = float(offsets[0])
    best_alignment = 0.0
    for offset in offsets:
        grid = _grid_from_offset(float(offset), duration, bpm)
        alignment = _grid_onset_alignment(grid, onset_times, onset_envelope, period)
        if alignment > best_alignment:
            best_alignment = alignment
            best_offset = float(offset)
    grid = _grid_from_offset(best_offset, duration, bpm)
    onset_alignment = _grid_onset_alignment(grid, onset_times, onset_envelope, period)
    accent = _accent_score(grid, strong_times, strong_values, period)
    interval_stability = _periodicity_score(strong_times, period)
    tempogram_score = _tempogram_score(onset_envelope, onset_times, period)
    density_penalty = _weak_grid_penalty(grid, onset_times, onset_envelope, period)
    confidence = (
        (0.30 * onset_alignment)
        + (0.18 * accent)
        + (0.20 * interval_stability)
        + (0.24 * tempogram_score)
        + (0.08 * density_penalty)
    )
    return _CandidateScore(
        bpm=bpm,
        alignment=best_alignment,
        onset_alignment=onset_alignment,
        accent=accent,
        interval_stability=interval_stability,
        tempogram_score=tempogram_score,
        confidence=float(np.clip(confidence, 0.0, 1.0)),
        offset=best_offset,
    )


def _choose_musical_candidate(scores: list[_CandidateScore], bpm_min: float, bpm_max: float) -> _CandidateScore:
    if not scores:
        return _CandidateScore(float(np.clip(120.0, bpm_min, bpm_max)), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    preferred_low = max(bpm_min, 70.0)
    preferred_high = min(bpm_max, 180.0)
    ranked: list[tuple[float, _CandidateScore]] = []
    for score in scores:
        preference = 0.04 if preferred_low <= score.bpm <= preferred_high else -0.04
        ranked.append((score.confidence + preference, score))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _track_beats_for_candidate(
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    duration: float,
    bpm: float,
    offset: float,
    tightness: float,
) -> np.ndarray:
    del tightness
    if bpm <= 0.0 or duration <= 0.0:
        return np.zeros(0, dtype=float)
    period = 60.0 / bpm
    grid = _grid_from_offset(offset, duration, bpm)
    tolerance = max(0.035, period * 0.10)
    snapped: list[float] = []
    for beat in grid:
        idx = int(np.searchsorted(onset_times, beat))
        left = max(0, idx - 4)
        right = min(len(onset_times), idx + 5)
        if right <= left:
            snapped.append(float(beat))
            continue
        local_times = onset_times[left:right]
        local_env = onset_envelope[left:right]
        distances = np.abs(local_times - beat)
        mask = distances <= tolerance
        if not np.any(mask):
            snapped.append(float(beat))
            continue
        weighted = local_env[mask] * np.clip(1.0 - (distances[mask] / tolerance), 0.0, 1.0)
        if float(np.max(weighted)) < 0.06:
            snapped.append(float(beat))
        else:
            snapped.append(float(local_times[mask][int(np.argmax(weighted))]))
    return np.asarray(snapped, dtype=float)


def _tempo_candidate_models(
    chosen: _CandidateScore,
    scores: list[_CandidateScore],
    bpm_min: float,
    bpm_max: float,
) -> list[TempoCandidate]:
    by_bpm = {round(score.bpm, 1): score for score in scores}
    labels = [
        ("Half-time", chosen.bpm / 2.0),
        ("Detected", chosen.bpm),
        ("Double-time", chosen.bpm * 2.0),
    ]
    result: list[TempoCandidate] = []
    for label, raw_bpm in labels:
        normalized = _normalize_bpm(raw_bpm, bpm_min, bpm_max)
        score = by_bpm.get(round(normalized, 1)) or _nearest_score(normalized, scores) or chosen
        in_range = bpm_min <= raw_bpm <= bpm_max
        result.append(
            TempoCandidate(
                label=label,
                bpm=float(normalized),
                beat_interval_ms=float(60000.0 / normalized) if normalized > 0 else 0.0,
                grid_alignment_score=score.alignment,
                onset_alignment_score=score.onset_alignment,
                accent_score=score.accent,
                confidence=score.confidence,
                in_configured_range=in_range,
            )
        )
    return result


def _nearest_score(bpm: float, scores: list[_CandidateScore]) -> Optional[_CandidateScore]:
    if not scores:
        return None
    return min(scores, key=lambda score: abs(score.bpm - bpm))


def _strong_onsets(onset_envelope: np.ndarray, onset_times: np.ndarray, bpm: float) -> tuple[np.ndarray, np.ndarray]:
    period = 60.0 / max(bpm, 1e-9)
    frame_step = float(np.median(np.diff(onset_times))) if len(onset_times) > 2 else period / 8.0
    distance = max(1, int(round((period * 0.20) / max(frame_step, 1e-9))))
    threshold = max(0.08, float(np.percentile(onset_envelope, 65)))
    peaks, _ = find_peaks(onset_envelope, distance=distance, height=threshold, prominence=0.03)
    if len(peaks) < 4:
        peaks, _ = find_peaks(onset_envelope, distance=max(1, distance // 2), height=max(0.04, threshold * 0.6))
    if len(peaks) == 0:
        return np.zeros(0, dtype=float), np.zeros(0, dtype=float)
    ranked = sorted(peaks, key=lambda idx: onset_envelope[int(idx)], reverse=True)
    times = onset_times[np.asarray(ranked, dtype=int)].astype(float)
    values = onset_envelope[np.asarray(ranked, dtype=int)].astype(float)
    return times, values


def _grid_onset_alignment(
    grid: np.ndarray,
    onset_times: np.ndarray,
    onset_envelope: np.ndarray,
    period: float,
) -> float:
    if len(grid) == 0:
        return 0.0
    tolerance = max(0.035, period * 0.12)
    scores = []
    for beat in grid:
        idx = int(np.searchsorted(onset_times, beat))
        left = max(0, idx - 3)
        right = min(len(onset_times), idx + 4)
        if right <= left:
            scores.append(0.0)
            continue
        distances = np.abs(onset_times[left:right] - beat)
        weights = np.clip(1.0 - (distances / tolerance), 0.0, 1.0)
        scores.append(float(np.max(onset_envelope[left:right] * weights)))
    return float(np.clip(np.mean(scores), 0.0, 1.0))


def _accent_score(grid: np.ndarray, strong_times: np.ndarray, strong_values: np.ndarray, period: float) -> float:
    if len(grid) == 0 or len(strong_times) == 0:
        return 0.0
    tolerance = max(0.035, period * 0.12)
    total = float(np.sum(strong_values)) or 1.0
    aligned = 0.0
    for onset_time, onset_value in zip(strong_times, strong_values):
        distance = float(np.min(np.abs(grid - onset_time))) if len(grid) else period
        aligned += float(onset_value) * max(0.0, 1.0 - (distance / tolerance))
    return float(np.clip(aligned / total, 0.0, 1.0))


def _periodicity_score(strong_times: np.ndarray, period: float) -> float:
    if len(strong_times) < 4 or period <= 0.0:
        return 0.0
    ordered = np.sort(strong_times)
    intervals = np.diff(ordered)
    normalized_error = np.minimum.reduce(
        [
            np.abs(intervals - period) / period,
            np.abs(intervals - (period / 2.0)) / period,
            np.abs(intervals - (period * 2.0)) / period,
        ]
    )
    return float(np.clip(1.0 - np.median(normalized_error) * 2.0, 0.0, 1.0))


def _tempogram_score(onset_envelope: np.ndarray, onset_times: np.ndarray, period: float) -> float:
    if len(onset_envelope) < 4 or len(onset_times) < 4 or period <= 0.0:
        return 0.0
    frame_step = float(np.median(np.diff(onset_times)))
    if frame_step <= 0.0:
        return 0.0
    lag = int(round(period / frame_step))
    if lag <= 0 or lag >= len(onset_envelope):
        return 0.0
    novelty = onset_envelope.astype(float) - float(np.mean(onset_envelope))
    corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    base = max(float(corr[0]), 1e-9)
    local = corr[max(1, lag - 1) : min(len(corr), lag + 2)]
    if len(local) == 0:
        return 0.0
    return float(np.clip(np.max(local) / base, 0.0, 1.0))


def _weak_grid_penalty(
    grid: np.ndarray,
    onset_times: np.ndarray,
    onset_envelope: np.ndarray,
    period: float,
) -> float:
    if len(grid) == 0:
        return 0.0
    alignment = _grid_onset_alignment(grid, onset_times, onset_envelope, period)
    too_dense_penalty = 0.08 if period < 0.34 and alignment < 0.45 else 0.0
    return float(np.clip(alignment - too_dense_penalty, 0.0, 1.0))


def _final_confidence(chosen: _CandidateScore, beat_times: np.ndarray) -> float:
    if len(beat_times) < 4:
        return float(np.clip(chosen.confidence * 0.6, 0.0, 1.0))
    expected = 60.0 / chosen.bpm
    intervals = np.diff(beat_times)
    jitter = float(np.median(np.abs(intervals - expected)) / max(expected, 1e-9))
    beat_stability = max(0.0, 1.0 - jitter * 2.0)
    return float(np.clip((chosen.confidence * 0.72) + (beat_stability * 0.28), 0.0, 1.0))


def _warnings_for_result(confidence: float, candidates: list[TempoCandidate]) -> list[str]:
    warnings: list[str] = []
    if confidence < 0.55:
        warnings.append("Confianza offline baja: revisa manualmente BPM, primer beat y candidatos half/double.")
    if len(candidates) >= 3:
        ordered = sorted(candidates, key=lambda item: item.confidence, reverse=True)
        if len(ordered) > 1 and abs(ordered[0].confidence - ordered[1].confidence) < 0.12:
            warnings.append("Ambiguedad half-time/double-time: dos candidatos tienen confianza similar.")
    return warnings


def _diagnostic_summary(
    chosen: _CandidateScore,
    candidates: list[TempoCandidate],
    confidence: float,
    beat_count: int,
) -> str:
    alternative = next((candidate for candidate in candidates if abs(candidate.bpm - chosen.bpm) > 1.0), None)
    alt_text = f", alternativa: {alternative.bpm:.1f}" if alternative is not None else ""
    return (
        f"BPM probable: {chosen.bpm:.1f}{alt_text}, confianza: {confidence:.2f}. "
        f"Grid con {beat_count} beats; alineacion onset {chosen.onset_alignment:.2f}, "
        f"acento {chosen.accent:.2f}, estabilidad {chosen.interval_stability:.2f}, "
        f"tempogram {chosen.tempogram_score:.2f}."
    )


def _grid_from_offset(offset: float, duration: float, bpm: float) -> np.ndarray:
    if bpm <= 0.0 or duration <= 0.0:
        return np.zeros(0, dtype=float)
    period = 60.0 / bpm
    first = float(offset)
    while first > 0.0:
        first -= period
    while first < 0.0:
        first += period
    return np.arange(first, duration + (period * 0.5), period, dtype=float)


def _trim_and_sort_beats(beat_times: np.ndarray, duration: float) -> np.ndarray:
    values = np.asarray(beat_times, dtype=float)
    values = values[(values >= 0.0) & (values <= duration)]
    if len(values) == 0:
        return values
    return np.unique(np.round(np.sort(values), 6)).astype(float)


def _normalize_bpm(bpm: float, bpm_min: float, bpm_max: float) -> float:
    if bpm <= 0.0:
        return 0.0
    value = float(bpm)
    while value < bpm_min:
        value *= 2.0
    while value > bpm_max:
        value /= 2.0
    return float(np.clip(value, bpm_min, bpm_max))


def _dedupe_bpms(candidates: list[float]) -> list[float]:
    result: list[float] = []
    for bpm in sorted(candidates):
        if not any(abs(existing - bpm) < 0.75 for existing in result):
            result.append(float(bpm))
    return result
