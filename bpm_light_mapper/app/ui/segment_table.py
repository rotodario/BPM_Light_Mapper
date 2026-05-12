from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from bpm_light_mapper.app.models.segment import Segment


class SegmentTable(QTableWidget):
    segments_changed = Signal()
    selection_changed = Signal(int)

    HEADERS = ["Start", "End", "BPM", "Confidence", "Confirmado", "Notas"]

    def __init__(self) -> None:
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.itemChanged.connect(self._on_item_changed)
        self.currentCellChanged.connect(self._on_selection_changed)
        self._segments: list[Segment] = []
        self._loading = False

    def load_segments(self, segments: list[Segment]) -> None:
        self._loading = True
        self._segments = segments
        self.setRowCount(len(segments))
        for row, segment in enumerate(segments):
            self._set_row(row, segment)
        self._loading = False
        self.resizeColumnsToContents()

    def _set_row(self, row: int, segment: Segment) -> None:
        values = [
            f"{segment.start:.3f}",
            f"{segment.end:.3f}",
            f"{segment.bpm:.2f}",
            f"{segment.confidence:.3f}",
            "1" if segment.confirmed else "0",
            segment.notes,
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 3:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, col, item)

    def selected_row(self) -> int:
        return self.currentRow()

    def _on_selection_changed(self, current_row: int, current_column: int, prev_row: int, prev_column: int) -> None:
        del current_column, prev_row, prev_column
        self.selection_changed.emit(current_row)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        row = item.row()
        if row < 0 or row >= len(self._segments):
            return
        segment = self._segments[row]
        try:
            segment.start = float(self.item(row, 0).text())
            segment.end = float(self.item(row, 1).text())
            segment.bpm = float(self.item(row, 2).text())
            segment.confirmed = self.item(row, 4).text().strip() in {"1", "true", "True", "yes", "YES"}
            segment.notes = self.item(row, 5).text()
        except (ValueError, AttributeError):
            return
        self.segments_changed.emit()
