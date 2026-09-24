import threading
import time

from motion.stepper import Stepper

# How far the rope moves per microstep. Placeholder until the drive is measured:
# 1600 microsteps per turn on a 50 mm wheel. Every metre in the system comes from here
MICROSTEPS_PER_METRE = 10186.0


# The stepper that moves the robot along the rope. It runs at a speed the scan plan picks
# and holds it for as long as the operator lets it, so cruise is fed in finite blocks by a
# thread of its own: that keeps every step countable without stopping between blocks
class Drive(Stepper):
    def __init__(self,
                 pul_pin,
                 dir_pin,
                 microsteps_per_metre=MICROSTEPS_PER_METRE,
                 cruise_block_s=0.02,
                 cruise_blocks_ahead=3,
                 **kwargs):                 # the rest is the base driver's, see stepper.py

        super().__init__(pul_pin, dir_pin, **kwargs)

        # drive geometry, the only place microsteps and metres meet
        self.microsteps_per_metre = microsteps_per_metre

        # One cruise block = one word to the PIO. Enough blocks stay queued to ride out a
        # busy CPU, few enough that a stop is not stuck behind them for long
        self.cruise_block_s      = cruise_block_s
        self.cruise_blocks_ahead = cruise_blocks_ahead

        self._cruise_speed = 0.0
        self._closing      = threading.Event()
        self._feeder       = threading.Thread(target=self._feeder_loop, daemon=True)
        self._feeder.start()

    # Take a new set of the operator's numbers. Only safe while the drive stands: all of
    # them are read inside a running ramp, and the scale turns the microsteps already
    # counted into a different number of metres
    def configure(self, microsteps, microsteps_per_metre, start_speed, max_speed, accel):
        self.microsteps           = microsteps
        self.microsteps_per_metre = microsteps_per_metre
        self.start_speed          = start_speed
        self.max_speed            = max_speed
        self.accel                = accel

    # metres for a microstep count. Speeds convert with the same factor, microsteps per
    # second over microsteps per metre is metres per second
    def to_metres(self, microsteps):
        return microsteps / self.microsteps_per_metre

    # microsteps for a distance in metres, or microsteps per second for a speed in m/s
    def to_microsteps(self, metres):
        return metres * self.microsteps_per_metre

    # distance since last reset, signed with the direction driven
    @property
    def metres_done(self):
        return self.to_metres(self.microsteps_done)

    # current speed in metres per second, signed like speed
    @property
    def speed_mps(self):
        return self.to_metres(self.speed)

    # tops up the queue while cruising, so cruise steps stay counted
    def _feeder_loop(self):
        while not self._closing.is_set():
            v = self._cruise_speed
            if v > 0.0 and self._pending_blocks() < self.cruise_blocks_ahead:
                self._put(v, max(1, int(self.cruise_block_s * v)))
            time.sleep(self.cruise_block_s / 4.0)

    # ramp to speed and cruise there (if cruise flag is set)
    def ramp_to(self, speed, cruise=True):
        target  = min(abs(speed), self.max_speed)
        forward = speed >= 0

        if self.moving and forward != self._forward:
            self.stop()

        if target < self.start_speed:
            self.stop()
            return

        if not self.moving:
            self.set_direction(forward)
            self._forward = forward

        completed = self._emit(self.ramp_segments(self._speed, target), abortable=True)

        if not completed:
            return

        if cruise:
            self._speed        = target
            self._cruise_speed = target   # hand over to the feeder thread
        else:
            self._wait_idle()
            self._speed = 0.0

    # stop feeding cruise blocks. Safe to call from any thread: the feeder picks it up on
    # its next pass and the queued blocks then play out within cruise_blocks_ahead blocks.
    # stop() has to run on the motion thread, this does not
    def cut_cruise(self):
        self._cruise_speed = 0.0

    # ramp stepper to 0.0
    def stop(self):
        if not self.moving:
            return

        self._cruise_speed = 0.0   # feeder stops adding blocks first

        segments = self.ramp_segments(self._speed, 0.0)
        if segments:
            self._emit(segments)

        # Blocks already handed to the PIO cannot be taken back, so the ramp and any cruise
        # block still queued play out first. Waiting for them keeps the position exact and
        # makes sure the last pulse is over before the direction may change
        self._wait_idle()
        self._speed = 0.0

    def close(self):
        try:
            self.stop()
        finally:
            self._closing.set()
            self._feeder.join(timeout=1.0)
            super().close()

    # keep script running for n seconds
    def hold_s(self, seconds):
        if seconds <= 0:
            return

        time.sleep(seconds)
