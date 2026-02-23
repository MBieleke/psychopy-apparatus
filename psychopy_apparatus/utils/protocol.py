"""
Protocol utilities for Apparatus communication.

Implements the binary message protocol with COBS encoding and XOR checksum
used to communicate with the ESP32 apparatus devices.

Message Format
--------------
Messages consist of a header + optional payload, COBS-encoded and delimited by 0x00.

Header (11 bytes, little-endian):
  - msg_type (u8): Message type identifier
  - seq (u32): Sequence number for matching ACK/NACK
  - payload_len (u16): Length of payload in bytes
  - src (u8): Source address (ADDR_PC, ADDR_SERVER, ADDR_CLIENT)
  - dst (u8): Destination address
  - flags (u8): Message flags (e.g., FLAG_ACK_REQUIRED)
  - checksum (u8): XOR checksum of header + payload

Message Types
-------------
Commands (PC -> Client):
  - 0x10 CMD_LED_SET_N: Set LED colors for N holes
  - 0x11 CMD_LED_SHOW: Show/update LED strip
  - 0x12 CMD_HOLE_START: Start hole measurement
  - 0x13 CMD_HOLE_STOP: Stop hole measurement
  - 0x14 CMD_REED_START: Start reed sensor streaming
  - 0x15 CMD_REED_STOP: Stop reed sensor streaming

Responses (Client -> PC):
  - 0x80 MSG_ACK: Command acknowledged
  - 0x81 MSG_NACK: Command rejected (with error code)
  - 0x91 DATA_REED: Reed sensor data stream
  - 0x92 DATA_HALL: Hall sensor measurement data

Routing Addresses
-----------------
  - ADDR_PC = 1: PC/PsychoPy
  - ADDR_SERVER = 2: Server ESP32
  - ADDR_CLIENT = 3: Client ESP32
"""

import struct
from typing import Optional, Tuple

# Routing addresses
ADDR_PC = 1
ADDR_SERVER = 2
ADDR_CLIENT = 3

# Message types - Commands (PC -> Client)
CMD_LED_SET_N = 0x10
CMD_LED_SHOW = 0x11
CMD_HOLE_START = 0x12
CMD_HOLE_STOP = 0x13
CMD_REED_START = 0x14
CMD_REED_STOP = 0x15

# Message types - Commands (PC -> Server)
CMD_FORCE_START = 0x03
CMD_FORCE_STOP = 0x04

# Message types - Responses
MSG_ACK = 0x80
MSG_NACK = 0x81
DATA_REED = 0x91
DATA_HALL = 0x92
DATA_FORCE = 0x90

# Flags
FLAG_ACK_REQUIRED = 0x01

# Error codes
ERR_BAD_LEN = 1
ERR_BAD_MSG = 2
ERR_BAD_PAYLOAD = 3

# Header format
HEADER_FORMAT = '<BIHBBBB'  # msg_type, seq, payload_len, src, dst, flags, checksum
HEADER_SIZE = 11


def cobs_encode(data: bytes) -> bytes:
    """
    COBS (Consistent Overhead Byte Stuffing) encode data and append 0x00 delimiter.
    
    COBS encoding removes all 0x00 bytes from the data, allowing 0x00 to be used
    as a reliable frame delimiter.
    
    Parameters
    ----------
    data : bytes
        Raw data to encode
        
    Returns
    -------
    bytes
        COBS-encoded data with trailing 0x00 delimiter
    """
    output = bytearray()
    code_index = 0
    code = 1
    output.append(0)  # placeholder for first code byte
    
    for byte in data:
        if byte == 0:
            output[code_index] = code
            code_index = len(output)
            output.append(0)
            code = 1
        else:
            output.append(byte)
            code += 1
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1
    
    output[code_index] = code
    output.append(0x00)  # delimiter
    return bytes(output)


def cobs_decode(data: bytes) -> bytes:
    """
    COBS decode data (without trailing 0x00 delimiter).
    
    Parameters
    ----------
    data : bytes
        COBS-encoded data (without the trailing 0x00)
        
    Returns
    -------
    bytes
        Decoded data
    """
    if not data:
        return b''
    
    output = bytearray()
    i = 0
    
    while i < len(data):
        code = data[i]
        if code == 0:
            return bytes(output)
        
        i += 1
        for _ in range(code - 1):
            if i >= len(data):
                return bytes(output)
            output.append(data[i])
            i += 1
        
        if code < 0xFF and i < len(data):
            output.append(0)
    
    return bytes(output)


def calculate_checksum(header_bytes: bytes, payload: bytes) -> int:
    """
    Calculate XOR checksum of header (without checksum byte) and payload.
    
    Parameters
    ----------
    header_bytes : bytes
        Header bytes (without checksum)
    payload : bytes
        Payload bytes
        
    Returns
    -------
    int
        XOR checksum (0-255)
    """
    checksum = 0
    for byte in header_bytes:
        checksum ^= byte
    for byte in payload:
        checksum ^= byte
    return checksum


def build_message(msg_type: int, seq: int, payload: bytes = b'', 
                  dst: int = ADDR_CLIENT, flags: int = FLAG_ACK_REQUIRED) -> bytes:
    """
    Build a binary message with header + payload, including XOR checksum.
    
    Parameters
    ----------
    msg_type : int
        Message type identifier
    seq : int
        Sequence number (32-bit unsigned)
    payload : bytes, optional
        Message payload
    dst : int, optional
        Destination address (default: ADDR_CLIENT)
    flags : int, optional
        Message flags (default: FLAG_ACK_REQUIRED)
        
    Returns
    -------
    bytes
        Complete message (header + payload) ready for COBS encoding
    """
    # Build header without checksum
    header_temp = struct.pack('<BIHBBB', 
                              msg_type,
                              seq,
                              len(payload),
                              ADDR_PC,
                              dst,
                              flags)
    
    # Calculate checksum
    checksum = calculate_checksum(header_temp, payload)
    
    # Build final message with checksum
    header = header_temp + struct.pack('<B', checksum)
    return header + payload


def parse_message(data: bytes) -> Optional[Tuple[dict, bytes]]:
    """
    Parse a received message (after COBS decoding).
    
    Parameters
    ----------
    data : bytes
        Decoded message data
        
    Returns
    -------
    tuple or None
        Tuple of (header_dict, payload) if valid, None if invalid
        header_dict contains: msg_type, seq, payload_len, src, dst, flags, checksum
    """
    if len(data) < HEADER_SIZE:
        return None
    
    # Parse header
    msg_type, seq, payload_len, src, dst, flags, checksum = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )
    
    # Extract payload
    payload = data[HEADER_SIZE:HEADER_SIZE + payload_len]
    
    # Verify checksum
    header_temp = data[:HEADER_SIZE - 1]  # Header without checksum byte
    expected_checksum = calculate_checksum(header_temp, payload)
    
    if checksum != expected_checksum:
        return None
    
    header = {
        'msg_type': msg_type,
        'seq': seq,
        'payload_len': payload_len,
        'src': src,
        'dst': dst,
        'flags': flags,
        'checksum': checksum
    }
    
    return header, payload


def encode_led_payload_format_a(holes: list[int], r: int, g: int, b: int) -> bytes:
    """
    Encode LED payload in Format A (shared color for all holes).
    
    Format A: count(u8) + holes[count] + r(u8) + g(u8) + b(u8)
    
    Parameters
    ----------
    holes : list[int]
        List of hole numbers
    r, g, b : int
        RGB color values (0-255)
        
    Returns
    -------
    bytes
        Encoded payload
    """
    count = len(holes)
    payload = bytes([count]) + bytes(holes) + bytes([r, g, b])
    return payload


def encode_led_payload_format_b(holes: list[int], colors: list[tuple[int, int, int]]) -> bytes:
    """
    Encode LED payload in Format B (individual colors per hole).
    
    Format B: count(u8) + [hole(u8), r(u8), g(u8), b(u8)] × count
    
    Parameters
    ----------
    holes : list[int]
        List of hole numbers
    colors : list[tuple[int, int, int]]
        List of (r, g, b) tuples, one per hole
        
    Returns
    -------
    bytes
        Encoded payload
    """
    if len(holes) != len(colors):
        raise ValueError("holes and colors must have the same length")
    
    count = len(holes)
    payload = bytes([count])
    for hole, (r, g, b) in zip(holes, colors):
        payload += bytes([hole, r, g, b])
    return payload


def encode_led_payload_auto(holes: list[int], colors) -> bytes:
    """
    Automatically choose Format A or B based on whether all colors are the same.
    
    Parameters
    ----------
    holes : list[int]
        List of hole numbers
    colors : tuple or list
        Either a single (r, g, b) tuple OR list of (r, g, b) tuples
        
    Returns
    -------
    bytes
        Encoded payload using the most efficient format
    """
    if not holes:
        raise ValueError("holes list cannot be empty")
    
    # Check if colors is a single tuple or list of tuples
    if isinstance(colors, (tuple, list)) and len(colors) == 3 and isinstance(colors[0], int):
        # Single (r, g, b) tuple → Format A
        return encode_led_payload_format_a(holes, colors[0], colors[1], colors[2])
    
    # List of tuples - check if all are the same
    if all(c == colors[0] for c in colors):
        # All colors identical → Format A
        r, g, b = colors[0]
        return encode_led_payload_format_a(holes, r, g, b)
    else:
        # Different colors → Format B
        return encode_led_payload_format_b(holes, colors)


def encode_force_start_payload(rate_hz: float, device: str) -> bytes:
    """
    Encode payload for CMD_FORCE_START command.
    
    Converts Hz sampling rate to microsecond period and maps device to device selector.
    
    Payload format: period_us(u32) + device(u8)
    
    Parameters
    ----------
    rate_hz : float
        Sampling rate in Hz (e.g., 100 for 100 Hz)
    device : str
        Dynamometer selector:
        - 'white': Right/white dynamometer
        - 'blue': Left/blue dynamometer  
        - 'both': Both dynamometers
        
    Returns
    -------
    bytes
        Encoded payload (5 bytes)
    """
    # Convert Hz to microseconds
    period_us = int(1_000_000 / rate_hz)
    
    # Map device name to device selector
    device_map = {
        'white': 0,
        'blue': 1,
        'both': 2
    }
    
    device_lower = device.lower()
    if device_lower not in device_map:
        raise ValueError(f"Invalid device '{device}'. Must be 'white', 'blue', or 'both'")
    
    device_selector = device_map[device_lower]
    
    # Pack as little-endian u32 + u8
    return struct.pack('<IB', period_us, device_selector)


def parse_force_data_payload(payload: bytes) -> dict:
    """
    Parse DATA_FORCE payload.
    
    Payload format: time_us(u32) + value(i16) + device(u8)
    
    Parameters
    ----------
    payload : bytes
        Raw payload bytes (7 bytes)
        
    Returns
    -------
    dict
        Dictionary with keys: 'time_us', 'value', 'device'
        - time_us: Timestamp in microseconds
        - value: Force value in Newtons (int16)
        - device: Device identifier (0=right/white, 1=left/blue)
    """
    if len(payload) != 7:
        raise ValueError(f"Invalid force data payload length: {len(payload)} (expected 7)")
    
    time_us, value, device = struct.unpack('<IhB', payload)
    
    return {
        'time_us': time_us,
        'value': value,
        'device': device
    }
