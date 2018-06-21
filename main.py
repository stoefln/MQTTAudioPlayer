from Tkinter import *
from ttk import Combobox
import os
import appconfig as conf
import os.path
import time
import json
import pkgutil
import sched, time
from enum import Enum
import threading
from dateutil import parser
import datetime
import timer
from pprint import pprint

# ---------------------------------------------------
# 3rd Party Libs (install with pip)
# pip install enum
# pip install numpy
# pip install paho-mqtt
import numpy 
import paho.mqtt.client as mqtt 

class GameModes(Enum):
    SINGLE_HIT = "SINGLE_HIT"
    LOOP = "LOOP"

class Application(Frame):
    TRIGGER_LEVEL = 20
    scheduler = sched.scheduler(time.time, time.sleep)
    playStates = {}
    sensorStates = {}
    buttons = {}
    currentMode = GameModes.SINGLE_HIT
    setIndex = 0
    currentStep = None

    def load(self):
        print("loading sounds into PD..")
        command = ""
        path = conf.SoundSets.keys()[self.setIndex]
        soundSet = conf.SoundSets[path]

        for k in conf.SensorNames:
            channelName = conf.SensorNames[k]
            command += channelName + " load "+path+"/" + channelName.replace(" ", "") + ".wav,"
            self.playStates[channelName] = False
            self.enableButton(channelName, False)

        self.sendToPd(command)
            
    
    def singleHit(self, channelName):
        self.sendToPd(channelName+" play")
        
    def buttonPress(self, channelName):
        if(self.currentMode == GameModes.SINGLE_HIT):
            self.singleHit(channelName)
        else:
            self.playStates[channelName] = not self.playStates.get(channelName)
            if(self.playStates.get(channelName)):
                self.sendToPd(channelName+" volume 1")
            else:
                self.sendToPd(channelName+" volume 0")
        
            self.enableButton(channelName, self.playStates.get(channelName))

    def enableButton(self, channelName, enable):
        color = 'black' if enable else 'white'
        self.buttons[channelName].configure(highlightbackground=color)

    def sendToPd(self, command):
        print("sending command to PD: "+command)
        os.system("echo '" + command + "' | "+conf.SystemSettings["pdSendPath"]+" 3000 localhost udp")

    def switchSetIndex(self, index):
        self.setIndex = (index) % len(conf.SoundSets.keys())
        soundSet = conf.SoundSets.get(conf.SoundSets.keys()[self.setIndex])
        self.currentMode = GameModes.SINGLE_HIT if soundSet['mode'] == 'SINGLE_HIT' else GameModes.LOOP
        print("New setIndex: "+str(self.setIndex))
        if(self.currentMode == GameModes.SINGLE_HIT):
            self.sendToPd("loop stop, all volume 1")
        else:
            duration = soundSet['duration']
            self.sendToPd("loop start "+duration+", all volume 0") 
        print("New mode: "+self.currentMode)
        self.updateModeButton()
        self.updateSetIndexButton()
        self.load()
        
    def updateSetIndexButton(self):
        self.setIndexButton["text"] = "Set: "+conf.SoundSets.keys()[self.setIndex]
    
    def updateModeButton(self):
        self.modeButton["text"] = "Mode: "+self.currentMode


    def enableChannel(self, channelName):
        if(self.playStates[channelName]):
            return
        self.sendToPd(channelName + " volume 1")
        self.playStates[channelName] = True
        self.buttons[channelName].configure(highlightbackground='black')
    
    def disableChannel(self, channelName):
        if(not self.playStates[channelName]):
            return
        self.sendToPd(channelName + " volume 0")
        self.playStates[channelName] = False
        self.buttons[channelName].configure(highlightbackground='white')

    def onMessage(self, client, userdata, message):
        if(message.topic == "control"):
            val = str(message.payload.decode("utf-8"))
            if(val == "nextSet"):
                self.switchSetIndex(self.setIndex + 1)
            elif(val == "prevSet"):
                self.switchSetIndex(self.setIndex - 1)
            elif(val.startswith("pd:")):
                self.sendToPd(val.split(":")[1])

        elif(message.topic == "sensor"):
            '''
            Callback for MQTT messages
            {"k": "XXX", "v": 100}
            '''
            #print(str(message.payload.decode("utf-8")))
            val = json.loads(str(message.payload.decode("utf-8")))   
            v = 0.0
            channelName = ""
            try:
                sensorId = val['k']
                v = int(val['v'])
            except:
                print('Could not digest ' + str(message.payload.decode("utf-8")))
                return
            
            if(v > 50):
                self.activeMacAddrLabel["text"] = sensorId
            
            channelName = conf.SensorNames.get(sensorId)
            if(not channelName):
                print("channel not found")
                return

            prevVal = self.sensorStates.get(sensorId)
            self.sensorStates[sensorId] = v
            #print("sensorId: "+sensorId+", channel: "+channelName +  ", v: "+str(v))
            if(self.currentMode == GameModes.SINGLE_HIT):
                if(v > self.TRIGGER_LEVEL and prevVal < self.TRIGGER_LEVEL):
                    self.singleHit(channelName)
            else:
                if(v > self.TRIGGER_LEVEL):
                    self.enableChannel(channelName)
                else:
                    self.disableChannel(channelName)

    def checkTime(self):
        lastStep = None
        for step in conf.Controller['steps']:
            startHour = int(step.get('startTime').split(":")[0])
            startMinute = int(step.get('startTime').split(":")[1])
            startSecond = int(step.get('startTime').split(":")[2])
            startDate = datetime.datetime.now().replace(hour=startHour, minute=startMinute, second=startSecond, microsecond=0)
            #print("now", datetime.datetime.now())
            if(startDate < datetime.datetime.now()):
                lastStep = step

        if(lastStep is not None and lastStep != self.currentStep):
            print("automatic step switch: ", lastStep)
            self.loadStep(lastStep)

        info = "currentStep: "+str(self.currentStep)+"\n"
        info += "currentMode: "+self.currentMode+"\n"
        self.client.publish("info", "info: "+info, 0)


    def loadStep(self, step):
        if(step == self.currentStep):
            return
        self.currentStep = step
        soundSetPath = step.get('set')
        self.switchSetIndex(conf.SoundSets.keys().index(soundSetPath))
        if(step.get('pdCommand')):
            self.sendToPd(step.get('pdCommand'))
    
    def patchFirmware(self):
        self.client.publish("sensorControl", "{\"command\": \"patch\"}", 0)

    def copyMacToClipBoard(self):
        root.clipboard_clear()
        root.clipboard_append(self.activeMacAddrLabel['text'])
        root.update()

    def createWidgets(self):
        topFrame = Frame(self)
        topFrame.pack( side = TOP)


        self.modeButton = Button(topFrame)
        self.modeButton.pack( side = LEFT)

        self.setIndexButton = Button(topFrame, command=lambda :self.switchSetIndex(self.setIndex+1))
        self.setIndexButton.pack( side = LEFT)

        self.stepButton = Button(topFrame)
        self.stepButton.pack( side = LEFT)

        footerFrame = Frame(self)
        footerFrame.pack( side = BOTTOM )

        bottomFrame = Frame(self)
        bottomFrame.pack( side = BOTTOM )

        #self.stepCombo = Combobox(footerFrame)
        #self.stepCombo.pack(side = LEFT)
        self.activeMacAddrLabel = Button(footerFrame, text='Last active mac',command=self.copyMacToClipBoard)
        self.activeMacAddrLabel.pack(side = LEFT)

        self.patchFirmwareButton = Button(footerFrame, text='Patch Firmware',command=self.patchFirmware)
        self.patchFirmwareButton.pack( side = LEFT)

        #self.activeMacAddressLabel = Label(bottomFrame)
        #self.activeMacAddressLabel.pack( side = LEFT)

        cols = [1, 2, 3, 4, 5]
        rows = ["A", "B", "C", "D", "E"]
        
        for c in range(len(cols)):
            for r in range(len(rows)):
                channelName = str(rows[r])+" "+str(cols[c])
                button = Button(bottomFrame, text=channelName, command=lambda sn=channelName:self.buttonPress(sn))
                button.grid(row=r, column=c)
                self.buttons[channelName] = button
                
        #self.loadButton = Button(topFrame, text="Load", command=self.load)
        #self.loadButton.pack( side = LEFT)

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()
        print("Connecting to broker...")
        self.client = mqtt.Client(conf.brokerSettings['client'])
        self.client.connect(conf.brokerSettings['address'], conf.brokerSettings['port'])
        print("connected!")
        # wait for MQTT connection
        # TODO: implement proper callback https://www.eclipse.org/paho/clients/python/docs/
        #       with error handling on failed connection
        time.sleep(0.5)

        self.client.subscribe([(conf.brokerSettings['topic'], 0), ("control", 0)])

        # setup callback
        self.client.on_message=self.onMessage
        self.client.loop_start()
        self.switchSetIndex(0)
        # self.checkTime()
        #self.checkTime()
        self.scheduler = timer.Scheduler(5, self.checkTime)
        self.scheduler.start()

    def quit(self):
        print("Terminating...")
        self.scheduler.stop()
        root.destroy()

root = Tk()
app = Application(master=root)
root.protocol("WM_DELETE_WINDOW", app.quit)

app.mainloop()
