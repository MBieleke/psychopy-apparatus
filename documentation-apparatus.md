---
title: "Apparatus Setup Guide"
author: "Carolina"
date: "2026-08-02"
---

# Apparatus

## 1. The Apparatus: Fundamentals & Structure

**What is the Apparatus?**

*#####Modifications in progress*

*The Apparatus is a rotating pegboard equipped with 20 holes featuring LED light rings and sensors, which can be controlled using the Pegboard software. In addition to visual stimuli, auditory stimuli can also be played back through a built-in speaker. The Apparatus was developed in the Sports Psychology Laboratory by Dr. Ursula Fischer and Dr. Wanja Wolff and built by the scientific workshops at the University of Konstanz. The experimental setup allows for the continuous manipulation of various independent variables and can be programmed completely freely.*

## 2. System Architecture & Hardware Foundations

This section outlines the physical hardware design, microcontroller roles, and the pinout mapping configuration of the university-designed apparatus.

### 2.1 High-Level Architecture (USB Control)

The system operates under a streamlined Direct USB Control topology:

- Microcontrollers: The apparatus utilizes two ESP32 microcontrollers configured in a Server-Client relationship.

- Inter-device Communication: The ESP32 Server and ESP32 Client communicate wirelessly using the ESP-NOW (WiFi) protocol.

- PC Integration: The ESP32 Server establishes a direct Serial USB connection with the experimental computer. PsychoPy interacts exclusively with the Server via this serial interface to log data and dispatch high-level control commands.

### 2.2 Hardware Pinout & Component Mapping

The following tables define the active physical pin connections (GPIO) and I2C addresses for both microcontrollers.

### 2.2.1 ESP32 Client Configuration

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
- *Note: Sub-hole selectors 0 to 3 (`0x20, 0x22, 0x24, 0x26`) are currently physically present but software-unused.*

------------------------------------------------------------------------

*Hardware Variant Note: The pinout configuration detailed above corresponds strictly to the production-grade hardware currently deployed inside the physical Apparatus casing. It does NOT match the standalone development kits (Devkits) distributed for testing or prototyping. Researchers testing software on Devkits must cross-reference their specific board layouts as they differ from this primary experimental setup.*

*Safety Note: "Unused" components remain fully compiled in the firmware codebase. They represent available experimental hardware parameters but do not acquire or transmit data during the current cognitive/physical effort protocols.*

### 2.2.2 ESP32 Server Configuration

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

# 3. Software Installation & Environment Setup

This section details the step-by-step configuration required to prepare a local Windows computer to recognize, interface with, and control the physical apparatus.

## 3.1 USB-to-Serial Driver Installation (CP210x)

The ESP32 Server communicates with the PC via a Silicon Labs CP210x USB-to-UART Bridge chip. Windows requires the specific hardware driver to map the device to a virtual COM port.

1.  **Download**: Download the official **CP210x Universal Windows Driver** from Silicon Labs.
2.  **Installation**: Extract the `.zip` folder, right-click on `silabser.inf`, and select **Install**. Follow the desktop prompts.
3.  **Verification**:
    - Connect the ESP32 Server to the PC using a USB data cable.
    - Open the Windows **Device Manager** (`devmgmt.msc`).
    - Expand the **Ports (COM & LPT)** section.
    - Verify that **"Silicon Labs CP210x USB to UART Bridge (COMx)"** is listed without any yellow warning triangles. Note down the specific `COM` port number assigned (e.g., `COM3`).

## 3.2 PsychoPy Environment & Version Constraints

Due to a known upstream issue in the PsychoPy software framework, strict version control must be enforced to ensure plugin compatibility.

- **The PsychoPy Bug**: As of late 2025, PsychoPy releases *after* version **2025.1.1** contain a critical Plugin Manager bug that prevents the university-designed apparatus components from loading correctly.
- **Required Version**: The experimental setup **must** be deployed exclusively on **PsychoPy 2025.1.1**. Do not update the software past this release unless a patch is explicitly pushed to the main repository.

### 3.2.1 Installing the Apparatus Plugin

Once PsychoPy 2025.1.1 is active on Windows: 1. Open the PsychoPy application. 2. Navigate to the **Tools** menu and open the **Plugin Manager**. 3. Search for `psychopy-apparatus` or manual-load the local folder source to register the `ApparatusForce`, `ApparatusLED`, and `ApparatusReed` components into your experiment builder palette.

*#####Modifications in progress - Extract from previous Documentation*

***The Apparatus Interfaces - ESP32 Modules***

*There are two microcontrollers built into the Apparatus. They communicate with each other, execute commands from the Raspberry Pi, and receive data from the sensors. One microcontroller is located directly underneath the turntable and is responsible for reading the data as well as controlling the LED light rings in the holes. It is powered by a power bank—also located underneath the turntable—and communicates with the second ESP32.*

*The second microcontroller is located in the stationary housing. In addition to communicating with the turntable and the control laptop, it is responsible for controlling the motor, the speaker, and the LED control of the comparison hole. Just like the Raspberry Pi, it is powered by the wall power adapter (labeled/coded with 2 and 3).*

\*\*

***The Pegs & Sensors***

*The cylindrical pegs are made of balsa wood and feature an embedded magnet at one end. In combination with the reed switch built into the holes, this magnet confirms when a peg has entered a hole. In addition to measurements using the reed sensors, there is also the option to use the built-in Hall sensors. (However, in practice, this highly sensitive and extremely accurate measurement methodology has proven impractical so far due to the massive volume of data generated.) At the other end of the peg, a metal plate is embedded, which is attracted by the electromagnet of the hand dynamometer.*

\*\*

***Hand Dynamometer***

*In addition to the basic functions of the Apparatus, two connected hand dynamometers can be used. These are connected directly to the built-in ESP32 module via a British telephone jack connector and can be controlled in Node-Red. Attached to the Vernier hand dynamometer is an electromagnet that can be controlled via four threshold values: N & n, and F & f.*

*The threshold values can be set separately for each hand dynamometer:*

- *N determines the minimum force that must be applied for the magnet to activate.*

- *If the force drops below n, the magnet is turned off again.*

- *F determines the maximum force that can be applied before the magnet shuts off.*

- *f (like n) defines the range of the hysteresis barrier.*

*Furthermore, T defines the time in milliseconds \[ms\], which determines how long a force may be maintained within the hysteresis range before the electromagnet shuts off.*

***System Overview and Communication Protocol***

*The system operates using a dual-microcontroller architecture comprised of two ESP32 modules: a Server and a Client. These modules distribute the computational workload and communicate wirelessly via the ESP-NOW protocol (Wi-Fi).*

*Data transmission between the Apparatus and the workstation running PsychoPy is handled exclusively through a standard Serial USB connection connected to the Server module.*

*1. ESP32 Client Architecture (The Rotating Pegboard)*

*The Client microcontroller is positioned beneath the rotating turntable. Its primary functions are to control the visual feedback array and to detect peg insertions within the 20-hole matrix.*

***GPIO Pin Assignment***

- ***GPIO 21 (I2C_SDA) & GPIO 22 (I2C_SCL):** These pins form the main I2C bus channel, serving as the primary data highway for the peripheral sensors on the turntable.*

- ***GPIO 12 (REED_INT):** Configured as an input with an internal pull-up resistor. This pin acts as a hardware interrupt. When a peg is inserted, it immediately signals the microcontroller to process the sensor data.*

- ***GPIO 2 (LED_PIN):** Dedicated data line for the main WS2812 addressable LED strip, which illuminates the light rings around the holes.*

- ***GPIO 27 to 35 (GROUP_A to GROUP_F):** Initially designated for Hall effect sensor group selection. These pins are currently unused in the current experimental paradigm.*

***I2C Bus Address Map***

*Due to the high number of inputs required for the 20 holes, I2C port expanders are utilized to multiply the available inputs:*

- ***Addresses 0x21, 0x23, 0x25:** Connected to the Reed/PCF8574 expander modules responsible for detecting the magnetic insertion of the balsa wood pegs.*

- ***Addresses 0x0C and 0x20 to 0x26:** Associated with the Hall sensors and sub-hole selectors. These components are currently unused.*

*2. ESP32 Server Architecture (The Stationary Base and Force Measurement)*

*The Server microcontroller is located within the stationary housing of the apparatus. It interfaces directly with the computer via USB, manages the electromagnetic physical constraints, and processes force data.*

***GPIO Pin Assignment***

- ***GPIO 18 (MAGNET_RIGHT_PIN) & GPIO 19 (MAGNET_LEFT_PIN):** Digital outputs that control the left and right electromagnets attached to the hand dynamometer.*

- ***GPIO 25 (FORCE_ADC_SDA_PIN) & GPIO 26 (FORCE_ADC_SCL_PIN):** I2C communication lines dedicated to the external ADS1115 Analog-to-Digital Converter (ADC).*

- ***GPIO 21, 22, 23 (MOTOR_ENABLE, STEP, DIR):** Assigned to the stepper motor driver for automated turntable rotation. These are currently unused.*

- ***GPIO 4 (LIGHT_SENSOR_PIN):** Digital input for the optical positioning system. This is currently unused.*

- ***GPIO 32 & 33 (FORCE_SENSOR_RIGHT/LEFT):** Internal ADC channels for direct analog force readings. These are currently unused by the active backend.*

***Server I2C Address Map***

- ***Address 0x48:** Allocated to the external ADS1115 force ADC. This high-precision chip converts analog pressure from the hand dynamometer into digital values for PsychoPy, bypassing the internal ESP32 ADC pins.*

*Functional Specification Note*

*Components and firmware parameters marked as unused indicate that their corresponding physical hardware or software functions are dormant within the current experimental configuration. While the source code retains the foundational infrastructure for motor automation, light barriers, and Hall effect data streams, the active paradigm relies exclusively on manual turntable rotation, Reed switch peg detection, LED feedback illumination, and digital hand dynamometer force tracking.*