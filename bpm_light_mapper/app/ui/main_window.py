from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bpm_light_mapper.app.audio.loader import load_audio
from bpm_light_mapper.app.audio.offline_analyzer import OfflineAnalysisParameters, analyze_file
from bpm_light_mapper.app.export.export_csv import export_segments_csv, export_segments_txt
from bpm_light_mapper.app.export.export_json import export_analysis_json
from bpm_light_mapper.app.models.analysis_result import AnalysisResult
from bpm_light_mapper.app.models.segment import Segment
from bpm_light_mapper.app.ui.live_panel import LivePanel
from bpm_light_mapper.app.ui.segment_table import SegmentTable
from bpm_light_mapper.app.ui.waveform_widget import WaveformWidget
from bpm_light_mapper.app.utils.logging_utils import timestamped


class AnalysisThread(QThread):
    finished_ok = Signal(dict, object)
    failed = Signal(str)

    def __init__(self, file_path: str, params: OfflineAnalysisParameters) -> None:
        super().__init__()
        self.file_path = file_path
        self.params = params

    def run(self) -> None:
        try:
            audio, result = analyze_file(self.file_path, self.params)
            self.finished_ok.emit(audio, result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BPM Light Mapper")
        self.resize(1440, 900)
        self.current_file: str | None = None
        self.current_audio: dict | None = None
        self.analysis_result: AnalysisResult | None = None
        self.analysis_thread: AnalysisThread | None = None
        self.beat_offset_applied = 0.0

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_row = QHBoxLayout()
        self.load_button = QPushButton("Cargar audio")
        self.analyze_button = QPushButton("Analizar")
        self.export_json_button = QPushButton("Exportar JSON")
        self.export_csv_button = QPushButton("Exportar CSV")
        self.export_txt_button = QPushButton("Exportar TXT")
        self.add_segment_button = QPushButton("Anadir zona")
        self.delete_segment_button = QPushButton("Borrar zona")
        self.split_segment_button = QPushButton("Dividir zona")
        self.merge_segment_button = QPushButton("Fusionar con siguiente")
        for button in [
            self.load_button,
            self.analyze_button,
            self.export_json_button,
            self.export_csv_button,
            self.export_txt_button,
            self.add_segment_button,
            self.delete_segment_button,
            self.split_segment_button,
            self.merge_segment_button,
        ]:
            top_row.addWidget(button)
        main_layout.addLayout(top_row)

        info_row = QHBoxLayout()
        self.file_info = QLabel("Archivo: -")
        self.global_bpm_label = QLabel("BPM Global: -")
        self.global_bpm_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.zone_bpm_label = QLabel("Zona: -")
        info_row.addWidget(self.file_info, 2)
        info_row.addWidget(self.global_bpm_label, 1)
        info_row.addWidget(self.zone_bpm_label, 1)
        main_layout.addLayout(info_row)

        splitter = QSplitter()
        main_layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.waveform_widget = WaveformWidget()
        left_layout.addWidget(self.waveform_widget, 3)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        left_layout.addWidget(self.log_box, 1)
        splitter.addWidget(left)

        right_tabs = QTabWidget()
        splitter.addWidget(right_tabs)

        offline_tab = QWidget()
        offline_layout = QVBoxLayout(offline_tab)
        offline_layout.addWidget(self._build_params_box())
        self.segment_table = SegmentTable()
        offline_layout.addWidget(self.segment_table, 1)
        right_tabs.addTab(offline_tab, "Offline")

        self.live_panel = LivePanel()
        right_tabs.addTab(self.live_panel, "LIVE")
        self.live_panel.log_message.connect(self.log)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)

        self.load_button.clicked.connect(self.load_file)
        self.analyze_button.clicked.connect(self.start_analysis)
        self.export_json_button.clicked.connect(self.export_json)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.export_txt_button.clicked.connect(self.export_txt)
        self.beat_offset_button.clicked.connect(self.apply_beat_offset)
        self.segment_table.selection_changed.connect(self.on_segment_selected)
        self.segment_table.segments_changed.connect(self.refresh_segment_view)
        self.add_segment_button.clicked.connect(self.add_segment)
        self.delete_segment_button.clicked.connect(self.delete_segment)
        self.split_segment_button.clicked.connect(self.split_segment)
        self.merge_segment_button.clicked.connect(self.merge_segment)

        self._set_buttons_enabled(False)
        self.load_button.setEnabled(True)
        self.analyze_button.setEnabled(False)

    def _build_params_box(self) -> QGroupBox:
        group = QGroupBox("Parametros de analisis")
        layout = QFormLayout(group)
        self.window_spin = self._spin(4.0, 30.0, 12.0, 1.0)
        self.hop_spin = self._spin(0.5, 10.0, 2.0, 0.5)
        self.min_change_spin = self._spin(1.0, 20.0, 3.0, 0.5)
        self.min_segment_spin = self._spin(2.0, 60.0, 8.0, 1.0)
        self.onset_spin = self._spin(0.3, 3.0, 1.0, 0.1)
        self.bpm_min_spin = self._spin(40.0, 200.0, 60.0, 1.0)
        self.bpm_max_spin = self._spin(60.0, 240.0, 180.0, 1.0)
        self.beat_offset_spin = self._spin(-2.0, 2.0, 0.0, 0.01)
        self.beat_offset_button = QPushButton("Aplicar offset beats")
        layout.addRow("Ventana (s)", self.window_spin)
        layout.addRow("Hop (s)", self.hop_spin)
        layout.addRow("Cambio minimo BPM", self.min_change_spin)
        layout.addRow("Duracion minima zona (s)", self.min_segment_spin)
        layout.addRow("Sensibilidad onset", self.onset_spin)
        layout.addRow("BPM minimo", self.bpm_min_spin)
        layout.addRow("BPM maximo", self.bpm_max_spin)
        layout.addRow("Offset beats (s)", self.beat_offset_spin)
        layout.addRow("", self.beat_offset_button)
        return group

    @staticmethod
    def _spin(minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        return spin

    def _analysis_params(self) -> OfflineAnalysisParameters:
        return OfflineAnalysisParameters(
            window_seconds=self.window_spin.value(),
            hop_seconds=self.hop_spin.value(),
            min_bpm_change=self.min_change_spin.value(),
            min_segment_seconds=self.min_segment_spin.value(),
            onset_sensitivity=self.onset_spin.value(),
            bpm_min=self.bpm_min_spin.value(),
            bpm_max=self.bpm_max_spin.value(),
        )

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in [
            self.export_json_button,
            self.export_csv_button,
            self.export_txt_button,
            self.add_segment_button,
            self.delete_segment_button,
            self.split_segment_button,
            self.merge_segment_button,
        ]:
            button.setEnabled(enabled)

    def log(self, message: str) -> None:
        self.log_box.appendPlainText(timestamped(message))

    def load_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar audio",
            "",
            "Audio (*.wav *.mp3 *.flac *.aiff *.aif)",
        )
        if not file_path:
            return
        try:
            self.current_file = file_path
            self.log(f"Archivo cargado: {file_path}")
            self.log("Cargando waveform de previsualizacion...")
            audio = load_audio(file_path, target_sr=22050)
            self.current_audio = audio
            self.analysis_result = None
            self.waveform_widget.set_waveform(audio["waveform"], audio["duration"])
            self.waveform_widget.set_beats([])
            self.waveform_widget.set_segments([])
            self.segment_table.load_segments([])
            self.file_info.setText(
                f"Archivo: {Path(file_path).name} | Duracion: {audio['duration']:.2f}s | "
                f"SR: {audio['sample_rate']} | Canales: {audio['channels']}"
            )
            self.global_bpm_label.setText("BPM Global: analizando...")
            self.zone_bpm_label.setText("Zona: -")
            self.analyze_button.setEnabled(True)
            self.start_analysis()
        except Exception as exc:
            QMessageBox.critical(self, "Error al cargar audio", str(exc))
            self.log(f"Error al cargar audio: {exc}")

    def start_analysis(self) -> None:
        if not self.current_file:
            return
        self.analyze_button.setEnabled(False)
        self.log("Analisis offline iniciado.")
        self.analysis_thread = AnalysisThread(self.current_file, self._analysis_params())
        self.analysis_thread.finished_ok.connect(self.on_analysis_complete)
        self.analysis_thread.failed.connect(self.on_analysis_failed)
        self.analysis_thread.start()

    def on_analysis_complete(self, audio: dict, result: AnalysisResult) -> None:
        self.current_audio = audio
        self.analysis_result = result
        self.beat_offset_applied = 0.0
        self.beat_offset_spin.setValue(0.0)
        self.analyze_button.setEnabled(True)
        self._set_buttons_enabled(True)
        self.file_info.setText(
            f"Archivo: {result.file_name} | Duracion: {result.duration:.2f}s | "
            f"SR: {result.sample_rate} | Canales: {result.channels}"
        )
        candidates = " / ".join(f"{value:.2f}" for value in result.bpm_candidates)
        self.global_bpm_label.setText(
            f"BPM Global: {result.bpm_global:.2f} | Conf: {result.confidence_global:.2f} | Alt: {candidates}"
        )
        self.waveform_widget.set_waveform(audio["waveform"], result.duration)
        self.waveform_widget.set_beats(result.beat_times)
        self.waveform_widget.set_segments(result.segments)
        self.segment_table.load_segments(result.segments)
        if result.segments:
            self.on_segment_selected(0)
        for warning in result.warnings:
            self.log(f"Aviso: {warning}")
        self.log(f"Analisis completado. Segmentos detectados: {len(result.segments)}.")

    def apply_beat_offset(self) -> None:
        if self.analysis_result is None:
            return
        new_offset = self.beat_offset_spin.value()
        delta = new_offset - self.beat_offset_applied
        if abs(delta) < 1e-9:
            return
        duration = self.analysis_result.duration
        self.analysis_result.beat_times = [
            beat
            for beat in (value + delta for value in self.analysis_result.beat_times)
            if 0.0 <= beat <= duration
        ]
        for segment in self.analysis_result.segments:
            segment.beats = [
                beat
                for beat in (value + delta for value in segment.beats)
                if 0.0 <= beat <= duration
            ]
        self.beat_offset_applied = new_offset
        self.waveform_widget.set_beats(self.analysis_result.beat_times)
        self.waveform_widget.set_segments(self.analysis_result.segments)
        self.log(f"Offset de beats aplicado: {new_offset:+.3f}s")

    def on_analysis_failed(self, error: str) -> None:
        self.analyze_button.setEnabled(True)
        QMessageBox.critical(self, "Error de analisis", error)
        self.log(f"Error de analisis: {error}")

    def on_segment_selected(self, row: int) -> None:
        if self.analysis_result is None or row < 0 or row >= len(self.analysis_result.segments):
            return
        segment = self.analysis_result.segments[row]
        self.zone_bpm_label.setText(
            f"Zona: {segment.start:.2f}-{segment.end:.2f}s | {segment.bpm:.2f} BPM | Conf: {segment.confidence:.2f}"
        )
        self.waveform_widget.highlight_segment(row)

    def refresh_segment_view(self) -> None:
        if self.analysis_result is None:
            return
        self.waveform_widget.set_segments(self.analysis_result.segments)
        self.log("Segmentos actualizados manualmente.")

    def add_segment(self) -> None:
        if self.analysis_result is None:
            return
        end = self.analysis_result.duration
        start = max(0.0, end - 8.0)
        bpm = self.analysis_result.bpm_global
        self.analysis_result.segments.append(
            Segment(start=start, end=end, bpm=bpm, confidence=0.5, confirmed=True, notes="manual")
        )
        self.segment_table.load_segments(self.analysis_result.segments)
        self.refresh_segment_view()

    def delete_segment(self) -> None:
        if self.analysis_result is None:
            return
        row = self.segment_table.selected_row()
        if row < 0 or row >= len(self.analysis_result.segments):
            return
        del self.analysis_result.segments[row]
        self.segment_table.load_segments(self.analysis_result.segments)
        self.refresh_segment_view()

    def split_segment(self) -> None:
        if self.analysis_result is None:
            return
        row = self.segment_table.selected_row()
        if row < 0 or row >= len(self.analysis_result.segments):
            return
        segment = self.analysis_result.segments[row]
        midpoint = (segment.start + segment.end) / 2.0
        left = Segment(
            start=segment.start,
            end=midpoint,
            bpm=segment.bpm,
            confidence=segment.confidence,
            beats=[beat for beat in segment.beats if beat < midpoint],
            confirmed=segment.confirmed,
            notes=segment.notes,
        )
        right = Segment(
            start=midpoint,
            end=segment.end,
            bpm=segment.bpm,
            confidence=segment.confidence,
            beats=[beat for beat in segment.beats if beat >= midpoint],
            confirmed=segment.confirmed,
            notes=segment.notes,
        )
        self.analysis_result.segments[row : row + 1] = [left, right]
        self.segment_table.load_segments(self.analysis_result.segments)
        self.refresh_segment_view()

    def merge_segment(self) -> None:
        if self.analysis_result is None:
            return
        row = self.segment_table.selected_row()
        if row < 0 or row >= len(self.analysis_result.segments) - 1:
            return
        first = self.analysis_result.segments[row]
        second = self.analysis_result.segments[row + 1]
        merged = Segment(
            start=first.start,
            end=second.end,
            bpm=(first.bpm + second.bpm) / 2.0,
            confidence=(first.confidence + second.confidence) / 2.0,
            beats=sorted(set(first.beats + second.beats)),
            confirmed=first.confirmed or second.confirmed,
            notes=" | ".join(filter(None, [first.notes, second.notes])),
        )
        self.analysis_result.segments[row : row + 2] = [merged]
        self.segment_table.load_segments(self.analysis_result.segments)
        self.refresh_segment_view()

    def export_json(self) -> None:
        if self.analysis_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar JSON", "", "JSON (*.json)")
        if not path:
            return
        export_analysis_json(self.analysis_result, path)
        self.log(f"Exportado JSON: {path}")

    def export_csv(self) -> None:
        if self.analysis_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "", "CSV (*.csv)")
        if not path:
            return
        export_segments_csv(self.analysis_result, path)
        self.log(f"Exportado CSV: {path}")

    def export_txt(self) -> None:
        if self.analysis_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar TXT", "", "TXT (*.txt)")
        if not path:
            return
        export_segments_txt(self.analysis_result, path)
        self.log(f"Exportado TXT: {path}")
