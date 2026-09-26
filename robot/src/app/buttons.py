import logging

import lgpio

log = logging.getLogger(__name__)

# A press counts once the level has held this long: longer than the bounce of a switch or a
# spike the stepper drivers put on the wire, shorter than any press a hand can make
DEBOUNCE_US = 20000


# A push button between a GPIO pin and ground. The pull-up holds the pin high, so the press
# is the falling edge, and lgpio watches for it on a thread of its own. What a press means
# is not this driver's business: it calls an action, see app/main.py
class Button:
    def __init__(self, pin, action, chip=4, debounce_us=DEBOUNCE_US):
        self.pin     = pin
        self._action = action

        # chip 4 is the RP1 on the pi 5, chip 0 on older boards and newer kernels
        self.h = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_alert(self.h, pin, eFlags=lgpio.FALLING_EDGE, lFlags=lgpio.SET_PULL_UP)
        lgpio.gpio_set_debounce_micros(self.h, pin, debounce_us)
        self._cb = lgpio.callback(self.h, pin, lgpio.FALLING_EDGE, self._edge)

    # lgpio's thread, not the robot's. A press caught mid shutdown finds the event loop gone,
    # and the traceback would be swallowed in here
    def _edge(self, chip, pin, level, timestamp):
        try:
            self._action()
        except Exception:
            log.exception("press of the button on GPIO %d went nowhere", self.pin)

    def close(self):
        self._cb.cancel()
        lgpio.gpiochip_close(self.h)
