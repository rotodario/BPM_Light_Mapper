from __future__ import annotations

from statistics import mean
from time import time

import pyqtgraph as pg
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.device_combo = QComboBox()
        self.refresh_button = QPushButton("Refrescar")
        self.start_button = QPushButton("Iniciar LIVE")
        self.start_button.setProperty("role", "primary")
        self.stop_button = QPushButton("Parar")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setEnabled(False)
        self.tap_button = QPushButton("TAP")
        self.lock_button = QPushButton("Lock TAP")
        self.lock_button.setCheckable(True)
        top.addWidget(QLabel("INPUT"))
        top.addWidget(self.device_combo, 1)
        top.addWidget(self.refresh_button)
        top.addWidget(self.start_button)
        top.addWidget(self.stop_button)
        top.addWidget(self.tap_button)
        top.addWidget(self.lock_button)
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
        cockpit.addWidget(bpm_frame, 0, 0, 2, 2)

        self.conf_card = MetricCard("Confianza", "0.00", compact=True)
        self.tap_card = MetricCard("Tap BPM", "-", compact=True)
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        level_panel = SectionPanel("Nivel entrada")
        level_panel.body.addWidget(self.level_bar)
        cockpit.addWidget(self.conf_card, 0, 2)
        cockpit.addWidget(self.tap_card, 1, 2)
        cockpit.addWidget(level_panel, 2, 2)

        timing_panel = SectionPanel("Tiempos iluminacion")
        self.timing_grid = TimingGrid()
        timing_panel.body.addWidget(self.timing_grid)
        cockpit.addWidget(timing_panel, 2, 0, 1, 2)
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
        self.history_curve = self.history_plot.plot([], [], pen=pg.mkPen(COLORS["orange"], width=2))
        history_panel.body.addWidget(self.history_plot)
        layout.addWidget(history_panel, 1)

        self.refresh_button.clicked.connect(self.refresh_devices)
        self.start_button.clicked.connect(self.start_live)
        self.stop_button.clicked.connect(self.stop_live)
        self.tap_button.clicked.connect(self.handle_tap)
        self.lock_button.toggled.connect(self._toggle_manual_lock)
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
            callback=self.update_live_metrics,
            error_callback=self.log_message.emit,
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
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.state_badge.set_status("SEARCHING")
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

    def _apply_live_update(self, update: LiveUpdate) -> None:
        display_bpm = update.bpm
        display_state = update.state.upper().replace("-", " ")
        if self.lock_button.isChecked():
            try:
                display_bpm = float(self.tap_card.value_label.text())
                display_state = "MANUAL LOCK"
            except ValueError:
                pass
        self.bpm_label.setText(f"{display_bpm:.2f}")
        self.state_badge.set_status(display_state)
        self.conf_card.set_value(f"{update.confidence:.2f}")
        self.level_bar.setValue(int(max(0.0, min(1.0, update.level * 8.0)) * 100))
        beat_ms = (60000.0 / display_bpm) if display_bpm > 0 else 0.0
        self.beat_label.setText(f"{beat_ms:.2f} ms / beat" if beat_ms else "- ms / beat")
        self.timing_grid.set_beat_ms(beat_ms)
        x = list(range(len(update.history)))
        self.history_curve.setData(x, update.history)
        if update.change_detected:
            self.log_message.emit(f"Cambio de BPM detectado cerca de {update.bpm:.2f} BPM.")

    def _toggle_manual_lock(self, checked: bool) -> None:
        if checked:
            self.state_badge.set_status("MANUAL LOCK")
            self.log_message.emit("Manual lock activado usando Tap Tempo.")
        else:
            self.state_badge.set_status("SEARCHING")
            self.log_message.emit("Manual lock desactivado.")
