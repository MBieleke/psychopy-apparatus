"""
Small local UI for the Apparatus server serial protocol.

Features:
- connect/disconnect to the server serial port
- show parsed incoming frames and raw payload hex
- expose the server-local commands currently implemented in firmware:
  - motor start/stop
  - light sensor read
  - force start/stop
  - magnet on/off

Run:
python firmware/tests/server_control_ui.py COM6
"""

from __future__ import annotations

import argparse
import struct
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from serial import Serial
from serial import SerialException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psychopy_apparatus.utils.protocol import (  # noqa: E402
    ADDR_SERVER,
    CMD_FORCE_START,
    CMD_FORCE_STOP,
    DATA_FORCE,
    ERR_BAD_LEN,
    ERR_BAD_MSG,
    ERR_BAD_PAYLOAD,
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

CMD_MOTOR = 0x01
CMD_LIGHT = 0x02
CMD_MAGNET = 0x05

ERROR_LABELS = {
    ERR_BAD_LEN: "ERR_BAD_LEN",
    ERR_BAD_MSG: "ERR_BAD_MSG",
    ERR_BAD_PAYLOAD: "ERR_BAD_PAYLOAD",
}

FORCE_DEVICE_NAMES = {
    0: "white/right",
    1: "blue/left",
}

MAGNET_CHANNELS = {
    "right": 0,
    "left": 1,
    "both": 2,
}


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


class ServerControlUI:
    def __init__(self, root: tk.Tk, initial_port: str, initial_baudrate: int) -> None:
        self.root = root
        self.root.title("Apparatus Server Control")
        self.root.geometry("1200x820")

        self.serial: Serial | None = None
        self.decoder = COBSFrameStream()
        self.seq = 1
        self.pending: dict[int, str] = {}
        self.poll_job: str | None = None

        self.port_var = tk.StringVar(value=initial_port)
        self.baudrate_var = tk.StringVar(value=str(initial_baudrate))
        self.connection_var = tk.StringVar(value="Disconnected")

        self.motor_speed_var = tk.StringVar(value="1000")
        self.force_rate_var = tk.StringVar(value="100")
        self.force_device_var = tk.StringVar(value="both")
        self.force_white_var = tk.StringVar(value="--")
        self.force_blue_var = tk.StringVar(value="--")
        self.light_var = tk.StringVar(value="--")

        self._build_ui()
        self._set_command_widgets_state("disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        root = self.root

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Port").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.port_var, width=14).grid(row=0, column=1, padx=(6, 12))
        ttk.Label(top, text="Baud").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.baudrate_var, width=10).grid(row=0, column=3, padx=(6, 12))
        self.connect_button = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=4, padx=(0, 6))
        self.disconnect_button = ttk.Button(top, text="Disconnect", command=self.disconnect)
        self.disconnect_button.grid(row=0, column=5, padx=(0, 12))
        ttk.Label(top, textvariable=self.connection_var).grid(row=0, column=6, sticky="w")

        summary = ttk.LabelFrame(root, text="Live Summary", padding=10)
        summary.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(summary, text="white/right").grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.force_white_var, width=18).grid(row=0, column=1, sticky="w", padx=(8, 20))
        ttk.Label(summary, text="blue/left").grid(row=0, column=2, sticky="w")
        ttk.Label(summary, textvariable=self.force_blue_var, width=18).grid(row=0, column=3, sticky="w", padx=(8, 20))
        ttk.Label(summary, text="light").grid(row=0, column=4, sticky="w")
        ttk.Label(summary, textvariable=self.light_var, width=12).grid(row=0, column=5, sticky="w", padx=(8, 0))

        controls = ttk.Frame(root, padding=(10, 0, 10, 10))
        controls.pack(fill="x")

        self.command_widgets: list[tk.Widget] = []

        motor_frame = ttk.LabelFrame(controls, text="Motor", padding=10)
        motor_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(motor_frame, text="Speed us").grid(row=0, column=0, sticky="w")
        speed_entry = ttk.Entry(motor_frame, textvariable=self.motor_speed_var, width=10)
        speed_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.command_widgets.append(speed_entry)
        btn = ttk.Button(motor_frame, text="Start Forward", command=lambda: self.send_motor(1))
        btn.grid(row=1, column=0, pady=(8, 4), sticky="ew", columnspan=2)
        self.command_widgets.append(btn)
        btn = ttk.Button(motor_frame, text="Start Reverse", command=lambda: self.send_motor(0))
        btn.grid(row=2, column=0, pady=4, sticky="ew", columnspan=2)
        self.command_widgets.append(btn)
        btn = ttk.Button(motor_frame, text="Stop", command=self.stop_motor)
        btn.grid(row=3, column=0, pady=4, sticky="ew", columnspan=2)
        self.command_widgets.append(btn)

        light_frame = ttk.LabelFrame(controls, text="Light Sensor", padding=10)
        light_frame.grid(row=0, column=1, sticky="nsew", padx=8)
        btn = ttk.Button(light_frame, text="Read Light", command=self.read_light)
        btn.grid(row=0, column=0, sticky="ew")
        self.command_widgets.append(btn)

        force_frame = ttk.LabelFrame(controls, text="Force Stream", padding=10)
        force_frame.grid(row=0, column=2, sticky="nsew", padx=8)
        ttk.Label(force_frame, text="Rate Hz").grid(row=0, column=0, sticky="w")
        rate_entry = ttk.Entry(force_frame, textvariable=self.force_rate_var, width=8)
        rate_entry.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.command_widgets.append(rate_entry)
        ttk.Label(force_frame, text="Device").grid(row=1, column=0, sticky="w", pady=(8, 0))
        device_box = ttk.Combobox(force_frame, textvariable=self.force_device_var, width=10, state="readonly")
        device_box["values"] = ("white", "blue", "both")
        device_box.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        self.command_widgets.append(device_box)
        btn = ttk.Button(force_frame, text="Start Force", command=self.start_force)
        btn.grid(row=2, column=0, pady=(10, 4), sticky="ew", columnspan=2)
        self.command_widgets.append(btn)
        btn = ttk.Button(force_frame, text="Stop Force", command=self.stop_force)
        btn.grid(row=3, column=0, pady=4, sticky="ew", columnspan=2)
        self.command_widgets.append(btn)

        magnet_frame = ttk.LabelFrame(controls, text="Magnets", padding=10)
        magnet_frame.grid(row=0, column=3, sticky="nsew", padx=(8, 0))
        row = 0
        for label in ("right", "left", "both"):
            btn = ttk.Button(magnet_frame, text=f"{label.title()} ON", command=lambda c=label: self.set_magnet(c, True))
            btn.grid(row=row, column=0, pady=3, sticky="ew")
            self.command_widgets.append(btn)
            btn = ttk.Button(magnet_frame, text=f"{label.title()} OFF", command=lambda c=label: self.set_magnet(c, False))
            btn.grid(row=row, column=1, pady=3, padx=(6, 0), sticky="ew")
            self.command_widgets.append(btn)
            row += 1

        log_frame = ttk.LabelFrame(root, text="Parsed Incoming Frames", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_widget = ScrolledText(log_frame, wrap="word", height=30, font=("Consolas", 10))
        self.log_widget.pack(fill="both", expand=True)
        self.log_widget.configure(state="disabled")

        bottom = ttk.Frame(root, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Clear Log", command=self.clear_log).pack(side="left")

    def _set_command_widgets_state(self, state: str) -> None:
        for widget in self.command_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", f"[{timestamp}] {message}\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")

    def connect(self) -> None:
        if self.serial is not None:
            return
        try:
            baudrate = int(self.baudrate_var.get().strip())
            self.serial = Serial(self.port_var.get().strip(), baudrate=baudrate, timeout=0.0)
            time.sleep(2.0)
            try:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
            except Exception:
                pass
        except (ValueError, SerialException) as exc:
            self.connection_var.set(f"Connect failed: {exc}")
            return

        self.connection_var.set(f"Connected: {self.port_var.get().strip()}")
        self._set_command_widgets_state("normal")
        self.connect_button.configure(state="disabled")
        self.disconnect_button.configure(state="normal")
        self.log("Connected")
        self.schedule_poll()

    def disconnect(self) -> None:
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None
        self.connection_var.set("Disconnected")
        self._set_command_widgets_state("disabled")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")
        self.log("Disconnected")

    def on_close(self) -> None:
        self.disconnect()
        self.root.destroy()

    def schedule_poll(self) -> None:
        self.poll_serial()
        self.poll_job = self.root.after(25, self.schedule_poll)

    def poll_serial(self) -> None:
        if self.serial is None:
            return
        try:
            waiting = self.serial.in_waiting or 1
            chunk = self.serial.read(waiting)
        except Exception as exc:
            self.log(f"Serial read failed: {exc}")
            self.disconnect()
            return

        if not chunk:
            return

        for frame in self.decoder.feed(chunk):
            try:
                decoded = cobs_decode(frame)
                parsed = parse_message(decoded)
            except Exception as exc:
                self.log(f"RX invalid cobs={frame.hex()} error={exc}")
                continue

            if parsed is None:
                self.log(f"RX invalid decoded={decoded.hex()}")
                continue

            header, payload = parsed
            self.handle_frame(header, payload)

    def handle_frame(self, header: dict, payload: bytes) -> None:
        msg_type = header["msg_type"]
        seq = header["seq"]
        source = header["src"]
        destination = header["dst"]
        pending_label = self.pending.pop(seq, None)

        if msg_type == DATA_FORCE:
            sample = parse_force_data_payload(payload)
            device = int(sample["device"])
            value = float(sample["value"])
            name = FORCE_DEVICE_NAMES.get(device, f"device={device}")
            if device == 0:
                self.force_white_var.set(f"{value:.2f} N")
            elif device == 1:
                self.force_blue_var.set(f"{value:.2f} N")
            self.log(
                f"DATA_FORCE seq={seq} src={source} dst={destination} "
                f"device={name} value={value:.2f}N time_us={sample['time_us']} raw={payload.hex()}"
            )
            return

        if msg_type == MSG_ACK:
            detail = self.describe_ack(payload, pending_label)
            self.log(f"ACK seq={seq} for={pending_label or 'unknown'} {detail} raw={payload.hex()}")
            return

        if msg_type == MSG_NACK:
            code = payload[0] if payload else None
            code_label = ERROR_LABELS.get(code, f"ERR_{code}")
            self.log(f"NACK seq={seq} for={pending_label or 'unknown'} code={code_label} raw={payload.hex()}")
            return

        self.log(
            f"RX type=0x{msg_type:02X} seq={seq} src={source} dst={destination} "
            f"len={header['payload_len']} raw={payload.hex()}"
        )

    def describe_ack(self, payload: bytes, pending_label: str | None) -> str:
        if pending_label == "light_read" and len(payload) == 1:
            light_state = payload[0]
            self.light_var.set(str(light_state))
            return f"light_state={light_state}"

        if pending_label == "force_start" and len(payload) == 5:
            period_us = struct.unpack("<I", payload[:4])[0]
            device = payload[4]
            return f"period_us={period_us} device={device}"

        if pending_label and pending_label.startswith("magnet_") and len(payload) == 2:
            channel, state = payload
            return f"channel={channel} state={state}"

        return f"payload_len={len(payload)}"

    def send_server_command(self, msg_type: int, payload: bytes, label: str) -> None:
        if self.serial is None:
            self.log("Not connected")
            return

        seq = self.seq
        self.seq += 1
        message = build_message(
            msg_type=msg_type,
            seq=seq,
            payload=payload,
            dst=ADDR_SERVER,
            flags=FLAG_ACK_REQUIRED,
        )
        try:
            self.serial.write(cobs_encode(message))
        except Exception as exc:
            self.log(f"TX failed for {label}: {exc}")
            return

        self.pending[seq] = label
        self.log(f"TX seq={seq} {label} payload={payload.hex()}")

    def send_motor(self, direction: int) -> None:
        try:
            speed_us = int(self.motor_speed_var.get().strip())
        except ValueError:
            self.log("Invalid motor speed")
            return
        payload = struct.pack("<BBH", 1, direction, speed_us)
        self.send_server_command(CMD_MOTOR, payload, f"motor_start_dir_{direction}")

    def stop_motor(self) -> None:
        payload = struct.pack("<BBH", 0, 0, 0)
        self.send_server_command(CMD_MOTOR, payload, "motor_stop")

    def read_light(self) -> None:
        self.send_server_command(CMD_LIGHT, b"", "light_read")

    def start_force(self) -> None:
        try:
            rate_hz = float(self.force_rate_var.get().strip())
        except ValueError:
            self.log("Invalid force rate")
            return
        try:
            payload = encode_force_start_payload(rate_hz, self.force_device_var.get().strip())
        except Exception as exc:
            self.log(f"Force payload error: {exc}")
            return
        self.send_server_command(CMD_FORCE_START, payload, "force_start")

    def stop_force(self) -> None:
        self.send_server_command(CMD_FORCE_STOP, b"", "force_stop")

    def set_magnet(self, channel_name: str, state: bool) -> None:
        channel = MAGNET_CHANNELS[channel_name]
        payload = struct.pack("<BB", channel, 1 if state else 0)
        self.send_server_command(CMD_MAGNET, payload, f"magnet_{channel_name}_{'on' if state else 'off'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="UI for Apparatus server control.")
    parser.add_argument("port", nargs="?", default="COM6")
    parser.add_argument("--baudrate", type=int, default=115200)
    args = parser.parse_args()

    root = tk.Tk()
    app = ServerControlUI(root, args.port, args.baudrate)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
