from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import soundfile as sf

from bpm_light_mapper.app.audio.offline_analyzer import OfflineAnalysisParameters, analyze_file


TEST_SR = 22050
OUT_DIR = Path(__file__).resolve().parents[3] / "synthetic_test_output"


def click_track(bpm: float, duration: float, sr: int = TEST_SR, accents: bool = True) -> np.ndarray:
    samples = int(duration * sr)
    signal = np.zeros(samples, dtype=np.float32)
    interval = int((60.0 / bpm) * sr)
    click = np.hanning(256).astype(np.float32)
    for i, start in enumerate(range(0, samples - len(click), interval)):
        amp = 1.0 if not accents or i % 4 else 1.5
        signal[start : start + len(click)] += click * amp
    peak = max(np.max(np.abs(signal)), 1e-9)
    return signal / peak


def concat_segments(bpms: list[float], durations: list[float], silence_between: float = 0.0) -> np.ndarray:
    parts = []
    for bpm, duration in zip(bpms, durations):
        parts.append(click_track(bpm, duration))
        if silence_between > 0:
            parts.append(np.zeros(int(silence_between * TEST_SR), dtype=np.float32))
    return np.concatenate(parts)


def half_time_pattern(base_bpm: float, duration: float) -> np.ndarray:
    samples = int(duration * TEST_SR)
    signal = np.zeros(samples, dtype=np.float32)
    interval = int((60.0 / base_bpm) * TEST_SR)
    click = np.hanning(256).astype(np.float32)
    for i, start in enumerate(range(0, samples - len(click), interval)):
        if i % 2 == 0:
            signal[start : start + len(click)] += click * 1.2
        else:
            signal[start : start + len(click)] += click * 0.35
    peak = max(np.max(np.abs(signal)), 1e-9)
    return signal / peak


def write_case(name: str, audio: np.ndarray) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{name}.wav"
    sf.write(path, audio, TEST_SR)
    return path


def evaluate_case(name: str, expected_bpms: list[float], expected_segments: int) -> dict:
    params = OfflineAnalysisParameters()
    _, result = analyze_file(str(OUT_DIR / f"{name}.wav"), params)
    segment_bpms = [round(segment.bpm, 2) for segment in result.segments]
    bpm_error = min(abs(result.bpm_global - bpm) for bpm in expected_bpms)
    return {
        "case": name,
        "expected_bpms": expected_bpms,
        "detected_global_bpm": round(result.bpm_global, 2),
        "global_bpm_error": round(float(bpm_error), 2),
        "expected_segments": expected_segments,
        "detected_segments": len(result.segments),
        "segment_bpms": segment_bpms,
        "warnings": result.warnings,
    }


def main() -> None:
    cases = {
        "click_120": (click_track(120, 30.0), [120.0], 1),
        "click_128": (click_track(128, 30.0), [128.0], 1),
        "tempo_changes": (concat_segments([120, 128, 124], [20, 20, 20]), [120.0, 128.0, 124.0], 3),
        "silences": (concat_segments([122, 122], [15, 15], silence_between=3.0), [122.0], 1),
        "half_time": (half_time_pattern(140, 30.0), [70.0, 140.0], 1),
    }

    for name, (audio, _, _) in cases.items():
        write_case(name, audio)

    report = []
    for name, (_, expected_bpms, expected_segments) in cases.items():
        report.append(evaluate_case(name, expected_bpms, expected_segments))

    summary = {
        "report": report,
        "mean_global_error": round(
            float(np.mean([entry["global_bpm_error"] for entry in report])),
            2,
        ),
    }
    report_path = OUT_DIR / "report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
