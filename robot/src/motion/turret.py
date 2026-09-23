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

# Slowest the ring is driven. A move that has more time than it needs runs at this speed and
# is simply done early; below it the driver loses the feeling for where it is
MIN_SPEED = 50.0

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
# every target is absolute, so nothing drifts over a run
class Turret(Stepper):
    def __init__(self,
                 pul_pin,
                 dir_pin,
                 gear_ratio=GEAR_RATIO,
                 settle_s=SETTLE_S,
                 min_speed=MIN_SPEED,
                 ramp_segments=RAMP_SEGMENTS,
                 **kwargs):                 # the rest is the base driver's, see stepper.py

        super().__init__(pul_pin, dir_pin, ramp_segments=ramp_segments, **kwargs)

        self.gear_ratio = gear_ratio
        self.settle_s   = settle_s
        self.min_speed  = min_speed

        # One move at a time. A turn runs in a worker thread, and shutting down cancels the
        # task waiting on it without stopping the thread, so close() can arrive while the
        # ring is still going; two moves interleaving would leave it anywhere
        self._turning = threading.Lock()

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

    # Back to where the cameras started, unwinding their cables. Without a time it goes as
    # fast as the ring allows, which is more than the cables take
    def park(self, seconds=None):
        self.turn_to(0.0, seconds)

    def close(self, seconds=None):
        try:
            self.park(seconds)
        finally:
            super().close()
