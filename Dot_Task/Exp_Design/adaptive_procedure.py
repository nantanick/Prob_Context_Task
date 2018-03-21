"""
adaptive_procedure.py
---------------------
Handles all the highlevel functions during the adaptive (calibration)
phase of the experiment. 

"""
from copy import deepcopy
import json
import numpy as np
from psychopy import core, event
from psychopy.data import QuestHandler, StairHandler
import os
import subprocess
import sys
from Dot_Task.Exp_Design.BaseExp import BaseExp
from Dot_Task.Exp_Design.flowstim import OpticFlow
from Dot_Task.Exp_Design.utils import get_total_trials, get_tracker_data
from Dot_Task.Analysis.utils import fit_response_fun

class adaptiveThreshold(BaseExp):
    """ class defining a probabilistic context task
    """
    
    def __init__(self,config_file,subjid,save_dir,verbose=True, 
                 num_practice=32, trackers=None, ignore_pedestal=True,
                 win_kwargs={}):
        # set up internal variables
        self.stimulusInfo = []
        self.loadedStimulusFile = []
        self.expClock = core.Clock()
        self.alldata = []
        self.aperture=None
        self.num_practice = num_practice
        self.pointtracker = 0
        self.track_response = []
        
        #looks up the hash of the most recent git push. Stored in log file
        self.gitHash = subprocess.check_output(['git','rev-parse','--short','HEAD'])[:-1]
        # load config file
        self.config_file = config_file
        try:
            self.loadConfigFile(config_file)
        except Exception as e:
            print('cannot load config file', e)
            sys.exit()
        # setup trackers
        if not trackers:
            self.trackers = self.defineTrackers('quest',
                                                ignore_pedestal)
        else:
            print('Loading trackers')
            self.trackers = trackers
        # init Base Exp
        super(adaptiveThreshold, self).__init__(self.taskname, subjid, 
                                                 save_dir, win_kwargs)

            
    #**************************************************************************
    # ******* Function to Save Data **************
    #**************************************************************************
    
    def toJSON(self):
        """ log the initial conditions for the task. Exclude the list of all
        trials (stimulusinfo), the bot, and taskinfo (self.__dict__ includes 
        all of the same information as taskinfo)
        """
        init_dict = {k:self.__dict__[k] for k in self.__dict__.keys() if k 
                    not in ('clock', 'stimulusInfo', 'alldata', 'bot', 'taskinfo','win')}
        return json.dumps(init_dict)
    
    #**************************************************************************
    # ******* Display Functions **************
    #**************************************************************************
    def defineStims(self, stim = None):
        height = 1
        ratio = .3
        if stim == None:
            self.stim = OpticFlow(self.win, 
                                 speed=self.base_speed,
                                 color=[1,1,1], 
                                 nElements = 2000,
                                 sizes=[height*ratio, height])
        else:
            self.stim = stim 
        # define fixation
        self.fixation = self.stim.fixation
    
    def defineTrackers(self, method='quest', ignore_pedestal=False):
        trackers = {}
        if self.ts == "motion":
            difficulties = self.speed_difficulties
            maxVal = self.base_speed*.9
        elif self.ts == "orientation":
            difficulties = self.ori_difficulties
            maxVal = 40 # no more than a 40 degree change
        if method=='basic':
            step_lookup = {.85: 5,
                           .775: 4,
                           .7: 3}
            for (pedestal, difficulty),val in difficulties.items():
                key = (pedestal,difficulty)
                nDown = step_lookup[difficulty]
                trackers[key] = StairHandler(startVal=val, minVal=0, 
                                             maxVal=maxVal,
                                             stepSizes=maxVal/10.0, 
                                             stepType='lin',
                                             nDown=nDown,
                                             nReversals=20,
                                             staircase=trackers.get(key,None))
        elif method=='quest':
            for (pedestal, difficulty), val in difficulties.items():
                key = (pedestal,difficulty)
                threshold = difficulty
                trackers[key] = QuestHandler(pThreshold=threshold,
                                             nTrials = 5000,
                                             startVal=val, startValSd=maxVal,
                                             minVal=0.00001, 
                                             maxVal=maxVal,
                                             gamma=.5,
                                             grain=maxVal/400.0,
                                             range=maxVal*2,
                                             beta=3.5,
                                             staircase=trackers.get(key,None))            
                
        if ignore_pedestal:
            difficulties = np.unique([i[1] for i in trackers.keys()])
            for d in difficulties:
                difficulty_keys = [k for k in trackers.keys() if d in k]
                for k in difficulty_keys:
                    trackers[k] = trackers[difficulty_keys[0]]
        return trackers
    
    def get_response_intensity(self, desired_acc):
        responses, intensities = get_tracker_data(self.trackers)
        estimate = self.alldata[-1]['quest_estimate']
        out, metrics = fit_response_fun(responses,
                                        intensities,
                                        estimate)
        return out.inverse(desired_acc)
        
        
    def presentPause(self):
        pauseClock = core.Clock()
        timer_text = "Take a break!\n\nContinue in: \n\n       "
        self.presentTimer(duration=20, text=timer_text)
        self.presentTextToWindow('Get Ready!', size=.15)
        core.wait(1.5)
        self.aperture.enable()
        pause_time = pauseClock.getTime()
        self.alldata.append({'exp_stage': 'pause',
                             'trial_time':  pause_time})
        return pause_time
    
    def presentTrial(self, trial, practice=False, intensity=None):
        """
        This function presents a stimuli, waits for a response, tracks the
        response and RT and presents appropriate feedback. 
        This function also controls the timing of FB 
        presentation.
        -------------
        modes: 'trial' (default) saves values to tracker
                'practi' does not save values to tracker
        """
        trialClock = core.Clock()
        if practice:
            trial['exp_stage'] = 'practice'
        else:
            trial['exp_stage'] = 'adaptive_procedure'
        stim = trial['stim']
        # update difficulties based on adaptive tracker
        if self.ts == "motion":
            strength = stim["speedStrength"]
            pedestal = stim["motionDirection"]
            difficulties = self.speed_difficulties
        elif self.ts == "orientation":
            strength = stim["oriStrength"]
            pedestal = stim["oriBase"]
            difficulties = self.ori_difficulties
        if intensity is None:
            tracker_key = (pedestal,strength)
            tracker = self.trackers[tracker_key]
            decision_var = next(tracker)
        else:
            decision_var = intensity
        difficulties[(pedestal,strength)] = decision_var
        trial['decision_var'] = decision_var
        # get stim attributes
        trial_attributes = self.getTrialAttributes(stim)
        trial['stim'].update(trial_attributes)
        # print useful information about trial
        """
        print('*'*40)
        print('Trial: %s' % str(trial['trial_count']))
        print('Tracker: %s' % str(tracker_key), 'Best Guess: %s' % tracker.mean()) 
        print('Taskset: %s, choice value: %s\nSpeed: %s, Strength: %s \
              \nOriDirection: %s, OriStrength: %s \
              \nCorrectChoice: %s' % 
              (trial['ts'], decision_var, 
               stim['speedDirection'], stim['speedStrength'], 
               stim['oriDirection'],stim['oriStrength'],
               self.getCorrectChoice(trial_attributes,trial['ts'])))
        """
        trial['response'] = np.nan
        trial['rt'] = np.nan
        trial['FB'] = np.nan
        # present stimulus and get response
        event.clearEvents()
        key_response = self.presentStim(trial_attributes, 
                                        duration=trial['stimulusDuration'], 
                                        response_window=trial['responseWindow'], 
                                        SRI=trial['stimResponseInterval'])
        if key_response:
            # record response
            trial['response'], trial['rt'] = key_response
            # get feedback and update tracker
            correct_choice = self.getCorrectChoice(trial_attributes,trial['ts'])
            #update tracker if in trial mode
            if correct_choice == trial['response']:
                FB = trial['reward_amount']
                if not practice:
                    tracker.addResponse(1, intensity=decision_var)
            else:
                FB = trial['punishment_amount']
                if not practice:
                    tracker.addResponse(0, intensity=decision_var)
            # add current tracker estimate
            if not practice and intensity is None:
                trial['quest_estimate'] = tracker.mean()
            # record points for bonus
            if not practice:
                self.pointtracker += FB
            # Present FB to window
            if trial['displayFB'] == True:
                trial['FB'] = FB
                if trial['FBonset'] > 0: 
                    self.clearWindow(fixation=True)
                    core.wait(trial['FBonset'])  
                if FB == 1:
                    self.clearWindow(fixation=True,
                                     fixation_color='#66ff66')
                else:
                    self.clearWindow(fixation=True,
                                     fixation_color='#ff3300')
                core.wait(trial['FBDuration'])
        # If subject did not respond within the stimulus window clear the stim
        # and admonish the subject
        else:
            if not practice and intensity is None:
                tracker.addResponse(0)
            if trial['displayFB'] == True:
                if trial['FBonset'] > 0: 
                    self.clearWindow(fixation=True)
                    core.wait(trial['FBonset'])  
                self.clearWindow(fixation=True, fixation_color='#ff3300')
                core.wait(trial['FBDuration'])
        self.clearWindow(fixation=True)
        
        # log trial and add to data
        trial['trial_time'] = trialClock.getTime()
        self.writeToLog(json.dumps(trial))
        self.alldata.append(trial)
        return trial
    
    def run_practice(self):
        assert self.num_practice > 0
        self.presentInstruction(
            """
            Welcome to the experiment!
            
            Press 5 to move through instructions                         
            """)
        self.presentInstruction(
            """
            On every trial of this task you will see 
            many small slanted bars either moving 
            towards you or away from you.
            
            The bars will be changing their speed and rotating.
            
            Press 5 to see a demo.             
            """)
        trial = deepcopy(self.stimulusInfo[0])
        trial['displayFB'] = False
        self.presentTrial(trial, practice=True)

        if self.ts == "motion":
            self.presentInstruction(
            """
            Your task is to attend to the SPEED of the oriented bars.
            
            If the bars are speeding up (regardless of direction) 
            press "UP" on the arrow keys.
            
            If they are slowing down press "DOWN" on the arrow keys.
            
            You should respond after the stimulus ends. The central cross
            will change to green to indicate when you should respond.
            
            Wait for the experimenter
            
            """)
        elif self.ts == "orientation":
                        self.presentInstruction("""
            Your task is to attend to the ROTATION of the oriented bars.
            
            If the bars are rotating clockwise press "RIGHT" on the arrow keys.
            
            If they are rotatig counter-clockwise press "LEFT" on the arrow keys.
            
            You should respond after the stimulus ends. The central cross
            will change to green to indicate when you should respond.
            
            Wait for the experimenter
            """)
                        
        trial_timing = self.stimulusInfo[0:self.num_practice]#get timing from the first few trials
        practice = np.random.choice(self.stimulusInfo, self.num_practice, replace=False) #get random trials
        # get ready
        self.presentTextToWindow('Get Ready!', size=.15)
        core.wait(1.5)
        # start practice
        self.clearWindow(fixation=True)
        self.expClock.reset()
        for num, trial in enumerate(practice):            
            # wait for onset time
            while self.expClock.getTime() < trial_timing[num]['onset']:
                    key_response=event.getKeys([self.quit_key])
                    if len(key_response)==1:
                        self.shutDownEarly()
            self.presentTrial(deepcopy(trial), practice=True)
        self.presentInstruction(
            """
            Done with practice. Wait for the experimenter
            """)
    
    def run_super_threshold(self, numTrials=20):
        if self.ts == 'motion':
            decision_var = .1
        elif self.ts == 'orientation':
            decision_var = 30      
        trial_timing = self.stimulusInfo[0:numTrials] #get timing from the first few trials
        practice = np.random.choice(self.stimulusInfo, numTrials, replace=False) #get random trials
        # get ready
        self.presentTextToWindow('Get Ready!', size=.15)
        core.wait(1.5)
        # start practice
        self.clearWindow(fixation=True)
        self.expClock.reset()
        for num, trial in enumerate(practice):            
            # wait for onset time
            while self.expClock.getTime() < trial_timing[num]['onset']:
                    key_response=event.getKeys([self.quit_key])
                    if len(key_response)==1:
                        self.shutDownEarly()
            self.presentTrial(deepcopy(trial), practice=False, static_decision=decision_var)

    def run_estimation(self, intro=True, prop_estimate=.7):
        # set up pause trials
        length_min = self.stimulusInfo[-1]['onset']/60
        # have break every 6 minutes
        num_pauses = np.round(length_min/6)
        pause_trials = np.round(np.linspace(0,self.exp_len,num_pauses+1))[1:-1]
        pause_time = 0
        # get the total number of trials already run on this subject
        starting_trial_num = get_total_trials(self.trackers)
        if intro:
            # get ready
            self.presentTextToWindow('Get Ready!', size=.15)
            core.wait(1.5)
        # randomly set some trials to sample from response function
        N = len(self.stimulusInfo)
        response_samples = [.6, .7, .85, .95]*int(N*(1-prop_estimate)/4)
        trial_type = ['estimate']*(N-len(response_samples)) + response_samples
        np.random.shuffle(trial_type)
        # start the task
        self.expClock.reset()
        self.clearWindow(fixation=True)
        for i, trial in enumerate(self.stimulusInfo):
            if trial['trial_count'] in pause_trials:
                pause_time += self.presentPause()
            # wait for onset time
            while self.expClock.getTime() < trial['onset']+pause_time:
                key_response=event.getKeys([self.quit_key])
                if len(key_response)==1:
                    self.shutDownEarly()
            if trial_type[i] == 'estimate' or (starting_trial_num+i+0) < 50:
                trial['trial_type'] = 'threshold_estimation'
                self.presentTrial(trial)
            else:
                desired_acc = trial_type[i]
                trial['trial_type'] = 'intensity%s' % int(desired_acc)
                intensity = self.get_response_intensity(desired_acc)
                self.presentTrial(trial, intensity=intensity)
                
    def run_task(self, practice=False,  eyetracker=False):
        self.setupWindow()
        self.defineStims()
        # set up eyetracker
        if eyetracker:
            from Dot_Task.pylinkwrapper.connector import Connect
            conn = Connect(self.win, 'eyetest')
            conn.calibrate()
        # run practice
        if practice:
            self.run_practice()
        else:
            self.presentInstruction(self.ts.title(), size=.15)
        # run the estimation procedure
        self.run_estimation(intro=True)
        # clean up and save
        other_data={'taskinfo': self.taskinfo,
                    'configfile': self.config_file,
                    'trackers': self.trackers}
        self.writeData(taskdata=self.alldata,
                       other_data=other_data)
        resp = self.presentInstruction(
                """
                Please wait for the experimenter.
                
                Continue? Y/N
                """,
                keys = ['y', 'n'])
        done = True if resp=='n' else False
        if eyetracker:
            conn.end_experiment(self.save_dir)
            default_eyefile = os.path.join(self.save_dir, 'eyetest.edf')
            os.rename(default_eyefile, os.path.join('..','Data','EyeTrackData',
                                                    self.datafilename.replace('pkl','edf')))
        self.closeWindow()
        return done
        
    










