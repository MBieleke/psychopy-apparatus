# PCB server firmware

`esp_server_experimental4_PCB.ino` connects PsychoPy over USB serial to the
pegboard client over ESP-NOW. It also acquires force data from an ADS1115 and
controls the motor and magnets.

## Build and upload

Open the sketch in Arduino IDE and keep every `.h` and `.cpp` file beside it
in the `esp_server_experimental4_PCB` folder. Select the board that matches the
fitted module and its USB port. The compilation target used for this package
is **ESP32 Dev Module** (`esp32:esp32:esp32`).

Dependencies:

- Arduino ESP32 core 3.3.8
- FastAccelStepper 0.34.0
- Adafruit ADS1X15 2.6.2
- Adafruit BusIO 1.17.4

With those dependencies installed, run from this folder:

```sh
arduino-cli compile --fqbn esp32:esp32:esp32 .
arduino-cli compile --fqbn esp32:esp32:esp32 --upload --port COM4 .
```

Replace `COM4` with the server's USB port. Set the PsychoPy device baud rate to
**921600**. Text logging on the server's binary protocol port is disabled by
default; enabling it requires `PC_SERIAL_LOG_ENABLED=1` and a diagnostic session
that does not expect an uninterrupted binary stream.

## PCB connections

| Function | Assignment |
| --- | --- |
| ADS1115 SDA / SCL | GPIO26 / GPIO27 |
| ADS1115 address | 0x48 |
| Right / white force input | ADS1115 A0 |
| Left / blue force input | ADS1115 A3 |
| Motor step / direction / enable | GPIO22 / GPIO23 / GPIO21 |
| Light input | GPIO4 |
| Right / left magnet output | GPIO18 / GPIO19 |

The default force backend is ADS1115 with `GAIN_ONE` and a converter rate of
475 SPS. A FreeRTOS worker performs acquisition; the main loop handles serial
routing, ESP-NOW pairing, outgoing force frames, and motor polling. Requested
stream rates are limited to 250 Hz for one channel or 125 Hz per channel when
both channels are selected.

Keep both force sensors unloaded during startup tare. Boot tare is enabled;
retare on stream start is disabled by default. The source uses a fixed force
conversion slope of 176.8325 N/V. Check calibration against the actual sensors
before interpreting results as calibrated force measurements.

## Protocol and pairing

USB frames use COBS encoding, a zero delimiter, and an XOR checksum. The force
payload is 9 bytes: timestamp (`u32`), force (`i16`, 0.1 N units), raw ADC count
(`i16`), and dynamometer (`u8`). Multi-byte fields are little-endian.

ESP-NOW uses channel 1. Power the server and client together with other unpaired
units switched off. Pairing is stored in NVS (`Preferences`) and restored after
reboot. Erase the chip's flash and re-upload to clear a pairing; a normal upload
may preserve NVS.

After flashing, verify serial communication at 921600 baud, pairing after a
power cycle, both force channels and tare, requested sample rates, motor and
magnet commands, and forwarded client commands. Compilation does not establish
hardware readiness.

## Source files

- `apparatus_config.h`: pins and compile-time configuration.
- `apparatus_protocol.h`: command IDs and wire-format structures.
- `protocol_utils.*`: checksum and COBS encoding.
- `protocol_io.*`: USB framing, acknowledgments, and outgoing messages.
- `force_service.*`: acquisition, filtering, tare, and force streaming.
- `motor_control.*`: stepper setup and queued motor actions.
- `pairing_radio.*`: peer discovery, persistent pairing, and ESP-NOW routing.
