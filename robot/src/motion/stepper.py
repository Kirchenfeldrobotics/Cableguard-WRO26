import lgpio, math, threading, time
from collections import deque

from motion import stepgen

# What every stepper on the robot has in common: a step pin fed by a PIO channel, a
# direction pin on plain GPIO, a ramp and an exact count of the steps that were played.
# The two drivers built on it are motion/drive.py, which moves the robot along the rope,
# and motion/turret.py, which swings the cameras around it
class Stepper():
    def __init__(self,
                 pul_pin,
                 dir_pin,
                 ena_pin=None,
                 chip=4,
                 dir_setup_s=0.001,
                 ena_settle_s=0.2,
                 invert_dir=False,
                 ena_active_high=False,
                 full_steps=200,
                 microsteps=8,
                 ramp_segments=40,
                 start_speed=200.0,
                 max_speed=2000.0,
                 accel=400.0):

        # specify pin numbers
        self.pul_pin = pul_pin
        self.dir_pin = dir_pin
        self.ena_pin = ena_pin

        # specify driver timing, the pulse itself is fixed at 10 us by the PIO program
        self.dir_setup_s  = dir_setup_s   # break after direction high
        self.ena_settle_s = ena_settle_s  # break after enabled high

        # specify driver flags
        self.invert_dir      = invert_dir        # stepper direction inverted
        self.ena_active_high = ena_active_high   # stepper active on enabled high

        # specify steps
        self.full_steps_per_rev = full_steps    # what one turn of the shaft takes
        self.microsteps         = microsteps    # what the driver makes of each of them

        # how many constant-speed segments a ramp is approximated with
        self.n_ramp_segments = ramp_segments

        # speed
        self.start_speed = start_speed
        self.max_speed   = max_speed
        self.accel       = accel

        # the PIO takes the step pin over, lgpio must not claim it afterwards or the pin
        # falls back to plain GPIO
        self._channel = stepgen.open_channel(pul_pin)

        # lgpio (no daemon, unlike pigpio) drives direction and enable
        # chip 4 is the RP1 on the pi 5, chip 0 on older boards and newer kernels
        self.h = lgpio.gpiochip_open(chip)

        lgpio.gpio_claim_output(self.h, dir_pin, 0)

        if ena_pin is not None:
            lgpio.gpio_claim_output(self.h, ena_pin, 0)
            self.disable()

        # runtime vars
        self._speed   = 0.0
        self._forward = True
        self.abort    = threading.Event()   # cuts a running ramp short, see _emit

        # position: a block's steps are banked once the PIO reports it played, so the count
        # never runs ahead of the motor
        self._accum   = 0
        self._pending = deque()   # signed steps of every block the PIO has not played yet
        self._lock    = threading.Lock()

    def __enter__(self):
        self.enable()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # Microsteps for one turn of the shaft: the motor's own steps times what the driver makes
    # of each. It has to be what the hardware really does, or every angle and distance the
    # robot reports is out by the same factor
    @property
    def steps_per_rev(self):
        return self.full_steps_per_rev * self.microsteps

    # fastest train the step generator can play, microsteps per second. Nothing above this
    # reaches the motor: the PIO refuses the block instead
    @property
    def max_pulse_speed(self):
        return 1e6 / stepgen.MIN_PERIOD_US

    # and the slowest. A block below it is refused too, which would leave a move half played
    @property
    def min_pulse_speed(self):
        return 1e6 / stepgen.MAX_PERIOD_US

    # returns moving state
    @property
    def moving(self):
        return self._speed > 0.0

    # return current speed
    @property
    def speed(self):
        return self._speed if self._forward else self._speed * -1

    # number of microsteps since last reset, signed with the direction driven
    @property
    def microsteps_done(self):
        return self._accum

    # number of steps since last reset
    @property
    def full_steps_done(self):
        return self.microsteps_done / self.microsteps

    # number of revolutions since last reset
    def revolutions_done(self):
        return self.full_steps_done / self.steps_per_rev

    # reset number of microsteps done
    def reset_steps_done(self):
        with self._lock:
            self._accum = 0

    # enable stepper (ena pin required)
    def enable(self):
        if self.ena_pin is None:
            return
        lgpio.gpio_write(self.h, self.ena_pin, 1 if self.ena_active_high else 0)
        time.sleep(self.ena_settle_s)

    # disable stepper (ena pin required)
    def disable(self):
        if self.ena_pin is None:
            return
        lgpio.gpio_write(self.h, self.ena_pin, 0 if self.ena_active_high else 1)

    # set spin direction of stepper
    def set_direction(self, forward):
        level = 1 if (forward != self.invert_dir) else 0
        lgpio.gpio_write(self.h, self.dir_pin, level)
        time.sleep(self.dir_setup_s)

    # ramp as a list of (speed, cycles) segments
    # the PIO takes a period plus a step count per block, not one entry per step,
    # so the ramp is approximated with n segments of constant speed
    def ramp_segments(self, v_from, v_to):
        v_from = max(v_from, self.start_speed)
        v_to   = max(v_to, self.start_speed)

        total = int(abs(v_to ** 2 - v_from ** 2) / (2. * self.accel))
        if total <= 0:
            return []

        n    = min(self.n_ramp_segments, total)
        per  = total // n
        done = 0

        segments = []
        for i in range(n):
            cycles = per if i < n - 1 else total - done
            mid    = done + cycles / 2.0   # speed taken at the middle of the segment

            if v_from < v_to:
                v = min(math.sqrt(v_from ** 2 + 2.0 * self.accel * mid), v_to)
            else:
                v = max(math.sqrt(max(v_from ** 2 - 2.0 * self.accel * mid, 0.0)), v_to)

            segments.append((v, cycles))
            done += cycles

        return segments

    # seconds a list of segments takes to play
    @staticmethod
    def duration(segments):
        return sum(cycles / v for v, cycles in segments)

    # bank the steps of every block the PIO has played since the last look, caller holds the lock
    def _reap(self):
        for _ in range(stepgen.done(self._channel)):
            self._accum += self._pending.popleft()

    # number of blocks the PIO has not played yet
    def _pending_blocks(self):
        with self._lock:
            self._reap()
            return len(self._pending)

    # hand one block to the PIO, False if its FIFO is full
    def _put(self, v, cycles):
        with self._lock:
            self._reap()
            if len(self._pending) >= stepgen.FIFO_DEPTH:
                return False
            if not stepgen.put(self._channel, int(round(1e6 / v)), cycles):
                raise ValueError(f"{cycles} steps at {v:.0f} microsteps/s do not fit in a PIO block")
            self._pending.append(cycles if self._forward else -cycles)
            return True

    # queue one block of pulses, blocks until there is room in the queue
    def _queue(self, v, cycles):
        while not self._put(v, cycles):
            time.sleep(0.001)

    # blocks until every queued pulse has been sent
    def _wait_idle(self):
        while self._pending_blocks():
            time.sleep(0.001)

    # queue a whole ramp, segments play back to back with no gap
    def _emit(self, segments, abortable=False):
        for v, cycles in segments:
            if abortable and self.abort.is_set():
                return False
            self._queue(v, cycles)
            self._speed = v
        return True

    # let the pulses run out, then hand the pins back
    def close(self):
        self._wait_idle()
        stepgen.close(self._channel)
        self.disable()
        lgpio.gpiochip_close(self.h)
