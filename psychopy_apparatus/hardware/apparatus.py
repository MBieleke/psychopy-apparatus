from psychopy.tools.attributetools import AttributeGetSetMixin
from psychopy import logging, core
from psychopy.constants import NOT_STARTED, STARTED, FINISHED
from psychopy.hardware import DeviceManager
from psychopy.colors import Color
import time

from psychopy_apparatus.hardware.apparatusDevice import ApparatusResponse
from psychopy_apparatus.utils.protocol import DATA_FORCE, DATA_REED


def _parse_holes(holes_spec):
    """
    Convert hole specification to list of hole indices (internal helper).
    
    Automatically handles keywords and explicit values transparently.
    
    Parameters
    ----------
    holes_spec : str, int, or list
        Hole specification:
        - Keyword string: 'all' (0-20), 'inner' (0-7), 'outer' (8-20), 'none'
        - Single integer: 0, 5, etc.
        - List of integers: [0, 1, 2]
        
    Returns
    -------
    list[int]
        List of hole indices
    """
    # Check for common mistake: passing Python's built-in all() function
    if callable(holes_spec):
        raise TypeError(
            "holes_spec appears to be a function (did you forget quotes?). "
            "Use 'all' (string) instead of all (built-in function). "
            "Valid values: 'all', 'inner', 'outer', 'none', integer, or list."
        )
    
    if isinstance(holes_spec, str):
        if holes_spec == 'all':
            return list(range(21))  # Holes 0-20
        elif holes_spec == 'none':
            return []
        elif holes_spec == 'inner':
            return list(range(8))  # Holes 0-7
        elif holes_spec == 'outer':
            return list(range(8, 21))  # Holes 8-20
        else:
            raise ValueError(f"Unknown hole keyword: '{holes_spec}'. Use 'all', 'inner', 'outer', 'none', or explicit hole number(s).")
    elif isinstance(holes_spec, int):
        return [holes_spec]
    else:
        # Assume it's an iterable (list, tuple, etc.)
        try:
            return list(holes_spec)
        except TypeError:
            raise TypeError(
                f"Invalid holes_spec type: {type(holes_spec).__name__}. "
                "Expected: 'all'/'inner'/'outer'/'none' (string), integer, or list of integers."
            )


class Apparatus(AttributeGetSetMixin):
    """
    A class representing a Apparatus device.
    """

    def __init__(self, deviceName=None):
        if deviceName == "" or deviceName is None:
            # Try to get the first available apparatus device
            candidates = DeviceManager.getInitialisedDeviceNames('psychopy.hardware.ApparatusDevice')
            if candidates:
                deviceName = candidates[0]
                logging.info(f"No device name provided. Using the first available Apparatus device: '{deviceName}'")
            else:
                raise ValueError("No Apparatus device name provided and no initialized Apparatus devices found in DeviceManager.")
        elif deviceName not in DeviceManager.devices:
            raise ValueError(f"Device '{deviceName}' not found in DeviceManager. Make sure to create it first and assign it in the component.")
        
        self._device = DeviceManager.getDevice(deviceName)
        self.status = NOT_STARTED

        self.times = []
        self.responses = []
        
        # Human-readable force data (for data output)
        self.whiteForceValues = []  # List of white force samples
        self.blueForceValues = []   # List of blue force samples
        self.whiteForceTimestamps = []  # Timestamps for white force samples
        self.blueForceTimestamps = []   # Timestamps for blue force samples

        self.whiteForce = 0
        self.blueForce = 0
        self.maxWhiteForce = 0
        self.maxBlueForce = 0
        
        # Force measurement state
        self._force_measuring = False
        self._force_start_response_count = 0
        
        # Reed sensor data (for data output)
        self.reedTimes = []  # List of event timestamps
        self.reedHoles = []  # List of hole numbers (parallel to reedTimes)
        self.reedActions = []  # List of actions: 1=insert, 0=remove (parallel to reedTimes)
        self.reedSummary = []  # Per-hole summary: [{'hole': h, 'insertions': n, 'removals': m, 'duration': s}, ...]
        
        # Reed measurement state (internal tracking)
        self._reed_measuring = False
        self._reed_monitored_holes = []  # Which holes to monitor
        self._reed_start_response_count = 0
        self._reed_last_states = {}  # Last known state per hole (0 or 1)
        self._reed_last_timestamp = None  # Timestamp of last state change
        self._reed_insertion_counts = {}  # Count of insertions per hole
        self._reed_removal_counts = {}  # Count of removals per hole
        self._reed_active_durations = {}  # Total active time per hole
        self._reed_last_insert_time = {}  # When each hole was last inserted (for duration calc)  # Last update timestamp

    def setHoleLights(self, holes, color: Color, rate_limited: bool = False) -> bool:
        """
        Set the color of specific holes on the apparatus.
        
        Parameters
        ----------
        holes : str, int, or list[int]
            Holes to control:
            - Keyword: 'all' (0-20), 'inner' (0-7), 'outer' (8-20), 'none'
            - Single hole: 0, 5
            - Multiple holes: [0, 1, 2]
        color : Color
            RGB color value as a Color object.
        rate_limited : bool
            If True, skip command if sent too soon after previous command.
            
        Returns
        -------
        bool
            True if successful, False if skipped due to rate limiting or error.
        """
        # Parse holes intelligently
        holes_list = _parse_holes(holes)
        
        if not holes_list:
            return True  # No holes to update
        
        if rate_limited:
            # Check rate limiting
            if time.monotonic() - self._device._last_send_time < self._device._rate_limit_interval:
                return False
        
        # Convert color to RGB255
        color255 = tuple(int(c.item()) for c in color.rgb255)
        
        # Send LED command with auto show
        return self._device.setLedColors(holes_list, color255, show=True, wait_ack=True)
    
    def setColors(self, colors: dict[int, Color], rate_limited: bool = False) -> bool:
        """
        Set the color of multiple holes on the apparatus (each with a different color).
        
        Parameters
        ----------
        colors : dict
            Dictionary mapping hole spec to Color object. Hole specs can be:
            - Keywords: 'all', 'inner', 'outer', 'none'
            - Single hole: 0, 5
            - Multiple holes: (0, 1, 2) as tuple/list key
            Or simply: {0: Color(...), 1: Color(...), ...}
        rate_limited : bool
            If True, skip command if sent too soon after previous command.
            
        Returns
        -------
        bool
            True if successful, False if skipped due to rate limiting or error.
        """
        if rate_limited:
            # Check rate limiting
            if time.monotonic() - self._device._last_send_time < self._device._rate_limit_interval:
                return False
        
        if not colors:
            return True
        
        # Convert to lists of holes and colors
        holes = list(colors.keys())
        color_tuples = [tuple(int(c.item()) for c in color.rgb255) for color in colors.values()]
        
        # Send LED command with auto show
        return self._device.setLedColors(holes, color_tuples, show=True, wait_ack=True)

    def turnOffHoleLights(self, holes, rate_limited: bool = False) -> bool:
        """
        Turn off the lights for specific holes on the apparatus.
        
        Parameters
        ----------
        holes : str, int, or list[int]
            Holes to turn off:
            - Keyword: 'all' (0-20), 'inner' (0-7), 'outer' (8-20), 'none'
            - Single hole: 0, 5
            - Multiple holes: [0, 1, 2]
        rate_limited : bool
            If True, skip command if sent too soon after previous command.
            
        Returns
        -------
        bool
            True if successful, False if skipped due to rate limiting or error.
        """
        return self.setHoleLights(holes, Color([0, 0, 0], 'rgb255'), rate_limited=rate_limited)

    def turnOffAllLights(self, rate_limited: bool = False) -> bool:
        """
        Turn off all lights on the apparatus.
        
        Parameters
        ----------
        rate_limited : bool
            If True, skip command if sent too soon after previous command.
            
        Returns
        -------
        bool
            True if successful, False if skipped due to rate limiting or error.
        """
        if rate_limited:
            # Check rate limiting
            if time.monotonic() - self._device._last_send_time < self._device._rate_limit_interval:
                return False
        
        return self._device.clearLeds(wait_ack=True)

    # ===== DORMANT: Motor control (not yet ported to new protocol) =====
    
    def moveMotor(self, speed):
        """
        Move the apparatus plate at a specified speed.
        
        NOTE: This method is dormant and not yet ported to the new protocol.

        Parameters
        ----------
        speed : int
            Speed value for the motor.
        """
        raise NotImplementedError("Motor control not yet ported to new protocol")

    def stopMotor(self):
        """
        Stop the apparatus plate motor.
        
        NOTE: This method is dormant and not yet ported to the new protocol.
        """
        raise NotImplementedError("Motor control not yet ported to new protocol")

    def home(self):
        """
        Move the apparatus plate to the home position.
        
        NOTE: This method is dormant and not yet ported to the new protocol.
        """
        raise NotImplementedError("Motor control not yet ported to new protocol")

    def configureHandDynamometer(self, mode, hysteresisTime, blueLowerHysteresis, blueUpperHysteresis, whiteLowerHysteresis, whiteUpperHysteresis):
        """
        Configure the hand dynamometer settings.
        
        NOTE: This method is dormant and not yet ported to the new protocol.

        Parameters
        ----------
        mode : str
            The mode of the hand dynamometer. Options are "disabled", "transmit", "magnets", "transmit+magnets".
        hysteresisTime : float
            Hysteresis time in seconds after which to release the magnets.
        blueLowerHysteresis : list[int]
            Lower hysteresis value for the blue meter.
        blueUpperHysteresis : list[int]
            Upper hysteresis value for the blue meter.
        whiteLowerHysteresis : list[int]
            Lower hysteresis value for the white meter.
        whiteUpperHysteresis : list[int]
            Upper hysteresis value for the white meter.
        """
        raise NotImplementedError("Hand dynamometer configuration not yet ported to new protocol")

    def startForceMeasurement(self, rate: float, device: str) -> bool:
        """
        Start force measurement on the apparatus device.
        
        Begins streaming force data from the specified dynamometer(s) at the given rate.
        Force data will be collected in .times and .responses lists, and current/max force
        values will be updated in real-time.

        Parameters
        ----------
        rate : float
            Sampling rate in Hz (e.g., 100 for 100 Hz sampling).
        device : str
            Dynamometer selector:
            - 'white': Right/white dynamometer only
            - 'blue': Left/blue dynamometer only
            - 'both': Both dynamometers
            
        Returns
        -------
        bool
            True if measurement started successfully, False otherwise.
        """
        # Clear previous data
        self.times.clear()
        self.responses.clear()
        self.whiteForceValues.clear()
        self.blueForceValues.clear()
        self.whiteForceTimestamps.clear()
        self.blueForceTimestamps.clear()
        self.whiteForce = 0
        self.blueForce = 0
        self.maxWhiteForce = 0
        self.maxBlueForce = 0
        
        # Clear device responses to start fresh
        self._device.clearResponses()
        self._force_start_response_count = self._device.getNumberOfResponses()
        
        # Start measurement on device
        success = self._device.startForceMeasurement(rate, device, wait_ack=True)
        
        if success:
            self._force_measuring = True
            self.status = STARTED
            logging.info(f"Force measurement started: {rate} Hz, device '{device}'")
        else:
            logging.error("Failed to start force measurement")
            
        return success

    def stopForceMeasurement(self) -> bool:
        """
        Stop force measurement on the apparatus device.
        
        Stops the streaming of force data and finalizes the measurement session.
        
        Returns
        -------
        bool
            True if measurement stopped successfully, False otherwise.
        """
        if not self._force_measuring:
            logging.warning("Force measurement was not running")
            return True
        
        # Collect any remaining responses before stopping
        self._collectForceResponses()
        
        # Stop measurement on device
        success = self._device.stopForceMeasurement(wait_ack=True)
        
        if success:
            self._force_measuring = False
            self.status = FINISHED
            logging.info(f"Force measurement stopped. Collected {len(self.responses)} samples.")
        else:
            logging.error("Failed to stop force measurement")
            
        return success

    def _collectForceResponses(self):
        """
        Collect force measurement responses from the device.
        
        This method should be called regularly (e.g., each frame) during measurement
        to retrieve new force data and update current/max force values.
        """
        if not self._force_measuring:
            return
        
        # Get all responses from device
        all_responses = self._device.getResponses()
        
        # Process only new responses (those received after measurement started)
        new_responses = all_responses[self._force_start_response_count:]
        
        for response in new_responses:
            # Only process force data responses
            if response.msg_type == DATA_FORCE:
                # Store response and timestamp
                self.times.append(response.t)
                self.responses.append(response)
                
                # Extract and store force values
                if response.whiteForce is not None:
                    self.whiteForce = response.whiteForce
                    self.whiteForceValues.append(response.whiteForce)
                    self.whiteForceTimestamps.append(response.t)
                    if response.whiteForce > self.maxWhiteForce:
                        self.maxWhiteForce = response.whiteForce
                        
                if response.blueForce is not None:
                    self.blueForce = response.blueForce
                    self.blueForceValues.append(response.blueForce)
                    self.blueForceTimestamps.append(response.t)
                    if response.blueForce > self.maxBlueForce:
                        self.maxBlueForce = response.blueForce
        
        # Update the response counter
        self._force_start_response_count = len(all_responses)

    def updateForceMeasurement(self):
        """
        Update force measurement data.
        
        Call this method regularly (e.g., each frame) during active measurement
        to collect new force data from the device.
        """
        self._collectForceResponses()

    def startReedMeasurement(self, rate: float, holes) -> bool:
        """
        Start reed sensor measurement on the apparatus device.
        
        Begins streaming reed sensor data from the client at the given rate.
        Reed data will be collected only for specified holes, and active durations
        will be tracked automatically.

        Parameters
        ----------
        rate : float
            Sampling rate in Hz (e.g., 100 for 100 Hz sampling).
        holes : str, int, or list[int]
            Holes to monitor:
            - Keyword: 'all' (0-20), 'inner' (0-7), 'outer' (8-20), 'none'
            - Single hole: 0, 5
            - Multiple holes: [0, 1, 2]
            
        Returns
        -------
        bool
            True if measurement started successfully, False otherwise.
        """
        # Parse holes specification
        self._reed_monitored_holes = _parse_holes(holes)
        
        # Clear previous data
        self.reedTimes.clear()
        self.reedHoles.clear()
        self.reedActions.clear()
        self.reedSummary.clear()
        
        # Initialize tracking for each monitored hole
        self._reed_last_states = {hole: 0 for hole in self._reed_monitored_holes}
        self._reed_insertion_counts = {hole: 0 for hole in self._reed_monitored_holes}
        self._reed_removal_counts = {hole: 0 for hole in self._reed_monitored_holes}
        self._reed_active_durations = {hole: 0.0 for hole in self._reed_monitored_holes}
        self._reed_last_insert_time = {hole: None for hole in self._reed_monitored_holes}
        self._reed_last_timestamp = None
        
        # Clear device responses to start fresh
        self._device.clearResponses()
        self._reed_start_response_count = self._device.getNumberOfResponses()
        
        # Start measurement on device
        success = self._device.startReedMeasurement(rate, wait_ack=True)
        
        if success:
            self._reed_measuring = True
            self.status = STARTED
            logging.info(f"Reed measurement started: {rate} Hz, monitoring holes {self._reed_monitored_holes}")
        else:
            logging.error("Failed to start reed measurement")
            
        return success

    def stopReedMeasurement(self) -> bool:
        """
        Stop reed sensor measurement on the apparatus device.
        
        Stops the streaming of reed sensor data and finalizes the measurement session.
        
        Returns
        -------
        bool
            True if measurement stopped successfully, False otherwise.
        """
        if not self._reed_measuring:
            logging.warning("Reed measurement was not running")
            return True
        
        # Collect any remaining responses before stopping
        self._collectReedResponses()
        
        # Finalize durations for any holes that are still inserted
        final_timestamp = core.getTime()
        for hole in self._reed_monitored_holes:
            if self._reed_last_states[hole] == 1 and self._reed_last_insert_time[hole] is not None:
                # Hole is still inserted, calculate final duration
                duration = final_timestamp - self._reed_last_insert_time[hole]
                self._reed_active_durations[hole] += duration
        
        # Build summary statistics (only for holes with activity)
        self.reedSummary = []
        for hole in sorted(self._reed_monitored_holes):
            if self._reed_insertion_counts[hole] > 0 or self._reed_removal_counts[hole] > 0:
                self.reedSummary.append({
                    'hole': hole,
                    'insertions': self._reed_insertion_counts[hole],
                    'removals': self._reed_removal_counts[hole],
                    'duration': self._reed_active_durations[hole]
                })
        
        # Stop measurement on device
        success = self._device.stopReedMeasurement(wait_ack=True)
        
        if success:
            self._reed_measuring = False
            self.status = FINISHED
            logging.info(f"Reed measurement stopped. Collected {len(self.reedTimes)} events across {len(self.reedSummary)} active holes.")
        else:
            logging.error("Failed to stop reed measurement")
            
        return success

    def _collectReedResponses(self):
        """
        Collect reed sensor responses from the device.
        
        This method should be called regularly (e.g., each frame) during measurement
        to retrieve new reed data and update states/durations.
        """
        if not self._reed_measuring:
            return
        
        # Get all responses from device
        all_responses = self._device.getResponses()
        
        # Process only new responses (those received after measurement started)
        new_responses = all_responses[self._reed_start_response_count:]
        
        for response in new_responses:
            # Only process reed data responses
            if response.msg_type != DATA_REED:
                continue
            
            if hasattr(response, 'reed_holes') and response.reed_holes is not None:
                timestamp = response.t
                
                # Check each monitored hole for state changes
                for hole in self._reed_monitored_holes:
                    new_state = response.reed_holes.get(hole, 0)
                    old_state = self._reed_last_states[hole]
                    
                    # Detect state change
                    if new_state != old_state:
                        if new_state == 1:
                            # Insertion detected
                            action = 1
                            self._reed_insertion_counts[hole] += 1
                            self._reed_last_insert_time[hole] = timestamp
                        else:
                            # Removal detected
                            action = 0
                            self._reed_removal_counts[hole] += 1
                            # Calculate duration if we have an insertion time
                            if self._reed_last_insert_time[hole] is not None:
                                duration = timestamp - self._reed_last_insert_time[hole]
                                self._reed_active_durations[hole] += duration
                                self._reed_last_insert_time[hole] = None
                        
                        # Record event in parallel lists
                        self.reedTimes.append(timestamp)
                        self.reedHoles.append(hole)
                        self.reedActions.append(action)
                        
                        # Update last known state
                        self._reed_last_states[hole] = new_state
        
        # Update the response counter
        self._reed_start_response_count = len(all_responses)

    def updateReedMeasurement(self):
        """
        Update reed sensor measurement data.
        
        Call this method regularly (e.g., each frame) during active measurement
        to collect new reed sensor data from the device.
        """
        self._collectReedResponses()

    def startMeasurement(self, hole, method, light_feedback):
        """
        Start measurement on the apparatus device.
        
        NOTE: This method is dormant and not yet ported to the new protocol.
        Use startForceMeasurement() for force measurements.

        Parameters
        ----------
        hole : int
            The number of the hole to measure.
        method : str
            The measurement method to use. See the Apparatus manual for details.
        light_feedback : bool
            Whether to enable light feedback.
        """
        raise NotImplementedError("Generic measurement not yet ported to new protocol. Use startForceMeasurement() for force measurements.")

    def stopMeasurement(self):
        """
        Stop measurement on the apparatus device.
        
        NOTE: This method is dormant and not yet ported to the new protocol.
        Use stopForceMeasurement() for force measurements.
        """
        raise NotImplementedError("Generic measurement not yet ported to new protocol. Use stopForceMeasurement() for force measurements.")

    # ===== Response management =====

    def getResponses(self) -> list[ApparatusResponse]:
        """
        Get all responses received by the device.

        Returns
        -------
        list[ApparatusResponse]
            List of all responses received.
        """
        return self._device.getResponses()

    def clearResponses(self):
        """
        Clear all responses received by the device.
        """
        self._device.clearResponses()

    def resetClock(self):
        """
        Reset the device clock.
        """
        self._device.resetClock()

    def getLatestResponse(self) -> ApparatusResponse:
        """
        Get the latest response received by the device or None if there are no responses.

        Returns
        -------
        ApparatusResponse
            The latest response received.
        """
        return self._device.getLatestResponse()

    def getNumberOfResponses(self) -> int:
        """
        Get the number of responses received during measurement.

        Returns
        -------
        int
            Number of responses received.
        """
        return self._device.getNumberOfResponses()
