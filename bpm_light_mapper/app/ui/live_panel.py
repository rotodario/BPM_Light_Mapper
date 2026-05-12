from __future__ import annotations

from statistics import mean
from time import time

import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from bpm_light_mapper.app.audio.live_analyzer import LiveBpmAnalyzer, LiveUpdate


class LivePanel(QWidget):
    log_message = Signal(str)
    live_update_received = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.analyzer: LiveBpmAnalyzer | None = None
        self.tap_times: list[float] = []

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.device_combo = QComboBox()
        self.refresh_button = QPushButton("Refrescar entradas")
        self.start_button = QPushButton("Iniciar LIVE")
        self.stop_button = QPushButton("Parar LIVE")
        self.stop_button.setEnabled(False)
        self.tap_button = QPushButton("Tap Tempo")
        self.lock_button = QPushButton("Lock TAP")
        self.lock_button.setCheckable(True)
        controls.addWidget(self.device_combo, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.tap_button)
        controls.addWidget(self.lock_button)
        layout.addLayout(controls)

        metrics_box = QGroupBox("Deteccion LIVE")
        metrics_layout = QGridLayout(metrics_box)
        self.bpm_label = QLabel("0.00")
        self.bpm_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        self.state_label = QLabel("searching")
        self.conf_label = QLabel("0.00")
        self.tap_label = QLabel("-")
        self.level_bar = QProgressBar()
        self.level_bar.setRange(0, 100)
        self.use_manual_lock = QLabel("Manual lock: no")
        self.ms_labels = {
            "1/1": QLabel("-"),
            "1/2": QLabel("-"),
            "1/4": QLabel("-"),
            "1/8": QLabel("-"),
            "1/16": QLabel("-"),
        }
        metrics_layout.addWidget(QLabel("BPM"), 0, 0)
        metrics_layout.addWidget(self.bpm_label, 0, 1)
        metrics_layout.addWidget(QLabel("Estado"), 1, 0)
        metrics_layout.addWidget(self.state_label, 1, 1)
        metrics_layout.addWidget(QLabel("Confianza"), 2, 0)
        metrics_layout.addWidget(self.conf_label, 2, 1)
        metrics_layout.addWidget(QLabel("Tap BPM"), 3, 0)
        metrics_layout.addWidget(self.tap_label, 3, 1)
        metrics_layout.addWidget(QLabel("Nivel"), 4, 0)
        metrics_layout.addWidget(self.level_bar, 4, 1)
        metrics_layout.addWidget(self.use_manual_lock, 5, 0, 1, 2)
        row = 6
        for key, label in self.ms_labels.items():
            metrics_layout.addWidget(QLabel(key), row, 0)
            metrics_layout.addWidget(label, row, 1)
            row += 1
        layout.addWidget(metrics_box)

        self.history_plot = pg.PlotWidget()
        self.history_plot.setLabel("left", "BPM")
        self.history_plot.setLabel("bottom", "Muestras")
        self.history_plot.showGrid(x=True, y=True, alpha=0.2)
        self.history_curve = self.history_plot.plot([], [], pen=pg.mkPen("#d35400", width=2))
        layout.addWidget(self.history_plot, 1)

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
        self.analyzer = LiveBpmAnalyzer(device=device, callback=self.update_live_metrics)
        try:
            self.analyzer.start()
        except Exception as exc:
            self.analyzer = None
            self.log_message.emit(f"No se pudo iniciar LIVE: {exc}")
            return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_message.emit("LIVE iniciado.")

    def stop_live(self) -> None:
        if self.analyzer is not None:
            self.analyzer.stop()
            self.analyzer = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_message.emit("LIVE detenido.")

    def handle_tap(self) -> None:
        now = time()
        self.tap_times.append(now)
        self.tap_times = self.tap_times[-8:]
        if len(self.tap_times) >= 2:
            intervals = [b - a for a, b in zip(self.tap_times[:-1], self.tap_times[1:]) if b > a]
            if intervals:
                bpm = 60.0 / mean(intervals)
                self.tap_label.setText(f"{bpm:.2f}")
                if self.lock_button.isChecked():
                    self.use_manual_lock.setText(f"Manual lock: si ({bpm:.2f} BPM)")

    def update_live_metrics(self, update: LiveUpdate) -> None:
        self.live_update_received.emit(update)

    def _apply_live_update(self, update: LiveUpdate) -> None:
        display_bpm = update.bpm
        display_state = update.state
        if self.lock_button.isChecked():
            try:
                display_bpm = float(self.tap_label.text())
                display_state = "manual-lock"
            except ValueError:
                pass
        self.bpm_label.setText(f"{display_bpm:.2f}")
        self.state_label.setText(display_state)
        self.conf_label.setText(f"{update.confidence:.2f}")
        self.level_bar.setValue(int(max(0.0, min(1.0, update.level * 8.0)) * 100))
        beat_ms = (60000.0 / display_bpm) if display_bpm > 0 else 0.0
        self._set_subdivision_labels(beat_ms)
        x = list(range(len(update.history)))
        self.history_curve.setData(x, update.history)
        if update.change_detected:
            self.log_message.emit(f"Cambio de BPM detectado cerca de {update.bpm:.2f} BPM.")

    def _toggle_manual_lock(self, checked: bool) -> None:
        if checked:
            self.use_manual_lock.setText(f"Manual lock: si ({self.tap_label.text()})")
            self.log_message.emit("Manual lock activado usando Tap Tempo.")
        else:
            self.use_manual_lock.setText("Manual lock: no")
            self.log_message.emit("Manual lock desactivado.")

    def _set_subdivision_labels(self, beat_ms: float) -> None:
        if beat_ms <= 0:
            for label in self.ms_labels.values():
                label.setText("-")
            return
        self.ms_labels["1/1"].setText(f"{beat_ms:.2f} ms")
        self.ms_labels["1/2"].setText(f"{beat_ms / 2:.2f} ms")
        self.ms_labels["1/4"].setText(f"{beat_ms / 4:.2f} ms")
        self.ms_labels["1/8"].setText(f"{beat_ms / 8:.2f} ms")
        self.ms_labels["1/16"].setText(f"{beat_ms / 16:.2f} ms")
