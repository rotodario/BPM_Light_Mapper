from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel


class TimingGrid(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TimingGrid")
        self.labels: dict[str, QLabel] = {}
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)
        for row, key in enumerate(["1/1", "1/2", "1/4", "1/8", "1/16"]):
            name = QLabel(key)
            name.setObjectName("MetricTitle")
            value = QLabel("-")
            value.setObjectName("MetricValueSmall")
            layout.addWidget(name, row, 0)
            layout.addWidget(value, row, 1)
            self.labels[key] = value

    def set_beat_ms(self, beat_ms: float) -> None:
        if beat_ms <= 0:
            for label in self.labels.values():
                label.setText("-")
            return
        self.labels["1/1"].setText(f"{beat_ms:.2f} ms")
        self.labels["1/2"].setText(f"{beat_ms / 2:.2f} ms")
        self.labels["1/4"].setText(f"{beat_ms / 4:.2f} ms")
        self.labels["1/8"].setText(f"{beat_ms / 8:.2f} ms")
        self.labels["1/16"].setText(f"{beat_ms / 16:.2f} ms")
