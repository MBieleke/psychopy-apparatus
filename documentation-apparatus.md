---
title: "Apparatus Setup Guide"
date: "2026-08-02"
---

# Apparatus

## Table of Contents

- **1. Introduction and Fundamentals**
  - 1.1 System Purpose and High-Level Description
  - 1.2 High-Level Architecture (USB Topology)
- **2. External Physical Specifications**
  - 2.1 Chassis Dimensions and Materials
  - 2.2 Figure 1: Full Frontal View of the Apparatus
  - 2.3 Component Layout Description
  - 2.4 Inventory and Cable Interface
- **3. Visual Component Log and Labels**
  - 3.1 Figure 2: Front Panel Interface
  - 3.2 Figure 3: Input Transducers (Handgrips)
- **4. System Architecture & Hardware Foundations**
  - 4.1 High-Level Architecture (USB Control)
  - 4.2 Hardware Pinout & Component Mapping
- **5. Software Installation & Environment Setup**
  - 5.1 USB-to-Serial Driver Installation (CP210x)
  - 5.2 PsychoPy Environment & Version Constraints
  - 5.3 Serial Connection Mapping
- **6. First-Time Operation Guide**
  - 6.1 Step-by-Step Power-Up Sequence

## 1. Introduction and Fundamentals

**What is the Apparatus?**

The Apparatus is a rotating pegboard equipped with 20 holes featuring integrated LED light rings and magnetic sensors, controlled directly within the **PsychoPy** framework via a custom plugin. In addition to dynamic visual stimuli, the system delivers auditory feedback through a built-in internal speaker.

This versatile experimental setup allows for the continuous manipulation of multiple independent variables. Operating within an open-source programming architecture, the entire ecosystem can be programmed completely freely to accommodate complex physical and cognitive effort protocols.

------------------------------------------------------------------------

## 2. External Physical Specifications

### 2.1 Chassis Dimensions and Materials

The Apparatus is constructed within a solid, custom made wood case designed specifically for desktop laboratory deployment.

The panels and outer case are custom made from precision cut clear wood, creating a stable and solid frame designed to sit on a laboratory desk.

- **Total Outer Panel Dimensions**: 90 cm x 90 cm
- **Rotator Spin Diameter**: 70 cm
- **Outer Hole Diameter**: 5 cm
- **Built-In Speaker Diameter**: 10 cm
- **Primary Materials**: Natural wood face panels integrated with internal mechanical components and flush mounted electrical sensor housings

### 2.2 Figure 1: Full Frontal View of the Apparatus

<img src="images/figure%200.png" width="480"/>

### 2.3 Component Layout Description

At the macro level, the device consists of a centralized, mechanical rotating pegboard disk embedded within a square control frame:

- **The Rotating Pegboard**: Features exactly 20 precision-drilled holes arranged in a concentric circular matrix. The cylindrical pegs are constructed from lightweight balsa wood and feature an embedded magnet at one end to trigger the internal tracking sensors.

- **Visual Feedback**: Every single hole is surrounded by an integrated, flush-mounted circular LED light ring containing programmable WS2812 addressable components.

- **Silent Hardware Features**:

  - *Acoustic System*: A built-in internal audio speaker mounted within the chassis, capable of playing back auditory stimuli and error tones directly from the hardware layer.
  - *Mechanical Motion*: An internal motion rotator assembly that allows the centralized pegboard matrix to spin or adjust orientation continuously during experimental trial transitions.

### 2.4 Peripheral Inventory and Cable Interface

Connection of external accessories is restricted to the dedicated outer ports of the housing:

- **Main PC Data Link**: The system connects to the experimental workstation using a single standard Serial-over-USB data cable linked directly to the internal Server module.

- **Handgrip Dynamometers**: The apparatus includes two custom-integrated Vernier handgrip dynamometers (color-coded as White and Blue). These isometric transducers measure linear grip force exerted by the participant.

------------------------------------------------------------------------

## 3. Visual Component Log and Labels

### 3.1 Figure 2: Lateral View of the Apparatus

<img src="images/figure%202.png" width="480"/>

### 3.2 Input Transducers (Handgrips)

*#####Images in progress*

Figure 2: External Force Transducers.

Labels to include in graphic:

Label E: White Dynamometer (Device ID 0)

Label F: Blue Dynamometer (Device ID 1)

Label G: Main Strain-Gauge Signal Cable Connection

## 4. System Architecture & Hardware Foundations

This section outlines the physical hardware design, microcontroller roles, and the pinout mapping configuration of the university-designed apparatus.

## 4.1 High-Level Architecture (USB Control)

The system operates under a streamlined Direct USB Control topology:

- Microcontrollers: The apparatus utilizes two ESP32 microcontrollers configured in a Server-Client relationship.

- Inter-device Communication: The ESP32 Server and ESP32 Client communicate wirelessly using the ESP-NOW (WiFi) protocol.

- PC Integration: The ESP32 Server establishes a direct Serial USB connection with the experimental computer. PsychoPy interacts exclusively with the Server via this serial interface to log data and dispatch high-level control commands.

## 4.2 Hardware Pinout & Component Mapping

The following tables define the active physical pin connections (GPIO) and I2C addresses for both microcontrollers.

*#####Images in progress* Figure 3: Main Circuit Board and ESP32 Microcontroller Interconnects.

### 4.2.1 ESP32 Client Configuration

The Client microcontroller manages visual feedback (LEDs) and primary input sensors.

| ESP32 GPIO | Firmware Identifier | Physical Component / Purpose | Status |
|:-----------------|:-----------------|:-----------------|:-----------------|
| **21** | `I2C_SDA` | Main Client I2C Data Line | **Active** |
| **22** | `I2C_SCL` | Main Client I2C Clock Line | **Active** |
| **2** | `LED_PIN` | Main WS2812 LED Strip Data Output | **Active** |
| **12** | `REED_INT` | Reed/PCF8574 Expander Interrupt Input (`INPUT_PULLUP`) | **Active** |
| **25, 26, 27** | `GROUP_C, B, A` | Hall Group Select Channels | *Unused in current study* |
| **32, 33, 35** | `GROUP_E, D, F` | Hall Group Select Channels | *Unused in current study* |

#### Client I2C Device Addresses

- **`0x0C`**: Hall Sensor (Active)
- **`0x21`**: PCF8574 I/O Expander 0 (Active)
- **`0x23`**: PCF8574 I/O Expander 1 (Active)
- **`0x25`**: PCF8574 I/O Expander 2 (Active)

*Note: Sub-hole selectors 0 to 3 (`0x20, 0x22, 0x24, 0x26`) are currently physically present but software-unused.*

------------------------------------------------------------------------

*Hardware Note: The pinout configuration detailed above corresponds strictly to the production-grade hardware currently deployed inside the physical Apparatus casing. It does NOT match the standalone development kits (Devkits) distributed for testing or prototyping. Researchers testing software on Devkits must cross-reference their specific board layouts as they differ from this primary experimental setup.*

*Safety Note: "Unused" components remain fully compiled in the firmware codebase. They represent available experimental hardware parameters but do not acquire or transmit data during the current cognitive/physical effort protocols.*

### 4.2.2 ESP32 Server Configuration

The Server microcontroller acts as the central hub, managing force transducers, magnetic loads, and PC communication.

| ESP32 GPIO | Firmware Identifier | Physical Component / Purpose | Status |
|:-----------------|:-----------------|:-----------------|:-----------------|
| **25** | `FORCE_ADC_SDA_PIN` | ADS1115 I2C Data Line (Handgrip Force Data) | **Active** |
| **26** | `FORCE_ADC_SCL_PIN` | ADS1115 I2C Clock Line (Handgrip Force Data) | **Active** |
| **18** | `MAGNET_RIGHT_PIN` | Right Electromagnetic Load Output | **Active** |
| **19** | `MAGNET_LEFT_PIN` | Left Electromagnetic Load Output | **Active** |
| **32** | `FORCE_SENSOR_RIGHT_PIN` | Internal ADC Force Right (Internal Backend Only) | *Unused in current study* |
| **33** | `FORCE_SENSOR_LEFT_PIN` | Internal ADC Force Left (Internal Backend Only) | *Unused in current study* |
| **4** | `LIGHT_SENSOR_PIN` | Light Sensor Digital Input | *Unused in current study* |
| **21, 22, 23** | `MOTOR_ENABLE/STEP/DIR` | Stepper Driver Control Pins | *Unused in current study* |

#### Server I2C Device Addresses

- **`0x48`**: ADS1115 Force Analog-to-Digital Converter (ADC). This chip amplifies and processes the handgrip force data (measured in Newtons) before transmission.

------------------------------------------------------------------------

*Safety Note: "Unused" components remain fully compiled in the firmware codebase. They represent available experimental hardware parameters but do not acquire or transmit data during the current cognitive/physical effort protocols.*

# 5. Software Installation & Environment Setup

*#####Modifications in progress*

This section details the step-by-step configuration required to prepare a local Windows computer to recognize, interface with, and control the physical apparatus.

## 5.1 USB-to-Serial Driver Installation (CP210x)

The ESP32 Server communicates with the PC via a Silicon Labs CP210x USB-to-UART Bridge chip. Windows requires the specific hardware driver to map the device to a virtual COM port.

1.  Download: Download the official CP210x Universal Windows Driver from Silicon Labs.
2.  Installation: Extract the `.zip` folder, right-click on `silabser.inf`, and select Install. Follow the desktop prompts.
3.  Verification:
    - Connect the ESP32 Server to the PC using a USB data cable.
    - Open the Windows Device Manager (`devmgmt.msc`).
    - Expand the Ports (COM & LPT) section.
    - Verify that "Silicon Labs CP210x USB to UART Bridge (COMx)" is listed without any yellow warning triangles. Note down the specific `COM` port number assigned (e.g., `COM3`).

## 5.2 PsychoPy Environment

Due to a known upstream issue in the PsychoPy software framework, strict version control must be enforced to ensure plugin compatibility.

- The PsychoPy Bug: As of late 2025, PsychoPy releases after version 2025.1.1 contain a critical Plugin Manager bug that prevents the university-designed apparatus components from loading correctly.
- Required Version: The experimental setup must be deployed exclusively on PsychoPy 2025.1.1. Do not update the software past this release unless a patch is explicitly pushed to the main repository.

### 5.2.1 Installing the Apparatus Plugin

Once PsychoPy 2025.1.1 is active on Windows:

1.  Open the PsychoPy application.

2.  Navigate to the Tools menu and open the Plugin Manager.

3.  Search for `psychopy-apparatus` or manual-load the local folder source to register the `ApparatusForce`, `ApparatusLED`, and `ApparatusReed` components into your experiment builder palette.

## 5.3 Serial Connection

The connection and raw data exchange between Windows and the physical hardware are managed by the core script `apparatusDevice.py`. This implementation wraps the `pySerial` library to build a non-blocking, multi-threaded serial interface.

### 5.3.1 Port Initialization

When an experiment initiates the `ApparatusDevice` class, the framework executes the following hardware initialization sequence:

1.  Port Allocation: The device binds to a designated Windows port (e.g., `COM3`) at a hardcoded transmission speed of 115200 baud (`baudrate=115200`).

2.  Hardware Auto-Reset Mitigation: Many ESP32 development boards automatically reboot when a serial connection is established. To prevent data corruption, the script enforces a mandatory 4-second startup delay (`startup_delay=4.0`). This pause allows the microcontrollers to complete their boot sequence safely.

3.  Buffer Flushing: Immediately following the delay, the system calls `reset_input_buffer()` and `reset_output_buffer()` to purge any electrical noise or boot-time garbage text generated during power-up, ensuring the protocol starts on a clean frame boundary.

### 5.3.2 Multi-Threaded Ingestion Background Process

To ensure that high-frequency sensor tracking does not cause visual lag or frame drops in PsychoPy, serial monitoring is decoupled from the main thread:

- The Reader Thread: The script deploys a background `ReaderThread` utilizing an `ApparatusProtocol` class.

- Byte Asynchrony: This background routine constantly scans incoming binary traffic byte-by-byte. It intercepts raw data packets, checks for the `0x00` frame delimiter, and instantly pushes parsed metrics into a central asynchronous data queue (`_responses`).

### 5.3.3 Object-Oriented Event Handling

Every valid incoming signal is encapsulated into an `ApparatusResponse` object. The class exposes standardized high-level properties that map directly to physical behavioral sensors:

- `whiteForce` / `whiteForceRawCounts`: Real-time grip force data from the white dynamometer (Device ID 0).

- `blueForce` / `blueForceRawCounts`: Real-time grip force data from the blue dynamometer (Device ID 1).

- `reed_bits` / `reed_holes`: Positional array tracking which specific pegboard holes are currently plugged or unplugged by the participant.

## 6. First-Time Operation Guide

### 6.1 Step-by-Step Power-Up Sequence

To avoid port synchronization errors or packet drop during initialization, users must strictly follow this external deployment recipe: 1. **Peripheral Connection**: Connect both the White and Blue Vernier handgrips to their respective chassis sockets using the external British telephone jack interfaces before powering the unit. 2. **PC Data Link**: Connect the main Serial-USB data cable from the stationary base port to an active USB interface on the Windows workstation. 3. **Hardware Activation**: Toggle the primary power switch on the housing. 4. **Boot Wait-Time**: Wait a mandatory **4 seconds** without opening any software. This allows the ESP32 Server to stabilize its wireless ESP-NOW link with the Client and flush power-up transmission noise. 5. **Software Execution**: Open PsychoPy 2025.1.1 and launch your experimental protocol script.