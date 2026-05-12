# PsychoPy Apparatus

This plugin enables PsychoPy to operate the "Apparatus," a custom device designed for measuring and manipulating physical and cognitive effort in experimental settings.

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/MBieleke/psychopy-apparatus/releases/tag/v1.0.0)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/MBieleke/psychopy-apparatus/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.20133062.svg)](https://doi.org/10.5281/zenodo.20133062)
[![Firmware](https://img.shields.io/badge/firmware-Arduino%20%7C%20ESP32-teal)](https://www.arduino.cc)
[![Plugin](https://img.shields.io/badge/plugin-PsychoPy%20%7C%20Python-E83B3B)](https://www.psychopy.org)


## Repository Overview

| Directory            | Description                                                                                               |
|----------------------|-----------------------------------------------------------------------------------------------------------|
| `documentation`      | Documentation for the Apparatus and its usage. (To be done.)                                              |
| `firmware`           | Arduino source code for ESP32 microcontrollers (server and client roles).                                 |
| `psychopy_apparatus` | Main source code for the plugin.                                                                          |


## Requirements

- PsychoPy version 2025.2.1 or later.
    - Note: As of December 2025, versions after 2025.1.1 have a Plugin Manager bug. Install 2025.1.1 first, open the Plugin Manager, then upgrade to 2025.2.x.
    - This plugin has not been tested with PsychoPy Studio.
- [SiliconLabs CP210x driver](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads) for USB-to-UART communication.

## Installation

1. Clone this repository using Git or download the source code.
2. Open PsychoPy Builder and navigate to the Plugin/Packages Manager.
3. In the "Packages" tab, click "Install from file" and select the `pyproject.toml` file. Change the file type dropdown to "Python projects" to locate it.


## Usage

1. Connect the ESP32 (server role) to your computer via USB.
2. In PsychoPy, open the device manager and add a device named `apparatus`. Specify the serial port path (e.g., `COM4` on Windows). Use Device Manager to identify the correct port (`CP210x USB to UART Bridge`).
3. Ensure the CP210x driver is installed.
4. In Builder, new components will appear under the `Apparatus` section. These provide basic control; for advanced usage, refer to the code examples.


## Components

| Component          | Description                                                         | Status   |
|--------------------|---------------------------------------------------------------------|----------|
| `ApparatusForce`   | Measures handgrip force (N) for white and blue dynamometers         | beta     |
| `ApparatusLED`     | Controls LEDs on the 20-hole board                                  | beta     |
| `ApparatusReed`    | Detects reed contacts (peg inserts/removals)                        | beta     |
| `ApparatusMagnet`  | Controls magnets holding pegs in dynamometers                       | planned  |
| `ApparatusMotor`   | Operates the Apparatus turntable                                    | planned  |
| `ApparatusHall`    | Reads hall sensors for 3D proximity in each hole                    | planned  |


## Code Overview

All user-facing functions are documented in their respective `.py` files.

| File                          | Description                                                             | Classes                                                     |
|-------------------------------|-------------------------------------------------------------------------|-------------------------------------------------------------|
| `hardware/apparatus.py`       | High-level control of the Apparatus; constructs serial commands.        | `Apparatus`                                                 |
| `hardware/apparatusDevice.py` | Low-level device management; handles serial communication with ESP32.   | `ApparatusResponse`, `ApparatusProtocol`, `ApparatusDevice` |
| `utils/protocol.py`           | Helper functions for COBS encoding and XOR hecksums.                    |                                                             |

## How to Cite

Please cite this repositorium if you use the Apparatus in academic work.

### APA style

```text
Albrecht, M., Heinzelmann, L., Tessari, R., & Bieleke, M. (2026). *PsychoPy Apparatus* (v1.0.0). Zenodo. <https://doi.org/10.5281/zenodo.20133062>
```

### BibTeX

```bibtex
@software{Albrecht:2026,
  author  = {Albrecht, Matthias and Tessari, Ralf and Heinzelmann, Lukas and Bieleke, Maik},
  title   = {PsychoPy Apparatus},
  version = {1.0.0},
  year    = {2026},
  doi     = {10.5281/zenodo.20133062},
  url     = {https://doi.org/10.5281/zenodo.20133062}
}
```

### Related publications

- Wientges, J., Bieleke, M., Wolff, W., Fischer, U., & Schüler, J. (2025). A novel approach to analysing cognitive and physical effort in a unified motor task. PsyArXiv. <https://doi.org/10.13140/RG.2.2.23574.46401>

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, improvements, or new features.

## License

PsychoPy Apparatus is released under the **MIT License**.
See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This repositorium is based on [psychopy-pegboard](https://github.com/SportPsychologyLab/psychopy-pegboard) by [biosmanager](https://github.com/biosmanager), which has been retired as repositorium for operating the Apparatus in January 2026.

## Support

For questions, issues, or feature requests, please open an issue on GitHub or contact the maintainer [maik.bieleke@uni-konstanz.de](mailto:maik.bieleke@uni-konstanz.de).

