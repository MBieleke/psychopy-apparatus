import sys
import types


class DummyParam:
    def __init__(self, val, **kwargs):
        self.val = val
        self.updates = kwargs.get("updates")

    def __str__(self):
        return str(self.val)

    __repr__ = __str__


class DummyBuffer:
    def __init__(self):
        self.lines = []

    def writeIndentedLines(self, text):
        self.lines.append(text)

    def setIndentLevel(self, *_args, **_kwargs):
        pass

    def getvalue(self):
        return "".join(self.lines)


class DummyExperiment:
    def requireImport(self, *_args, **_kwargs):
        pass


class DummyBaseDeviceComponent:
    def __init__(
        self,
        exp,
        parentName,
        name,
        startType,
        startVal,
        stopType,
        stopVal,
        startEstim,
        durationEstim,
        deviceLabel,
    ):
        self.exp = exp
        self.parentName = parentName
        self.currentLoop = "currentLoop"
        self.order = []
        self.params = {
            "name": DummyParam(name),
            "deviceLabel": DummyParam(deviceLabel),
            "startType": DummyParam(startType),
            "startVal": DummyParam(startVal),
            "stopType": DummyParam(stopType),
            "stopVal": DummyParam(stopVal),
            "startEstim": DummyParam(startEstim),
            "durationEstim": DummyParam(durationEstim),
        }

    @classmethod
    def registerBackend(cls, _backend):
        return None

    def writeParamUpdates(self, *_args, **_kwargs):
        return None

    def writeStartTestCode(self, *_args, **_kwargs):
        return 0

    def writeActiveTestCode(self, *_args, **_kwargs):
        return 0

    def writeStopTestCode(self, *_args, **_kwargs):
        return 0


class DummyDeviceBackend:
    def __init__(self, _profile):
        pass


def dummy_get_init_vals(params):
    return params


def install_psychopy_stubs():
    psychopy = types.ModuleType("psychopy")
    experiment = types.ModuleType("psychopy.experiment")
    components = types.ModuleType("psychopy.experiment.components")
    devices = types.ModuleType("psychopy.experiment.devices")

    components.BaseDeviceComponent = DummyBaseDeviceComponent
    components.Param = DummyParam
    components.getInitVals = dummy_get_init_vals
    devices.DeviceBackend = DummyDeviceBackend

    psychopy.experiment = experiment
    experiment.components = components
    experiment.devices = devices

    sys.modules["psychopy"] = psychopy
    sys.modules["psychopy.experiment"] = experiment
    sys.modules["psychopy.experiment.components"] = components
    sys.modules["psychopy.experiment.devices"] = devices


install_psychopy_stubs()

from psychopy_apparatus.components.apparatusLED import ApparatusLEDComponent


class Recorder:
    def __init__(self):
        self.calls = []

    def turnOffLights(self, holes):
        self.calls.append(holes)


def build_routine_end_code(**kwargs):
    component = ApparatusLEDComponent(DummyExperiment(), "routine", **kwargs)
    buff = DummyBuffer()
    component.writeRoutineEndCode(buff)
    return buff.getvalue(), component


def exec_routine_end(code, component_name, component, led_off_sent):
    namespace = {
        component_name: component,
        f"{component_name}_led_off_sent": led_off_sent,
    }
    exec(code, namespace)
    return component.calls


def test_routine_end_turns_lights_off_when_stop_option_is_enabled():
    code, _component = build_routine_end_code(
        name="apparatusLED",
        lightHoles='"all"',
        turnOffOnStop=True,
        turnOffOnRoutineEnd=False,
    )

    lights = Recorder()

    calls = exec_routine_end(code, "apparatusLED", lights, led_off_sent=False)

    assert calls == ["all"]


def test_routine_end_does_not_turn_lights_off_twice():
    code, _component = build_routine_end_code(
        name="apparatusLED",
        lightHoles='"all"',
        turnOffOnStop=True,
        turnOffOnRoutineEnd=False,
    )

    lights = Recorder()

    calls = exec_routine_end(code, "apparatusLED", lights, led_off_sent=True)

    assert calls == []


def test_routine_end_respects_routine_end_flag_when_stop_option_is_disabled():
    code, _component = build_routine_end_code(
        name="apparatusLED",
        lightHoles="[0, 1]",
        turnOffOnStop=False,
        turnOffOnRoutineEnd=True,
    )

    lights = Recorder()

    calls = exec_routine_end(code, "apparatusLED", lights, led_off_sent=False)

    assert calls == [[0, 1]]
