from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev
from typing import Any

from bpm_light_mapper.app.light_mood.lighting_palette_engine import LightingRecipe, recipe_for_mood
from bpm_light_mapper.app.models.analysis_result import AnalysisResult


@dataclass(frozen=True)
class MoodFeatures:
    bpm: float
    bpm_confidence: float
    rms_energy: float
    transient_level: float
    tempo_stability: float
    brightness: float
    key: str = "unknown"
    mode: str = "unknown"


@dataclass(frozen=True)
class LightMoodRecommendation:
    mood: str
    confidence: float
    explanation: str
    recipe: LightingRecipe
    features: MoodFeatures


def analyze_light_mood(result: AnalysisResult, audio: dict[str, Any] | None = None) -> LightMoodRecommendation:
    features = _extract_features(result, audio)
    mood, base_confidence, reasons = _classify_mood(features)
    confidence = _clamp(base_confidence * (0.55 + (features.bpm_confidence * 0.45)), 0.2, 0.95)
    explanation = _build_explanation(features, reasons)
    return LightMoodRecommendation(
        mood=mood,
        confidence=confidence,
        explanation=explanation,
        recipe=recipe_for_mood(mood),
        features=features,
    )


def _extract_features(result: AnalysisResult, audio: dict[str, Any] | None) -> MoodFeatures:
    waveform = audio.get("waveform") if audio else None
    rms_energy = _audio_rms_energy(audio, waveform)
    transient_level = _transient_level(result.onset_envelope)
    tempo_stability = _tempo_stability(result)
    brightness = _brightness_proxy(waveform, transient_level)
    return MoodFeatures(
        bpm=max(0.0, float(result.bpm_global)),
        bpm_confidence=_clamp(float(result.confidence_global), 0.0, 1.0),
        rms_energy=rms_energy,
        transient_level=transient_level,
        tempo_stability=tempo_stability,
        brightness=brightness,
    )


def _classify_mood(features: MoodFeatures) -> tuple[str, float, list[str]]:
    bpm = features.bpm
    energy = features.rms_energy
    transient = features.transient_level
    stability = features.tempo_stability
    brightness = features.brightness
    reasons: list[str] = []

    if bpm < 80 and energy < 0.30 and transient < 0.35:
        reasons.extend(["BPM lento", "energia baja", "pocos transitorios"])
        return "Calm", 0.78, reasons
    if bpm < 95 and brightness < 0.38 and energy >= 0.30:
        reasons.extend(["tempo contenido", "color espectral oscuro", "energia media"])
        return "Dark", 0.72, reasons
    if bpm >= 145 and energy > 0.58 and transient > 0.58:
        reasons.extend(["BPM alto", "energia alta", "transitorios marcados"])
        return "Aggressive", 0.82, reasons
    if bpm >= 124 and energy > 0.48 and brightness > 0.52 and stability > 0.62:
        reasons.extend(["pulso estable", "brillo alto", "energia de pista"])
        return "Euphoric", 0.80, reasons
    if 92 <= bpm <= 124 and transient > 0.48 and stability > 0.58:
        reasons.extend(["BPM medio", "groove estable", "ataques ritmicos claros"])
        return "Groove", 0.76, reasons
    if bpm < 92 and 0.28 <= energy <= 0.58 and brightness >= 0.42:
        reasons.extend(["tempo moderado", "energia controlada", "brillo suave"])
        return "Romantic", 0.68, reasons
    if energy > 0.62 and stability < 0.55:
        reasons.extend(["energia alta", "tempo menos estable", "sensacion de empuje"])
        return "Dramatic", 0.70, reasons
    if transient > 0.62 and brightness < 0.45:
        reasons.extend(["transitorios fuertes", "brillo bajo", "contraste ritmico"])
        return "Tension", 0.72, reasons
    if energy < 0.24 and transient < 0.42:
        reasons.extend(["energia reducida", "textura contenida"])
        return "Minimal", 0.74, reasons
    if bpm >= 118 and energy > 0.50:
        reasons.extend(["BPM elevado", "energia sostenida"])
        return "Epic", 0.68, reasons

    reasons.extend(["BPM medio", "energia equilibrada"])
    return "Groove", 0.58, reasons


def _sampled_rms(values: Any, max_samples: int = 20000) -> float:
    samples = _sample(values, max_samples)
    if not samples:
        return 0.0
    return _clamp(sqrt(sum(float(x) * float(x) for x in samples) / len(samples)), 0.0, 1.0)


def _audio_rms_energy(audio: dict[str, Any] | None, waveform: Any) -> float:
    if audio is not None:
        try:
            value = float(audio.get("rms_energy", 0.0))
            if value > 0.0:
                return _clamp(value, 0.0, 1.0)
        except (TypeError, ValueError):
            pass
    return _sampled_rms(waveform)


def _transient_level(onset_envelope: list[float], max_samples: int = 8000) -> float:
    values = _sample(onset_envelope, max_samples)
    if not values:
        return 0.0
    avg = mean(abs(float(x)) for x in values)
    peak = max(abs(float(x)) for x in values) or 1.0
    return _clamp((avg / peak) * 2.4, 0.0, 1.0)


def _tempo_stability(result: AnalysisResult) -> float:
    bpms = [float(segment.bpm) for segment in result.segments if segment.bpm > 0.0]
    if len(bpms) >= 2:
        avg = mean(bpms)
        if avg > 0.0:
            return _clamp(1.0 - (pstdev(bpms) / avg) * 4.0, 0.0, 1.0)
    beats = [float(value) for value in result.beat_times]
    if len(beats) >= 4:
        intervals = [right - left for left, right in zip(beats, beats[1:]) if right > left]
        if len(intervals) >= 3:
            avg = mean(intervals)
            if avg > 0.0:
                return _clamp(1.0 - (pstdev(intervals) / avg) * 5.0, 0.0, 1.0)
    return _clamp(result.confidence_global, 0.0, 1.0)


def _brightness_proxy(values: Any, transient_level: float, max_samples: int = 16000) -> float:
    samples = _sample(values, max_samples)
    if len(samples) < 3:
        return _clamp(0.35 + transient_level * 0.35, 0.0, 1.0)
    diffs = [abs(float(right) - float(left)) for left, right in zip(samples, samples[1:])]
    avg_diff = mean(diffs) if diffs else 0.0
    return _clamp((avg_diff * 3.0) + (transient_level * 0.45), 0.0, 1.0)


def _sample(values: Any, max_samples: int) -> list[float]:
    if values is None:
        return []
    try:
        count = len(values)
    except TypeError:
        return []
    if count <= 0:
        return []
    step = max(1, count // max_samples)
    return [float(values[index]) for index in range(0, count, step)]


def _build_explanation(features: MoodFeatures, reasons: list[str]) -> str:
    reason_text = ", ".join(reasons[:3]) if reasons else "datos ritmicos disponibles"
    key_text = "tonalidad desconocida" if features.key == "unknown" else f"tonalidad {features.key}"
    mode_text = "modo desconocido" if features.mode == "unknown" else f"modo {features.mode}"
    return (
        f"{reason_text}; {key_text} y {mode_text}. "
        f"BPM {features.bpm:.1f}, estabilidad {features.tempo_stability:.0%}, "
        f"energia {features.rms_energy:.0%}."
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
