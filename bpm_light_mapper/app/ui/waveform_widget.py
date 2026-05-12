from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from bpm_light_mapper.app.models.segment import Segment
from bpm_light_mapper.app.ui.theme import COLORS


class WaveformWidget(QWidget):
    segment_selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.plot = pg.PlotWidget()
        self.plot.setBackground(COLORS["bg"])
        self.plot.showGrid(x=True, y=True, alpha=0.16)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(y=False)
        self.plot.setLabel("bottom", "Tiempo", units="s")
        self.plot.setLabel("left", "Amplitud")
        self.plot.getAxis("bottom").setPen(pg.mkPen("#41566a"))
        self.plot.getAxis("left").setPen(pg.mkPen("#41566a"))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(COLORS["muted"]))
        self.plot.getAxis("left").setTextPen(pg.mkPen(COLORS["muted"]))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.wave_curve = self.plot.plot([], [], pen=pg.mkPen(COLORS["cyan"], width=1.2))
        self.beat_lines: list[pg.InfiniteLine] = []
        self.segment_regions: list[pg.LinearRegionItem] = []

    def set_waveform(self, waveform: np.ndarray, duration: float) -> None:
        self.clear_overlays()
        if len(waveform) == 0 or duration <= 0:
            self.wave_curve.setData([], [])
            return
        target_points = min(5000, len(waveform))
        indices = np.linspace(0, len(waveform) - 1, target_points, dtype=int)
        times = np.linspace(0.0, duration, target_points)
        self.wave_curve.setData(times, waveform[indices])
        self.plot.setXRange(0.0, duration, padding=0.01)

    def set_beats(self, beat_times: list[float]) -> None:
        for line in self.beat_lines:
            self.plot.removeItem(line)
        self.beat_lines.clear()
        for beat in beat_times:
            line = pg.InfiniteLine(pos=beat, angle=90, pen=pg.mkPen((247, 201, 72, 105), width=1))
            self.plot.addItem(line)
            self.beat_lines.append(line)

    def set_segments(self, segments: list[Segment]) -> None:
        for region in self.segment_regions:
            self.plot.removeItem(region)
        self.segment_regions.clear()
        colors = [
            (40, 215, 255, 42),
            (57, 255, 136, 38),
            (247, 201, 72, 38),
            (177, 140, 255, 38),
            (255, 159, 67, 36),
        ]
        for idx, segment in enumerate(segments):
            color = colors[idx % len(colors)]
            region = pg.LinearRegionItem(
                values=(segment.start, segment.end),
                movable=False,
                brush=pg.mkBrush(color),
                pen=pg.mkPen(color[:3], width=1.2),
            )
            region.lines[0].sigPositionChanged.connect(lambda _, i=idx: self.segment_selected.emit(i))
            region.lines[1].sigPositionChanged.connect(lambda _, i=idx: self.segment_selected.emit(i))
            self.plot.addItem(region)
            self.segment_regions.append(region)

    def highlight_segment(self, index: int) -> None:
        for idx, region in enumerate(self.segment_regions):
            alpha = 110 if idx == index else 34
            brush = region.brush
            color = brush.color()
            color.setAlpha(alpha)
            region.setBrush(color)
            pen_color = color
            pen_color.setAlpha(220 if idx == index else 115)
            region.setPen(pg.mkPen(pen_color, width=2 if idx == index else 1))

    def clear_overlays(self) -> None:
        self.set_beats([])
        self.set_segments([])
