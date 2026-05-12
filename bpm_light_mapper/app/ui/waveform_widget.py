from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from bpm_light_mapper.app.models.segment import Segment
from bpm_light_mapper.app.ui.theme import COLORS


class WaveformWidget(QWidget):
    segment_selected = Signal(int)
    seek_requested = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.duration = 0.0
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
        self.segment_labels: list[pg.TextItem] = []
        self.playhead = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(COLORS["red"], width=2))
        self.playhead.setZValue(50)
        self.plot.addItem(self.playhead)
        self.plot.scene().sigMouseClicked.connect(self._on_plot_clicked)

    def set_waveform(self, waveform: np.ndarray, duration: float) -> None:
        self.duration = max(0.0, float(duration))
        self.clear_overlays()
        if len(waveform) == 0 or duration <= 0:
            self.wave_curve.setData([], [])
            self.set_playhead(0.0)
            return
        target_points = min(5000, len(waveform))
        indices = np.linspace(0, len(waveform) - 1, target_points, dtype=int)
        times = np.linspace(0.0, duration, target_points)
        self.wave_curve.setData(times, waveform[indices])
        self.plot.setXRange(0.0, duration, padding=0.01)
        self.set_playhead(0.0)

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
        for label in self.segment_labels:
            self.plot.removeItem(label)
        self.segment_regions.clear()
        self.segment_labels.clear()
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
            label = pg.TextItem(
                text=f"{segment.bpm:.1f} BPM",
                color=COLORS["text"],
                anchor=(0.5, 0.5),
                fill=pg.mkBrush(5, 10, 15, 185),
                border=pg.mkPen(color[:3], width=1),
            )
            label.setPos((segment.start + segment.end) / 2.0, 0.72)
            label.setZValue(40)
            self.plot.addItem(label)
            self.segment_labels.append(label)

    def highlight_segment(self, index: int) -> None:
        for idx, region in enumerate(self.segment_regions):
            alpha = 110 if idx == index else 34
            brush = region.brush
            color = brush.color()
            color.setAlpha(alpha)
            region.setBrush(color)
            pen_color = color
            pen_color.setAlpha(220 if idx == index else 115)
            pen = pg.mkPen(pen_color, width=2 if idx == index else 1)
            for line in region.lines:
                line.setPen(pen)
            if idx < len(self.segment_labels):
                self.segment_labels[idx].setColor(COLORS["cyan"] if idx == index else COLORS["text"])

    def clear_overlays(self) -> None:
        self.set_beats([])
        self.set_segments([])

    def set_playhead(self, seconds: float) -> None:
        self.playhead.setPos(max(0.0, min(float(seconds), self.duration)))

    def _on_plot_clicked(self, event) -> None:
        if self.duration <= 0:
            return
        if not self.plot.sceneBoundingRect().contains(event.scenePos()):
            return
        mouse_point = self.plot.plotItem.vb.mapSceneToView(event.scenePos())
        seconds = max(0.0, min(float(mouse_point.x()), self.duration))
        self.set_playhead(seconds)
        self.seek_requested.emit(seconds)
