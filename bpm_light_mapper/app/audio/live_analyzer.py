from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd

from bpm_light_mapper.app.audio.beat_tracker import compute_onset_envelope
from bpm_light_mapper.app.utils.logging_utils import get_logger


@dataclass
class LiveUpdate:
    bpm: float
    confidence: float
    state: str
    level: float
    beat_ms: float
    history: list[float]
    change_detected: bool
    timestamp: float


class LiveBpmAnalyzer:
    def __init__(
        self,
        device: int | None,
        sample_rate: int = 22050,
        channels: int = 1,
        block_size: int = 1024,
        window_seconds: float = 8.0,
        callback: Callable[[LiveUpdate], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.logger = get_logger("live")
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.window_samples = int(window_seconds * sample_rate)
        self.callback = callback
        self.error_callback = error_callback
        self.stream: sd.InputStream | None = None
        self.buffer = deque(maxlen=self.window_samples)
        self.history = deque(maxlen=180)
        self.last_bpms = deque(maxlen=8)
        self.last_emit = 0.0
        self.last_state = "searching"
        self.buffer_lock = threading.Lock()
        self.analysis_running = False
        self.last_error: str | None = None

    @staticmethod
    def list_input_devices() -> list[tuple[int, str]]:
        devices = sd.query_devices()
        result = []
        for idx, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                result.append((idx, device["name"]))
        return result

    def start(self) -> None:
        self.logger.info("Starting live analyzer on device=%s sr=%s block_size=%s", self.device, self.sample_rate, self.block_size)
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.channels,
            device=self.device,
            callback=self._audio_callback,
        )
        self.stream.start()

    def stop(self) -> None:
        self.logger.info("Stopping live analyzer")
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        del frames, time_info, status
        try:
            mono = np.mean(indata, axis=1)
            level = float(np.sqrt(np.mean(np.square(mono)))) if len(mono) else 0.0
            with self.buffer_lock:
                for sample in mono:
                    self.buffer.append(float(sample))

            now = time.time()
            if now - self.last_emit < 0.5 or self.analysis_running:
                return
            with self.buffer_lock:
                if len(self.buffer) < self.window_samples:
                    return
                window = np.array(self.buffer, dtype=np.float32)
            self.last_emit = now
            self.analysis_running = True
            threading.Thread(
                target=self._process_window,
                args=(window, level, now),
                daemon=True,
            ).start()
        except Exception as exc:
            self._report_error(f"Error en callback LIVE: {exc}")

    def _process_window(self, window: np.ndarray, level: float, now: float) -> None:
        try:
            bpm, confidence = self._estimate_bpm(window)
            self.last_bpms.append(bpm)
            smoothed = float(np.median(list(self.last_bpms))) if self.last_bpms else bpm
            self.history.append(smoothed)

            variance = float(np.std(self.last_bpms)) if len(self.last_bpms) > 1 else 999.0
            if confidence > 0.75 and variance < 1.5:
                state = "locked"
            elif confidence > 0.45:
                state = "unstable"
            else:
                state = "searching"

            change_detected = False
            if len(self.history) > 10:
                prev = list(self.history)[-10]
                if abs(smoothed - prev) >= 3.0 and state != "searching":
                    change_detected = True

            if self.callback is not None:
                self.callback(
                    LiveUpdate(
                        bpm=smoothed,
                        confidence=confidence,
                        state=state,
                        level=level,
                        beat_ms=(60000.0 / smoothed) if smoothed > 0 else 0.0,
                        history=list(self.history),
                        change_detected=change_detected,
                        timestamp=now,
                    )
                )
            self.last_state = state
        except Exception as exc:
            self._report_error(f"Error de analisis LIVE: {exc}")
        finally:
            self.analysis_running = False

    def _estimate_bpm(self, samples: np.ndarray) -> tuple[float, float]:
        onset_env, _ = compute_onset_envelope(samples, self.sample_rate, hop_length=1024)
        if len(onset_env) < 8 or np.max(onset_env) <= 1e-6:
            return 0.0, 0.0
        novelty = onset_env.astype(float) - float(np.mean(onset_env))
        corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
        lag_min = max(1, int(np.floor((60.0 / 190.0) * self.sample_rate / 1024)))
        lag_max = min(len(corr) - 1, int(np.ceil((60.0 / 55.0) * self.sample_rate / 1024)))
        if lag_max <= lag_min:
            return 0.0, 0.0
        local = corr[lag_min : lag_max + 1]
        if len(local) == 0 or np.max(local) <= 1e-9:
            return 0.0, 0.0
        lag = lag_min + int(np.argmax(local))
        bpm = 60.0 * self.sample_rate / (1024 * lag)
        while bpm < 55.0:
            bpm *= 2.0
        while bpm > 190.0:
            bpm /= 2.0
        confidence = float(np.clip(float(np.max(local)) / max(float(corr[0]), 1e-9), 0.0, 1.0))
        return bpm, confidence

    def _report_error(self, message: str) -> None:
        if message == self.last_error:
            return
        self.last_error = message
        self.logger.error(message)
        if self.error_callback is not None:
            self.error_callback(message)
