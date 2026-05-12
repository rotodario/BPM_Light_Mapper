from __future__ import annotations

import json

from bpm_light_mapper.app.models.analysis_result import AnalysisResult


def export_analysis_json(result: AnalysisResult, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)
