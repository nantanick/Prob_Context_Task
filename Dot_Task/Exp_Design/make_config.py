# -*- coding: utf-8 -*-
"""
Created on Thu Nov 20 16:13:45 2014

@author: admin
"""

import datetime
import numpy as np
from os import path
import random as r
from scipy.stats import norm
import yaml
    
class ProbContextConfig(object): 
    def __init__(self, color_difficulties, motion_difficulties,
                 taskname='taskname', subjid='000', rp=.9,
                 action_keys=None, distribution=norm, args=None, 
                 stim_repetitions=5, ts_order=None, 
                 seed=None):
        self.seed = seed
        if self.seed is not None:
            np.random.seed(self.seed)
        self.distribution = norm
        self.stim_repetitions = stim_repetitions
        self.rp = rp # recursive probability
        self.subjid = subjid
        self.taskname = taskname
        try:
            self.distribution_name = distribution.name
        except AttributeError:
            self.distribution_name = 'unknown'
        self.action_keys = action_keys
        if action_keys == None:
            self.action_keys = ['down','up','z', 'x']
        self.args = args
        if args == None:
            self.args = [{'loc': -.3, 'scale': .37}, {'loc': .3, 'scale': .37}]
        self.ts_order = ts_order
        if ts_order == None:
            self.ts_order = ['motion','color']
            r.shuffle(self.ts_order)
        else:
            assert (set(['motion','color']) == set(self.ts_order)), \
                'Tasksets not recognized. Must be "motion" and "color"'
        self.timestamp=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.loc = '../Config_Files/'
        self.states = None
        self.trial_states = None
        self.trial_list = None
        # stim attributes. Difficulties are a dictionary passed to the constructor
        # colors in LAB space
        self.stim_colors = np.array([[75,128,75],[75,-128,75]])
        self.stim_motions = ['in','out']
        self.color_starts = [.15,.85]
        self.color_difficulties = color_difficulties
        # motion speeds
        self.base_speed = .1
        self.motion_difficulties = motion_difficulties
        # calculate exp len
        num_stims = len(self.color_difficulties)*len(self.motion_difficulties)\
                    *len(self.stim_colors)*len(self.stim_motions)*4
        self.exp_len = int(stim_repetitions*num_stims)
        # setup
        self.setup_stims()
    
    def get_config(self, save=True, filey=None):
        if self.trial_list==None:
            self.setup_trial_list()
        
        initial_params = {
          'clearAfterResponse': 1,
          'quit_key': 'q',
          'responseWindow': 1.0,
          'taskname': self.taskname,
          'id': self.subjid,
          'trigger_key': '5',
          'action_keys': self.action_keys,
          'states': self.states,
          'rp': self.rp,
          'exp_len': self.exp_len,
          'stim_ids': self.stim_ids,
          'ts_order': self.ts_order,
          'stim_colors': self.stim_colors.tolist(),
          'stim_motions': self.stim_motions,
          'color_difficulties': self.color_difficulties,
          'motion_difficulties': self.motion_difficulties,
          'base_speed': self.base_speed
        }
        to_save = self.trial_list
        to_save.insert(0,initial_params)
        if save==True:
            filename = self.taskname + '_' + self.subjid + '_config_' + self.timestamp + '.yaml'
            if filey == None:
                filey = path.join(self.loc,filename)
            yaml.dump(to_save, open(filey,'w'))
            return filey
        else:
            return to_save
      
    def load_config_settings(self, filename, **kwargs):
        if not path.exists(filename):
            raise BaseException('Config file not found')
        config_file = yaml.load(open(filename,'r'))
        configuration = config_file[0]
        for k,v in configuration.items():
            self.__dict__[k] = v
        for k,v in kwargs.items():
            self.__dict__[k] = v  
        self.stim_colors = np.array([np.array(x) for x in self.stim_colors])
        # setup
        self.setup_stims()
        self.setup_trial_states()
        
    def setup_stims(self):
        stim_ids = []
        for motion_difficulty in self.motion_difficulties.keys():
            for direction in self.stim_motions:
                for color_difficulty in self.color_difficulties.keys():
                    for color_space in self.color_starts:
                        for color_direction in [-1,1]:
                            for speed_direction in [-1,1]:
                                stim_ids.append({'motionDirection': direction,
                                                 'colorSpace': color_space,
                                                 'speedStrength': motion_difficulty,
                                                 'speedDirection': speed_direction,
                                                 'colorStrength': color_difficulty,
                                                 'colorDirection': color_direction})

        self.stim_ids = stim_ids
        self.states = {i: {'ts': self.ts_order[i], 'dist_args': self.args[i]} for i in range(len(self.ts_order))}
        self.setup_trial_states()
  
    def setup_trial_states(self):
        """
        Create a list of trials with the correct block length. Define tasksets with
        "probs" = P(reward | correct) and P(reward | incorrect), and "actions" =
        correct action for stim 1 and stim 2.
        """
        if self.seed is not None:
            np.random.seed(self.seed)
        trans_probs = np.matrix([[self.rp, 1-self.rp], [1-self.rp, self.rp]])
        trial_states = [1] #start off the function
        #creates the task-set trial list. Task-sets alternate based on recusive_p
        #with a maximum repetition of 25 trials. This function also makes sure
        #that each task-set composes at least 40% of trials
        while abs(np.mean(trial_states)-.5) > .1:
            curr_state = r.choice(list(self.states.keys()))
            trial_states = []
            state_reps = 0
            for trial in range(self.exp_len):
                trial_states.append(curr_state)
                if r.random() > trans_probs[curr_state,curr_state] or state_reps > 25:
                    curr_state = 1-curr_state
                    state_reps = 0
                else:
                    state_reps += 1
        self.trial_states = trial_states
            
    def setup_trial_list(self, cueDuration=1.5, CSI=.5, stimulusDuration=2, 
                         responseWindow=1, FBDuration=.5, FBonset=.5, 
                         base_ITI=1, displayFB = True):
        if self.seed is not None:
            np.random.seed(self.seed)
        trial_list = []    
        trial_count = 1
        curr_onset = 2 #initial onset time
        stims = r.sample(self.stim_ids*self.stim_repetitions,self.exp_len)   
            
        #define bins. Will set context to center point of each bin
        bin_boundaries = np.linspace(-1,1,11)
        
        for trial in range(self.exp_len):
            # define ITI
            ITI = base_ITI + r.random()*.5
            state = self.states[self.trial_states[trial]]
            dist = self.distribution(**state['dist_args'])
            binned = -1.1 + np.digitize([dist.rvs()],bin_boundaries)*.2
            context_sample = round(max(-1, min(1, binned[0])),2)
            trial_dict = {
                'trial_count': trial_count,
                'state': self.trial_states[trial],
                'ts': state['ts'],
                'task_distributions': self.distribution_name,
                'distribution_args': state['dist_args'],
                'context': context_sample,
                'stim': stims[trial],
                'onset': curr_onset,
                'cueDuration': cueDuration,
                'stimulusDuration': stimulusDuration,
                'FBDuration': FBDuration,
                'FBonset': FBonset,
                'displayFB': displayFB,
                'CSI': CSI,
                'ITI': ITI,
                #option to change based on state and stim
                'reward_amount': 1,
                'punishment_amount': 0
            }

            trial_list += [trial_dict]

            trial_count += 1
            curr_onset += cueDuration+CSI+stimulusDuration+responseWindow\
                            +FBDuration+FBonset+ITI
        self.trial_list = trial_list
       

class ThresholdConfig(object): 
    def __init__(self, taskname='taskname', subjid='000', action_keys=None,  
                 stim_repetitions=5, ts='motion', seed=None, exp_len=None):
        self.seed = seed
        if self.seed is not None:
            np.random.seed(self.seed)
        self.distribution = norm
        self.stim_repetitions = stim_repetitions
        self.subjid = subjid
        # set task set
        assert ts in ['color','motion']
        self.ts = ts
        self.taskname = taskname
        self.action_keys = action_keys
        if action_keys == None:
            self.action_keys = ['down','up','z','x']
        self.timestamp=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.loc = '../Config_Files/'
        self.states = None
        self.trial_states = None
        self.trial_list = None
        # stim attributes
        # colors in LAB space
        self.stim_colors = np.array([[75,128,75],[75,-128,75]])
        self.stim_motions = ['in','out']
        self.color_starts = [.15,.85]
        # from easy to hard
        # each tuple defines a starting color proportion, and the change in color proportion
        # each difficulty level has two tuples, for different sides of the
        # color space.
        self.color_difficulties = {'easy':.15,'hard':.05}
        # motion speeds
        self.base_speed = .1
        self.motion_difficulties = {'easy':.05, 'hard':.02}
        # calculate exp len
        num_stims = len(self.color_difficulties)*len(self.motion_difficulties)\
                    *len(self.stim_colors)*len(self.stim_motions)*4
        if exp_len is None:
            self.exp_len = int(stim_repetitions*num_stims)
        else:
            assert exp_len < int(stim_repetitions*num_stims)
            self.exp_len=exp_len
        # setup
        self.setup_stims()
    
    def get_config(self, save=True, filey=None):
        if self.trial_list==None:
            self.setup_trial_list()
        
        initial_params = {
          'clearAfterResponse': 1,
          'quit_key': 'q',
          'responseWindow': 1.0,
          'taskname': self.taskname,
          'id': self.subjid,
          'trigger_key': '5',
          'action_keys': self.action_keys,
          'exp_len': self.exp_len,
          'stim_ids': self.stim_ids,
          'ts': self.ts,
          'stim_colors': self.stim_colors.tolist(),
          'stim_motions': self.stim_motions,
          'color_difficulties': self.color_difficulties,
          'motion_difficulties': self.motion_difficulties,
          'color_starts': self.color_starts,
          'base_speed': self.base_speed
        }
        to_save = self.trial_list
        to_save.insert(0,initial_params)
        if save==True:
            filename = self.taskname + '_' + self.subjid + '_config_' + self.timestamp + '.yaml'
            if filey == None:
                filey = path.join(self.loc,filename)
            yaml.dump(to_save, open(filey,'w'))
            return filey
        else:
            return to_save
      
    def load_config_settings(self, filename, **kwargs):
        if not path.exists(filename):
            raise BaseException('Config file not found')
        config_file = yaml.load(open(filename,'r'))
        configuration = config_file[0]
        for k,v in configuration.items():
            self.__dict__[k] = v
        for k,v in kwargs.items():
            self.__dict__[k] = v  
        self.stim_colors = np.array([np.array(x) for x in self.stim_colors])
        # setup
        self.setup_stims()
        
    def setup_stims(self):
        stim_ids = []
        for motion_difficulty in self.motion_difficulties.keys():
            for direction in self.stim_motions:
                for color_difficulty in self.color_difficulties.keys():
                    for color_space in self.color_starts:
                        for color_direction in [-1,1]:
                            for speed_direction in [-1,1]:
                                stim_ids.append({'motionDirection': direction,
                                                 'colorSpace': color_space,
                                                 'speedStrength': motion_difficulty,
                                                 'speedDirection': speed_direction,
                                                 'colorStrength': color_difficulty,
                                                 'colorDirection': color_direction})

        self.stim_ids = stim_ids
  
                    
    def setup_trial_list(self, stimulusDuration=2, responseWindow=1,
                         FBDuration=.5, FBonset=.5, base_ITI=1, 
                         displayFB = True):
        if self.seed is not None:
            np.random.seed(self.seed)
        trial_list = []    
        trial_count = 1
        curr_onset = 2 #initial onset time
        stims = r.sample(self.stim_ids*self.stim_repetitions,self.exp_len)   
        for trial in range(self.exp_len):
            # set ITI
            ITI = base_ITI + r.random()*.5
            trial_dict = {
                'trial_count': trial_count,
                'ts': self.ts,
                'stim': stims[trial],
                'onset': curr_onset,
                'stimulusDuration': stimulusDuration,
                'responseWindow': responseWindow,
                'FBDuration': FBDuration,
                'FBonset': FBonset,
                'displayFB': displayFB,
                'ITI': ITI,
                #option to change based on state and stim
                'reward_amount': 1,
                'punishment_amount': 0
            }

            trial_list += [trial_dict]

            trial_count += 1
            curr_onset += stimulusDuration+responseWindow\
                          +FBDuration+FBonset+ITI
        self.trial_list = trial_list
       