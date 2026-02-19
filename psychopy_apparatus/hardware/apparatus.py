from psychopy.tools.attributetools import AttributeGetSetMixin
from psychopy import logging
from psychopy.constants import NOT_STARTED
from psychopy.hardware import DeviceManager
from psychopy.colors import Color
import time

from psychopy_apparatus.hardware.apparatusDevice import ApparatusResponse


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
        return list(holes_spec)


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

        self.whiteForce = 0
        self.blueForce = 0
        self.maxWhiteForce = 0
        self.maxBlueForce = 0

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
        raise NotImplementedError("Hand dynamometer not yet ported to new protocol")

    def startMeasurement(self, hole, method, light_feedback):
        """
        Start measurement on the apparatus device.
        
        NOTE: This method is dormant and not yet ported to the new protocol.

        Parameters
        ----------
        hole : int
            The number of the hole to measure.
        method : str
            The measurement method to use. See the Apparatus manual for details.
        light_feedback : bool
            Whether to enable light feedback.
        """
        raise NotImplementedError("Measurement not yet ported to new protocol")

    def stopMeasurement(self):
        """
        Stop measurement on the apparatus device.
        
        NOTE: This method is dormant and not yet ported to the new protocol.
        """
        raise NotImplementedError("Measurement not yet ported to new protocol")

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
