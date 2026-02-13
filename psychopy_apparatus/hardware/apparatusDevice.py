import time
import psychopy
from serial import Serial
from serial.threaded import ReaderThread, Protocol
from psychopy import logging
from psychopy.hardware.base import BaseResponseDevice, BaseResponse


class ApparatusResponse(BaseResponse):
    """ 
    Blank hardware response object to showcase how to make a new type of hardware response for a ResponseDevice.

    Parameters
    ----------
    t : float
        Time at which the response happened
    value
        Value received (e.g. the key on a keyboard)
    """

class ApparatusDevice(BaseResponseDevice, aliases=["apparatus"]):
    """
    Blank hardware object to showcase how to make a new type of hardware object for a response device.
    
    Should be deleted before publishing your plugin.

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

    def __init__(self, port, baudrate=115200, simulate=False, debug=False, **kwargs):
        """
        Initialize the ApparatusDevice.

        Parameters
        ----------
        port : str
            Serial port to which the apparatus is connected.
        simulate : bool
            If True, simulate the device without actual hardware connection.
        debug : bool
            If True, enable debug logging.
        """
        super().__init__(**kwargs)
        self._port = port
        self._baudrate = baudrate
        self._simulate = simulate
        self._debug = debug
 
    @staticmethod
    def getAvailableDevices():
        return [{
            'deviceName': "Apparatus Device",
            'deviceClass': "psychopy.hardware.ApparatusDevice",
        }]
