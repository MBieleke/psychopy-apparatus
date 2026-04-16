"""
Standalone reed sensor readout with circular GUI (no PsychoPy dependency).

Layout
------
- Inner ring: 8 sensors
- Outer ring: 12 sensors

Color coding
------------
- Green: currently active (reed closed)
- Red: currently inactive (reed open)
- Orange border: potential bouncing/ringing detected
- Client LEDs mirror reed states (green=active, red=inactive)

Examples
--------
python firmware/tests/test_reed.py COM4
python firmware/tests/test_reed.py COM4 --rate-hz 100 --duration 30
python firmware/tests/test_reed.py COM4 --no-gui
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from pathlib import Path
from typing import Dict, List

from serial import Serial

# Ensure local package imports work when script is launched directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psychopy_apparatus.utils.protocol import (  # noqa: E402
    ADDR_CLIENT,
    CMD_LED_SET_N,
    CMD_LED_SHOW,
    CMD_REED_START,
    CMD_REED_STOP,
    DATA_REED,
    FLAG_ACK_REQUIRED,
    MSG_ACK,
    MSG_NACK,
    build_message,
    cobs_decode,
    cobs_encode,
    encode_led_payload_format_b,
    encode_reed_start_payload,
    parse_message,
    parse_reed_data_payload,
)

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


class COBSFrameStream:
    """Incrementally split incoming bytes into COBS frames (delimited by 0x00)."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        frames: list[bytes] = []
        for b in data:
            if b == 0:
                if self._buffer:
                    frames.append(bytes(self._buffer))
                    self._buffer.clear()
            else:
                self._buffer.append(b)
        return frames


def send_command(
    ser: Serial,
    seq: int,
    msg_type: int,
    payload: bytes,
    *,
    flags: int = FLAG_ACK_REQUIRED,
) -> None:
    raw = build_message(msg_type=msg_type, seq=seq, payload=payload, dst=ADDR_CLIENT, flags=flags)
    ser.write(cobs_encode(raw))


def send_led_mirror_update(ser: Serial, seq: int, holes: List[int], reed_bits: int) -> int:
    """Update the client LEDs for given holes, then flush with CMD_LED_SHOW."""
    if not holes:
        return seq

    colors = []
    for hole in holes:
        active = ((reed_bits >> hole) & 1) == 1
        colors.append((0, 180, 0) if active else (180, 0, 0))

    payload = encode_led_payload_format_b(holes, colors)
    send_command(ser, seq=seq, msg_type=CMD_LED_SET_N, payload=payload, flags=0)
    seq += 1
    send_command(ser, seq=seq, msg_type=CMD_LED_SHOW, payload=b"", flags=0)
    seq += 1
    return seq


class ReedMatrixGUI:
    def __init__(
        self,
        inner_count: int = 8,
        outer_count: int = 12,
        bounce_window_s: float = 0.15,
        bounce_toggle_threshold: int = 3,
    ) -> None:
        if plt is None:
            raise RuntimeError("matplotlib is not available")

        self.inner_count = inner_count
        self.outer_count = outer_count
        self.hole_ids: List[int] = list(range(inner_count + outer_count))

        self.state: Dict[int, int] = {h: 0 for h in self.hole_ids}
        self.ever_triggered: Dict[int, bool] = {h: False for h in self.hole_ids}
        self.toggle_times: Dict[int, deque[float]] = {h: deque(maxlen=16) for h in self.hole_ids}
        self.bouncing: Dict[int, bool] = {h: False for h in self.hole_ids}

        self.bounce_window_s = bounce_window_s
        self.bounce_toggle_threshold = bounce_toggle_threshold

        self.all_triggered_latched = False
        self.last_draw_s = 0.0
        self.draw_interval_s = 1.0 / 30.0

        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.canvas.manager.set_window_title("Reed Sensor Matrix")
        self.ax.set_aspect("equal")
        self.ax.set_xlim(-2.6, 2.6)
        self.ax.set_ylim(-2.6, 2.6)
        self.ax.axis("off")
        self.ax.set_title("Reed Sensor Status")

        xs, ys = self._build_layout()

        self.scatter = self.ax.scatter(
            xs,
            ys,
            s=1150,
            c=["red"] * len(self.hole_ids),
            edgecolors=["black"] * len(self.hole_ids),
            linewidths=2.0,
            zorder=2,
        )

        for idx, hole in enumerate(self.hole_ids):
            self.ax.text(xs[idx], ys[idx], str(hole), ha="center", va="center", fontsize=10, color="white", zorder=3)

        self.status_text = self.ax.text(-2.5, 2.4, "", ha="left", va="top", fontsize=10)
        self.bounce_text = self.ax.text(-2.5, -2.45, "", ha="left", va="bottom", fontsize=10)

        self._redraw(force=True)
        plt.show(block=False)

    def _build_layout(self) -> tuple[list[float], list[float]]:
        xs: list[float] = []
        ys: list[float] = []

        inner_radius = 1.1
        outer_radius = 2.0

        for i in range(self.inner_count):
            angle = (math.pi / 2.0) - (2.0 * math.pi * i / self.inner_count)
            xs.append(inner_radius * math.cos(angle))
            ys.append(inner_radius * math.sin(angle))

        for i in range(self.outer_count):
            angle = (math.pi / 2.0) - (2.0 * math.pi * i / self.outer_count)
            xs.append(outer_radius * math.cos(angle))
            ys.append(outer_radius * math.sin(angle))

        return xs, ys

    def is_closed(self) -> bool:
        return not plt.fignum_exists(self.fig.number)

    def update_bits(self, bits: int, now_s: float) -> None:
        for hole in self.hole_ids:
            new_state = (bits >> hole) & 1
            old_state = self.state[hole]

            if new_state != old_state:
                self.toggle_times[hole].append(now_s)
            self.state[hole] = new_state

            if new_state:
                self.ever_triggered[hole] = True

            while self.toggle_times[hole] and (now_s - self.toggle_times[hole][0]) > self.bounce_window_s:
                self.toggle_times[hole].popleft()

            self.bouncing[hole] = len(self.toggle_times[hole]) >= self.bounce_toggle_threshold

        if not self.all_triggered_latched and all(self.ever_triggered[h] for h in self.hole_ids):
            self.all_triggered_latched = True
            print("[INFO] ALL-SENSORS-TRIGGERED latch set.")

        self._redraw()

    def _redraw(self, force: bool = False) -> None:
        now_s = time.time()
        if not force and (now_s - self.last_draw_s) < self.draw_interval_s:
            return
        self.last_draw_s = now_s

        facecolors = ["limegreen" if self.state[h] else "red" for h in self.hole_ids]
        edgecolors = ["orange" if self.bouncing[h] else "black" for h in self.hole_ids]

        self.scatter.set_facecolor(facecolors)
        self.scatter.set_edgecolor(edgecolors)

        active = sum(self.state[h] for h in self.hole_ids)
        triggered = sum(1 for h in self.hole_ids if self.ever_triggered[h])
        self.status_text.set_text(
            f"Active: {active}/{len(self.hole_ids)}\n"
            f"Ever triggered: {triggered}/{len(self.hole_ids)}\n"
            f"All triggered latch: {'YES' if self.all_triggered_latched else 'NO'}"
        )

        bouncing_ids = [h for h in self.hole_ids if self.bouncing[h]]
        if bouncing_ids:
            self.bounce_text.set_text("Bouncing/ringing: " + ", ".join(str(h) for h in bouncing_ids))
        else:
            self.bounce_text.set_text("Bouncing/ringing: none")

        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone reed switch readout with circular matrix GUI.")
    parser.add_argument("port", help="Serial port, e.g. COM4")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--rate-hz", type=float, default=100.0)
    parser.add_argument("--startup-delay", type=float, default=2.0)
    parser.add_argument("--duration", type=float, default=0.0, help="0 = run until Ctrl+C")
    parser.add_argument("--start-retries", type=int, default=4)
    parser.add_argument("--inner", type=int, default=8, help="Inner ring sensor count")
    parser.add_argument("--outer", type=int, default=12, help="Outer ring sensor count")
    parser.add_argument("--bounce-window-ms", type=float, default=150.0)
    parser.add_argument("--bounce-toggle-threshold", type=int, default=3)
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI and print text only")
    parser.add_argument("--no-led-mirror", action="store_true", help="Disable LED mirror output to client")
    parser.add_argument(
        "--clear-leds-on-exit",
        action="store_true",
        help="Clear mirrored LEDs (set black) before exit",
    )
    args = parser.parse_args()

    if args.inner <= 0 or args.outer <= 0:
        raise SystemExit("inner/outer must be > 0")

    gui = None
    if not args.no_gui:
        if plt is None:
            print("[WARN] matplotlib not available, running without GUI.")
        else:
            gui = ReedMatrixGUI(
                inner_count=args.inner,
                outer_count=args.outer,
                bounce_window_s=max(0.01, args.bounce_window_ms / 1000.0),
                bounce_toggle_threshold=max(2, args.bounce_toggle_threshold),
            )

    displayed_holes = list(range(args.inner + args.outer))
    # Client firmware currently exposes 21 logical holes (0..20) for LED addressing.
    led_holes = [h for h in displayed_holes if 0 <= h <= 20]
    if len(led_holes) != len(displayed_holes):
        print(
            f"[WARN] LED mirror limited to holes 0..20. "
            f"Displayed={len(displayed_holes)} mirrored={len(led_holes)}"
        )

    seq = 1
    start_payload = encode_reed_start_payload(args.rate_hz)

    frames_total = 0
    ack_total = 0
    nack_total = 0
    reed_total = 0
    start_acknowledged = False
    waiting_ack_for: int | None = None
    attempts_left = args.start_retries
    last_tx_time = 0.0
    last_led_bits: int | None = None

    prev_bits: int | None = None
    first_ts = None
    t0 = time.perf_counter()

    frame_stream = COBSFrameStream()

    with Serial(args.port, baudrate=args.baud, timeout=0.02) as ser:
        print(f"[INFO] Connected to {args.port} @ {args.baud}")
        if args.startup_delay > 0:
            print(f"[INFO] Waiting {args.startup_delay:.1f}s for device boot...")
            time.sleep(args.startup_delay)

        def tx_start() -> None:
            nonlocal seq, waiting_ack_for, attempts_left, last_tx_time
            send_command(ser, seq=seq, msg_type=CMD_REED_START, payload=start_payload)
            waiting_ack_for = seq
            attempts_left -= 1
            last_tx_time = time.time()
            print(
                f"[TX] CMD_REED_START seq={seq} rate_hz={args.rate_hz:.3f} "
                f"payload={start_payload.hex()} attempts_left_after_send={attempts_left}"
            )
            seq += 1

        tx_start()
        if not args.no_led_mirror:
            seq = send_led_mirror_update(ser, seq, led_holes, reed_bits=0)
            last_led_bits = 0

        print("[INFO] Streaming... Press Ctrl+C to stop.")

        last_stats_print = 0.0
        stop_deadline = (time.time() + args.duration) if args.duration > 0 else None
        all_triggered_latched = False
        ever_triggered = {h: False for h in displayed_holes}

        try:
            while True:
                now = time.time()
                if stop_deadline is not None and now >= stop_deadline:
                    print("[INFO] Duration reached, stopping.")
                    break
                if gui is not None and gui.is_closed():
                    print("[INFO] GUI window closed, stopping.")
                    break

                data = ser.read(ser.in_waiting or 1)
                for enc in frame_stream.feed(data):
                    try:
                        decoded = cobs_decode(enc)
                        parsed = parse_message(decoded)
                        if not parsed:
                            continue
                        hdr, payload = parsed
                        frames_total += 1

                        msg_type = int(hdr["msg_type"])
                        src = int(hdr["src"])
                        msg_seq = int(hdr["seq"])

                        if msg_type == MSG_ACK:
                            ack_total += 1
                            if waiting_ack_for is not None and msg_seq == waiting_ack_for:
                                start_acknowledged = True
                                waiting_ack_for = None
                                print(f"[RX] ACK seq={msg_seq} src={src}")
                            continue

                        if msg_type == MSG_NACK:
                            nack_total += 1
                            print(f"[RX] NACK seq={msg_seq} src={src} payload={payload.hex()}")
                            if waiting_ack_for is not None and msg_seq == waiting_ack_for:
                                waiting_ack_for = None
                            continue

                        if msg_type == DATA_REED:
                            reed_total += 1
                            rd = parse_reed_data_payload(payload)
                            bits = int(rd["reed_bits"])
                            dev_us = int(rd["time_us"])
                            if first_ts is None:
                                first_ts = dev_us
                            rel_s = (dev_us - first_ts) / 1_000_000.0

                            for h in displayed_holes:
                                if ((bits >> h) & 1) == 1:
                                    ever_triggered[h] = True
                            if not all_triggered_latched and all(ever_triggered.values()):
                                all_triggered_latched = True
                                print("[INFO] ALL-SENSORS-TRIGGERED latch set.")

                            if gui is not None:
                                gui.update_bits(bits, now)

                            if not args.no_led_mirror and led_holes:
                                if last_led_bits is None:
                                    seq = send_led_mirror_update(ser, seq, led_holes, bits)
                                elif bits != last_led_bits:
                                    changed_holes = [h for h in led_holes if ((bits ^ last_led_bits) >> h) & 1]
                                    if changed_holes:
                                        seq = send_led_mirror_update(ser, seq, changed_holes, bits)
                                last_led_bits = bits

                            if prev_bits is None:
                                print(f"[REED] t={rel_s:8.3f}s bits=0x{bits:08X}")
                            elif bits != prev_bits:
                                changed = bits ^ prev_bits
                                changes = []
                                for hole in displayed_holes:
                                    if (changed >> hole) & 1:
                                        state = (bits >> hole) & 1
                                        changes.append(f"h{hole}:{'in' if state else 'out'}")
                                if changes:
                                    print(f"[REED] t={rel_s:8.3f}s changes={','.join(changes)}")
                            prev_bits = bits

                    except Exception as exc:
                        print(f"[WARN] Frame parse error: {exc}")

                if waiting_ack_for is not None and (now - last_tx_time) > 2.0:
                    print(f"[WARN] ACK timeout for seq={waiting_ack_for}")
                    waiting_ack_for = None
                    if attempts_left > 0:
                        print("[INFO] Retrying CMD_REED_START...")
                        tx_start()
                    else:
                        print("[WARN] No CMD_REED_START retries left.")

                if (now - last_stats_print) >= 2.0:
                    elapsed = time.perf_counter() - t0
                    reed_rate = (reed_total / elapsed) if elapsed > 0 else 0.0
                    trig_count = sum(1 for v in ever_triggered.values() if v)
                    print(
                        f"[STATS] frames={frames_total} reed={reed_total} ({reed_rate:.1f} Hz) "
                        f"ack={ack_total} nack={nack_total} start_ack={start_acknowledged} "
                        f"triggered={trig_count}/{len(displayed_holes)} all={all_triggered_latched}"
                    )
                    last_stats_print = now

                if gui is not None:
                    plt.pause(0.001)

        except KeyboardInterrupt:
            print("\n[INFO] Stopping...")
        finally:
            try:
                if args.clear_leds_on_exit and not args.no_led_mirror and led_holes:
                    off_payload = encode_led_payload_format_b(led_holes, [(0, 0, 0)] * len(led_holes))
                    send_command(ser, seq=seq, msg_type=CMD_LED_SET_N, payload=off_payload, flags=0)
                    seq += 1
                    send_command(ser, seq=seq, msg_type=CMD_LED_SHOW, payload=b"", flags=0)
                    seq += 1
                send_command(ser, seq=seq, msg_type=CMD_REED_STOP, payload=b"")
                print(f"[TX] CMD_REED_STOP seq={seq}")
            except Exception as exc:
                print(f"[WARN] Failed to send CMD_REED_STOP: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

