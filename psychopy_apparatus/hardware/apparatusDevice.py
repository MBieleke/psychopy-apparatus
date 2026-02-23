import time
import struct
from serial import Serial
from serial.threaded import ReaderThread, Protocol
from psychopy import logging, core
from psychopy.hardware.base import BaseResponseDevice, BaseResponse

from psychopy_apparatus.utils.protocol import (
    cobs_encode, cobs_decode, build_message, parse_message,
    encode_led_payload_auto, encode_led_payload_format_a, encode_led_payload_format_b,
    encode_force_start_payload, parse_force_data_payload,
    CMD_LED_SET_N, CMD_LED_SHOW, CMD_HOLE_START, CMD_HOLE_STOP, CMD_REED_START, CMD_REED_STOP,
    CMD_FORCE_START, CMD_FORCE_STOP,
    MSG_ACK, MSG_NACK, DATA_REED, DATA_HALL, DATA_FORCE,
    ADDR_PC, ADDR_CLIENT, ADDR_SERVER,
    ERR_BAD_LEN, ERR_BAD_MSG, ERR_BAD_PAYLOAD
)


class ApparatusResponse(BaseResponse):
    """ 
    Apparatus hardware response object to interface with a apparatus response device.

    Parameters
    ----------
    t : float
        Time at which the response happened
    value : bytes
        Raw response frame from apparatus device
    msg_type : int
        Message type (MSG_ACK, MSG_NACK, DATA_REED, DATA_HALL)
    seq : int
        Sequence number matching the command
    payload : bytes
        Response payload
    """
    fields = ['t', 'value', 'msg_type', 'seq', 'payload']

    # Extended fields for sensor data (populated if applicable, kept dormant for LED-only phase)
    extended_fields = ['pluggedIn', 'reactionTime', 'holes', 'whiteForce', 'blueForce']

    def __init__(self, t, value, msg_type, seq, payload, device=None):
        super().__init__(t=t, value=value, device=device)
        
        self.msg_type = msg_type
        self.seq = seq
        self.payload = payload
        
        # Initialize extended fields as None (dormant for now)
        self.pluggedIn = None
        self.reactionTime = None
        self.holes = None
        self.whiteForce = None
        self.blueForce = None
        
        # Parse force data if this is a DATA_FORCE message
        if msg_type == DATA_FORCE and len(payload) == 7:
            try:
                force_data = parse_force_data_payload(payload)
                # Map device ID to force field
                if force_data['device'] == 0:
                    self.whiteForce = force_data['value']
                elif force_data['device'] == 1:
                    self.blueForce = force_data['value']
            except Exception as e:
                logging.warning(f"Failed to parse force data: {e}")
        
    def is_ack(self) -> bool:
        """Check if this is an ACK response."""
        return self.msg_type == MSG_ACK
    
    def is_nack(self) -> bool:
        """Check if this is a NACK response."""
        return self.msg_type == MSG_NACK
    
    def get_error_code(self) -> int:
        """Get error code from NACK response (0 if not NACK)."""
        if self.is_nack() and len(self.payload) > 0:
            return self.payload[0]
        return 0


class ApparatusProtocol(Protocol):
    """
    Serial protocol handler for COBS-framed binary messages.
    
    Reads COBS-encoded frames delimited by 0x00, decodes them, validates checksums,
    and converts them into ApparatusResponse objects.
    """
    DELIMITER = 0x00

    def __init__(self):
        super().__init__()
        self._buffer = bytearray()
        self._responses = []
        self._clock = core.Clock()

    def data_received(self, data: bytes):
        """Process incoming serial data byte by byte, looking for 0x00 delimiters."""
        for byte in data:
            if byte == self.DELIMITER:
                if len(self._buffer) > 0:
                    # Frame complete, try to decode and parse
                    self._process_frame(bytes(self._buffer))
                    self._buffer.clear()
            else:
                self._buffer.append(byte)

    def _process_frame(self, frame: bytes):
        """Decode COBS frame and parse message."""
        try:
            # COBS decode
            decoded = cobs_decode(frame)
            
            if len(decoded) < 11:  # Minimum header size
                logging.warning(f"Apparatus: Frame too short ({len(decoded)} bytes)")
                return
            
            # Parse message header and payload
            result = parse_message(decoded)
            if result is None:
                logging.warning("Apparatus: Invalid message (checksum failed)")
                return
            
            header, payload = result
            
            # Create response object
            response = ApparatusResponse(
                t=self._clock.getTime(),
                value=decoded,
                msg_type=header['msg_type'],
                seq=header['seq'],
                payload=payload
            )
            
            self._responses.append(response)
            
        except Exception as e:
            logging.warning(f"Apparatus: Frame processing error: {e}")

    def get_responses(self):
        """Get all responses received so far."""
        return self._responses.copy()
    
    def get_latest_response(self):
        """Get the most recent response or None."""
        if self._responses:
            return self._responses[-1]
        else:
            return None
    
    def get_number_of_responses(self):
        """Get the number of responses received."""
        return len(self._responses)

    def clear_responses(self):
        """Clear all stored responses."""
        self._responses.clear()

    def reset_clock(self):
        """Reset the internal timestamp clock."""
        self._clock.reset()


class ApparatusDevice(BaseResponseDevice, aliases=["apparatus"]):
    """
    Apparatus hardware object to interface with a apparatus response device.
    
    Communicates with ESP32-based apparatus using binary protocol with COBS framing.

    Attributes
    ----------
    listeners : list[psychopy.hardware.listeners.BaseListener]
        List of listeners to send responses to
    responses : list[ApparatusResponse]
        List of responses received by this device object
    muteOutsidePsychopy : bool
        If True, then mute any responses gathered when the PsychoPy window is not in focus
    """
    responseClass = ApparatusResponse

    def __init__(self, port, baudrate=115200, simulate=False, debug=False, ack_timeout=2.0, **kwargs):
        """
        Initialize the ApparatusDevice.

        Parameters
        ----------
        port : str
            Serial port to which the apparatus is connected (e.g., 'COM6' on Windows).
        baudrate : int
            Serial communication baud rate (default: 115200).
        simulate : bool
            If True, simulate the device without actual hardware connection.
        debug : bool
            If True, enable debug logging.
        ack_timeout : float
            Timeout in seconds for waiting for ACK/NACK responses (default: 2.0).
        """
        super().__init__(**kwargs)
        self._port = port
        self._baudrate = baudrate
        self._simulate = simulate
        self._debug = debug
        self._ack_timeout = ack_timeout

        self._reader_thread = None
        self._protocol = None
        self._seq_counter = 1
        
        # Rate limiting for commands
        self._last_send_time = time.monotonic()
        self._rate_limit_interval = 0.05

        if not self._simulate:
            self._com = Serial(port, baudrate=baudrate, timeout=None)

            if not self._com.is_open:
                raise RuntimeError(
                    f"Could not open serial port {port} for Apparatus device! "
                    "Try restarting and reconnecting the device."
                )

            # Start threaded reader with protocol handler
            thread = ReaderThread(self._com, ApparatusProtocol)
            thread.start()
            self._reader_thread, self._protocol = thread.connect()
            
            if self._debug:
                logging.info(f"Apparatus device initialized on {port} at {baudrate} baud")

    def __del__(self):
        """Clean up serial connection on deletion."""
        if not self._simulate and self._reader_thread:
            self._reader_thread.close()

    @property
    def rateLimitInterval(self) -> float:
        """Get the rate limit interval (in seconds) for sending commands."""
        return self._rate_limit_interval
    
    @rateLimitInterval.setter
    def rateLimitInterval(self, value: float):
        """Set the rate limit interval (in seconds) for sending commands."""
        self._rate_limit_interval = value

    def _get_next_seq(self) -> int:
        """Get the next sequence number for a command."""
        seq = self._seq_counter
        self._seq_counter += 1
        if self._seq_counter > 0xFFFFFFFF:  # 32-bit wrap around
            self._seq_counter = 1
        return seq

    def _send_message(self, msg_type: int, payload: bytes = b'', dst: int = ADDR_CLIENT, expect_ack: bool = True) -> int:
        """
        Send a message to the apparatus device.
        
        Parameters
        ----------
        msg_type : int
            Message type identifier
        payload : bytes
            Message payload
        dst : int
            Destination address (ADDR_CLIENT or ADDR_SERVER)
        expect_ack : bool
            Whether to expect an ACK response
            
        Returns
        -------
        int
            Sequence number of the sent message
        """
        seq = self._get_next_seq()
        
        # Build and encode message
        raw_msg = build_message(msg_type, seq, payload, dst=dst)
        encoded = cobs_encode(raw_msg)
        
        if not self._simulate:
            self._reader_thread.write(encoded)
        
        if self._debug:
            msg_names = {
                CMD_LED_SET_N: 'CMD_LED_SET_N',
                CMD_LED_SHOW: 'CMD_LED_SHOW',
                CMD_HOLE_START: 'CMD_HOLE_START',
                CMD_HOLE_STOP: 'CMD_HOLE_STOP',
                CMD_REED_START: 'CMD_REED_START',
                CMD_REED_STOP: 'CMD_REED_STOP',
                CMD_FORCE_START: 'CMD_FORCE_START',
                CMD_FORCE_STOP: 'CMD_FORCE_STOP',
            }
            msg_name = msg_names.get(msg_type, f'0x{msg_type:02X}')
            payload_hex = payload.hex() if payload else '(empty)'
            dst_name = 'CLIENT' if dst == ADDR_CLIENT else 'SERVER'
            logging.info(f"Apparatus TX: seq={seq}, type={msg_name}, dst={dst_name}, payload={payload_hex[:60]}")
        
        return seq

    def _wait_for_ack(self, expected_seq: int, timeout: float = None) -> bool:
        """
        Wait for ACK or NACK response matching the expected sequence number.
        
        Parameters
        ----------
        expected_seq : int
            Expected sequence number
        timeout : float, optional
            Timeout in seconds (uses self._ack_timeout if None)
            
        Returns
        -------
        bool
            True if ACK received, False if NACK or timeout
        """
        if self._simulate:
            return True
        
        if timeout is None:
            timeout = self._ack_timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            responses = self._protocol.get_responses()
            
            # Look for response with matching sequence number
            for response in responses:
                if response.seq == expected_seq and response.msg_type in (MSG_ACK, MSG_NACK):
                    # Remove this response from the queue
                    self._protocol._responses.remove(response)
                    
                    if response.is_ack():
                        if self._debug:
                            logging.info(f"Apparatus RX: ACK for seq={expected_seq}")
                        return True
                    else:
                        error_code = response.get_error_code()
                        error_names = {
                            ERR_BAD_LEN: 'BAD_LEN',
                            ERR_BAD_MSG: 'BAD_MSG',
                            ERR_BAD_PAYLOAD: 'BAD_PAYLOAD'
                        }
                        error_name = error_names.get(error_code, f'UNKNOWN({error_code})')
                        logging.warning(f"Apparatus RX: NACK for seq={expected_seq}, error={error_name}")
                        return False
            
            time.sleep(0.001)  # Small sleep to avoid busy-waiting
        
        logging.warning(f"Apparatus: Timeout waiting for ACK/NACK (seq={expected_seq})")
        return False

    # ===== LED Control Methods =====

    def setLedColors(self, holes: list[int], colors, show: bool = True, wait_ack: bool = True) -> bool:
        """
        Set LED colors for specified holes.
        
        Automatically chooses the most efficient payload format:
        - Format A if all holes have the same color (more efficient)
        - Format B if holes have different colors
        
        Parameters
        ----------
        holes : list[int]
            List of hole numbers (0-20)
        colors : tuple or list
            Either a single (r, g, b) tuple OR list of (r, g, b) tuples (one per hole)
        show : bool
            If True, automatically send LED_SHOW command after setting colors
        wait_ack : bool
            If True, wait for ACK before returning
            
        Returns
        -------
        bool
            True if successful (or if wait_ack=False), False if NACK or timeout
        """
        if not holes:
            return True
        
        # Build payload
        payload = encode_led_payload_auto(holes, colors)
        
        # Send command
        seq = self._send_message(CMD_LED_SET_N, payload)
        
        # Wait for ACK if requested
        if wait_ack:
            success = self._wait_for_ack(seq)
            if not success:
                return False
        
        # Send show command if requested
        if show:
            time.sleep(0.01)  # Small delay between commands
            return self.showLeds(wait_ack=wait_ack)
        
        return True

    def showLeds(self, wait_ack: bool = True) -> bool:
        """
        Update LED strip to display the colors set by setLedColors.
        
        Parameters
        ----------
        wait_ack : bool
            If True, wait for ACK before returning
            
        Returns
        -------
        bool
            True if successful (or if wait_ack=False), False if NACK or timeout
        """
        seq = self._send_message(CMD_LED_SHOW, b'')
        
        if wait_ack:
            return self._wait_for_ack(seq)
        
        return True

    def clearLeds(self, wait_ack: bool = True) -> bool:
        """
        Turn off all LEDs (convenience method).
        
        Parameters
        ----------
        wait_ack : bool
            If True, wait for ACK before returning
            
        Returns
        -------
        bool
            True if successful
        """
        # Set all 21 holes to black (0, 0, 0)
        holes = list(range(21))
        return self.setLedColors(holes, (0, 0, 0), show=True, wait_ack=wait_ack)

    # ===== Force Measurement Methods =====

    def startForceMeasurement(self, rate_hz: float, device: str, wait_ack: bool = True) -> bool:
        """
        Start streaming force measurements from handgrip dynamometer(s).
        
        The server will continuously measure and transmit force data at the specified rate
        until stopForceMeasurement() is called.
        
        Parameters
        ----------
        rate_hz : float
            Sampling rate in Hz (e.g., 100 for 100 Hz)
        device : str
            Dynamometer selector:
            - 'white': Right/white dynamometer only
            - 'blue': Left/blue dynamometer only
            - 'both': Both dynamometers
        wait_ack : bool
            If True, wait for ACK before returning
            
        Returns
        -------
        bool
            True if successful (or if wait_ack=False), False if NACK or timeout
        """
        payload = encode_force_start_payload(rate_hz, device)
        seq = self._send_message(CMD_FORCE_START, payload, dst=ADDR_SERVER)
        
        if wait_ack:
            return self._wait_for_ack(seq)
        
        return True

    def stopForceMeasurement(self, wait_ack: bool = True) -> bool:
        """
        Stop streaming force measurements.
        
        The server will stop measuring and send a final ACK.
        
        Parameters
        ----------
        wait_ack : bool
            If True, wait for ACK before returning
            
        Returns
        -------
        bool
            True if successful (or if wait_ack=False), False if NACK or timeout
        """
        seq = self._send_message(CMD_FORCE_STOP, b'', dst=ADDR_SERVER)
        
        if wait_ack:
            return self._wait_for_ack(seq)
        
        return True

    # ===== Response Management =====

    def getResponses(self) -> list[ApparatusResponse]:
        """
        Get the list of responses received by the device.

        Returns
        -------
        list[ApparatusResponse]
            List of responses received.
        """
        if self._simulate:
            return []
        else:
            return self._protocol.get_responses()
        
    def getLatestResponse(self) -> ApparatusResponse:
        """
        Get the latest response received by the device or None if there are no responses.

        Returns
        -------
        ApparatusResponse
            The latest response received.
        """
        return self._protocol.get_latest_response()

    def getNumberOfResponses(self) -> int:
        """
        Get the number of responses received by the device.

        Returns
        -------
        int
            Number of responses received.
        """
        if self._simulate:
            return 0
        else:
            return self._protocol.get_number_of_responses()
        
    def clearResponses(self):
        """
        Clear the list of responses received by the device.
        """
        if not self._simulate:
            self._protocol.clear_responses()

    def resetClock(self):
        """
        Reset the internal clock of the device.
        """
        if not self._simulate:
            self._protocol.reset_clock()

    def isSameDevice(self, other) -> bool:
        """
        Determine whether this object represents the same physical device as a given other object.

        Parameters
        ----------
        other : ApparatusDevice, dict
            Other device object to compare against, or a dict of params (which must include `port` as key).

        Returns
        -------
        bool
            True if the two objects represent the same physical device
        """
        if isinstance(other, ApparatusDevice):
            return self._port == other._port
        elif isinstance(other, dict):
            return self._port == other.get('port')
        return False
    
    @staticmethod
    def getAvailableDevices():
        return [{
            'deviceName': "Apparatus",
            'deviceClass': "psychopy.hardware.ApparatusDevice",
        }]