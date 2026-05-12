from __future__ import annotations

import threading
import time
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
        window_seconds: float = 10.0,
        update_interval: float = 0.25,
        hop_length: int = 512,
        bpm_min: float = 55.0,
        bpm_max: float = 190.0,
        callback: Callable[[LiveUpdate], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.logger = get_logger("live")
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.window_samples = int(window_seconds * sample_rate)
        self.update_interval = update_interval
        self.hop_length = hop_length
        self.bpm_min = bpm_min
        self.bpm_max = bpm_max
        self.callback = callback
        self.error_callback = error_callback
        self.stream: sd.InputStream | None = None
        self.buffer = np.zeros(self.window_samples, dtype=np.float32)
        self.write_index = 0
        self.filled_samples = 0
        self.latest_level = 0.0
        self.history: list[float] = []
        self.last_bpms: list[float] = []
        self.smoothed_bpm = 0.0
        self.last_state = "searching"
        self.buffer_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.analysis_thread: threading.Thread | None = None
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
        self.logger.info(
            "Starting live analyzer on device=%s sr=%s block_size=%s window_samples=%s update_interval=%.3f",
            self.device,
            self.sample_rate,
            self.block_size,
            self.window_samples,
            self.update_interval,
        )
        self.stop_event.clear()
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.channels,
            device=self.device,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

    def stop(self) -> None:
        self.logger.info("Stopping live analyzer")
        self.stop_event.set()
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.analysis_thread is not None and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=1.0)
        self.analysis_thread = None

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        del frames, time_info, status
        try:
            mono = np.mean(indata, axis=1)
            level = float(np.sqrt(np.mean(np.square(mono)))) if len(mono) else 0.0
            block = np.asarray(mono, dtype=np.float32)
            with self.buffer_lock:
                self._write_block(block)
                self.latest_level = (self.latest_level * 0.75) + (level * 0.25)
        except Exception as exc:
            self._report_error(f"Error en callback LIVE: {exc}")

    def _write_block(self, block: np.ndarray) -> None:
        if block.size == 0:
            return
        if block.size >= self.window_samples:
            self.buffer[:] = block[-self.window_samples :]
            self.write_index = 0
            self.filled_samples = self.window_samples
            return
        end = self.write_index + block.size
        if end <= self.window_samples:
            self.buffer[self.write_index : end] = block
        else:
            first = self.window_samples - self.write_index
            self.buffer[self.write_index :] = block[:first]
            self.buffer[: end % self.window_samples] = block[first:]
        self.write_index = end % self.window_samples
        self.filled_samples = min(self.window_samples, self.filled_samples + block.size)

    def _snapshot_window(self) -> tuple[np.ndarray | None, float]:
        with self.buffer_lock:
            if self.filled_samples < self.window_samples:
                return None, self.latest_level
            if self.write_index == 0:
                window = self.buffer.copy()
            else:
                window = np.concatenate((self.buffer[self.write_index :], self.buffer[: self.write_index])).astype(
                    np.float32,
                    copy=False,
                )
            return window, self.latest_level

    def _analysis_loop(self) -> None:
        next_run = time.time()
        while not self.stop_event.is_set():
            now = time.time()
            wait = max(0.0, next_run - now)
            if self.stop_event.wait(wait):
                return
            next_run = time.time() + self.update_interval
            window, level = self._snapshot_window()
            if window is None:
                continue
            self._process_window(window, level, time.time())

    def _process_window(self, window: np.ndarray, level: float, now: float) -> None:
        try:
            bpm, confidence = self._estimate_bpm(window)
            if bpm <= 0.0:
                smoothed = self.smoothed_bpm
            elif self.smoothed_bpm <= 0.0:
                smoothed = bpm
            else:
                alpha = 0.18 + (0.30 * confidence)
                if abs(bpm - self.smoothed_bpm) >= 4.0 and confidence >= 0.55:
                    alpha = 0.65
                smoothed = (self.smoothed_bpm * (1.0 - alpha)) + (bpm * alpha)
            self.smoothed_bpm = smoothed

            if bpm > 0.0:
                self.last_bpms.append(smoothed)
                self.last_bpms = self.last_bpms[-12:]
            if smoothed > 0.0:
                self.history.append(smoothed)
                self.history = self.history[-240:]

            variance = float(np.std(self.last_bpms)) if len(self.last_bpms) > 3 else 999.0
            if confidence > 0.68 and variance < 1.2:
                state = "locked"
            elif confidence > 0.38 and smoothed > 0.0:
                state = "unstable"
            else:
                state = "searching"

            change_detected = False
            if len(self.history) > 16:
                prev = self.history[-16]
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

    def _estimate_bpm(self, samples: np.ndarray) -> tuple[float, float]:
        full_bpm, full_confidence = self._estimate_bpm_from_samples(samples)
        recent_seconds = 4.5
        recent_samples = int(recent_seconds * self.sample_rate)
        recent_bpm, recent_confidence = self._estimate_bpm_from_samples(samples[-recent_samples:])

        if recent_confidence > full_confidence + 0.08 and recent_confidence >= 0.45:
            bpm, confidence = recent_bpm, recent_confidence
        else:
            bpm = full_bpm
            confidence = (full_confidence * 0.75) + (recent_confidence * 0.25)

        if bpm <= 0.0:
            return 0.0, 0.0

        if self.smoothed_bpm > 0.0:
            related = np.array([bpm / 2.0, bpm, bpm * 2.0], dtype=float)
            valid = related[(related >= self.bpm_min) & (related <= self.bpm_max)]
            if valid.size:
                bpm = float(valid[int(np.argmin(np.abs(valid - self.smoothed_bpm)))])
        return bpm, float(np.clip(confidence, 0.0, 1.0))

    def _estimate_bpm_from_samples(self, samples: np.ndarray) -> tuple[float, float]:
        onset_env, _ = compute_onset_envelope(samples, self.sample_rate, hop_length=self.hop_length)
        if len(onset_env) < 12 or np.max(onset_env) <= 1e-6:
            return 0.0, 0.0
        novelty = onset_env.astype(float) - float(np.mean(onset_env))
        novelty *= np.hanning(len(novelty))
        corr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
        lag_min = max(1, int(np.floor((60.0 / self.bpm_max) * self.sample_rate / self.hop_length)))
        lag_max = min(len(corr) - 1, int(np.ceil((60.0 / self.bpm_min) * self.sample_rate / self.hop_length)))
        if lag_max <= lag_min:
            return 0.0, 0.0
        local = corr[lag_min : lag_max + 1]
        if len(local) == 0 or np.max(local) <= 1e-9:
            return 0.0, 0.0
        peak_index = int(np.argmax(local))
        lag = float(lag_min + peak_index)
        if 0 < peak_index < len(local) - 1:
            left = float(local[peak_index - 1])
            center = float(local[peak_index])
            right = float(local[peak_index + 1])
            denom = left - (2.0 * center) + right
            if abs(denom) > 1e-9:
                lag += float(np.clip(0.5 * (left - right) / denom, -0.5, 0.5))

        bpm = 60.0 * self.sample_rate / (self.hop_length * lag)
        while bpm < self.bpm_min:
            bpm *= 2.0
        while bpm > self.bpm_max:
            bpm /= 2.0
        max_local = float(np.max(local))
        if bpm < 85.0 and bpm * 2.0 <= self.bpm_max:
            double_lag = lag / 2.0
            double_index = int(round(double_lag - lag_min))
            double_strength = 0.0
            if 0 <= double_index < len(local) and max_local > 1e-9:
                double_strength = float(local[double_index]) / max_local
            previous_prefers_double = (
                self.smoothed_bpm > 0.0
                and abs((bpm * 2.0) - self.smoothed_bpm) < abs(bpm - self.smoothed_bpm)
            )
            if double_strength >= 0.35 or previous_prefers_double:
                bpm *= 2.0

        normalized_peak = max_local / max(float(corr[0]), 1e-9)
        sorted_peaks = np.sort(local)
        contrast = 0.0
        if len(sorted_peaks) >= 4 and sorted_peaks[-1] > 1e-9:
            contrast = float((sorted_peaks[-1] - sorted_peaks[-4]) / sorted_peaks[-1])
        energy_score = float(np.clip(np.percentile(onset_env, 90) * 1.4, 0.0, 1.0))
        confidence = (normalized_peak * 0.55) + (contrast * 0.30) + (energy_score * 0.15)
        return float(np.clip(bpm, self.bpm_min, self.bpm_max)), float(np.clip(confidence, 0.0, 1.0))

    def _report_error(self, message: str) -> None:
        if message == self.last_error:
            return
        self.last_error = message
        self.logger.error(message)
        if self.error_callback is not None:
            self.error_callback(message)
