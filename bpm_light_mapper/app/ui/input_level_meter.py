from __future__ import annotations

from dataclasses import dataclass
from math import exp
from time import monotonic
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from bpm_light_mapper.app.ui.theme import COLORS


@dataclass(frozen=True)
class InputMeterConfig:
    min_db: float = -60.0
    max_db: float = 0.0
    attack_time: float = 0.010
    release_time: float = 0.280
    peak_hold_time: float = 0.850
    peak_fall_db_per_second: float = 18.0
    clip_threshold_db: float = -0.1
    clip_hold_time: float = 2.0


class InputLevelMeter(QWidget):
    """DAW-style dBFS input meter with RMS ballistics, peak hold and clip latch."""

    def __init__(self, config: InputMeterConfig | None = None) -> None:
        super().__init__()
        self.config = config or InputMeterConfig()
        self.current_rms_db = [self.config.min_db]
        self.current_peak_db = [self.config.min_db]
        self.displayed_level_db = [self.config.min_db]
        self.peak_hold_db = [self.config.min_db]
        self.last_peak_hold_time = [0.0]
        self.clip_active = [False]
        self.last_clip_time = [0.0]
        self._last_frame_time = monotonic()
        self.setMinimumHeight(58)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_levels(self, rms_db: Sequence[float], peak_db: Sequence[float]) -> None:
        now = monotonic()
        dt = max(0.0, now - self._last_frame_time)
        self._last_frame_time = now

        channel_count = max(1, len(rms_db), len(peak_db))
        self._ensure_channels(channel_count)
        for index in range(channel_count):
            rms = float(rms_db[index]) if index < len(rms_db) else self.config.min_db
            peak = float(peak_db[index]) if index < len(peak_db) else self.config.min_db
            rms = max(self.config.min_db, min(self.config.max_db, rms))
            peak = max(self.config.min_db, min(self.config.max_db, peak))
            self.current_rms_db[index] = rms
            self.current_peak_db[index] = peak

            tau = self.config.attack_time if rms > self.displayed_level_db[index] else self.config.release_time
            coeff = 1.0 - exp(-dt / max(0.001, tau))
            self.displayed_level_db[index] += (rms - self.displayed_level_db[index]) * coeff

            if peak >= self.peak_hold_db[index] or now - self.last_peak_hold_time[index] <= 0.001:
                self.peak_hold_db[index] = peak
                self.last_peak_hold_time[index] = now
            elif now - self.last_peak_hold_time[index] > self.config.peak_hold_time:
                self.peak_hold_db[index] = max(
                    peak,
                    self.peak_hold_db[index] - (self.config.peak_fall_db_per_second * dt),
                )

            if peak >= self.config.clip_threshold_db:
                self.clip_active[index] = True
                self.last_clip_time[index] = now
            elif now - self.last_clip_time[index] > self.config.clip_hold_time:
                self.clip_active[index] = False

        self.update()

    def reset_clip(self) -> None:
        self.clip_active = [False for _ in self.clip_active]
        self.last_clip_time = [0.0 for _ in self.last_clip_time]
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.reset_clip()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(4, 3, -4, -3)
        painter.fillRect(rect, QColor("#071018"))
        painter.setPen(QPen(QColor(COLORS["panel_edge"]), 1))
        painter.drawRoundedRect(rect, 4, 4)

        channels = len(self.displayed_level_db)
        label_width = 18 if channels > 1 else 0
        value_width = 110
        clip_width = 34
        meter_left = rect.left() + label_width + 8
        meter_right = rect.right() - value_width - clip_width - 8
        meter_width = max(10, meter_right - meter_left)
        row_gap = 5
        tick_height = 12
        row_height = max(10, int((rect.height() - tick_height - row_gap * (channels - 1)) / max(1, channels)))

        self._draw_ticks(painter, meter_left, meter_width, rect.bottom() - tick_height + 2)
        for index in range(channels):
            top = rect.top() + index * (row_height + row_gap)
            self._draw_channel(painter, index, meter_left, top, meter_width, row_height, value_width, clip_width)

    def _draw_channel(
        self,
        painter: QPainter,
        index: int,
        left: int,
        top: int,
        width: int,
        height: int,
        value_width: int,
        clip_width: int,
    ) -> None:
        if len(self.displayed_level_db) > 1:
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(6, top, 18, height, Qt.AlignVCenter | Qt.AlignLeft, "L" if index == 0 else "R")

        bg_rect = self._rect_tuple(left, top, width, height)
        painter.fillRect(*bg_rect, QColor("#0b151e"))
        self._draw_zone(painter, left, top, width, height, self.config.min_db, -18.0, QColor("#123a2a"))
        self._draw_zone(painter, left, top, width, height, -18.0, -6.0, QColor("#4a3811"))
        self._draw_zone(painter, left, top, width, height, -6.0, self.config.max_db, QColor("#4a1520"))

        fill_width = int(width * self._db_to_unit(self.displayed_level_db[index]))
        if fill_width > 0:
            painter.fillRect(left, top, fill_width, height, self._level_color(self.displayed_level_db[index]))

        peak_x = left + int(width * self._db_to_unit(self.current_peak_db[index]))
        painter.setPen(QPen(QColor("#e8f0f6"), 1))
        painter.drawLine(peak_x, top + 2, peak_x, top + height - 2)

        hold_x = left + int(width * self._db_to_unit(self.peak_hold_db[index]))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(hold_x, top, hold_x, top + height)

        painter.setPen(QPen(QColor("#1f3342"), 1))
        painter.drawRect(left, top, width, height)

        value_left = left + width + 8
        painter.setPen(QColor(COLORS["muted"]))
        painter.drawText(
            value_left,
            top,
            value_width,
            height,
            Qt.AlignVCenter | Qt.AlignLeft,
            f"RMS {self.displayed_level_db[index]:5.1f}  PK {self.current_peak_db[index]:5.1f}",
        )

        clip_left = value_left + value_width
        clip_color = QColor(COLORS["red"] if self.clip_active[index] else "#1a2630")
        painter.setBrush(clip_color)
        painter.setPen(QPen(QColor("#6c2533" if self.clip_active[index] else COLORS["panel_edge"]), 1))
        painter.drawRoundedRect(clip_left, top + 1, clip_width - 2, height - 2, 3, 3)
        painter.setPen(QColor("#fff4f6" if self.clip_active[index] else "#526170"))
        painter.drawText(clip_left, top, clip_width - 2, height, Qt.AlignCenter, "CLIP")

    def _draw_ticks(self, painter: QPainter, left: int, width: int, y: int) -> None:
        ticks = [-60, -48, -36, -24, -18, -12, -6, -3, 0]
        painter.setPen(QColor("#536879"))
        for tick in ticks:
            x = left + int(width * self._db_to_unit(float(tick)))
            painter.drawLine(x, y, x, y + 4)
            label = "0" if tick == 0 else str(tick)
            painter.drawText(x - 14, y + 4, 28, 10, Qt.AlignCenter, label)

    def _draw_zone(
        self,
        painter: QPainter,
        left: int,
        top: int,
        width: int,
        height: int,
        start_db: float,
        end_db: float,
        color: QColor,
    ) -> None:
        x1 = left + int(width * self._db_to_unit(start_db))
        x2 = left + int(width * self._db_to_unit(end_db))
        painter.fillRect(x1, top, max(1, x2 - x1), height, color)

    def _level_color(self, db: float) -> QColor:
        if db >= -6.0:
            return QColor(COLORS["red"])
        if db >= -18.0:
            return QColor(COLORS["orange"])
        return QColor(COLORS["green"])

    def _db_to_unit(self, db: float) -> float:
        value = (db - self.config.min_db) / (self.config.max_db - self.config.min_db)
        return max(0.0, min(1.0, value))

    def _ensure_channels(self, channel_count: int) -> None:
        current = len(self.displayed_level_db)
        if channel_count <= current:
            return
        extra = channel_count - current
        self.current_rms_db.extend([self.config.min_db] * extra)
        self.current_peak_db.extend([self.config.min_db] * extra)
        self.displayed_level_db.extend([self.config.min_db] * extra)
        self.peak_hold_db.extend([self.config.min_db] * extra)
        self.last_peak_hold_time.extend([0.0] * extra)
        self.clip_active.extend([False] * extra)
        self.last_clip_time.extend([0.0] * extra)

    @staticmethod
    def _rect_tuple(left: int, top: int, width: int, height: int) -> tuple[int, int, int, int]:
        return left, top, width, height
