#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2026.1.1),
    on April 14, 2026, at 11:51
If you publish work using this script the most relevant publication is:

    Peirce J, Gray JR, Simpson S, MacAskill M, Höchenberger R, Sogo H, Kastman E, Lindeløv JK. (2019) 
        PsychoPy2: Experiments in behavior made easy Behav Res 51: 195. 
        https://doi.org/10.3758/s13428-018-01193-y

"""

# --- Import packages ---
from psychopy import locale_setup
from psychopy import prefs
from psychopy import plugins
plugins.activatePlugins()
from psychopy import sound, gui, visual, core, data, event, logging, clock, colors, layout, hardware
from psychopy.tools import environmenttools
from psychopy.constants import (
    NOT_STARTED, STARTED, PLAYING, PAUSED, STOPPED, STOPPING, FINISHED, PRESSED, 
    RELEASED, FOREVER, priority
)

import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import (sin, cos, tan, log, log10, pi, average,
                   sqrt, std, deg2rad, rad2deg, linspace, asarray)
from numpy.random import random, randint, normal, shuffle, choice as randchoice
import os  # handy system and path functions
import sys  # to get file system encoding

from psychopy.hardware import keyboard
from psychopy.colors import Color
from psychopy_apparatus.hardware.apparatus import Apparatus
import os

# Run 'Before Experiment' code from colorCode
import random
import math

def rgb_to_lab(rgb):
    """
    Convert color from RGB to CIELAB space. 

    Parameters
    ----------
    c: tuple
        A tuple of three floats representing the RGB color (each in range 0-1).
    """
    def pivot_rgb(c):
        return ((c + 0.055)/1.055)**2.4 if c > 0.04045 else c/12.92

    R, G, B = [pivot_rgb(v) for v in rgb]

    X = 0.4124564*R + 0.3575761*G + 0.1804375*B
    Y = 0.2126729*R + 0.7151522*G + 0.0721750*B
    Z = 0.0193339*R + 0.1191920*G + 0.9503041*B

    X /= 0.95047
    Z /= 1.08883

    def f(t):
        return t**(1/3) if t > 0.008856 else (7.787*t + 16/116)

    L = 116 * f(Y) - 16
    a = 500 * (f(X) - f(Y))
    b = 200 * (f(Y) - f(Z))

    return (L, a, b)

def delta_e2000(lab1, lab2):
    """
    Calculate the Delta E 2000 color difference between two CIELAB colors.

    Parameters
    ----------
    lab1 : tuple
        A tuple of three floats representing the first CIELAB color (L, a, b).
    lab2 : tuple
        A tuple of three floats representing the second CIELAB color (L, a, b).
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_L = (L1 + L2) / 2
    C1 = math.sqrt(a1*a1 + b1*b1)
    C2 = math.sqrt(a2*a2 + b2*b2)
    avg_C = (C1 + C2) / 2

    G = 0.5 * (1 - math.sqrt((avg_C**7)/((avg_C**7) + (25**7))))
    a1p = a1 * (1 + G)
    a2p = a2 * (1 + G)

    C1p = math.sqrt(a1p*a1p + b1*b1)
    C2p = math.sqrt(a2p*a2p + b2*b2)
    avg_Cp = (C1p + C2p) / 2

    h1p = (math.degrees(math.atan2(b1, a1p)) + 360) % 360
    h2p = (math.degrees(math.atan2(b2, a2p)) + 360) % 360

    dhp = h2p - h1p
    if abs(dhp) > 180:
        dhp -= 360 * math.copysign(1, dhp)
    dHp = 2 * math.sqrt(C1p*C2p) * math.sin(math.radians(dhp/2))

    avg_hp = (h1p + dhp/2) % 360

    T = 1 - 0.17*math.cos(math.radians(avg_hp - 30)) \
          + 0.24*math.cos(math.radians(2*avg_hp)) \
          + 0.32*math.cos(math.radians(3*avg_hp + 6)) \
          - 0.20*math.cos(math.radians(4*avg_hp - 63))

    Sl = 1 + (0.015*((avg_L - 50)**2)) / math.sqrt(20 + (avg_L - 50)**2)
    Sc = 1 + 0.045 * avg_Cp
    Sh = 1 + 0.015 * avg_Cp * T

    Rt = -2 * math.sqrt((avg_Cp**7)/((avg_Cp**7)+(25**7))) * \
         math.sin(math.radians(60 * math.exp(-(((avg_hp - 275)/25)**2))))

    dE = math.sqrt(
        (L2-L1)**2 / (Sl**2) +
        (C2p-C1p)**2 / (Sc**2) +
        (dHp)**2 / (Sh**2) +
        Rt * (C2p-C1p)/Sc * dHp/Sh
    )
    return dE

def generate_distractors(target_rgb, deltaE_mid, n):
    """
    Generate n distractor colors in RGB space that are approximately deltaE_mid away from the target_rgb color.
    
    Parameters
    ----------
    target_rgb : tuple
        A tuple of three floats representing the target RGB color (each in range 0-1).
    deltaE_mid : float
        The target Delta E 2000 distance from the target color.
    n : int
        The number of distractor colors to generate.
    """
    target_lab = rgb_to_lab(target_rgb)

    distractors = []
    attempts = 0

    while len(distractors) < n and attempts < 50000:
        attempts += 1

        # random RGB candidate
        rgb = (random.random(), random.random(), random.random())
        lab = rgb_to_lab(rgb)
        dE = delta_e2000(target_lab, lab)

        if abs(dE - deltaE_mid) <= 1.5:  # Bandbreite 3
            distractors.append(rgb)

    if len(distractors) < n:
        print("WARNUNG: nicht genug Farben im DeltaE-Band gefunden.")
        # auffüllen mit Zufallsfarben
        while len(distractors) < n:
            distractors.append((random.random(),random.random(),random.random()))

    return distractors



# Run 'Before Experiment' code from targetBalanceCognitive
import random
import numpy as np
# from scipy.stats import truncnorm, nur bei truncated normal distribution

NUM_REPS = 6 # Number of repetitions = Anzahl Durchgaenge per unique delatE value
nTrials = 12 # number of total repetitions
NUM_PALETTES = 24       # Number of palettes per repetition = Anzahl Paletten pro Durchgang
NUM_TARGETS_PER_REP = 4 # How many palettes have a target present in a single repetition
DELTA_E_MIN = 10    
DELTA_E_MAX = 60
deltaEPhysical = 70
mvcCognitive = 0.03

# --- Setup global variables (available in all functions) ---
# create a device manager to handle hardware (keyboards, mice, mirophones, speakers, etc.)
deviceManager = hardware.DeviceManager()
# ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
# store info about the experiment session
psychopyVersion = '2026.1.1'
expName = 'maxForce'  # from the Builder filename that created this script
expVersion = ''
# a list of functions to run when the experiment ends (starts off blank)
runAtExit = []
# information about this experiment
expInfo = {
    'participant': f"{randint(0, 999999):06.0f}",
    'session': '001',
    'date|hid': data.getDateStr(),
    'expName|hid': expName,
    'expVersion|hid': expVersion,
    'psychopyVersion|hid': psychopyVersion,
}

# --- Define some variables which will change depending on pilot mode ---
'''
To run in pilot mode, either use the run/pilot toggle in Builder, Coder and Runner, 
or run the experiment with `--pilot` as an argument. To change what pilot 
#mode does, check out the 'Pilot mode' tab in preferences.
'''
# work out from system args whether we are running in pilot mode
PILOTING = core.setPilotModeFromArgs()
# start off with values from experiment settings
_fullScr = True
_winSize = [1280, 800]
# if in pilot mode, apply overrides according to preferences
if PILOTING:
    # force windowed mode
    if prefs.piloting['forceWindowed']:
        _fullScr = False
        # set window size
        _winSize = prefs.piloting['forcedWindowSize']
    # replace default participant ID
    if prefs.piloting['replaceParticipantID']:
        expInfo['participant'] = 'pilot'

def showExpInfoDlg(expInfo):
    """
    Show participant info dialog.
    Parameters
    ==========
    expInfo : dict
        Information about this experiment.
    
    Returns
    ==========
    dict
        Information about this experiment.
    """
    # show participant info dialog
    dlg = gui.DlgFromDict(
        dictionary=expInfo, sortKeys=False, title=expName, alwaysOnTop=True
    )
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    # return expInfo
    return expInfo


def setupData(expInfo, dataDir=None):
    """
    Make an ExperimentHandler to handle trials and saving.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    dataDir : Path, str or None
        Folder to save the data to, leave as None to create a folder in the current directory.    
    Returns
    ==========
    psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    # remove dialog-specific syntax from expInfo
    for key, val in expInfo.copy().items():
        newKey, _ = data.utils.parsePipeSyntax(key)
        expInfo[newKey] = expInfo.pop(key)
    
    # data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
    if dataDir is None:
        dataDir = _thisDir
    filename = u'data/%s_%s_%s' % (expInfo['participant'], expName, expInfo['date'])
    # make sure filename is relative to dataDir
    if os.path.isabs(filename):
        dataDir = os.path.commonprefix([dataDir, filename])
        filename = os.path.relpath(filename, dataDir)
    
    # an ExperimentHandler isn't essential but helps with data saving
    thisExp = data.ExperimentHandler(
        name=expName, version=expVersion,
        extraInfo=expInfo, runtimeInfo=None,
        originPath='C:\\Users\\pop555877\\Documents\\GitHub\\Apparatus\\experiments\\experiment-1\\experiment-1_lastrun.py',
        savePickle=True, saveWideText=True,
        dataFileName=dataDir + os.sep + filename, sortColumns='time'
    )
    # store pilot mode in data file
    thisExp.addData('piloting', PILOTING, priority=priority.LOW)
    thisExp.setPriority('thisRow.t', priority.CRITICAL)
    thisExp.setPriority('expName', priority.LOW)
    # return experiment handler
    return thisExp


def setupLogging(filename):
    """
    Setup a log file and tell it what level to log at.
    
    Parameters
    ==========
    filename : str or pathlib.Path
        Filename to save log file and data files as, doesn't need an extension.
    
    Returns
    ==========
    psychopy.logging.LogFile
        Text stream to receive inputs from the logging system.
    """
    # set how much information should be printed to the console / app
    if PILOTING:
        logging.console.setLevel(
            prefs.piloting['pilotConsoleLoggingLevel']
        )
    else:
        logging.console.setLevel('warning')
    # save a log file for detail verbose info
    logFile = logging.LogFile(filename+'.log')
    if PILOTING:
        logFile.setLevel(
            prefs.piloting['pilotLoggingLevel']
        )
    else:
        logFile.setLevel(
            logging.getLevel('debug')
        )
    
    return logFile


def setupWindow(expInfo=None, win=None):
    """
    Setup the Window
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    win : psychopy.visual.Window
        Window to setup - leave as None to create a new window.
    
    Returns
    ==========
    psychopy.visual.Window
        Window in which to run this experiment.
    """
    if PILOTING:
        logging.debug('Fullscreen settings ignored as running in pilot mode.')
    
    if win is None:
        # if not given a window to setup, make one
        win = visual.Window(
            size=_winSize, fullscr=_fullScr, screen=1,
            winType='pyglet', allowGUI=False, allowStencil=False,
            monitor='testMonitor', color=[0,0,0], colorSpace='rgb',
            backgroundImage='', backgroundFit='none',
            blendMode='avg', useFBO=True,
            units='height',
            checkTiming=False  # we're going to do this ourselves in a moment
        )
    else:
        # if we have a window, just set the attributes which are safe to set
        win.color = [0,0,0]
        win.colorSpace = 'rgb'
        win.backgroundImage = ''
        win.backgroundFit = 'none'
        win.units = 'height'
    if expInfo is not None:
        # get/measure frame rate if not already in expInfo
        if win._monitorFrameRate is None:
            win._monitorFrameRate = win.getActualFrameRate(infoMsg='Attempting to measure frame rate of screen, please wait...')
        expInfo['frameRate'] = win._monitorFrameRate
    win.hideMessage()
    if PILOTING:
        # show a visual indicator if we're in piloting mode
        if prefs.piloting['showPilotingIndicator']:
            win.showPilotingIndicator()
        # always show the mouse in piloting mode
        if prefs.piloting['forceMouseVisible']:
            win.mouseVisible = True
    
    return win


def setupDevices(expInfo, thisExp, win):
    """
    Setup whatever devices are available (mouse, keyboard, speaker, eyetracker, etc.) and add them to 
    the device manager (deviceManager)
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window in which to run this experiment.
    Returns
    ==========
    bool
        True if completed successfully.
    """
    # --- Setup input devices ---
    ioConfig = {}
    ioSession = ioServer = eyetracker = None
    
    # store ioServer object in the device manager
    deviceManager.ioServer = ioServer
    
    # create a default keyboard (e.g. to check for escape)
    if deviceManager.getDevice('defaultKeyboard') is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='ptb'
        )
    # initialize 'apparatus'
    deviceManager.addDevice(
        deviceName='apparatus',
        deviceClass='psychopy.hardware.ApparatusDevice',
        port='COM6',
        baudrate='921600',
        simulate=False,
        debug=False
    )
    # return True if completed successfully
    return True

def pauseExperiment(thisExp, win=None, timers=[], currentRoutine=None):
    """
    Pause this experiment, preventing the flow from advancing to the next routine until resumed.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    timers : list, tuple
        List of timers to reset once pausing is finished.
    currentRoutine : psychopy.data.Routine
        Current Routine we are in at time of pausing, if any. This object tells PsychoPy what Components to pause/play/dispatch.
    """
    # if we are not paused, do nothing
    if thisExp.status != PAUSED:
        return
    
    # start a timer to figure out how long we're paused for
    pauseTimer = core.Clock()
    # pause any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.pause()
    # make sure we have a keyboard
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        defaultKeyboard = deviceManager.addKeyboard(
            deviceClass='keyboard',
            deviceName='defaultKeyboard',
            backend='PsychToolbox',
        )
    # run a while loop while we wait to unpause
    while thisExp.status == PAUSED:
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=['escape']):
            endExperiment(thisExp, win=win)
        # dispatch messages on response components
        if currentRoutine is not None:
            for comp in currentRoutine.getDispatchComponents():
                comp.device.dispatchMessages()
        # sleep 1ms so other threads can execute
        clock.time.sleep(0.001)
    # if stop was requested while paused, quit
    if thisExp.status == FINISHED:
        endExperiment(thisExp, win=win)
    # resume any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.play()
    # reset any timers
    for timer in timers:
        timer.addTime(-pauseTimer.getTime())


def run(expInfo, thisExp, win, globalClock=None, thisSession=None):
    """
    Run the experiment flow.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    psychopy.visual.Window
        Window in which to run this experiment.
    globalClock : psychopy.core.clock.Clock or None
        Clock to get global time from - supply None to make a new one.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    # mark experiment as started
    thisExp.status = STARTED
    # update experiment info
    expInfo['date'] = data.getDateStr()
    expInfo['expName'] = expName
    expInfo['expVersion'] = expVersion
    expInfo['psychopyVersion'] = psychopyVersion
    # make sure window is set to foreground to prevent losing focus
    win.winHandle.activate()
    # make sure variables created by exec are available globally
    exec = environmenttools.setExecEnvironment(globals())
    # get device handles from dict of input devices
    ioServer = deviceManager.ioServer
    # get/create a default keyboard (e.g. to check for escape)
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='PsychToolbox'
        )
    eyetracker = deviceManager.getDevice('eyetracker')
    # make sure we're running in the directory for this experiment
    os.chdir(_thisDir)
    # get filename from ExperimentHandler for convenience
    filename = thisExp.dataFileName
    frameTolerance = 0.001  # how close to onset before 'same' frame
    endExpNow = False  # flag for 'escape' or other condition => quit the exp
    # get frame duration from frame rate in expInfo
    if 'frameRate' in expInfo and expInfo['frameRate'] is not None:
        frameDur = 1.0 / round(expInfo['frameRate'])
    else:
        frameDur = 1.0 / 60.0  # could not measure, so guess
    
    # Start Code - component code to be run after the window creation
    
    # --- Initialize components for Routine "setup" ---
    # Run 'Begin Experiment' code from soundCode
    global _state_lock, _target_freq, _target_amp, _cur_amp, _phase, _stream
    global proposed, toneState, _lastSwitchT
    
    import numpy as np
    import sounddevice as sd
    import threading
    
    
    # Ton SetUp
    FS = 48000
    CHANNELS = 1
    
    
    
    # Tone control (shared)
    _state_lock = threading.Lock()
    _target_freq = 440.0
    _target_amp  = 0.0      # start muted
    _cur_amp     = 0.0
    _phase       = 0.0
    
    AMP_MAX = 1.0          # overall loudness
    AMP_SMOOTH = 0.1      # 0..1, higher = faster fade (avoids clicks)
    
    # Anti-chatter for threshold switching ---
    proposed = 0
    toneState = 0          # 0=mute, 1=440, 2=880
    stateHold = 0.1       # seconds: minimum time before state can change again
    _lastSwitchT = 0
    
    def audio_callback(outdata, frames, time, status):
        global _phase, _cur_amp, _target_amp, _target_freq
        # read target state thread-safely
        with _state_lock:
            tf = float(_target_freq)
            ta = float(_target_amp)
    
        # smooth amplitude to avoid clicks on on/off
        _cur_amp = (1.0 - AMP_SMOOTH) * _cur_amp + AMP_SMOOTH * ta
    
        # generate sine (even if muted; fine and simple)
        t = (np.arange(frames) / FS).astype(np.float32)
        phase_inc = 2.0 * np.pi * tf
        y = np.sin(_phase + phase_inc * t).astype(np.float32)
    
        # advance phase
        _phase = float((_phase + phase_inc * (frames / FS)) % (2.0 * np.pi))
    
        outdata[:] = (_cur_amp * y).reshape(-1, 1)
    
    _stream = sd.OutputStream(
        samplerate=FS,
        channels=CHANNELS,
        dtype="float32",
        callback=audio_callback,
    )
    if not _stream.active:
        _stream.start()
    
    
    # --- Initialize components for Routine "countdown" ---
    
    countdown_led = Apparatus('apparatus')
    countdown_text = visual.TextStim(win=win, name='countdown_text',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.2, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
    # --- Initialize components for Routine "mvc" ---
    
    led_mvc = Apparatus('apparatus')
    
    apparatusForce = Apparatus('apparatus')
    # Run 'Begin Experiment' code from code_2
    mvc_max_experimental = 0
    mvc_keyboard = keyboard.Keyboard(deviceName='defaultKeyboard')
    text = visual.TextStim(win=win, name='text',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    
    # --- Initialize components for Routine "targetColorBalance" ---
    
    # --- Initialize components for Routine "countdown" ---
    
    countdown_led = Apparatus('apparatus')
    countdown_text = visual.TextStim(win=win, name='countdown_text',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.2, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
    # --- Initialize components for Routine "target_presentation" ---
    
    targetLED = Apparatus(None)
    # Run 'Begin Experiment' code from ColorCode
    from psychopy.colors import Color
    
    # define amount of palettes and reps per domain
    NUM_PALETTES = 24
    NUM_TARGETS_PER_REP = 4
    
    practiceForce = Apparatus(None)
    targetText = visual.TextStim(win=win, name='targetText',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    
    # --- Initialize components for Routine "task" ---
    
    taskReed = Apparatus(None)
    
    taskLED = Apparatus(None)
    # Run 'Begin Experiment' code from distractorSamplingCode
    stimulus = 0.416
    N_DISTRACTORS = 8
    
    INNER_RING_HOLES = list(range(0, 8))
    OUTER_RING_HOLES = list(range(9, 21))
    
    taskText = visual.TextStim(win=win, name='taskText',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-3.0);
    
    taskForce = Apparatus(None)
    
    # --- Initialize components for Routine "postTask" ---
    dprimeText = visual.TextStim(win=win, name='dprimeText',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    # Run 'Begin Experiment' code from dprimeCode
    from scipy.stats import norm
    dprimeKeyResp = keyboard.Keyboard(deviceName='defaultKeyboard')
    
    # --- Initialize components for Routine "slider" ---
    EffortRating = visual.Slider(win=win, name='EffortRating',
        startValue=None, size=(1.0, 0.1), pos=(0, -0.2), units=win.units,
        labels=(0,1,2,3,4,5,6,7,8,9,10), ticks=(0,1,2,3,4,5,6,7,8,9,10), granularity=1.0,
        style='rating', styleTweaks=[], opacity=None,
        labelColor='LightGray', markerColor='Red', lineColor='White', colorSpace='rgb',
        font='Noto Sans', labelHeight=0.05,
        flip=False, ori=0.0, depth=0, readOnly=False)
    sliderText = visual.TextStim(win=win, name='sliderText',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-1.0);
    keyRespSlider = keyboard.Keyboard(deviceName='defaultKeyboard')
    
    # create some handy timers
    
    # global clock to track the time since experiment started
    if globalClock is None:
        # create a clock if not given one
        globalClock = core.Clock()
    if isinstance(globalClock, str):
        # if given a string, make a clock accoridng to it
        if globalClock == 'float':
            # get timestamps as a simple value
            globalClock = core.Clock(format='float')
        elif globalClock == 'iso':
            # get timestamps in ISO format
            globalClock = core.Clock(format='%Y-%m-%d_%H:%M:%S.%f%z')
        else:
            # get timestamps in a custom format
            globalClock = core.Clock(format=globalClock)
    if ioServer is not None:
        ioServer.syncClock(globalClock)
    logging.setDefaultClock(globalClock)
    if eyetracker is not None:
        eyetracker.enableEventReporting()
    # routine timer to track time remaining of each (possibly non-slip) routine
    routineTimer = core.Clock()
    win.flip()  # flip window to reset last flip timer
    # store the exact time the global clock started
    expInfo['expStart'] = data.getDateStr(
        format='%Y-%m-%d %Hh%M.%S.%f %z', fractionalSecondDigits=6
    )
    
    # --- Prepare to start Routine "setup" ---
    # create an object to store info about Routine setup
    setup = data.Routine(
        name='setup',
        components=[],
    )
    setup.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for setup
    setup.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    setup.tStart = globalClock.getTime(format='float')
    setup.status = STARTED
    thisExp.addData('setup.started', setup.tStart)
    setup.maxDuration = None
    # keep track of which components have finished
    setupComponents = setup.components
    for thisComponent in setup.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "setup" ---
    thisExp.currentRoutine = setup
    setup.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=setup,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            setup.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if setup.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in setup.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "setup" ---
    for thisComponent in setup.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for setup
    setup.tStop = globalClock.getTime(format='float')
    setup.tStopRefresh = tThisFlipGlobal
    thisExp.addData('setup.stopped', setup.tStop)
    thisExp.nextEntry()
    # the Routine "setup" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    loop_mvc_block = data.TrialHandler2(
        name='loop_mvc_block',
        nReps=1.0, 
        method='sequential', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('mvc_block.xlsx'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(loop_mvc_block)  # add the loop to the experiment
    thisLoop_mvc_block = loop_mvc_block.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisLoop_mvc_block.rgb)
    if thisLoop_mvc_block != None:
        for paramName in thisLoop_mvc_block:
            globals()[paramName] = thisLoop_mvc_block[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisLoop_mvc_block in loop_mvc_block:
        loop_mvc_block.status = STARTED
        if hasattr(thisLoop_mvc_block, 'status'):
            thisLoop_mvc_block.status = STARTED
        currentLoop = loop_mvc_block
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisLoop_mvc_block.rgb)
        if thisLoop_mvc_block != None:
            for paramName in thisLoop_mvc_block:
                globals()[paramName] = thisLoop_mvc_block[paramName]
        
        # set up handler to look after randomisation of conditions etc
        loop_mvc_trial = data.TrialHandler2(
            name='loop_mvc_trial',
            nReps=mvc_trial_nrepeat, 
            method='sequential', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(loop_mvc_trial)  # add the loop to the experiment
        thisLoop_mvc_trial = loop_mvc_trial.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisLoop_mvc_trial.rgb)
        if thisLoop_mvc_trial != None:
            for paramName in thisLoop_mvc_trial:
                globals()[paramName] = thisLoop_mvc_trial[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisLoop_mvc_trial in loop_mvc_trial:
            loop_mvc_trial.status = STARTED
            if hasattr(thisLoop_mvc_trial, 'status'):
                thisLoop_mvc_trial.status = STARTED
            currentLoop = loop_mvc_trial
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisLoop_mvc_trial.rgb)
            if thisLoop_mvc_trial != None:
                for paramName in thisLoop_mvc_trial:
                    globals()[paramName] = thisLoop_mvc_trial[paramName]
            
            # --- Prepare to start Routine "countdown" ---
            # create an object to store info about Routine countdown
            countdown = data.Routine(
                name='countdown',
                components=[countdown_led, countdown_text],
            )
            countdown.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from countdown_code
            from psychopy.colors import Color
            
            # Countdown configuration
            countdown_holes = list(range(8))  # inner holes (8-20)
            countdown_current_index = len(countdown_holes)  # Start with all lights on
            countdown_last_update = None
            countdown_interval = 0.5  # Update every 0.5 seconds
            
            # Turn on all outer lights initially
            if countdown_current_index > 0:
                active_holes = countdown_holes[:countdown_current_index]
                countdown_led.setHoleLights(active_holes, Color('white'))
            # store start times for countdown
            countdown.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            countdown.tStart = globalClock.getTime(format='float')
            countdown.status = STARTED
            thisExp.addData('countdown.started', countdown.tStart)
            countdown.maxDuration = None
            # keep track of which components have finished
            countdownComponents = countdown.components
            for thisComponent in countdown.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "countdown" ---
            thisExp.currentRoutine = countdown
            countdown.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisLoop_mvc_trial, 'status') and thisLoop_mvc_trial.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # if countdown_led is starting this frame...
                if countdown_led.status == NOT_STARTED and t >= 0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_led.frameNStart = frameN  # exact frame index
                    countdown_led.tStart = t  # local t and not account for scr refresh
                    countdown_led.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_led, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('countdown_led.started', t)
                    # update status
                    countdown_led.status = STARTED
                    # Handle colors: single or multiple
                    _colors = 'black'
                    
                    # Detect if we have multiple colors (list of lists/tuples or list of strings)
                    _is_multiple_colors = (
                        isinstance(_colors, (list, tuple)) and
                        len(_colors) > 0 and
                        (isinstance(_colors[0], (list, tuple)) or isinstance(_colors[0], str))
                    )
                    
                    if _is_multiple_colors:
                        # Multiple colors per hole - use setColors with mapping
                        # Note: holes parameter must match the number of colors
                        _holes_spec = 'none'
                        _color_dict = {}
                        # If holes is a keyword, we can't map individual colors; warn user
                        if isinstance(_holes_spec, str):
                            logging.warning('Cannot use keyword holes with multiple colors. Use explicit list of holes instead.')
                        else:
                            # Map each hole to its color
                            _holes_list = [_holes_spec] if isinstance(_holes_spec, int) else list(_holes_spec)
                            if len(_holes_list) == len(_colors):
                                for _hole, _color_spec in zip(_holes_list, _colors):
                                    if isinstance(_color_spec, str):
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                    else:
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                countdown_led.setColors(_color_dict)
                    else:
                        # Single color for all holes (Apparatus will handle hole parsing)
                        if isinstance(_colors, str):
                            _color = Color(_colors, space='rgb')
                        else:
                            _color = Color(_colors, space='rgb')
                        countdown_led.setHoleLights('none', _color)
                
                # if countdown_led is active this frame...
                if countdown_led.status == STARTED:
                    # update params
                    pass
                    
                # Run 'Each Frame' code from countdown_code
                # Check if it's time to update the countdown
                if countdown_last_update is None:
                    countdown_last_update = t  # t is the routine timer
                
                if t - countdown_last_update >= countdown_interval:
                    # Decrease the number of active lights
                    countdown_current_index -= 1
                    countdown_last_update = t
                    
                    if countdown_current_index > 0:
                        # Turn on the remaining lights
                        active_holes = countdown_holes[:countdown_current_index]
                        countdown_led.setHoleLights(active_holes, Color('white'))
                        # Turn off the rest
                        inactive_holes = countdown_holes[countdown_current_index:]
                        countdown_led.turnOffHoleLights(inactive_holes)
                    else:
                        # All lights off
                        countdown_led.turnOffHoleLights('outer')
                        continueRoutine = False
                
                # *countdown_text* updates
                
                # if countdown_text is starting this frame...
                if countdown_text.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_text.frameNStart = frameN  # exact frame index
                    countdown_text.tStart = t  # local t and not account for scr refresh
                    countdown_text.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_text, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'countdown_text.started')
                    # update status
                    countdown_text.status = STARTED
                    countdown_text.setAutoDraw(True)
                
                # if countdown_text is active this frame...
                if countdown_text.status == STARTED:
                    # update params
                    countdown_text.setText(countdown_current_index, log=False)
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=countdown,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    countdown.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if countdown.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in countdown.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "countdown" ---
            for thisComponent in countdown.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for countdown
            countdown.tStop = globalClock.getTime(format='float')
            countdown.tStopRefresh = tThisFlipGlobal
            thisExp.addData('countdown.stopped', countdown.tStop)
            if False:
                countdown_led.turnOffHoleLights('none')
            # the Routine "countdown" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # --- Prepare to start Routine "mvc" ---
            # create an object to store info about Routine mvc
            mvc = data.Routine(
                name='mvc',
                components=[led_mvc, apparatusForce, mvc_keyboard, text],
            )
            mvc.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from code_2
            mvc_max_trial = 0
            # create starting attributes for mvc_keyboard
            mvc_keyboard.keys = []
            mvc_keyboard.rt = []
            _mvc_keyboard_allKeys = []
            # store start times for mvc
            mvc.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            mvc.tStart = globalClock.getTime(format='float')
            mvc.status = STARTED
            thisExp.addData('mvc.started', mvc.tStart)
            mvc.maxDuration = None
            # keep track of which components have finished
            mvcComponents = mvc.components
            for thisComponent in mvc.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "mvc" ---
            thisExp.currentRoutine = mvc
            mvc.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisLoop_mvc_trial, 'status') and thisLoop_mvc_trial.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # if led_mvc is starting this frame...
                if led_mvc.status == NOT_STARTED and t >= 0-frameTolerance:
                    # keep track of start time/frame for later
                    led_mvc.frameNStart = frameN  # exact frame index
                    led_mvc.tStart = t  # local t and not account for scr refresh
                    led_mvc.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(led_mvc, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('led_mvc.started', t)
                    # update status
                    led_mvc.status = STARTED
                    # Handle colors: single or multiple
                    _colors = 'white'
                    
                    # Detect if we have multiple colors (list of lists/tuples or list of strings)
                    _is_multiple_colors = (
                        isinstance(_colors, (list, tuple)) and
                        len(_colors) > 0 and
                        (isinstance(_colors[0], (list, tuple)) or isinstance(_colors[0], str))
                    )
                    
                    if _is_multiple_colors:
                        # Multiple colors per hole - use setColors with mapping
                        # Note: holes parameter must match the number of colors
                        _holes_spec = 'all'
                        _color_dict = {}
                        # If holes is a keyword, we can't map individual colors; warn user
                        if isinstance(_holes_spec, str):
                            logging.warning('Cannot use keyword holes with multiple colors. Use explicit list of holes instead.')
                        else:
                            # Map each hole to its color
                            _holes_list = [_holes_spec] if isinstance(_holes_spec, int) else list(_holes_spec)
                            if len(_holes_list) == len(_colors):
                                for _hole, _color_spec in zip(_holes_list, _colors):
                                    if isinstance(_color_spec, str):
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                    else:
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                led_mvc.setColors(_color_dict)
                    else:
                        # Single color for all holes (Apparatus will handle hole parsing)
                        if isinstance(_colors, str):
                            _color = Color(_colors, space='rgb')
                        else:
                            _color = Color(_colors, space='rgb')
                        led_mvc.setHoleLights('all', _color)
                
                # if led_mvc is active this frame...
                if led_mvc.status == STARTED:
                    # update params
                    pass
                    
                
                # if led_mvc is stopping this frame...
                if led_mvc.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > led_mvc.tStartRefresh + 3-frameTolerance:
                        # keep track of stop time/frame for later
                        led_mvc.tStop = t  # not accounting for scr refresh
                        led_mvc.tStopRefresh = tThisFlipGlobal  # on global time
                        led_mvc.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('led_mvc.stopped', t)
                        # update status
                        led_mvc.status = FINISHED
                        if True:
                            led_mvc.turnOffHoleLights('all')
                
                # if apparatusForce is starting this frame...
                if apparatusForce.status == NOT_STARTED and t >= 0-frameTolerance:
                    # keep track of start time/frame for later
                    apparatusForce.frameNStart = frameN  # exact frame index
                    apparatusForce.tStart = t  # local t and not account for scr refresh
                    apparatusForce.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(apparatusForce, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('apparatusForce.started', t)
                    # update status
                    apparatusForce.status = STARTED
                    apparatusForce.startForceMeasurement(50, 'white')
                
                # if apparatusForce is active this frame...
                if apparatusForce.status == STARTED:
                    # update params
                    pass
                    apparatusForce.updateForceMeasurement()
                    if False and apparatusForce.getNumberOfResponses() > 0:
                        apparatusForce.stopForceMeasurement()
                        continueRoutine = False
                
                # if apparatusForce is stopping this frame...
                if apparatusForce.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > apparatusForce.tStartRefresh + 10-frameTolerance:
                        # keep track of stop time/frame for later
                        apparatusForce.tStop = t  # not accounting for scr refresh
                        apparatusForce.tStopRefresh = tThisFlipGlobal  # on global time
                        apparatusForce.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('apparatusForce.stopped', t)
                        # update status
                        apparatusForce.status = FINISHED
                        apparatusForce.stopForceMeasurement()
                # Run 'Each Frame' code from code_2
                if apparatusForce.maxWhiteForce > mvc_max_trial:
                    mvc_max_trial = apparatusForce.maxWhiteForce
                    
                if mvc_trial_type == "experimental":
                    if mvc_max_trial > mvc_max_experimental:
                        mvc_max_experimental = mvc_max_trial
                
                # *mvc_keyboard* updates
                waitOnFlip = False
                
                # if mvc_keyboard is starting this frame...
                if mvc_keyboard.status == NOT_STARTED and tThisFlip >= 3.0-frameTolerance:
                    # keep track of start time/frame for later
                    mvc_keyboard.frameNStart = frameN  # exact frame index
                    mvc_keyboard.tStart = t  # local t and not account for scr refresh
                    mvc_keyboard.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(mvc_keyboard, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'mvc_keyboard.started')
                    # update status
                    mvc_keyboard.status = STARTED
                    # keyboard checking is just starting
                    waitOnFlip = True
                    win.callOnFlip(mvc_keyboard.clock.reset)  # t=0 on next screen flip
                    win.callOnFlip(mvc_keyboard.clearEvents, eventType='keyboard')  # clear events on next screen flip
                
                # if mvc_keyboard is stopping this frame...
                if mvc_keyboard.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > mvc_keyboard.tStartRefresh + mvc_trial_duration-frameTolerance:
                        # keep track of stop time/frame for later
                        mvc_keyboard.tStop = t  # not accounting for scr refresh
                        mvc_keyboard.tStopRefresh = tThisFlipGlobal  # on global time
                        mvc_keyboard.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'mvc_keyboard.stopped')
                        # update status
                        mvc_keyboard.status = FINISHED
                        mvc_keyboard.status = FINISHED
                if mvc_keyboard.status == STARTED and not waitOnFlip:
                    theseKeys = mvc_keyboard.getKeys(keyList=['y','n','left','right','space'], ignoreKeys=["escape"], waitRelease=False)
                    _mvc_keyboard_allKeys.extend(theseKeys)
                    if len(_mvc_keyboard_allKeys):
                        mvc_keyboard.keys = _mvc_keyboard_allKeys[-1].name  # just the last key pressed
                        mvc_keyboard.rt = _mvc_keyboard_allKeys[-1].rt
                        mvc_keyboard.duration = _mvc_keyboard_allKeys[-1].duration
                        # a response ends the routine
                        continueRoutine = False
                
                # *text* updates
                
                # if text is starting this frame...
                if text.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    text.frameNStart = frameN  # exact frame index
                    text.tStart = t  # local t and not account for scr refresh
                    text.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(text, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'text.started')
                    # update status
                    text.status = STARTED
                    text.setAutoDraw(True)
                
                # if text is active this frame...
                if text.status == STARTED:
                    # update params
                    text.setText(f"Trial Type: {mvc_trial_type}\n\nForce: {apparatusForce.whiteForce}\n\nMax Experimental: {mvc_max_experimental}", log=False)
                
                # if text is stopping this frame...
                if text.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > text.tStartRefresh + 45-frameTolerance:
                        # keep track of stop time/frame for later
                        text.tStop = t  # not accounting for scr refresh
                        text.tStopRefresh = tThisFlipGlobal  # on global time
                        text.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'text.stopped')
                        # update status
                        text.status = FINISHED
                        text.setAutoDraw(False)
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=mvc,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    mvc.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if mvc.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in mvc.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "mvc" ---
            for thisComponent in mvc.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for mvc
            mvc.tStop = globalClock.getTime(format='float')
            mvc.tStopRefresh = tThisFlipGlobal
            thisExp.addData('mvc.stopped', mvc.tStop)
            if True:
                led_mvc.turnOffHoleLights('all')
            loop_mvc_trial.addData('apparatusForce.rate', 50)
            loop_mvc_trial.addData('apparatusForce.device', 'white')
            loop_mvc_trial.addData('apparatusForce.maxWhiteForce', apparatusForce.maxWhiteForce)
            loop_mvc_trial.addData('apparatusForce.maxBlueForce', apparatusForce.maxBlueForce)
            if True:
                _raw_path = thisExp.dataFileName + '_force_long.tsv'
                _write_header = not os.path.exists(_raw_path)
                _loop = loop_mvc_trial
                _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                _identifier = "test" if "test" != None else ''
                _times = apparatusForce.times
                _white = apparatusForce.whiteForceValues
                _blue = apparatusForce.blueForceValues
                _n = max(len(_times), len(_white), len(_blue))
                with open(_raw_path, 'a', encoding='utf-8') as _f:
                    if _write_header:
                        _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	time	white_force	blue_force\n')
                    for _i in range(_n):
                        _t = _times[_i] if _i < len(_times) else ''
                        _w = _white[_i] if _i < len(_white) else ''
                        _b = _blue[_i] if _i < len(_blue) else ''
                        _row = [
                            expInfo.get("participant", ""),
                            expInfo.get("session", ""),
                            'mvc',
                            'apparatusForce',
                            _trial_index,
                            _trial_name,
                            _identifier,
                            _i,
                            _t,
                            _w,
                            _b,
                        ]
                        _f.write('	'.join(str(_v) for _v in _row) + '\n')
            # Run 'End Routine' code from code_2
            print(f"Maximum force across all experimental trials: {mvc_max_experimental}")
            # check responses
            if mvc_keyboard.keys in ['', [], None]:  # No response was made
                mvc_keyboard.keys = None
            loop_mvc_trial.addData('mvc_keyboard.keys',mvc_keyboard.keys)
            if mvc_keyboard.keys != None:  # we had a response
                loop_mvc_trial.addData('mvc_keyboard.rt', mvc_keyboard.rt)
                loop_mvc_trial.addData('mvc_keyboard.duration', mvc_keyboard.duration)
            # the Routine "mvc" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            # mark thisLoop_mvc_trial as finished
            if hasattr(thisLoop_mvc_trial, 'status'):
                thisLoop_mvc_trial.status = FINISHED
            # if awaiting a pause, pause now
            if loop_mvc_trial.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                loop_mvc_trial.status = STARTED
            thisExp.nextEntry()
            
        # completed mvc_trial_nrepeat repeats of 'loop_mvc_trial'
        loop_mvc_trial.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # mark thisLoop_mvc_block as finished
        if hasattr(thisLoop_mvc_block, 'status'):
            thisLoop_mvc_block.status = FINISHED
        # if awaiting a pause, pause now
        if loop_mvc_block.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            loop_mvc_block.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'loop_mvc_block'
    loop_mvc_block.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # set up handler to look after randomisation of conditions etc
    domainLoop = data.TrialHandler2(
        name='domainLoop',
        nReps=1.0, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('domainLoop.xlsx'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(domainLoop)  # add the loop to the experiment
    thisDomainLoop = domainLoop.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisDomainLoop.rgb)
    if thisDomainLoop != None:
        for paramName in thisDomainLoop:
            globals()[paramName] = thisDomainLoop[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisDomainLoop in domainLoop:
        domainLoop.status = STARTED
        if hasattr(thisDomainLoop, 'status'):
            thisDomainLoop.status = STARTED
        currentLoop = domainLoop
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisDomainLoop.rgb)
        if thisDomainLoop != None:
            for paramName in thisDomainLoop:
                globals()[paramName] = thisDomainLoop[paramName]
        
        # --- Prepare to start Routine "targetColorBalance" ---
        # create an object to store info about Routine targetColorBalance
        targetColorBalance = data.Routine(
            name='targetColorBalance',
            components=[],
        )
        targetColorBalance.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from targetBalanceCognitive
        import random
        import numpy as np
        from psychopy.colors import Color
        
        if domain == 'physical':
            deltaELevels = np.linspace(DELTA_E_MIN, DELTA_E_MAX, 6).tolist()
            n_blocks = 3
        
            deltaE_order_per_block = {}
        
            for block in range(n_blocks):
                levels = deltaELevels.copy()
                random.shuffle(levels)
                deltaE_order_per_block[block] = levels
        
            targetColors = [
                Color([255, 0, 0], 'rgb255'),
                Color([0, 255, 0], 'rgb255'),
                Color([0, 0, 255], 'rgb255')
            ]
        
            deltaE_color_map = {}
        
            for dE in deltaELevels:
                shuffled_colors = random.sample(targetColors, n_blocks)
                deltaE_color_map[dE] = {
                    block: shuffled_colors[block]
                    for block in range(n_blocks)
                }
                
                
            print("\n===== DELTAE DESIGN CHECK =====")
            for block in range(n_blocks):
                print(f"\nBlock {block+1} order:")
                for dE in deltaE_order_per_block[block]:
                    print(
                        f"  DeltaE {dE:.3f} -> "
                        f"Color {deltaE_color_map[dE][block]}"
                    )
            print("================================\n")
            deltaE = 70
        else:
        
        
            # -----------------------------
            # 1) MVC-Level definieren
            # -----------------------------
            mvcLevels = np.linspace(0.1, 0.4, 6).tolist()
            n_blocks = 3
        
            # -----------------------------
            # 2) MVC-Reihenfolge PRO BLOCK
            # mvc_order_per_block[block][trial] -> mvcLevel
            # -----------------------------
            mvc_order_per_block = {}
        
            for block in range(n_blocks):
                levels = mvcLevels.copy()
                random.shuffle(levels)
                mvc_order_per_block[block] = levels
        
            # -----------------------------
            # 3) Target-Farben definieren
            # -----------------------------
            targetColors = [
                Color([255, 0, 0], 'rgb255'),
                Color([0, 255, 0], 'rgb255'),
                Color([0, 0, 255], 'rgb255')
            ]
        
            # -----------------------------
            # 4) MVC × Block → Farbe
            # color_map[mvcLevel][block] -> Farbe
            # -----------------------------
            color_map = {}
        
            for lvl in mvcLevels:
                shuffled_colors = random.sample(targetColors, n_blocks)
                color_map[lvl] = {
                    block: shuffled_colors[block]
                    for block in range(n_blocks)
                }
        
            # -----------------------------
            # 5) DEBUG: vollständiger Design-Check
            # -----------------------------
            print("\n===== PHYSICAL TASK DESIGN CHECK =====")
        
            for block in range(n_blocks):
                print(f"\nBlock {block + 1} order:")
                for lvl in mvc_order_per_block[block]:
                    print(
                        f"  MVC {lvl:.3f} -> "
                        f"Color {color_map[lvl][block]}"
                    )
        
            print("======================================\n")
            mvcLevel = 0.03
        # store start times for targetColorBalance
        targetColorBalance.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        targetColorBalance.tStart = globalClock.getTime(format='float')
        targetColorBalance.status = STARTED
        thisExp.addData('targetColorBalance.started', targetColorBalance.tStart)
        targetColorBalance.maxDuration = None
        # keep track of which components have finished
        targetColorBalanceComponents = targetColorBalance.components
        for thisComponent in targetColorBalance.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "targetColorBalance" ---
        thisExp.currentRoutine = targetColorBalance
        targetColorBalance.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisDomainLoop, 'status') and thisDomainLoop.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=targetColorBalance,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                targetColorBalance.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if targetColorBalance.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in targetColorBalance.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "targetColorBalance" ---
        for thisComponent in targetColorBalance.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for targetColorBalance
        targetColorBalance.tStop = globalClock.getTime(format='float')
        targetColorBalance.tStopRefresh = tThisFlipGlobal
        thisExp.addData('targetColorBalance.stopped', targetColorBalance.tStop)
        # the Routine "targetColorBalance" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # set up handler to look after randomisation of conditions etc
        blockLoop = data.TrialHandler2(
            name='blockLoop',
            nReps=3, 
            method='random', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(blockLoop)  # add the loop to the experiment
        thisBlockLoop = blockLoop.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisBlockLoop.rgb)
        if thisBlockLoop != None:
            for paramName in thisBlockLoop:
                globals()[paramName] = thisBlockLoop[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisBlockLoop in blockLoop:
            blockLoop.status = STARTED
            if hasattr(thisBlockLoop, 'status'):
                thisBlockLoop.status = STARTED
            currentLoop = blockLoop
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisBlockLoop.rgb)
            if thisBlockLoop != None:
                for paramName in thisBlockLoop:
                    globals()[paramName] = thisBlockLoop[paramName]
            
            # --- Prepare to start Routine "countdown" ---
            # create an object to store info about Routine countdown
            countdown = data.Routine(
                name='countdown',
                components=[countdown_led, countdown_text],
            )
            countdown.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from countdown_code
            from psychopy.colors import Color
            
            # Countdown configuration
            countdown_holes = list(range(8))  # inner holes (8-20)
            countdown_current_index = len(countdown_holes)  # Start with all lights on
            countdown_last_update = None
            countdown_interval = 0.5  # Update every 0.5 seconds
            
            # Turn on all outer lights initially
            if countdown_current_index > 0:
                active_holes = countdown_holes[:countdown_current_index]
                countdown_led.setHoleLights(active_holes, Color('white'))
            # store start times for countdown
            countdown.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            countdown.tStart = globalClock.getTime(format='float')
            countdown.status = STARTED
            thisExp.addData('countdown.started', countdown.tStart)
            countdown.maxDuration = None
            # keep track of which components have finished
            countdownComponents = countdown.components
            for thisComponent in countdown.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "countdown" ---
            thisExp.currentRoutine = countdown
            countdown.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisBlockLoop, 'status') and thisBlockLoop.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # if countdown_led is starting this frame...
                if countdown_led.status == NOT_STARTED and t >= 0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_led.frameNStart = frameN  # exact frame index
                    countdown_led.tStart = t  # local t and not account for scr refresh
                    countdown_led.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_led, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('countdown_led.started', t)
                    # update status
                    countdown_led.status = STARTED
                    # Handle colors: single or multiple
                    _colors = 'black'
                    
                    # Detect if we have multiple colors (list of lists/tuples or list of strings)
                    _is_multiple_colors = (
                        isinstance(_colors, (list, tuple)) and
                        len(_colors) > 0 and
                        (isinstance(_colors[0], (list, tuple)) or isinstance(_colors[0], str))
                    )
                    
                    if _is_multiple_colors:
                        # Multiple colors per hole - use setColors with mapping
                        # Note: holes parameter must match the number of colors
                        _holes_spec = 'none'
                        _color_dict = {}
                        # If holes is a keyword, we can't map individual colors; warn user
                        if isinstance(_holes_spec, str):
                            logging.warning('Cannot use keyword holes with multiple colors. Use explicit list of holes instead.')
                        else:
                            # Map each hole to its color
                            _holes_list = [_holes_spec] if isinstance(_holes_spec, int) else list(_holes_spec)
                            if len(_holes_list) == len(_colors):
                                for _hole, _color_spec in zip(_holes_list, _colors):
                                    if isinstance(_color_spec, str):
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                    else:
                                        _color_dict[_hole] = Color(_color_spec, space='rgb')
                                countdown_led.setColors(_color_dict)
                    else:
                        # Single color for all holes (Apparatus will handle hole parsing)
                        if isinstance(_colors, str):
                            _color = Color(_colors, space='rgb')
                        else:
                            _color = Color(_colors, space='rgb')
                        countdown_led.setHoleLights('none', _color)
                
                # if countdown_led is active this frame...
                if countdown_led.status == STARTED:
                    # update params
                    pass
                    
                # Run 'Each Frame' code from countdown_code
                # Check if it's time to update the countdown
                if countdown_last_update is None:
                    countdown_last_update = t  # t is the routine timer
                
                if t - countdown_last_update >= countdown_interval:
                    # Decrease the number of active lights
                    countdown_current_index -= 1
                    countdown_last_update = t
                    
                    if countdown_current_index > 0:
                        # Turn on the remaining lights
                        active_holes = countdown_holes[:countdown_current_index]
                        countdown_led.setHoleLights(active_holes, Color('white'))
                        # Turn off the rest
                        inactive_holes = countdown_holes[countdown_current_index:]
                        countdown_led.turnOffHoleLights(inactive_holes)
                    else:
                        # All lights off
                        countdown_led.turnOffHoleLights('outer')
                        continueRoutine = False
                
                # *countdown_text* updates
                
                # if countdown_text is starting this frame...
                if countdown_text.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_text.frameNStart = frameN  # exact frame index
                    countdown_text.tStart = t  # local t and not account for scr refresh
                    countdown_text.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_text, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'countdown_text.started')
                    # update status
                    countdown_text.status = STARTED
                    countdown_text.setAutoDraw(True)
                
                # if countdown_text is active this frame...
                if countdown_text.status == STARTED:
                    # update params
                    countdown_text.setText(countdown_current_index, log=False)
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=countdown,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    countdown.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if countdown.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in countdown.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "countdown" ---
            for thisComponent in countdown.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for countdown
            countdown.tStop = globalClock.getTime(format='float')
            countdown.tStopRefresh = tThisFlipGlobal
            thisExp.addData('countdown.stopped', countdown.tStop)
            if False:
                countdown_led.turnOffHoleLights('none')
            # the Routine "countdown" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # set up handler to look after randomisation of conditions etc
            levelLoop = data.TrialHandler2(
                name='levelLoop',
                nReps=6, 
                method='random', 
                extraInfo=expInfo, 
                originPath=-1, 
                trialList=[None], 
                seed=None, 
                isTrials=True, 
            )
            thisExp.addLoop(levelLoop)  # add the loop to the experiment
            thisLevelLoop = levelLoop.trialList[0]  # so we can initialise stimuli with some values
            # abbreviate parameter names if possible (e.g. rgb = thisLevelLoop.rgb)
            if thisLevelLoop != None:
                for paramName in thisLevelLoop:
                    globals()[paramName] = thisLevelLoop[paramName]
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            
            for thisLevelLoop in levelLoop:
                levelLoop.status = STARTED
                if hasattr(thisLevelLoop, 'status'):
                    thisLevelLoop.status = STARTED
                currentLoop = levelLoop
                thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # abbreviate parameter names if possible (e.g. rgb = thisLevelLoop.rgb)
                if thisLevelLoop != None:
                    for paramName in thisLevelLoop:
                        globals()[paramName] = thisLevelLoop[paramName]
                
                # --- Prepare to start Routine "target_presentation" ---
                # create an object to store info about Routine target_presentation
                target_presentation = data.Routine(
                    name='target_presentation',
                    components=[targetLED, practiceForce, targetText],
                )
                target_presentation.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from ColorCode
                # index auf 0 setzen
                index = 0
                # Target Color configuration
                holes = list(range(8))  # inner holes (0-7)
                
                #set up which trials show a target
                targetPresentTrials = random.sample(range(NUM_PALETTES), NUM_TARGETS_PER_REP)
                currentTrial = 0
                
                # Reset hits/misses/fa/cr for dprime calculation later in slider Routine
                hits = 0
                misses = 0
                false_alarms = 0
                correct_rejections = 0
                
                # Run 'Begin Routine' code from audioPracticeCode
                # Begin Routine
                with _state_lock:
                    _target_amp = 0.0   # definiert stumm
                # Begin Routine
                toneState = 0
                _lastSwitchT = -1e9   # erlaubt sofortigen Wechsel
                
                maxForce = mvc_max_experimental
                currentMVCLevel = mvcLevel
                targetForce = currentMVCLevel * maxForce
                
                tolerance = 15.0
                lower_threshold = targetForce - tolerance
                upper_threshold = targetForce + tolerance
                
                #print("Upper threshold set:", upper_threshold)
                #print("lower threshold set:", lower_threshold)
                targetColorText = f"Target color is: {targetColor}"
                mvcLevelText = f"Target MVC Level is: {currentMVCLevel:.2f}"
                
                #print("MVC level:", currentMVCLevel)
                
                targetText.setText(f"Color: {targetColor}, Force: {practiceForce.whiteForce}")
                # store start times for target_presentation
                target_presentation.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                target_presentation.tStart = globalClock.getTime(format='float')
                target_presentation.status = STARTED
                thisExp.addData('target_presentation.started', target_presentation.tStart)
                target_presentation.maxDuration = None
                # keep track of which components have finished
                target_presentationComponents = target_presentation.components
                for thisComponent in target_presentation.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "target_presentation" ---
                thisExp.currentRoutine = target_presentation
                target_presentation.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine and routineTimer.getTime() < 3.0:
                    # if trial has changed, end Routine now
                    if hasattr(thisLevelLoop, 'status') and thisLevelLoop.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    
                    # if targetLED is starting this frame...
                    if targetLED.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        targetLED.frameNStart = frameN  # exact frame index
                        targetLED.tStart = t  # local t and not account for scr refresh
                        targetLED.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(targetLED, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('targetLED.started', t)
                        # update status
                        targetLED.status = STARTED
                        # Handle colors: single or multiple
                        _colors = ''
                        
                        # Detect if we have multiple colors (list of lists/tuples or list of strings)
                        _is_multiple_colors = (
                            isinstance(_colors, (list, tuple)) and
                            len(_colors) > 0 and
                            (isinstance(_colors[0], (list, tuple)) or isinstance(_colors[0], str))
                        )
                        
                        if _is_multiple_colors:
                            # Multiple colors per hole - use setColors with mapping
                            # Note: holes parameter must match the number of colors
                            _holes_spec = 'none'
                            _color_dict = {}
                            # If holes is a keyword, we can't map individual colors; warn user
                            if isinstance(_holes_spec, str):
                                logging.warning('Cannot use keyword holes with multiple colors. Use explicit list of holes instead.')
                            else:
                                # Map each hole to its color
                                _holes_list = [_holes_spec] if isinstance(_holes_spec, int) else list(_holes_spec)
                                if len(_holes_list) == len(_colors):
                                    for _hole, _color_spec in zip(_holes_list, _colors):
                                        if isinstance(_color_spec, str):
                                            _color_dict[_hole] = Color(_color_spec, space='rgb')
                                        else:
                                            _color_dict[_hole] = Color(_color_spec, space='rgb')
                                    targetLED.setColors(_color_dict)
                        else:
                            # Single color for all holes (Apparatus will handle hole parsing)
                            if isinstance(_colors, str):
                                _color = Color(_colors, space='rgb')
                            else:
                                _color = Color(_colors, space='rgb')
                            targetLED.setHoleLights('none', _color)
                    
                    # if targetLED is active this frame...
                    if targetLED.status == STARTED:
                        # update params
                        pass
                        
                    
                    # if targetLED is stopping this frame...
                    if targetLED.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > targetLED.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            targetLED.tStop = t  # not accounting for scr refresh
                            targetLED.tStopRefresh = tThisFlipGlobal  # on global time
                            targetLED.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.addData('targetLED.stopped', t)
                            # update status
                            targetLED.status = FINISHED
                            if True:
                                targetLED.turnOffHoleLights('none')
                    # Run 'Each Frame' code from ColorCode
                    # timing in each frame:
                    # t = Zeit seit Beginn der Routine (in Sekunden)
                    if t < 2.0:
                        # LEDs AN
                        targetLED.setHoleLights(holes, Color(eval(targetColor), 'rgb255'))
                    else:
                        # LEDs AUS
                        targetLED.turnOffAllLights()
                    
                    # if practiceForce is starting this frame...
                    if practiceForce.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        practiceForce.frameNStart = frameN  # exact frame index
                        practiceForce.tStart = t  # local t and not account for scr refresh
                        practiceForce.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(practiceForce, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('practiceForce.started', t)
                        # update status
                        practiceForce.status = STARTED
                        practiceForce.startForceMeasurement(50, 'white')
                    
                    # if practiceForce is active this frame...
                    if practiceForce.status == STARTED:
                        # update params
                        pass
                        practiceForce.updateForceMeasurement()
                        if False and practiceForce.getNumberOfResponses() > 0:
                            practiceForce.stopForceMeasurement()
                            continueRoutine = False
                    
                    # if practiceForce is stopping this frame...
                    if practiceForce.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > practiceForce.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            practiceForce.tStop = t  # not accounting for scr refresh
                            practiceForce.tStopRefresh = tThisFlipGlobal  # on global time
                            practiceForce.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.addData('practiceForce.stopped', t)
                            # update status
                            practiceForce.status = FINISHED
                            practiceForce.stopForceMeasurement()
                    # Run 'Each Frame' code from audioPracticeCode
                    tNow = t   # t = Zeit seit Routinenstart (automatisch verfügbar)
                    
                    if practiceForce.whiteForce is not None:
                    
                        # propose next state (ONLY upper threshold)
                        if practiceForce.whiteForce > upper_threshold:
                            proposed = 2   # high tone
                        elif practiceForce.whiteForce < lower_threshold:
                            proposed = 1   # zu niedrig    
                        else:
                            proposed = 0   # mute
                    
                        # anti-chatter logic
                        if proposed != toneState and (tNow - _lastSwitchT) >= stateHold:
                            toneState = proposed
                            _lastSwitchT = tNow
                    
                            # apply state
                            if toneState == 2:
                                freq, amp = 880.0, AMP_MAX
                            elif toneState == 1:
                                freq, amp = 440.0, AMP_MAX
                            else:
                                freq, amp = 0.0, 0.0  # muted
                    
                            with _state_lock:
                                _target_freq = freq
                                _target_amp  = amp
                    else:
                        print("Force is None!")
                    # debugging for forces
                    #print("force:", force, "upper_threshold:", upper_threshold)
                    
                    
                    # *targetText* updates
                    
                    # if targetText is starting this frame...
                    if targetText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        targetText.frameNStart = frameN  # exact frame index
                        targetText.tStart = t  # local t and not account for scr refresh
                        targetText.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(targetText, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'targetText.started')
                        # update status
                        targetText.status = STARTED
                        targetText.setAutoDraw(True)
                    
                    # if targetText is active this frame...
                    if targetText.status == STARTED:
                        # update params
                        pass
                    
                    # if targetText is stopping this frame...
                    if targetText.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > targetText.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            targetText.tStop = t  # not accounting for scr refresh
                            targetText.tStopRefresh = tThisFlipGlobal  # on global time
                            targetText.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'targetText.stopped')
                            # update status
                            targetText.status = FINISHED
                            targetText.setAutoDraw(False)
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=target_presentation,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        target_presentation.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if target_presentation.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in target_presentation.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "target_presentation" ---
                for thisComponent in target_presentation.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for target_presentation
                target_presentation.tStop = globalClock.getTime(format='float')
                target_presentation.tStopRefresh = tThisFlipGlobal
                thisExp.addData('target_presentation.stopped', target_presentation.tStop)
                if True:
                    targetLED.turnOffHoleLights('none')
                # Run 'End Routine' code from ColorCode
                targetLED.turnOffAllLights()
                levelLoop.addData('practiceForce.rate', 50)
                levelLoop.addData('practiceForce.device', 'white')
                levelLoop.addData('practiceForce.maxWhiteForce', practiceForce.maxWhiteForce)
                levelLoop.addData('practiceForce.maxBlueForce', practiceForce.maxBlueForce)
                if True:
                    _raw_path = thisExp.dataFileName + '_force_long.tsv'
                    _write_header = not os.path.exists(_raw_path)
                    _loop = levelLoop
                    _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                    _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                    _identifier = practiceForce if practiceForce != None else ''
                    _times = practiceForce.times
                    _white = practiceForce.whiteForceValues
                    _blue = practiceForce.blueForceValues
                    _n = max(len(_times), len(_white), len(_blue))
                    with open(_raw_path, 'a', encoding='utf-8') as _f:
                        if _write_header:
                            _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	time	white_force	blue_force\n')
                        for _i in range(_n):
                            _t = _times[_i] if _i < len(_times) else ''
                            _w = _white[_i] if _i < len(_white) else ''
                            _b = _blue[_i] if _i < len(_blue) else ''
                            _row = [
                                expInfo.get("participant", ""),
                                expInfo.get("session", ""),
                                'target_presentation',
                                'practiceForce',
                                _trial_index,
                                _trial_name,
                                _identifier,
                                _i,
                                _t,
                                _w,
                                _b,
                            ]
                            _f.write('	'.join(str(_v) for _v in _row) + '\n')
                # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
                if target_presentation.maxDurationReached:
                    routineTimer.addTime(-target_presentation.maxDuration)
                elif target_presentation.forceEnded:
                    routineTimer.reset()
                else:
                    routineTimer.addTime(-3.000000)
                
                # set up handler to look after randomisation of conditions etc
                paletteLoop = data.TrialHandler2(
                    name='paletteLoop',
                    nReps=10, 
                    method='random', 
                    extraInfo=expInfo, 
                    originPath=-1, 
                    trialList=[None], 
                    seed=None, 
                    isTrials=True, 
                )
                thisExp.addLoop(paletteLoop)  # add the loop to the experiment
                thisPaletteLoop = paletteLoop.trialList[0]  # so we can initialise stimuli with some values
                # abbreviate parameter names if possible (e.g. rgb = thisPaletteLoop.rgb)
                if thisPaletteLoop != None:
                    for paramName in thisPaletteLoop:
                        globals()[paramName] = thisPaletteLoop[paramName]
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                for thisPaletteLoop in paletteLoop:
                    paletteLoop.status = STARTED
                    if hasattr(thisPaletteLoop, 'status'):
                        thisPaletteLoop.status = STARTED
                    currentLoop = paletteLoop
                    thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                    if thisSession is not None:
                        # if running in a Session with a Liaison client, send data up to now
                        thisSession.sendExperimentData()
                    # abbreviate parameter names if possible (e.g. rgb = thisPaletteLoop.rgb)
                    if thisPaletteLoop != None:
                        for paramName in thisPaletteLoop:
                            globals()[paramName] = thisPaletteLoop[paramName]
                    
                    # --- Prepare to start Routine "task" ---
                    # create an object to store info about Routine task
                    task = data.Routine(
                        name='task',
                        components=[taskReed, taskLED, taskText, taskForce],
                    )
                    task.status = NOT_STARTED
                    continueRoutine = True
                    # update component parameters for each repeat
                    # Run 'Begin Routine' code from distractorSamplingCode
                    target = Color(eval(targetColor), 'rgb255')
                    # Setup stimulus
                    # Parameters for a cognitive task trial:
                    # targetColor
                    # deltaE
                    candidateHoles = random.sample(range(0, 8), N_DISTRACTORS)
                    innerColors = {i: Color([0, 0, 0], 'rgb255') for i in range(0, 8)}
                    
                    # Calculate distractor colors
                    #deltaE = currentDeltaE
                    targetColorNorm = (target.rgb255[0] / 255, target.rgb255[1] / 255, target.rgb255[2] / 255)
                    generatedDistractors = generate_distractors(targetColorNorm, int(deltaE), N_DISTRACTORS)
                    
                    # Convert distractors from 0-1 to 0-255
                    distractorColors = {}
                    for i in range(N_DISTRACTORS):
                        hole = candidateHoles[i]
                        gen = generatedDistractors[i]
                        distractorColors[hole] = Color([int(gen[0] * 255), int(gen[1] * 255), int(gen[2] * 255)], 'rgb255')
                    
                    # Determine if the current trial should present a target and set the target color if so
                    targetPresent = currentTrial in targetPresentTrials
                    if targetPresent:
                        targetHole = random.choice(candidateHoles)
                        distractorColors[targetHole] = target
                        currentLoop.addData('targetPresent', True)
                        currentLoop.addData('targetHole', targetHole)
                    else:
                        targetHole = None
                        currentLoop.addData('targetPresent', False)
                        currentLoop.addData('targetHole', None)
                    taskText.setText(f"Palette: {index}, deltaE: {deltaE}, Kraftlevel: {mvcLevel}"
                    )
                    # Run 'Begin Routine' code from taskReedCode
                    #taskReed.startReedMeasurement(100, 1)
                    # Run 'Begin Routine' code from audioCode
                    # Begin Routine
                    with _state_lock:
                        _target_amp = 0.0   # definiert stumm
                    # Begin Routine
                    toneState = 0
                    _lastSwitchT = -1e9   # erlaubt sofortigen Wechsel
                    
                    maxForce = mvc_max_experimental
                    currentMVCLevel = mvcLevel
                    targetForce = currentMVCLevel * maxForce
                    
                    tolerance = 15.0
                    lower_threshold = targetForce - tolerance
                    upper_threshold = targetForce + tolerance
                    
                    #print("Upper threshold set:", upper_threshold)
                    #print("lower threshold set:", lower_threshold)
                    targetColorText = f"Target color is: {targetColor}"
                    mvcLevelText = f"Target MVC Level is: {currentMVCLevel:.2f}"
                    
                    #print("MVC level:", currentMVCLevel)
                    
                    # store start times for task
                    task.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                    task.tStart = globalClock.getTime(format='float')
                    task.status = STARTED
                    thisExp.addData('task.started', task.tStart)
                    task.maxDuration = None
                    # keep track of which components have finished
                    taskComponents = task.components
                    for thisComponent in task.components:
                        thisComponent.tStart = None
                        thisComponent.tStop = None
                        thisComponent.tStartRefresh = None
                        thisComponent.tStopRefresh = None
                        if hasattr(thisComponent, 'status'):
                            thisComponent.status = NOT_STARTED
                    # reset timers
                    t = 0
                    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                    frameN = -1
                    
                    # --- Run Routine "task" ---
                    thisExp.currentRoutine = task
                    task.forceEnded = routineForceEnded = not continueRoutine
                    while continueRoutine and routineTimer.getTime() < 1.416:
                        # if trial has changed, end Routine now
                        if hasattr(thisPaletteLoop, 'status') and thisPaletteLoop.status == STOPPING:
                            continueRoutine = False
                        # get current time
                        t = routineTimer.getTime()
                        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                        # update/draw components on each frame
                        
                        # if taskReed is starting this frame...
                        if taskReed.status == NOT_STARTED and t >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            taskReed.frameNStart = frameN  # exact frame index
                            taskReed.tStart = t  # local t and not account for scr refresh
                            taskReed.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(taskReed, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.addData('taskReed.started', t)
                            # update status
                            taskReed.status = STARTED
                            taskReed.startReedMeasurement(100, 'all')
                        
                        # if taskReed is active this frame...
                        if taskReed.status == STARTED:
                            # update params
                            pass
                            taskReed.updateReedMeasurement()
                            if False and len(taskReed.reedTimes) > 0:
                                taskReed.stopReedMeasurement()
                                continueRoutine = False
                        
                        # if taskReed is stopping this frame...
                        if taskReed.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > taskReed.tStartRefresh + 1.416-frameTolerance:
                                # keep track of stop time/frame for later
                                taskReed.tStop = t  # not accounting for scr refresh
                                taskReed.tStopRefresh = tThisFlipGlobal  # on global time
                                taskReed.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('taskReed.stopped', t)
                                # update status
                                taskReed.status = FINISHED
                                taskReed.stopReedMeasurement()
                        
                        # if taskLED is starting this frame...
                        if taskLED.status == NOT_STARTED and t >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            taskLED.frameNStart = frameN  # exact frame index
                            taskLED.tStart = t  # local t and not account for scr refresh
                            taskLED.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(taskLED, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.addData('taskLED.started', t)
                            # update status
                            taskLED.status = STARTED
                            # Handle colors: single or multiple
                            _colors = 'black'
                            
                            # Detect if we have multiple colors (list of lists/tuples or list of strings)
                            _is_multiple_colors = (
                                isinstance(_colors, (list, tuple)) and
                                len(_colors) > 0 and
                                (isinstance(_colors[0], (list, tuple)) or isinstance(_colors[0], str))
                            )
                            
                            if _is_multiple_colors:
                                # Multiple colors per hole - use setColors with mapping
                                # Note: holes parameter must match the number of colors
                                _holes_spec = 'none'
                                _color_dict = {}
                                # If holes is a keyword, we can't map individual colors; warn user
                                if isinstance(_holes_spec, str):
                                    logging.warning('Cannot use keyword holes with multiple colors. Use explicit list of holes instead.')
                                else:
                                    # Map each hole to its color
                                    _holes_list = [_holes_spec] if isinstance(_holes_spec, int) else list(_holes_spec)
                                    if len(_holes_list) == len(_colors):
                                        for _hole, _color_spec in zip(_holes_list, _colors):
                                            if isinstance(_color_spec, str):
                                                _color_dict[_hole] = Color(_color_spec, space='rgb')
                                            else:
                                                _color_dict[_hole] = Color(_color_spec, space='rgb')
                                        taskLED.setColors(_color_dict)
                            else:
                                # Single color for all holes (Apparatus will handle hole parsing)
                                if isinstance(_colors, str):
                                    _color = Color(_colors, space='rgb')
                                else:
                                    _color = Color(_colors, space='rgb')
                                taskLED.setHoleLights('none', _color)
                        
                        # if taskLED is active this frame...
                        if taskLED.status == STARTED:
                            # update params
                            pass
                            
                        
                        # if taskLED is stopping this frame...
                        if taskLED.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > taskLED.tStartRefresh + 0.416-frameTolerance:
                                # keep track of stop time/frame for later
                                taskLED.tStop = t  # not accounting for scr refresh
                                taskLED.tStopRefresh = tThisFlipGlobal  # on global time
                                taskLED.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('taskLED.stopped', t)
                                # update status
                                taskLED.status = FINISHED
                                if True:
                                    taskLED.turnOffHoleLights('none')
                        # Run 'Each Frame' code from distractorSamplingCode
                        # timing in each frame:
                        # t ist die Zeit seit Beginn der Routine (in Sekunden)
                        if t < 0.417:
                            # LEDs AN
                            innerColors.update(distractorColors)
                            taskLED.setColors(innerColors)
                        else:
                            # LEDs AUS
                            taskLED.turnOffAllLights()
                            
                        # Reedkontakte auslesen
                        holes = taskReed.reedHoles
                        has_target = targetHole is not None
                        has_response = len(holes) > 0
                        
                        hit  = int(has_target and targetHole in holes)
                        fa   = int(not has_target and has_response)
                        miss = int(has_target and not has_response)
                        cr   = int(not has_target and not has_response)
                        
                        # *taskText* updates
                        
                        # if taskText is starting this frame...
                        if taskText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            taskText.frameNStart = frameN  # exact frame index
                            taskText.tStart = t  # local t and not account for scr refresh
                            taskText.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(taskText, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'taskText.started')
                            # update status
                            taskText.status = STARTED
                            taskText.setAutoDraw(True)
                        
                        # if taskText is active this frame...
                        if taskText.status == STARTED:
                            # update params
                            pass
                        
                        # if taskText is stopping this frame...
                        if taskText.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > taskText.tStartRefresh + 1.416-frameTolerance:
                                # keep track of stop time/frame for later
                                taskText.tStop = t  # not accounting for scr refresh
                                taskText.tStopRefresh = tThisFlipGlobal  # on global time
                                taskText.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.timestampOnFlip(win, 'taskText.stopped')
                                # update status
                                taskText.status = FINISHED
                                taskText.setAutoDraw(False)
                        # Run 'Each Frame' code from taskReedCode
                        #taskReed.updateReedMeasurement()
                        
                        # if taskForce is starting this frame...
                        if taskForce.status == NOT_STARTED and t >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            taskForce.frameNStart = frameN  # exact frame index
                            taskForce.tStart = t  # local t and not account for scr refresh
                            taskForce.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(taskForce, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.addData('taskForce.started', t)
                            # update status
                            taskForce.status = STARTED
                            taskForce.startForceMeasurement(50, 'white')
                        
                        # if taskForce is active this frame...
                        if taskForce.status == STARTED:
                            # update params
                            pass
                            taskForce.updateForceMeasurement()
                            if False and taskForce.getNumberOfResponses() > 0:
                                taskForce.stopForceMeasurement()
                                continueRoutine = False
                        
                        # if taskForce is stopping this frame...
                        if taskForce.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > taskForce.tStartRefresh + 1.416-frameTolerance:
                                # keep track of stop time/frame for later
                                taskForce.tStop = t  # not accounting for scr refresh
                                taskForce.tStopRefresh = tThisFlipGlobal  # on global time
                                taskForce.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('taskForce.stopped', t)
                                # update status
                                taskForce.status = FINISHED
                                taskForce.stopForceMeasurement()
                        # Run 'Each Frame' code from audioCode
                        tNow = t   # t = Zeit seit Routinenstart (automatisch verfügbar)
                        
                        if taskForce.whiteForce is not None:
                        
                            # propose next state (ONLY upper threshold)
                            if taskForce.whiteForce > upper_threshold:
                                proposed = 2   # high tone
                            elif taskForce.whiteForce < lower_threshold:
                                proposed = 1   # zu niedrig    
                            else:
                                proposed = 0   # mute
                        
                            # anti-chatter logic
                            if proposed != toneState and (tNow - _lastSwitchT) >= stateHold:
                                toneState = proposed
                                _lastSwitchT = tNow
                        
                                # apply state
                                if toneState == 2:
                                    freq, amp = 880.0, AMP_MAX
                                elif toneState == 1:
                                    freq, amp = 440.0, AMP_MAX
                                else:
                                    freq, amp = 0.0, 0.0  # muted
                        
                                with _state_lock:
                                    _target_freq = freq
                                    _target_amp  = amp
                        else:
                            print("Force is None!")
                        # debugging for forces
                        #print("force:", force, "upper_threshold:", upper_threshold)
                        
                        
                        # check for quit (typically the Esc key)
                        if defaultKeyboard.getKeys(keyList=["escape"]):
                            thisExp.status = FINISHED
                        if thisExp.status == FINISHED or endExpNow:
                            endExperiment(thisExp, win=win)
                            return
                        # pause experiment here if requested
                        if thisExp.status == PAUSED:
                            pauseExperiment(
                                thisExp=thisExp, 
                                win=win, 
                                timers=[routineTimer, globalClock], 
                                currentRoutine=task,
                            )
                            # skip the frame we paused on
                            continue
                        
                        # has a Component requested the Routine to end?
                        if not continueRoutine:
                            task.forceEnded = routineForceEnded = True
                        # has the Routine been forcibly ended?
                        if task.forceEnded or routineForceEnded:
                            break
                        # has every Component finished?
                        continueRoutine = False
                        for thisComponent in task.components:
                            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                                continueRoutine = True
                                break  # at least one component has not yet finished
                        
                        # refresh the screen
                        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                            win.flip()
                    
                    # --- Ending Routine "task" ---
                    for thisComponent in task.components:
                        if hasattr(thisComponent, "setAutoDraw"):
                            thisComponent.setAutoDraw(False)
                    # store stop times for task
                    task.tStop = globalClock.getTime(format='float')
                    task.tStopRefresh = tThisFlipGlobal
                    thisExp.addData('task.stopped', task.tStop)
                    # make sure reed measurement is stopped
                    if taskReed.status == STARTED:
                        taskReed.stopReedMeasurement()
                    paletteLoop.addData('taskReed.rate', 100)
                    paletteLoop.addData('taskReed.holes', 'all')
                    paletteLoop.addData('taskReed.reedTimes', taskReed.reedTimes)
                    paletteLoop.addData('taskReed.reedHoles', taskReed.reedHoles)
                    paletteLoop.addData('taskReed.reedActions', taskReed.reedActions)
                    paletteLoop.addData('taskReed.reedSummary', taskReed.reedSummary)
                    if True:
                        taskLED.turnOffHoleLights('none')
                    # Run 'End Routine' code from distractorSamplingCode
                    # Index um eins hochzählen, damit richtige Palette angezeigt wird
                    index += 1
                    currentTrial += 1
                    
                    # Hochzählen der hits, fa, cr & misses
                    if hit:
                        hits += 1
                    if miss: 
                        misses += 1
                    if fa:
                        false_alarms += 1
                    if cr:
                        correct_rejections += 1
                    
                    #Daten anhängen
                    currentLoop.addData ('hit', hit)
                    currentLoop.addData ('falsealarm', fa)
                    currentLoop.addData ('correct rejection', cr)
                    currentLoop.addData ('miss', miss)
                    
                    # Run 'End Routine' code from taskReedCode
                    #taskReed.stopReedMeasurement()
                    paletteLoop.addData('taskForce.rate', 50)
                    paletteLoop.addData('taskForce.device', 'white')
                    paletteLoop.addData('taskForce.maxWhiteForce', taskForce.maxWhiteForce)
                    paletteLoop.addData('taskForce.maxBlueForce', taskForce.maxBlueForce)
                    if True:
                        _raw_path = thisExp.dataFileName + '_force_long.tsv'
                        _write_header = not os.path.exists(_raw_path)
                        _loop = paletteLoop
                        _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                        _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                        _identifier = taskForce if taskForce != None else ''
                        _times = taskForce.times
                        _white = taskForce.whiteForceValues
                        _blue = taskForce.blueForceValues
                        _n = max(len(_times), len(_white), len(_blue))
                        with open(_raw_path, 'a', encoding='utf-8') as _f:
                            if _write_header:
                                _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	time	white_force	blue_force\n')
                            for _i in range(_n):
                                _t = _times[_i] if _i < len(_times) else ''
                                _w = _white[_i] if _i < len(_white) else ''
                                _b = _blue[_i] if _i < len(_blue) else ''
                                _row = [
                                    expInfo.get("participant", ""),
                                    expInfo.get("session", ""),
                                    'task',
                                    'taskForce',
                                    _trial_index,
                                    _trial_name,
                                    _identifier,
                                    _i,
                                    _t,
                                    _w,
                                    _b,
                                ]
                                _f.write('	'.join(str(_v) for _v in _row) + '\n')
                    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
                    if task.maxDurationReached:
                        routineTimer.addTime(-task.maxDuration)
                    elif task.forceEnded:
                        routineTimer.reset()
                    else:
                        routineTimer.addTime(-1.416000)
                    # mark thisPaletteLoop as finished
                    if hasattr(thisPaletteLoop, 'status'):
                        thisPaletteLoop.status = FINISHED
                    # if awaiting a pause, pause now
                    if paletteLoop.status == PAUSED:
                        thisExp.status = PAUSED
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[globalClock], 
                        )
                        # once done pausing, restore running status
                        paletteLoop.status = STARTED
                    thisExp.nextEntry()
                    
                # completed 10 repeats of 'paletteLoop'
                paletteLoop.status = FINISHED
                
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                # --- Prepare to start Routine "postTask" ---
                # create an object to store info about Routine postTask
                postTask = data.Routine(
                    name='postTask',
                    components=[dprimeText, dprimeKeyResp],
                )
                postTask.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from dprimeCode
                #dprime Calculation
                H = hits + misses
                F = false_alarms + correct_rejections
                
                hit_rate = (hits+0.5)/(H+1) if H>0 else 0.5
                fa_rate = (false_alarms+0.5)/(F+1) if F>0 else 0.5
                dprime = norm.ppf(hit_rate) - norm.ppf(fa_rate)
                
                currentLoop.addData('dprime', dprime)
                # create starting attributes for dprimeKeyResp
                dprimeKeyResp.keys = []
                dprimeKeyResp.rt = []
                _dprimeKeyResp_allKeys = []
                # store start times for postTask
                postTask.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                postTask.tStart = globalClock.getTime(format='float')
                postTask.status = STARTED
                thisExp.addData('postTask.started', postTask.tStart)
                postTask.maxDuration = None
                # keep track of which components have finished
                postTaskComponents = postTask.components
                for thisComponent in postTask.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "postTask" ---
                thisExp.currentRoutine = postTask
                postTask.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisLevelLoop, 'status') and thisLevelLoop.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    
                    # *dprimeText* updates
                    
                    # if dprimeText is starting this frame...
                    if dprimeText.status == NOT_STARTED and tThisFlip >= 0-frameTolerance:
                        # keep track of start time/frame for later
                        dprimeText.frameNStart = frameN  # exact frame index
                        dprimeText.tStart = t  # local t and not account for scr refresh
                        dprimeText.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(dprimeText, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'dprimeText.started')
                        # update status
                        dprimeText.status = STARTED
                        dprimeText.setAutoDraw(True)
                    
                    # if dprimeText is active this frame...
                    if dprimeText.status == STARTED:
                        # update params
                        dprimeText.setText('Last dprime: ' + str(dprime) + '\n'
                        'Hits: ' + str(hits) + '\n'
                        'Misses: ' + str(misses) + '\n'
                        'False alarms: ' + str(false_alarms) + '\n'
                        'Correct rejections: ' + str(correct_rejections) + '\n', log=False)
                    
                    # *dprimeKeyResp* updates
                    waitOnFlip = False
                    
                    # if dprimeKeyResp is starting this frame...
                    if dprimeKeyResp.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        dprimeKeyResp.frameNStart = frameN  # exact frame index
                        dprimeKeyResp.tStart = t  # local t and not account for scr refresh
                        dprimeKeyResp.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(dprimeKeyResp, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'dprimeKeyResp.started')
                        # update status
                        dprimeKeyResp.status = STARTED
                        # keyboard checking is just starting
                        waitOnFlip = True
                        win.callOnFlip(dprimeKeyResp.clock.reset)  # t=0 on next screen flip
                        win.callOnFlip(dprimeKeyResp.clearEvents, eventType='keyboard')  # clear events on next screen flip
                    if dprimeKeyResp.status == STARTED and not waitOnFlip:
                        theseKeys = dprimeKeyResp.getKeys(keyList=['space'], ignoreKeys=["escape"], waitRelease=False)
                        _dprimeKeyResp_allKeys.extend(theseKeys)
                        if len(_dprimeKeyResp_allKeys):
                            dprimeKeyResp.keys = _dprimeKeyResp_allKeys[-1].name  # just the last key pressed
                            dprimeKeyResp.rt = _dprimeKeyResp_allKeys[-1].rt
                            dprimeKeyResp.duration = _dprimeKeyResp_allKeys[-1].duration
                            # a response ends the routine
                            continueRoutine = False
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=postTask,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        postTask.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if postTask.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in postTask.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "postTask" ---
                for thisComponent in postTask.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for postTask
                postTask.tStop = globalClock.getTime(format='float')
                postTask.tStopRefresh = tThisFlipGlobal
                thisExp.addData('postTask.stopped', postTask.tStop)
                # check responses
                if dprimeKeyResp.keys in ['', [], None]:  # No response was made
                    dprimeKeyResp.keys = None
                levelLoop.addData('dprimeKeyResp.keys',dprimeKeyResp.keys)
                if dprimeKeyResp.keys != None:  # we had a response
                    levelLoop.addData('dprimeKeyResp.rt', dprimeKeyResp.rt)
                    levelLoop.addData('dprimeKeyResp.duration', dprimeKeyResp.duration)
                # the Routine "postTask" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                
                # set up handler to look after randomisation of conditions etc
                sliderLoop = data.TrialHandler2(
                    name='sliderLoop',
                    nReps=1, 
                    method='sequential', 
                    extraInfo=expInfo, 
                    originPath=-1, 
                    trialList=data.importConditions('sliderResponse.xlsx'), 
                    seed=None, 
                    isTrials=True, 
                )
                thisExp.addLoop(sliderLoop)  # add the loop to the experiment
                thisSliderLoop = sliderLoop.trialList[0]  # so we can initialise stimuli with some values
                # abbreviate parameter names if possible (e.g. rgb = thisSliderLoop.rgb)
                if thisSliderLoop != None:
                    for paramName in thisSliderLoop:
                        globals()[paramName] = thisSliderLoop[paramName]
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                for thisSliderLoop in sliderLoop:
                    sliderLoop.status = STARTED
                    if hasattr(thisSliderLoop, 'status'):
                        thisSliderLoop.status = STARTED
                    currentLoop = sliderLoop
                    thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                    if thisSession is not None:
                        # if running in a Session with a Liaison client, send data up to now
                        thisSession.sendExperimentData()
                    # abbreviate parameter names if possible (e.g. rgb = thisSliderLoop.rgb)
                    if thisSliderLoop != None:
                        for paramName in thisSliderLoop:
                            globals()[paramName] = thisSliderLoop[paramName]
                    
                    # --- Prepare to start Routine "slider" ---
                    # create an object to store info about Routine slider
                    slider = data.Routine(
                        name='slider',
                        components=[EffortRating, sliderText, keyRespSlider],
                    )
                    slider.status = NOT_STARTED
                    continueRoutine = True
                    # update component parameters for each repeat
                    EffortRating.reset()
                    sliderText.setText(f"{sliderResponse} Effort")
                    # create starting attributes for keyRespSlider
                    keyRespSlider.keys = []
                    keyRespSlider.rt = []
                    _keyRespSlider_allKeys = []
                    # store start times for slider
                    slider.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                    slider.tStart = globalClock.getTime(format='float')
                    slider.status = STARTED
                    thisExp.addData('slider.started', slider.tStart)
                    slider.maxDuration = None
                    # keep track of which components have finished
                    sliderComponents = slider.components
                    for thisComponent in slider.components:
                        thisComponent.tStart = None
                        thisComponent.tStop = None
                        thisComponent.tStartRefresh = None
                        thisComponent.tStopRefresh = None
                        if hasattr(thisComponent, 'status'):
                            thisComponent.status = NOT_STARTED
                    # reset timers
                    t = 0
                    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                    frameN = -1
                    
                    # --- Run Routine "slider" ---
                    thisExp.currentRoutine = slider
                    slider.forceEnded = routineForceEnded = not continueRoutine
                    while continueRoutine:
                        # if trial has changed, end Routine now
                        if hasattr(thisSliderLoop, 'status') and thisSliderLoop.status == STOPPING:
                            continueRoutine = False
                        # get current time
                        t = routineTimer.getTime()
                        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                        # update/draw components on each frame
                        
                        # *EffortRating* updates
                        
                        # if EffortRating is starting this frame...
                        if EffortRating.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            EffortRating.frameNStart = frameN  # exact frame index
                            EffortRating.tStart = t  # local t and not account for scr refresh
                            EffortRating.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(EffortRating, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'EffortRating.started')
                            # update status
                            EffortRating.status = STARTED
                            EffortRating.setAutoDraw(True)
                        
                        # if EffortRating is active this frame...
                        if EffortRating.status == STARTED:
                            # update params
                            pass
                        
                        # *sliderText* updates
                        
                        # if sliderText is starting this frame...
                        if sliderText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            sliderText.frameNStart = frameN  # exact frame index
                            sliderText.tStart = t  # local t and not account for scr refresh
                            sliderText.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(sliderText, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'sliderText.started')
                            # update status
                            sliderText.status = STARTED
                            sliderText.setAutoDraw(True)
                        
                        # if sliderText is active this frame...
                        if sliderText.status == STARTED:
                            # update params
                            pass
                        
                        # *keyRespSlider* updates
                        waitOnFlip = False
                        
                        # if keyRespSlider is starting this frame...
                        if keyRespSlider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            keyRespSlider.frameNStart = frameN  # exact frame index
                            keyRespSlider.tStart = t  # local t and not account for scr refresh
                            keyRespSlider.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(keyRespSlider, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'keyRespSlider.started')
                            # update status
                            keyRespSlider.status = STARTED
                            # keyboard checking is just starting
                            waitOnFlip = True
                            win.callOnFlip(keyRespSlider.clock.reset)  # t=0 on next screen flip
                            win.callOnFlip(keyRespSlider.clearEvents, eventType='keyboard')  # clear events on next screen flip
                        if keyRespSlider.status == STARTED and not waitOnFlip:
                            theseKeys = keyRespSlider.getKeys(keyList=['space'], ignoreKeys=["escape"], waitRelease=False)
                            _keyRespSlider_allKeys.extend(theseKeys)
                            if len(_keyRespSlider_allKeys):
                                keyRespSlider.keys = _keyRespSlider_allKeys[-1].name  # just the last key pressed
                                keyRespSlider.rt = _keyRespSlider_allKeys[-1].rt
                                keyRespSlider.duration = _keyRespSlider_allKeys[-1].duration
                                # a response ends the routine
                                continueRoutine = False
                        
                        # check for quit (typically the Esc key)
                        if defaultKeyboard.getKeys(keyList=["escape"]):
                            thisExp.status = FINISHED
                        if thisExp.status == FINISHED or endExpNow:
                            endExperiment(thisExp, win=win)
                            return
                        # pause experiment here if requested
                        if thisExp.status == PAUSED:
                            pauseExperiment(
                                thisExp=thisExp, 
                                win=win, 
                                timers=[routineTimer, globalClock], 
                                currentRoutine=slider,
                            )
                            # skip the frame we paused on
                            continue
                        
                        # has a Component requested the Routine to end?
                        if not continueRoutine:
                            slider.forceEnded = routineForceEnded = True
                        # has the Routine been forcibly ended?
                        if slider.forceEnded or routineForceEnded:
                            break
                        # has every Component finished?
                        continueRoutine = False
                        for thisComponent in slider.components:
                            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                                continueRoutine = True
                                break  # at least one component has not yet finished
                        
                        # refresh the screen
                        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                            win.flip()
                    
                    # --- Ending Routine "slider" ---
                    for thisComponent in slider.components:
                        if hasattr(thisComponent, "setAutoDraw"):
                            thisComponent.setAutoDraw(False)
                    # store stop times for slider
                    slider.tStop = globalClock.getTime(format='float')
                    slider.tStopRefresh = tThisFlipGlobal
                    thisExp.addData('slider.stopped', slider.tStop)
                    sliderLoop.addData('EffortRating.response', EffortRating.getRating())
                    sliderLoop.addData('EffortRating.rt', EffortRating.getRT())
                    # check responses
                    if keyRespSlider.keys in ['', [], None]:  # No response was made
                        keyRespSlider.keys = None
                    sliderLoop.addData('keyRespSlider.keys',keyRespSlider.keys)
                    if keyRespSlider.keys != None:  # we had a response
                        sliderLoop.addData('keyRespSlider.rt', keyRespSlider.rt)
                        sliderLoop.addData('keyRespSlider.duration', keyRespSlider.duration)
                    # the Routine "slider" was not non-slip safe, so reset the non-slip timer
                    routineTimer.reset()
                    # mark thisSliderLoop as finished
                    if hasattr(thisSliderLoop, 'status'):
                        thisSliderLoop.status = FINISHED
                    # if awaiting a pause, pause now
                    if sliderLoop.status == PAUSED:
                        thisExp.status = PAUSED
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[globalClock], 
                        )
                        # once done pausing, restore running status
                        sliderLoop.status = STARTED
                    thisExp.nextEntry()
                    
                # completed 1 repeats of 'sliderLoop'
                sliderLoop.status = FINISHED
                
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # mark thisLevelLoop as finished
                if hasattr(thisLevelLoop, 'status'):
                    thisLevelLoop.status = FINISHED
                # if awaiting a pause, pause now
                if levelLoop.status == PAUSED:
                    thisExp.status = PAUSED
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[globalClock], 
                    )
                    # once done pausing, restore running status
                    levelLoop.status = STARTED
                thisExp.nextEntry()
                
            # completed 6 repeats of 'levelLoop'
            levelLoop.status = FINISHED
            
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # mark thisBlockLoop as finished
            if hasattr(thisBlockLoop, 'status'):
                thisBlockLoop.status = FINISHED
            # if awaiting a pause, pause now
            if blockLoop.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                blockLoop.status = STARTED
            thisExp.nextEntry()
            
        # completed 3 repeats of 'blockLoop'
        blockLoop.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # mark thisDomainLoop as finished
        if hasattr(thisDomainLoop, 'status'):
            thisDomainLoop.status = FINISHED
        # if awaiting a pause, pause now
        if domainLoop.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            domainLoop.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'domainLoop'
    domainLoop.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # mark experiment as finished
    endExperiment(thisExp, win=win)


def saveData(thisExp):
    """
    Save data from this experiment
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    filename = thisExp.dataFileName
    # these shouldn't be strictly necessary (should auto-save)
    thisExp.saveAsWideText(filename + '.csv', delim='auto')
    thisExp.saveAsPickle(filename)


def endExperiment(thisExp, win=None):
    """
    End this experiment, performing final shut down operations.
    
    This function does NOT close the window or end the Python process - use `quit` for this.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    """
    # stop any playback components
    if thisExp.currentRoutine is not None:
        for comp in thisExp.currentRoutine.getPlaybackComponents():
            comp.stop()
    if win is not None:
        # remove autodraw from all current components
        win.clearAutoDraw()
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed
        win.flip()
    # return console logger level to WARNING
    logging.console.setLevel(logging.WARNING)
    # mark experiment handler as finished
    thisExp.status = FINISHED
    # run any 'at exit' functions
    for fcn in runAtExit:
        fcn()
    logging.flush()


def quit(thisExp, win=None, thisSession=None):
    """
    Fully quit, closing the window and ending the Python process.
    
    Parameters
    ==========
    win : psychopy.visual.Window
        Window to close.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    thisExp.abort()  # or data files will save again on exit
    # make sure everything is closed down
    if win is not None:
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed before quitting
        win.flip()
        win.close()
    logging.flush()
    if thisSession is not None:
        thisSession.stop()
    # terminate Python process
    core.quit()


# if running this experiment as a script...
if __name__ == '__main__':
    # call all functions in order
    expInfo = showExpInfoDlg(expInfo=expInfo)
    thisExp = setupData(expInfo=expInfo)
    logFile = setupLogging(filename=thisExp.dataFileName)
    win = setupWindow(expInfo=expInfo)
    setupDevices(expInfo=expInfo, thisExp=thisExp, win=win)
    run(
        expInfo=expInfo, 
        thisExp=thisExp, 
        win=win,
        globalClock='float'
    )
    saveData(thisExp=thisExp)
    quit(thisExp=thisExp, win=win)
