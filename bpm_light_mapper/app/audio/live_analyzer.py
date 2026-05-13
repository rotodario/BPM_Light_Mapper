from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.signal import find_peaks

from bpm_light_mapper.app.audio.beat_tracker import compute_onset_envelope
from bpm_light_mapper.app.audio.tempo_candidate_resolver import resolve_tempo_candidates
from bpm_light_mapper.app.models.tempo_candidate import TempoCandidate
from bpm_light_mapper.app.utils.logging_utils import get_logger


@dataclass
class LiveUpdate:
    bpm: float
    confidence: float
    state: str
    level: float
    beat_ms: float
    history: list[float]
    tempo_candidates: list[TempoCandidate]
    change_detected: bool
    timestamp: float


@dataclass
class LiveVisualState:
    level: float
    peak: float
    rms_db: np.ndarray
    peak_db: np.ndarray
    waveform_min: np.ndarray
    waveform_max: np.ndarray
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
        visual_interval: float = 1.0 / 30.0,
        waveform_seconds: float = 2.5,
        waveform_columns: int = 360,
        hop_length: int = 512,
        bpm_min: float = 35.0,
        bpm_max: float = 240.0,
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
        self.visual_interval = visual_interval
        self.waveform_samples = int(waveform_seconds * sample_rate)
        self.waveform_columns = waveform_columns
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
        self.latest_peak = 0.0
        self.latest_visual = LiveVisualState(
            level=0.0,
            peak=0.0,
            rms_db=np.array([-60.0], dtype=np.float32),
            peak_db=np.array([-60.0], dtype=np.float32),
            waveform_min=np.zeros(self.waveform_columns, dtype=np.float32),
            waveform_max=np.zeros(self.waveform_columns, dtype=np.float32),
            timestamp=0.0,
        )
        self.latest_update: LiveUpdate | None = None
        self.history: list[float] = []
        self.last_bpms: list[float] = []
        self.smoothed_bpm = 0.0
        self.locked_bpm = 0.0
        self.pending_bpm = 0.0
        self.pending_count = 0
        self.low_level_count = 0
        self.latest_tempo_candidates: list[TempoCandidate] = []
        self.last_candidate_update = 0.0
        self.last_state = "searching"
        self.buffer_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.analysis_thread: threading.Thread | None = None
        self.visual_thread: threading.Thread | None = None
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
        self.visual_thread = threading.Thread(target=self._visual_loop, daemon=True)
        self.visual_thread.start()

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
        if self.visual_thread is not None and self.visual_thread.is_alive():
            self.visual_thread.join(timeout=1.0)
        self.visual_thread = None

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        del frames, time_info, status
        try:
            # The audio callback must stay cheap: convert, write, return.
            mono = np.mean(indata, axis=1)
            block = np.asarray(mono, dtype=np.float32)
            with self.buffer_lock:
                self._write_block(block)
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

    def _snapshot_recent(self, max_samples: int) -> np.ndarray | None:
        with self.buffer_lock:
            available = min(self.filled_samples, max_samples)
            if available <= 0:
                return None
            start = (self.write_index - available) % self.window_samples
            if start < self.write_index:
                return self.buffer[start : self.write_index].copy()
            return np.concatenate((self.buffer[start:], self.buffer[: self.write_index])).astype(np.float32, copy=False)

    def latest_live_update(self) -> LiveUpdate | None:
        with self.buffer_lock:
            return self.latest_update

    def latest_live_visual(self) -> LiveVisualState:
        with self.buffer_lock:
            return LiveVisualState(
                level=self.latest_visual.level,
                peak=self.latest_visual.peak,
                rms_db=self.latest_visual.rms_db.copy(),
                peak_db=self.latest_visual.peak_db.copy(),
                waveform_min=self.latest_visual.waveform_min.copy(),
                waveform_max=self.latest_visual.waveform_max.copy(),
                timestamp=self.latest_visual.timestamp,
            )

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

    def _visual_loop(self) -> None:
        next_run = time.time()
        while not self.stop_event.is_set():
            if self.stop_event.wait(max(0.0, next_run - time.time())):
                return
            next_run = time.time() + self.visual_interval
            samples = self._snapshot_recent(self.waveform_samples)
            if samples is None:
                continue
            visual = self._build_visual_state(samples, time.time())
            with self.buffer_lock:
                self.latest_visual = visual
                self.latest_level = visual.level
                self.latest_peak = visual.peak

    def _build_visual_state(self, samples: np.ndarray, now: float) -> LiveVisualState:
        if samples.size == 0:
            min_values = np.zeros(self.waveform_columns, dtype=np.float32)
            max_values = np.zeros(self.waveform_columns, dtype=np.float32)
            silence_db = np.array([-60.0], dtype=np.float32)
            return LiveVisualState(0.0, 0.0, silence_db, silence_db, min_values, max_values, now)

        peak, rms, peak_db, rms_db = self._meter_levels(samples)
        min_values, max_values = self._min_max_envelope(samples, self.waveform_columns)
        level = (self.latest_level * 0.80) + (rms * 0.20)
        peak_hold = max(peak, self.latest_peak * 0.92)
        return LiveVisualState(level, peak_hold, rms_db, peak_db, min_values, max_values, now)

    @staticmethod
    def _meter_levels(samples: np.ndarray) -> tuple[float, float, np.ndarray, np.ndarray]:
        values = np.asarray(samples, dtype=np.float32)
        if values.ndim == 1:
            channel_values = values.reshape(-1, 1)
        else:
            channel_values = values.reshape(values.shape[0], -1)
        abs_values = np.abs(channel_values)
        peak_by_channel = np.max(abs_values, axis=0)
        rms_by_channel = np.sqrt(np.mean(np.square(channel_values), axis=0))
        peak_db = LiveBpmAnalyzer._amplitude_to_dbfs(peak_by_channel)
        rms_db = LiveBpmAnalyzer._amplitude_to_dbfs(rms_by_channel)
        return (
            float(np.max(peak_by_channel)),
            float(np.max(rms_by_channel)),
            peak_db.astype(np.float32),
            rms_db.astype(np.float32),
        )

    @staticmethod
    def _amplitude_to_dbfs(values: np.ndarray) -> np.ndarray:
        safe_values = np.maximum(np.asarray(values, dtype=np.float32), 1e-9)
        return np.maximum(20.0 * np.log10(safe_values), -60.0)

    @staticmethod
    def _min_max_envelope(samples: np.ndarray, columns: int) -> tuple[np.ndarray, np.ndarray]:
        if columns <= 0:
            return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
        if samples.size < columns:
            padded = np.zeros(columns, dtype=np.float32)
            padded[-samples.size :] = samples
            samples = padded
        usable = (samples.size // columns) * columns
        if usable <= 0:
            return np.zeros(columns, dtype=np.float32), np.zeros(columns, dtype=np.float32)
        reshaped = samples[-usable:].reshape(columns, usable // columns)
        return reshaped.min(axis=1).astype(np.float32), reshaped.max(axis=1).astype(np.float32)

    def _process_window(self, window: np.ndarray, level: float, now: float) -> None:
        try:
            bpm, confidence = self._estimate_bpm(window)
            if level < 0.003:
                self.low_level_count += 1
                if self.low_level_count >= 8:
                    self._reset_tempo_lock()
            else:
                self.low_level_count = 0
            bpm = self._apply_hysteresis(bpm, confidence)
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

            variance = float(np.std(self.last_bpms)) if len(self.last_bpms) >= 6 else 999.0
            signal_present = level >= 0.003
            bpm_stable = len(self.last_bpms) >= 6 and variance < 1.5
            if signal_present and smoothed > 0.0 and bpm_stable and confidence >= 0.40:
                state = "locked"
            elif signal_present and smoothed > 0.0 and confidence >= 0.25:
                state = "unstable"
            else:
                state = "searching"

            change_detected = False
            if len(self.history) > 16:
                prev = self.history[-16]
                if abs(smoothed - prev) >= 3.0 and state != "searching":
                    change_detected = True

            if smoothed > 0.0 and (now - self.last_candidate_update >= 1.0 or not self.latest_tempo_candidates):
                candidate_onsets, candidate_times = compute_onset_envelope(
                    window,
                    self.sample_rate,
                    hop_length=self.hop_length,
                )
                candidate_beats = self._onset_peak_times(candidate_onsets, candidate_times)
                self.latest_tempo_candidates, _ = resolve_tempo_candidates(
                    smoothed,
                    candidate_beats,
                    candidate_onsets,
                    candidate_times,
                    self.bpm_min,
                    self.bpm_max,
                )
                self.last_candidate_update = now
            update = LiveUpdate(
                bpm=smoothed,
                confidence=confidence,
                state=state,
                level=level,
                beat_ms=(60000.0 / smoothed) if smoothed > 0 else 0.0,
                history=list(self.history),
                tempo_candidates=list(self.latest_tempo_candidates),
                change_detected=change_detected,
                timestamp=now,
            )
            with self.buffer_lock:
                self.latest_update = update
            if self.callback is not None:
                self.callback(update)
            self.last_state = state
        except Exception as exc:
            self._report_error(f"Error de analisis LIVE: {exc}")

    def _apply_hysteresis(self, bpm: float, confidence: float) -> float:
        if bpm <= 0.0:
            return self.locked_bpm if self.locked_bpm > 0.0 else 0.0
        if self.locked_bpm <= 0.0:
            if confidence < 0.25:
                return 0.0
            self.locked_bpm = bpm
            self.pending_bpm = 0.0
            self.pending_count = 0
            return bpm

        if confidence < 0.25:
            return self.locked_bpm

        ratio = bpm / self.locked_bpm
        same_tempo = 0.85 <= ratio <= 1.15
        octave_change = 0.45 <= ratio <= 0.55 or 1.8 <= ratio <= 2.2
        large_change = 0.60 <= ratio <= 0.85 or 1.15 <= ratio <= 1.65

        if same_tempo:
            self.locked_bpm = (self.locked_bpm * 0.8) + (bpm * 0.2)
            self.pending_bpm = 0.0
            self.pending_count = 0
            return self.locked_bpm

        if self.pending_bpm > 0.0 and abs(self.pending_bpm - bpm) <= max(1.0, self.pending_bpm * 0.08):
            self.pending_count += 1
        else:
            self.pending_bpm = bpm
            self.pending_count = 1

        required_hits = 5 if octave_change else 3
        if not octave_change and not large_change:
            required_hits = 3
        confidence_gate = 0.45 if octave_change else 0.40
        if self.pending_count >= required_hits and confidence >= confidence_gate:
            self.locked_bpm = bpm
            self.pending_bpm = 0.0
            self.pending_count = 0
            self.last_bpms.clear()
            self.logger.info("LIVE BPM relocked to %.2f after source/tempo change", bpm)
            return bpm

        return self.locked_bpm

    def _reset_tempo_lock(self) -> None:
        if self.locked_bpm <= 0.0 and self.pending_bpm <= 0.0:
            return
        self.logger.info("Resetting LIVE tempo lock after low-level audio")
        self.locked_bpm = 0.0
        self.pending_bpm = 0.0
        self.pending_count = 0
        self.last_bpms.clear()

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

        return bpm, float(np.clip(confidence, 0.0, 1.0))

    def _estimate_bpm_from_samples(self, samples: np.ndarray) -> tuple[float, float]:
        onset_env, _ = compute_onset_envelope(samples, self.sample_rate, hop_length=self.hop_length)
        if len(onset_env) < 12 or np.max(onset_env) <= 1e-6:
            return 0.0, 0.0
        onset_env = self._suppress_close_onset_repeats(onset_env)
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
        normalized_peak = max_local / max(float(corr[0]), 1e-9)
        sorted_peaks = np.sort(local)
        contrast = 0.0
        if len(sorted_peaks) >= 4 and sorted_peaks[-1] > 1e-9:
            contrast = float((sorted_peaks[-1] - sorted_peaks[-4]) / sorted_peaks[-1])
        energy_score = float(np.clip(np.percentile(onset_env, 90) * 1.4, 0.0, 1.0))
        bpm = self._resolve_techno_three_two_subdivision(corr, bpm)
        bpm = self._resolve_octave_by_peak_spacing(onset_env, bpm)
        confidence = (normalized_peak * 0.50) + (contrast * 0.25) + (energy_score * 0.25)
        return float(np.clip(bpm, self.bpm_min, self.bpm_max)), float(np.clip(confidence, 0.0, 1.0))

    def _suppress_close_onset_repeats(self, onset_env: np.ndarray) -> np.ndarray:
        """Remove very close repeated onset peaks that often come from click/reverb tails.

        This protects slow metronomes and sparse click-like sources from being
        interpreted as double-time while preserving normal musical beat spacing.
        """
        env = np.asarray(onset_env, dtype=float)
        if len(env) < 8 or np.max(env) <= 1e-9:
            return onset_env
        distance = max(1, int(round(0.16 * self.sample_rate / self.hop_length)))
        peaks, _ = find_peaks(env, distance=distance, prominence=max(0.02, float(np.max(env)) * 0.05))
        if len(peaks) < 3:
            return onset_env
        cleaned = np.zeros_like(env)
        cleaned[peaks] = env[peaks]
        # Keep a small floor of the original envelope so broad musical energy is
        # not completely discarded, but close click tails stop dominating timing.
        return np.maximum(cleaned, env * 0.08)

    def _resolve_techno_three_two_subdivision(self, corr: np.ndarray, bpm: float) -> float:
        """Promote common 80->120 metrical errors when the faster grid is supported.

        Some steady 4/4 electronic tracks expose a strong 3:2 correlation peak.
        The raw autocorrelation can then prefer ~80 BPM even when the useful
        lighting clock is clearly ~120 BPM. This is intentionally narrow: it
        only considers the x1.5 candidate in the normal dance-music area.
        """
        candidate = bpm * 1.5
        if not (70.0 <= bpm <= 95.0 and 105.0 <= candidate <= 145.0):
            return bpm
        if candidate < self.bpm_min or candidate > self.bpm_max:
            return bpm

        current_score = self._correlation_score_for_bpm(corr, bpm)
        candidate_score = self._correlation_score_for_bpm(corr, candidate)
        if current_score <= 1e-9:
            return bpm
        if candidate_score >= current_score * 0.62:
            self.logger.info(
                "LIVE BPM promoted from %.2f to %.2f by 3:2 subdivision resolver",
                bpm,
                candidate,
            )
            return candidate
        return bpm

    def _correlation_score_for_bpm(self, corr: np.ndarray, bpm: float) -> float:
        if bpm <= 0.0 or len(corr) == 0:
            return 0.0
        lag = int(round((60.0 * self.sample_rate) / (self.hop_length * bpm)))
        if lag <= 0 or lag >= len(corr):
            return 0.0
        start = max(1, lag - 1)
        end = min(len(corr), lag + 2)
        return float(np.max(corr[start:end]))

    def _resolve_octave_by_peak_spacing(self, onset_env: np.ndarray, bpm: float) -> float:
        candidates = [bpm]
        if bpm / 2.0 >= self.bpm_min:
            candidates.append(bpm / 2.0)
        if bpm * 2.0 <= self.bpm_max:
            candidates.append(bpm * 2.0)

        env = np.asarray(onset_env, dtype=float)
        if len(env) < 8 or np.max(env) <= 1e-9:
            return bpm

        env_max = max(float(np.max(env)), 1e-9)
        prominence = max(0.03, env_max * 0.08)
        peaks, _ = find_peaks(env, distance=2, prominence=prominence)
        if len(peaks) < 3:
            return bpm

        best_bpm = bpm
        best_score = self._tempo_match_score(peaks, env, bpm)
        for candidate in candidates[1:]:
            score = self._tempo_match_score(peaks, env, candidate)
            if score > best_score + 0.08:
                best_score = score
                best_bpm = candidate
        return best_bpm

    def _tempo_match_score(self, peaks: np.ndarray, onset_env: np.ndarray, bpm: float) -> float:
        if bpm <= 0.0 or len(peaks) < 3:
            return 0.0
        period = (60.0 * self.sample_rate) / (self.hop_length * bpm)
        if period <= 1.0:
            return 0.0
        env = np.asarray(onset_env, dtype=float)
        env_max = max(float(np.max(env)), 1e-9)
        interval_error = 0.0
        intervals = np.diff(peaks.astype(float))
        if len(intervals) > 0:
            normalized = np.abs(intervals - period) / max(period, 1e-9)
            interval_error = float(np.clip(np.median(normalized), 0.0, 2.0))
        interval_score = float(np.clip(1.0 - interval_error, 0.0, 1.0))

        tolerance = max(1, int(round(period * 0.18)))
        aligned = 0
        for peak in peaks:
            if abs((peak % max(1, int(round(period))))) <= tolerance:
                aligned += 1
        grid_score = aligned / len(peaks)
        peak_energy = float(np.mean(env[peaks]) / env_max) if len(peaks) else 0.0
        return (interval_score * 0.60) + (grid_score * 0.25) + (peak_energy * 0.15)

    @staticmethod
    def _onset_peak_times(onset_env: np.ndarray, onset_times: np.ndarray) -> np.ndarray:
        if len(onset_env) < 4 or len(onset_times) != len(onset_env):
            return np.zeros(0, dtype=float)
        env_max = max(float(np.max(onset_env)), 1e-9)
        peaks, _ = find_peaks(onset_env, distance=2, prominence=max(0.03, env_max * 0.08))
        return onset_times[peaks].astype(float)

    def _report_error(self, message: str) -> None:
        if message == self.last_error:
            return
        self.last_error = message
        self.logger.error(message)
        if self.error_callback is not None:
            self.error_callback(message)
