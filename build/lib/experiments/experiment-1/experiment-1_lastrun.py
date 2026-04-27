#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2026.1.3),
    on April 24, 2026, at 15:40
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
from psychopy_apparatus.hardware.apparatus import Apparatus
import os

# Run 'Before Experiment' code from setup_constants
# IMPORT MODULES ----
import random
import math
import numpy as np
import sounddevice as sd
import threading

# IMPORT SUBMODULES ----
# from scipy.stats import truncnorm, nur bei truncated normal distribution
from psychopy.colors import Color
from scipy.stats import norm
# Run 'Before Experiment' code from setup_color_utils
def rgb_to_lab(rgb):
    """
    Convert color from RGB to CIELAB space. 

    Parameters
    ----------
    rgb : tuple or list
        A tuple/list of three values representing the RGB color.
        Accepts either normalized (0-1) or rgb255 (0-255) format.
        Auto-detects format: if any value > 1, assumes 0-255 range.
    """
    # Auto-normalize if input is in 0-255 range
    if any(c > 1 for c in rgb):
        rgb = tuple(c / 255 for c in rgb)
    
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
    Generate n distractor colors that are approximately deltaE_mid away from target.
    
    Parameters
    ----------
    target_rgb : tuple/list
        RGB color in 0-1 (normalized) or 0-255 format (auto-detected).
    deltaE_mid : float
        Target Delta E 2000 distance from target color.
    n : int
        Number of distractor colors to generate.
    
    Returns
    -------
    list of lists
        Distractor colors in rgb255 format (0-255 ints).
    """
    target_lab = rgb_to_lab(target_rgb)
    distractors = []
    attempts = 0

    while len(distractors) < n and attempts < 50000:
        attempts += 1
        rgb = (random.random(), random.random(), random.random())
        lab = rgb_to_lab(rgb)
        dE = delta_e2000(target_lab, lab)

        if abs(dE - deltaE_mid) <= 1.5:
            distractors.append([int(c * 255) for c in rgb])  # Convert to rgb255

    if len(distractors) < n:
        print("WARNUNG: nicht genug Farben im DeltaE-Band gefunden.")
        while len(distractors) < n:
            distractors.append([int(c * 255) for c in (random.random(), random.random(), random.random())])

    return distractors
# --- Setup global variables (available in all functions) ---
# create a device manager to handle hardware (keyboards, mice, mirophones, speakers, etc.)
deviceManager = hardware.DeviceManager()
# ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
# store info about the experiment session
psychopyVersion = '2026.1.3'
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
        originPath='C:\\Users\\Maik Bieleke\\My Drive\\Labor\\psychopy-apparatus\\experiments\\experiment-1\\experiment-1_lastrun.py',
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
            winType='pyglet', allowGUI=True, allowStencil=False,
            monitor='testMonitor', color=(-1.0000, -1.0000, -1.0000), colorSpace='rgb',
            backgroundImage='', backgroundFit='none',
            blendMode='avg', useFBO=True,
            units='height',
            checkTiming=False  # we're going to do this ourselves in a moment
        )
    else:
        # if we have a window, just set the attributes which are safe to set
        win.color = (-1.0000, -1.0000, -1.0000)
        win.colorSpace = 'rgb'
        win.backgroundImage = ''
        win.backgroundFit = 'none'
        win.units = 'height'
    if expInfo is not None:
        # get/measure frame rate if not already in expInfo
        if win._monitorFrameRate is None:
            win._monitorFrameRate = win.getActualFrameRate(infoMsg='Experiment wird geladen...')
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
        debug=True
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
    
    # --- Initialize components for Routine "rr_setup" ---
    # Run 'Begin Experiment' code from setup_constants
    # DEFINITIONS AND CONSTANTS ----
    
    #nTrials = 12 # number of total repetitions
    
    NUM_MVC      = 3  # How many MVC trials to conduct
    NUM_DOMAINS  = 0 #1  # How often each domain is repeated
    NUM_BLOCKS   = 3  # How often each block within the domain is repeated
    NUM_LEVELS   = 6  # How often each level within the block is repeated
    NUM_PALETTES = 24 # How many palettes are generated per trial
    NUM_TARGETS  = 4  # How many targets appear in NUM_PALETTES palettes
    NUM_DISTRACTORS = 8
    
    MVC_PCT_MIN       = 0.10
    MVC_PCT_MAX       = 0.40
    MVC_PCT_COGNITIVE = 0.03
    DELTA_E_MIN       = 10
    DELTA_E_MAX       = 60
    DELTA_E_PHYSICAL  = 70
    
    # TARGET COLORS ----
    TARGET_COLORS_RGB255 = [
        Color([255, 0, 0], 'rgb255'),
        Color([0, 255, 0], 'rgb255'),
        Color([0, 0, 255], 'rgb255')
    ]
    
    INNER_HOLES = list(range(8))
    OUTER_HOLES = list(range(9, 21))
    
    # TIMING CONSTANTS ----
    PALETTE_DURATION_SEC = 0.416
    COUNTDOWN_STEP_SEC = 0.5
    
    # Run 'Begin Experiment' code from setup_audio
    global _state_lock, _target_freq, _target_amp, _cur_amp, _phase, _stream
    global proposed, toneState, _lastSwitchT
    
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
    
    
    # --- Initialize components for Routine "rr_countdown" ---
    
    countdown_lights = Apparatus('apparatus')
    countdown_display = visual.TextStim(win=win, name='countdown_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.2, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
    # --- Initialize components for Routine "rr_maxforce" ---
    # Run 'Begin Experiment' code from maxforce_code
    # Initialize value for maximum voluntary contraction (MVC)
    mvc = 0
    
    maxforce_lights = Apparatus(None)
    
    maxforce_force = Apparatus('apparatus')
    maxforce_display = visual.TextStim(win=win, name='maxforce_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-3.0);
    maxforce_continue = visual.ButtonStim(win, 
        text='Weiter', font='Arvo',
        pos=(0, -0.3),
        letterHeight=0.05,
        size=(0.25, 0.15), 
        ori=0.0
        ,borderWidth=0.0,
        fillColor=(-1.0000, -0.2157, -1.0000), borderColor=None,
        color='white', colorSpace='rgb',
        opacity=None,
        bold=True, italic=False,
        padding=None,
        anchor='center',
        name='maxforce_continue',
        depth=-4
    )
    maxforce_continue.buttonClock = core.Clock()
    
    # --- Initialize components for Routine "rr_domain" ---
    
    # --- Initialize components for Routine "rr_countdown" ---
    
    countdown_lights = Apparatus('apparatus')
    countdown_display = visual.TextStim(win=win, name='countdown_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.2, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
    # --- Initialize components for Routine "rr_target" ---
    
    target_lights = Apparatus(None)
    
    target_force = Apparatus(None)
    target_display = visual.TextStim(win=win, name='target_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    
    # --- Initialize components for Routine "rr_trial" ---
    
    trial_reed = Apparatus(None)
    
    trial_lights = Apparatus(None)
    
    trial_force = Apparatus(None)
    trial_display = visual.TextStim(win=win, name='trial_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "rr_feedback" ---
    feedback_keyboard = keyboard.Keyboard(deviceName='defaultKeyboard')
    feedback_display = visual.TextStim(win=win, name='feedback_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
    # --- Initialize components for Routine "rr_rating" ---
    rating_slider = visual.Slider(win=win, name='rating_slider',
        startValue=None, size=(1.0, 0.1), pos=(0, -0.2), units=win.units,
        labels=(0,1,2,3,4,5,6,7,8,9,10), ticks=(0,1,2,3,4,5,6,7,8,9,10), granularity=1.0,
        style='rating', styleTweaks=[], opacity=None,
        labelColor='LightGray', markerColor='Red', lineColor='White', colorSpace='rgb',
        font='Noto Sans', labelHeight=0.05,
        flip=False, ori=0.0, depth=0, readOnly=False)
    rating_keyboard = keyboard.Keyboard(deviceName='defaultKeyboard')
    rating_display = visual.TextStim(win=win, name='rating_display',
        text='',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    
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
    
    # --- Prepare to start Routine "rr_setup" ---
    # create an object to store info about Routine rr_setup
    rr_setup = data.Routine(
        name='rr_setup',
        components=[],
    )
    rr_setup.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for rr_setup
    rr_setup.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    rr_setup.tStart = globalClock.getTime(format='float')
    rr_setup.status = STARTED
    thisExp.addData('rr_setup.started', rr_setup.tStart)
    rr_setup.maxDuration = None
    # keep track of which components have finished
    rr_setupComponents = rr_setup.components
    for thisComponent in rr_setup.components:
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
    
    # --- Run Routine "rr_setup" ---
    thisExp.currentRoutine = rr_setup
    rr_setup.forceEnded = routineForceEnded = not continueRoutine
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
                currentRoutine=rr_setup,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            rr_setup.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if rr_setup.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in rr_setup.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "rr_setup" ---
    for thisComponent in rr_setup.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for rr_setup
    rr_setup.tStop = globalClock.getTime(format='float')
    rr_setup.tStopRefresh = tThisFlipGlobal
    thisExp.addData('rr_setup.stopped', rr_setup.tStop)
    thisExp.nextEntry()
    # the Routine "rr_setup" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    oo_mvc_type = data.TrialHandler2(
        name='oo_mvc_type',
        nReps=1.0, 
        method='sequential', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('oo_mvc_type.xlsx'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(oo_mvc_type)  # add the loop to the experiment
    thisOo_mvc_type = oo_mvc_type.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisOo_mvc_type.rgb)
    if thisOo_mvc_type != None:
        for paramName in thisOo_mvc_type:
            globals()[paramName] = thisOo_mvc_type[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisOo_mvc_type in oo_mvc_type:
        oo_mvc_type.status = STARTED
        if hasattr(thisOo_mvc_type, 'status'):
            thisOo_mvc_type.status = STARTED
        currentLoop = oo_mvc_type
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisOo_mvc_type.rgb)
        if thisOo_mvc_type != None:
            for paramName in thisOo_mvc_type:
                globals()[paramName] = thisOo_mvc_type[paramName]
        
        # set up handler to look after randomisation of conditions etc
        oo_mvc_rep = data.TrialHandler2(
            name='oo_mvc_rep',
            nReps=cond_num_maxforce, 
            method='sequential', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(oo_mvc_rep)  # add the loop to the experiment
        thisOo_mvc_rep = oo_mvc_rep.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisOo_mvc_rep.rgb)
        if thisOo_mvc_rep != None:
            for paramName in thisOo_mvc_rep:
                globals()[paramName] = thisOo_mvc_rep[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisOo_mvc_rep in oo_mvc_rep:
            oo_mvc_rep.status = STARTED
            if hasattr(thisOo_mvc_rep, 'status'):
                thisOo_mvc_rep.status = STARTED
            currentLoop = oo_mvc_rep
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisOo_mvc_rep.rgb)
            if thisOo_mvc_rep != None:
                for paramName in thisOo_mvc_rep:
                    globals()[paramName] = thisOo_mvc_rep[paramName]
            
            # --- Prepare to start Routine "rr_countdown" ---
            # create an object to store info about Routine rr_countdown
            rr_countdown = data.Routine(
                name='rr_countdown',
                components=[countdown_lights, countdown_display],
            )
            rr_countdown.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from countdown_code
            # Countdown setup
            cur_countdown_idx = len(INNER_HOLES)
            cur_countdown_last_update_sec = None
            
            # Turn on all inner lights initially
            if cur_countdown_idx > 0:
                cur_active_hole_ids = INNER_HOLES[:cur_countdown_idx]
                countdown_lights.setLights(cur_active_hole_ids, Color('white'))
            countdown_lights.setLights("all", 'black')
            # store start times for rr_countdown
            rr_countdown.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            rr_countdown.tStart = globalClock.getTime(format='float')
            rr_countdown.status = STARTED
            thisExp.addData('rr_countdown.started', rr_countdown.tStart)
            rr_countdown.maxDuration = None
            # keep track of which components have finished
            rr_countdownComponents = rr_countdown.components
            for thisComponent in rr_countdown.components:
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
            
            # --- Run Routine "rr_countdown" ---
            thisExp.currentRoutine = rr_countdown
            rr_countdown.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisOo_mvc_rep, 'status') and thisOo_mvc_rep.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from countdown_code
                # Check if it's time to update the countdown
                if cur_countdown_last_update_sec is None:
                    cur_countdown_last_update_sec = t  # t is the routine timer
                
                if t - cur_countdown_last_update_sec >= COUNTDOWN_STEP_SEC:
                    if cur_countdown_idx > 0:
                        # Turn on the remaining lights
                        active_holes = INNER_HOLES[:cur_countdown_idx]
                        countdown_lights.setLights(active_holes, Color('white'))
                        # Turn off the rest
                        inactive_holes = INNER_HOLES[cur_countdown_idx:]
                        countdown_lights.turnOffLights(inactive_holes)
                    else:
                        # All lights off
                        countdown_lights.turnOffLights('outer')
                        continueRoutine = False
                    
                # Decrease the number of active lights
                    cur_countdown_idx -= 1
                    cur_countdown_last_update_sec = t
                
                # if countdown_lights is stopping this frame...
                if countdown_lights.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > countdown_lights.tStartRefresh + 4-frameTolerance:
                        # keep track of stop time/frame for later
                        countdown_lights.tStop = t  # not accounting for scr refresh
                        countdown_lights.tStopRefresh = tThisFlipGlobal  # on global time
                        countdown_lights.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('countdown_lights.stopped', t)
                        # update status
                        countdown_lights.status = FINISHED
                        if False:
                            countdown_lights.turnOffLights("all")
                
                # *countdown_display* updates
                
                # if countdown_display is starting this frame...
                if countdown_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_display.frameNStart = frameN  # exact frame index
                    countdown_display.tStart = t  # local t and not account for scr refresh
                    countdown_display.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_display, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'countdown_display.started')
                    # update status
                    countdown_display.status = STARTED
                    countdown_display.setAutoDraw(True)
                
                # if countdown_display is active this frame...
                if countdown_display.status == STARTED:
                    # update params
                    countdown_display.setText(cur_countdown_idx, log=False)
                
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
                        currentRoutine=rr_countdown,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    rr_countdown.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if rr_countdown.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in rr_countdown.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "rr_countdown" ---
            for thisComponent in rr_countdown.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for rr_countdown
            rr_countdown.tStop = globalClock.getTime(format='float')
            rr_countdown.tStopRefresh = tThisFlipGlobal
            thisExp.addData('rr_countdown.stopped', rr_countdown.tStop)
            if False:
                countdown_lights.turnOffLights("all")
            # the Routine "rr_countdown" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # --- Prepare to start Routine "rr_maxforce" ---
            # create an object to store info about Routine rr_maxforce
            rr_maxforce = data.Routine(
                name='rr_maxforce',
                components=[maxforce_lights, maxforce_force, maxforce_display, maxforce_continue],
            )
            rr_maxforce.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from maxforce_code
            # Initialize current value of MVC
            cur_mvc = maxforce_force.whiteForce = 0
            maxforce_lights.setLights("all", 'white')
            # reset maxforce_continue to account for continued clicks & clear times on/off
            maxforce_continue.reset()
            # store start times for rr_maxforce
            rr_maxforce.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            rr_maxforce.tStart = globalClock.getTime(format='float')
            rr_maxforce.status = STARTED
            thisExp.addData('rr_maxforce.started', rr_maxforce.tStart)
            rr_maxforce.maxDuration = None
            # keep track of which components have finished
            rr_maxforceComponents = rr_maxforce.components
            for thisComponent in rr_maxforce.components:
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
            
            # --- Run Routine "rr_maxforce" ---
            thisExp.currentRoutine = rr_maxforce
            rr_maxforce.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisOo_mvc_rep, 'status') and thisOo_mvc_rep.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from maxforce_code
                # Update current MVC value based on dynamometer measurement
                cur_mvc = max(cur_mvc, maxforce_force.whiteForce)
                
                # Update MVC only if we are in a calibration trial
                if cond_maxforce_type == "calibration":
                    mvc = max(mvc, cur_mvc)
                
                # Display text
                maxforce_display_text = (
                    f"=== TRIAL INFO ===\n"
                    f"Trial Type:        {cond_maxforce_type}\n"
                    f"Current Force:     {maxforce_force.whiteForce:.2f} N\n"
                    f"MVC (cur / max):   {cur_mvc:.2f} / {mvc:.2f} N\n"
                )
                
                
                
                
                # if maxforce_lights is stopping this frame...
                if maxforce_lights.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > maxforce_lights.tStartRefresh + 3.0-frameTolerance:
                        # keep track of stop time/frame for later
                        maxforce_lights.tStop = t  # not accounting for scr refresh
                        maxforce_lights.tStopRefresh = tThisFlipGlobal  # on global time
                        maxforce_lights.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('maxforce_lights.stopped', t)
                        # update status
                        maxforce_lights.status = FINISHED
                        if True:
                            maxforce_lights.turnOffLights("all")
                
                # if maxforce_force is starting this frame...
                if maxforce_force.status == NOT_STARTED and t >= 0-frameTolerance:
                    # keep track of start time/frame for later
                    maxforce_force.frameNStart = frameN  # exact frame index
                    maxforce_force.tStart = t  # local t and not account for scr refresh
                    maxforce_force.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(maxforce_force, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('maxforce_force.started', t)
                    # update status
                    maxforce_force.status = STARTED
                    maxforce_force.startForceMeasurement(60, 'both')
                
                # if maxforce_force is active this frame...
                if maxforce_force.status == STARTED:
                    # update params
                    pass
                    maxforce_force.updateForceMeasurement()
                
                # if maxforce_force is stopping this frame...
                if maxforce_force.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > maxforce_force.tStartRefresh + 3-frameTolerance:
                        # keep track of stop time/frame for later
                        maxforce_force.tStop = t  # not accounting for scr refresh
                        maxforce_force.tStopRefresh = tThisFlipGlobal  # on global time
                        maxforce_force.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('maxforce_force.stopped', t)
                        # update status
                        maxforce_force.status = FINISHED
                        maxforce_force.stopForceMeasurement()
                
                # *maxforce_display* updates
                
                # if maxforce_display is starting this frame...
                if maxforce_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    maxforce_display.frameNStart = frameN  # exact frame index
                    maxforce_display.tStart = t  # local t and not account for scr refresh
                    maxforce_display.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(maxforce_display, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'maxforce_display.started')
                    # update status
                    maxforce_display.status = STARTED
                    maxforce_display.setAutoDraw(True)
                
                # if maxforce_display is active this frame...
                if maxforce_display.status == STARTED:
                    # update params
                    maxforce_display.setText(maxforce_display_text, log=False)
                # *maxforce_continue* updates
                
                # if maxforce_continue is starting this frame...
                if maxforce_continue.status == NOT_STARTED and tThisFlip >= 3-frameTolerance:
                    # keep track of start time/frame for later
                    maxforce_continue.frameNStart = frameN  # exact frame index
                    maxforce_continue.tStart = t  # local t and not account for scr refresh
                    maxforce_continue.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(maxforce_continue, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'maxforce_continue.started')
                    # update status
                    maxforce_continue.status = STARTED
                    win.callOnFlip(maxforce_continue.buttonClock.reset)
                    maxforce_continue.setAutoDraw(True)
                
                # if maxforce_continue is active this frame...
                if maxforce_continue.status == STARTED:
                    # update params
                    pass
                    # check whether maxforce_continue has been pressed
                    if maxforce_continue.isClicked:
                        if not maxforce_continue.wasClicked:
                            # if this is a new click, store time of first click and clicked until
                            maxforce_continue.timesOn.append(maxforce_continue.buttonClock.getTime())
                            maxforce_continue.timesOff.append(maxforce_continue.buttonClock.getTime())
                        elif len(maxforce_continue.timesOff):
                            # if click is continuing from last frame, update time of clicked until
                            maxforce_continue.timesOff[-1] = maxforce_continue.buttonClock.getTime()
                        if not maxforce_continue.wasClicked:
                            # end routine when maxforce_continue is clicked
                            continueRoutine = False
                        if not maxforce_continue.wasClicked:
                            # run callback code when maxforce_continue is clicked
                            pass
                # take note of whether maxforce_continue was clicked, so that next frame we know if clicks are new
                maxforce_continue.wasClicked = maxforce_continue.isClicked and maxforce_continue.status == STARTED
                
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
                        currentRoutine=rr_maxforce,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    rr_maxforce.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if rr_maxforce.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in rr_maxforce.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "rr_maxforce" ---
            for thisComponent in rr_maxforce.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for rr_maxforce
            rr_maxforce.tStop = globalClock.getTime(format='float')
            rr_maxforce.tStopRefresh = tThisFlipGlobal
            thisExp.addData('rr_maxforce.stopped', rr_maxforce.tStop)
            if True:
                maxforce_lights.turnOffLights("all")
            oo_mvc_rep.addData('maxforce_force.rate', 60)
            oo_mvc_rep.addData('maxforce_force.dynamometer', 'both')
            oo_mvc_rep.addData('maxforce_force.maxWhiteForce', maxforce_force.maxWhiteForce)
            oo_mvc_rep.addData('maxforce_force.maxBlueForce', maxforce_force.maxBlueForce)
            if True:
                _raw_path = thisExp.dataFileName + '_force_long.tsv'
                _write_header = not os.path.exists(_raw_path)
                _loop = oo_mvc_rep
                _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                _identifier = str("test") if "test" is not None else ''
                _records = maxforce_force.forceRows if hasattr(maxforce_force, 'forceRows') else []
                _times = maxforce_force.times
                _white = maxforce_force.whiteForceValues
                _blue = maxforce_force.blueForceValues
                _n = max(len(_times), len(_white), len(_blue))
                with open(_raw_path, 'a', encoding='utf-8') as _f:
                    if _write_header:
                        _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	white_time	blue_time	time	white_force	blue_force	white_force_raw_counts	blue_force_raw_counts\n')
                    for _i, _record in enumerate(_records):
                        _row = [
                            expInfo.get("participant", ""),
                            expInfo.get("session", ""),
                            'rr_maxforce',
                            'maxforce_force',
                            _trial_index,
                            _trial_name,
                            _identifier,
                            _i,
                            _record['white_time'],
                            _record['blue_time'],
                            _record['time'],
                            _record['white_force'],
                            _record['blue_force'],
                            _record['white_force_raw_counts'] if _record['white_force_raw_counts'] is not None else '',
                            _record['blue_force_raw_counts'] if _record['blue_force_raw_counts'] is not None else '',
                        ]
                        _f.write('	'.join(str(_v) for _v in _row) + '\n')
            oo_mvc_rep.addData('maxforce_continue.numClicks', maxforce_continue.numClicks)
            if maxforce_continue.numClicks:
               oo_mvc_rep.addData('maxforce_continue.timesOn', maxforce_continue.timesOn)
               oo_mvc_rep.addData('maxforce_continue.timesOff', maxforce_continue.timesOff)
            else:
               oo_mvc_rep.addData('maxforce_continue.timesOn', "")
               oo_mvc_rep.addData('maxforce_continue.timesOff', "")
            # the Routine "rr_maxforce" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            # mark thisOo_mvc_rep as finished
            if hasattr(thisOo_mvc_rep, 'status'):
                thisOo_mvc_rep.status = FINISHED
            # if awaiting a pause, pause now
            if oo_mvc_rep.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                oo_mvc_rep.status = STARTED
            thisExp.nextEntry()
            
        # completed cond_num_maxforce repeats of 'oo_mvc_rep'
        oo_mvc_rep.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # mark thisOo_mvc_type as finished
        if hasattr(thisOo_mvc_type, 'status'):
            thisOo_mvc_type.status = FINISHED
        # if awaiting a pause, pause now
        if oo_mvc_type.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            oo_mvc_type.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'oo_mvc_type'
    oo_mvc_type.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # set up handler to look after randomisation of conditions etc
    oo_domain = data.TrialHandler2(
        name='oo_domain',
        nReps=NUM_DOMAINS, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('oo_domain.xlsx'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(oo_domain)  # add the loop to the experiment
    thisOo_domain = oo_domain.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisOo_domain.rgb)
    if thisOo_domain != None:
        for paramName in thisOo_domain:
            globals()[paramName] = thisOo_domain[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisOo_domain in oo_domain:
        oo_domain.status = STARTED
        if hasattr(thisOo_domain, 'status'):
            thisOo_domain.status = STARTED
        currentLoop = oo_domain
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisOo_domain.rgb)
        if thisOo_domain != None:
            for paramName in thisOo_domain:
                globals()[paramName] = thisOo_domain[paramName]
        
        # --- Prepare to start Routine "rr_domain" ---
        # create an object to store info about Routine rr_domain
        rr_domain = data.Routine(
            name='rr_domain',
            components=[],
        )
        rr_domain.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from domain_code
        # Define shared resources outside the condition
        #def build_level_color_map(levels, num_blocks, colors):
        #    order_per_block = {}
        #    for block in range(num_blocks):
        #        lvls = levels.copy()
        #        random.shuffle(lvls)
        #        order_per_block[block] = lvls
        
        #    color_map = {}
        #    for lvl in levels:
        #        shuffled = random.sample(colors, num_blocks)
        #        color_map[lvl] = {block: shuffled[block] for block in range(NUM_BLOCKS)}
        
        #    return order_per_block, color_map
        
        #def print_design_check(label, order_per_block, color_map):
        #    print(f"\n===== {label} DESIGN CHECK =====")
        #    for block, levels in order_per_block.items():
        #        print(f"\nBlock {block + 1} order:")
        #        for lvl in levels:
        #            print(f"  Level {lvl:.3f} -> Color {color_map[lvl][block]}")
        #    print("=" * 34 + "\n")
        
        #if domain == 'cognitive':
        #    levels = np.linspace(DELTA_E_MIN, DELTA_E_MAX, NUM_LEVELS).tolist()
        #    order_per_block, color_map = build_level_color_map(levels, NUM_BLOCKS, TARGET_COLORS)
        #    print_design_check("DELTA E", order_per_block, color_map)
            # deltaE_order_per_block = order_per_block
            # deltaE_color_map = color_map
        #    deltaE = DELTA_E_PHYSICAL
        #if domain == 'physical':
        #    levels = np.linspace(PERCENT_MVC_MIN, PERCENT_MVC_MAX, NUM_LEVELS).tolist()
        #    order_per_block, color_map = build_level_color_map(levels, NUM_BLOCKS, TARGET_COLORS)
        #    print_design_check("MVC", order_per_block, color_map)
            # mvc_order_per_block = order_per_block
            # mvc_color_map = color_map
            # mvc_level = PERCENT_MVC_COGNITIVE
        # store start times for rr_domain
        rr_domain.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        rr_domain.tStart = globalClock.getTime(format='float')
        rr_domain.status = STARTED
        thisExp.addData('rr_domain.started', rr_domain.tStart)
        rr_domain.maxDuration = None
        # keep track of which components have finished
        rr_domainComponents = rr_domain.components
        for thisComponent in rr_domain.components:
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
        
        # --- Run Routine "rr_domain" ---
        thisExp.currentRoutine = rr_domain
        rr_domain.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisOo_domain, 'status') and thisOo_domain.status == STOPPING:
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
                    currentRoutine=rr_domain,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                rr_domain.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if rr_domain.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in rr_domain.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "rr_domain" ---
        for thisComponent in rr_domain.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for rr_domain
        rr_domain.tStop = globalClock.getTime(format='float')
        rr_domain.tStopRefresh = tThisFlipGlobal
        thisExp.addData('rr_domain.stopped', rr_domain.tStop)
        # the Routine "rr_domain" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # set up handler to look after randomisation of conditions etc
        oo_block = data.TrialHandler2(
            name='oo_block',
            nReps=NUM_BLOCKS, 
            method='random', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(oo_block)  # add the loop to the experiment
        thisOo_block = oo_block.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisOo_block.rgb)
        if thisOo_block != None:
            for paramName in thisOo_block:
                globals()[paramName] = thisOo_block[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisOo_block in oo_block:
            oo_block.status = STARTED
            if hasattr(thisOo_block, 'status'):
                thisOo_block.status = STARTED
            currentLoop = oo_block
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisOo_block.rgb)
            if thisOo_block != None:
                for paramName in thisOo_block:
                    globals()[paramName] = thisOo_block[paramName]
            
            # --- Prepare to start Routine "rr_countdown" ---
            # create an object to store info about Routine rr_countdown
            rr_countdown = data.Routine(
                name='rr_countdown',
                components=[countdown_lights, countdown_display],
            )
            rr_countdown.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from countdown_code
            # Countdown setup
            cur_countdown_idx = len(INNER_HOLES)
            cur_countdown_last_update_sec = None
            
            # Turn on all inner lights initially
            if cur_countdown_idx > 0:
                cur_active_hole_ids = INNER_HOLES[:cur_countdown_idx]
                countdown_lights.setLights(cur_active_hole_ids, Color('white'))
            countdown_lights.setLights("all", 'black')
            # store start times for rr_countdown
            rr_countdown.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            rr_countdown.tStart = globalClock.getTime(format='float')
            rr_countdown.status = STARTED
            thisExp.addData('rr_countdown.started', rr_countdown.tStart)
            rr_countdown.maxDuration = None
            # keep track of which components have finished
            rr_countdownComponents = rr_countdown.components
            for thisComponent in rr_countdown.components:
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
            
            # --- Run Routine "rr_countdown" ---
            thisExp.currentRoutine = rr_countdown
            rr_countdown.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisOo_block, 'status') and thisOo_block.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from countdown_code
                # Check if it's time to update the countdown
                if cur_countdown_last_update_sec is None:
                    cur_countdown_last_update_sec = t  # t is the routine timer
                
                if t - cur_countdown_last_update_sec >= COUNTDOWN_STEP_SEC:
                    if cur_countdown_idx > 0:
                        # Turn on the remaining lights
                        active_holes = INNER_HOLES[:cur_countdown_idx]
                        countdown_lights.setLights(active_holes, Color('white'))
                        # Turn off the rest
                        inactive_holes = INNER_HOLES[cur_countdown_idx:]
                        countdown_lights.turnOffLights(inactive_holes)
                    else:
                        # All lights off
                        countdown_lights.turnOffLights('outer')
                        continueRoutine = False
                    
                # Decrease the number of active lights
                    cur_countdown_idx -= 1
                    cur_countdown_last_update_sec = t
                
                # if countdown_lights is stopping this frame...
                if countdown_lights.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > countdown_lights.tStartRefresh + 4-frameTolerance:
                        # keep track of stop time/frame for later
                        countdown_lights.tStop = t  # not accounting for scr refresh
                        countdown_lights.tStopRefresh = tThisFlipGlobal  # on global time
                        countdown_lights.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.addData('countdown_lights.stopped', t)
                        # update status
                        countdown_lights.status = FINISHED
                        if False:
                            countdown_lights.turnOffLights("all")
                
                # *countdown_display* updates
                
                # if countdown_display is starting this frame...
                if countdown_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    countdown_display.frameNStart = frameN  # exact frame index
                    countdown_display.tStart = t  # local t and not account for scr refresh
                    countdown_display.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(countdown_display, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'countdown_display.started')
                    # update status
                    countdown_display.status = STARTED
                    countdown_display.setAutoDraw(True)
                
                # if countdown_display is active this frame...
                if countdown_display.status == STARTED:
                    # update params
                    countdown_display.setText(cur_countdown_idx, log=False)
                
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
                        currentRoutine=rr_countdown,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    rr_countdown.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if rr_countdown.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in rr_countdown.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "rr_countdown" ---
            for thisComponent in rr_countdown.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for rr_countdown
            rr_countdown.tStop = globalClock.getTime(format='float')
            rr_countdown.tStopRefresh = tThisFlipGlobal
            thisExp.addData('rr_countdown.stopped', rr_countdown.tStop)
            if False:
                countdown_lights.turnOffLights("all")
            # the Routine "rr_countdown" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # set up handler to look after randomisation of conditions etc
            oo_level = data.TrialHandler2(
                name='oo_level',
                nReps=NUM_LEVELS, 
                method='random', 
                extraInfo=expInfo, 
                originPath=-1, 
                trialList=data.importConditions('oo_level.xlsx'), 
                seed=None, 
                isTrials=True, 
            )
            thisExp.addLoop(oo_level)  # add the loop to the experiment
            thisOo_level = oo_level.trialList[0]  # so we can initialise stimuli with some values
            # abbreviate parameter names if possible (e.g. rgb = thisOo_level.rgb)
            if thisOo_level != None:
                for paramName in thisOo_level:
                    globals()[paramName] = thisOo_level[paramName]
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            
            for thisOo_level in oo_level:
                oo_level.status = STARTED
                if hasattr(thisOo_level, 'status'):
                    thisOo_level.status = STARTED
                currentLoop = oo_level
                thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # abbreviate parameter names if possible (e.g. rgb = thisOo_level.rgb)
                if thisOo_level != None:
                    for paramName in thisOo_level:
                        globals()[paramName] = thisOo_level[paramName]
                
                # --- Prepare to start Routine "rr_target" ---
                # create an object to store info about Routine rr_target
                rr_target = data.Routine(
                    name='rr_target',
                    components=[target_lights, target_force, target_display],
                )
                rr_target.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from target_color_code
                # set up which trials show a target
                target_present_palette_indices = random.sample(range(NUM_PALETTES), NUM_TARGETS)
                
                # Initialize values
                cur_palette_idx = cur_palette_global_idx = 0
                
                # Reset hits/misses/fa/cr for dprime calculation later in slider Routine
                hits = misses = false_alarms = correct_rejections = 0
                # Run 'Begin Routine' code from target_audio_code
                # Begin Routine
                with _state_lock:
                    _target_amp = 0.0   # definiert stumm
                # Begin Routine
                toneState = 0
                _lastSwitchT = -1e9   # erlaubt sofortigen Wechsel
                
                currentMVCLevel = mvcLevel
                targetForce = currentMVCLevel * mvc
                
                tolerance = 15.0
                lower_threshold = targetForce - tolerance
                upper_threshold = targetForce + tolerance
                
                target_lights.setLights("inner", cond_target_color_rgb255)
                target_display.setText(f"Color: {cond_target_color}, Force: {traget_Force.whiteForce}")
                # store start times for rr_target
                rr_target.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                rr_target.tStart = globalClock.getTime(format='float')
                rr_target.status = STARTED
                thisExp.addData('rr_target.started', rr_target.tStart)
                rr_target.maxDuration = None
                # keep track of which components have finished
                rr_targetComponents = rr_target.components
                for thisComponent in rr_target.components:
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
                
                # --- Run Routine "rr_target" ---
                thisExp.currentRoutine = rr_target
                rr_target.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine and routineTimer.getTime() < 3.0:
                    # if trial has changed, end Routine now
                    if hasattr(thisOo_level, 'status') and thisOo_level.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    # Run 'Each Frame' code from target_audio_code
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
                    
                    
                    # if target_lights is stopping this frame...
                    if target_lights.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > target_lights.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            target_lights.tStop = t  # not accounting for scr refresh
                            target_lights.tStopRefresh = tThisFlipGlobal  # on global time
                            target_lights.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.addData('target_lights.stopped', t)
                            # update status
                            target_lights.status = FINISHED
                            if True:
                                target_lights.turnOffLights("inner")
                    
                    # if target_force is starting this frame...
                    if target_force.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        target_force.frameNStart = frameN  # exact frame index
                        target_force.tStart = t  # local t and not account for scr refresh
                        target_force.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(target_force, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('target_force.started', t)
                        # update status
                        target_force.status = STARTED
                        target_force.startForceMeasurement(50, 'both')
                    
                    # if target_force is active this frame...
                    if target_force.status == STARTED:
                        # update params
                        pass
                        target_force.updateForceMeasurement()
                    
                    # if target_force is stopping this frame...
                    if target_force.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > target_force.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            target_force.tStop = t  # not accounting for scr refresh
                            target_force.tStopRefresh = tThisFlipGlobal  # on global time
                            target_force.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.addData('target_force.stopped', t)
                            # update status
                            target_force.status = FINISHED
                            target_force.stopForceMeasurement()
                    
                    # *target_display* updates
                    
                    # if target_display is starting this frame...
                    if target_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        target_display.frameNStart = frameN  # exact frame index
                        target_display.tStart = t  # local t and not account for scr refresh
                        target_display.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(target_display, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'target_display.started')
                        # update status
                        target_display.status = STARTED
                        target_display.setAutoDraw(True)
                    
                    # if target_display is active this frame...
                    if target_display.status == STARTED:
                        # update params
                        pass
                    
                    # if target_display is stopping this frame...
                    if target_display.status == STARTED:
                        # is it time to stop? (based on global clock, using actual start)
                        if tThisFlipGlobal > target_display.tStartRefresh + 3.0-frameTolerance:
                            # keep track of stop time/frame for later
                            target_display.tStop = t  # not accounting for scr refresh
                            target_display.tStopRefresh = tThisFlipGlobal  # on global time
                            target_display.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'target_display.stopped')
                            # update status
                            target_display.status = FINISHED
                            target_display.setAutoDraw(False)
                    
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
                            currentRoutine=rr_target,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        rr_target.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if rr_target.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in rr_target.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "rr_target" ---
                for thisComponent in rr_target.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for rr_target
                rr_target.tStop = globalClock.getTime(format='float')
                rr_target.tStopRefresh = tThisFlipGlobal
                thisExp.addData('rr_target.stopped', rr_target.tStop)
                if True:
                    target_lights.turnOffLights("inner")
                oo_level.addData('target_force.rate', 50)
                oo_level.addData('target_force.dynamometer', 'both')
                oo_level.addData('target_force.maxWhiteForce', target_force.maxWhiteForce)
                oo_level.addData('target_force.maxBlueForce', target_force.maxBlueForce)
                if True:
                    _raw_path = thisExp.dataFileName + '_force_long.tsv'
                    _write_header = not os.path.exists(_raw_path)
                    _loop = oo_level
                    _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                    _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                    _identifier = str(target_force) if target_force is not None else ''
                    _records = target_force.forceRows if hasattr(target_force, 'forceRows') else []
                    _times = target_force.times
                    _white = target_force.whiteForceValues
                    _blue = target_force.blueForceValues
                    _n = max(len(_times), len(_white), len(_blue))
                    with open(_raw_path, 'a', encoding='utf-8') as _f:
                        if _write_header:
                            _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	white_time	blue_time	time	white_force	blue_force	white_force_raw_counts	blue_force_raw_counts\n')
                        for _i, _record in enumerate(_records):
                            _row = [
                                expInfo.get("participant", ""),
                                expInfo.get("session", ""),
                                'rr_target',
                                'target_force',
                                _trial_index,
                                _trial_name,
                                _identifier,
                                _i,
                                _record['white_time'],
                                _record['blue_time'],
                                _record['time'],
                                _record['white_force'],
                                _record['blue_force'],
                                _record['white_force_raw_counts'] if _record['white_force_raw_counts'] is not None else '',
                                _record['blue_force_raw_counts'] if _record['blue_force_raw_counts'] is not None else '',
                            ]
                            _f.write('	'.join(str(_v) for _v in _row) + '\n')
                # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
                if rr_target.maxDurationReached:
                    routineTimer.addTime(-rr_target.maxDuration)
                elif rr_target.forceEnded:
                    routineTimer.reset()
                else:
                    routineTimer.addTime(-3.000000)
                
                # set up handler to look after randomisation of conditions etc
                oo_palette = data.TrialHandler2(
                    name='oo_palette',
                    nReps=NUM_PALETTES, 
                    method='random', 
                    extraInfo=expInfo, 
                    originPath=-1, 
                    trialList=[None], 
                    seed=None, 
                    isTrials=True, 
                )
                thisExp.addLoop(oo_palette)  # add the loop to the experiment
                thisOo_palette = oo_palette.trialList[0]  # so we can initialise stimuli with some values
                # abbreviate parameter names if possible (e.g. rgb = thisOo_palette.rgb)
                if thisOo_palette != None:
                    for paramName in thisOo_palette:
                        globals()[paramName] = thisOo_palette[paramName]
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                for thisOo_palette in oo_palette:
                    oo_palette.status = STARTED
                    if hasattr(thisOo_palette, 'status'):
                        thisOo_palette.status = STARTED
                    currentLoop = oo_palette
                    thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                    if thisSession is not None:
                        # if running in a Session with a Liaison client, send data up to now
                        thisSession.sendExperimentData()
                    # abbreviate parameter names if possible (e.g. rgb = thisOo_palette.rgb)
                    if thisOo_palette != None:
                        for paramName in thisOo_palette:
                            globals()[paramName] = thisOo_palette[paramName]
                    
                    # --- Prepare to start Routine "rr_trial" ---
                    # create an object to store info about Routine rr_trial
                    rr_trial = data.Routine(
                        name='rr_trial',
                        components=[trial_reed, trial_lights, trial_force, trial_display],
                    )
                    rr_trial.status = NOT_STARTED
                    continueRoutine = True
                    # update component parameters for each repeat
                    trial_reed.startReedMeasurement(100, "all")
                    trial_lights.setLights("inner", 'inner_colors')
                    # Run 'Begin Routine' code from trial_color_code
                    # Initialize all holes with distractor colors
                    inner_colors = {
                        hole: Color(rgb255, 'rgb255')
                        for hole, rgb255 in zip(INNER_HOLES, generate_distractors(cond_target_color_rgb255, int(deltaE), N_DISTRACTORS))
                    }
                    
                    # If target present, replace one distractor with the target
                    if cur_palette in target_present_palette_indices:
                        cur_has_target = True
                        target_hole_idx = random.choice(list(INNER_HOLES))
                        inner_colors[target_hole_idx] = Color(cond_target_color_rgb255, 'rgb255')
                        currentLoop.addData('targetPresent', cur_has_target)
                        currentLoop.addData('targetHole', target_hole_idx)
                    else:
                        cur_has_target = False
                        currentLoop.addData('targetPresent', cur_has_target)
                        currentLoop.addData('targetHole', None)
                    
                    paletteResponses = set()
                    paletteResponseEvents = []
                    # Run 'Begin Routine' code from trial_audio_code
                    # Begin Routine
                    with _state_lock:
                        _target_amp = 0.0   # definiert stumm
                    # Begin Routine
                    toneState = 0
                    _lastSwitchT = -1e9   # erlaubt sofortigen Wechsel
                    
                    currentMVCLevel = mvcLevel
                    targetForce = currentMVCLevel * mvc
                    
                    tolerance = 15.0
                    lower_threshold = targetForce - tolerance
                    upper_threshold = targetForce + tolerance
                    trial_display.setText(f"Palette: {index}, deltaE: {deltaE}, Kraftlevel: {mvcLevel}"
                    )
                    # store start times for rr_trial
                    rr_trial.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                    rr_trial.tStart = globalClock.getTime(format='float')
                    rr_trial.status = STARTED
                    thisExp.addData('rr_trial.started', rr_trial.tStart)
                    rr_trial.maxDuration = None
                    # keep track of which components have finished
                    rr_trialComponents = rr_trial.components
                    for thisComponent in rr_trial.components:
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
                    
                    # --- Run Routine "rr_trial" ---
                    thisExp.currentRoutine = rr_trial
                    rr_trial.forceEnded = routineForceEnded = not continueRoutine
                    while continueRoutine:
                        # if trial has changed, end Routine now
                        if hasattr(thisOo_palette, 'status') and thisOo_palette.status == STOPPING:
                            continueRoutine = False
                        # get current time
                        t = routineTimer.getTime()
                        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                        # update/draw components on each frame
                        
                        # if trial_reed is starting this frame...
                        if trial_reed.status == NOT_STARTED and t >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            trial_reed.frameNStart = frameN  # exact frame index
                            trial_reed.tStart = t  # local t and not account for scr refresh
                            trial_reed.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(trial_reed, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.addData('trial_reed.started', t)
                            # update status
                            trial_reed.status = STARTED
                            
                        
                        # if trial_reed is active this frame...
                        if trial_reed.status == STARTED:
                            # update params
                            pass
                            trial_reed.updateReedMeasurement()
                            if False and len(trial_reed.reedTimes) > 0:
                                trial_reed.stopReedMeasurement()
                                continueRoutine = False
                        
                        # if trial_reed is stopping this frame...
                        if trial_reed.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > trial_reed.tStartRefresh + PALETTE_DURATION_SEC + 1-frameTolerance:
                                # keep track of stop time/frame for later
                                trial_reed.tStop = t  # not accounting for scr refresh
                                trial_reed.tStopRefresh = tThisFlipGlobal  # on global time
                                trial_reed.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('trial_reed.stopped', t)
                                # update status
                                trial_reed.status = FINISHED
                                trial_reed.stopReedMeasurement()
                        
                        # if trial_lights is stopping this frame...
                        if trial_lights.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > trial_lights.tStartRefresh + PALETTE_DURATION_SEC-frameTolerance:
                                # keep track of stop time/frame for later
                                trial_lights.tStop = t  # not accounting for scr refresh
                                trial_lights.tStopRefresh = tThisFlipGlobal  # on global time
                                trial_lights.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('trial_lights.stopped', t)
                                # update status
                                trial_lights.status = FINISHED
                                if True:
                                    trial_lights.turnOffLights("inner")
                        # Run 'Each Frame' code from trial_color_code
                        # Reedkontakte auslesen (paletteweise, robust gegen mehrere Antworten)
                        taskReed.updateReedMeasurement()
                        for hole in taskReed.reedNewInsertions:
                            paletteResponses.add(hole)
                            paletteResponseEvents.append((t, hole))
                        paletteResponses.update(taskReed.reedActiveHoles)
                        
                        responses = set(paletteResponses)
                        has_response = bool(responses)
                        
                        if cur_has_target:
                            is_hit = int(targetHole in paletteResponses)
                            is_false_alarm = int(bool(responses - {targetHole}))
                            is_miss = 1 - is_hit
                            is_correct_rejection = 0
                        else:
                            is_hit = 0
                            is_miss = 0
                            is_false_alarm = int(has_response)
                            is_correct_rejection = 1 - is_false_alarm
                        
                        # if trial_force is starting this frame...
                        if trial_force.status == NOT_STARTED and t >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            trial_force.frameNStart = frameN  # exact frame index
                            trial_force.tStart = t  # local t and not account for scr refresh
                            trial_force.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(trial_force, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.addData('trial_force.started', t)
                            # update status
                            trial_force.status = STARTED
                            trial_force.startForceMeasurement(50, 'both')
                        
                        # if trial_force is active this frame...
                        if trial_force.status == STARTED:
                            # update params
                            pass
                            trial_force.updateForceMeasurement()
                        
                        # if trial_force is stopping this frame...
                        if trial_force.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > trial_force.tStartRefresh + PALETTE_DURATION_SEC + 1-frameTolerance:
                                # keep track of stop time/frame for later
                                trial_force.tStop = t  # not accounting for scr refresh
                                trial_force.tStopRefresh = tThisFlipGlobal  # on global time
                                trial_force.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.addData('trial_force.stopped', t)
                                # update status
                                trial_force.status = FINISHED
                                trial_force.stopForceMeasurement()
                        # Run 'Each Frame' code from trial_audio_code
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
                        
                        
                        # *trial_display* updates
                        
                        # if trial_display is starting this frame...
                        if trial_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            trial_display.frameNStart = frameN  # exact frame index
                            trial_display.tStart = t  # local t and not account for scr refresh
                            trial_display.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(trial_display, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'trial_display.started')
                            # update status
                            trial_display.status = STARTED
                            trial_display.setAutoDraw(True)
                        
                        # if trial_display is active this frame...
                        if trial_display.status == STARTED:
                            # update params
                            pass
                        
                        # if trial_display is stopping this frame...
                        if trial_display.status == STARTED:
                            # is it time to stop? (based on global clock, using actual start)
                            if tThisFlipGlobal > trial_display.tStartRefresh + PALETTE_DURATION_SEC + 1-frameTolerance:
                                # keep track of stop time/frame for later
                                trial_display.tStop = t  # not accounting for scr refresh
                                trial_display.tStopRefresh = tThisFlipGlobal  # on global time
                                trial_display.frameNStop = frameN  # exact frame index
                                # add timestamp to datafile
                                thisExp.timestampOnFlip(win, 'trial_display.stopped')
                                # update status
                                trial_display.status = FINISHED
                                trial_display.setAutoDraw(False)
                        
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
                                currentRoutine=rr_trial,
                            )
                            # skip the frame we paused on
                            continue
                        
                        # has a Component requested the Routine to end?
                        if not continueRoutine:
                            rr_trial.forceEnded = routineForceEnded = True
                        # has the Routine been forcibly ended?
                        if rr_trial.forceEnded or routineForceEnded:
                            break
                        # has every Component finished?
                        continueRoutine = False
                        for thisComponent in rr_trial.components:
                            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                                continueRoutine = True
                                break  # at least one component has not yet finished
                        
                        # refresh the screen
                        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                            win.flip()
                    
                    # --- Ending Routine "rr_trial" ---
                    for thisComponent in rr_trial.components:
                        if hasattr(thisComponent, "setAutoDraw"):
                            thisComponent.setAutoDraw(False)
                    # store stop times for rr_trial
                    rr_trial.tStop = globalClock.getTime(format='float')
                    rr_trial.tStopRefresh = tThisFlipGlobal
                    thisExp.addData('rr_trial.stopped', rr_trial.tStop)
                    # make sure reed measurement is stopped
                    if trial_reed.status == STARTED:
                        trial_reed.stopReedMeasurement()
                    oo_palette.addData('trial_reed.rate', 100)
                    oo_palette.addData('trial_reed.holes', "all")
                    oo_palette.addData('trial_reed.reedTimes', trial_reed.reedTimes)
                    oo_palette.addData('trial_reed.reedHoles', trial_reed.reedHoles)
                    oo_palette.addData('trial_reed.reedActions', trial_reed.reedActions)
                    oo_palette.addData('trial_reed.reedSummary', trial_reed.reedSummary)
                    oo_palette.addData('trial_reed.reedCurrentStates', trial_reed.reedCurrentStates)
                    oo_palette.addData('trial_reed.reedActiveHoles', trial_reed.reedActiveHoles)
                    oo_palette.addData('trial_reed.reedNewInsertions', trial_reed.reedNewInsertions)
                    oo_palette.addData('trial_reed.reedNewRemovals', trial_reed.reedNewRemovals)
                    oo_palette.addData('trial_reed.reedLatestEvent', trial_reed.reedLatestEvent)
                    oo_palette.addData('trial_reed.reedFrameTimes', trial_reed.reedFrameTimes)
                    oo_palette.addData('trial_reed.reedFrameStates', trial_reed.reedFrameStates)
                    oo_palette.addData('trial_reed.reedFrameActiveHoles', trial_reed.reedFrameActiveHoles)
                    if True:
                        trial_lights.turnOffLights("inner")
                    # Run 'End Routine' code from trial_color_code
                    # Index um eins hochzählen, damit richtige Palette angezeigt wird
                    cur_palette_idx += 1
                    cur_palette_global_idx += 1
                    
                    # Hochzählen der hits, fa, cr & misses
                    hits += is_hit
                    false_alarms += is_false_alarm
                    misses += is_miss
                    correct_rejections += is_correct_rejection
                    
                    #Daten anhängen
                    paletteResponseList = sorted(paletteResponses)
                    currentLoop.addData('paletteResponseCount', len(paletteResponseList))
                    currentLoop.addData('paletteResponses', paletteResponseList)
                    currentLoop.addData('paletteResponseEvents', paletteResponseEvents)
                    currentLoop.addData('hit', hit)
                    currentLoop.addData('falsealarm', fa)
                    currentLoop.addData('correct rejection', cr)
                    currentLoop.addData('miss', miss)
                    
                    oo_palette.addData('trial_force.rate', 50)
                    oo_palette.addData('trial_force.dynamometer', 'both')
                    oo_palette.addData('trial_force.maxWhiteForce', trial_force.maxWhiteForce)
                    oo_palette.addData('trial_force.maxBlueForce', trial_force.maxBlueForce)
                    if True:
                        _raw_path = thisExp.dataFileName + '_force_long.tsv'
                        _write_header = not os.path.exists(_raw_path)
                        _loop = oo_palette
                        _trial_index = _loop.thisN if _loop is not None and hasattr(_loop, 'thisN') else -1
                        _trial_name = _loop.name if _loop is not None and hasattr(_loop, 'name') else ''
                        _identifier = str(trial_force) if trial_force is not None else ''
                        _records = trial_force.forceRows if hasattr(trial_force, 'forceRows') else []
                        _times = trial_force.times
                        _white = trial_force.whiteForceValues
                        _blue = trial_force.blueForceValues
                        _n = max(len(_times), len(_white), len(_blue))
                        with open(_raw_path, 'a', encoding='utf-8') as _f:
                            if _write_header:
                                _f.write('participant	session	routine	component	trial_index	trial_name	identifier	sample_index	white_time	blue_time	time	white_force	blue_force	white_force_raw_counts	blue_force_raw_counts\n')
                            for _i, _record in enumerate(_records):
                                _row = [
                                    expInfo.get("participant", ""),
                                    expInfo.get("session", ""),
                                    'rr_trial',
                                    'trial_force',
                                    _trial_index,
                                    _trial_name,
                                    _identifier,
                                    _i,
                                    _record['white_time'],
                                    _record['blue_time'],
                                    _record['time'],
                                    _record['white_force'],
                                    _record['blue_force'],
                                    _record['white_force_raw_counts'] if _record['white_force_raw_counts'] is not None else '',
                                    _record['blue_force_raw_counts'] if _record['blue_force_raw_counts'] is not None else '',
                                ]
                                _f.write('	'.join(str(_v) for _v in _row) + '\n')
                    # the Routine "rr_trial" was not non-slip safe, so reset the non-slip timer
                    routineTimer.reset()
                    # mark thisOo_palette as finished
                    if hasattr(thisOo_palette, 'status'):
                        thisOo_palette.status = FINISHED
                    # if awaiting a pause, pause now
                    if oo_palette.status == PAUSED:
                        thisExp.status = PAUSED
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[globalClock], 
                        )
                        # once done pausing, restore running status
                        oo_palette.status = STARTED
                    thisExp.nextEntry()
                    
                # completed NUM_PALETTES repeats of 'oo_palette'
                oo_palette.status = FINISHED
                
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                # --- Prepare to start Routine "rr_feedback" ---
                # create an object to store info about Routine rr_feedback
                rr_feedback = data.Routine(
                    name='rr_feedback',
                    components=[feedback_keyboard, feedback_display],
                )
                rr_feedback.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from feedback_code
                #dprime Calculation
                H = hits + misses
                F = false_alarms + correct_rejections
                
                hit_rate = (hits+0.5)/(H+1) if H>0 else 0.5
                fa_rate = (false_alarms+0.5)/(F+1) if F>0 else 0.5
                d_prime = norm.ppf(hit_rate) - norm.ppf(fa_rate)
                
                currentLoop.addData('d_prime', d_prime)
                # create starting attributes for feedback_keyboard
                feedback_keyboard.keys = []
                feedback_keyboard.rt = []
                _feedback_keyboard_allKeys = []
                # store start times for rr_feedback
                rr_feedback.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                rr_feedback.tStart = globalClock.getTime(format='float')
                rr_feedback.status = STARTED
                thisExp.addData('rr_feedback.started', rr_feedback.tStart)
                rr_feedback.maxDuration = None
                # keep track of which components have finished
                rr_feedbackComponents = rr_feedback.components
                for thisComponent in rr_feedback.components:
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
                
                # --- Run Routine "rr_feedback" ---
                thisExp.currentRoutine = rr_feedback
                rr_feedback.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisOo_level, 'status') and thisOo_level.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    
                    # *feedback_keyboard* updates
                    waitOnFlip = False
                    
                    # if feedback_keyboard is starting this frame...
                    if feedback_keyboard.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        feedback_keyboard.frameNStart = frameN  # exact frame index
                        feedback_keyboard.tStart = t  # local t and not account for scr refresh
                        feedback_keyboard.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(feedback_keyboard, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'feedback_keyboard.started')
                        # update status
                        feedback_keyboard.status = STARTED
                        # keyboard checking is just starting
                        waitOnFlip = True
                        win.callOnFlip(feedback_keyboard.clock.reset)  # t=0 on next screen flip
                        win.callOnFlip(feedback_keyboard.clearEvents, eventType='keyboard')  # clear events on next screen flip
                    if feedback_keyboard.status == STARTED and not waitOnFlip:
                        theseKeys = feedback_keyboard.getKeys(keyList=['space'], ignoreKeys=["escape"], waitRelease=False)
                        _feedback_keyboard_allKeys.extend(theseKeys)
                        if len(_feedback_keyboard_allKeys):
                            feedback_keyboard.keys = _feedback_keyboard_allKeys[-1].name  # just the last key pressed
                            feedback_keyboard.rt = _feedback_keyboard_allKeys[-1].rt
                            feedback_keyboard.duration = _feedback_keyboard_allKeys[-1].duration
                            # a response ends the routine
                            continueRoutine = False
                    
                    # *feedback_display* updates
                    
                    # if feedback_display is starting this frame...
                    if feedback_display.status == NOT_STARTED and tThisFlip >= 0-frameTolerance:
                        # keep track of start time/frame for later
                        feedback_display.frameNStart = frameN  # exact frame index
                        feedback_display.tStart = t  # local t and not account for scr refresh
                        feedback_display.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(feedback_display, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'feedback_display.started')
                        # update status
                        feedback_display.status = STARTED
                        feedback_display.setAutoDraw(True)
                    
                    # if feedback_display is active this frame...
                    if feedback_display.status == STARTED:
                        # update params
                        feedback_display.setText('Last dprime: ' + str(d_prime) + '\n'
                        'Hits: ' + str(hits) + '\n'
                        'Misses: ' + str(misses) + '\n'
                        'False alarms: ' + str(false_alarms) + '\n'
                        'Correct rejections: ' + str(correct_rejections) + '\n', log=False)
                    
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
                            currentRoutine=rr_feedback,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        rr_feedback.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if rr_feedback.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in rr_feedback.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "rr_feedback" ---
                for thisComponent in rr_feedback.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for rr_feedback
                rr_feedback.tStop = globalClock.getTime(format='float')
                rr_feedback.tStopRefresh = tThisFlipGlobal
                thisExp.addData('rr_feedback.stopped', rr_feedback.tStop)
                # check responses
                if feedback_keyboard.keys in ['', [], None]:  # No response was made
                    feedback_keyboard.keys = None
                oo_level.addData('feedback_keyboard.keys',feedback_keyboard.keys)
                if feedback_keyboard.keys != None:  # we had a response
                    oo_level.addData('feedback_keyboard.rt', feedback_keyboard.rt)
                    oo_level.addData('feedback_keyboard.duration', feedback_keyboard.duration)
                # the Routine "rr_feedback" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                
                # set up handler to look after randomisation of conditions etc
                oo_slider = data.TrialHandler2(
                    name='oo_slider',
                    nReps=1, 
                    method='sequential', 
                    extraInfo=expInfo, 
                    originPath=-1, 
                    trialList=data.importConditions('oo_slider.xlsx'), 
                    seed=None, 
                    isTrials=True, 
                )
                thisExp.addLoop(oo_slider)  # add the loop to the experiment
                thisOo_slider = oo_slider.trialList[0]  # so we can initialise stimuli with some values
                # abbreviate parameter names if possible (e.g. rgb = thisOo_slider.rgb)
                if thisOo_slider != None:
                    for paramName in thisOo_slider:
                        globals()[paramName] = thisOo_slider[paramName]
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                
                for thisOo_slider in oo_slider:
                    oo_slider.status = STARTED
                    if hasattr(thisOo_slider, 'status'):
                        thisOo_slider.status = STARTED
                    currentLoop = oo_slider
                    thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                    if thisSession is not None:
                        # if running in a Session with a Liaison client, send data up to now
                        thisSession.sendExperimentData()
                    # abbreviate parameter names if possible (e.g. rgb = thisOo_slider.rgb)
                    if thisOo_slider != None:
                        for paramName in thisOo_slider:
                            globals()[paramName] = thisOo_slider[paramName]
                    
                    # --- Prepare to start Routine "rr_rating" ---
                    # create an object to store info about Routine rr_rating
                    rr_rating = data.Routine(
                        name='rr_rating',
                        components=[rating_slider, rating_keyboard, rating_display],
                    )
                    rr_rating.status = NOT_STARTED
                    continueRoutine = True
                    # update component parameters for each repeat
                    rating_slider.reset()
                    # create starting attributes for rating_keyboard
                    rating_keyboard.keys = []
                    rating_keyboard.rt = []
                    _rating_keyboard_allKeys = []
                    rating_display.setText(f"{sliderResponse} Effort")
                    # store start times for rr_rating
                    rr_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                    rr_rating.tStart = globalClock.getTime(format='float')
                    rr_rating.status = STARTED
                    thisExp.addData('rr_rating.started', rr_rating.tStart)
                    rr_rating.maxDuration = None
                    # keep track of which components have finished
                    rr_ratingComponents = rr_rating.components
                    for thisComponent in rr_rating.components:
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
                    
                    # --- Run Routine "rr_rating" ---
                    thisExp.currentRoutine = rr_rating
                    rr_rating.forceEnded = routineForceEnded = not continueRoutine
                    while continueRoutine:
                        # if trial has changed, end Routine now
                        if hasattr(thisOo_slider, 'status') and thisOo_slider.status == STOPPING:
                            continueRoutine = False
                        # get current time
                        t = routineTimer.getTime()
                        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                        # update/draw components on each frame
                        
                        # *rating_slider* updates
                        
                        # if rating_slider is starting this frame...
                        if rating_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            rating_slider.frameNStart = frameN  # exact frame index
                            rating_slider.tStart = t  # local t and not account for scr refresh
                            rating_slider.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(rating_slider, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'rating_slider.started')
                            # update status
                            rating_slider.status = STARTED
                            rating_slider.setAutoDraw(True)
                        
                        # if rating_slider is active this frame...
                        if rating_slider.status == STARTED:
                            # update params
                            pass
                        
                        # *rating_keyboard* updates
                        waitOnFlip = False
                        
                        # if rating_keyboard is starting this frame...
                        if rating_keyboard.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            rating_keyboard.frameNStart = frameN  # exact frame index
                            rating_keyboard.tStart = t  # local t and not account for scr refresh
                            rating_keyboard.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(rating_keyboard, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'rating_keyboard.started')
                            # update status
                            rating_keyboard.status = STARTED
                            # keyboard checking is just starting
                            waitOnFlip = True
                            win.callOnFlip(rating_keyboard.clock.reset)  # t=0 on next screen flip
                            win.callOnFlip(rating_keyboard.clearEvents, eventType='keyboard')  # clear events on next screen flip
                        if rating_keyboard.status == STARTED and not waitOnFlip:
                            theseKeys = rating_keyboard.getKeys(keyList=['space'], ignoreKeys=["escape"], waitRelease=False)
                            _rating_keyboard_allKeys.extend(theseKeys)
                            if len(_rating_keyboard_allKeys):
                                rating_keyboard.keys = _rating_keyboard_allKeys[-1].name  # just the last key pressed
                                rating_keyboard.rt = _rating_keyboard_allKeys[-1].rt
                                rating_keyboard.duration = _rating_keyboard_allKeys[-1].duration
                                # a response ends the routine
                                continueRoutine = False
                        
                        # *rating_display* updates
                        
                        # if rating_display is starting this frame...
                        if rating_display.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                            # keep track of start time/frame for later
                            rating_display.frameNStart = frameN  # exact frame index
                            rating_display.tStart = t  # local t and not account for scr refresh
                            rating_display.tStartRefresh = tThisFlipGlobal  # on global time
                            win.timeOnFlip(rating_display, 'tStartRefresh')  # time at next scr refresh
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'rating_display.started')
                            # update status
                            rating_display.status = STARTED
                            rating_display.setAutoDraw(True)
                        
                        # if rating_display is active this frame...
                        if rating_display.status == STARTED:
                            # update params
                            pass
                        
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
                                currentRoutine=rr_rating,
                            )
                            # skip the frame we paused on
                            continue
                        
                        # has a Component requested the Routine to end?
                        if not continueRoutine:
                            rr_rating.forceEnded = routineForceEnded = True
                        # has the Routine been forcibly ended?
                        if rr_rating.forceEnded or routineForceEnded:
                            break
                        # has every Component finished?
                        continueRoutine = False
                        for thisComponent in rr_rating.components:
                            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                                continueRoutine = True
                                break  # at least one component has not yet finished
                        
                        # refresh the screen
                        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                            win.flip()
                    
                    # --- Ending Routine "rr_rating" ---
                    for thisComponent in rr_rating.components:
                        if hasattr(thisComponent, "setAutoDraw"):
                            thisComponent.setAutoDraw(False)
                    # store stop times for rr_rating
                    rr_rating.tStop = globalClock.getTime(format='float')
                    rr_rating.tStopRefresh = tThisFlipGlobal
                    thisExp.addData('rr_rating.stopped', rr_rating.tStop)
                    oo_slider.addData('rating_slider.response', rating_slider.getRating())
                    oo_slider.addData('rating_slider.rt', rating_slider.getRT())
                    # check responses
                    if rating_keyboard.keys in ['', [], None]:  # No response was made
                        rating_keyboard.keys = None
                    oo_slider.addData('rating_keyboard.keys',rating_keyboard.keys)
                    if rating_keyboard.keys != None:  # we had a response
                        oo_slider.addData('rating_keyboard.rt', rating_keyboard.rt)
                        oo_slider.addData('rating_keyboard.duration', rating_keyboard.duration)
                    # the Routine "rr_rating" was not non-slip safe, so reset the non-slip timer
                    routineTimer.reset()
                    # mark thisOo_slider as finished
                    if hasattr(thisOo_slider, 'status'):
                        thisOo_slider.status = FINISHED
                    # if awaiting a pause, pause now
                    if oo_slider.status == PAUSED:
                        thisExp.status = PAUSED
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[globalClock], 
                        )
                        # once done pausing, restore running status
                        oo_slider.status = STARTED
                    thisExp.nextEntry()
                    
                # completed 1 repeats of 'oo_slider'
                oo_slider.status = FINISHED
                
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # mark thisOo_level as finished
                if hasattr(thisOo_level, 'status'):
                    thisOo_level.status = FINISHED
                # if awaiting a pause, pause now
                if oo_level.status == PAUSED:
                    thisExp.status = PAUSED
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[globalClock], 
                    )
                    # once done pausing, restore running status
                    oo_level.status = STARTED
                thisExp.nextEntry()
                
            # completed NUM_LEVELS repeats of 'oo_level'
            oo_level.status = FINISHED
            
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # mark thisOo_block as finished
            if hasattr(thisOo_block, 'status'):
                thisOo_block.status = FINISHED
            # if awaiting a pause, pause now
            if oo_block.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                oo_block.status = STARTED
            thisExp.nextEntry()
            
        # completed NUM_BLOCKS repeats of 'oo_block'
        oo_block.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # mark thisOo_domain as finished
        if hasattr(thisOo_domain, 'status'):
            thisOo_domain.status = FINISHED
        # if awaiting a pause, pause now
        if oo_domain.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            oo_domain.status = STARTED
        thisExp.nextEntry()
        
    # completed NUM_DOMAINS repeats of 'oo_domain'
    oo_domain.status = FINISHED
    
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
