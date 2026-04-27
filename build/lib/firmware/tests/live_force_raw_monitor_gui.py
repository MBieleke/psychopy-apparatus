"""
Live GUI monitor for Apparatus force packets with embedded raw ADC counts.

Features
--------
- Connect/disconnect from a selectable COM port and baudrate
- Start/stop force streaming from the GUI
- Numeric display for calibrated force and raw ADC counts on both channels
- Live receive-rate display
- Optional live time-series plot
- Optional FFT view for any combination of force/raw and right/left channels
- Tolerant to serial disconnects and malformed frames

Examples
--------
py firmware/tests/live_force_raw_monitor_gui.py
py firmware/tests/live_force_raw_monitor_gui.py --baudrate 921600 --device both --rate-hz 250
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import ttk
from typing import Deque, Optional

from serial import Serial
from serial.serialutil import SerialException
from serial.tools import list_ports

try:
    import numpy as np
except Exception as exc:  # pragma: no cover - runtime environment dependent
    raise SystemExit(f"numpy is required for this script: {exc}")

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception as exc:  # pragma: no cover - runtime environment dependent
    raise SystemExit(f"matplotlib is required for this script: {exc}")

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


POLL_MS = 20
PLOT_MS = 150
PLOT_WINDOW_S = 10.0
RATE_WINDOW_S = 2.0
SERIES_MAXLEN = 8192
DISCONNECT_TIMEOUT_S = 2.5
COMMON_BAUDS = ("115200", "230400", "460800", "921600")
DEVICE_NAMES = {0: "right/white", 1: "left/blue"}


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


@dataclass
class RateWindow:
    times: Deque[float] = field(default_factory=lambda: deque(maxlen=4096))

    def add(self, ts: float) -> None:
        self.times.append(ts)

    def rate_hz(self, now: float, window_s: float = RATE_WINDOW_S) -> float:
        while self.times and (now - self.times[0]) > window_s:
            self.times.popleft()
        if len(self.times) < 2:
            return 0.0
        span = self.times[-1] - self.times[0]
        if span <= 0:
            return 0.0
        return (len(self.times) - 1) / span


@dataclass
class SampleSeries:
    times: Deque[float] = field(default_factory=lambda: deque(maxlen=SERIES_MAXLEN))
    values: Deque[float] = field(default_factory=lambda: deque(maxlen=SERIES_MAXLEN))

    def append(self, ts: float, value: float) -> None:
        self.times.append(ts)
        self.values.append(value)

    def recent_arrays(self, now: float, window_s: float = PLOT_WINDOW_S) -> tuple[np.ndarray, np.ndarray]:
        if not self.times:
            return np.asarray([]), np.asarray([])
        ts = np.asarray(self.times, dtype=float)
        values = np.asarray(self.values, dtype=float)
        mask = ts >= (now - window_s)
        return ts[mask], values[mask]


def safe_close_serial(ser: Optional[Serial]) -> None:
    if ser is None:
        return
    try:
        ser.close()
    except Exception:
        pass


class ForceRawMonitorGUI:
    def __init__(self, initial_baudrate: int, initial_rate_hz: float, initial_device: str) -> None:
        self.root = tk.Tk()
        self.root.title("Apparatus Force + Raw Monitor")
        self.root.geometry("1360x920")
        self.root.minsize(1120, 760)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.serial: Optional[Serial] = None
        self.decoder = COBSFrameStream()
        self.seq = 1
        self.running = True
        self.last_rx_s = 0.0

        self.series_force = {0: SampleSeries(), 1: SampleSeries()}
        self.series_raw = {0: SampleSeries(), 1: SampleSeries()}
        self.rate_total = RateWindow()
        self.rate_device = {0: RateWindow(), 1: RateWindow()}
        self.frame_count = 0

        self.port_var = tk.StringVar(value="")
        self.baud_var = tk.StringVar(value=str(initial_baudrate))
        self.stream_rate_var = tk.StringVar(value=f"{initial_rate_hz:g}")
        self.stream_device_var = tk.StringVar(value=initial_device)
        self.status_var = tk.StringVar(value="Disconnected")
        self.note_var = tk.StringVar(value="Select a COM port and connect")

        self.right_force_var = tk.StringVar(value="--")
        self.left_force_var = tk.StringVar(value="--")
        self.right_raw_var = tk.StringVar(value="--")
        self.left_raw_var = tk.StringVar(value="--")
        self.total_hz_var = tk.StringVar(value="0.0 Hz")
        self.right_hz_var = tk.StringVar(value="0.0 Hz")
        self.left_hz_var = tk.StringVar(value="0.0 Hz")
        self.frames_var = tk.StringVar(value="0")

        self.show_plot_var = tk.BooleanVar(value=True)
        self.show_fft_var = tk.BooleanVar(value=False)
        self.hold_sample_var = tk.BooleanVar(value=False)
        self.show_right_force_var = tk.BooleanVar(value=True)
        self.show_left_force_var = tk.BooleanVar(value=True)
        self.show_right_raw_var = tk.BooleanVar(value=True)
        self.show_left_raw_var = tk.BooleanVar(value=True)
        self.auto_start_var = tk.BooleanVar(value=True)
        self.stream_requested = False
        self.hold_capture_time: Optional[float] = None
        self.held_series_force = {
            0: (np.asarray([], dtype=float), np.asarray([], dtype=float)),
            1: (np.asarray([], dtype=float), np.asarray([], dtype=float)),
        }
        self.held_series_raw = {
            0: (np.asarray([], dtype=float), np.asarray([], dtype=float)),
            1: (np.asarray([], dtype=float), np.asarray([], dtype=float)),
        }
        self.held_fft_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}

        self._build_ui()
        self.refresh_ports()
        self.root.after(POLL_MS, self.poll_serial)
        self.root.after(PLOT_MS, self.refresh_plot)

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="COM").grid(row=0, column=0, sticky="w")
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=18)
        self.port_box.grid(row=0, column=1, padx=(6, 8), sticky="w")
        ttk.Button(top, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=(0, 12))

        ttk.Label(top, text="Baud").grid(row=0, column=3, sticky="w")
        self.baud_box = ttk.Combobox(top, textvariable=self.baud_var, values=COMMON_BAUDS, width=10)
        self.baud_box.grid(row=0, column=4, padx=(6, 12), sticky="w")

        self.connect_button = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=5, padx=(0, 6))
        self.disconnect_button = ttk.Button(top, text="Disconnect", command=self.disconnect)
        self.disconnect_button.grid(row=0, column=6, padx=(0, 12))
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=7, sticky="w")

        ttk.Label(top, text="Rate Hz").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(top, textvariable=self.stream_rate_var, width=10).grid(row=1, column=1, padx=(6, 8), pady=(10, 0), sticky="w")
        ttk.Label(top, text="Device").grid(row=1, column=3, sticky="w", pady=(10, 0))
        self.device_box = ttk.Combobox(top, textvariable=self.stream_device_var, values=("white", "blue", "both"), width=10, state="readonly")
        self.device_box.grid(row=1, column=4, padx=(6, 12), pady=(10, 0), sticky="w")
        ttk.Checkbutton(top, text="Auto-start on connect", variable=self.auto_start_var).grid(row=1, column=5, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(top, text="Start Stream", command=self.start_stream).grid(row=1, column=7, padx=(0, 6), pady=(10, 0), sticky="w")
        ttk.Button(top, text="Stop Stream", command=self.stop_stream).grid(row=1, column=8, pady=(10, 0), sticky="w")

        summary = ttk.LabelFrame(self.root, text="Live Values", padding=10)
        summary.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(summary, text="Right Force").grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.right_force_var, font=("Consolas", 16)).grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Label(summary, text="Right Raw").grid(row=0, column=2, sticky="w")
        ttk.Label(summary, textvariable=self.right_raw_var, font=("Consolas", 16)).grid(row=0, column=3, sticky="w", padx=(8, 18))
        ttk.Label(summary, text="Right Hz").grid(row=0, column=4, sticky="w")
        ttk.Label(summary, textvariable=self.right_hz_var, font=("Consolas", 14)).grid(row=0, column=5, sticky="w", padx=(8, 18))

        ttk.Label(summary, text="Left Force").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.left_force_var, font=("Consolas", 16)).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(summary, text="Left Raw").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.left_raw_var, font=("Consolas", 16)).grid(row=1, column=3, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(summary, text="Left Hz").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.left_hz_var, font=("Consolas", 14)).grid(row=1, column=5, sticky="w", padx=(8, 18), pady=(8, 0))

        ttk.Label(summary, text="Total RX Hz").grid(row=0, column=6, sticky="w")
        ttk.Label(summary, textvariable=self.total_hz_var, font=("Consolas", 14)).grid(row=0, column=7, sticky="w", padx=(8, 18))
        ttk.Label(summary, text="Frames").grid(row=1, column=6, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.frames_var, font=("Consolas", 14)).grid(row=1, column=7, sticky="w", padx=(8, 18), pady=(8, 0))

        options = ttk.LabelFrame(self.root, text="Display Options", padding=10)
        options.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Checkbutton(options, text="Live Plot", variable=self.show_plot_var, command=self._refresh_plot_once).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options, text="FFT", variable=self.show_fft_var, command=self._refresh_plot_once).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Checkbutton(options, text="Hold Sample", variable=self.hold_sample_var, command=self.on_hold_sample_toggle).grid(row=0, column=2, sticky="w", padx=(18, 0))
        ttk.Checkbutton(options, text="Right Force", variable=self.show_right_force_var, command=self._refresh_plot_once).grid(row=0, column=3, sticky="w", padx=(18, 0))
        ttk.Checkbutton(options, text="Left Force", variable=self.show_left_force_var, command=self._refresh_plot_once).grid(row=0, column=4, sticky="w", padx=(12, 0))
        ttk.Checkbutton(options, text="Right Raw", variable=self.show_right_raw_var, command=self._refresh_plot_once).grid(row=0, column=5, sticky="w", padx=(12, 0))
        ttk.Checkbutton(options, text="Left Raw", variable=self.show_left_raw_var, command=self._refresh_plot_once).grid(row=0, column=6, sticky="w", padx=(12, 0))

        figure_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        figure_frame.pack(fill="both", expand=True)

        self.figure = Figure(figsize=(11, 7), dpi=100)
        self.ax_plot = self.figure.add_subplot(211)
        self.ax_fft = self.figure.add_subplot(212)
        self.figure.tight_layout(pad=2.0)
        self.canvas = FigureCanvasTkAgg(self.figure, master=figure_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        bottom = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.note_var).pack(side="left")

    def refresh_ports(self) -> None:
        ports = [port.device for port in list_ports.comports()]
        self.port_box["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def connect(self) -> None:
        if self.serial is not None:
            return
        port = self.port_var.get().strip()
        if not port:
            self.note_var.set("No COM port selected")
            return
        try:
            baudrate = int(self.baud_var.get().strip())
        except ValueError:
            self.note_var.set("Invalid baudrate")
            return

        try:
            self.serial = Serial(port, baudrate=baudrate, timeout=0.0)
            time.sleep(2.0)
            try:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
            except Exception:
                pass
        except (SerialException, OSError, PermissionError, ValueError) as exc:
            self.serial = None
            self.status_var.set("Disconnected")
            self.note_var.set(f"Connect failed: {exc}")
            return

        self.decoder = COBSFrameStream()
        self.status_var.set(f"Connected: {port} @ {baudrate}")
        self.note_var.set("Connected")
        self.last_rx_s = time.monotonic()

        if self.auto_start_var.get():
            self.start_stream()

    def disconnect(self) -> None:
        safe_close_serial(self.serial)
        self.serial = None
        self.decoder = COBSFrameStream()
        self.status_var.set("Disconnected")
        self.note_var.set("Disconnected")

    def on_close(self) -> None:
        self.running = False
        self.disconnect()
        self.root.destroy()

    def set_link_lost(self, reason: str) -> None:
        self.disconnect()
        self.note_var.set(reason)

    def _send_message(self, msg_type: int, payload: bytes) -> None:
        if self.serial is None:
            self.note_var.set("Not connected")
            return
        message = build_message(
            msg_type=msg_type,
            seq=self.seq,
            payload=payload,
            dst=ADDR_SERVER,
            flags=FLAG_ACK_REQUIRED,
        )
        self.seq += 1
        try:
            self.serial.write(cobs_encode(message))
        except (SerialException, OSError, PermissionError) as exc:
            self.set_link_lost(f"Write failed: {exc}")

    def start_stream(self) -> None:
        try:
            rate_hz = float(self.stream_rate_var.get().strip())
        except ValueError:
            self.note_var.set("Invalid stream rate")
            return
        try:
            payload = encode_force_start_payload(rate_hz, self.stream_device_var.get().strip())
        except Exception as exc:
            self.note_var.set(f"Invalid stream settings: {exc}")
            return
        self.stream_requested = True
        if self.hold_sample_var.get():
            self.note_var.set("Hold sample active: stream start deferred until hold is released")
            return
        self._send_message(CMD_FORCE_START, payload)
        self.note_var.set(f"Requested stream start: {rate_hz:g} Hz, {self.stream_device_var.get().strip()}")

    def stop_stream(self) -> None:
        self.stream_requested = False
        self._send_message(CMD_FORCE_STOP, b"")
        self.note_var.set("Requested stream stop")

    def _capture_hold_sample(self, now: float) -> None:
        self.hold_capture_time = now
        for device in (0, 1):
            self.held_series_force[device] = self.series_force[device].recent_arrays(now)
            self.held_series_raw[device] = self.series_raw[device].recent_arrays(now)
        self.held_fft_cache = {}
        for label, ts, values in (
            ("Right Force", *self.held_series_force[0]),
            ("Left Force", *self.held_series_force[1]),
            ("Right Raw", *self.held_series_raw[0]),
            ("Left Raw", *self.held_series_raw[1]),
        ):
            fft_data = self._compute_fft_data(ts, values)
            if fft_data is not None:
                self.held_fft_cache[label] = fft_data

    def on_hold_sample_toggle(self) -> None:
        hold_enabled = self.hold_sample_var.get()
        if hold_enabled:
            now = time.monotonic()
            self._capture_hold_sample(now)
            if self.serial is not None and self.stream_requested:
                self._send_message(CMD_FORCE_STOP, b"")
            self.note_var.set("Hold sample enabled: live capture frozen and FFT uses the held sample")
        else:
            self.hold_capture_time = None
            self.held_fft_cache = {}
            if self.serial is not None and self.stream_requested:
                self.start_stream()
            else:
                self.note_var.set("Hold sample released")
        self._refresh_plot_once()

    def _handle_force_sample(self, now: float, sample: dict) -> None:
        if self.hold_sample_var.get():
            return
        device = int(sample["device"])
        if device not in (0, 1):
            return

        force_value = float(sample["value"])
        raw_counts = sample["adc_raw_counts"]

        self.series_force[device].append(now, force_value)
        if raw_counts is not None:
            self.series_raw[device].append(now, float(raw_counts))

        self.rate_total.add(now)
        self.rate_device[device].add(now)
        self.frame_count += 1
        self.last_rx_s = now

        if device == 0:
            self.right_force_var.set(f"{force_value:8.3f} N")
            self.right_raw_var.set("--" if raw_counts is None else f"{int(raw_counts):8d}")
        else:
            self.left_force_var.set(f"{force_value:8.3f} N")
            self.left_raw_var.set("--" if raw_counts is None else f"{int(raw_counts):8d}")

    def _handle_frame(self, header: dict, payload: bytes) -> None:
        msg_type = int(header["msg_type"])
        now = time.monotonic()

        if msg_type == DATA_FORCE:
            try:
                sample = parse_force_data_payload(payload)
            except Exception as exc:
                self.note_var.set(f"Force parse error: {exc}")
                return
            self._handle_force_sample(now, sample)
            return

        if msg_type == MSG_ACK:
            self.note_var.set("ACK received")
            return

        if msg_type == MSG_NACK:
            self.note_var.set(f"NACK received: {payload.hex()}")
            return

    def poll_serial(self) -> None:
        if not self.running:
            return

        if self.serial is not None:
            try:
                waiting = self.serial.in_waiting or 1
                data = self.serial.read(waiting)
            except (SerialException, OSError, PermissionError) as exc:
                self.set_link_lost(f"Link lost: {exc}")
                data = b""

            if data:
                for frame in self.decoder.feed(data):
                    try:
                        decoded = cobs_decode(frame)
                        parsed = parse_message(decoded)
                    except Exception:
                        continue
                    if parsed is None:
                        continue
                    header, payload = parsed
                    self._handle_frame(header, payload)

            now = time.monotonic()
            self.total_hz_var.set(f"{self.rate_total.rate_hz(now):6.1f} Hz")
            self.right_hz_var.set(f"{self.rate_device[0].rate_hz(now):6.1f} Hz")
            self.left_hz_var.set(f"{self.rate_device[1].rate_hz(now):6.1f} Hz")
            self.frames_var.set(str(self.frame_count))

            if self.serial is not None and not self.hold_sample_var.get() and (now - self.last_rx_s) > DISCONNECT_TIMEOUT_S:
                # Keep the app alive even if the link goes quiet; only show it in status.
                self.note_var.set("Connected, waiting for DATA_FORCE frames")

        self.root.after(POLL_MS, self.poll_serial)

    def _selected_series(self, now: float) -> list[tuple[str, np.ndarray, np.ndarray, str]]:
        selected: list[tuple[str, np.ndarray, np.ndarray, str]] = []
        hold_enabled = self.hold_sample_var.get() and self.hold_capture_time is not None
        if self.show_right_force_var.get():
            t, y = self.held_series_force[0] if hold_enabled else self.series_force[0].recent_arrays(now)
            selected.append(("Right Force", t, y, "#1f77b4"))
        if self.show_left_force_var.get():
            t, y = self.held_series_force[1] if hold_enabled else self.series_force[1].recent_arrays(now)
            selected.append(("Left Force", t, y, "#ff7f0e"))
        if self.show_right_raw_var.get():
            t, y = self.held_series_raw[0] if hold_enabled else self.series_raw[0].recent_arrays(now)
            selected.append(("Right Raw", t, y, "#2ca02c"))
        if self.show_left_raw_var.get():
            t, y = self.held_series_raw[1] if hold_enabled else self.series_raw[1].recent_arrays(now)
            selected.append(("Left Raw", t, y, "#d62728"))
        return selected

    def _draw_time_plot(self, selected: list[tuple[str, np.ndarray, np.ndarray, str]], now: float) -> None:
        self.ax_plot.clear()
        self.ax_plot.set_title("Held Signal" if self.hold_sample_var.get() else "Live Signal")
        self.ax_plot.set_xlabel("Seconds Ago")
        self.ax_plot.set_ylabel("Value")
        if not self.show_plot_var.get():
            self.ax_plot.text(0.5, 0.5, "Live plot disabled", ha="center", va="center", transform=self.ax_plot.transAxes)
            self.ax_plot.set_xticks([])
            self.ax_plot.set_yticks([])
            return
        plotted = False
        for label, ts, values, color in selected:
            if ts.size == 0:
                continue
            x = ts - now
            self.ax_plot.plot(x, values, lw=1.2, label=label, color=color)
            plotted = True
        if plotted:
            self.ax_plot.set_xlim(-PLOT_WINDOW_S, 0.0)
            self.ax_plot.grid(True, alpha=0.3)
            self.ax_plot.legend(loc="upper left", ncol=2)
        else:
            self.ax_plot.text(0.5, 0.5, "No samples yet", ha="center", va="center", transform=self.ax_plot.transAxes)
            self.ax_plot.set_xticks([])
            self.ax_plot.set_yticks([])

    def _compute_fft_data(self, ts: np.ndarray, values: np.ndarray) -> Optional[tuple[np.ndarray, np.ndarray]]:
        if ts.size < 8 or values.size < 8:
            return None
        dt = np.diff(ts)
        dt = dt[dt > 0]
        if dt.size == 0:
            return None
        sample_rate_hz = 1.0 / float(np.mean(dt))
        centered = values - float(np.mean(values))
        spectrum = np.fft.rfft(centered)
        freqs = np.fft.rfftfreq(centered.size, d=1.0 / sample_rate_hz)
        if freqs.size <= 1:
            return None
        amplitudes = np.abs(spectrum) / max(1, centered.size)
        return freqs[1:], amplitudes[1:]

    def _draw_fft_plot(self, selected: list[tuple[str, np.ndarray, np.ndarray, str]]) -> None:
        self.ax_fft.clear()
        self.ax_fft.set_title("FFT")
        self.ax_fft.set_xlabel("Frequency (Hz)")
        self.ax_fft.set_ylabel("Amplitude")
        if not self.show_fft_var.get():
            self.ax_fft.text(0.5, 0.5, "FFT disabled", ha="center", va="center", transform=self.ax_fft.transAxes)
            self.ax_fft.set_xticks([])
            self.ax_fft.set_yticks([])
            return
        if not self.hold_sample_var.get():
            self.ax_fft.text(0.5, 0.5, "Enable Hold Sample to run FFT on frozen data", ha="center", va="center", transform=self.ax_fft.transAxes)
            self.ax_fft.set_xticks([])
            self.ax_fft.set_yticks([])
            return

        plotted = False
        for label, ts, values, color in selected:
            fft_data = self.held_fft_cache.get(label)
            if fft_data is None:
                continue
            freqs, amplitudes = fft_data
            self.ax_fft.plot(freqs, amplitudes, lw=1.0, label=label, color=color)
            plotted = True

        if plotted:
            self.ax_fft.set_xlim(left=0.0)
            self.ax_fft.grid(True, alpha=0.3)
            self.ax_fft.legend(loc="upper right", ncol=2)
        else:
            self.ax_fft.text(0.5, 0.5, "Need more samples for FFT", ha="center", va="center", transform=self.ax_fft.transAxes)
            self.ax_fft.set_xticks([])
            self.ax_fft.set_yticks([])

    def _refresh_plot_once(self) -> None:
        if not self.running:
            return
        now = self.hold_capture_time if self.hold_sample_var.get() and self.hold_capture_time is not None else time.monotonic()
        selected = self._selected_series(now)
        self._draw_time_plot(selected, now)
        self._draw_fft_plot(selected)
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw_idle()

    def refresh_plot(self) -> None:
        if not self.running:
            return
        self._refresh_plot_once()
        self.root.after(PLOT_MS, self.refresh_plot)

    def run(self) -> int:
        self.root.mainloop()
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Live GUI for Apparatus force/raw monitoring")
    parser.add_argument("--baudrate", type=int, default=921600)
    parser.add_argument("--rate-hz", type=float, default=250.0)
    parser.add_argument("--device", choices=["white", "blue", "both"], default="both")
    args = parser.parse_args()

    app = ForceRawMonitorGUI(
        initial_baudrate=args.baudrate,
        initial_rate_hz=args.rate_hz,
        initial_device=args.device,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
