import logging

import lgpio

log = logging.getLogger(__name__)

# a square wave, which is as loud as a passive buzzer gets
TONE_DUTY = 50


# What the robot sounds like. A sound is (tone in Hz, seconds) played back to back and 0 Hz is
# a silent gap. They have to be told apart by ear across a hall, so no two share a rhythm: an
# active buzzer makes its own pitch and leaves the rhythm as all there is to go on
class Sound:
    READY = ((2000, 0.07), (0, 0.05), (2600, 0.07))     # two short, rising: it takes commands
    START = ((2000, 0.08), (0, 0.05), (2600, 0.25))     # short then long: the drive is running
    STOP  = ((2600, 0.25), (0, 0.05), (2000, 0.08))     # long then short: the drive stands
    OPEN  = ((2600, 0.05), (0, 0.05), (2600, 0.05), (0, 0.05), (2600, 0.05))   # three chirps
    CLOSE = ((2000, 0.35),)                             # one long: scanning again
    FAULT = ((2600, 0.5), (0, 0.08), (2600, 0.5))       # two long: it stopped itself


# A buzzer between a GPIO pin and ground. lgpio times the sound on its own thread, so nothing
# that drives the robot ever waits on a beep, and sounds queue rather than cut each other off
class Buzzer:
    def __init__(self, pin, chip=4):
        self.pin = pin
        # chip 4 is the RP1 on the pi 5, chip 0 on older boards and newer kernels
        self.h = lgpio.gpiochip_open(chip)
        lgpio.gpio_claim_output(self.h, pin, 0)

    # Safe to call from any thread, and it swallows whatever the driver makes of it: this is
    # called from the middle of telling the robot what to do, and a beep is worth nothing there
    def play(self, sound):
        try:
            for hz, seconds in sound:
                if hz:
                    lgpio.tx_pwm(self.h, self.pin, hz, TONE_DUTY, 0, round(hz * seconds))
                else:
                    # a gap is one cycle of a wave that is never pulled high
                    lgpio.tx_pwm(self.h, self.pin, 1.0 / seconds, 0, 0, 1)
        except Exception:
            log.exception("the buzzer did not take a sound")

    def close(self):
        # A sound cut off mid cycle leaves the pin where it stood, so it is put down by hand: a
        # buzzer still sounding after the robot is down is worse than no buzzer at all. lgpio
        # calls a cancel with nothing playing a bad request, which is no reason to fail a stop
        try:
            lgpio.tx_pwm(self.h, self.pin, 0, 0, 0, 0)
        except Exception:
            pass
        lgpio.gpio_write(self.h, self.pin, 0)
        lgpio.gpiochip_close(self.h)
