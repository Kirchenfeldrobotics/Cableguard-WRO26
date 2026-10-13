import logging

import lgpio

log = logging.getLogger(__name__)

# A press counts once the level has held this long: longer than the bounce of a switch or a
# spike the stepper drivers put on the wire, shorter than any press a hand can make
DEBOUNCE_US = 20000

# what lgpio reports for a pin that came to rest low, which is the button held down
PRESSED = 0


# A push button between a GPIO pin and ground. The pull-up holds the pin high and a press
# pulls it low, and lgpio watches the pin on a thread of its own. What a press means is not
# this driver's business: it calls an action, see app/main.py.
#
# Both edges are watched although only the press is wanted. lgpio's debounce never reads the
# pin: it waits until the edges it is shown have stopped coming and reports the last of them.
# Shown falling edges alone, it cannot tell a pin that stayed low from one that went straight
# back up, so the bounce of a button being let go came out as a second press, and any spike on
# the wire as a press of its own. Shown both, the last edge is where the pin came to rest
class Button:
    def __init__(self, pin, action, chip=4, debounce_us=DEBOUNCE_US):
        self.pin     = pin
        self._action = action

        # chip 4 is the RP1 on the pi 5, chip 0 on older boards and newer kernels
        self.h = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_alert(self.h, pin, eFlags=lgpio.BOTH_EDGES, lFlags=lgpio.SET_PULL_UP)
        lgpio.gpio_set_debounce_micros(self.h, pin, debounce_us)
        # the edge named here selects nothing, lgpio hands every report for the pin over
        self._cb = lgpio.callback(self.h, pin, lgpio.BOTH_EDGES, self._edge)

    # lgpio's thread, not the robot's. A press caught mid shutdown finds the event loop gone,
    # and the traceback would be swallowed in here
    def _edge(self, chip, pin, level, timestamp):
        # the button being let go is reported as well, and is not a press
        if level != PRESSED:
            return
        try:
            self._action()
        except Exception:
            log.exception("press of the button on GPIO %d went nowhere", self.pin)

    def close(self):
        self._cb.cancel()
        lgpio.gpiochip_close(self.h)
