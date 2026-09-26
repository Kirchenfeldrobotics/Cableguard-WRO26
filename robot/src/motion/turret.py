import math
import threading
import time

from motion.stepper import Stepper

# Motor turns for one full turn of the camera ring. Placeholder until the ring is measured:
# 1.0 means the motor sits on the ring axis, a reduction makes it larger
GEAR_RATIO = 1.0

# The ring rings after a move. The cameras get this long to come to rest before a frame is
# captured, otherwise the rope is smeared across it
SETTLE_S = 0.05

# The fastest the ring is swung, degrees per second. The camera cables set this, not the
# motor: every move of the ring is paced by it, and the scan cycle asks for all of it. The
# robot passes the operator's own value from comm_protocols/settings.py, this is what a script
# that drives the ring alone gets
MAX_DEG_S = 200.0

# Where a turn starts from and ends at, degrees per second. A stepper cannot be asked for its
# full speed out of nowhere. It is low on purpose: with a reduction between motor and ring,
# a degree of the ring is several times as much motor, and the ramp makes the time up anyway
START_DEG_S = 10.0

# How hard the ring ramps, degrees per second squared. Gentle on purpose: the motor carries
# the ring itself, and one asked for more than it can pull slips instead of turning
ACCEL_DEG_S2 = 500.0

# Slowest the ring is driven. A move that has more time than it needs runs at this speed and
# is simply done early; below it the driver loses the feeling for where it is
MIN_DEG_S = 5.0

# Segments a ramp is cut into. The whole move is ramp, so it is kept short enough that the
# PIO holds most of it at once and plays the segments back to back
RAMP_SEGMENTS = 6


# The stepper that swings both cameras around the rope. Two cameras facing each other see
# two sides of it and leave two blind ones, so between detector frames the ring turns them
# a quarter turn onto the blind sides and back again. It always comes back: the cameras
# hang on their cables, a ring that kept turning one way would wind them up.
#
# Where the ring stands is its own step counter, and the counter only grows by blocks the
# PIO reports as played. A move that is cut short therefore leaves the angle correct, and
# every target is absolute, so nothing drifts over a run.
#
# Its whole pace is set in the degrees the operator can measure rather than in the microsteps
# the driver counts: see _scale, the only place the two meet
class Turret(Stepper):
    def __init__(self,
                 pul_pin,
                 dir_pin,
                 gear_ratio=GEAR_RATIO,
                 start_deg_s=START_DEG_S,
                 max_deg_s=MAX_DEG_S,
                 accel_deg_s2=ACCEL_DEG_S2,
                 settle_s=SETTLE_S,
                 min_deg_s=MIN_DEG_S,
                 ramp_segments=RAMP_SEGMENTS,
                 start_angle=0.0,
                 **kwargs):                 # the rest is the base driver's, see stepper.py

        super().__init__(pul_pin, dir_pin, ramp_segments=ramp_segments, **kwargs)

        self.gear_ratio = gear_ratio
        self.settle_s   = settle_s

        self.start_deg_s  = start_deg_s
        self.max_deg_s    = max_deg_s
        self.accel_deg_s2 = accel_deg_s2
        self.min_deg_s    = min_deg_s
        self._scale()

        # The ring has no endstop, so its angle is the one it is told it has. Whoever sets
        # the robot up leaves it at start_angle, and the counter starts from there
        self.start_angle = start_angle
        self._accum      = self._steps_at(start_angle)

        # One move at a time. A turn runs in a worker thread, and shutting down cancels the
        # task waiting on it without stopping the thread, so close() can arrive while the
        # ring is still going; two moves interleaving would leave it anywhere
        self._turning = threading.Lock()

    # The ring's pace in the microsteps per second the base driver works in. One place, so a
    # change of microstepping or gearing carries all of them with it. A move given no time of
    # its own runs at max_speed, and min_turn_s reports what a turn costs at it
    def _scale(self):
        per_deg = self.microsteps_per_deg

        # The operator's pace is the pace. Nothing else may quietly cap the ring: a reduction
        # between motor and ring multiplies the microsteps a degree costs, and a ceiling in
        # microsteps would then turn the speed that was asked for into some fraction of it
        self.max_speed = min(self.max_deg_s * per_deg, self.max_pulse_speed)
        # a start above the cap would be a move that ignores the cap altogether
        self.start_speed = min(self.start_deg_s, self.max_deg_s) * per_deg
        self.accel       = self.accel_deg_s2 * per_deg
        self.min_speed   = self.min_deg_s * per_deg

    # Take a new set of the operator's numbers. The ring has to be standing at the angle it
    # is calibrated against, because none of this moves it: only the numbers that describe
    # it change, so the counter is seated again at the angle the robot is set up to rest at
    def configure(self, full_steps, microsteps, gear_ratio, start_deg_s, max_deg_s,
                  accel_deg_s2, settle_s, start_angle):
        with self._turning:
            self._wait_idle()          # the counter is only ours to set once nothing is queued

            self.full_steps_per_rev = full_steps
            self.microsteps   = microsteps
            self.gear_ratio   = gear_ratio
            self.start_deg_s  = start_deg_s
            self.max_deg_s    = max_deg_s
            self.accel_deg_s2 = accel_deg_s2
            self.settle_s     = settle_s
            self.start_angle  = start_angle
            self._scale()

            with self._lock:
                self._accum = self._steps_at(start_angle)

    # microsteps for one degree of the ring, not of the motor
    @property
    def microsteps_per_deg(self):
        return self.steps_per_rev * self.gear_ratio / 360.0

    # where the ring stands, degrees from the parked position
    @property
    def angle(self):
        return self.microsteps_done / self.microsteps_per_deg

    # microsteps from the parked position for an angle
    def _steps_at(self, degrees):
        return round(degrees * self.microsteps_per_deg)

    # whether the ring stands on an angle, compared in steps so it is exact
    def at(self, degrees):
        return self.microsteps_done == self._steps_at(degrees)

    # Cruise speed that gets `steps` done in `seconds`, or the fastest the ramp allows when
    # there is no time to fill. Both ramps and the cruise between them add up to
    #   seconds = 2 * (v - v0) / a + (steps - (v^2 - v0^2) / a) / v
    # which is a quadratic in v; its smaller root is the one that lasts the full time
    def _cruise_speed_for(self, steps, seconds):
        v0, a = self.start_speed, self.accel

        peak    = math.sqrt(v0 ** 2 + a * steps)   # a ramp up and straight down again
        fastest = min(peak, self.max_speed)

        if seconds is None:
            return fastest

        b    = 2.0 * v0 + a * seconds
        disc = b ** 2 - 4.0 * (a * steps + v0 ** 2)
        if disc <= 0.0:
            return fastest                         # no speed is slow enough to fill it

        return min(max((b - math.sqrt(disc)) / 2.0, self.min_speed), fastest)

    # the move as (speed, steps) segments: ramp up, cruise, ramp down. The cruise block
    # takes whatever the two ramps leave over, so the step count comes out exact
    def _profile(self, steps, v):
        up   = self.ramp_segments(self.start_speed, v)
        down = self.ramp_segments(v, self.start_speed)

        cruise = steps - sum(c for _, c in up) - sum(c for _, c in down)
        return up + ([(v, cruise)] if cruise > 0 else []) + down

    # shortest a turn of this size can take, the settle after it included
    def min_turn_s(self, degrees):
        steps = abs(self._steps_at(degrees))
        if steps == 0:
            return 0.0
        return self.duration(self._profile(steps, self._cruise_speed_for(steps, None))) + self.settle_s

    # Turn the ring to an absolute angle and take `seconds` over it, or go as fast as the
    # ramp allows when no time is given. Returns once the cameras stand still
    def turn_to(self, degrees, seconds=None):
        with self._turning:
            self._wait_idle()                 # the counter is only exact once nothing is queued

            delta = self._steps_at(degrees) - self.microsteps_done
            if delta == 0:
                return

            budget = max(seconds - self.settle_s, 0.0) if seconds is not None else None

            self.set_direction(delta > 0)
            self._forward = delta > 0

            steps = abs(delta)
            self._emit(self._profile(steps, self._cruise_speed_for(steps, budget)))

            self._wait_idle()
            self._speed = 0.0
            time.sleep(self.settle_s)

    # back to the angle the ring was calibrated at, unwinding its cables
    def park(self):
        self.turn_to(self.start_angle)

    def close(self):
        try:
            self.park()
        finally:
            super().close()
