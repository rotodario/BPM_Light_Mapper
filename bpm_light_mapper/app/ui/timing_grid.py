from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel


class TimingGrid(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TimingGrid")
        self.mult_labels: dict[str, QLabel] = {}
        self.div_labels: dict[str, QLabel] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)
        mult_header = QLabel("BPM x")
        mult_header.setObjectName("MetricTitle")
        div_header = QLabel("BPM /")
        div_header.setObjectName("MetricTitle")
        layout.addWidget(QLabel(""), 0, 0)
        layout.addWidget(mult_header, 0, 1)
        layout.addWidget(div_header, 0, 2)
        for row, key in enumerate(["1x", "2x", "4x", "8x", "16x"], start=1):
            name = QLabel(key)
            name.setObjectName("MetricTitle")
            mult_value = QLabel("-")
            mult_value.setObjectName("MetricValueSmall")
            div_value = QLabel("-")
            div_value.setObjectName("MetricValueSmall")
            layout.addWidget(name, row, 0)
            layout.addWidget(mult_value, row, 1)
            layout.addWidget(div_value, row, 2)
            self.mult_labels[key] = mult_value
            self.div_labels[key] = div_value

    def set_beat_ms(self, beat_ms: float) -> None:
        if beat_ms <= 0:
            for label in self.mult_labels.values():
                label.setText("-")
            for label in self.div_labels.values():
                label.setText("-")
            return
        base_bpm = 60000.0 / beat_ms if beat_ms > 0 else 0.0
        for key, factor in {"1x": 1, "2x": 2, "4x": 4, "8x": 8, "16x": 16}.items():
            mult_bpm = base_bpm * factor if base_bpm > 0 else 0.0
            div_bpm = base_bpm / factor if base_bpm > 0 else 0.0
            self.mult_labels[key].setText(f"{mult_bpm:.2f} BPM")
            self.div_labels[key].setText(f"{div_bpm:.2f} BPM")
