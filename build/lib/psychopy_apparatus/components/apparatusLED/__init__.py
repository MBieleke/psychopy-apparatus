from pathlib import Path
from psychopy.experiment.components import BaseDeviceComponent, Param, getInitVals
from psychopy_apparatus.components.apparatusDeviceBackend import ApparatusDeviceBackend

class ApparatusLEDComponent(BaseDeviceComponent):
    """
    Controls Apparatus LEDs.
    """
    # mark it as coming from this plugin
    plugin = "psychopy-apparatus"
    # specify what libraries it has code for - PsychoPy and/or PsychoJS
    targets = ["PsychoPy"]
    # specify what category (or categories) to list this Component under in Builder
    categories = ['Apparatus']
    # path to this Component's icon file - ignoring the light/dark/classic folder and any @2x in the filename (PsychoPy will add these accordingly)
    iconFile = Path(__file__).parent / "led.png"
    # Text to display when this Component is hovered over
    tooltip = "Controls Apparatus LEDs."
    # what is the earliest version of PsychoPy this Component works with?
    version = "0.0.1"
    # is this Component still in beta?
    beta = True

    def __init__(
        self, exp, parentName, 
        # basic
        name = "apparatusLED",
        startType = 'time (s)', startVal = 0.0,
        stopType = 'duration (s)', stopVal = 1.0,
        startEstim = '', durationEstim = '',
        lightHoles = '"all"',
        lightColors = "black",
        turnOffOnStop = True,
        turnOffOnRoutineEnd = True,
        # device
        deviceLabel = "",
    ):
        # initialise the base component class
        BaseDeviceComponent.__init__(
            self, exp, parentName, 
            name = name, 
            startType = startType, startVal = startVal,
            stopType = stopType, stopVal = stopVal,
            startEstim = startEstim, durationEstim = durationEstim,
            deviceLabel = deviceLabel)
        # base params like start and stop time are already added by BaseComponent, so add any other params in here...

        self.exp.requireImport("Apparatus", "psychopy_apparatus.hardware.apparatus")

        # --- Params ---

        # appearance
        self.order += [
            "lightHoles",
            "lightColors",
            "turnOffOnStop",
            "turnOffOnRoutineEnd"
        ]
        self.params['lightHoles'] = Param(   
            lightHoles, valType = "code", inputType = "single", categ = "Basic",
            label = "Holes",
            updates = 'constant',
            allowedUpdates = ['constant', 'set every repeat'],
            hint = "Keywords (quoted): 'all' (0-20), 'inner' (0-7), 'outer' (8-20), 'none'. Or explicit: 0, [0,1,2]. Can use $variable from loops."
        )
        self.params['lightColors'] = Param(
            lightColors, valType = 'color', inputType = "color", categ = 'Basic',
            label = "Hole Color(s)",
            updates = 'constant',
            allowedUpdates = ['constant', 'set every repeat'],
            hint = "Single color: black, red, [1,0,0], [255,0,0]. Or list: ['red', 'green']. Can use $variable from loops."
        )
        self.params['turnOffOnStop'] = Param(
            turnOffOnStop, valType = "code", inputType = "bool", categ = "Basic",
            label = "Turn Off Hole Lights On Stop", hint = "Whether to turn off the selected hole lights when the component stops."
        )
        self.params['turnOffOnRoutineEnd'] = Param(
            turnOffOnRoutineEnd, valType = "code", inputType = "bool", categ = "Basic",
            label = "Turn Off Hole Lights On Routine End", hint = "Whether to turn off the selected hole lights when the routine ends."
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
        # Only apply colors if at least one parameter is 'set every repeat'
        if (self.params['lightHoles'].val != 'constant' or 
            self.params['lightColors'].val != 'constant'):
            code = (
                "%(name)s.setLights(%(lightHoles)s, %(lightColors)s)\n"
            )
            buff.writeIndentedLines(code % self.params)
    
    def writeFrameCode(self, buff):
        """
        Write the Python code which is called each frame for this Component.

        Parameters
        ----------
        buff : 
            String buffer to write to, i.e. the .py file
        """
        # No frame-specific updates needed; holes and colors are set at routine start
        # via writeParamUpdates() in writeRoutineStartCode()
        
        # use the same principles again for last-frame-of-Component code
        dedent = self.writeStopTestCode(buff)
        if dedent:
            # aaaaaaand some extra code for when the Component stops
            code = (
                "if %(turnOffOnStop)s:\n"
                "    print('turnOffOnStop in place!')\n"
                "    %(name)s.turnOffLights(%(lightHoles)s)\n"
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
        # store any data we'd like to store (start/stop are already handled)
        code = (
            "if %(turnOffOnRoutineEnd)s:\n"
            "    print('turnOffOnRoutineEnd in place!')\n"
            "    %(name)s.turnOffLights(%(lightHoles)s)\n"
        )
        buff.writeIndentedLines(code % params)

# Register device backend for this component
ApparatusLEDComponent.registerBackend(ApparatusDeviceBackend)