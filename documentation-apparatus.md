---
title: "Apparatus Setup Guide"
author: "Carolina"
date: "2026-08-02"
---

## **Apparatus**

\
**The Apparatus \~ Fundamentals & Structure**

\

**What is the Apparatus?**

The Apparatus is a rotating pegboard equipped with 20 holes featuring LED light rings and sensors, which can be controlled using the Pegboard software. In addition to visual stimuli, auditory stimuli can also be played back through a built-in speaker. The Apparatus was developed in the Sports Psychology Laboratory by Dr. Ursula Fischer and Dr. Wanja Wolff and built by the scientific workshops at the University of Konstanz. The experimental setup allows for the continuous manipulation of various independent variables and can be programmed completely freely.

\

**How is the Apparatus structured?**

***Controlling the Device \~ The Raspberry Pi***

*The Apparatus is controlled via a connection to a built-in single-board computer, the Raspberry Pi. When powered, it establishes its own Wi-Fi network, which you must log into. Once connected to the network, you can, among other things, program new experimental procedures, start prepared experimental runs, download data, and directly access the operating system (Linux).*

*\###################### change*

*System Architecture Evolution: Transition from Raspberry Pi to Direct USB Control*

***Historical Context***

*The initial iteration of the Apparatus control system relied on an embedded single-board computer (Raspberry Pi) integrated into the hardware housing. In that legacy configuration, the Raspberry Pi functioned as a local Linux server, establishing a dedicated Wi-Fi network. Researchers were required to log into this network and utilize a Node-Red interface to deploy experimental paradigms, manage data packets, and orchestrate communication between the built-in ESP32 microcontrollers.*

***Current Architecture***

*In the current implementation optimized for the psychopy-apparatus framework, the Raspberry Pi and the Node-Red network infrastructure have been completely bypassed.*

*Control authority is now centralized within the local workstation running Python and PsychoPy. The workstation interfaces directly with the stationary ESP32 Server microcontroller via a physical Serial USB connection. The master-client communication between the Server and the rotating Client microcontroller continues to operate wirelessly via the ESP-NOW protocol, but the data transmission pipeline to the PC is fully hardware-serialized.*

***Implications for the Experimental Setup***

*This architectural streamlined shift alters the system deployment procedure in the following ways:*

- ***Network Infrastructure:** There is no longer a requirement to connect the workstation to an external or device-specific Wi-Fi network to run experiments.*

- ***Software Dependencies:** Linux OS access and Node-Red runtime environments are obsolete for the user. All experimental logic, hardware initialization, and data logging are managed natively through the PsychoPy Python package execution.*

- ***Hardware Interfacing:** The physical setup is reduced to connecting a standard USB cable from the workstation to the Apparatus Server module port.*

\######################

**The Apparatus Interfaces \~ ESP32 Modules**

There are two microcontrollers built into the Apparatus. They communicate with each other, execute commands from the Raspberry Pi, and receive data from the sensors. One microcontroller is located directly underneath the turntable and is responsible for reading the data as well as controlling the LED light rings in the holes. It is powered by a power bank—also located underneath the turntable—and communicates with the second ESP32.

The second microcontroller is located in the stationary housing. In addition to communicating with the turntable and the control laptop, it is responsible for controlling the motor, the speaker, and the LED control of the comparison hole. Just like the Raspberry Pi, it is powered by the wall power adapter (labeled/coded with 2 and 3).

\

**The Pegs & Sensors**

The cylindrical pegs are made of balsa wood and feature an embedded magnet at one end. In combination with the reed switch built into the holes, this magnet confirms when a peg has entered a hole. In addition to measurements using the reed sensors, there is also the option to use the built-in Hall sensors. (However, in practice, this highly sensitive and extremely accurate measurement methodology has proven impractical so far due to the massive volume of data generated.) At the other end of the peg, a metal plate is embedded, which is attracted by the electromagnet of the hand dynamometer.

\

**Hand Dynamometer**

In addition to the basic functions of the Apparatus, two connected hand dynamometers can be used. These are connected directly to the built-in ESP32 module via a British telephone jack connector and can be controlled in Node-Red. Attached to the Vernier hand dynamometer is an electromagnet that can be controlled via four threshold values: N & n, and F & f.

The threshold values can be set separately for each hand dynamometer:

- N determines the minimum force that must be applied for the magnet to activate.

- If the force drops below n, the magnet is turned off again.

- F determines the maximum force that can be applied before the magnet shuts off.

- f (like n) defines the range of the hysteresis barrier.

Furthermore, T defines the time in milliseconds \[ms\], which determines how long a force may be maintained within the hysteresis range before the electromagnet shuts off.

**Pin out**

Client

|                |                   |                                         |
|----------------|-------------------|-----------------------------------------|
| **ESP32 GPIO** | **Firmware name** | **Attached / purpose**                  |
| 21             | I2C_SDA           | Main client I2C SDA                     |
| 22             | I2C_SCL           | Main client I2C SCL                     |
| 35             | GROUP_F           | Hall group select F \| CURRENTLY UNUSED |
| 32             | GROUP_E           | Hall group select E \| CURRENTLY UNUSED |
| 33             | GROUP_D           | Hall group select D \| CURRENTLY UNUSED |
| 25             | GROUP_C           | Hall group select C \| CURRENTLY UNUSED |
| 26             | GROUP_B           | Hall group select B \| CURRENTLY UNUSED |
| 27             | GROUP_A           | Hall group select A \| CURRENTLY UNUSED |
| 12             | REED_INT          | Reed/PCF interrupt input, INPUT_PULLUP  |
| 2              | LED_PIN           | Main WS2812 LED strip data              |

I2C attached devices:

|             |                                         |
|-------------|-----------------------------------------|
| **Address** | **Attached / purpose**                  |
| 0x0C        | Hall sensor                             |
| 0x20        | Sub-hole selector 0 \| CURRENTLY UNUSED |
| 0x22        | Sub-hole selector 1 \| CURRENTLY UNUSED |
| 0x24        | Sub-hole selector 2 \| CURRENTLY UNUSED |
| 0x26        | Sub-hole selector 3 \| CURRENTLY UNUSED |
| 0x21        | Reed/PCF expander 0                     |
| 0x23        | Reed/PCF expander 1                     |
| 0x25        | Reed/PCF expander 2                     |

ESP32 Server:

|  |  |  |
|----|----|----|
| **ESP32 GPIO** | **Firmware name** | **Attached / purpose** |
| 22 | MOTOR_STEP_PIN | Stepper driver STEP \| CURRENTLY UNUSED |
| 23 | MOTOR_DIR_PIN | Stepper driver DIR \| CURRENTLY UNUSED |
| 21 | MOTOR_ENABLE_PIN | Stepper driver ENABLE \| CURRENTLY UNUSED |
| 4 | LIGHT_SENSOR_PIN | Light sensor digital input \| CURRENTLY UNUSED |
| 18 | MAGNET_RIGHT_PIN | Right magnet output |
| 19 | MAGNET_LEFT_PIN | Left magnet output |
| 25 | FORCE_ADC_SDA_PIN | ADS1115 I2C SDA |
| 26 | FORCE_ADC_SCL_PIN | ADS1115 I2C SCL |
| 32 | FORCE_SENSOR_RIGHT_PIN | Internal ADC force right, only for internal backend \| CURRENTLY UNUSED |
| 33 | FORCE_SENSOR_LEFT_PIN | Internal ADC force left, only for internal backend \| CURRENTLY UNUSED |

 

Server I2C 

|                       |                        |
|-----------------------|------------------------|
| **Address / channel** | **Attached / purpose** |
| 0x48                  | ADS1115 force ADC      |
|                       |                        |
|                       |                        |

*Server uses Serial USB for the Data transmission to the PC (and thus Psychopy) and Server+Client use ESP-NOW/WiFi to communicate*

*Unused in the case here doesnt mean its not in software, it just means this experiment does not use it in any way shape or form, however technically it is still there and available.*

Technical Specification of the Apparatus Hardware Architecture

**System Overview and Communication Protocol**

The system operates using a dual-microcontroller architecture comprised of two ESP32 modules: a Server and a Client. These modules distribute the computational workload and communicate wirelessly via the ESP-NOW protocol (Wi-Fi).

Data transmission between the Apparatus and the workstation running PsychoPy is handled exclusively through a standard Serial USB connection connected to the Server module.

1\. ESP32 Client Architecture (The Rotating Pegboard)

The Client microcontroller is positioned beneath the rotating turntable. Its primary functions are to control the visual feedback array and to detect peg insertions within the 20-hole matrix.

**GPIO Pin Assignment**

- **GPIO 21 (I2C_SDA) & GPIO 22 (I2C_SCL):** These pins form the main I2C bus channel, serving as the primary data highway for the peripheral sensors on the turntable.

- **GPIO 12 (REED_INT):** Configured as an input with an internal pull-up resistor. This pin acts as a hardware interrupt. When a peg is inserted, it immediately signals the microcontroller to process the sensor data.

- **GPIO 2 (LED_PIN):** Dedicated data line for the main WS2812 addressable LED strip, which illuminates the light rings around the holes.

- **GPIO 27 to 35 (GROUP_A to GROUP_F):** Initially designated for Hall effect sensor group selection. These pins are currently unused in the current experimental paradigm.

**I2C Bus Address Map**

Due to the high number of inputs required for the 20 holes, I2C port expanders are utilized to multiply the available inputs:

- **Addresses 0x21, 0x23, 0x25:** Connected to the Reed/PCF expander modules responsible for detecting the magnetic insertion of the balsa wood pegs.

- **Addresses 0x0C and 0x20 to 0x26:** Associated with the Hall sensors and sub-hole selectors. These components are currently unused.

2\. ESP32 Server Architecture (The Stationary Base and Force Measurement)

The Server microcontroller is located within the stationary housing of the apparatus. It interfaces directly with the computer via USB, manages the electromagnetic physical constraints, and processes force data.

**GPIO Pin Assignment**

- **GPIO 18 (MAGNET_RIGHT_PIN) & GPIO 19 (MAGNET_LEFT_PIN):** Digital outputs that control the left and right electromagnets attached to the hand dynamometer.

- **GPIO 25 (FORCE_ADC_SDA_PIN) & GPIO 26 (FORCE_ADC_SCL_PIN):** I2C communication lines dedicated to the external ADS1115 Analog-to-Digital Converter (ADC).

- **GPIO 21, 22, 23 (MOTOR_ENABLE, STEP, DIR):** Assigned to the stepper motor driver for automated turntable rotation. These are currently unused.

- **GPIO 4 (LIGHT_SENSOR_PIN):** Digital input for the optical positioning system. This is currently unused.

- **GPIO 32 & 33 (FORCE_SENSOR_RIGHT/LEFT):** Internal ADC channels for direct analog force readings. These are currently unused by the active backend.

**Server I2C Address Map**

- **Address 0x48:** Allocated to the external ADS1115 force ADC. This high-precision chip converts analog pressure from the hand dynamometer into digital values for PsychoPy, bypassing the internal ESP32 ADC pins.

Functional Specification Note

Components and firmware parameters marked as unused indicate that their corresponding physical hardware or software functions are dormant within the current experimental configuration. While the source code retains the foundational infrastructure for motor automation, light barriers, and Hall effect data streams, the active paradigm relies exclusively on manual turntable rotation, Reed switch peg detection, LED feedback illumination, and digital hand dynamometer force tracking.

**NOTES:**

\*we are currently using psychopy and no force-dependent electromagnetic field

 Questions for Maik:

- About the raspberry and the new adaptions?

- About my local files