"""
Live ADS1115 scale/noise/FFT analysis suite.

Changes vs the earlier live script
---------------------------------
- Slice the live window using device timestamps when available, not host arrival time.
- Drain the serial port aggressively to reduce batching and stale host timestamps.
- Track actual received frame rate per channel.
- Add live FFT plots for both channels over the selected window.
- Decouple acquisition from UI refresh so plotting does not throttle reads.
- Survive serial unplug/replug and automatically reconnect to the same port.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Optional

from serial import Serial, SerialException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psychopy_apparatus.utils.protocol import (  # noqa: E402
    ADDR_SERVER,
    CMD_FORCE_START,
    CMD_FORCE_STOP,
    DATA_FORCE,
    FLAG_ACK_REQUIRED,
    MSG_ACK,
    MSG_NACK,
    build_message,
    cobs_decode,
    cobs_encode,
    encode_force_start_payload,
    parse_force_data_payload,
    parse_message,
)

try:
    import numpy as np
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"numpy is required for this script: {exc}")

try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, CheckButtons, Slider
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"matplotlib is required for this script: {exc}")


VISIBLE_OPTIONS = ("A1", "A2", "Center", "Fit")


class COBSFrameStream:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        frames: list[bytes] = []
        for byte in data:
            if byte == 0:
                if self._buffer:
                    frames.append(bytes(self._buffer))
                    self._buffer.clear()
            else:
                self._buffer.append(byte)
        return frames

    def clear(self) -> None:
        self._buffer.clear()


@dataclass
class RateStats:
    first_host_ts: Optional[float] = None
    last_host_ts: Optional[float] = None
    count: int = 0

    def update(self, host_ts: float) -> None:
        host_ts = float(host_ts)
        if self.first_host_ts is None:
            self.first_host_ts = host_ts
        self.last_host_ts = host_ts
        self.count += 1

    @property
    def host_rate_hz(self) -> float:
        if self.first_host_ts is None or self.last_host_ts is None or self.count < 2:
            return 0.0
        span = self.last_host_ts - self.first_host_ts
        if span <= 0.0:
            return 0.0
        return (self.count - 1) / span


@dataclass
class ChannelState:
    label: str
    color: str
    times_host_s: Deque[float]
    times_dev_us: Deque[int]
    raw_counts: Deque[float]
    received_stats: RateStats = field(default_factory=RateStats)

    def update(self, host_ts: float, raw_value: int, dev_us: int) -> None:
        self.times_host_s.append(float(host_ts))
        self.times_dev_us.append(int(dev_us))
        self.raw_counts.append(float(raw_value))
        self.received_stats.update(float(host_ts))


@dataclass
class SpectrumAnalysis:
    freqs_hz: np.ndarray
    amps: np.ndarray
    sample_rate_hz: float
    nyquist_hz: float
    dominant_freq_hz: float
    dominant_amp: float

    def mirrored_plot(self, max_hz: float) -> tuple[np.ndarray, np.ndarray]:
        """
        Return a display spectrum that can extend beyond Nyquist by mirroring the
        one-sided FFT about Nyquist.

        This does not recover out-of-band content from the sampled data. It is a
        visualization aid for alias hunting: a tone at f_alias can also be shown
        at fs - f_alias.
        """
        if self.freqs_hz.size == 0 or self.amps.size == 0 or self.sample_rate_hz <= 0.0:
            return np.asarray([]), np.asarray([])

        max_hz = float(max_hz)
        if max_hz <= 0.0:
            return np.asarray([]), np.asarray([])

        base_mask = self.freqs_hz <= min(max_hz, self.nyquist_hz)
        plot_freqs = [self.freqs_hz[base_mask]]
        plot_amps = [self.amps[base_mask]]

        if max_hz > self.nyquist_hz:
            mirror_freqs = self.sample_rate_hz - self.freqs_hz[1:-1]
            mirror_amps = self.amps[1:-1]
            mirror_mask = (mirror_freqs > self.nyquist_hz) & (mirror_freqs <= max_hz)
            if np.any(mirror_mask):
                plot_freqs.append(mirror_freqs[mirror_mask])
                plot_amps.append(mirror_amps[mirror_mask])

        if len(plot_freqs) == 1:
            return plot_freqs[0], plot_amps[0]

        freqs = np.concatenate(plot_freqs)
        amps = np.concatenate(plot_amps)
        order = np.argsort(freqs)
        return freqs[order], amps[order]


@dataclass
class WindowAnalysis:
    count: int
    sample_rate_hz: float
    host_rate_hz: float
    mean: float
    std: float
    rms: float
    p2p: float
    min_value: float
    max_value: float
    slope_counts_per_s: float
    intercept: float
    fit_y: np.ndarray
    residuals: np.ndarray
    residual_std: float
    lag1: float
    n_eff: float
    sem_counts: float
    two_window_95_counts: float
    two_window_3sigma_counts: float
    drift_95_counts_per_window: float
    r_squared: float
    time_axis_s: np.ndarray
    raw_values: np.ndarray
    spectrum: SpectrumAnalysis


def send_command(ser: Serial, seq: int, msg_type: int, payload: bytes, dst: int = ADDR_SERVER) -> None:
    msg = build_message(msg_type=msg_type, seq=seq, payload=payload, dst=dst, flags=FLAG_ACK_REQUIRED)
    ser.write(cobs_encode(msg))


def decode_frame(frame: bytes):
    try:
        decoded = cobs_decode(frame)
        parsed = parse_message(decoded)
        if parsed is None:
            return None, None, decoded
        header, payload = parsed
        return header, payload, decoded
    except Exception:
        return None, None, b""


def compute_sample_interval_s(host_times: np.ndarray, dev_times_us: np.ndarray) -> float:
    if dev_times_us.size >= 2:
        diffs = np.diff(dev_times_us.astype(float)) / 1_000_000.0
        diffs = diffs[diffs > 0]
        if diffs.size:
            return float(np.median(diffs))
    if host_times.size >= 2:
        diffs = np.diff(host_times.astype(float))
        diffs = diffs[diffs > 0]
        if diffs.size:
            return float(np.median(diffs))
    return 0.0


def compute_host_rate_hz(host_times: np.ndarray) -> float:
    if host_times.size < 2:
        return 0.0
    diffs = np.diff(host_times.astype(float))
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return 0.0
    return 1.0 / float(np.median(diffs))


def preferred_time_axis_s(host_times: np.ndarray, dev_times_us: np.ndarray) -> np.ndarray:
    if dev_times_us.size:
        dev = dev_times_us.astype(float) / 1_000_000.0
        return dev - float(dev[0])
    if host_times.size:
        host = host_times.astype(float)
        return host - float(host[0])
    return np.asarray([], dtype=float)


def slice_recent(channel: ChannelState, now_s: float, window_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    host = np.asarray(channel.times_host_s, dtype=float)
    dev = np.asarray(channel.times_dev_us, dtype=np.int64)
    raw = np.asarray(channel.raw_counts, dtype=float)
    if raw.size == 0:
        return host, dev, raw

    if dev.size:
        cutoff_dev_us = int(dev[-1] - max(0.0, window_s) * 1_000_000.0)
        mask = dev >= cutoff_dev_us
    else:
        cutoff_host = float(now_s) - max(0.0, window_s)
        mask = host >= cutoff_host
    return host[mask], dev[mask], raw[mask]


def compute_lag1(values: np.ndarray) -> float:
    if values.size < 3:
        return 0.0
    x0 = values[:-1]
    x1 = values[1:]
    std0 = float(np.std(x0))
    std1 = float(np.std(x1))
    if std0 <= 0.0 or std1 <= 0.0:
        return 0.0
    rho = float(np.corrcoef(x0, x1)[0, 1])
    if not np.isfinite(rho):
        return 0.0
    return max(-0.95, min(0.95, rho))


def compute_spectrum(host_times: np.ndarray, dev_times_us: np.ndarray, values: np.ndarray) -> SpectrumAnalysis:
    if values.size < 8:
        return SpectrumAnalysis(np.asarray([]), np.asarray([]), 0.0, 0.0, 0.0, 0.0)

    dt_s = compute_sample_interval_s(host_times, dev_times_us)
    if dt_s <= 0.0:
        return SpectrumAnalysis(np.asarray([]), np.asarray([]), 0.0, 0.0, 0.0, 0.0)

    sample_rate_hz = 1.0 / dt_s
    nyquist_hz = sample_rate_hz * 0.5
    centered = values.astype(float) - float(np.mean(values))
    window = np.hanning(centered.size)
    scaled = centered * window
    spectrum = np.fft.rfft(scaled)
    freqs = np.fft.rfftfreq(centered.size, d=dt_s)
    amps = np.abs(spectrum) * (2.0 / max(1.0, np.sum(window)))

    dominant_freq_hz = 0.0
    dominant_amp = 0.0
    if amps.size > 1:
        idx = 1 + int(np.argmax(amps[1:]))
        dominant_freq_hz = float(freqs[idx])
        dominant_amp = float(amps[idx])

    return SpectrumAnalysis(freqs, amps, sample_rate_hz, nyquist_hz, dominant_freq_hz, dominant_amp)


def compute_window_analysis(host_times: np.ndarray, dev_times_us: np.ndarray, raw_values: np.ndarray) -> Optional[WindowAnalysis]:
    if raw_values.size == 0:
        return None

    x = preferred_time_axis_s(host_times, dev_times_us)
    y = raw_values.astype(float)
    n = int(y.size)
    fs = 0.0
    dt_s = compute_sample_interval_s(host_times, dev_times_us)
    if dt_s > 0.0:
        fs = 1.0 / dt_s
    host_rate_hz = compute_host_rate_hz(host_times)

    mean = float(np.mean(y))
    std = float(np.std(y, ddof=1)) if n > 1 else 0.0
    centered = y - mean
    rms = float(np.sqrt(np.mean(centered ** 2)))
    p2p = float(np.max(y) - np.min(y))
    min_value = float(np.min(y))
    max_value = float(np.max(y))

    slope = 0.0
    intercept = mean
    fit_y = np.full_like(y, mean, dtype=float)
    residuals = y - fit_y
    residual_std = std
    r_squared = 0.0
    drift_95 = 0.0

    if n >= 3 and x.size == y.size and float(np.ptp(x)) > 0.0:
        slope, intercept = np.polyfit(x, y, 1)
        fit_y = (slope * x) + intercept
        residuals = y - fit_y
        residual_std = float(np.std(residuals, ddof=1)) if n > 2 else 0.0

        ss_tot = float(np.sum((y - mean) ** 2))
        ss_res = float(np.sum((y - fit_y) ** 2))
        if ss_tot > 0.0:
            r_squared = max(0.0, 1.0 - (ss_res / ss_tot))

        sxx = float(np.sum((x - np.mean(x)) ** 2))
        if n > 2 and sxx > 0.0:
            sigma2 = ss_res / float(n - 2)
            slope_se = math.sqrt(max(0.0, sigma2 / sxx))
            drift_95 = 1.96 * slope_se * float(np.ptp(x))

    lag1 = compute_lag1(residuals)
    n_eff = float(n)
    if n > 1 and abs(1.0 + lag1) > 1e-9:
        n_eff = n * (1.0 - lag1) / (1.0 + lag1)
        n_eff = max(1.0, min(float(n), n_eff))

    noise_for_detection = residual_std if residual_std > 0.0 else std
    sem = noise_for_detection / math.sqrt(n_eff) if n_eff > 0 else 0.0
    two_window_95 = 1.96 * noise_for_detection * math.sqrt(2.0 / n_eff) if n_eff > 0 else 0.0
    two_window_3sigma = 3.0 * noise_for_detection * math.sqrt(2.0 / n_eff) if n_eff > 0 else 0.0
    spectrum = compute_spectrum(host_times, dev_times_us, y)

    return WindowAnalysis(
        count=n,
        sample_rate_hz=fs,
        host_rate_hz=host_rate_hz,
        mean=mean,
        std=std,
        rms=rms,
        p2p=p2p,
        min_value=min_value,
        max_value=max_value,
        slope_counts_per_s=float(slope),
        intercept=float(intercept),
        fit_y=fit_y,
        residuals=residuals,
        residual_std=float(noise_for_detection),
        lag1=float(lag1),
        n_eff=float(n_eff),
        sem_counts=float(sem),
        two_window_95_counts=float(two_window_95),
        two_window_3sigma_counts=float(two_window_3sigma),
        drift_95_counts_per_window=float(drift_95),
        r_squared=float(r_squared),
        time_axis_s=x,
        raw_values=y,
        spectrum=spectrum,
    )


def counts_to_grams(counts: float, full_scale_kg: Optional[float], full_scale_counts: float) -> Optional[float]:
    if full_scale_kg is None or full_scale_counts <= 0:
        return None
    grams_per_count = (full_scale_kg * 1000.0) / full_scale_counts
    return counts * grams_per_count


class ScaleAnalysisUI:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.visible = {0: True, 1: True}
        self.center = False
        self.show_fit = True
        self.last_notice = "waiting for data"
        self.last_ack = "disconnected"
        self.current_requested_rate_hz = float(args.rate_hz)
        self.pending_requested_rate_hz: Optional[float] = None

        self.fig = plt.figure(figsize=(18, 10))
        self.fig.canvas.manager.set_window_title("ADC Scale Analysis + FFT")

        self.raw_ax = self.fig.add_axes([0.05, 0.58, 0.48, 0.33])
        self.resid_ax = self.fig.add_axes([0.05, 0.30, 0.48, 0.18])
        self.fft_ax = self.fig.add_axes([0.57, 0.58, 0.22, 0.33])
        self.hist_ax = self.fig.add_axes([0.81, 0.58, 0.16, 0.33])
        self.summary_ax = self.fig.add_axes([0.57, 0.18, 0.40, 0.28])
        self.summary_ax.axis("off")

        self.raw_ax.set_title("Selected Window: Raw ADC Counts")
        self.raw_ax.set_xlabel("Time (s)")
        self.raw_ax.set_ylabel("Counts")
        self.raw_ax.grid(True, alpha=0.3)

        self.resid_ax.set_title("Selected Window: Residual Noise After Line Fit")
        self.resid_ax.set_xlabel("Time (s)")
        self.resid_ax.set_ylabel("Residual")
        self.resid_ax.grid(True, alpha=0.3)

        self.fft_ax.set_title("Selected Window: FFT (mirrored above Nyquist for alias view)")
        self.fft_ax.set_xlabel("Frequency (Hz)")
        self.fft_ax.set_ylabel("Amplitude")
        self.fft_ax.grid(True, alpha=0.3)

        self.hist_ax.set_title("Selected Window: Residual Histogram")
        self.hist_ax.set_xlabel("Residual Counts")
        self.hist_ax.set_ylabel("Density")
        self.hist_ax.grid(True, alpha=0.3)

        self.raw_lines = {
            0: self.raw_ax.plot([], [], color="#c1121f", lw=1.1, label="A1 raw")[0],
            1: self.raw_ax.plot([], [], color="#005f73", lw=1.1, label="A2 raw")[0],
        }
        self.fit_lines = {
            0: self.raw_ax.plot([], [], color="#780000", lw=1.8, alpha=0.85, label="A1 fit")[0],
            1: self.raw_ax.plot([], [], color="#0a9396", lw=1.8, alpha=0.85, label="A2 fit")[0],
        }
        self.resid_lines = {
            0: self.resid_ax.plot([], [], color="#c1121f", lw=1.0, label="A1 residual")[0],
            1: self.resid_ax.plot([], [], color="#005f73", lw=1.0, label="A2 residual")[0],
        }
        self.fft_lines = {
            0: self.fft_ax.plot([], [], color="#c1121f", lw=1.2, label="A1 FFT")[0],
            1: self.fft_ax.plot([], [], color="#005f73", lw=1.2, label="A2 FFT")[0],
        }

        self.raw_ax.legend(loc="upper right")
        self.resid_ax.legend(loc="upper right")
        self.fft_ax.legend(loc="upper right")
        self.summary_text = self.summary_ax.text(
            0.0,
            1.0,
            "",
            ha="left",
            va="top",
            family="monospace",
            fontsize=9,
        )

        checks_ax = self.fig.add_axes([0.05, 0.07, 0.16, 0.14])
        window_ax = self.fig.add_axes([0.25, 0.12, 0.24, 0.03])
        rate_ax = self.fig.add_axes([0.25, 0.07, 0.24, 0.03])
        fft_max_ax = self.fig.add_axes([0.57, 0.10, 0.20, 0.03])
        ui_rate_ax = self.fig.add_axes([0.57, 0.05, 0.20, 0.03])
        apply_rate_ax = self.fig.add_axes([0.80, 0.10, 0.08, 0.05])
        reset_ax = self.fig.add_axes([0.89, 0.10, 0.08, 0.05])

        self.check_buttons = CheckButtons(checks_ax, VISIBLE_OPTIONS, (True, True, False, True))
        self.window_slider = Slider(
            window_ax,
            "window (s)",
            1.0,
            max(5.0, float(args.buffer_seconds)),
            valinit=float(args.window_seconds),
            valstep=0.5,
        )
        self.rate_slider = Slider(
            rate_ax,
            "req Hz",
            5.0,
            250.0,
            valinit=float(args.rate_hz),
            valstep=5.0,
        )
        self.fft_max_slider = Slider(
            fft_max_ax,
            "FFT max Hz",
            5.0,
            200.0,
            valinit=float(args.fft_max_hz),
            valstep=1.0,
        )
        self.ui_rate_slider = Slider(
            ui_rate_ax,
            "UI Hz",
            2.0,
            60.0,
            valinit=float(args.ui_refresh_hz),
            valstep=1.0,
        )
        self.apply_rate_button = Button(apply_rate_ax, "Apply Hz")
        self.reset_button = Button(reset_ax, "Reset Y")

        self.check_buttons.on_clicked(self._handle_checks)
        self.window_slider.on_changed(self._handle_window_change)
        self.rate_slider.on_changed(self._handle_rate_change)
        self.fft_max_slider.on_changed(self._handle_fft_change)
        self.ui_rate_slider.on_changed(self._handle_ui_rate_change)
        self.apply_rate_button.on_clicked(self._apply_rate)
        self.reset_button.on_clicked(self._reset_y)
        plt.show(block=False)

    def _handle_checks(self, _label) -> None:
        states = self.check_buttons.get_status()
        self.visible[0] = bool(states[0])
        self.visible[1] = bool(states[1])
        self.center = bool(states[2])
        self.show_fit = bool(states[3])

    def _handle_window_change(self, _value) -> None:
        self.last_notice = f"window set to {self.window_slider.val:.1f}s"

    def _handle_rate_change(self, _value) -> None:
        self.last_notice = f"requested rate slider {self.rate_slider.val:.1f} Hz"

    def _handle_fft_change(self, _value) -> None:
        self.last_notice = f"FFT max set to {self.fft_max_slider.val:.1f} Hz"

    def _handle_ui_rate_change(self, _value) -> None:
        self.last_notice = f"UI refresh target {self.ui_rate_slider.val:.1f} Hz"

    def _apply_rate(self, _event) -> None:
        self.pending_requested_rate_hz = float(self.rate_slider.val)
        self.last_notice = f"queued rate change to {self.pending_requested_rate_hz:.1f} Hz"

    def _reset_y(self, _event) -> None:
        self.last_notice = "plot limits reset"
        self.raw_ax.relim()
        self.raw_ax.autoscale_view()
        self.resid_ax.relim()
        self.resid_ax.autoscale_view()
        self.fft_ax.relim()
        self.fft_ax.autoscale_view()

    def is_closed(self) -> bool:
        return not plt.fignum_exists(self.fig.number)

    def consume_requested_rate_hz(self) -> Optional[float]:
        rate = self.pending_requested_rate_hz
        self.pending_requested_rate_hz = None
        return rate

    def target_ui_period_s(self) -> float:
        return 1.0 / max(1.0, float(self.ui_rate_slider.val))

    def update(self, channels: dict[int, ChannelState], now_s: float) -> None:
        window_s = float(self.window_slider.val)
        analyses: dict[int, Optional[WindowAnalysis]] = {}

        raw_y_candidates: list[float] = []
        resid_y_candidates: list[float] = []
        fft_y_candidates: list[float] = []
        hist_has_data = False
        self.hist_ax.clear()
        self.hist_ax.set_title("Selected Window: Residual Histogram")
        self.hist_ax.set_xlabel("Residual Counts")
        self.hist_ax.set_ylabel("Density")
        self.hist_ax.grid(True, alpha=0.3)

        fft_max_hz = float(self.fft_max_slider.val)

        for device in (0, 1):
            host, dev, raw = slice_recent(channels[device], now_s, window_s)
            analysis = compute_window_analysis(host, dev, raw)
            analyses[device] = analysis

            if analysis is None or not self.visible[device]:
                self.raw_lines[device].set_data([], [])
                self.fit_lines[device].set_data([], [])
                self.resid_lines[device].set_data([], [])
                self.fft_lines[device].set_data([], [])
                continue

            y = analysis.raw_values - analysis.mean if self.center else analysis.raw_values
            fit_y = analysis.fit_y - analysis.mean if self.center else analysis.fit_y

            self.raw_lines[device].set_data(analysis.time_axis_s, y)
            self.fit_lines[device].set_data(analysis.time_axis_s if self.show_fit else [], fit_y if self.show_fit else [])
            self.resid_lines[device].set_data(analysis.time_axis_s, analysis.residuals)

            raw_y_candidates.extend([float(np.min(y)), float(np.max(y))])
            resid_y_candidates.extend([float(np.min(analysis.residuals)), float(np.max(analysis.residuals))])

            if analysis.residuals.size:
                self.hist_ax.hist(
                    analysis.residuals,
                    bins=min(40, max(10, analysis.residuals.size // 10)),
                    density=True,
                    alpha=0.45,
                    color=channels[device].color,
                    label=channels[device].label,
                )
                hist_has_data = True

            freqs, amps = analysis.spectrum.mirrored_plot(fft_max_hz)
            if freqs.size:
                self.fft_lines[device].set_data(freqs, amps)
                if amps.size:
                    fft_y_candidates.append(float(np.max(amps)))
            else:
                self.fft_lines[device].set_data([], [])

        if hist_has_data:
            self.hist_ax.legend(loc="upper right")

        x_right = window_s
        for analysis in analyses.values():
            if analysis is not None and analysis.time_axis_s.size:
                x_right = max(x_right, float(analysis.time_axis_s[-1]))
        self.raw_ax.set_xlim(max(0.0, x_right - window_s), max(window_s, x_right))
        self.resid_ax.set_xlim(max(0.0, x_right - window_s), max(window_s, x_right))

        if raw_y_candidates:
            ymin = min(raw_y_candidates)
            ymax = max(raw_y_candidates)
            if math.isclose(ymin, ymax):
                ymin -= 1.0
                ymax += 1.0
            pad = max(2.0, 0.08 * (ymax - ymin))
            self.raw_ax.set_ylim(ymin - pad, ymax + pad)

        if resid_y_candidates:
            ymin = min(resid_y_candidates)
            ymax = max(resid_y_candidates)
            if math.isclose(ymin, ymax):
                ymin -= 1.0
                ymax += 1.0
            pad = max(2.0, 0.08 * (ymax - ymin))
            self.resid_ax.set_ylim(ymin - pad, ymax + pad)

        self.fft_ax.set_xlim(0.0, fft_max_hz)
        if fft_y_candidates:
            ymax = max(fft_y_candidates)
            self.fft_ax.set_ylim(0.0, ymax * 1.15 if ymax > 0.0 else 1.0)
        else:
            self.fft_ax.set_ylim(0.0, 1.0)

        summary_lines = [
            f"Window: {window_s:4.1f}s",
            f"Req Hz: {self.current_requested_rate_hz:5.1f}",
            f"Notice: {self.last_notice}",
            f"Link:   {self.last_ack}",
            "",
        ]

        for device in (0, 1):
            analysis = analyses[device]
            if analysis is None:
                summary_lines.append(f"{channels[device].label}: no data in window")
                summary_lines.append("")
                continue

            grams95 = counts_to_grams(
                analysis.two_window_95_counts,
                self.args.full_scale_kg,
                self.args.full_scale_counts,
            )
            grams3 = counts_to_grams(
                analysis.two_window_3sigma_counts,
                self.args.full_scale_kg,
                self.args.full_scale_counts,
            )
            drift_grams = counts_to_grams(
                analysis.drift_95_counts_per_window,
                self.args.full_scale_kg,
                self.args.full_scale_counts,
            )

            summary_lines.append(
                f"{channels[device].label}: n={analysis.count:4d} fs_dev={analysis.sample_rate_hz:6.1f}Hz "
                f"fs_host={analysis.host_rate_hz:6.1f}Hz mean={analysis.mean:9.2f} std={analysis.std:7.2f}"
            )
            summary_lines.append(
                f"  noise(resid std)={analysis.residual_std:7.2f} p2p={analysis.p2p:7.2f} "
                f"lag1={analysis.lag1:+5.2f} neff={analysis.n_eff:6.1f}"
            )
            summary_lines.append(
                f"  line slope={analysis.slope_counts_per_s:+8.3f} cnt/s "
                f"drift95/window={analysis.drift_95_counts_per_window:7.2f} cnt "
                f"R2={analysis.r_squared:5.3f}"
            )
            summary_lines.append(
                f"  detect mean95={1.96 * analysis.sem_counts:7.2f} cnt "
                f"step95(two windows)={analysis.two_window_95_counts:7.2f} cnt "
                f"step3sigma={analysis.two_window_3sigma_counts:7.2f} cnt"
            )
            summary_lines.append(
                f"  FFT peak={analysis.spectrum.dominant_freq_hz:7.2f} Hz amp={analysis.spectrum.dominant_amp:7.2f} "
                f"(Nyquist {analysis.spectrum.nyquist_hz:7.2f} Hz)"
            )
            if grams95 is not None and grams3 is not None and drift_grams is not None:
                summary_lines.append(
                    f"  approx grams: step95={grams95:7.3f} g "
                    f"step3sigma={grams3:7.3f} g drift95/window={drift_grams:7.3f} g"
                )
            summary_lines.append("")

        summary_lines.append("Interpretation:")
        summary_lines.append("  fs_dev uses device timestamps; fs_host uses host arrival timing.")
        summary_lines.append("  FFT above Nyquist is mirrored for alias hunting only; it is not recovered out-of-band data.")
        summary_lines.append("  step95(two windows): smallest step likely distinguishable between two equal windows")
        summary_lines.append("  line drift95/window: smallest ramp across the window likely distinguishable from noise")
        self.summary_text.set_text("\n".join(summary_lines))

        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()


class SerialLinkManager:
    def __init__(self, args: argparse.Namespace, ui: ScaleAnalysisUI, decoder: COBSFrameStream) -> None:
        self.args = args
        self.ui = ui
        self.decoder = decoder
        self.ser: Optional[Serial] = None
        self.connected = False
        self.seq = 1
        self.last_connect_attempt = 0.0
        self.reconnect_interval_s = max(0.2, float(args.reconnect_interval))

    def is_open(self) -> bool:
        return self.ser is not None and bool(getattr(self.ser, "is_open", False))

    def close(self, reason: str) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.connected = False
        self.decoder.clear()
        self.ui.last_ack = f"disconnected: {reason}"
        self.ui.last_notice = f"waiting for {self.args.port}"

    def try_connect(self) -> bool:
        now = time.monotonic()
        if self.is_open():
            return True
        if (now - self.last_connect_attempt) < self.reconnect_interval_s:
            return False
        self.last_connect_attempt = now

        try:
            self.ser = Serial(self.args.port, self.args.baudrate, timeout=self.args.serial_timeout)
            print(f"[INFO] Opened {self.args.port} @ {self.args.baudrate}")
            if self.args.startup_delay > 0.0:
                time.sleep(max(0.0, self.args.startup_delay))
            try:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            except Exception:
                pass
            self.connected = True
            self.decoder.clear()
            if self.args.no_start:
                self.ui.last_ack = "passive listen mode"
                self.ui.last_notice = f"connected to {self.args.port}"
            else:
                self.send_start(float(self.ui.current_requested_rate_hz))
            return True
        except Exception as exc:
            self.ser = None
            self.connected = False
            self.ui.last_ack = f"reconnect failed: {exc}"
            self.ui.last_notice = f"retrying {self.args.port}"
            return False

    def send_start(self, rate_hz: float) -> None:
        if self.args.no_start or not self.is_open() or self.ser is None:
            return
        start_payload = encode_force_start_payload(rate_hz=rate_hz, device=self.args.device)
        send_command(self.ser, seq=self.seq, msg_type=CMD_FORCE_START, payload=start_payload, dst=ADDR_SERVER)
        print(f"[TX] CMD_FORCE_START seq={self.seq} device={self.args.device} rate_hz={rate_hz:.3f}")
        self.ui.current_requested_rate_hz = float(rate_hz)
        self.ui.last_ack = f"start sent; waiting for ACK seq={self.seq}"
        self.ui.last_notice = f"connected to {self.args.port}"
        self.seq += 1

    def send_stop(self) -> None:
        if self.args.no_start or not self.is_open() or self.ser is None:
            return
        try:
            send_command(self.ser, seq=self.seq, msg_type=CMD_FORCE_STOP, payload=b"", dst=ADDR_SERVER)
            print(f"[TX] CMD_FORCE_STOP seq={self.seq}")
            self.seq += 1
        except Exception as exc:
            print(f"[WARN] Failed to send CMD_FORCE_STOP: {exc}")

    def read_chunk(self) -> bytes:
        if not self.is_open() or self.ser is None:
            return b""
        try:
            waiting = self.ser.in_waiting
            return self.ser.read(waiting or 1)
        except (SerialException, PermissionError, OSError) as exc:
            print(f"[WARN] Serial disconnected while reading: {exc}")
            self.close(str(exc))
            return b""

    def safe_reconfigure_rate(self, rate_hz: float) -> bool:
        if self.args.no_start:
            return False
        if not self.is_open() or self.ser is None:
            self.ui.pending_requested_rate_hz = rate_hz
            self.ui.last_notice = f"queued rate change to {rate_hz:.1f} Hz after reconnect"
            return False
        try:
            self.send_start(rate_hz)
            return True
        except (SerialException, PermissionError, OSError) as exc:
            print(f"[WARN] Rate change failed; reconnecting: {exc}")
            self.ui.pending_requested_rate_hz = rate_hz
            self.close(str(exc))
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Live scale/noise/FFT analysis for raw 16-bit ADC stream.")
    parser.add_argument("port", help="Serial port, e.g. COM6")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--rate-hz", type=float, default=100.0, help="Requested firmware stream rate")
    parser.add_argument(
        "--device",
        choices=("white", "blue", "both"),
        default="both",
        help="Which device/channel selection to request from firmware",
    )
    parser.add_argument("--startup-delay", type=float, default=2.0, help="Seconds to wait before sending start command")
    parser.add_argument("--buffer-seconds", type=float, default=30.0, help="Ring buffer length in seconds")
    parser.add_argument("--window-seconds", type=float, default=5.0, help="Default analysis window length")
    parser.add_argument("--stats-interval", type=float, default=1.0, help="Console print interval")
    parser.add_argument("--serial-timeout", type=float, default=0.005, help="Serial read timeout")
    parser.add_argument("--ui-refresh-hz", type=float, default=15.0, help="Target UI refresh rate")
    parser.add_argument("--fft-max-hz", type=float, default=80.0, help="Initial FFT x-axis max")
    parser.add_argument("--no-start", action="store_true", help="Passive listen only; do not send CMD_FORCE_START")
    parser.add_argument("--full-scale-kg", type=float, default=None, help="Optional full-scale mass for count->gram estimates")
    parser.add_argument(
        "--full-scale-counts",
        type=float,
        default=65535.0,
        help="Counts corresponding to the full-scale mass if --full-scale-kg is set",
    )
    parser.add_argument(
        "--reconnect-interval",
        type=float,
        default=0.75,
        help="Seconds between reconnect attempts after unplugging",
    )
    args = parser.parse_args()

    max_samples = max(2000, int(max(5.0, args.buffer_seconds) * max(100.0, args.rate_hz, 250.0) * 2.5))
    channels = {
        0: ChannelState("A1", "#c1121f", deque(maxlen=max_samples), deque(maxlen=max_samples), deque(maxlen=max_samples)),
        1: ChannelState("A2", "#005f73", deque(maxlen=max_samples), deque(maxlen=max_samples), deque(maxlen=max_samples)),
    }

    ui = ScaleAnalysisUI(args)
    decoder = COBSFrameStream()
    link = SerialLinkManager(args, ui, decoder)

    last_print = time.monotonic()
    last_ui_update = 0.0

    try:
        while not ui.is_closed():
            if not link.is_open():
                link.try_connect()
                time.sleep(0.02)

            data = link.read_chunk()
            loop_now = time.monotonic()

            if data:
                for frame in decoder.feed(data):
                    frame_now = time.monotonic()
                    header, payload, _decoded = decode_frame(frame)
                    if header is None:
                        continue
                    msg_type = header["msg_type"]
                    seq_rx = header["seq"]

                    if msg_type == MSG_ACK:
                        ui.last_ack = f"ACK seq={seq_rx}"
                        continue
                    if msg_type == MSG_NACK:
                        ui.last_ack = f"NACK seq={seq_rx}"
                        continue
                    if msg_type != DATA_FORCE:
                        continue

                    parsed = parse_force_data_payload(payload)
                    if parsed is None:
                        continue
                    dev_us = int(parsed["time_us"])
                    value = int(parsed["raw_value"])
                    device = int(parsed["device"])
                    if device not in channels:
                        continue
                    channels[device].update(frame_now, value, dev_us)

            requested_rate_hz = ui.consume_requested_rate_hz()
            if requested_rate_hz is not None:
                link.safe_reconfigure_rate(float(requested_rate_hz))

            ui_period_s = ui.target_ui_period_s()
            if (loop_now - last_ui_update) >= ui_period_s:
                ui.update(channels, loop_now)
                plt.pause(0.001)
                last_ui_update = loop_now

            if loop_now - last_print >= args.stats_interval:
                last_print = loop_now
                for device in (0, 1):
                    host, dev, raw = slice_recent(channels[device], loop_now, float(ui.window_slider.val))
                    analysis = compute_window_analysis(host, dev, raw)
                    if analysis is None:
                        print(f"{channels[device].label}: no data")
                        continue
                    print(
                        f"{channels[device].label}: n={analysis.count} fs_dev={analysis.sample_rate_hz:6.1f}Hz "
                        f"fs_host={analysis.host_rate_hz:6.1f}Hz mean={analysis.mean:8.2f} "
                        f"noise={analysis.residual_std:6.2f} peak={analysis.spectrum.dominant_freq_hz:6.2f}Hz "
                        f"step95={analysis.two_window_95_counts:6.2f} slope={analysis.slope_counts_per_s:+7.3f}cnt/s"
                    )
                print(f"[LINK] {ui.last_ack}")
    finally:
        link.send_stop()
        link.close("shutdown")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
