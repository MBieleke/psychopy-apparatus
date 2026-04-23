"""
Live serial readout tool for Apparatus server messages (no PsychoPy required).

Reads the COBS-framed binary stream from the server, prints decoded frames, and
shows live force/ADC stats with an optional live plot.

Examples
--------
python firmware/tests/live_force_readout.py COM6
python firmware/tests/live_force_readout.py COM6 --device both --rate-hz 100
python firmware/tests/live_force_readout.py COM6 --no-start --force-only
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Optional

from serial import Serial

# Make sure local package imports work when script is launched directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psychopy_apparatus.utils.protocol import (  # noqa: E402
    ADDR_SERVER,
    CMD_FORCE_START,
    CMD_FORCE_STOP,
    DATA_FORCE,
    MSG_ACK,
    MSG_NACK,
    FLAG_ACK_REQUIRED,
    build_message,
    cobs_decode,
    cobs_encode,
    encode_force_start_payload,
    parse_force_data_payload,
    parse_message,
)

FORCE_CAL_SLOPE_N_PER_V = 176.8325
FORCE_CAL_INTERCEPT_N = -19.5057
ADC_FULL_SCALE_COUNTS = 4095.0
ADC_FULL_SCALE_MV = 3300.0


def newton_to_estimated_mv(force_n: float) -> float:
    return max(0.0, ((force_n - FORCE_CAL_INTERCEPT_N) / FORCE_CAL_SLOPE_N_PER_V) * 1000.0)


def newton_to_estimated_adc(force_n: float) -> float:
    mv = newton_to_estimated_mv(force_n)
    return (mv / ADC_FULL_SCALE_MV) * ADC_FULL_SCALE_COUNTS


def noise_n_to_adc_rms(noise_n: float) -> float:
    # For noise around a local mean, intercept cancels out.
    n_per_count = FORCE_CAL_SLOPE_N_PER_V * (ADC_FULL_SCALE_MV / 1000.0) / ADC_FULL_SCALE_COUNTS
    if n_per_count <= 0:
        return 0.0
    return noise_n / n_per_count


class COBSFrameStream:
    """Incrementally split incoming bytes into COBS frames (delimited by 0x00)."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        frames = []
        for byte in data:
            if byte == 0:
                if self._buffer:
                    frames.append(bytes(self._buffer))
                    self._buffer.clear()
            else:
                self._buffer.append(byte)
        return frames


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2
        if x < self.minimum:
            self.minimum = x
        if x > self.maximum:
            self.maximum = x

    @property
    def std(self) -> float:
        if self.n < 2:
            return 0.0
        return math.sqrt(self.m2 / (self.n - 1))


@dataclass
class ChannelState:
    label: str
    times: Deque[float]
    values_n: Deque[float]
    value_stats: RunningStats = field(default_factory=RunningStats)
    adc_stats: RunningStats = field(default_factory=RunningStats)
    host_dt_ms: RunningStats = field(default_factory=RunningStats)
    dev_dt_ms: RunningStats = field(default_factory=RunningStats)
    first_host_ts: Optional[float] = None
    last_host_ts: Optional[float] = None
    last_dev_us: Optional[int] = None

    def update(self, host_ts: float, value_n: float, dev_us: int) -> None:
        if self.first_host_ts is None:
            self.first_host_ts = host_ts
        if self.last_host_ts is not None:
            self.host_dt_ms.update((host_ts - self.last_host_ts) * 1000.0)
        if self.last_dev_us is not None:
            self.dev_dt_ms.update((dev_us - self.last_dev_us) / 1000.0)

        self.last_host_ts = host_ts
        self.last_dev_us = dev_us

        self.values_n.append(float(value_n))
        self.times.append(host_ts)
        self.value_stats.update(float(value_n))
        self.adc_stats.update(newton_to_estimated_adc(float(value_n)))

    @property
    def count(self) -> int:
        return self.value_stats.n

    @property
    def host_rate_hz(self) -> float:
        if self.first_host_ts is None or self.last_host_ts is None or self.count < 2:
            return 0.0
        span = self.last_host_ts - self.first_host_ts
        if span <= 0:
            return 0.0
        return (self.count - 1) / span


def format_stats(ch: ChannelState) -> str:
    if ch.count == 0:
        return f"{ch.label}: no samples"
    return (
        f"{ch.label}: n={ch.count} rate={ch.host_rate_hz:6.1f}Hz "
        f"N(mean/std/min/max)=({ch.value_stats.mean:7.2f}/{ch.value_stats.std:6.2f}/"
        f"{ch.value_stats.minimum:7.2f}/{ch.value_stats.maximum:7.2f}) "
        f"ADCest(mean/std)=({ch.adc_stats.mean:8.1f}/{ch.adc_stats.std:7.1f}) "
        f"dt_host_ms(mean/std)=({ch.host_dt_ms.mean:6.2f}/{ch.host_dt_ms.std:5.2f})"
    )


def compute_window_metrics(ch: ChannelState, now_s: float, window_s: float) -> Optional[dict]:
    if len(ch.times) == 0:
        return None

    cutoff = now_s - window_s
    times = list(ch.times)
    values = list(ch.values_n)

    start = 0
    while start < len(times) and times[start] < cutoff:
        start += 1

    if start >= len(times):
        return None

    wt = times[start:]
    wv = values[start:]
    n = len(wv)
    if n == 0:
        return None

    mean_v = sum(wv) / n
    if n > 1:
        std_v = math.sqrt(sum((v - mean_v) ** 2 for v in wv) / (n - 1))
    else:
        std_v = 0.0
    rms_noise = math.sqrt(sum((v - mean_v) ** 2 for v in wv) / n)
    p2p_v = max(wv) - min(wv)

    rate_hz = 0.0
    if len(wt) > 1:
        span = wt[-1] - wt[0]
        if span > 0:
            rate_hz = (len(wt) - 1) / span

    return {
        "n": n,
        "current": wv[-1],
        "mean": mean_v,
        "std": std_v,
        "rms_noise": rms_noise,
        "p2p": p2p_v,
        "rate_hz": rate_hz,
        "adc_rms": noise_n_to_adc_rms(rms_noise),
    }


def format_window_metrics(ch: ChannelState, now_s: float, window_s: float) -> str:
    m = compute_window_metrics(ch, now_s, window_s)
    if m is None:
        return f"{ch.label}: no window data"

    return (
        f"{ch.label:11s} | rate={m['rate_hz']:6.1f}Hz | current={m['current']:7.2f}N | "
        f"mean={m['mean']:7.2f}N | noise_std={m['std']:6.3f}N | noise_rms={m['rms_noise']:6.3f}N | "
        f"p2p={m['p2p']:6.3f}N | adc_rms={m['adc_rms']:7.2f}"
    )


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


def maybe_init_plot(disable_plot: bool):
    if disable_plot:
        return None
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[WARN] matplotlib unavailable ({exc}); continuing without plot.")
        return None

    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.subplots_adjust(bottom=0.30)
    ax.set_title("Live Force Readout")
    ax.set_xlabel("Host time (s)")
    ax.set_ylabel("Force (N)")
    ax.grid(True, alpha=0.3)
    white_line, = ax.plot([], [], label="white/right (device=0)", lw=1.5)
    blue_line, = ax.plot([], [], label="blue/left (device=1)", lw=1.5)
    ax.legend(loc="upper right")

    metrics_text = fig.text(
        0.01,
        0.02,
        "",
        ha="left",
        va="bottom",
        fontsize=9,
        family="monospace",
    )

    plt.show(block=False)
    return plt, fig, ax, white_line, blue_line, metrics_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Live readout of Apparatus server serial stream.")
    parser.add_argument("port", help="Serial port, e.g. COM6")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--rate-hz", type=float, default=100.0, help="Force stream rate when starting stream")
    parser.add_argument(
        "--device",
        choices=["white", "blue", "both"],
        default="both",
        help="Force device selector when starting stream",
    )
    parser.add_argument("--window-seconds", type=float, default=10.0, help="Plot window length in seconds")
    parser.add_argument("--noise-window-seconds", type=float, default=3.0, help="Window used for live noise metrics")
    parser.add_argument("--stats-interval", type=float, default=1.0, help="Stats print interval in seconds")
    parser.add_argument("--ack-timeout", type=float, default=2.0, help="ACK wait timeout in seconds")
    parser.add_argument("--startup-delay", type=float, default=2.0, help="Wait this long after opening serial before first command")
    parser.add_argument("--start-retries", type=int, default=4, help="How many CMD_FORCE_START attempts to make")
    parser.add_argument("--no-sample-timeout", type=float, default=3.0, help="Warn/retry if ACKed but no DATA_FORCE arrives")
    parser.add_argument("--no-start", action="store_true", help="Do not send CMD_FORCE_START")
    parser.add_argument("--force-only", action="store_true", help="Only print DATA_FORCE frames")
    parser.add_argument("--no-plot", action="store_true", help="Disable live plotting")
    args = parser.parse_args()

    plot_ctx = maybe_init_plot(args.no_plot)

    max_points = max(200, int(args.window_seconds * max(args.rate_hz, 20) * 2))
    channels: Dict[int, ChannelState] = {
        0: ChannelState(label="white/right", times=deque(maxlen=max_points), values_n=deque(maxlen=max_points)),
        1: ChannelState(label="blue/left", times=deque(maxlen=max_points), values_n=deque(maxlen=max_points)),
    }

    seq = 1
    started_by_script = False
    waiting_ack_for: Optional[int] = None
    ack_deadline = 0.0
    start_attempts_left = 0 if args.no_start else max(1, args.start_retries)
    no_sample_deadline: Optional[float] = None
    saw_force_sample = False
    start_payload = encode_force_start_payload(rate_hz=args.rate_hz, device=args.device)

    decoder = COBSFrameStream()
    t0 = time.monotonic()
    last_stats_print = t0
    last_plot_update = t0

    total_frames = 0
    invalid_frames = 0
    data_force_frames = 0
    ack_frames = 0
    nack_frames = 0

    with Serial(args.port, baudrate=args.baudrate, timeout=0.05) as ser:
        print(f"[INFO] Connected to {args.port} @ {args.baudrate}")


        if args.startup_delay > 0:
            print(f"[INFO] Waiting {args.startup_delay:.1f}s for device boot...")
            time.sleep(args.startup_delay)

        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass

        def send_force_start_once() -> None:
            nonlocal seq, waiting_ack_for, ack_deadline, start_attempts_left, started_by_script
            send_command(ser, seq=seq, msg_type=CMD_FORCE_START, payload=start_payload, dst=ADDR_SERVER)
            print(
                f"[TX] CMD_FORCE_START seq={seq} device={args.device} rate_hz={args.rate_hz:.3f} "
                f"payload={start_payload.hex()} attempts_left_after_send={start_attempts_left - 1}"
            )
            waiting_ack_for = seq
            ack_deadline = time.monotonic() + args.ack_timeout
            started_by_script = True
            start_attempts_left -= 1
            seq += 1

        if not args.no_start:
            send_force_start_once()
        else:
            print("[INFO] Passive listen mode (--no-start)")

        print("[INFO] Streaming... Press Ctrl+C to stop.")

        try:
            while True:
                chunk = ser.read(ser.in_waiting or 1)
                now = time.monotonic()
                if chunk:
                    for frame in decoder.feed(chunk):
                        total_frames += 1
                        header, payload, decoded = decode_frame(frame)
                        if header is None:
                            invalid_frames += 1
                            print(f"[RX INVALID] cobs={frame.hex()} decoded={decoded.hex()}")
                            continue

                        msg_type = header["msg_type"]
                        payload_hex = payload.hex()

                        if msg_type != DATA_FORCE and args.force_only:
                            continue

                        line = (
                            f"[RX {now - t0:8.3f}s] type=0x{msg_type:02X} seq={header['seq']} "
                            f"src={header['src']} dst={header['dst']} flags=0x{header['flags']:02X} "
                            f"len={header['payload_len']} checksum=0x{header['checksum']:02X} "
                            f"payload={payload_hex}"
                        )

                        if msg_type == DATA_FORCE:
                            data_force_frames += 1
                            try:
                                force = parse_force_data_payload(payload)
                                device = int(force["device"])
                                value_n = float(force["value"])
                                dev_us = int(force["time_us"])
                                adc_est = newton_to_estimated_adc(float(value_n))
                                dev_name = {0: "white/right", 1: "blue/left"}.get(device, f"unknown({device})")
                                line += (
                                    f" | force_n={value_n:.2f} adc_est={adc_est:.1f} "
                                    f"device={dev_name} time_us={dev_us}"
                                )
                                if device in channels:
                                    channels[device].update(host_ts=now - t0, value_n=value_n, dev_us=dev_us)
                                    saw_force_sample = True
                                    no_sample_deadline = None
                            except Exception as exc:
                                line += f" | DATA_FORCE parse_error={exc}"
                        elif msg_type == MSG_ACK:
                            ack_frames += 1
                            line += " | ACK"
                        elif msg_type == MSG_NACK:
                            nack_frames += 1
                            err = payload[0] if payload else None
                            line += f" | NACK error={err}"

                        print(line)

                        if waiting_ack_for is not None and header["seq"] == waiting_ack_for and msg_type in (MSG_ACK, MSG_NACK):
                            if msg_type == MSG_ACK:
                                print(f"[INFO] ACK received for seq={waiting_ack_for}")
                                if not saw_force_sample:
                                    no_sample_deadline = now + args.no_sample_timeout
                            else:
                                print(f"[WARN] NACK received for seq={waiting_ack_for}")
                            waiting_ack_for = None

                if waiting_ack_for is not None and now > ack_deadline:
                    print(f"[WARN] ACK timeout for seq={waiting_ack_for}")
                    waiting_ack_for = None
                    if start_attempts_left > 0:
                        print("[INFO] Retrying CMD_FORCE_START...")
                        send_force_start_once()
                    else:
                        print("[WARN] No CMD_FORCE_START retries left.")

                if (
                    no_sample_deadline is not None
                    and now > no_sample_deadline
                    and not saw_force_sample
                ):
                    print(
                        f"[WARN] ACK received but no DATA_FORCE within {args.no_sample_timeout:.1f}s. "
                        "Will retry start if attempts remain."
                    )
                    no_sample_deadline = None
                    if start_attempts_left > 0:
                        send_force_start_once()

                if now - last_stats_print >= args.stats_interval:
                    print("[STATS] " + format_stats(channels[0]))
                    print("[STATS] " + format_stats(channels[1]))
                    last_stats_print = now

                if plot_ctx is not None and now - last_plot_update >= 0.05:
                    plt, fig, ax, white_line, blue_line, metrics_text = plot_ctx
                    t_now = now - t0
                    t_min = max(0.0, t_now - args.window_seconds)
                    t_max = max(args.window_seconds, t_now)

                    white_line.set_data(channels[0].times, channels[0].values_n)
                    blue_line.set_data(channels[1].times, channels[1].values_n)

                    ax.set_xlim(t_min, t_max)
                    ax.relim()
                    ax.autoscale_view(scaley=True)

                    metrics_lines = [
                        (
                            f"window={args.noise_window_seconds:.1f}s "
                            f"total_frames={total_frames} invalid={invalid_frames} "
                            f"force={data_force_frames} ack={ack_frames} nack={nack_frames}"
                        ),
                        format_window_metrics(channels[0], t_now, args.noise_window_seconds),
                        format_window_metrics(channels[1], t_now, args.noise_window_seconds),
                    ]
                    metrics_text.set_text("\n".join(metrics_lines))

                    fig.canvas.draw_idle()
                    fig.canvas.flush_events()
                    last_plot_update = now

        except KeyboardInterrupt:
            print("\n[INFO] Stopping...")
        finally:
            if started_by_script:
                try:
                    send_command(ser, seq=seq, msg_type=CMD_FORCE_STOP, payload=b"", dst=ADDR_SERVER)
                    print(f"[TX] CMD_FORCE_STOP seq={seq}")
                except Exception as exc:
                    print(f"[WARN] Failed to send CMD_FORCE_STOP: {exc}")

    print("[FINAL] " + format_stats(channels[0]))
    print("[FINAL] " + format_stats(channels[1]))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())













