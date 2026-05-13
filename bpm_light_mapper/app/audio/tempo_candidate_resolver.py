from __future__ import annotations

import numpy as np

from bpm_light_mapper.app.models.tempo_candidate import TempoCandidate


def resolve_tempo_candidates(
    detected_bpm: float,
    beat_times: np.ndarray,
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    bpm_min: float,
    bpm_max: float,
) -> tuple[list[TempoCandidate], list[str]]:
    if detected_bpm <= 0:
        return [], []

    candidates = [
        ("Half-time", detected_bpm / 2.0),
        ("Detected", detected_bpm),
        ("Double-time", detected_bpm * 2.0),
    ]
    resolved = [
        _score_candidate(label, bpm, beat_times, onset_envelope, onset_times, bpm_min, bpm_max)
        for label, bpm in candidates
        if bpm > 0
    ]
    warnings = []
    strong = [candidate for candidate in resolved if candidate.confidence >= 0.45]
    if len(strong) >= 2:
        warnings.append("Possible half-time/double-time ambiguity.")
    return resolved, warnings


def _score_candidate(
    label: str,
    bpm: float,
    beat_times: np.ndarray,
    onset_envelope: np.ndarray,
    onset_times: np.ndarray,
    bpm_min: float,
    bpm_max: float,
) -> TempoCandidate:
    interval = 60.0 / bpm
    beat_interval_ms = interval * 1000.0
    in_range = bpm_min <= bpm <= bpm_max
    grid_score = _grid_alignment_score(beat_times, interval)
    onset_score = _onset_alignment_score(onset_envelope, onset_times, interval)
    accent_score = _accent_score(onset_envelope, onset_times, interval)
    confidence = float(np.clip((grid_score * 0.40) + (onset_score * 0.35) + (accent_score * 0.25), 0.0, 1.0))
    if not in_range:
        confidence *= 0.92
    return TempoCandidate(
        label=label,
        bpm=float(bpm),
        beat_interval_ms=float(beat_interval_ms),
        grid_alignment_score=float(grid_score),
        onset_alignment_score=float(onset_score),
        accent_score=float(accent_score),
        confidence=confidence,
        in_configured_range=in_range,
    )


def _grid_alignment_score(beat_times: np.ndarray, interval: float) -> float:
    if len(beat_times) < 3 or interval <= 0:
        return 0.0
    phases = ((beat_times - beat_times[0]) % interval) / interval
    distance = np.minimum(phases, 1.0 - phases)
    score = 1.0 - float(np.median(np.clip(distance * 2.0, 0.0, 1.0)))
    return float(np.clip(score, 0.0, 1.0))


def _onset_alignment_score(onset_envelope: np.ndarray, onset_times: np.ndarray, interval: float) -> float:
    if len(onset_envelope) < 4 or len(onset_times) != len(onset_envelope) or interval <= 0:
        return 0.0
    env = np.asarray(onset_envelope, dtype=float)
    if np.max(env) <= 1e-9:
        return 0.0
    phases = ((onset_times - onset_times[0]) % interval) / interval
    distance = np.minimum(phases, 1.0 - phases)
    tolerance = 0.16
    aligned = np.clip(1.0 - (distance / tolerance), 0.0, 1.0)
    weighted = float(np.sum(aligned * env) / max(np.sum(env), 1e-9))
    return float(np.clip(weighted, 0.0, 1.0))


def _accent_score(onset_envelope: np.ndarray, onset_times: np.ndarray, interval: float) -> float:
    if len(onset_envelope) < 4 or len(onset_times) != len(onset_envelope) or interval <= 0:
        return 0.0
    env = np.asarray(onset_envelope, dtype=float)
    if np.max(env) <= 1e-9:
        return 0.0
    phases = ((onset_times - onset_times[0]) % interval) / interval
    downbeat_mask = np.minimum(phases, 1.0 - phases) <= 0.10
    offbeat_mask = np.abs(phases - 0.5) <= 0.10
    if not np.any(downbeat_mask):
        return 0.0
    downbeat_energy = float(np.mean(env[downbeat_mask]))
    offbeat_energy = float(np.mean(env[offbeat_mask])) if np.any(offbeat_mask) else 0.0
    ratio = downbeat_energy / max(downbeat_energy + offbeat_energy, 1e-9)
    return float(np.clip(ratio, 0.0, 1.0))
