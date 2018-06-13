import threading

class Scheduler(threading.Thread):
    def __init__(self, interval, callback):
        threading.Thread.__init__(self)
        self.event = threading.Event()
        self.count = 0
        self.interval = interval
        self.callback = callback

    def run(self):
        while not self.event.is_set():
            self.count = (self.count + 1) % self.interval
            if(self.count == 0):
                self.callback()

            self.event.wait(1)

    def stop(self):
        self.event.set()
