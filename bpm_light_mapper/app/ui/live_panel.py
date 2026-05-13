from __future__ import annotations

from statistics import mean
from time import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from bpm_light_mapper.app.audio.live_analyzer import LiveBpmAnalyzer, LiveUpdate
from bpm_light_mapper.app.ui.metric_card import MetricCard
from bpm_light_mapper.app.ui.section_panel import SectionPanel
from bpm_light_mapper.app.ui.status_badge import StatusBadge
from bpm_light_mapper.app.ui.theme import COLORS
from bpm_light_mapper.app.ui.timing_grid import TimingGrid


class LiveStartThread(QThread):
    started_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, analyzer: LiveBpmAnalyzer) -> None:
        super().__init__()
        self.analyzer = analyzer

    def run(self) -> None:
        try:
            self.analyzer.start()
            self.started_ok.emit(self.analyzer)
        except Exception as exc:
            self.failed.emit(str(exc))


class LivePanel(QWidget):
    log_message = Signal(str)
    live_update_received = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.analyzer: LiveBpmAnalyzer | None = None
        self.start_thread: LiveStartThread | None = None
        self.tap_times: list[float] = []
        self.last_live_update_timestamp = 0.0
        self.last_change_timestamp = 0.0
        self.waveform_x = np.arange(360, dtype=float)
        self.history_x = np.arange(240, dtype=float)
        self.history_display = np.full(240, np.nan, dtype=float)
        self.target_bpm = 0.0
        self.display_bpm = 0.0
        self.target_confidence = 0.0
        self.display_confidence = 0.0
        self.target_state = "SEARCHING"
        self.live_candidate_mode = "Detected"
        self.latest_candidate_text = "-"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.device_combo = QComboBox()
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Normal 80-160", "Slow 50-90", "Fast 140-200", "Custom 35-240"])
        self.refresh_button = QPushButton("Refrescar")
        self.start_button = QPushButton("Iniciar LIVE")
        self.start_button.setProperty("role", "primary")
        self.stop_button = QPushButton("Parar")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setEnabled(False)
        self.tap_button = QPushButton("TAP")
        self.lock_button = QPushButton("Lock TAP")
        self.lock_button.setCheckable(True)
        self.normalize_half_button = QCheckBox("Normalizar half-time x2")
        self.normalize_half_button.setChecked(False)
        top.addWidget(QLabel("INPUT"))
        top.addWidget(self.device_combo, 1)
        top.addWidget(QLabel("RANGE"))
        top.addWidget(self.range_combo)
        top.addWidget(self.refresh_button)
        top.addWidget(self.start_button)
        top.addWidget(self.stop_button)
        top.addWidget(self.tap_button)
        top.addWidget(self.lock_button)
        top.addWidget(self.normalize_half_button)
        layout.addLayout(top)

        cockpit = QGridLayout()
        cockpit.setSpacing(10)

        bpm_frame = QFrame()
        bpm_frame.setObjectName("SectionPanel")
        bpm_layout = QVBoxLayout(bpm_frame)
        bpm_layout.setContentsMargins(18, 14, 18, 16)
        self.state_badge = StatusBadge("SEARCHING")
        self.bpm_label = QLabel("0.00")
        self.bpm_label.setObjectName("MetricValue")
        self.bpm_label.setStyleSheet("font-size: 76px; font-weight: 900; color: #28d7ff;")
        self.beat_label = QLabel("- ms / beat")
        self.beat_label.setObjectName("MetricSubtitle")
        bpm_layout.addWidget(self.state_badge)
        bpm_layout.addWidget(self.bpm_label)
        bpm_layout.addWidget(self.beat_label)
        bpm_frame.setMaximumWidth(460)
        bpm_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        cockpit.addWidget(bpm_frame, 0, 0, 2, 1)

        self.conf_card = MetricCard("Confianza", "0.00", compact=True)
        self.tap_card = MetricCard("Tap BPM", "-", compact=True)
        self.live_candidates_card = MetricCard("Half / Main / Double", "-", compact=True)
        self.live_half_button = QPushButton("Use half")
        self.live_detected_button = QPushButton("Use main")
        self.live_double_button = QPushButton("Use double")
        self.live_detected_button.setProperty("role", "primary")
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setMaximumHeight(12)
        self.level_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        level_panel = SectionPanel("Nivel entrada")
        level_panel.layout().setContentsMargins(8, 5, 8, 8)
        level_panel.layout().setSpacing(4)
        level_panel.title_label.setMaximumHeight(14)
        level_panel.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        level_panel.body.setSpacing(4)
        level_panel.layout().setStretch(0, 0)
        level_panel.layout().setStretch(1, 0)
        level_panel.body.addWidget(self.level_bar)
        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setBackground(COLORS["bg"])
        self.waveform_plot.setMouseEnabled(x=False, y=False)
        self.waveform_plot.hideAxis("bottom")
        self.waveform_plot.setYRange(-1.0, 1.0)
        self.waveform_plot.setMinimumSize(0, 0)
        self.waveform_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.waveform_plot.showGrid(x=False, y=True, alpha=0.10)
        self.waveform_plot.getAxis("left").setPen(pg.mkPen("#41566a"))
        self.waveform_plot.getAxis("left").setTextPen(pg.mkPen(COLORS["muted"]))
        self.waveform_min_curve = self.waveform_plot.plot(
            self.waveform_x,
            np.zeros_like(self.waveform_x),
            pen=pg.mkPen(COLORS["cyan_dim"], width=1),
        )
        self.waveform_max_curve = self.waveform_plot.plot(
            self.waveform_x,
            np.zeros_like(self.waveform_x),
            pen=pg.mkPen(COLORS["cyan"], width=1),
        )
        self.waveform_fill = pg.FillBetweenItem(
            self.waveform_min_curve,
            self.waveform_max_curve,
            brush=pg.mkBrush(40, 215, 255, 55),
        )
        self.waveform_plot.addItem(self.waveform_fill)
        level_panel.body.addWidget(self.waveform_plot, 1)
        level_panel.body.setStretch(0, 0)
        level_panel.body.setStretch(1, 1)
        cockpit.addWidget(self.conf_card, 0, 1)
        cockpit.addWidget(self.tap_card, 1, 1)
        candidate_panel = SectionPanel("Tempo candidates")
        candidate_panel.layout().setContentsMargins(8, 5, 8, 8)
        candidate_panel.layout().setSpacing(4)
        candidate_panel.title_label.setMaximumHeight(14)
        candidate_panel.body.setSpacing(6)
        live_choice_row = QHBoxLayout()
        live_choice_row.setSpacing(6)
        live_choice_row.addWidget(self.live_half_button)
        live_choice_row.addWidget(self.live_detected_button)
        live_choice_row.addWidget(self.live_double_button)
        candidate_panel.body.addWidget(self.live_candidates_card)
        candidate_panel.body.addLayout(live_choice_row)
        candidate_panel.setMinimumWidth(260)
        candidate_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cockpit.addWidget(candidate_panel, 0, 2, 2, 1)
        cockpit.addWidget(level_panel, 2, 1, 1, 2)

        timing_panel = SectionPanel("Tiempos iluminacion")
        self.timing_grid = TimingGrid()
        timing_panel.body.addWidget(self.timing_grid)
        timing_panel.setMaximumWidth(460)
        timing_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        level_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cockpit.addWidget(timing_panel, 2, 0)
        cockpit.setColumnStretch(0, 0)
        cockpit.setColumnMinimumWidth(1, 260)
        cockpit.setColumnMinimumWidth(2, 260)
        cockpit.setColumnStretch(1, 1)
        cockpit.setColumnStretch(2, 1)
        layout.addLayout(cockpit)

        history_panel = SectionPanel("Historial BPM")
        self.history_plot = pg.PlotWidget()
        self.history_plot.setBackground(COLORS["bg"])
        self.history_plot.setLabel("left", "BPM")
        self.history_plot.setLabel("bottom", "Muestras")
        self.history_plot.showGrid(x=True, y=True, alpha=0.16)
        self.history_plot.getAxis("bottom").setPen(pg.mkPen("#41566a"))
        self.history_plot.getAxis("left").setPen(pg.mkPen("#41566a"))
        self.history_plot.getAxis("bottom").setTextPen(pg.mkPen(COLORS["muted"]))
        self.history_plot.getAxis("left").setTextPen(pg.mkPen(COLORS["muted"]))
        self.history_curve = self.history_plot.plot(self.history_x, self.history_display, pen=pg.mkPen(COLORS["orange"], width=2))
        history_panel.body.addWidget(self.history_plot)
        layout.addWidget(history_panel, 1)

        self.render_timer = QTimer(self)
        self.render_timer.setInterval(33)
        self.render_timer.timeout.connect(self._render_live_frame)

        self.refresh_button.clicked.connect(self.refresh_devices)
        self.start_button.clicked.connect(self.start_live)
        self.stop_button.clicked.connect(self.stop_live)
        self.tap_button.clicked.connect(self.handle_tap)
        self.lock_button.toggled.connect(self._toggle_manual_lock)
        self.live_half_button.clicked.connect(lambda: self._set_live_candidate_mode("Half-time"))
        self.live_detected_button.clicked.connect(lambda: self._set_live_candidate_mode("Detected"))
        self.live_double_button.clicked.connect(lambda: self._set_live_candidate_mode("Double-time"))
        self.live_update_received.connect(self._apply_live_update)
        self.refresh_devices()

    def refresh_devices(self) -> None:
        self.device_combo.clear()
        devices = LiveBpmAnalyzer.list_input_devices()
        if not devices:
            self.device_combo.addItem("Sin entradas disponibles", None)
            return
        for idx, name in devices:
            self.device_combo.addItem(name, idx)

    def start_live(self) -> None:
        device = self.device_combo.currentData()
        if device is None:
            self.log_message.emit("No hay dispositivo de entrada disponible.")
            return
        self.analyzer = LiveBpmAnalyzer(
            device=device,
            callback=None,
            error_callback=self.log_message.emit,
            visual_interval=1.0 / 30.0,
            waveform_columns=len(self.waveform_x),
            bpm_min=self._live_bpm_range()[0],
            bpm_max=self._live_bpm_range()[1],
        )
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.state_badge.set_status("SEARCHING")
        self.log_message.emit("Iniciando LIVE...")
        self.start_thread = LiveStartThread(self.analyzer)
        self.start_thread.started_ok.connect(self._on_live_started)
        self.start_thread.failed.connect(self._on_live_failed)
        self.start_thread.finished.connect(self._on_live_start_thread_finished)
        self.start_thread.start()

    def _on_live_started(self, analyzer: LiveBpmAnalyzer) -> None:
        self.analyzer = analyzer
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.state_badge.set_status("LIVE")
        self.last_live_update_timestamp = 0.0
        self.last_change_timestamp = 0.0
        self.target_bpm = 0.0
        self.display_bpm = 0.0
        self.target_confidence = 0.0
        self.display_confidence = 0.0
        self.target_state = "SEARCHING"
        self.live_candidate_mode = "Detected"
        self.latest_candidate_text = "-"
        self.history_display[:] = np.nan
        self.render_timer.start()
        self.log_message.emit("LIVE iniciado.")

    def _on_live_failed(self, error: str) -> None:
        self.analyzer = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.state_badge.set_status("ERROR")
        self.log_message.emit(f"No se pudo iniciar LIVE: {error}")

    def _on_live_start_thread_finished(self) -> None:
        self.start_thread = None

    def stop_live(self) -> None:
        if self.start_thread is not None and self.start_thread.isRunning():
            self.log_message.emit("LIVE aun esta inicializando; se cerrara al terminar el intento de arranque.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return
        if self.analyzer is not None:
            self.analyzer.stop()
            self.analyzer = None
        self.render_timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.state_badge.set_status("SEARCHING")
        self.bpm_label.setText("0.00")
        self.beat_label.setText("- ms / beat")
        self.conf_card.set_value("0.00")
        self.live_candidates_card.set_value("-")
        self.history_display[:] = np.nan
        self.history_curve.setData(self.history_x, self.history_display)
        self.log_message.emit("LIVE detenido.")

    def handle_tap(self) -> None:
        now = time()
        self.tap_times.append(now)
        self.tap_times = self.tap_times[-8:]
        if len(self.tap_times) >= 2:
            intervals = [b - a for a, b in zip(self.tap_times[:-1], self.tap_times[1:]) if b > a]
            if intervals:
                bpm = 60.0 / mean(intervals)
                self.tap_card.set_value(f"{bpm:.2f}")
                if self.lock_button.isChecked():
                    self.state_badge.set_status("MANUAL LOCK")

    def update_live_metrics(self, update: LiveUpdate) -> None:
        self.live_update_received.emit(update)

    def _render_live_frame(self) -> None:
        if self.analyzer is None:
            return

        visual = self.analyzer.latest_live_visual()
        self._apply_live_visual(visual)

        update = self.analyzer.latest_live_update()
        if update is not None and update.timestamp > self.last_live_update_timestamp:
            self.last_live_update_timestamp = update.timestamp
            self._ingest_live_update(update)
        self._render_live_metrics()

    def _apply_live_visual(self, visual) -> None:
        if len(visual.waveform_min) and len(visual.waveform_max):
            if len(visual.waveform_min) != len(self.waveform_x):
                self.waveform_x = np.arange(len(visual.waveform_min), dtype=float)
            self.waveform_min_curve.setData(self.waveform_x, visual.waveform_min)
            self.waveform_max_curve.setData(self.waveform_x, visual.waveform_max)
        self.level_bar.setValue(int(max(0.0, min(1.0, visual.level * 8.0)) * 100))

    def _apply_live_update(self, update: LiveUpdate) -> None:
        self._ingest_live_update(update)
        self._render_live_metrics(force=True)

    def _ingest_live_update(self, update: LiveUpdate) -> None:
        display_bpm = update.bpm
        display_state = update.state.upper().replace("-", " ")
        normalized_half = False
        candidate_by_label = {candidate.label: candidate for candidate in update.tempo_candidates}
        half = candidate_by_label.get("Half-time")
        detected = candidate_by_label.get("Detected")
        double = candidate_by_label.get("Double-time")
        if half and detected and double:
            self.latest_candidate_text = f"{half.bpm:.0f} / {detected.bpm:.0f} / {double.bpm:.0f}"
        selected_candidate = candidate_by_label.get(self.live_candidate_mode)
        if selected_candidate is not None:
            display_bpm = selected_candidate.bpm
        if self.normalize_half_button.isChecked() and 60.0 <= display_bpm < 120.0 and update.confidence >= 0.55:
            doubled = display_bpm * 2.0
            if doubled <= 240.0:
                display_bpm = doubled
                normalized_half = True
        if self.lock_button.isChecked():
            try:
                display_bpm = float(self.tap_card.value_label.text())
                display_state = "MANUAL LOCK"
            except ValueError:
                pass
        self.target_bpm = display_bpm
        self.target_confidence = update.confidence
        self.target_state = display_state
        if normalized_half and "MANUAL" not in display_state:
            self.log_message.emit(f"Half-time normalizado a x2: {update.bpm:.2f} -> {display_bpm:.2f} BPM")
        if update.change_detected and update.timestamp > self.last_change_timestamp:
            self.last_change_timestamp = update.timestamp
            self.log_message.emit(f"Cambio de BPM detectado cerca de {update.bpm:.2f} BPM.")

    def _render_live_metrics(self, force: bool = False) -> None:
        target_bpm = self.target_bpm
        target_state = self.target_state
        if self.lock_button.isChecked():
            try:
                target_bpm = float(self.tap_card.value_label.text())
                target_state = "MANUAL LOCK"
            except ValueError:
                pass
        if force or self.display_bpm <= 0.0 or target_bpm <= 0.0:
            self.display_bpm = target_bpm
        else:
            self.display_bpm = (self.display_bpm * 0.82) + (target_bpm * 0.18)
        self.display_confidence = (
            self.target_confidence if force else (self.display_confidence * 0.85) + (self.target_confidence * 0.15)
        )
        display_bpm = self.display_bpm
        display_state = target_state
        self.bpm_label.setText(f"{display_bpm:.2f}")
        self.state_badge.set_status(display_state)
        self.conf_card.set_value(f"{self.display_confidence:.2f}")
        self.live_candidates_card.set_value(self.latest_candidate_text, self.live_candidate_mode)
        beat_ms = (60000.0 / display_bpm) if display_bpm > 0 else 0.0
        self.beat_label.setText(f"{beat_ms:.2f} ms / beat" if beat_ms else "- ms / beat")
        self.timing_grid.set_beat_ms(beat_ms)
        if display_bpm > 0:
            self.history_display[:-1] = self.history_display[1:]
            self.history_display[-1] = display_bpm
            self.history_curve.setData(self.history_x, self.history_display)

    def _toggle_manual_lock(self, checked: bool) -> None:
        if checked:
            self.state_badge.set_status("MANUAL LOCK")
            self.log_message.emit("Manual lock activado usando Tap Tempo.")
        else:
            self.state_badge.set_status("SEARCHING")
            self.log_message.emit("Manual lock desactivado.")

    def _set_live_candidate_mode(self, mode: str) -> None:
        self.live_candidate_mode = mode
        self.live_candidates_card.set_value(self.latest_candidate_text, mode)
        self.log_message.emit(f"Live tempo mode: {mode}.")

    def _live_bpm_range(self) -> tuple[float, float]:
        ranges = {
            "Slow 50-90": (50.0, 90.0),
            "Normal 80-160": (80.0, 160.0),
            "Fast 140-200": (140.0, 200.0),
            "Custom 35-240": (35.0, 240.0),
        }
        return ranges.get(self.range_combo.currentText(), (35.0, 240.0))
