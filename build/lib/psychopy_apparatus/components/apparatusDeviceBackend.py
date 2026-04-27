from psychopy.experiment.devices import DeviceBackend
from psychopy.experiment.components import Param

class ApparatusDeviceBackend(DeviceBackend):
    backendLabel = "Apparatus"
    icon = ""
    deviceClass = "psychopy.hardware.ApparatusDevice"

    plugin = "psychopy-apparatus"

    def __init__(self, profile):
        super().__init__(profile)

        self.order += [
            "port",
            "baudrate",
            "simulate"
        ]

        self.params['port'] = Param(
            "COM1",
            valType="str",
            inputType="single",
            hint="Port number for the TCP connection to Apparatus",
            label="Port"
        )

        self.params['baudrate'] = Param(
            115200,
            valType="str",
            inputType="single",
            hint="Baudrate for the serial connection to Apparatus",
            label="Baudrate"
        )

        self.params['simulate'] = Param(
            False,
            valType="str",
            inputType="bool",
            hint="Whether to simulate the Apparatus device (for testing without hardware)",
            label="Simulate Apparatus"
        )

        self.params['debug'] = Param(
            False,
            valType="str",
            inputType="bool",
            hint="Whether to enable debug logging for the Apparatus device",
            label="Debug Logging"
        )

    def writeDeviceCode(self, buff):
        """
        Code to setup a device with this backend.

        Parameters
        ----------
        buff : io.StringIO
            Text buffer to write code to.
        """
        # write basic code
        self.writeBaseDeviceCode(buff, close=False)
        # add param and close
        code = (
            "    port=%(port)s,\n"
            "    baudrate=%(baudrate)s,\n"
            "    simulate=%(simulate)s,\n"
            "    debug=%(debug)s\n"
            ")\n"
        )
        buff.writeIndentedLines(code % self.params)