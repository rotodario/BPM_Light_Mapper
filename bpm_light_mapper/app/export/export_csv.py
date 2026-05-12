from __future__ import annotations

import csv

from bpm_light_mapper.app.models.analysis_result import AnalysisResult


def export_segments_csv(result: AnalysisResult, output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["start_seconds", "end_seconds", "bpm", "confidence", "confirmed", "notes"])
        for segment in result.segments:
            writer.writerow(
                [
                    f"{segment.start:.3f}",
                    f"{segment.end:.3f}",
                    f"{segment.bpm:.2f}",
                    f"{segment.confidence:.3f}",
                    int(segment.confirmed),
                    segment.notes,
                ]
            )


def export_segments_txt(result: AnalysisResult, output_path: str) -> None:
    from bpm_light_mapper.app.utils.time_format import seconds_to_timestamp

    with open(output_path, "w", encoding="utf-8") as handle:
        for segment in result.segments:
            note = segment.notes or "-"
            handle.write(
                f"{seconds_to_timestamp(segment.start)} - {seconds_to_timestamp(segment.end)} | "
                f"{segment.bpm:.2f} BPM | {note}\n"
            )
