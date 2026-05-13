from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from bpm_light_mapper.app.ui.theme import COLORS


class MetronomeIndicator(QFrame):
    """Compact HUD-style visual metronome.

    The widget does not generate audio. It only exposes a clear visual pulse so
    the operator can validate the detected beat grid without adding latency or
    sound-device complexity.
    """

    def __init__(self, title: str = "METRONOMO") -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.pulse_label = QLabel("")
        self.pulse_label.setFixedSize(24, 24)
        self.pulse_label.setAlignment(Qt.AlignCenter)
        self.beat_label = QLabel("-")
        self.beat_label.setObjectName("MetricValueSmall")
        self.detail_label = QLabel("sin clock")
        self.detail_label.setObjectName("MetricSubtitle")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.pulse_label)
        row.addWidget(self.beat_label, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addLayout(row)
        layout.addWidget(self.detail_label)

        self.set_active(False)

    def set_active(self, active: bool, beat: str = "-", detail: str = "sin clock", phase: float = 1.0) -> None:
        self.beat_label.setText(beat)
        self.detail_label.setText(detail)
        if not active:
            self._set_pulse_style(COLORS["muted"], 0.18)
            return
        phase = max(0.0, min(float(phase), 1.0))
        intensity = max(0.20, 1.0 - (phase * 1.65))
        self._set_pulse_style(COLORS["green"] if phase < 0.18 else COLORS["cyan"], intensity)

    def _set_pulse_style(self, color: str, intensity: float) -> None:
        alpha = int(max(0.12, min(intensity, 1.0)) * 255)
        self.pulse_label.setStyleSheet(
            f"""
            background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {alpha});
            border: 1px solid {color};
            border-radius: 12px;
            """
        )
