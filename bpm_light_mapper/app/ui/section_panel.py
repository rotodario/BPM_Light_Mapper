from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class SectionPanel(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("SectionPanel")
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("PanelTitle")
        self.body = QVBoxLayout()
        self.body.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addLayout(self.body)
