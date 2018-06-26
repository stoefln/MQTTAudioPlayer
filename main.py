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
# pip install paho-mqtt
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
    currentPlayMode = GameModes.SINGLE_HIT
    currentStep = None
    selectedChannelName = None

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
                command += channelName + " volume "+str(self.getChannelVolume(channelName, True))+","
                self.playStates[channelName] = False
                self.enableButton(channelName, False)

        self.sendToPd(command)
            
    def getMasterVolume(self):
        if(self.currentStep is None):
            return 1
        else:
            return self.currentStep["masterVolume"]

    def getChannelVolume(self, channelName, includeMasterVolume):
        channelConfig = self.currentSet.get(channelName)
        if(channelConfig):
            v = channelConfig.get("volume")
        else:
            v = 1
        if(includeMasterVolume):
            v = v * self.getMasterVolume()

        return v

    def singleHit(self, channelName):
        self.sendToPd(channelName+" play")
        
    def buttonPress(self, channelName):
        print(self.currentMode.get())
        if(self.currentMode.get() == "play"):
            if(self.currentGameMode == GameModes.SINGLE_HIT):
                self.singleHit(channelName)
            else:
                self.playStates[channelName] = not self.playStates.get(channelName)
                if(self.playStates.get(channelName)):
                    self.sendChannelVolumeToPd(channelName)
                else:
                    self.sendToPd(channelName+" volume 0")
            
                self.enableButton(channelName, self.playStates.get(channelName))
        elif(self.currentMode.get() == "setMac"):
            lastActiveMac = self.activeMacAddrLabel["text"]
            self.conf["SensorNames"][lastActiveMac] = channelName   
            self.currentMode.set("play")         
        elif(self.currentMode.get() == "setVolume"):
            self.currentChannelVolumeLabel["text"] = str(self.getChannelVolume(channelName, False))
            self.selectedChannelName = channelName

    def sendChannelVolumeToPd(self, channelName):
        self.sendToPd(channelName+" volume "+str(self.getChannelVolume(channelName, True))) 

    def enableButton(self, channelName, enable):
        color = 'black' if enable else 'white'
        self.buttons[channelName].configure(highlightbackground=color)

    def sendToPd(self, command):
        print("sending command to PD: "+command)
        os.system("echo '" + command + "' | "+self.conf["SystemSettings"]["pdSendPath"]+" 3000 localhost udp")

    def enableChannel(self, channelName):
        if(self.playStates[channelName]):
            return
        self.sendToPd(channelName + " volume "+str(self.getChannelVolume(channelName, True)))
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
        if(self.currentStep and self.currentStep.get("sensorBrightness")):
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
        if(self.currentGameMode == GameModes.SINGLE_HIT):
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
        info += "currentGameMode: "+self.currentGameMode+"\n"
        self.client.publish("info", "info: "+info, 0)


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
        self.currentSet = self.conf["SoundSets"].get(path)
        self.setCombo.set(path)

        self.currentGameMode = GameModes.SINGLE_HIT if self.currentSet['mode'] == 'SINGLE_HIT' else GameModes.LOOP

        if(self.currentGameMode == GameModes.SINGLE_HIT):
            self.sendToPd("loop stop, all volume "+str(self.getMasterVolume()))
        else:
            duration = self.currentSet['duration']
            self.sendToPd("loop start "+duration+", all volume 0") 

        print("New mode: "+self.currentGameMode)
        self.infoLabel["text"] = ("Mode: {0}\n"
                                  "MasterVolume: {1}\n"
                                  "SensorBrightness: {2}").format(self.currentGameMode, self.getMasterVolume(), self.getSensorBrightness())
        
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

    def increaseChannelVolume(self):
        self.setCurrentChannelVolume(self.getChannelVolume(self.selectedChannelName, False) + 0.1)
        
    def decreaseChannelVolume(self):
        self.setCurrentChannelVolume(self.getChannelVolume(self.selectedChannelName, False) - 0.1)
    
    def setCurrentChannelVolume(self, v):
        self.currentChannelVolumeLabel["text"] = str(v)
        self.currentSet[self.selectedChannelName] = {}
        self.currentSet[self.selectedChannelName]["volume"] = v
        self.sendChannelVolumeToPd(self.selectedChannelName)
        self.singleHit(self.selectedChannelName)

    def saveConfig(self):
        with open("conf1.json", "w") as confFile:
            json.dump(self.conf, confFile, indent=4, sort_keys=False)
        print("config saved: ")
        pprint(self.conf)

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

        contentFrame = Frame(self)
        contentFrame.pack( side = LEFT )

        contentLeft = Frame(contentFrame)
        contentLeft.pack( side = LEFT )

        contentMiddle = Frame(contentFrame)
        contentMiddle.pack( side = LEFT )

        contentRight = Frame(contentFrame)
        contentRight.pack( side = LEFT )

        footerFrame = Frame(self)
        footerFrame.pack( side = BOTTOM )
        
        self.infoLabel = Label(contentRight, text="info", anchor='w')
        self.infoLabel.pack(fill='both')

        self.currentMode = StringVar()
        Radiobutton(contentMiddle, text = "Play", variable = self.currentMode, value = "play").grid(row=0, column=0)
        Radiobutton(contentMiddle, text = "Write Mac to config", variable = self.currentMode, value = "setMac").grid(row=1, column=0)
        Radiobutton(contentMiddle, text = "Set volume", variable = self.currentMode, value = "setVolume").grid(row=2, column=0)

        Button(contentMiddle, text="-", command=self.decreaseChannelVolume).grid(row=2, column=1)        
        self.currentChannelVolumeLabel = Label(contentMiddle, text="vol")
        self.currentChannelVolumeLabel.grid(row=2, column=2)
        Button(contentMiddle, text="+", command=self.increaseChannelVolume).grid(row=2, column=3)        
        
        self.currentMode.set("play")

        self.activeMacAddrLabel = Button(contentMiddle, text='Last active mac',command=self.copyMacToClipBoard)
        self.activeMacAddrLabel.grid(row=3, column=0)

        self.patchFirmwareButton = Button(contentMiddle, text='Patch Firmware',command=self.patchFirmware)
        self.patchFirmwareButton.grid(row=4, column=0)

        self.saveButton = Button(contentMiddle, text='Save Configuration',command=self.saveConfig)
        self.saveButton.grid(row=5, column=0)

        #self.activeMacAddressLabel = Label(contentFrame)
        #self.activeMacAddressLabel.pack( side = LEFT)

        for c in range(len(self.cols)):
            for r in range(len(self.rows)):
                channelName = str(self.rows[r])+" "+str(self.cols[c])
                button = Button(contentLeft, text=channelName, command=lambda sn=channelName:self.buttonPress(sn))
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
