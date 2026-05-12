from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "audio" / "fixtures"
GROUND_TRUTH_PATH = FIXTURES_DIR / "ground_truth.json"
REPORT_DIR = REPO_ROOT / "data" / "test_reports"
REPORT_PATH = REPORT_DIR / "bpm_validation_report.md"

os.environ.setdefault("BPM_LIGHT_MAPPER_LOG_LEVEL", "WARNING")
os.environ.setdefault("BPM_LIGHT_MAPPER_CONSOLE_LOG", "0")


def _ensure_repo_on_path() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


@dataclass
class SegmentSummary:
    start: float
    end: float
    bpm: float
    confidence: float
    notes: str = ""


@dataclass
class TestOutcome:
    file_name: str
    description: str
    expected_bpm: float | None
    detected_bpm: float
    abs_error: float | None
    confidence: float
    expected_segments: list[SegmentSummary]
    detected_segments: list[SegmentSummary]
    passed: bool
    notes: list[str]


def _load_ground_truth() -> dict[str, Any]:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(f"Missing ground truth file: {GROUND_TRUTH_PATH}")
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def _load_test_entries(ground_truth: dict[str, Any]) -> list[dict[str, Any]]:
    entries = ground_truth.get("tests", [])
    if not isinstance(entries, list):
        raise ValueError("ground_truth.json: 'tests' must be a list")
    return entries


def _format_bpm(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _format_segments(segments: list[SegmentSummary]) -> str:
    if not segments:
        return "-"
    parts = []
    for seg in segments:
        bits = [
            f"{seg.start:.1f}-{seg.end:.1f}s",
            f"{seg.bpm:.2f} BPM",
        ]
        if seg.confidence >= 0:
            bits.append(f"conf {seg.confidence:.2f}")
        if seg.notes:
            bits.append(seg.notes)
        parts.append(" | ".join(bits))
    return "; ".join(parts)


def _segment_summaries_from_expected(test: dict[str, Any]) -> list[SegmentSummary]:
    segments = []
    for segment in test.get("segments", []):
        bpm = segment.get("bpm")
        if bpm is None and segment.get("bpm_start") is not None and segment.get("bpm_end") is not None:
            bpm = (float(segment["bpm_start"]) + float(segment["bpm_end"])) / 2.0
        segments.append(
            SegmentSummary(
                start=float(segment["start"]),
                end=float(segment["end"]),
                bpm=float(bpm) if bpm is not None else 0.0,
                confidence=-1.0,
                notes=str(segment.get("notes", "")),
            )
        )
    return segments


def _segment_summaries_from_detected(result) -> list[SegmentSummary]:
    summaries: list[SegmentSummary] = []
    for segment in result.segments:
        summaries.append(
            SegmentSummary(
                start=float(segment.start),
                end=float(segment.end),
                bpm=float(segment.bpm),
                confidence=float(segment.confidence),
                notes=str(segment.notes or ""),
            )
        )
    return summaries


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _match_segment(expected: SegmentSummary, detected: list[SegmentSummary]) -> tuple[SegmentSummary | None, float]:
    best = None
    best_score = 0.0
    expected_duration = max(expected.end - expected.start, 1e-9)
    for candidate in detected:
        overlap = _overlap(expected.start, expected.end, candidate.start, candidate.end)
        if overlap <= 0:
            continue
        coverage = overlap / expected_duration
        bpm_score = 1.0 / (1.0 + abs(candidate.bpm - expected.bpm))
        score = coverage * 0.7 + bpm_score * 0.3
        if score > best_score:
            best_score = score
            best = candidate
    return best, best_score


def _is_silence_gap(test: dict[str, Any], start: float, end: float) -> bool:
    active_ranges = [(float(seg["start"]), float(seg["end"])) for seg in test.get("segments", [])]
    if not active_ranges:
        return False
    overlaps_any = any(_overlap(start, end, seg_start, seg_end) > 0 for seg_start, seg_end in active_ranges)
    return not overlaps_any


def _detect_false_segments_in_silence(test: dict[str, Any], detected: list[SegmentSummary]) -> list[SegmentSummary]:
    false_segments = []
    for seg in detected:
        if _is_silence_gap(test, seg.start, seg.end):
            false_segments.append(seg)
    return false_segments


def _evaluate_test(test: dict[str, Any], result) -> TestOutcome:
    expected_bpm = test.get("global_bpm")
    if expected_bpm is None and "alternate_bpm" in test and test.get("alternate_bpm") is not None:
        expected_bpm = test["alternate_bpm"]
    expected_bpm = float(expected_bpm) if expected_bpm is not None else None
    detected_bpm = float(result.bpm_global)
    abs_error = abs(detected_bpm - expected_bpm) if expected_bpm is not None else None
    confidence = float(result.confidence_global)
    expected_segments = _segment_summaries_from_expected(test)
    detected_segments = _segment_summaries_from_detected(result)
    notes: list[str] = []
    passed = True

    file_name = test["file"]
    description = test.get("description", file_name)
    file_lower = file_name.lower()

    if "constant_click_120" in file_lower or "constant_click_128" in file_lower:
        threshold = 0.2
        if abs_error is None or abs_error > threshold:
            passed = False
            notes.append(f"global bpm error above {threshold:.1f} BPM")
    elif "kick_hat" in file_lower:
        threshold = 0.5
        if abs_error is None or abs_error > threshold:
            passed = False
            notes.append(f"global bpm error above {threshold:.1f} BPM")
    elif "tempo_map" in file_lower:
        matches = 0
        for expected_segment in expected_segments:
            matched, score = _match_segment(expected_segment, detected_segments)
            if matched is None:
                continue
            if abs(matched.bpm - expected_segment.bpm) <= 2.0 and score >= 0.55:
                matches += 1
        if matches < 2:
            passed = False
            notes.append(f"only {matches}/3 tempo zones matched")
    elif "silence_breaks" in file_lower:
        false_segments = _detect_false_segments_in_silence(test, detected_segments)
        if false_segments:
            passed = False
            notes.append(f"{len(false_segments)} false segments detected inside silence")
        else:
            notes.append("no false segments detected during silence")
    elif "half_time_70_double_140" in file_lower:
        warning_text = " ".join(result.warnings).lower()
        near_expected = expected_bpm is not None and abs(detected_bpm - expected_bpm) <= 5.0
        near_alternate = False
        alternate_bpm = test.get("alternate_bpm")
        if alternate_bpm is not None:
            near_alternate = abs(detected_bpm - float(alternate_bpm)) <= 5.0
        if "half-time" not in warning_text and "double-time" not in warning_text:
            passed = False
            notes.append("missing half-time/double-time ambiguity warning")
        if not (near_expected or near_alternate):
            passed = False
            notes.append("detected BPM is not near the expected half-time/double-time pair")
    elif "low_onset_pad" in file_lower:
        if confidence >= 0.75:
            passed = False
            notes.append("confidence too high for low-onset pad")
        elif confidence < 0.55:
            notes.append("low confidence as expected")
        else:
            notes.append("moderate confidence on a difficult pad fixture")
    else:
        if expected_bpm is not None and abs_error is not None and abs_error > 1.0:
            notes.append("informational: BPM mismatch above 1.0 BPM")

    if expected_bpm is not None and abs_error is not None:
        if (
            abs_error > 1.0
            and "low_onset_pad" not in file_lower
            and "half_time_70_double_140" not in file_lower
            and "silence_breaks" not in file_lower
            and "tempo_map" not in file_lower
            and "gradual_ramp" not in file_lower
        ):
            passed = False

    if "half_time_70_double_140" in file_lower and expected_bpm is not None:
        if abs_error is not None and abs(detected_bpm - expected_bpm) > 5.0:
            notes.append("global BPM is ambiguous by design")

    return TestOutcome(
        file_name=file_name,
        description=description,
        expected_bpm=expected_bpm,
        detected_bpm=detected_bpm,
        abs_error=abs_error,
        confidence=confidence,
        expected_segments=expected_segments,
        detected_segments=detected_segments,
        passed=passed,
        notes=notes,
    )


def _run_analysis(file_path: Path):
    from bpm_light_mapper.app.audio.offline_analyzer import OfflineAnalysisParameters, analyze_file

    params = OfflineAnalysisParameters()
    return analyze_file(str(file_path), params)


def _render_markdown(outcomes: list[TestOutcome], output_path: Path) -> None:
    lines: list[str] = []
    total = len(outcomes)
    passed = sum(1 for outcome in outcomes if outcome.passed)
    lines.append("# BPM Validation Report")
    lines.append("")
    lines.append(f"- Total tests: {total}")
    lines.append(f"- Passed: {passed}")
    lines.append(f"- Failed: {total - passed}")
    lines.append("")

    lines.append("| File | Expected BPM | Detected BPM | Abs Error | Confidence | Pass |")
    lines.append("| --- | ---: | ---: | ---: | ---: | :---: |")
    for outcome in outcomes:
        lines.append(
            "| {file} | {expected} | {detected} | {error} | {confidence} | {passed} |".format(
                file=outcome.file_name,
                expected=_format_bpm(outcome.expected_bpm),
                detected=f"{outcome.detected_bpm:.2f}",
                error=_format_bpm(outcome.abs_error),
                confidence=f"{outcome.confidence:.2f}",
                passed="PASS" if outcome.passed else "FAIL",
            )
        )
    lines.append("")

    for outcome in outcomes:
        lines.append(f"## {outcome.file_name}")
        lines.append("")
        lines.append(f"- Description: {outcome.description}")
        lines.append(f"- Expected BPM: {_format_bpm(outcome.expected_bpm)}")
        lines.append(f"- Detected BPM: {outcome.detected_bpm:.2f}")
        lines.append(f"- Absolute error: {_format_bpm(outcome.abs_error)}")
        lines.append(f"- Confidence: {outcome.confidence:.2f}")
        lines.append(f"- Result: {'PASS' if outcome.passed else 'FAIL'}")
        if outcome.notes:
            lines.append(f"- Notes: {'; '.join(outcome.notes)}")
        lines.append("")
        lines.append("### Segments")
        lines.append("")
        lines.append(f"- Expected: {_format_segments(outcome.expected_segments)}")
        lines.append(f"- Detected: {_format_segments(outcome.detected_segments)}")
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _print_console_report(outcomes: list[TestOutcome]) -> None:
    print("BPM validation report")
    print("=" * 80)
    for outcome in outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        error = "-" if outcome.abs_error is None else f"{outcome.abs_error:.2f}"
        print(
            f"[{status}] {outcome.file_name} | expected={_format_bpm(outcome.expected_bpm)} "
            f"detected={outcome.detected_bpm:.2f} error={error} conf={outcome.confidence:.2f}"
        )
        if outcome.notes:
            print(f"  notes: {'; '.join(outcome.notes)}")
    passed = sum(1 for outcome in outcomes if outcome.passed)
    print("-" * 80)
    print(f"Passed {passed}/{len(outcomes)} tests")


def main() -> int:
    _ensure_repo_on_path()
    ground_truth = _load_ground_truth()
    tests = _load_test_entries(ground_truth)
    if not FIXTURES_DIR.exists():
        raise FileNotFoundError(f"Missing fixtures directory: {FIXTURES_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    outcomes: list[TestOutcome] = []
    for test in tests:
        file_name = test.get("file")
        if not file_name:
            continue
        file_path = FIXTURES_DIR / file_name
        if not file_path.exists():
            outcomes.append(
                TestOutcome(
                    file_name=file_name,
                    description=test.get("description", file_name),
                    expected_bpm=float(test["global_bpm"]) if test.get("global_bpm") is not None else None,
                    detected_bpm=0.0,
                    abs_error=None,
                    confidence=0.0,
                    expected_segments=_segment_summaries_from_expected(test),
                    detected_segments=[],
                    passed=False,
                    notes=[f"missing file: {file_path}"],
                )
            )
            continue
        _, result = _run_analysis(file_path)
        outcomes.append(_evaluate_test(test, result))

    _render_markdown(outcomes, REPORT_PATH)
    _print_console_report(outcomes)
    print(f"Markdown report written to: {REPORT_PATH}")

    return 0 if all(outcome.passed for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
