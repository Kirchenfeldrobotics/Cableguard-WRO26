import logging
import queue
import threading
from motion.stepper import Stepper

log = logging.getLogger(__name__)

class MotionController: 
    def __init__(self, motor: Stepper): 
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
            while not self._cmds.empty():
                cmd, arg = self._cmds.get_nowait()
            try:
                if cmd == "speed":
                    self.motor.ramp_to(arg)
                elif cmd == "stop":
                    self.motor.stop()
                    log.info("stopped at %.2f m", self.motor.metres_done)
            except Exception:
                log.exception("motion command failed: %s", cmd)
                try:
                    self.motor.stop()
                except Exception:
                    log.exception("stop after failed command failed")

    # put cmd in queue
    def request(self, cmd: str, arg=None): 
        if cmd == "speed":
            self.motor.abort.clear()
        self._cmds.put((cmd, arg))

    # stop motor regardless of queue
    def emergency_stop(self):
        # The motion thread can be inside a ramp or waiting on the driver queue, and while
        # it is, the feeder keeps handing out cruise blocks. Cutting the cruise here stops
        # the pulses whatever that thread is doing; the queued stop ramps down the rest of
        # the way once it gets its turn.
        self.motor.abort.set()
        self.motor.cut_cruise()
        self._cmds.put(("stop", None))

    # set stop event, terminate thread and close motor driver
    def shutdown(self): 
        self._stop.set()
        self._thread.join(timeout=2.0)
        self.motor.close()

    