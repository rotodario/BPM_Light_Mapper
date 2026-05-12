from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bpm_light_mapper.app.audio.loader import load_audio_preview
from bpm_light_mapper.app.audio.offline_analyzer import AnalysisCanceled, OfflineAnalysisParameters, analyze_file
from bpm_light_mapper.app.export.export_csv import export_segments_csv, export_segments_txt
from bpm_light_mapper.app.export.export_json import export_analysis_json
from bpm_light_mapper.app.models.analysis_result import AnalysisResult
from bpm_light_mapper.app.models.segment import Segment
from bpm_light_mapper.app.ui.live_panel import LivePanel
from bpm_light_mapper.app.ui.metric_card import MetricCard
from bpm_light_mapper.app.ui.section_panel import SectionPanel
from bpm_light_mapper.app.ui.segment_table import SegmentTable
from bpm_light_mapper.app.ui.status_badge import StatusBadge
from bpm_light_mapper.app.ui.theme import COLORS
from bpm_light_mapper.app.ui.timing_grid import TimingGrid
from bpm_light_mapper.app.ui.waveform_widget import WaveformWidget
from bpm_light_mapper.app.utils.logging_utils import get_logger, timestamped


BACKGROUND_THREADS: list[QThread] = []


class AnalysisThread(QThread):
    finished_ok = Signal(dict, object)
    failed = Signal(str)
    progress = Signal(str)
    canceled = Signal()

    def __init__(self, file_path: str, params: OfflineAnalysisParameters) -> None:
        super().__init__()
        self.file_path = file_path
        self.params = params

    def run(self) -> None:
        try:
            audio, result = analyze_file(
                self.file_path,
                self.params,
                progress_callback=self.progress.emit,
                should_cancel=self.isInterruptionRequested,
            )
            self.finished_ok.emit(audio, result)
        except AnalysisCanceled:
            self.canceled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class AudioLoadThread(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            audio = load_audio_preview(self.file_path, max_points=6000)
            self.finished_ok.emit(audio)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger("ui.main_window")
        self.setWindowTitle("BPM Light Mapper")
        self.resize(1500, 940)
        self.current_file: str | None = None
        self.current_audio: dict | None = None
        self.analysis_result: AnalysisResult | None = None
        self.audio_load_thread: AudioLoadThread | None = None
        self.analysis_thread: AnalysisThread | None = None
        self.beat_offset_applied = 0.0
        self.busy_state = "idle"
        self.is_closing = False
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.85)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.offline_tab = self._build_offline_tab()
        self.live_panel = LivePanel()
        self.live_panel.log_message.connect(self.log)
        self.tabs.addTab(self.offline_tab, "OFFLINE MAP")
        self.tabs.addTab(self.live_panel, "LIVE")
        root_layout.addWidget(self.tabs, 1)

        self._connect_actions()
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(self.on_player_state_changed)
        self._set_buttons_enabled(False)
        self.load_button.setEnabled(True)
        self.analyze_button.setEnabled(False)
        self._set_app_state("IDLE", "listo")

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("AppHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        title_block = QVBoxLayout()
        self.app_title = QLabel("BPM Light Mapper")
        self.app_title.setObjectName("AppTitle")
        self.file_info = QLabel("Archivo: -")
        self.file_info.setObjectName("HeaderMeta")
        title_block.addWidget(self.app_title)
        title_block.addWidget(self.file_info)

        self.status_badge = StatusBadge("IDLE")
        self.status_label = QLabel("Estado: listo")
        self.status_label.setObjectName("HeaderMeta")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        status_block = QVBoxLayout()
        status_block.addWidget(self.status_badge)
        status_block.addWidget(self.status_label)
        status_block.addWidget(self.progress_bar)

        self.load_button = QPushButton("Cargar Audio")
        self.load_button.setProperty("role", "primary")
        self.analyze_button = QPushButton("Analizar")
        self.live_nav_button = QPushButton("LIVE")
        self.live_nav_button.setProperty("role", "primary")

        layout.addLayout(title_block, 3)
        layout.addStretch(1)
        layout.addLayout(status_block, 2)
        layout.addWidget(self.load_button)
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.live_nav_button)
        return header

    def _build_offline_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_splitter = QSplitter()
        left_splitter.setOrientation(Qt.Vertical)
        left_splitter.setChildrenCollapsible(False)
        left_layout.addWidget(left_splitter, 1)

        waveform_area = QWidget()
        waveform_area_layout = QVBoxLayout(waveform_area)
        waveform_area_layout.setContentsMargins(0, 0, 0, 0)
        waveform_area_layout.setSpacing(10)
        waveform_panel = SectionPanel("Waveform / Beat Grid / Tempo Zones")
        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setProperty("role", "primary")
        self.stop_button = QPushButton("Stop")
        self.position_label = QLabel("00:00.000")
        self.position_label.setObjectName("HeaderMeta")
        transport.addWidget(self.play_button)
        transport.addWidget(self.stop_button)
        transport.addWidget(self.position_label)
        transport.addStretch(1)
        self.waveform_widget = WaveformWidget()
        waveform_panel.body.addLayout(transport)
        waveform_panel.body.addWidget(self.waveform_widget)
        waveform_area_layout.addWidget(waveform_panel)
        left_splitter.addWidget(waveform_area)

        bottom_area = QWidget()
        bottom_layout = QVBoxLayout(bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)
        segment_panel = SectionPanel("Segmentos BPM")
        edit_row = QHBoxLayout()
        self.add_segment_button = QPushButton("Anadir zona")
        self.delete_segment_button = QPushButton("Borrar")
        self.split_segment_button = QPushButton("Dividir")
        self.merge_segment_button = QPushButton("Fusionar")
        for button in [
            self.add_segment_button,
            self.delete_segment_button,
            self.split_segment_button,
            self.merge_segment_button,
        ]:
            edit_row.addWidget(button)
        edit_row.addStretch(1)
        self.segment_table = SegmentTable()
        segment_panel.body.addLayout(edit_row)
        segment_panel.body.addWidget(self.segment_table)
        bottom_layout.addWidget(segment_panel, 1)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(110)
        bottom_layout.addWidget(self.log_box)
        left_splitter.addWidget(bottom_area)
        left_splitter.setSizes([520, 300])

        right = QWidget()
        right.setMinimumWidth(420)
        right.setMaximumWidth(540)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        metrics_panel = SectionPanel("Indicadores")
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)
        metrics_grid.setColumnMinimumWidth(0, 170)
        metrics_grid.setColumnMinimumWidth(1, 170)
        self.global_bpm_card = MetricCard("BPM Global", "-")
        self.zone_bpm_card = MetricCard("BPM Zona", "-")
        self.confidence_card = MetricCard("Confidence", "-", compact=True)
        self.beat_ms_card = MetricCard("Beat ms", "-", compact=True)
        self.candidates_card = MetricCard("Half / Double", "-", compact=True)
        self.zone_count_card = MetricCard("Zonas", "-", compact=True)
        self.duration_card = MetricCard("Duracion", "-", compact=True)
        self.current_zone_card = MetricCard("Zona Actual", "-", compact=True)
        metrics_grid.addWidget(self.global_bpm_card, 0, 0, 1, 2)
        metrics_grid.addWidget(self.zone_bpm_card, 1, 0, 1, 2)
        metrics_grid.addWidget(self.confidence_card, 2, 0)
        metrics_grid.addWidget(self.beat_ms_card, 2, 1)
        metrics_grid.addWidget(self.candidates_card, 3, 0, 1, 2)
        metrics_grid.addWidget(self.zone_count_card, 4, 0)
        metrics_grid.addWidget(self.duration_card, 4, 1)
        metrics_grid.addWidget(self.current_zone_card, 5, 0, 1, 2)
        metrics_panel.body.addLayout(metrics_grid)
        right_layout.addWidget(metrics_panel)

        timing_panel = SectionPanel("Timing")
        self.offline_timing_grid = TimingGrid()
        timing_panel.body.addWidget(self.offline_timing_grid)
        right_layout.addWidget(timing_panel)

        export_panel = SectionPanel("Exportacion")
        export_row = QHBoxLayout()
        self.export_json_button = QPushButton("JSON")
        self.export_csv_button = QPushButton("CSV")
        self.export_txt_button = QPushButton("TXT")
        export_row.addWidget(self.export_json_button)
        export_row.addWidget(self.export_csv_button)
        export_row.addWidget(self.export_txt_button)
        export_panel.body.addLayout(export_row)
        right_layout.addWidget(export_panel)

        right_layout.addWidget(self._build_params_box())
        right_layout.addStretch(1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([1050, 430])
        return tab

    def _build_params_box(self) -> QGroupBox:
        group = QGroupBox("Advanced Analysis")
        layout = QFormLayout(group)
        self.window_spin = self._spin(4.0, 30.0, 12.0, 1.0)
        self.hop_spin = self._spin(0.5, 10.0, 2.0, 0.5)
        self.min_change_spin = self._spin(1.0, 20.0, 3.0, 0.5)
        self.min_segment_spin = self._spin(2.0, 60.0, 8.0, 1.0)
        self.onset_spin = self._spin(0.3, 3.0, 1.0, 0.1)
        self.bpm_min_spin = self._spin(40.0, 200.0, 60.0, 1.0)
        self.bpm_max_spin = self._spin(60.0, 240.0, 180.0, 1.0)
        self.beat_offset_spin = self._spin(-2.0, 2.0, 0.0, 0.01)
        self.beat_offset_button = QPushButton("Aplicar offset")
        layout.addRow("Ventana (s)", self.window_spin)
        layout.addRow("Hop (s)", self.hop_spin)
        layout.addRow("Cambio BPM", self.min_change_spin)
        layout.addRow("Min zona (s)", self.min_segment_spin)
        layout.addRow("Onset", self.onset_spin)
        layout.addRow("BPM min", self.bpm_min_spin)
        layout.addRow("BPM max", self.bpm_max_spin)
        layout.addRow("Offset beats", self.beat_offset_spin)
        layout.addRow("", self.beat_offset_button)
        return group

    def _connect_actions(self) -> None:
        self.load_button.clicked.connect(self.load_file)
        self.analyze_button.clicked.connect(self.start_analysis)
        self.live_nav_button.clicked.connect(lambda: self.tabs.setCurrentWidget(self.live_panel))
        self.play_button.clicked.connect(self.toggle_playback)
        self.stop_button.clicked.connect(self.stop_playback)
        self.waveform_widget.seek_requested.connect(self.seek_playback)
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

    @staticmethod
    def _spin(minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        return spin

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes = int(seconds // 60)
        rest = int(seconds % 60)
        return f"{minutes:02d}:{rest:02d}"

    @staticmethod
    def _format_position_ms(milliseconds: int) -> str:
        total_ms = max(0, int(milliseconds))
        minutes, rem = divmod(total_ms, 60000)
        seconds, ms = divmod(rem, 1000)
        return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

    def _analysis_params(self) -> OfflineAnalysisParameters:
        params = OfflineAnalysisParameters(
            window_seconds=self.window_spin.value(),
            hop_seconds=self.hop_spin.value(),
            min_bpm_change=self.min_change_spin.value(),
            min_segment_seconds=self.min_segment_spin.value(),
            onset_sensitivity=self.onset_spin.value(),
            bpm_min=self.bpm_min_spin.value(),
            bpm_max=self.bpm_max_spin.value(),
        )
        duration = 0.0
        if self.current_audio is not None:
            duration = float(self.current_audio.get("duration", 0.0))

        if duration >= 900.0:
            params.target_sr = 8000
            params.hop_length = 2048
            params.window_seconds = max(params.window_seconds, 18.0)
            params.hop_seconds = max(params.hop_seconds, 4.0)
            params.min_segment_seconds = max(params.min_segment_seconds, 12.0)
        elif duration >= 300.0:
            params.target_sr = 11025
            params.hop_length = 1024
            params.window_seconds = max(params.window_seconds, 14.0)
            params.hop_seconds = max(params.hop_seconds, 3.0)
        else:
            params.target_sr = 11025
            params.hop_length = 1024

        return params

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

    def _set_app_state(self, state: str, message: str) -> None:
        self.status_badge.set_status(state)
        self.status_label.setText(f"Estado: {message}")

    def _set_busy(self, busy: bool, state: str, message: str) -> None:
        self.busy_state = state if busy else "idle"
        self.progress_bar.setVisible(busy)
        badge_state = state.upper() if busy or state.upper() == "ERROR" else "IDLE"
        self._set_app_state(badge_state, message)
        self.load_button.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy and self.current_file is not None)
        self.live_panel.setEnabled(not busy)
        if busy:
            self._set_buttons_enabled(False)
        elif self.analysis_result is not None:
            self._set_buttons_enabled(True)

    def _update_empty_metrics(self) -> None:
        for card in [
            self.global_bpm_card,
            self.zone_bpm_card,
            self.confidence_card,
            self.beat_ms_card,
            self.candidates_card,
            self.zone_count_card,
            self.duration_card,
            self.current_zone_card,
        ]:
            card.set_value("-")
        self.offline_timing_grid.set_beat_ms(0.0)

    def _track_thread(self, thread: QThread) -> None:
        BACKGROUND_THREADS.append(thread)

    def _untrack_thread(self, thread: QThread | None) -> None:
        if thread in BACKGROUND_THREADS:
            BACKGROUND_THREADS.remove(thread)

    def _finish_close_if_idle(self) -> None:
        if not self.is_closing:
            return
        active = any(thread.isRunning() for thread in BACKGROUND_THREADS)
        if not active:
            self.logger.info("All background threads finished after close request")
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def log(self, message: str) -> None:
        self.logger.info(message)
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
        self.current_file = file_path
        self.current_audio = None
        self.analysis_result = None
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.position_label.setText("00:00.000")
        self.file_info.setText(f"Archivo: {Path(file_path).name}")
        self._update_empty_metrics()
        self.waveform_widget.set_waveform([], 0.0)
        self.segment_table.load_segments([])
        self.log(f"Archivo cargado: {file_path}")
        self.log("Cargando waveform de previsualizacion...")
        self._set_busy(True, "LOADING", "cargando audio...")
        self.audio_load_thread = AudioLoadThread(file_path)
        self.audio_load_thread.finished_ok.connect(self.on_audio_loaded)
        self.audio_load_thread.failed.connect(self.on_audio_load_failed)
        self.audio_load_thread.finished.connect(self._on_audio_load_thread_finished)
        self._track_thread(self.audio_load_thread)
        self.audio_load_thread.start()

    def on_audio_loaded(self, audio: dict) -> None:
        self.current_audio = audio
        self.waveform_widget.set_waveform(audio["waveform"], audio["duration"])
        self.waveform_widget.set_beats([])
        self.waveform_widget.set_segments([])
        self.segment_table.load_segments([])
        self.file_info.setText(
            f"Archivo: {audio['file_name']} | {self._format_duration(audio['duration'])} | "
            f"SR {audio['sample_rate']} | {audio['channels']} ch"
        )
        self.duration_card.set_value(self._format_duration(audio["duration"]), f"{audio['duration']:.2f}s")
        self.log("Waveform cargado. Iniciando analisis offline...")
        self.start_analysis()

    def on_audio_load_failed(self, error: str) -> None:
        self._set_busy(False, "ERROR", "error de carga")
        self.logger.exception("Audio load failed: %s", error)
        QMessageBox.critical(self, "Error al cargar audio", error)
        self.log(f"Error al cargar audio: {error}")

    def start_analysis(self) -> None:
        if not self.current_file:
            return
        self._set_busy(True, "ANALYZING", "analizando BPM...")
        self.log("Analisis offline iniciado.")
        self.analysis_thread = AnalysisThread(self.current_file, self._analysis_params())
        self.analysis_thread.finished_ok.connect(self.on_analysis_complete)
        self.analysis_thread.failed.connect(self.on_analysis_failed)
        self.analysis_thread.canceled.connect(self.on_analysis_canceled)
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.finished.connect(self._on_analysis_thread_finished)
        self._track_thread(self.analysis_thread)
        self.analysis_thread.start()

    def on_analysis_progress(self, message: str) -> None:
        self.status_label.setText(f"Estado: {message}")
        self.log(message)

    def _on_audio_load_thread_finished(self) -> None:
        self._untrack_thread(self.audio_load_thread)
        self.audio_load_thread = None
        self._finish_close_if_idle()

    def _on_analysis_thread_finished(self) -> None:
        self._untrack_thread(self.analysis_thread)
        self.analysis_thread = None
        self._finish_close_if_idle()

    def on_analysis_complete(self, audio: dict, result: AnalysisResult) -> None:
        self.logger.info(
            "UI received analysis result | file=%s bpm_global=%.2f segments=%s",
            result.file_name,
            result.bpm_global,
            len(result.segments),
        )
        self.current_audio = audio
        self.analysis_result = result
        self.beat_offset_applied = 0.0
        self.beat_offset_spin.setValue(0.0)
        self._set_busy(False, "IDLE", "listo")
        self.file_info.setText(
            f"Archivo: {result.file_name} | {self._format_duration(result.duration)} | "
            f"SR {result.sample_rate} | {result.channels} ch"
        )
        beat_ms = 60000.0 / result.bpm_global if result.bpm_global > 0 else 0.0
        candidates = " / ".join(f"{value:.2f}" for value in result.bpm_candidates)
        self.global_bpm_card.set_value(f"{result.bpm_global:.2f}", "BPM estimado")
        self.global_bpm_card.set_accent(COLORS["green"] if result.confidence_global >= 0.7 else COLORS["cyan"])
        self.confidence_card.set_value(f"{result.confidence_global:.2f}")
        self.beat_ms_card.set_value(f"{beat_ms:.2f}", "ms por negra")
        self.candidates_card.set_value(candidates or "-")
        self.zone_count_card.set_value(str(len(result.segments)))
        self.duration_card.set_value(self._format_duration(result.duration), f"{result.duration:.2f}s")
        self.offline_timing_grid.set_beat_ms(beat_ms)
        self.waveform_widget.set_waveform(audio["waveform"], result.duration)
        self.waveform_widget.set_beats(result.beat_times)
        self.waveform_widget.set_segments(result.segments)
        self.segment_table.load_segments(result.segments)
        if result.segments:
            self.segment_table.selectRow(0)
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
        self._set_busy(False, "ERROR", "error de analisis")
        self.logger.exception("Analysis failed: %s", error)
        QMessageBox.critical(self, "Error de analisis", error)
        self.log(f"Error de analisis: {error}")

    def on_analysis_canceled(self) -> None:
        self._set_busy(False, "IDLE", "analisis cancelado")
        self.log("Analisis cancelado.")

    def toggle_playback(self) -> None:
        if not self.current_file:
            return
        if self.player.source().isEmpty():
            self.player.setSource(QUrl.fromLocalFile(self.current_file))
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop_playback(self) -> None:
        self.player.stop()
        self.waveform_widget.set_playhead(0.0)
        self.position_label.setText("00:00.000")

    def seek_playback(self, seconds: float) -> None:
        if self.current_file and self.player.source().isEmpty():
            self.player.setSource(QUrl.fromLocalFile(self.current_file))
        self.player.setPosition(int(max(0.0, seconds) * 1000))
        self.position_label.setText(self._format_position_ms(int(seconds * 1000)))

    def on_player_position_changed(self, milliseconds: int) -> None:
        seconds = milliseconds / 1000.0
        self.waveform_widget.set_playhead(seconds)
        self.position_label.setText(self._format_position_ms(milliseconds))

    def on_player_state_changed(self, state) -> None:
        self.play_button.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")

    def on_segment_selected(self, row: int) -> None:
        if self.analysis_result is None or row < 0 or row >= len(self.analysis_result.segments):
            return
        segment = self.analysis_result.segments[row]
        beat_ms = 60000.0 / segment.bpm if segment.bpm > 0 else 0.0
        self.zone_bpm_card.set_value(f"{segment.bpm:.2f}", f"{segment.start:.2f}s - {segment.end:.2f}s")
        self.zone_bpm_card.set_accent(COLORS["green"] if segment.confirmed else COLORS["cyan"])
        self.current_zone_card.set_value(
            f"#{row + 1}",
            "MANUAL" if segment.confirmed else f"Conf {segment.confidence:.2f}",
        )
        self.beat_ms_card.set_value(f"{beat_ms:.2f}", "ms zona actual")
        self.offline_timing_grid.set_beat_ms(beat_ms)
        self.waveform_widget.highlight_segment(row)

    def refresh_segment_view(self) -> None:
        if self.analysis_result is None:
            return
        self.waveform_widget.set_segments(self.analysis_result.segments)
        self.zone_count_card.set_value(str(len(self.analysis_result.segments)))
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

    def closeEvent(self, event: QCloseEvent) -> None:
        self.logger.info("Close requested")
        self.is_closing = True
        self._set_app_state("IDLE", "cerrando...")
        self.player.stop()
        self.live_panel.stop_live()
        if self.audio_load_thread is not None and self.audio_load_thread.isRunning():
            self.audio_load_thread.requestInterruption()
            self.log("Cancelando carga de audio...")
        if self.analysis_thread is not None and self.analysis_thread.isRunning():
            self.analysis_thread.requestInterruption()
            self.log("Cancelando analisis offline...")
        self.hide()
        self.logger.info("Close accepted; waiting for background work to finish")
        self._finish_close_if_idle()
        event.accept()
