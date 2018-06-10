from Tkinter import *
import os
import appconfig as conf
import os.path
import time
import json
import pkgutil
from threading import Thread

# ---------------------------------------------------
# 3rd Party Libs (install with pip)
import numpy #pip install numpy
import paho.mqtt.client as mqtt # pip install paho-mqtt

class Application(Frame):
    TRIGGER_LEVEL = 70
    playStates = {"looping": False}
    sensorStates = {}
    buttons = {}
    currentMode = 1 # 0... single shot, 1...loop

    def load(self):
        print "loading sounds into PD.."
        command = ""
        for k in conf.SensorNames:
            v = conf.SensorNames[k]
            command += v + " load ../media/loops1/" + v.replace(" ", "") + ".wav,"
        print "command: "+command
        self.sendToPd(command)
    
    def playAll(self):
        if(self.playStates.get("looping")):
            self.sendToPd("loop stop")    
        else:
            self.sendToPd("loop start 60, all volume 0") 
        self.playStates["looping"] = not self.playStates["looping"]   
        
    def playChannel(self, sensorName):
        self.sendToPd(sensorName+" play")
        
    def buttonPress(self, channelName):
        command = channelName
        if(self.playStates.get(channelName)):
            self.playStates[channelName] = False
            command += " volume 0"
        else:
            self.playStates[channelName] = True
            command += " volume 1"
        color = 'black' if self.playStates.get(channelName) else 'white'
        self.buttons[channelName].configure(highlightbackground=color)
        return command
    
    def sendToPd(self, command):
        print("sending command to PD: "+command)
        os.system("echo '" + command + "' | "+conf.SystemSettings["pdSendPath"]+" 3000 localhost udp")

    def createWidgets(self):
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit

        #self.QUIT.pack({"side": "left"})

        cols = [1, 2, 3, 4, 5]
        rows = ["A", "B", "C", "D", "E"]
        
        for c in range(len(cols)):
            for r in range(len(rows)):
                button = Button(self)
                channelName = str(rows[r])+" "+str(cols[c])
                button["text"] = channelName
                button["command"] = lambda sn=channelName:self.sendToPd(self.buttonPress(sn))
                button.grid(row=r, column=c)
                self.buttons[channelName] = button
                
        self.loadButton = Button(self, text="Load", command=self.load)
        self.loadButton.grid(row=5, column=0, columnspan=2)

        self.playAllButton = Button(self, text="PlayAll", command=self.playAll)
        self.playAllButton.grid(row=5, column=2, columnspan=2)

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
        if(self.currentMode == 0):
            if(v > self.TRIGGER_LEVEL and prevVal < self.TRIGGER_LEVEL):
                self.playChannel(channelName)
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

root = Tk()
app = Application(master=root)
app.mainloop()
root.destroy()
