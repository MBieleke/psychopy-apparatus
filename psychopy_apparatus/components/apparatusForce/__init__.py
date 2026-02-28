from psychopy.experiment.components import BaseDeviceComponent, Param, getInitVals
from pathlib import Path

from psychopy_apparatus.components.apparatusDeviceBackend import ApparatusDeviceBackend
from psychopy.experiment.devices import DeviceBackend

class ApparatusForceComponent(BaseDeviceComponent):
    """
    Controls Apparatus force measurement.
    """
    # mark it as coming from this plugin
    plugin = "psychopy-apparatus"
    # specify what libraries it has code for - PsychoPy and/or PsychoJS
    targets = ["PsychoPy"]
    # specify what category (or categories) to list this Component under in Builder
    categories = ['Apparatus']
    # path to this Component's icon file - ignoring the light/dark/classic folder and any @2x in the filename (PsychoPy will add these accordingly)
    iconFile = Path(__file__).parent / "force.png"
    # Text to display when this Component is hovered over
    tooltip = "Controls Apparatus force measurement."
    # what is the earliest version of PsychoPy this Component works with?
    version = "0.0.1"
    # is this Component still in beta?
    beta = True

    def __init__(
        self, exp, parentName, 
        # basic
        name = "apparatusForce",
        rate = 100,
        device = "both",
        endRoutineOnResponse = False,
        saveRawData = False,
        rawDataId = "",
        # device
        deviceLabel = "",
    ):
        # initialise the base component class
        BaseDeviceComponent.__init__(self, exp, parentName, name=name, deviceLabel=deviceLabel)
        # base params like start and stop time are already added by BaseComponent, so add any other params in here...

        self.exp.requireImport("Apparatus", "psychopy_apparatus.hardware.apparatus")
        self.exp.requireImport("os")

        # --- Params ---

        # appearance
        self.order += [
            "rate",
            "device",
            "endRoutineOnResponse",
            "saveRawData",
            "rawDataId"
        ]
        self.params['rate'] = Param(
            rate, valType="code", inputType="single", categ="Basic",
            label="Rate (Hz)", hint="Sampling rate in Hz (e.g., 100 for 100 Hz)."
        )
        self.params['device'] = Param(
            device, valType="str", inputType="choice", categ="Basic",
            allowedVals=["white", "blue", "both"],
            label="Device", hint="Which dynamometer to measure: 'white' (right), 'blue' (left), or 'both'."
        )
        self.params['endRoutineOnResponse'] = Param(
            endRoutineOnResponse, valType="code", inputType="bool", categ="Basic",
            label="End Routine On Response", hint="If checked, the routine will end when a response is received."
        )
        self.params['saveRawData'] = Param(
            saveRawData, valType="code", inputType="bool", categ="Basic",
            label="Save Raw Data", hint="If checked, save raw force samples to a long-format file per experiment."
        )
        self.params['rawDataId'] = Param(
            rawDataId, valType="code", inputType="single", categ="Basic",
            label="Raw Data Identifier", hint="Optional identifier to tag rows (string or variable)."
        )

    def writeInitCode(self, buff):
        """
        Write the Python code which initialises the object for this Component.

        Parameters
        ----------
        buff : 
            String buffer to write to, i.e. the .py file
        """
        # any params using set each frame / repeat will need a safe value to start off with, this functon automatically substitutes those
        inits = getInitVals(self.params)
        # construct the actual code, using Python string formatting
        # remember that params with valType="str" will already have quotes so you don't need to add them
        # point component name to device object
        code = (
            "\n"
            "%(name)s = Apparatus(%(deviceLabel)s)\n"
        )

        # write the code to the string buffer (with params inserted)
        buff.writeIndentedLines(code % inits)

    def writeRoutineStartCode(self, buff):
        """
        Write the Python code which is called at the start of this Component's Routine

        Parameters
        ----------
        buff : 
            String buffer to write to, i.e. the .py file
        """
        # update any parameters which need updating
        self.writeParamUpdates(buff, updateType="set every repeat")
        # aaaaand that's all you need! unless you want anything else to happen here - it's essentially the equivalent of the Begin Routine tab in a Code Component
    
    def writeFrameCode(self, buff):
        """
        Write the Python code which is called each frame for this Component.

        Parameters
        ----------
        buff : 
            String buffer to write to, i.e. the .py file
        """
        # update any parameters which need updating
        self.writeParamUpdates(buff, updateType="set every frame")
        # some code we want to run just once on the first frame of the Component - so we'll use the writeStartTestCode function to open an if statement and then dedent after
        dedent = self.writeStartTestCode(buff)
        # we only want the following code written if an if loop actually was opened, not if the start time is None! so make sure to use dedent as a boolean to avoid writing broken code
        if dedent:
            # status setting is already written by writeStartTestCode, so here we can just worry about extra stuff
            code = (
                "%(name)s.startForceMeasurement(%(rate)s, %(device)s)\n"
            )
            buff.writeIndentedLines(code % self.params)
            # dedent after!
            buff.setIndentLevel(-dedent, relative=True)
        
        # # use the same principle as we used for first-frame-of-Component code to add code which only runs while the Component is active
        dedent = self.writeActiveTestCode(buff)
        if dedent:
            # Update force measurement data each frame
            code = (
                "%(name)s.updateForceMeasurement()\n"
                "if %(endRoutineOnResponse)s and %(name)s.getNumberOfResponses() > 0:\n"
                "    %(name)s.stopForceMeasurement()\n"
                "    continueRoutine = False\n"
            )   
            buff.writeIndentedLines(code % self.params)
            # dedent after!
            buff.setIndentLevel(-dedent, relative=True)
        
        # use the same principles again for last-frame-of-Component code
        dedent = self.writeStopTestCode(buff)
        if dedent:
            # aaaaaaand some extra code for when the Component stops
            code = (
                "%(name)s.stopForceMeasurement()\n"
            )
            buff.writeIndentedLines(code % self.params)
            # dedent after!
            buff.setIndentLevel(-dedent, relative=True)
    
    def writeRoutineEndCode(self, buff):
        """
        Write the Python code which is called at the end of this Component's Routine

        Parameters
        ----------
        buff : 
            String buffer to write to, i.e. the .py file
        """
        # create a copy of params so that we can safely edit stuff
        params = self.params.copy()
        # add reference to the current loop (handy for data writing)
        params['currentLoop'] = self.currentLoop
        params['parentName'] = self.parentName
        # store any data we'd like to store (start/stop are already handled)
        code = (
            "%(currentLoop)s.addData('%(name)s.rate', %(rate)s)\n"
            "%(currentLoop)s.addData('%(name)s.device', %(device)s)\n"
            "%(currentLoop)s.addData('%(name)s.maxWhiteForce', %(name)s.maxWhiteForce)\n"
            "%(currentLoop)s.addData('%(name)s.maxBlueForce', %(name)s.maxBlueForce)\n"
            "if %(saveRawData)s:\n"
            "    _raw_path = thisExp.dataFileName + '_force_long.tsv'\n"
            "    _write_header = not os.path.exists(_raw_path)\n"
            "    _loop = %(currentLoop)s\n"
            "    _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1\n"
            "    _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''\n"
            "    _identifier = %(rawDataId)s if %(rawDataId)s != None else ''\n"
            "    _times = %(name)s.times\n"
            "    _white = %(name)s.whiteForceValues\n"
            "    _blue = %(name)s.blueForceValues\n"
            "    _n = max(len(_times), len(_white), len(_blue))\n"
            "    with open(_raw_path, 'a', encoding='utf-8') as _f:\n"
            "        if _write_header:\n"
            "            _f.write('participant\tsession\troutine\tcomponent\ttrial_index\ttrial_name\tidentifier\tsample_index\ttime\twhite_force\tblue_force\\n')\n"
            "        for _i in range(_n):\n"
            "            _t = _times[_i] if _i < len(_times) else ''\n"
            "            _w = _white[_i] if _i < len(_white) else ''\n"
            "            _b = _blue[_i] if _i < len(_blue) else ''\n"
            "            _row = [\n"
            "                expInfo.get(\"participant\", \"\"),\n"
            "                expInfo.get(\"session\", \"\"),\n"
            "                '%(parentName)s',\n"
            "                '%(name)s',\n"
            "                _trial_index,\n"
            "                _trial_name,\n"
            "                _identifier,\n"
            "                _i,\n"
            "                _t,\n"
            "                _w,\n"
            "                _b,\n"
            "            ]\n"
            "            _f.write('\t'.join(str(_v) for _v in _row) + '\\n')\n"
        )
        buff.writeIndentedLines(code % params)

# Register device backend for this component
ApparatusForceComponent.registerBackend(ApparatusDeviceBackend)