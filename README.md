# psychopy-apparatus

PsychoPy plugin and firmware bundle for the "Apparatus," a custom hardware setup for measuring and manipulating physical and cognitive effort.

The repository contains two tightly linked parts:

- the PsychoPy plugin used from Builder / experiments on the PC
- the ESP32 firmware used by the apparatus server and client nodes

## Repository Layout

- `psychopy_apparatus/`: Python package for the PsychoPy plugin
- `firmware/esp_server/`: server ESP32 firmware
- `firmware/esp_client/`: client ESP32 firmware
- `firmware/esp_server_experimental/`: alternate server build
- `firmware/tests/`: serial, force, LED, and reed test utilities
- `experiments/`: experiment notes and application documentation

## Installation

- Install PsychoPy `2025.2.1` or later.
- If the PsychoPy plugin manager is broken on your machine, install `2025.1.1` first, open the plugin manager once, then upgrade to a `2025.2.x` release.
- Clone this repository or download the source tree.
- In PsychoPy Builder, open `Plugins & Packages Manager`.
- In the `Packages` tab, choose `Install from file` and select [pyproject.toml](/C:/Users/pop555877/Documents/GitHub/Apparatus/pyproject.toml). Change the file-type filter to `Python projects` if needed.

## System Overview

The apparatus uses two ESP32 nodes:

- `Server`: USB-connected bridge to the PC. It handles motor control, light readout, magnets, force acquisition, and relays client traffic over ESP-NOW.
- `Client`: remote pegboard node. It controls peg LEDs, streams reed switch states, and performs per-hole hall measurements.

Normal runtime flow:

1. The PC talks to the server over USB serial using a framed binary protocol.
2. The server executes local commands or forwards client-targeted messages over ESP-NOW.
3. The client returns ACK/data frames to the server.
4. The server relays those frames back to the PC.

## Firmware Roles

### Server firmware

Primary commands:

- `CMD_MOTOR (0x01)`
- `CMD_LIGHT (0x02)`
- `CMD_FORCE_START (0x03)`
- `CMD_FORCE_STOP (0x04)`
- `CMD_MAGNET (0x05)`

Primary data output:

- `DATA_FORCE (0x90)` with payload `time_us(u32) + value(i16, 0.1N) + device(u8)`
- `firmware/esp_server_experimental3_modular` extends `DATA_FORCE` to `time_us(u32) + value(i16, 0.1N) + adc_raw_counts(i16) + device(u8)`

The current default force backend is an ADS1115 connected over I2C. The server scans `0x48`, `0x49`, `0x4A`, and `0x4B`, uses the first detected device, sets gain `GAIN_ONE`, and runs at `250 SPS`.

Force conversion path:

1. Read filtered sensor millivolts from the ADS1115 cache.
2. Subtract the tare baseline captured at stream start.
3. Convert the delta to volts.
4. Apply calibration:
   - slope `176.8325 N/V`
   - intercept `-19.5057 N`
5. Encode as `0.1 N` units in the production `DATA_FORCE` packet.

Important force-streaming behavior:

- tare warmup cycles: `12`
- tare accumulation cycles: `96`
- tare timeout: `1.5 s`
- tare RMS stability threshold: `4.0 mV`
- stale ADS1115 data cutoff: `500 ms`

If no ADS1115 is detected, `CMD_FORCE_START` is rejected.

### Client firmware

Primary commands and data:

- `CMD_LED_SET_N (0x10)`
- `CMD_LED_SHOW (0x11)`
- `CMD_HOLE_START (0x12)`
- `CMD_HOLE_STOP (0x13)`
- `CMD_REED_START (0x14)`
- `CMD_REED_STOP (0x15)`
- `DATA_REED (0x91)`
- `DATA_HALL (0x92)`

Client sensor responsibilities:

- peg LED control
- reed switch streaming via I2C expanders
- hall-sensor measurement for selected holes

Relevant client bus addresses:

- hall sensor: `0x0C`
- sub-hole selectors: `0x20`, `0x22`, `0x24`, `0x26`
- reed expanders: `0x21`, `0x23`, `0x25`

## Pairing and Communication

The server and client communicate over ESP-NOW on fixed channel `1`.

Pairing control packet types:

- `CTRL_HELLO`
- `CTRL_PAIR_OFFER`
- `CTRL_PAIR_ACCEPT`
- `CTRL_PAIR_CONFIRM`

Pairing state is persisted in ESP32 NVS (`Preferences`), including local UID, peer UID, peer MAC, and pair state. In practice:

- pairing usually survives reboot and normal reflashing
- first-time pairing is easiest when only the intended pair is powered nearby
- if you swap hardware or need a clean re-pair, erase NVS or fully erase flash

Handshake summary:

1. Unpaired devices broadcast `HELLO` every `500 ms`.
2. The server offers pairing to a valid client.
3. The client replies with `PAIR_ACCEPT`.
4. The server sends `PAIR_CONFIRM` and saves pairing.
5. The client receives `PAIR_CONFIRM` and saves pairing.

After pairing, discovery slows to `2000 ms`, and normal traffic is accepted only from the stored peer.

## Pinouts

### Server ESP32 pinout

| Function | GPIO | Notes |
| --- | --- | --- |
| Motor step | `22` | stepper pulse output |
| Motor direction | `23` | stepper direction |
| Motor enable | `21` | stepper enable |
| Light sensor | `4` | digital input |
| Force sensor right | `32` | legacy/internal ADC1 path |
| Force sensor left | `33` | legacy/internal ADC1 path |
| Magnet right | `18` | digital output |
| Magnet left | `19` | digital output |
| ADS1115 SDA | `25` | force I2C bus |
| ADS1115 SCL | `26` | force I2C bus |

Server force-channel mapping:

- ADS1115 channel `0`: right force sensor
- ADS1115 channel `1`: left force sensor

### Client ESP32 pinout

| Function | GPIO / Address | Notes |
| --- | --- | --- |
| Main I2C SDA | `21` | client sensor bus |
| Main I2C SCL | `22` | client sensor bus |
| LED strip data | `2` | NeoPixel output |
| Reed interrupt | `12` | input pull-up |
| Hole group A | `27` | hole selector line |
| Hole group B | `26` | hole selector line |
| Hole group C | `25` | hole selector line |
| Hole group D | `33` | hole selector line |
| Hole group E | `32` | hole selector line |
| Hole group F | `35` | hole selector line |
| Hall sensor | `0x0C` | I2C device |
| Sub-hole selector 0 | `0x20` | I2C device |
| Sub-hole selector 1 | `0x22` | I2C device |
| Sub-hole selector 2 | `0x24` | I2C device |
| Sub-hole selector 3 | `0x26` | I2C device |
| Reed expander 0 | `0x21` | I2C device |
| Reed expander 1 | `0x23` | I2C device |
| Reed expander 2 | `0x25` | I2C device |

Client LED configuration:

- logical holes: `21`
- LEDs per hole: `8`
- LED addressing range used by the client firmware: `0..20`

Client hole-selection tables are implemented in [firmware/esp_client/esp_client.ino](/C:/Users/pop555877/Documents/GitHub/Apparatus/firmware/esp_client/esp_client.ino).

## Debugging Notes

Most likely issues during bring-up:

- No force stream after `CMD_FORCE_START`: verify ADS1115 wiring, power, and detected address.
- Force stream starts but values are off: verify tare stability and calibration assumptions.
- Devices discover each other but normal traffic fails: check whether one side is paired to an old peer in NVS.
- Force works but client data does not: focus on the client I2C path, not the server force backend.

## Application Notes

- Secure pairing and commissioning plan: [experiments/application-note-opsec-pairing.md](/C:/Users/pop555877/Documents/GitHub/Apparatus/experiments/application-note-opsec-pairing.md)
- Firmware architecture reference used for this README: [firmware/EXPERIMENTAL_CLIENT_SERVER_OVERVIEW.md](/C:/Users/pop555877/Documents/GitHub/Apparatus/firmware/EXPERIMENTAL_CLIENT_SERVER_OVERVIEW.md)
