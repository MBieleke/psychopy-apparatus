from psychopy.experiment.components import BaseDeviceComponent, Param, getInitVals
from pathlib import Path

from psychopy_apparatus.components.apparatusDeviceBackend import ApparatusDeviceBackend
from psychopy.experiment.devices import DeviceBackend

class ApparatusReedComponent(BaseDeviceComponent):
    """
    Controls Apparatus reed measurement.
    """
    # mark it as coming from this plugin
    plugin = "psychopy-apparatus"
    # specify what libraries it has code for - PsychoPy and/or PsychoJS
    targets = ["PsychoPy"]
    # specify what category (or categories) to list this Component under in Builder
    categories = ['Apparatus']
    # path to this Component's icon file - ignoring the light/dark/classic folder and any @2x in the filename (PsychoPy will add these accordingly)
    iconFile = Path(__file__).parent / "example.png"
    # Text to display when this Component is hovered over
    tooltip = "Controls Apparatus reed measurement."
    # what is the earliest version of PsychoPy this Component works with?
    version = "0.0.1"
    # is this Component still in beta?
    beta = True

    def __init__(
        self, exp, parentName, 
        # basic
        name = "apparatusReed",
        holes = "'all'",
        rate = 100,
        endRoutineOnResponse = False,
        # device
        deviceLabel = "",
    ):
        # initialise the base component class
        BaseDeviceComponent.__init__(self, exp, parentName, name=name, deviceLabel=deviceLabel)
        # base params like start and stop time are already added by BaseComponent, so add any other params in here...

        self.exp.requireImport("Apparatus", "psychopy_apparatus.hardware.apparatus")

        # --- Params ---

        # appearance
        self.order += [
            "holes",
            "rate",
            "endRoutineOnResponse"
        ]
        self.params['holes'] = Param(   
            holes, valType="code", inputType="single", categ="Basic",
            label="Holes",
            hint="Keywords: 'all', 'inner', 'outer', 'none' (MUST use quotes!). Or: 0, [0,1,2], $loopVar"
        )
        self.params['rate'] = Param(
            rate, valType="code", inputType="single", categ="Basic",
            label="Rate (Hz)", hint="Sampling rate in Hz (e.g., 100 for 100 Hz)."
        )
        self.params['endRoutineOnResponse'] = Param(
            endRoutineOnResponse, valType="code", inputType="bool", categ="Basic",
            label="End Routine On State Change", hint="If checked, the routine will end when any monitored hole changes state."
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
                "%(name)s.startReedMeasurement(%(rate)s, %(holes)s)\n"
            )
            buff.writeIndentedLines(code % self.params)
            # dedent after!
            buff.setIndentLevel(-dedent, relative=True)
        
        # # use the same principle as we used for first-frame-of-Component code to add code which only runs while the Component is active
        dedent = self.writeActiveTestCode(buff)
        if dedent:
            # Update reed measurement data each frame
            code = (
                "%(name)s.updateReedMeasurement()\n"
                "if %(endRoutineOnResponse)s and len(%(name)s.reedTimes) > 0:\n"
                "    %(name)s.stopReedMeasurement()\n"
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
                "%(name)s.stopReedMeasurement()\n"
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
        # Stop measurement if it's still running (ensures summary is populated)
        code = (
            "# make sure reed measurement is stopped\n"
            "if %(name)s.status == STARTED:\n"
            "    %(name)s.stopReedMeasurement()\n"
        )
        buff.writeIndentedLines(code % self.params)
        
        # create a copy of params so that we can safely edit stuff
        params = self.params.copy()
        # add reference to the current loop (handy for data writing)
        params['currentLoop'] = self.currentLoop
        # store any data we'd like to store (start/stop are already handled)
        code = (
            "%(currentLoop)s.addData('%(name)s.rate', %(rate)s)\n"
            "%(currentLoop)s.addData('%(name)s.holes', %(holes)s)\n"
            "%(currentLoop)s.addData('%(name)s.reedTimes', %(name)s.reedTimes)\n"
            "%(currentLoop)s.addData('%(name)s.reedHoles', %(name)s.reedHoles)\n"
            "%(currentLoop)s.addData('%(name)s.reedActions', %(name)s.reedActions)\n"
            "%(currentLoop)s.addData('%(name)s.reedSummary', %(name)s.reedSummary)\n"
        )
        buff.writeIndentedLines(code % params)

# Register device backend for this component
ApparatusReedComponent.registerBackend(ApparatusDeviceBackend)