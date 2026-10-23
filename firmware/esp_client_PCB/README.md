# PCB client firmware

`esp_client_PCB.ino` controls the pegboard LEDs, reed inputs, and Hall sensors.
It communicates with the PCB server over ESP-NOW on channel 1.

## Build and upload

Open `esp_client_PCB.ino` in Arduino IDE. Keep the sketch inside the
`esp_client_PCB` folder. Select the board that matches the fitted module and
its USB port. The compilation target used for this package is **ESP32 Dev
Module** (`esp32:esp32:esp32`).

Dependencies:

- Arduino ESP32 core 3.3.8
- Adafruit NeoPixel 1.15.4

With those dependencies installed, run from this folder:

```sh
arduino-cli compile --fqbn esp32:esp32:esp32 .
arduino-cli compile --fqbn esp32:esp32:esp32 --upload --port COM4 .
```

Replace `COM4` with this client's USB port. Its diagnostic serial output uses
115200 baud. PsychoPy connects to the server, which uses 921600 baud.

## PCB connections

| Function | Assignment |
| --- | --- |
| I2C SDA / SCL | GPIO21 / GPIO22, 40 kHz |
| Main LED output | GPIO2, 8 LEDs per logical hole |
| Mirrored LED output | GPIO4, 1 LED per logical hole |
| Reed expanders | I2C 0x21, 0x23, 0x25 |
| Reed interrupt input | GPIO18 |
| Hall sensor | I2C 0x0C |
| Hall sub-addresses | 0x20, 0x22, 0x24, 0x26 |
| Group A / B / C | GPIO27 / GPIO26 / GPIO25 |
| Group D / E / F | GPIO33 / GPIO32 / GPIO35 |

The firmware addresses holes 0 through 20. Each reed expander supplies seven
active-low inputs; the three groups form bits 0 through 20 in `DATA_REED`.
Both LED outputs display the same logical colors.

**Board check:** Group F is assigned to GPIO35 in the supplied revision.
GPIO35 is input-only on the classic ESP32, so this assignment must be checked
against the fitted chip and PCB before using Hall group selection. The package
preserves the supplied pin assignments.

## Pairing and checks

Power the client and server together with other unpaired units switched off.
The firmware discovers its peer and stores the pairing in NVS (`Preferences`).
The serial monitor reports client readiness and pairing information. To remove
a stored pairing, erase the chip's flash using the flashing tool and upload the
firmware again; a normal upload may preserve NVS.

After flashing, verify both LED outputs, every reed input, Hall selection,
command acknowledgments, and reconnection after a power cycle. Compilation
does not verify PCB wiring or sensor operation.
