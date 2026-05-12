from __future__ import annotations

from PySide6.QtWidgets import QLabel

from bpm_light_mapper.app.ui.theme import COLORS


STATUS_COLORS = {
    "IDLE": COLORS["muted"],
    "LOADING": COLORS["blue"],
    "ANALYZING": COLORS["yellow"],
    "LIVE": COLORS["green"],
    "ERROR": COLORS["red"],
    "SEARCHING": COLORS["yellow"],
    "UNSTABLE": COLORS["orange"],
    "LOCKED": COLORS["green"],
    "MANUAL LOCK": COLORS["cyan"],
}


class StatusBadge(QLabel):
    def __init__(self, text: str = "IDLE") -> None:
        super().__init__()
        self.setObjectName("StatusBadge")
        self.set_status(text)

    def set_status(self, text: str) -> None:
        normalized = text.upper().replace("-", " ")
        color = STATUS_COLORS.get(normalized, COLORS["muted"])
        self.setText(normalized)
        self.setStyleSheet(f"background: {color}; color: #061015;")
