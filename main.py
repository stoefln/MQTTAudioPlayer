from Tkinter import *
from ttk import Combobox
import os
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
from thread import start_new_thread

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
    cols = [1, 2, 3, 4, 5]
    rows = ["A", "B", "C", "D", "E"]
    
    scheduler = sched.scheduler(time.time, time.sleep)
    playStates = {}
    sensorStates = {}
    buttons = {}
    currentMode = GameModes.SINGLE_HIT
    currentStep = None
    
    

    def load(self):
        print("loading sounds into PD..")
        command = ""
        path = self.setCombo.get()
        soundSet = self.conf["SoundSets"][path]

        sensorsPerRow = 5.0
        gapsPerRow = sensorsPerRow - 1
        balanceSpread = 1.0 / gapsPerRow # 0.25
        col = 0.0
        row = 0.0

        for r in range(len(self.rows)):
            for c in range(len(self.cols)):
                channelName = str(self.rows[r])+" "+str(self.cols[c])
                command += channelName + " load "+path+"/" + channelName.replace(" ", "") + ".wav,"
                backFrontMultiplyer = (gapsPerRow - r) / gapsPerRow # row0: 1, row1: 0.75, row3: 0.5, row4: 0.25, row5: 0
                v1 = (1 - (balanceSpread * c)) *  backFrontMultiplyer
                v2 = (balanceSpread * c) * backFrontMultiplyer  
                v3 = (1 - (balanceSpread * c)) * (1 - backFrontMultiplyer)
                v4 = (balanceSpread * c) * (1 - backFrontMultiplyer)
                command += channelName + " panorama "+str(v1)+" "+str(v2)+" "+str(v3)+" "+str(v4)+","
                self.playStates[channelName] = False
                self.enableButton(channelName, False)

        command += "all volume "+str(self.getMasterVolume())+","
        self.sendToPd(command)
            
    def getMasterVolume(self):
        if(self.currentStep is None):
            return 1
        else:
            return self.currentStep["masterVolume"]

    def getChannelVolume(self, channelName):
        v = self.getMasterVolume()
        # todo: implement channel volume
        return v

    def singleHit(self, channelName):
        self.sendToPd(channelName+" play")
        
    def buttonPress(self, channelName):
        if(self.currentMode == GameModes.SINGLE_HIT):
            self.singleHit(channelName)
        else:
            self.playStates[channelName] = not self.playStates.get(channelName)
            if(self.playStates.get(channelName)):
                self.sendToPd(channelName+" volume "+str(self.getChannelVolume(channelName)))
            else:
                self.sendToPd(channelName+" volume 0")
        
            self.enableButton(channelName, self.playStates.get(channelName))

    def enableButton(self, channelName, enable):
        color = 'black' if enable else 'white'
        self.buttons[channelName].configure(highlightbackground=color)

    def sendToPd(self, command):
        print("sending command to PD: "+command)
        os.system("echo '" + command + "' | "+self.conf["SystemSettings"]["pdSendPath"]+" 3000 localhost udp")

    def enableChannel(self, channelName):
        if(self.playStates[channelName]):
            return
        self.sendToPd(channelName + " volume 1")
        self.playStates[channelName] = True
    
    def disableChannel(self, channelName):
        if(not self.playStates.get(channelName)):
            return
        self.sendToPd(channelName + " volume 0")
        self.playStates[channelName] = False

    def onMessage(self, client, userdata, message):
        val = str(message.payload.decode("utf-8"))
        if(message.topic == "control"):
            if(val == "nextSet"):
                self.switchNextSet()
            elif(val == "prevSet"):
                self.switchPrevSet()
            elif(val.startswith("pd:")):
                self.sendToPd(val.split(":")[1])
        elif(message.topic == "sensor"):
            '''
            Callback for MQTT messages
            {"k": "XXX", "v": 100}
            '''
            #print(str(message.payload.decode("utf-8")))
            start_new_thread(self.handleSensorData, (message,))
        elif(message.topic.startswith("sensorControl")):
            if(message.topic.find("set/brightness")):
                self.conf["SystemSettings"]["sensorBrightness"] = int(val)
            elif(message.topic.find("set/triggerLevel")):
                self.conf["SystemSettings"]["sensorTriggerLevel"] = int(val)

        elif(message.topic == "status"):
            obj = json.loads(val)   
            status = obj.get("status")
            mac = obj.get('k')
            print("status: "+mac+" status: "+status)
            if(status == "connected"):
                sensorTopic = "sensorControl"+mac
                self.client.publish(sensorTopic, "{\"command\": \"setTriggerLevel\", \"val\": "+str(self.getSensorTriggerLevel())+"}", 1)
                self.client.publish(sensorTopic, "{\"command\": \"setBrightness\", \"val\": "+str(self.getSensorBrightness())+"}", 1)


    def getSensorBrightness(self): # the brightness of the lights in the sensor
        if(self.currentStep.get("sensorBrightness")):
            return self.currentStep.get("sensorBrightness")
        return self.conf["SystemSettings"]["sensorBrightness"]

    def getSensorTriggerLevel(self): # the sensor value threshold which makes the sensors send an ON and OFF signal
        return self.conf["SystemSettings"]["sensorTriggerLevel"]

    def handleSensorData(self, message):
        val = json.loads(str(message.payload.decode("utf-8")))   
        v = 0.0
        s = 0
        channelName = ""
        try:
            sensorId = val['k']
            v = int(val['v'])
            s = int(val.get('s'))
        except:
            print('Could not digest ' + str(message.payload.decode("utf-8")))
            return
        
        channelName = self.conf["SensorNames"].get(sensorId)
        if(not channelName):
            print("channel for sensorId "+sensorId+" not found")
            return

        prevVal = self.sensorStates.get(sensorId)
        self.sensorStates[sensorId] = v
        print("sensorId: "+sensorId+", channel: "+channelName +  ", v: "+str(v)+ " s:"+str(s))
        if(self.currentMode == GameModes.SINGLE_HIT):
            if(s == 1):
                self.singleHit(channelName)
                self.buttons[channelName].configure(highlightbackground='red')
            else:
                self.buttons[channelName].configure(highlightbackground='white')
        else:
            if(s == 1):
                self.enableChannel(channelName)
                self.buttons[channelName].configure(highlightbackground='black')
            else:
                self.disableChannel(channelName)
                self.buttons[channelName].configure(highlightbackground='white')

        if(s == 1):
            self.activeMacAddrLabel["text"] = sensorId

    def checkTime(self):
        lastStep = None
        for step in self.conf["Scheduler"]['steps'].keys():
            startHour = int(step.split(":")[0])
            startMinute = int(step.split(":")[1])
            startSecond = int(step.split(":")[2])
            startDate = datetime.datetime.now().replace(hour=startHour, minute=startMinute, second=startSecond, microsecond=0)
            #print("now", datetime.datetime.now())
            if(startDate < datetime.datetime.now()):
                lastStep = step

        if(lastStep is not None and lastStep != self.stepCombo.get()):
            print("automatic step switch: ", lastStep)
            self.switchStep(lastStep)

        info = "currentStep: "+self.stepCombo.get()+"\n"
        info += "currentMode: "+self.currentMode+"\n"
        self.client.publish("info", "info: "+info, 0)

        with open("conf1.json", "w") as confFile:
            json.dump(self.conf, confFile, indent=4, sort_keys=False)

    def switchStep(self, stepId):

        self.client.publish("info/step", stepId, 0)
        self.stepCombo.set(stepId)
        self.currentStep = self.conf["Scheduler"]["steps"][stepId]
        print("switch step: ")
        pprint(self.currentStep)
        if(self.currentStep.get('pdCommand')):
            self.sendToPd(self.currentStep.get('pdCommand'))

        self.switchSet(self.currentStep.get("set"))

    def switchNextSet(self):
        currentSet = self.setCombo.get()
        nextIndex = (self.conf["SoundSets"].keys().index(currentSet) + 1) % len(self.conf["SoundSets"].keys())
        nextSetPath = self.conf["SoundSets"].keys()[nextIndex]
        self.switchSet(nextSetPath)

    def switchPrevSet(self):
        currentSet = self.setCombo.get()
        prevIndex = (self.conf["SoundSets"].keys().index(currentSet) - 1) % len(self.conf["SoundSets"].keys())
        prevSetPath = self.conf["SoundSets"].keys()[prevIndex]
        self.switchSet(prevSetPath)

    def switchSet(self, path):
        soundSet = self.conf["SoundSets"].get(path)
        self.setCombo.set(path)

        self.currentMode = GameModes.SINGLE_HIT if soundSet['mode'] == 'SINGLE_HIT' else GameModes.LOOP

        if(self.currentMode == GameModes.SINGLE_HIT):
            self.sendToPd("loop stop, all volume "+str(self.getMasterVolume()))
        else:
            duration = soundSet['duration']
            self.sendToPd("loop start "+duration+", all volume 0") 

        print("New mode: "+self.currentMode)
        self.modeButton["text"] = "Mode: "+self.currentMode
        self.load()
        self.client.publish("info/set", path, 0)
      
    def patchFirmware(self):
        self.client.publish("sensorControl/patch", self.conf["SystemSettings"]["otaUpdateUrl"], 1)

    def copyMacToClipBoard(self):
        root.clipboard_clear()
        root.clipboard_append(self.activeMacAddrLabel['text'])
        root.update()

    def onStepComboChanged(self, event):
        print(self.stepCombo.get())
        self.switchStep(self.stepCombo.get())

    def onSetComboChanged(self, event):
        pprint(self.setCombo.get())
        self.switchSet(self.setCombo.get())

    def createWidgets(self):
        topFrame = Frame(self)
        topFrame.pack( side = TOP)

        stepKeys = self.conf["Scheduler"]["steps"].keys()
        stepKeys.sort()
        self.stepCombo = Combobox(topFrame, values=stepKeys, state="readonly")
        self.stepCombo.pack(side = LEFT)
        self.stepCombo.bind("<<ComboboxSelected>>", self.onStepComboChanged)

        self.setCombo = Combobox(topFrame, values=self.conf["SoundSets"].keys(), state="readonly")
        self.setCombo.pack(side = LEFT)
        self.setCombo.bind("<<ComboboxSelected>>", self.onSetComboChanged)

        self.modeButton = Button(topFrame)
        self.modeButton.pack( side = LEFT)

        footerFrame = Frame(self)
        footerFrame.pack( side = BOTTOM )

        bottomFrame = Frame(self)
        bottomFrame.pack( side = BOTTOM )


        self.activeMacAddrLabel = Button(footerFrame, text='Last active mac',command=self.copyMacToClipBoard)
        self.activeMacAddrLabel.pack(side = LEFT)

        self.patchFirmwareButton = Button(footerFrame, text='Patch Firmware',command=self.patchFirmware)
        self.patchFirmwareButton.pack( side = LEFT)

        #self.activeMacAddressLabel = Label(bottomFrame)
        #self.activeMacAddressLabel.pack( side = LEFT)

        for c in range(len(self.cols)):
            for r in range(len(self.rows)):
                channelName = str(self.rows[r])+" "+str(self.cols[c])
                button = Button(bottomFrame, text=channelName, command=lambda sn=channelName:self.buttonPress(sn))
                button.grid(row=r, column=c)
                self.buttons[channelName] = button


    def __init__(self, master=None):
        Frame.__init__(self, master)

        with open('conf.json') as f:
            self.conf = json.load(f)

        self.pack()
        self.createWidgets()
        print("Connecting to broker...")
        self.client = mqtt.Client(self.conf["brokerSettings"]['client'])
        self.client.connect(self.conf["brokerSettings"]['address'], self.conf["brokerSettings"]['port'])
        print("connected!")
        # wait for MQTT connection
        # TODO: implement proper callback https://www.eclipse.org/paho/clients/python/docs/
        #       with error handling on failed connection
        time.sleep(0.5)
        # sensor: updates from the sensors; control: topic for controlling this program; status: topic where status updates are posted (mostly sensors when the join the network); sensorControl: listening to the control messages of the sensors
        self.client.subscribe([("sensor", 0), ("control", 0), ("status", 0), ("sensorControl/#", 0)])


        # setup callback
        self.client.on_message=self.onMessage
        self.client.loop_start()
        #self.switchSetIndex(0)
        self.switchSet(self.conf["SoundSets"].keys()[0])
        # self.checkTime()
        #self.checkTime()
        self.scheduler = timer.Scheduler(30, self.checkTime)
        self.scheduler.start()


    def quit(self):
        print("Terminating...")
        self.scheduler.stop()
        root.destroy()

root = Tk()
app = Application(master=root)
root.protocol("WM_DELETE_WINDOW", app.quit)

app.mainloop()
