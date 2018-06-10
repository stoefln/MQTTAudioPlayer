from Tkinter import *
import os
import appconfig as conf
import os.path
import time
import json
import pkgutil
import sched, time
from enum import Enum
from threading import Thread

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
    TRIGGER_LEVEL = 70
    scheduler = sched.scheduler(time.time, time.sleep)
    playStates = {}
    sensorStates = {}
    buttons = {}
    currentMode = GameModes.SINGLE_HIT
    setIndex = 0

    def load(self):
        print "loading sounds into PD.."
        command = ""
        currentSet = conf.SoundSets[self.currentMode][self.setIndex]
        for k in conf.SensorNames:
            v = conf.SensorNames[k]
            command += v + " load "+currentSet["path"]+"/" + v.replace(" ", "") + ".wav,"
        print "command: "+command
        self.sendToPd(command)
    
    def singleHit(self, channelName):
        self.sendToPd(channelName+" play")
        self.enableButton(channelName, True)
        self.scheduler.enter(2, 1, self.enableButton, (channelName, False))
        self.scheduler.run()
        
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
        print("enablebutton", channelName, enable)
        color = 'black' if enable else 'white'
        self.buttons[channelName].configure(highlightbackground=color)

    def sendToPd(self, command):
        print("sending command to PD: "+command)
        os.system("echo '" + command + "' | "+conf.SystemSettings["pdSendPath"]+" 3000 localhost udp")

    def switchMode(self):
        setIndex = 0
        if(self.currentMode == GameModes.SINGLE_HIT):
            self.currentMode = GameModes.LOOP
            self.sendToPd("loop start 60, all volume 0") 

        else:
            self.currentMode = GameModes.SINGLE_HIT
            self.sendToPd("loop stop, all volume 1")
  
        print("New mode: "+self.currentMode)
        self.updateModeButton()
        self.switchSetIndex()

    def updateModeButton(self):
        self.modeButton["text"] = "Mode: "+self.currentMode

    def switchSetIndex(self):
        self.setIndex = (self.setIndex + 1) % len(conf.SoundSets[self.currentMode])
        print("New setIndex: "+str(self.setIndex))
        self.updateSetIndexButton()
        self.load()

    def updateSetIndexButton(self):
        self.setIndexButton["text"] = "Set: "+conf.SoundSets[self.currentMode][self.setIndex]['path']

    def createWidgets(self):
        topFrame = Frame(self)
        topFrame.pack( side = TOP)

        bottomFrame = Frame(self)
        bottomFrame.pack( side = BOTTOM )

        self.modeButton = Button(topFrame, command=self.switchMode)
        self.modeButton.pack( side = LEFT)
        self.updateModeButton()

        self.setIndexButton = Button(topFrame, command=self.switchSetIndex)
        self.setIndexButton.pack( side = LEFT)
        self.updateSetIndexButton()

        cols = [1, 2, 3, 4, 5]
        rows = ["A", "B", "C", "D", "E"]
        
        for c in range(len(cols)):
            for r in range(len(rows)):
                channelName = str(rows[r])+" "+str(cols[c])
                button = Button(bottomFrame, text=channelName, command=lambda sn=channelName:self.buttonPress(sn))
                button.grid(row=r, column=c)
                self.buttons[channelName] = button
                
        self.loadButton = Button(topFrame, text="Load", command=self.load)
        self.loadButton.pack( side = LEFT)
        #self.loadButton.grid(row=5, column=0, columnspan=2)

        #self.playAllButton = Button(topFrame, text="PlayAll", command=self.playAll)
        #self.playAllButton.pack( side = LEFT)
        #self.playAllButton.grid(row=5, column=2, columnspan=2)

    def enableChannel(self, channelName):
        self.sendToPd(channelName + " volume 1")
        self.playStates[channelName] = True
        self.buttons[channelName].configure(highlightbackground='black')
    
    def disableChannel(self, channelName):
        self.sendToPd(channelName + " volume 0")
        self.playStates[channelName] = True
        self.buttons[channelName].configure(highlightbackground='white')

    def onMessage(self, client, userdata, message):
        '''
        Callback for MQTT messages
        {"k": "XXX", "v": 100}
        '''
        val = json.loads(str(message.payload.decode("utf-8")))   
        v = 0.0
        channelName = ""
        try:
            sensorId = val['k']
            v = int(val['v'])
        except:
            print('Could not digest ' + str(message.payload.decode("utf-8")))

        channelName = conf.SensorNames[sensorId]
        prevVal = self.sensorStates.get(sensorId)
        self.sensorStates[sensorId] = v
        print("sensorId: "+sensorId+", channel: "+channelName +  ", v: "+str(v))
        if(self.currentMode == GameModes.SINGLE_HIT):
            if(v > self.TRIGGER_LEVEL and prevVal < self.TRIGGER_LEVEL):
                self.singleHit(channelName)
        else:
            if(v > self.TRIGGER_LEVEL):
                self.enableChannel(channelName)
            else:
                self.disableChannel(channelName)


    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()
        print("Initialising...")
        self.client = mqtt.Client(conf.brokerSettings['client'])
        self.client.connect(conf.brokerSettings['address'], conf.brokerSettings['port'])

        # wait for MQTT connection
        # TODO: implement proper callback https://www.eclipse.org/paho/clients/python/docs/
        #       with error handling on failed connection
        time.sleep(0.5)

        self.client.subscribe(conf.brokerSettings['topic'])

        # setup callback
        self.client.on_message=self.onMessage
        self.client.loop_start()
        self.switchMode()

root = Tk()
app = Application(master=root)
app.mainloop()
root.destroy()
