import queue 
import threading 

class MotionController: 
    def __init__(self, motor): 
        self.motor = motor 
        self._cmds = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # Check queue (max block .1 sec) for speed motion cmds, stop if error or stop cmd
    def _loop(self): 
        while not self._stop.is_set(): 
            try: 
                cmd, arg = self._cmds.get(timeout=0.1)
            except queue.Empty: 
                continue 
            try: 
                if cmd == "speed": 
                    self.motor.ramp_to(arg)
            except Exception: 
                self.motor.stop()

    # put cmd in queue
    def request(self, cmd, arg=None): 
        self._cmds.put((cmd, arg))

    # stop motor regardless of queue
    def emergency_stop(self): 
        while not self._cmds.empty(): 
            self._cmds.get_nowait()
        self.motor.stop()

    # set stop event, terminate thread and close motor driver
    def shutdown(self): 
        self._stop.set()
        self._thread.join(timeout=2.0)
        self.motor.close()

    