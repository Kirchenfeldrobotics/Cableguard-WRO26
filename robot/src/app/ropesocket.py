import logging

log = logging.getLogger(__name__)


# A rope socket is the fitting the rope ends in. The camera ring cannot turn past one, so
# before the robot reaches it, it opens: the ring parks at the one angle that clears the
# socket and the detector stops until the socket is behind the robot. Driving and the video
# stream carry on, the robot has to get past the socket after all.
#
# Two things open the robot, and whichever did decides what closes it again. The distance
# sensor opens it when what it sees changes, and closes it once the robot has driven clear;
# the operator opens it from the webapp, and only the operator closes that again.
#
# The sensor knows a socket by how far its reading has come in from the one it was calibrated
# on, not by the reading itself: where the beam lands and what it finds there depends on how
# the sensor sits and which rope it is, so an absolute distance would mean something different
# on every run.
#
# Every caller runs on the robot's event loop, so the state needs no lock.
class RopeSocket:
    def __init__(self, trigger_diff_m, clear_m, watch=True):
        self.trigger_diff_m = trigger_diff_m  # this much nearer than normal is a socket ahead
        self.clear_m        = clear_m   # driven from the last sighting, the socket is behind
        self.watch          = watch     # the sensor may open the robot by itself
        self.baseline_m     = None      # what the sensor reads with no socket in front of it
        self._opened_by     = None      # "sensor", "user", or None while the robot is closed
        self._mark          = 0.0       # metres where the sensor last saw something

    # What the sensor sees along the rope with nothing in the way, taken while the robot still
    # stands where it was put on. Readings that found no target say nothing about the distance
    # and are left out; a burst that is half of those is not a normal to measure against, so
    # the sensor's own opening is switched off rather than left to guess
    def calibrate(self, readings):
        seen = [r for r in readings if r is not None]

        if len(seen) * 2 <= len(readings):
            self.watch = False
            log.warning("the distance sensor found nothing to calibrate on in %d readings, "
                        "it will not open the robot by itself", len(readings))
            return False

        self.baseline_m = sum(seen) / len(seen)
        log.info("distance sensor calibrated at %.2f m over %d of %d readings, a socket is "
                 "%.2f m nearer than that", self.baseline_m, len(seen), len(readings),
                 self.trigger_diff_m)
        return True

    @property
    def is_open(self):
        return self._opened_by is not None

    # One reading of the distance sensor, None when nothing is in range. The mark is set
    # again on every close reading, so the clear distance runs from the last sight of the
    # socket rather than the first: a long socket would otherwise let the ring turn while
    # the robot is still beside it
    def saw(self, distance_m, position):
        if not self.watch or distance_m is None or self.baseline_m is None:
            return

        # A socket is something the beam meets nearer than what it was calibrated on. Only
        # nearer: a reading that runs long has lost its target, which is not a socket
        if self.baseline_m - distance_m < self.trigger_diff_m:
            return

        if self._opened_by is None:
            log.info("%.2f m where %.2f m is normal, opening the robot for a rope socket",
                     distance_m, self.baseline_m)
            self._opened_by = "sensor"

        if self._opened_by == "sensor":
            self._mark = position

    # Closes a robot the sensor opened, once it has driven the clear distance from the last
    # sighting. Reversing counts as well: away from the socket is past it too
    def close_if_clear(self, position):
        if self._opened_by == "sensor" and abs(position - self._mark) >= self.clear_m:
            log.info("%.2f m driven since the rope socket, closing the robot", self.clear_m)
            self._opened_by = None

    # the operator's own opening, which outlasts anything the sensor decides
    def open_by_user(self):
        if self._opened_by != "user":
            log.info("open requested")
            self._opened_by = "user"

    def close_by_user(self):
        if self.is_open:
            log.info("close requested")
            self._opened_by = None

    # Taking the sensor out of the loop also closes an opening it caused: the sensor was the
    # only reason the robot was open
    def set_watch(self, enabled):
        self.watch = enabled
        log.info("rope socket watch %s", "armed" if enabled else "off")

        if not enabled and self._opened_by == "sensor":
            log.info("closing the robot, its rope socket watch was switched off")
            self._opened_by = None

    # The run's origin moved, so the mark the clear distance is measured from has to move
    # with it, or the robot closes on the spot or never
    def rebase(self, position):
        self._mark = position
