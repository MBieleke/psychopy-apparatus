# esp_server_experimental3_modular

This folder is the Wave 1 modular refactor of the current experimental server firmware.
The `experimental3` variant extends `DATA_FORCE` with embedded raw ADC counts.

Baseline source:
- `firmware/esp_server_experimental/esp_server_experimental2.ino`

Wave 1 goals:
- preserve runtime behavior
- keep the sketch single-threaded
- move subsystem implementations out of the `.ino`

Current module layout:
- `apparatus_config.h`: board and firmware configuration macros shared across modules
- `apparatus_protocol.h`: protocol constants and wire-format structs
- `protocol_utils.{h,cpp}`: checksum and COBS helpers
- `protocol_io.{h,cpp}`: serial framing, ACK/NACK, and outbound server messages
- `motor_control.{h,cpp}`: stepper setup and motor state application
- `force_service.{h,cpp}`: force backend setup, tare/filtering, and streaming
- `pairing_radio.{h,cpp}`: ESP-NOW peer management and pairing flow
- `esp_server_experimental3_modular.ino`: top-level wiring, command dispatch, setup, and loop
