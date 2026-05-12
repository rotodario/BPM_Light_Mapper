from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from bpm_light_mapper.app.models.segment import Segment


class WaveformWidget(QWidget):
    segment_selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(y=False)
        self.plot.setLabel("bottom", "Tiempo", units="s")
        self.plot.setLabel("left", "Amplitud")
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot)
        self.wave_curve = self.plot.plot([], [], pen=pg.mkPen("#6fa8dc", width=1))
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
            line = pg.InfiniteLine(pos=beat, angle=90, pen=pg.mkPen((255, 180, 0, 90), width=1))
            self.plot.addItem(line)
            self.beat_lines.append(line)

    def set_segments(self, segments: list[Segment]) -> None:
        for region in self.segment_regions:
            self.plot.removeItem(region)
        self.segment_regions.clear()
        colors = [
            (0, 140, 255, 40),
            (0, 200, 120, 40),
            (255, 170, 0, 40),
            (255, 80, 80, 40),
        ]
        for idx, segment in enumerate(segments):
            color = colors[idx % len(colors)]
            region = pg.LinearRegionItem(
                values=(segment.start, segment.end),
                movable=False,
                brush=pg.mkBrush(color),
                pen=pg.mkPen(color[:3], width=1),
            )
            region.lines[0].sigPositionChanged.connect(lambda _, i=idx: self.segment_selected.emit(i))
            region.lines[1].sigPositionChanged.connect(lambda _, i=idx: self.segment_selected.emit(i))
            self.plot.addItem(region)
            self.segment_regions.append(region)

    def highlight_segment(self, index: int) -> None:
        for idx, region in enumerate(self.segment_regions):
            alpha = 90 if idx == index else 35
            brush = region.brush
            color = brush.color()
            color.setAlpha(alpha)
            region.setBrush(color)

    def clear_overlays(self) -> None:
        self.set_beats([])
        self.set_segments([])
