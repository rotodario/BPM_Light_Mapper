from __future__ import annotations

from dataclasses import dataclass
from math import exp
from time import monotonic
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from bpm_light_mapper.app.ui.theme import COLORS


@dataclass(frozen=True)
class LedBallistics:
    attack_time: float = 0.012
    decay_time: float = 0.16
    glow_amount: float = 1.0
    accent_color: str = COLORS["yellow"]
    normal_beat_color: str = COLORS["green"]
    idle_color: str = "#16212b"


class BallisticLed(QWidget):
    """Painted LED with meter-style attack/release ballistics."""

    def __init__(self, config: Optional[LedBallistics] = None) -> None:
        super().__init__()
        self.config = config or LedBallistics()
        self.led_intensity = 0.0
        self._target_intensity = 0.0
        self._last_beat_time: Optional[float] = None
        self._last_frame_time = monotonic()
        self._beat_interval = 0.5
        self._is_accent = False
        self._active = False
        self.setFixedSize(30, 30)

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(16)
        self._frame_timer.timeout.connect(self._render_frame)
        self._frame_timer.start()

    def trigger(
        self,
        beat_interval: Optional[float] = None,
        accent: bool = False,
        event_time: Optional[float] = None,
    ) -> None:
        self._active = True
        self._is_accent = accent
        if beat_interval is not None and beat_interval > 0.0:
            self._beat_interval = beat_interval
        self._last_beat_time = event_time if event_time is not None else monotonic()
        self._target_intensity = 1.0
        self.led_intensity = max(self.led_intensity, 0.92)
        self.update()

    def set_idle(self) -> None:
        self._active = False
        self._target_intensity = 0.0
        self._last_beat_time = None

    def _render_frame(self) -> None:
        now = monotonic()
        dt = max(0.0, now - self._last_frame_time)
        self._last_frame_time = now

        if self._active and self._last_beat_time is not None:
            elapsed = max(0.0, now - self._last_beat_time)
            decay_time = min(self.config.decay_time, max(0.045, self._beat_interval * 0.35))
            self._target_intensity = exp(-elapsed / decay_time)
        else:
            self._target_intensity = 0.0

        if self._target_intensity > self.led_intensity:
            coeff = 1.0 - exp(-dt / max(0.001, self.config.attack_time))
        else:
            coeff = 1.0 - exp(-dt / 0.055)
        self.led_intensity += (self._target_intensity - self.led_intensity) * coeff

        if not self._active and self.led_intensity < 0.01:
            self.led_intensity = 0.0

        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        intensity = max(0.0, min(self.led_intensity, 1.0))
        base = QColor(self.config.accent_color if self._is_accent else self.config.normal_beat_color)
        idle = QColor(self.config.idle_color)
        size = min(self.width(), self.height())
        center = self.rect().center()
        radius = size * 0.34

        glow_alpha = int(150 * intensity * self.config.glow_amount)
        if glow_alpha > 0:
            glow = QRadialGradient(center, size * 0.50)
            glow_color = QColor(base)
            glow_color.setAlpha(glow_alpha)
            transparent = QColor(base)
            transparent.setAlpha(0)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.52, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), int(glow_alpha * 0.38)))
            glow.setColorAt(1.0, transparent)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(center, size * 0.50, size * 0.50)

        led_color = QColor(
            int(idle.red() + (base.red() - idle.red()) * intensity),
            int(idle.green() + (base.green() - idle.green()) * intensity),
            int(idle.blue() + (base.blue() - idle.blue()) * intensity),
        )
        led = QRadialGradient(center.x() - radius * 0.25, center.y() - radius * 0.35, radius * 1.25)
        highlight = QColor(255, 255, 255, int(45 + 110 * intensity))
        edge = QColor(max(0, led_color.red() - 35), max(0, led_color.green() - 35), max(0, led_color.blue() - 35))
        led.setColorAt(0.0, highlight)
        led.setColorAt(0.22, led_color.lighter(120 + int(45 * intensity)))
        led.setColorAt(1.0, edge)

        painter.setBrush(led)
        border = QColor(base if intensity > 0.08 else COLORS["panel_edge"])
        border.setAlpha(int(95 + 130 * intensity))
        painter.setPen(QPen(border, 1.2))
        subtle_scale = 1.0 + 0.035 * intensity
        painter.drawEllipse(center, radius * subtle_scale, radius * subtle_scale)


class MetronomeIndicator(QFrame):
    """Compact HUD-style visual metronome.

    The widget does not generate audio. It only exposes a clear visual pulse so
    the operator can validate the detected beat grid without adding latency or
    sound-device complexity.
    """

    def __init__(self, title: str = "METRONOMO", led_config: Optional[LedBallistics] = None) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self._last_active = False
        self._last_phase: Optional[float] = None
        self._last_beat = ""
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.pulse_led = BallisticLed(led_config)
        self.beat_label = QLabel("-")
        self.beat_label.setObjectName("MetricValueSmall")
        self.detail_label = QLabel("sin clock")
        self.detail_label.setObjectName("MetricSubtitle")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.pulse_led)
        row.addWidget(self.beat_label, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addLayout(row)
        layout.addWidget(self.detail_label)

        self.set_active(False)

    def set_active(
        self,
        active: bool,
        beat: str = "-",
        detail: str = "sin clock",
        phase: float = 1.0,
        beat_interval: Optional[float] = None,
        accent: bool = False,
    ) -> None:
        self.beat_label.setText(beat)
        self.detail_label.setText(detail)
        if not active:
            self._last_active = False
            self._last_phase = None
            self._last_beat = beat
            self.pulse_led.set_idle()
            return

        phase = max(0.0, min(float(phase), 1.0))
        is_new_beat = (
            not self._last_active
            or beat != self._last_beat
            or (self._last_phase is not None and phase < self._last_phase - 0.45)
        )
        if is_new_beat:
            event_time = None
            if beat_interval is not None:
                event_time = monotonic() - (phase * beat_interval)
            self.pulse_led.trigger(beat_interval=beat_interval, accent=accent, event_time=event_time)

        self._last_active = True
        self._last_phase = phase
        self._last_beat = beat
