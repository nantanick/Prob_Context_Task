"""
runprobContextTask
"""

from psychopy import core, event
import smtplib
import json
import webbrowser
from prob_context_task import probContextTask
from make_config import makeConfigList, makePracticeConfigList
from test_bot import test_bot
import glob
from Load_Data import load_data
import os
#set-up some variables

verbose=True
fullscr= True
subdata=[]
practice_on = True
train_on = True
test_on = True
bot_on = False
bot_mode = "ignore_base" #other for optimal
home = os.getenv('HOME') 
save_dir = home + '/Mega/IanE_RawData/Prob_Context_Task/' #cloud storage
trainname = 'Prob_Context'

# set things up for practice, training and tests
try:
    f = open('IDs.txt','r')
    lines = f.readlines()
    f.close()
    last_id = lines[-1][:-1]
    subject_code = raw_input('Last subject: "%s". Input new subject code: ' % last_id);
except IOError:
    subject_code = raw_input('Input first subject code: ');
f = open('IDs.txt', 'a')
f.write(subject_code + '\n')
f.close()

#set up some task variables
train_mins = 45 #train_length in minutes
test_mins = 30 #test_length in minutes
avg_test_trial_len = 2.25 #in seconds
avg_train_trial_len = avg_test_trial_len + 1 #factor in FB
#Find the minimum even number of blocks to last at least train_length minutes
train_len = int(round(train_mins*60/avg_train_trial_len/4)*4)
test_len = int(round(test_mins*60/avg_test_trial_len/4)*4)
recursive_p = .9

#counterbalance ts_order (which ts is associated with top of screen)
if int(subject_code)%2 == 0:
    ts_order = [0,1]
else:
    ts_order = [1,0]
    
#set up config files
practice_config_file = '../Config_Files/Prob_Context_Practice_config.npy'
try:
    practice=probContextTask(practice_config_file,subject_code, fullscreen = fullscr, mode = 'practice')
except:
    practice_config_file = makePracticeConfigList(taskname = trainname + '_Practice')
    practice=probContextTask(practice_config_file,subject_code, fullscreen = fullscr, mode = 'practice')
    
train_config_file = makeConfigList(taskname = trainname, iden = subject_code, exp_len = train_len, 
                                   recursive_p = recursive_p, ts_order = ts_order)
    
train=probContextTask(train_config_file,subject_code, fullscreen = fullscr)
if bot_on == True:
    train.setBot(bot = test_bot(train_config_file, mode = bot_mode), mode = "full")
train.writeToLog(train.toJSON(),loc = save_dir + 'Log/')



#************************************
# Start Practice
#************************************

if practice_on:
    # prepare to start
    practice.setupWindow()
    practice.defineStims()
    task_intro_text = [
        'Welcome\n\nPress 5 to move through instructions',
        """
        This experiment starts with a training phase followed by a testing phase.
        Training will last 45 minutes and testing will last 30 minutes.
        
        Your performance on the training AND test phase determines your bonus payment. 
        To perform well on the test phase you'll need to stay
        motivated and learn as much as possible in the training phase.
        """,
        """
        In the training phase, shapes will appear on the screen
        one at a time, and you will need to learn how to respond to them.
        
        Your responses will consist of one of four buttons: 'd', 'f', 'j' and 'k'.
        Use your index and middle fingers on both hands to respond.
        
        The goal is to learn the best key(s) to press for each shape.
        After you press a key, the shape will disappear and 
        you will get a point if you responded correctly.
        
        Press '5' to see the four shapes that will be used in practice.
        """,
        """
        As you could see, these shapes differ in their identity (which
        shape they are) and their color.
        
        Your responses should depend on these features. At certain points
        in the experiment you should respond based on color, and at other times
        you should respond based on identity, but not both at the same time.
        
        We will now practice responding to the shapes. For these trials,
        just pay attention to the identity of the shape when making your response.
        
        Please wait for the experimenter.
        """,
        """
        In those trials, one key worked for the pentagon, and one worked for the triangle.
        
        We'll now practice responding to the color of the shape.
        
        Please wait for the experimenter.
        """,
        """
        In those trials, one key worked for yellow shapes and one for green shapes.
        
        For the rest of the experiment, the shape's vertical position will also 
        change from trial to trial.
        
        Press "5" to see this in a few trials.
        """,
        """
        Your job in this experiment is to figure out on which trials you
        should respond based on identity and on which trials you should
        respond based on color.
        
        Use the points during the training phase to learn how to respond.
        """,
        """
        After the training phase, there will be a test phase 
        with no feedback. You will still be earning points, and these
        test phase points will also be used to determine your bonus pay.
        
        Because there is no feedback, it will be impossible to learn anything
        new during the test phase. Therefore it is important that you learn all
        you can during the training phase.
        """,
        """
        You must respond while the shape is on the screen.
        Please respond as quickly and accurately as possible.
        
        The task is hard! Stay motivated and try to learn
        all you can.
        
        We will start with a brief practice session. 
        Please wait for the experimenter.
        """
    ]
    
    for line in task_intro_text:
        practice.presentTextToWindow(line)
        resp,practice.startTime=practice.waitForKeypress(practice.trigger_key)
        practice.checkRespForQuitKey(resp)
        event.clearEvents()
        if 'used in practice' in line:
            practice.presentStims(mode = 'practice')
            resp,practice.startTime=practice.waitForKeypress(practice.trigger_key)
            practice.checkRespForQuitKey(resp)
        if "pay attention to the identity of the shape" in line:
            pos_count = 0
            startTime = core.getTime()
            for trial in practice.stimulusInfo[0:40]:
                # wait for onset time
                while core.getTime() < trial['onset'] + startTime:
                        key_response=event.getKeys(None,True)
                        if len(key_response)==0:
                            continue
                        for key,response_time in key_response:
                            if practice.quit_key==key:
                                practice.shutDownEarly()
                trial=practice.presentTrial(trial)
                if trial['FB'] == 1:
                    pos_count += 1
                else:
                    pos_count = 0
                if pos_count ==6:
                    break
            core.wait(1)
        if "responding to the color of the shape" in line:
            pos_count = 0
            startTime = core.getTime()
            elapsed_time = practice.stimulusInfo[39]['onset']+1
            for trial in practice.stimulusInfo[40:80]: 
                # wait for onset time
                while core.getTime() < trial['onset'] + startTime - elapsed_time:
                        key_response=event.getKeys(None,True)
                        if len(key_response)==0:
                            continue
                        for key,response_time in key_response:
                            if practice.quit_key==key:
                                practice.shutDownEarly()
                trial=practice.presentTrial(trial)
                if trial['FB'] == 1:
                    pos_count += 1
                else:
                    pos_count = 0
                if pos_count ==6:
                    break
            core.wait(1)
        if "see this in a few trials" in line:
            pos_count = 0
            startTime = core.getTime()
            elapsed_time = practice.stimulusInfo[79]['onset']+1
            for trial in practice.stimulusInfo[80:84]: 
                # wait for onset time
                while core.getTime() < trial['onset'] + startTime - elapsed_time:
                        key_response=event.getKeys(None,True)
                        if len(key_response)==0:
                            continue
                        for key,response_time in key_response:
                            if practice.quit_key==key:
                                practice.shutDownEarly()
                trial=practice.presentTrial(trial)
            core.wait(1)
    
    for trial in practice.stimulusInfo[84:]:
        # wait for onset time
        startTime = core.getTime()
        elapsed_time = practice.stimulusInfo[83]['onset'] + 1
        while core.getTime() < trial['onset'] + practice.startTime - elapsed_time:
                key_response=event.getKeys(None,True)
                if len(key_response)==0:
                    continue
                for key,response_time in key_response:
                    if practice.quit_key==key:
                        practice.shutDownEarly()
        trial=practice.presentTrial(trial)
    
    practice.presentTextToWindow(
    """
    That's enough practice. In the actual experiment, there will
    be new shapes that you have to learn about. You still have to
    learn when to respond based on the identity or color of the shape,
    but the correct responses may be different from what you learned
    during practice. 
    
    Before we start the experiment
    press 5 to see the shapes you will have to respond to
    during the training and test phases.
    """)
    resp,practice.startTime=practice.waitForKeypress(practice.trigger_key)
    practice.checkRespForQuitKey(resp)
    practice.presentStims(mode = 'task')
    resp,practice.startTime=practice.waitForKeypress(practice.trigger_key)
    practice.checkRespForQuitKey(resp)
    
    # clean up
    practice.closeWindow()

#************************************
# Start training
#************************************

if train_on:
    # prepare to start
    train.setupWindow()
    train.defineStims()
    if bot_on == False:
        train.presentTextToWindow(
            """
            We will now start the training phase of the experiment.
            
            Remember, following this training phase will be a test phase with no
            feedback (you won't see points). Use this training to learn when
            you have to respond to the identity or color of the shape without
            needing to use the points.
            
            There will be one break half way through. As soon
            as you press '5' the experiment will start so get ready!
            
            Please wait for the experimenter.
            """)
        resp,train.startTime=train.waitForKeypress(train.trigger_key)
        train.checkRespForQuitKey(resp)
        event.clearEvents()
    else:
        train.startTime = core.getTime()
        
    
    pause_trial = train.stimulusInfo[len(train.stimulusInfo)/2]
    pause_time = 0
    
    for trial in train.stimulusInfo:
        if not train.bot:
            if trial == pause_trial:
                time1 = core.getTime()
                train.presentTextToWindow("Take a break! Press '5' when you're ready to continue.")
                train.waitForKeypress(train.trigger_key)
                train.clearWindow()
                pause_time = core.getTime() - time1
        
        #if botMode = short, don't wait for onset times
        if train.botMode != 'short':
            # wait for onset time
            while core.getTime() < trial['onset'] + train.startTime + pause_time:
                    key_response=event.getKeys(None,True)
                    if len(key_response)==0:
                        continue
                    for key,response_time in key_response:
                        if train.quit_key==key:
                            train.shutDownEarly()
                        elif train.trigger_key==key:
                            train.trigger_times.append(response_time-train.startTime)
                            train.waitForKeypress()
                            continue
    
        trial=train.presentTrial(trial)
        train.writeToLog(json.dumps(trial), loc = save_dir + 'Log/')
        train.alldata.append(trial)

    #************************************
    # Send text about train performance
    #************************************

    if bot_on == False:   
        username = "thedummyspeaks@gmail.com"
        password = "r*kO84gSzzD4"
        atttext = "9148155478@txt.att.net"
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.starttls()
        server.login(username,password)
        message = "Training done."
        
        msg = """From: %s
        To: %s
        Subject: "Training done"
        
        %s""" % (username, atttext, message)
        server.sendmail(username, atttext, msg)
        server.quit()
        
    # clean up and save
    train.writeToLog(json.dumps({'trigger_times':train.trigger_times}), loc = save_dir + 'Log/')
    train.writeData(loc = save_dir + 'RawData/')
    if bot_on == False:
        train.presentTextToWindow('Thank you. Please wait for the experimenter.')
        train.waitForKeypress(train.quit_key)

    train.closeWindow()



#************************************
# Start test
#************************************

if test_on:
    #if experiment crashed for some reason between train and test set task_on
    #to false and the experiment will load up the parameters from the training
    if train_on == False:
        train_file = glob.glob('../RawData/' + subject_code + '*Context_20*yaml')[0]
        train_name = train_file[11:-5]
        taskinfo, df, dfa = load_data(train_file, train_name, mode = 'train')
        action_keys = taskinfo['action_keys']
        states = taskinfo['states']
        ts_order = [states[0]['ts'],states[1]['ts']] 
    else:
        action_keys = train.getActions()
    test_config_file = makeConfigList(taskname = trainname + '_test', iden = subject_code, exp_len = test_len, 
                                      recursive_p = recursive_p, FBDuration = 0, FBonset = 0, action_keys = action_keys,
                                      ts_order = ts_order)
                                      
    test=probContextTask(test_config_file,subject_code, fullscreen = fullscr)
    if bot_on == True:
        test.setBot(bot = test_bot(test_config_file, mode = bot_mode), mode = "full")

    test.writeToLog(test.toJSON(), loc = save_dir + 'Log/')
    
    # prepare to start
    test.setupWindow()
    test.defineStims()
    if bot_on == False:
        test.presentTextToWindow(
            """
            In this next part the feedback will be invisible. You
            are still earning points, though, and these points are
            used to determine your bonus.
            
            Do your best to respond to the shapes as you learned to
            in the last section.
            
            Please wait for the experimenter.
            """)
                            
        resp,test.startTime=test.waitForKeypress(test.trigger_key)
        test.checkRespForQuitKey(resp)
        event.clearEvents()
    else:
        test.startTime = core.getTime()
        
    pause_trial = test.stimulusInfo[len(test.stimulusInfo)/2]
    pause_time = 0
    prompt_time = 0 #change if "please respond faster" comes on the screen
    for trial in test.stimulusInfo:
        if not test.bot:
            if trial == pause_trial:
                time1 = core.getTime()
                test.presentTextToWindow("Take a break! Press '5' when you're ready to continue.")
                test.waitForKeypress(test.trigger_key)
                test.clearWindow()
                pause_time = core.getTime() - time1
            
        #if botMode = short, don't wait for onset times
        if test.botMode != 'short':
            # wait for onset time
            while core.getTime() < trial['onset'] + test.startTime + pause_time + prompt_time:
                    key_response=event.getKeys(None,True)
                    if len(key_response)==0:
                        continue
                    for key,response_time in key_response:
                        if test.quit_key==key:
                            test.shutDownEarly()
                        elif test.trigger_key==key:
                            test.trigger_times.append(response_time-test.startTime)
                            continue
    
        trial=test.presentTrial(trial)
        test.writeToLog(json.dumps(trial), loc = save_dir + 'Log/')
        test.alldata.append(trial)
        if test.alldata[-1]['response'][0] == 999:
            prompt_time += 1
        
    #************************************
    # Send text about test performance
    #************************************

    if bot_on == False:   
        username = "thedummyspeaks@gmail.com"
        password = "r*kO84gSzzD4"
        atttext = "9148155478@txt.att.net"
        server = smtplib.SMTP('smtp.gmail.com',587)
        server.starttls()
        server.login(username,password)
        message = "Testing done."
        
        msg = """From: %s
        To: %s
        Subject: text-message
        
        %s""" % (username, atttext, message)
        server.sendmail(username, atttext, msg)
        server.quit()
       
    # clean up and save
    test.writeToLog(json.dumps({'trigger_times':test.trigger_times}), loc = save_dir + 'Log/')
    test.writeData(loc = save_dir + 'RawData/')
    if bot_on == False:
        test.presentTextToWindow('Thank you. Please wait for the experimenter.')
        test.waitForKeypress(test.quit_key)
    
    
    test.closeWindow()
    


    
#************************************
# Determine payment
#************************************
points,trials = test.getPoints()
performance = (float(points)/trials-.25)/.75
pay_bonus = round(performance*5)
print('Participant ' + subject_code + ' won ' + str(points) + ' points out of ' + str(trials) + ' trials. Bonus: $' + str(pay_bonus))

#open post-task questionnaire
if bot_on == False:
    webbrowser.open_new('https://stanforduniversity.qualtrics.com/SE/?SID=SV_9KzEWE7l4xuORIF')






