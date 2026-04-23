/***************** 
 * Maxforce *
 *****************/

import { core, data, sound, util, visual, hardware } from './lib/psychojs-2026.1.1.js';
const { PsychoJS } = core;
const { TrialHandler, MultiStairHandler } = data;
const { Scheduler } = util;
//some handy aliases as in the psychopy scripts;
const { abs, sin, cos, PI: pi, sqrt } = Math;
const { round } = util;


// store info about the experiment session:
let expName = 'maxForce';  // from the Builder filename that created this script
let expInfo = {
    'participant': `${util.pad(Number.parseFloat(util.randint(0, 999999)).toFixed(0), 6)}`,
    'session': '001',
};
let PILOTING = util.getUrlParameters().has('__pilotToken');

// Start code blocks for 'Before Experiment'
// init psychoJS:
const psychoJS = new PsychoJS({
  debug: true
});

// open window:
psychoJS.openWindow({
  fullscr: true,
  color: new util.Color([0,0,0]),
  units: 'height',
  waitBlanking: true,
  backgroundImage: '',
  backgroundFit: 'none',
});
// schedule the experiment:
psychoJS.schedule(psychoJS.gui.DlgFromDict({
  dictionary: expInfo,
  title: expName
}));

const flowScheduler = new Scheduler(psychoJS);
const dialogCancelScheduler = new Scheduler(psychoJS);
psychoJS.scheduleCondition(function() { return (psychoJS.gui.dialogComponent.button === 'OK'); },flowScheduler, dialogCancelScheduler);

// flowScheduler gets run if the participants presses OK
flowScheduler.add(updateInfo); // add timeStamp
flowScheduler.add(experimentInit);
flowScheduler.add(setupRoutineBegin());
flowScheduler.add(setupRoutineEachFrame());
flowScheduler.add(setupRoutineEnd());
const loop_mvc_blockLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(loop_mvc_blockLoopBegin(loop_mvc_blockLoopScheduler));
flowScheduler.add(loop_mvc_blockLoopScheduler);
flowScheduler.add(loop_mvc_blockLoopEnd);





const domainLoopLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(domainLoopLoopBegin(domainLoopLoopScheduler));
flowScheduler.add(domainLoopLoopScheduler);
flowScheduler.add(domainLoopLoopEnd);















flowScheduler.add(quitPsychoJS, 'Thank you for your patience.', true);

// quit if user presses Cancel in dialog box:
dialogCancelScheduler.add(quitPsychoJS, 'Thank you for your patience.', false);

psychoJS.start({
  expName: expName,
  expInfo: expInfo,
  resources: [
    // resources:
    {'name': 'mvc_block.xlsx', 'path': 'mvc_block.xlsx'},
    {'name': 'domainLoop.xlsx', 'path': 'domainLoop.xlsx'},
    {'name': 'sliderResponse.xlsx', 'path': 'sliderResponse.xlsx'},
  ]
});

psychoJS.experimentLogger.setLevel(core.Logger.ServerLevel.INFO);

async function updateInfo() {
  currentLoop = psychoJS.experiment;  // right now there are no loops
  expInfo['date'] = util.MonotonicClock.getDateStr();  // add a simple timestamp
  expInfo['expName'] = expName;
  expInfo['psychopyVersion'] = '2026.1.1';
  expInfo['OS'] = window.navigator.platform;


  // store frame rate of monitor if we can measure it successfully
  expInfo['frameRate'] = psychoJS.window.getActualFrameRate();
  if (typeof expInfo['frameRate'] !== 'undefined')
    frameDur = 1.0 / Math.round(expInfo['frameRate']);
  else
    frameDur = 1.0 / 60.0; // couldn't get a reliable measure so guess

  // add info from the URL:
  util.addInfoFromUrl(expInfo);
  

  
  psychoJS.experiment.dataFileName = (("." + "/") + `data/${expInfo["participant"]}_${expName}_${expInfo["date"]}`);
  psychoJS.experiment.field_separator = '\t';


  return Scheduler.Event.NEXT;
}

async function experimentInit() {
  // Initialize components for Routine "setup"
  setupClock = new util.Clock();
  // Initialize components for Routine "countdown"
  countdownClock = new util.Clock();
  countdown_text = new visual.TextStim({
    win: psychoJS.window,
    name: 'countdown_text',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.2,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -1.0 
  });
  
  // Initialize components for Routine "mvc"
  mvcClock = new util.Clock();
  // Run 'Begin Experiment' code from code_2
  mvc_max_experimental = 0;
  
  mvc_keyboard = new core.Keyboard({psychoJS: psychoJS, clock: new util.Clock(), waitForStart: true});
  
  text = new visual.TextStim({
    win: psychoJS.window,
    name: 'text',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -2.0 
  });
  
  // Initialize components for Routine "targetColorBalance"
  targetColorBalanceClock = new util.Clock();
  // Initialize components for Routine "target_presentation"
  target_presentationClock = new util.Clock();
  targetText = new visual.TextStim({
    win: psychoJS.window,
    name: 'targetText',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -2.0 
  });
  
  // Initialize components for Routine "task"
  taskClock = new util.Clock();
  taskText = new visual.TextStim({
    win: psychoJS.window,
    name: 'taskText',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -1.0 
  });
  
  // Initialize components for Routine "postTask"
  postTaskClock = new util.Clock();
  dprimeText = new visual.TextStim({
    win: psychoJS.window,
    name: 'dprimeText',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: 0.0 
  });
  
  dprimeKeyResp = new core.Keyboard({psychoJS: psychoJS, clock: new util.Clock(), waitForStart: true});
  
  // Initialize components for Routine "slider"
  sliderClock = new util.Clock();
  EffortRating = new visual.Slider({
    win: psychoJS.window, name: 'EffortRating',
    startValue: undefined,
    size: [1.0, 0.1], pos: [0, (- 0.2)], ori: 0.0, units: psychoJS.window.units,
    labels: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], fontSize: 0.05, ticks: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    granularity: 1.0, style: ["RATING"],
    color: new util.Color('LightGray'), markerColor: new util.Color('Red'), lineColor: new util.Color('White'), 
    opacity: undefined, fontFamily: 'Noto Sans', bold: true, italic: false, depth: 0, 
    flip: false,
  });
  
  sliderText = new visual.TextStim({
    win: psychoJS.window,
    name: 'sliderText',
    text: '',
    font: 'Arial',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -1.0 
  });
  
  keyRespSlider = new core.Keyboard({psychoJS: psychoJS, clock: new util.Clock(), waitForStart: true});
  
  // Create some handy timers
  globalClock = new util.Clock();  // to track the time since experiment started
  routineTimer = new util.CountdownTimer();  // to track time remaining of each (non-slip) routine
  
  return Scheduler.Event.NEXT;
}

function setupRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'setup' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    // keep track of whether this Routine was forcibly ended
    routineForceEnded = false;
    setupClock.reset();
    routineTimer.reset();
    setupMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('setup.started', globalClock.getTime());
    setupMaxDuration = null
    // keep track of which components have finished
    setupComponents = [];
    
    for (const thisComponent of setupComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function setupRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'setup' ---
    // get current time
    t = setupClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      routineForceEnded = true;
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of setupComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function setupRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'setup' ---
    for (const thisComponent of setupComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('setup.stopped', globalClock.getTime());
    // the Routine "setup" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function loop_mvc_blockLoopBegin(loop_mvc_blockLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    loop_mvc_block = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 1, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: 'mvc_block.xlsx',
      seed: undefined, name: 'loop_mvc_block'
    });
    psychoJS.experiment.addLoop(loop_mvc_block); // add the loop to the experiment
    currentLoop = loop_mvc_block;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisLoop_mvc_block of loop_mvc_block) {
      snapshot = loop_mvc_block.getSnapshot();
      loop_mvc_blockLoopScheduler.add(importConditions(snapshot));
      const loop_mvc_trialLoopScheduler = new Scheduler(psychoJS);
      loop_mvc_blockLoopScheduler.add(loop_mvc_trialLoopBegin(loop_mvc_trialLoopScheduler, snapshot));
      loop_mvc_blockLoopScheduler.add(loop_mvc_trialLoopScheduler);
      loop_mvc_blockLoopScheduler.add(loop_mvc_trialLoopEnd);
      loop_mvc_blockLoopScheduler.add(loop_mvc_blockLoopEndIteration(loop_mvc_blockLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

function loop_mvc_trialLoopBegin(loop_mvc_trialLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    loop_mvc_trial = new TrialHandler({
      psychoJS: psychoJS,
      nReps: mvc_trial_nrepeat, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'loop_mvc_trial'
    });
    psychoJS.experiment.addLoop(loop_mvc_trial); // add the loop to the experiment
    currentLoop = loop_mvc_trial;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisLoop_mvc_trial of loop_mvc_trial) {
      snapshot = loop_mvc_trial.getSnapshot();
      loop_mvc_trialLoopScheduler.add(importConditions(snapshot));
      loop_mvc_trialLoopScheduler.add(countdownRoutineBegin(snapshot));
      loop_mvc_trialLoopScheduler.add(countdownRoutineEachFrame());
      loop_mvc_trialLoopScheduler.add(countdownRoutineEnd(snapshot));
      loop_mvc_trialLoopScheduler.add(mvcRoutineBegin(snapshot));
      loop_mvc_trialLoopScheduler.add(mvcRoutineEachFrame());
      loop_mvc_trialLoopScheduler.add(mvcRoutineEnd(snapshot));
      loop_mvc_trialLoopScheduler.add(loop_mvc_trialLoopEndIteration(loop_mvc_trialLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function loop_mvc_trialLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(loop_mvc_trial);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function loop_mvc_trialLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

async function loop_mvc_blockLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(loop_mvc_block);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function loop_mvc_blockLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function domainLoopLoopBegin(domainLoopLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    domainLoop = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 1, method: TrialHandler.Method.RANDOM,
      extraInfo: expInfo, originPath: undefined,
      trialList: 'domainLoop.xlsx',
      seed: undefined, name: 'domainLoop'
    });
    psychoJS.experiment.addLoop(domainLoop); // add the loop to the experiment
    currentLoop = domainLoop;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisDomainLoop of domainLoop) {
      snapshot = domainLoop.getSnapshot();
      domainLoopLoopScheduler.add(importConditions(snapshot));
      domainLoopLoopScheduler.add(targetColorBalanceRoutineBegin(snapshot));
      domainLoopLoopScheduler.add(targetColorBalanceRoutineEachFrame());
      domainLoopLoopScheduler.add(targetColorBalanceRoutineEnd(snapshot));
      const blockLoopLoopScheduler = new Scheduler(psychoJS);
      domainLoopLoopScheduler.add(blockLoopLoopBegin(blockLoopLoopScheduler, snapshot));
      domainLoopLoopScheduler.add(blockLoopLoopScheduler);
      domainLoopLoopScheduler.add(blockLoopLoopEnd);
      domainLoopLoopScheduler.add(domainLoopLoopEndIteration(domainLoopLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

function blockLoopLoopBegin(blockLoopLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    blockLoop = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 3, method: TrialHandler.Method.RANDOM,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'blockLoop'
    });
    psychoJS.experiment.addLoop(blockLoop); // add the loop to the experiment
    currentLoop = blockLoop;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisBlockLoop of blockLoop) {
      snapshot = blockLoop.getSnapshot();
      blockLoopLoopScheduler.add(importConditions(snapshot));
      blockLoopLoopScheduler.add(countdownRoutineBegin(snapshot));
      blockLoopLoopScheduler.add(countdownRoutineEachFrame());
      blockLoopLoopScheduler.add(countdownRoutineEnd(snapshot));
      const levelLoopLoopScheduler = new Scheduler(psychoJS);
      blockLoopLoopScheduler.add(levelLoopLoopBegin(levelLoopLoopScheduler, snapshot));
      blockLoopLoopScheduler.add(levelLoopLoopScheduler);
      blockLoopLoopScheduler.add(levelLoopLoopEnd);
      blockLoopLoopScheduler.add(blockLoopLoopEndIteration(blockLoopLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

function levelLoopLoopBegin(levelLoopLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    levelLoop = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 6, method: TrialHandler.Method.RANDOM,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'levelLoop'
    });
    psychoJS.experiment.addLoop(levelLoop); // add the loop to the experiment
    currentLoop = levelLoop;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisLevelLoop of levelLoop) {
      snapshot = levelLoop.getSnapshot();
      levelLoopLoopScheduler.add(importConditions(snapshot));
      levelLoopLoopScheduler.add(target_presentationRoutineBegin(snapshot));
      levelLoopLoopScheduler.add(target_presentationRoutineEachFrame());
      levelLoopLoopScheduler.add(target_presentationRoutineEnd(snapshot));
      const paletteLoopLoopScheduler = new Scheduler(psychoJS);
      levelLoopLoopScheduler.add(paletteLoopLoopBegin(paletteLoopLoopScheduler, snapshot));
      levelLoopLoopScheduler.add(paletteLoopLoopScheduler);
      levelLoopLoopScheduler.add(paletteLoopLoopEnd);
      levelLoopLoopScheduler.add(postTaskRoutineBegin(snapshot));
      levelLoopLoopScheduler.add(postTaskRoutineEachFrame());
      levelLoopLoopScheduler.add(postTaskRoutineEnd(snapshot));
      const sliderLoopLoopScheduler = new Scheduler(psychoJS);
      levelLoopLoopScheduler.add(sliderLoopLoopBegin(sliderLoopLoopScheduler, snapshot));
      levelLoopLoopScheduler.add(sliderLoopLoopScheduler);
      levelLoopLoopScheduler.add(sliderLoopLoopEnd);
      levelLoopLoopScheduler.add(levelLoopLoopEndIteration(levelLoopLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

function paletteLoopLoopBegin(paletteLoopLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    paletteLoop = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 10, method: TrialHandler.Method.RANDOM,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'paletteLoop'
    });
    psychoJS.experiment.addLoop(paletteLoop); // add the loop to the experiment
    currentLoop = paletteLoop;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisPaletteLoop of paletteLoop) {
      snapshot = paletteLoop.getSnapshot();
      paletteLoopLoopScheduler.add(importConditions(snapshot));
      paletteLoopLoopScheduler.add(taskRoutineBegin(snapshot));
      paletteLoopLoopScheduler.add(taskRoutineEachFrame());
      paletteLoopLoopScheduler.add(taskRoutineEnd(snapshot));
      paletteLoopLoopScheduler.add(paletteLoopLoopEndIteration(paletteLoopLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function paletteLoopLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(paletteLoop);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function paletteLoopLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function sliderLoopLoopBegin(sliderLoopLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    sliderLoop = new TrialHandler({
      psychoJS: psychoJS,
      nReps: 1, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: 'sliderResponse.xlsx',
      seed: undefined, name: 'sliderLoop'
    });
    psychoJS.experiment.addLoop(sliderLoop); // add the loop to the experiment
    currentLoop = sliderLoop;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisSliderLoop of sliderLoop) {
      snapshot = sliderLoop.getSnapshot();
      sliderLoopLoopScheduler.add(importConditions(snapshot));
      sliderLoopLoopScheduler.add(sliderRoutineBegin(snapshot));
      sliderLoopLoopScheduler.add(sliderRoutineEachFrame());
      sliderLoopLoopScheduler.add(sliderRoutineEnd(snapshot));
      sliderLoopLoopScheduler.add(sliderLoopLoopEndIteration(sliderLoopLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function sliderLoopLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(sliderLoop);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function sliderLoopLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

async function levelLoopLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(levelLoop);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function levelLoopLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

async function blockLoopLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(blockLoop);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function blockLoopLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

async function domainLoopLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(domainLoop);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function domainLoopLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function countdownRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'countdown' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    // keep track of whether this Routine was forcibly ended
    routineForceEnded = false;
    countdownClock.reset();
    routineTimer.reset();
    countdownMaxDurationReached = false;
    // update component parameters for each repeat
    // Run 'Begin Routine' code from countdown_code
    
            // add-on: list(s: string): string[]
            function list(s) {
                // if s is a string, we return a list of its characters
                if (typeof s === 'string')
                    return s.split('');
                else
                    // otherwise we return s:
                    return s;
            }
    
            import {Color} from 'psychopy/colors';
    countdown_holes = list(util.range(8));
    countdown_current_index = countdown_holes.length;
    countdown_last_update = null;
    countdown_interval = 0.5;
    if ((countdown_current_index > 0)) {
        active_holes = countdown_holes.slice(0, countdown_current_index);
        countdown_led.setHoleLights(active_holes, new Color("white"));
    }
    
    psychoJS.experiment.addData('countdown.started', globalClock.getTime());
    countdownMaxDuration = null
    // keep track of which components have finished
    countdownComponents = [];
    countdownComponents.push(countdown_text);
    
    for (const thisComponent of countdownComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function countdownRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'countdown' ---
    // get current time
    t = countdownClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // Run 'Each Frame' code from countdown_code
    if ((countdown_last_update === null)) {
        countdown_last_update = t;
    }
    if (((t - countdown_last_update) >= countdown_interval)) {
        countdown_current_index -= 1;
        countdown_last_update = t;
        if ((countdown_current_index > 0)) {
            active_holes = countdown_holes.slice(0, countdown_current_index);
            countdown_led.setHoleLights(active_holes, new Color("white"));
            inactive_holes = countdown_holes.slice(countdown_current_index);
            countdown_led.turnOffHoleLights(inactive_holes);
        } else {
            countdown_led.turnOffHoleLights("outer");
            continueRoutine = false;
        }
    }
    
    
    // *countdown_text* updates
    if (t >= 0.0 && countdown_text.status === PsychoJS.Status.NOT_STARTED) {
      // update params
      countdown_text.setText(countdown_current_index, false);
      // keep track of start time/frame for later
      countdown_text.tStart = t;  // (not accounting for frame time here)
      countdown_text.frameNStart = frameN;  // exact frame index
      
      countdown_text.setAutoDraw(true);
    }
    
    
    // if countdown_text is active this frame...
    if (countdown_text.status === PsychoJS.Status.STARTED) {
      // update params
      countdown_text.setText(countdown_current_index, false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      routineForceEnded = true;
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of countdownComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function countdownRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'countdown' ---
    for (const thisComponent of countdownComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('countdown.stopped', globalClock.getTime());
    // the Routine "countdown" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function mvcRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'mvc' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    // keep track of whether this Routine was forcibly ended
    routineForceEnded = false;
    mvcClock.reset();
    routineTimer.reset();
    mvcMaxDurationReached = false;
    // update component parameters for each repeat
    // Run 'Begin Routine' code from code_2
    mvc_max_trial = 0;
    
    mvc_keyboard.keys = undefined;
    mvc_keyboard.rt = undefined;
    _mvc_keyboard_allKeys = [];
    psychoJS.experiment.addData('mvc.started', globalClock.getTime());
    mvcMaxDuration = null
    // keep track of which components have finished
    mvcComponents = [];
    mvcComponents.push(mvc_keyboard);
    mvcComponents.push(text);
    
    for (const thisComponent of mvcComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function mvcRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'mvc' ---
    // get current time
    t = mvcClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // Run 'Each Frame' code from code_2
    if ((apparatusForce.maxWhiteForce > mvc_max_trial)) {
        mvc_max_trial = apparatusForce.maxWhiteForce;
    }
    if ((mvc_trial_type === "experimental")) {
        if ((mvc_max_trial > mvc_max_experimental)) {
            mvc_max_experimental = mvc_max_trial;
        }
    }
    
    
    // *mvc_keyboard* updates
    if (t >= 3.0 && mvc_keyboard.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mvc_keyboard.tStart = t;  // (not accounting for frame time here)
      mvc_keyboard.frameNStart = frameN;  // exact frame index
      
      // keyboard checking is just starting
      psychoJS.window.callOnFlip(function() { mvc_keyboard.clock.reset(); });  // t=0 on next screen flip
      psychoJS.window.callOnFlip(function() { mvc_keyboard.start(); }); // start on screen flip
      psychoJS.window.callOnFlip(function() { mvc_keyboard.clearEvents(); });
    }
    frameRemains = 3.0 + mvc_trial_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (mvc_keyboard.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      // keep track of stop time/frame for later
      mvc_keyboard.tStop = t;  // not accounting for scr refresh
      mvc_keyboard.frameNStop = frameN;  // exact frame index
      // update status
      mvc_keyboard.status = PsychoJS.Status.FINISHED;
      frameRemains = 3.0 + mvc_trial_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
      if (mvc_keyboard.status === PsychoJS.Status.STARTED && t >= frameRemains) {
        // keep track of stop time/frame for later
        mvc_keyboard.tStop = t;  // not accounting for scr refresh
        mvc_keyboard.frameNStop = frameN;  // exact frame index
        // update status
        mvc_keyboard.status = PsychoJS.Status.FINISHED;
        mvc_keyboard.status = PsychoJS.Status.FINISHED;
          }
        
      }
      
      // if mvc_keyboard is active this frame...
      if (mvc_keyboard.status === PsychoJS.Status.STARTED) {
        let theseKeys = mvc_keyboard.getKeys({
          keyList: typeof ['y','n','left','right','space'] === 'string' ? [['y','n','left','right','space']] : ['y','n','left','right','space'], 
          waitRelease: false
        });
        _mvc_keyboard_allKeys = _mvc_keyboard_allKeys.concat(theseKeys);
        if (_mvc_keyboard_allKeys.length > 0) {
          mvc_keyboard.keys = _mvc_keyboard_allKeys[_mvc_keyboard_allKeys.length - 1].name;  // just the last key pressed
          mvc_keyboard.rt = _mvc_keyboard_allKeys[_mvc_keyboard_allKeys.length - 1].rt;
          mvc_keyboard.duration = _mvc_keyboard_allKeys[_mvc_keyboard_allKeys.length - 1].duration;
          // a response ends the routine
          continueRoutine = false;
        }
      }
      
      
      // *text* updates
      if (t >= 0.0 && text.status === PsychoJS.Status.NOT_STARTED) {
        // update params
        text.setText(f'''Trial Type: {mvc_trial_type}
        
        Force: {apparatusForce.whiteForce}
        
        Max Experimental: {mvc_max_experimental}''', false);
        // keep track of start time/frame for later
        text.tStart = t;  // (not accounting for frame time here)
        text.frameNStart = frameN;  // exact frame index
        
        text.setAutoDraw(true);
      }
      
      
      // if text is active this frame...
      if (text.status === PsychoJS.Status.STARTED) {
        // update params
        text.setText(f'''Trial Type: {mvc_trial_type}
        
        Force: {apparatusForce.whiteForce}
        
        Max Experimental: {mvc_max_experimental}''', false);
      }
      
      frameRemains = 0.0 + 45 - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
      if (text.status === PsychoJS.Status.STARTED && t >= frameRemains) {
        // keep track of stop time/frame for later
        text.tStop = t;  // not accounting for scr refresh
        text.frameNStop = frameN;  // exact frame index
        // update status
        text.status = PsychoJS.Status.FINISHED;
        text.setAutoDraw(false);
      }
      
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of mvcComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function mvcRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'mvc' ---
      for (const thisComponent of mvcComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('mvc.stopped', globalClock.getTime());
      // Run 'End Routine' code from code_2
      console.log(`Maximum force across all experimental trials: ${mvc_max_experimental}`);
      
      // update the trial handler
      if (currentLoop instanceof MultiStairHandler) {
        currentLoop.addResponse(mvc_keyboard.corr, level);
      }
      psychoJS.experiment.addData('mvc_keyboard.keys', mvc_keyboard.keys);
      if (typeof mvc_keyboard.keys !== 'undefined') {  // we had a response
          psychoJS.experiment.addData('mvc_keyboard.rt', mvc_keyboard.rt);
          psychoJS.experiment.addData('mvc_keyboard.duration', mvc_keyboard.duration);
          routineTimer.reset();
          }
      
      mvc_keyboard.stop();
      // the Routine "mvc" was not non-slip safe, so reset the non-slip timer
      routineTimer.reset();
      
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function targetColorBalanceRoutineBegin(snapshot) {
    return async function () {
      TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
      
      //--- Prepare to start Routine 'targetColorBalance' ---
      t = 0;
      frameN = -1;
      continueRoutine = true; // until we're told otherwise
      // keep track of whether this Routine was forcibly ended
      routineForceEnded = false;
      targetColorBalanceClock.reset();
      routineTimer.reset();
      targetColorBalanceMaxDurationReached = false;
      // update component parameters for each repeat
      psychoJS.experiment.addData('targetColorBalance.started', globalClock.getTime());
      targetColorBalanceMaxDuration = null
      // keep track of which components have finished
      targetColorBalanceComponents = [];
      
      for (const thisComponent of targetColorBalanceComponents)
        if ('status' in thisComponent)
          thisComponent.status = PsychoJS.Status.NOT_STARTED;
      return Scheduler.Event.NEXT;
    }
  }
  
  function targetColorBalanceRoutineEachFrame() {
    return async function () {
      //--- Loop for each frame of Routine 'targetColorBalance' ---
      // get current time
      t = targetColorBalanceClock.getTime();
      frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
      // update/draw components on each frame
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of targetColorBalanceComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function targetColorBalanceRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'targetColorBalance' ---
      for (const thisComponent of targetColorBalanceComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('targetColorBalance.stopped', globalClock.getTime());
      // the Routine "targetColorBalance" was not non-slip safe, so reset the non-slip timer
      routineTimer.reset();
      
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function target_presentationRoutineBegin(snapshot) {
    return async function () {
      TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
      
      //--- Prepare to start Routine 'target_presentation' ---
      t = 0;
      frameN = -1;
      continueRoutine = true; // until we're told otherwise
      // keep track of whether this Routine was forcibly ended
      routineForceEnded = false;
      target_presentationClock.reset(routineTimer.getTime());
      routineTimer.add(3.000000);
      target_presentationMaxDurationReached = false;
      // update component parameters for each repeat
      targetText.setText(`Color: ${targetColor}, Force: ${practiceForce.whiteForce}`);
      psychoJS.experiment.addData('target_presentation.started', globalClock.getTime());
      target_presentationMaxDuration = null
      // keep track of which components have finished
      target_presentationComponents = [];
      target_presentationComponents.push(targetText);
      
      for (const thisComponent of target_presentationComponents)
        if ('status' in thisComponent)
          thisComponent.status = PsychoJS.Status.NOT_STARTED;
      return Scheduler.Event.NEXT;
    }
  }
  
  function target_presentationRoutineEachFrame() {
    return async function () {
      //--- Loop for each frame of Routine 'target_presentation' ---
      // get current time
      t = target_presentationClock.getTime();
      frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
      // update/draw components on each frame
      
      // *targetText* updates
      if (t >= 0.0 && targetText.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        targetText.tStart = t;  // (not accounting for frame time here)
        targetText.frameNStart = frameN;  // exact frame index
        
        targetText.setAutoDraw(true);
      }
      
      
      // if targetText is active this frame...
      if (targetText.status === PsychoJS.Status.STARTED) {
      }
      
      frameRemains = 0.0 + 3.0 - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
      if (targetText.status === PsychoJS.Status.STARTED && t >= frameRemains) {
        // keep track of stop time/frame for later
        targetText.tStop = t;  // not accounting for scr refresh
        targetText.frameNStop = frameN;  // exact frame index
        // update status
        targetText.status = PsychoJS.Status.FINISHED;
        targetText.setAutoDraw(false);
      }
      
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of target_presentationComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine && routineTimer.getTime() > 0) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function target_presentationRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'target_presentation' ---
      for (const thisComponent of target_presentationComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('target_presentation.stopped', globalClock.getTime());
      if (routineForceEnded) {
          routineTimer.reset();} else if (target_presentationMaxDurationReached) {
          target_presentationClock.add(target_presentationMaxDuration);
      } else {
          target_presentationClock.add(3.000000);
      }
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function taskRoutineBegin(snapshot) {
    return async function () {
      TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
      
      //--- Prepare to start Routine 'task' ---
      t = 0;
      frameN = -1;
      continueRoutine = true; // until we're told otherwise
      // keep track of whether this Routine was forcibly ended
      routineForceEnded = false;
      taskClock.reset(routineTimer.getTime());
      routineTimer.add(1.416000);
      taskMaxDurationReached = false;
      // update component parameters for each repeat
      taskText.setText(`Palette: ${index}, deltaE: ${deltaE}, Kraftlevel: ${mvcLevel}`);
      psychoJS.experiment.addData('task.started', globalClock.getTime());
      taskMaxDuration = null
      // keep track of which components have finished
      taskComponents = [];
      taskComponents.push(taskText);
      
      for (const thisComponent of taskComponents)
        if ('status' in thisComponent)
          thisComponent.status = PsychoJS.Status.NOT_STARTED;
      return Scheduler.Event.NEXT;
    }
  }
  
  function taskRoutineEachFrame() {
    return async function () {
      //--- Loop for each frame of Routine 'task' ---
      // get current time
      t = taskClock.getTime();
      frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
      // update/draw components on each frame
      
      // *taskText* updates
      if (t >= 0.0 && taskText.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        taskText.tStart = t;  // (not accounting for frame time here)
        taskText.frameNStart = frameN;  // exact frame index
        
        taskText.setAutoDraw(true);
      }
      
      
      // if taskText is active this frame...
      if (taskText.status === PsychoJS.Status.STARTED) {
      }
      
      frameRemains = 0.0 + 1.416 - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
      if (taskText.status === PsychoJS.Status.STARTED && t >= frameRemains) {
        // keep track of stop time/frame for later
        taskText.tStop = t;  // not accounting for scr refresh
        taskText.frameNStop = frameN;  // exact frame index
        // update status
        taskText.status = PsychoJS.Status.FINISHED;
        taskText.setAutoDraw(false);
      }
      
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of taskComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine && routineTimer.getTime() > 0) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function taskRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'task' ---
      for (const thisComponent of taskComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('task.stopped', globalClock.getTime());
      if (routineForceEnded) {
          routineTimer.reset();} else if (taskMaxDurationReached) {
          taskClock.add(taskMaxDuration);
      } else {
          taskClock.add(1.416000);
      }
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function postTaskRoutineBegin(snapshot) {
    return async function () {
      TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
      
      //--- Prepare to start Routine 'postTask' ---
      t = 0;
      frameN = -1;
      continueRoutine = true; // until we're told otherwise
      // keep track of whether this Routine was forcibly ended
      routineForceEnded = false;
      postTaskClock.reset();
      routineTimer.reset();
      postTaskMaxDurationReached = false;
      // update component parameters for each repeat
      dprimeKeyResp.keys = undefined;
      dprimeKeyResp.rt = undefined;
      _dprimeKeyResp_allKeys = [];
      psychoJS.experiment.addData('postTask.started', globalClock.getTime());
      postTaskMaxDuration = null
      // keep track of which components have finished
      postTaskComponents = [];
      postTaskComponents.push(dprimeText);
      postTaskComponents.push(dprimeKeyResp);
      
      for (const thisComponent of postTaskComponents)
        if ('status' in thisComponent)
          thisComponent.status = PsychoJS.Status.NOT_STARTED;
      return Scheduler.Event.NEXT;
    }
  }
  
  function postTaskRoutineEachFrame() {
    return async function () {
      //--- Loop for each frame of Routine 'postTask' ---
      // get current time
      t = postTaskClock.getTime();
      frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
      // update/draw components on each frame
      
      // *dprimeText* updates
      if (t >= 0 && dprimeText.status === PsychoJS.Status.NOT_STARTED) {
        // update params
        dprimeText.setText((('Last dprime: ' + str(dprime)) + '\n')
        (('Hits: ' + str(hits)) + '\n')
        (('Misses: ' + str(misses)) + '\n')
        (('False alarms: ' + str(false_alarms)) + '\n')
        (('Correct rejections: ' + str(correct_rejections)) + '\n'), false);
        // keep track of start time/frame for later
        dprimeText.tStart = t;  // (not accounting for frame time here)
        dprimeText.frameNStart = frameN;  // exact frame index
        
        dprimeText.setAutoDraw(true);
      }
      
      
      // if dprimeText is active this frame...
      if (dprimeText.status === PsychoJS.Status.STARTED) {
        // update params
        dprimeText.setText((('Last dprime: ' + str(dprime)) + '\n')
        (('Hits: ' + str(hits)) + '\n')
        (('Misses: ' + str(misses)) + '\n')
        (('False alarms: ' + str(false_alarms)) + '\n')
        (('Correct rejections: ' + str(correct_rejections)) + '\n'), false);
      }
      
      
      // *dprimeKeyResp* updates
      if (t >= 0.0 && dprimeKeyResp.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        dprimeKeyResp.tStart = t;  // (not accounting for frame time here)
        dprimeKeyResp.frameNStart = frameN;  // exact frame index
        
        // keyboard checking is just starting
        psychoJS.window.callOnFlip(function() { dprimeKeyResp.clock.reset(); });  // t=0 on next screen flip
        psychoJS.window.callOnFlip(function() { dprimeKeyResp.start(); }); // start on screen flip
        psychoJS.window.callOnFlip(function() { dprimeKeyResp.clearEvents(); });
      }
      
      // if dprimeKeyResp is active this frame...
      if (dprimeKeyResp.status === PsychoJS.Status.STARTED) {
        let theseKeys = dprimeKeyResp.getKeys({
          keyList: typeof 'space' === 'string' ? ['space'] : 'space', 
          waitRelease: false
        });
        _dprimeKeyResp_allKeys = _dprimeKeyResp_allKeys.concat(theseKeys);
        if (_dprimeKeyResp_allKeys.length > 0) {
          dprimeKeyResp.keys = _dprimeKeyResp_allKeys[_dprimeKeyResp_allKeys.length - 1].name;  // just the last key pressed
          dprimeKeyResp.rt = _dprimeKeyResp_allKeys[_dprimeKeyResp_allKeys.length - 1].rt;
          dprimeKeyResp.duration = _dprimeKeyResp_allKeys[_dprimeKeyResp_allKeys.length - 1].duration;
          // a response ends the routine
          continueRoutine = false;
        }
      }
      
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of postTaskComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function postTaskRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'postTask' ---
      for (const thisComponent of postTaskComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('postTask.stopped', globalClock.getTime());
      // update the trial handler
      if (currentLoop instanceof MultiStairHandler) {
        currentLoop.addResponse(dprimeKeyResp.corr, level);
      }
      psychoJS.experiment.addData('dprimeKeyResp.keys', dprimeKeyResp.keys);
      if (typeof dprimeKeyResp.keys !== 'undefined') {  // we had a response
          psychoJS.experiment.addData('dprimeKeyResp.rt', dprimeKeyResp.rt);
          psychoJS.experiment.addData('dprimeKeyResp.duration', dprimeKeyResp.duration);
          routineTimer.reset();
          }
      
      dprimeKeyResp.stop();
      // the Routine "postTask" was not non-slip safe, so reset the non-slip timer
      routineTimer.reset();
      
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function sliderRoutineBegin(snapshot) {
    return async function () {
      TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
      
      //--- Prepare to start Routine 'slider' ---
      t = 0;
      frameN = -1;
      continueRoutine = true; // until we're told otherwise
      // keep track of whether this Routine was forcibly ended
      routineForceEnded = false;
      sliderClock.reset();
      routineTimer.reset();
      sliderMaxDurationReached = false;
      // update component parameters for each repeat
      EffortRating.reset()
      sliderText.setText(`${sliderResponse} Effort`);
      keyRespSlider.keys = undefined;
      keyRespSlider.rt = undefined;
      _keyRespSlider_allKeys = [];
      psychoJS.experiment.addData('slider.started', globalClock.getTime());
      sliderMaxDuration = null
      // keep track of which components have finished
      sliderComponents = [];
      sliderComponents.push(EffortRating);
      sliderComponents.push(sliderText);
      sliderComponents.push(keyRespSlider);
      
      for (const thisComponent of sliderComponents)
        if ('status' in thisComponent)
          thisComponent.status = PsychoJS.Status.NOT_STARTED;
      return Scheduler.Event.NEXT;
    }
  }
  
  function sliderRoutineEachFrame() {
    return async function () {
      //--- Loop for each frame of Routine 'slider' ---
      // get current time
      t = sliderClock.getTime();
      frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
      // update/draw components on each frame
      
      // *EffortRating* updates
      if (t >= 0.0 && EffortRating.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        EffortRating.tStart = t;  // (not accounting for frame time here)
        EffortRating.frameNStart = frameN;  // exact frame index
        
        EffortRating.setAutoDraw(true);
      }
      
      
      // if EffortRating is active this frame...
      if (EffortRating.status === PsychoJS.Status.STARTED) {
      }
      
      
      // *sliderText* updates
      if (t >= 0.0 && sliderText.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        sliderText.tStart = t;  // (not accounting for frame time here)
        sliderText.frameNStart = frameN;  // exact frame index
        
        sliderText.setAutoDraw(true);
      }
      
      
      // if sliderText is active this frame...
      if (sliderText.status === PsychoJS.Status.STARTED) {
      }
      
      
      // *keyRespSlider* updates
      if (t >= 0.0 && keyRespSlider.status === PsychoJS.Status.NOT_STARTED) {
        // keep track of start time/frame for later
        keyRespSlider.tStart = t;  // (not accounting for frame time here)
        keyRespSlider.frameNStart = frameN;  // exact frame index
        
        // keyboard checking is just starting
        psychoJS.window.callOnFlip(function() { keyRespSlider.clock.reset(); });  // t=0 on next screen flip
        psychoJS.window.callOnFlip(function() { keyRespSlider.start(); }); // start on screen flip
        psychoJS.window.callOnFlip(function() { keyRespSlider.clearEvents(); });
      }
      
      // if keyRespSlider is active this frame...
      if (keyRespSlider.status === PsychoJS.Status.STARTED) {
        let theseKeys = keyRespSlider.getKeys({
          keyList: typeof 'space' === 'string' ? ['space'] : 'space', 
          waitRelease: false
        });
        _keyRespSlider_allKeys = _keyRespSlider_allKeys.concat(theseKeys);
        if (_keyRespSlider_allKeys.length > 0) {
          keyRespSlider.keys = _keyRespSlider_allKeys[_keyRespSlider_allKeys.length - 1].name;  // just the last key pressed
          keyRespSlider.rt = _keyRespSlider_allKeys[_keyRespSlider_allKeys.length - 1].rt;
          keyRespSlider.duration = _keyRespSlider_allKeys[_keyRespSlider_allKeys.length - 1].duration;
          // a response ends the routine
          continueRoutine = false;
        }
      }
      
      // check for quit (typically the Esc key)
      if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
        return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
      }
      
      // check if the Routine should terminate
      if (!continueRoutine) {  // a component has requested a forced-end of Routine
        routineForceEnded = true;
        return Scheduler.Event.NEXT;
      }
      
      continueRoutine = false;  // reverts to True if at least one component still running
      for (const thisComponent of sliderComponents)
        if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
          continueRoutine = true;
          break;
        }
      
      // refresh the screen if continuing
      if (continueRoutine) {
        return Scheduler.Event.FLIP_REPEAT;
      } else {
        return Scheduler.Event.NEXT;
      }
    };
  }
  
  function sliderRoutineEnd(snapshot) {
    return async function () {
      //--- Ending Routine 'slider' ---
      for (const thisComponent of sliderComponents) {
        if (typeof thisComponent.setAutoDraw === 'function') {
          thisComponent.setAutoDraw(false);
        }
      }
      psychoJS.experiment.addData('slider.stopped', globalClock.getTime());
      psychoJS.experiment.addData('EffortRating.response', EffortRating.getRating());
      psychoJS.experiment.addData('EffortRating.rt', EffortRating.getRT());
      // update the trial handler
      if (currentLoop instanceof MultiStairHandler) {
        currentLoop.addResponse(keyRespSlider.corr, level);
      }
      psychoJS.experiment.addData('keyRespSlider.keys', keyRespSlider.keys);
      if (typeof keyRespSlider.keys !== 'undefined') {  // we had a response
          psychoJS.experiment.addData('keyRespSlider.rt', keyRespSlider.rt);
          psychoJS.experiment.addData('keyRespSlider.duration', keyRespSlider.duration);
          routineTimer.reset();
          }
      
      keyRespSlider.stop();
      // the Routine "slider" was not non-slip safe, so reset the non-slip timer
      routineTimer.reset();
      
      // Routines running outside a loop should always advance the datafile row
      if (currentLoop === psychoJS.experiment) {
        psychoJS.experiment.nextEntry(snapshot);
      }
      return Scheduler.Event.NEXT;
    }
  }
  
  function importConditions(currentLoop) {
    return async function () {
      psychoJS.importAttributes(currentLoop.getCurrentTrial());
      return Scheduler.Event.NEXT;
      };
  }
  
  async function quitPsychoJS(message, isCompleted) {
    // Check for and save orphaned data
    if (psychoJS.experiment.isEntryEmpty()) {
      psychoJS.experiment.nextEntry();
    }
    psychoJS.window.close();
    psychoJS.quit({message: message, isCompleted: isCompleted});
    
    return Scheduler.Event.QUIT;
  }
