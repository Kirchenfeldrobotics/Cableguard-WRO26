import ctypes, lgpio, math, os, threading, time
from collections import deque

# How far the rope moves per microstep. Placeholder until the drive is measured:
# 1600 microsteps per turn on a 50 mm wheel. Every metre in the system comes from here
MICROSTEPS_PER_METRE = 10186.0

# The step pulses come from a PIO state machine on the RP1 (stepgen.c), not from Linux,
# which cannot time them evenly. Build the library on the Pi before the first run
_stepgen = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libstepgen.so"))
_stepgen.stepgen_open.argtypes = [ctypes.c_uint]
_stepgen.stepgen_put.argtypes  = [ctypes.c_uint, ctypes.c_uint]
_stepgen.stepgen_close.restype = None

# depth of the RP1 PIO FIFOs. A block counts as pending until the PIO reports it played,
# so with at most this many pending neither the TX nor the RX FIFO can overflow
PIO_FIFO_DEPTH = 8

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
                 steps_per_rev=200,
                 microsteps=8,
                 microsteps_per_metre=MICROSTEPS_PER_METRE,
                 cruise_block_s=0.02,
                 cruise_blocks_ahead=3,
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
        self.full_steps_per_rev = steps_per_rev  # full steps per revolution
        self.microsteps         = microsteps     # microsteps per full step

        # drive geometry, the only place microsteps and metres meet
        self.microsteps_per_metre = microsteps_per_metre

        # One cruise block = one word to the PIO. Enough blocks stay queued to ride out a
        # busy CPU, few enough that a stop is not stuck behind them for long
        self.cruise_block_s      = cruise_block_s
        self.cruise_blocks_ahead = cruise_blocks_ahead

        # how many constant-speed segments a ramp is approximated with
        self.n_ramp_segments = ramp_segments

        # speed
        self.start_speed = start_speed
        self.max_speed   = max_speed
        self.accel       = accel

        # the PIO takes the step pin over, lgpio must not claim it afterwards or the pin
        # falls back to plain GPIO
        err = _stepgen.stepgen_open(pul_pin)
        if err < 0:
            raise OSError(-err, f"cannot drive the step pin from /dev/pio0: {os.strerror(-err)}")

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
        self.abort    = threading.Event()

        # position: a block's steps are banked once the PIO reports it played, so the count
        # never runs ahead of the motor
        self._accum   = 0
        self._pending = deque()   # signed steps of every block the PIO has not played yet
        self._lock    = threading.Lock()

        # cruise is fed in finite blocks so the steps stay countable
        self._cruise_speed = 0.0
        self._closing      = threading.Event()
        self._feeder       = threading.Thread(target=self._feeder_loop, daemon=True)
        self._feeder.start()

    def __enter__(self):
        self.enable()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # total amount of steps per revolution
    @property
    def steps_per_rev(self):
        return self.full_steps_per_rev * self.microsteps

    # returns moving state
    @property
    def moving(self):
        return self._speed > 0.0

    # return current speed
    @property
    def speed(self):
        return self._speed if self._forward else self._speed * -1

    # metres for a microstep count. Speeds convert with the same factor, microsteps per
    # second over microsteps per metre is metres per second
    def to_metres(self, microsteps):
        return microsteps / self.microsteps_per_metre

    # microsteps for a distance in metres, or microsteps per second for a speed in m/s
    def to_microsteps(self, metres):
        return metres * self.microsteps_per_metre

    # number of microsteps since last reset
    @property
    def microsteps_done(self):
        return self._accum

    # distance since last reset, signed with the direction driven
    @property
    def metres_done(self):
        return self.to_metres(self._accum)

    # current speed in metres per second, signed like speed
    @property
    def speed_mps(self):
        return self.to_metres(self.speed)

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

    # bank the steps of every block the PIO has played since the last look, caller holds the lock
    def _reap(self):
        for _ in range(_stepgen.stepgen_done()):
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
            if len(self._pending) >= PIO_FIFO_DEPTH:
                return False
            if _stepgen.stepgen_put(int(round(1e6 / v)), cycles) < 0:
                raise ValueError(f"{cycles} steps at {v:.0f} microsteps/s do not fit in a PIO block")
            self._pending.append(cycles if self._forward else -cycles)
            return True

    # queue one block of pulses, blocks until there is room in the queue
    def _queue(self, v, cycles):
        while not self._put(v, cycles):
            time.sleep(0.001)

    # tops up the queue while cruising, so cruise steps stay counted
    def _feeder_loop(self):
        while not self._closing.is_set():
            v = self._cruise_speed
            if v > 0.0 and self._pending_blocks() < self.cruise_blocks_ahead:
                self._put(v, max(1, int(self.cruise_block_s * v)))
            time.sleep(self.cruise_block_s / 4.0)

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
            self._wait_idle()
            _stepgen.stepgen_close()
            self.disable()
            lgpio.gpiochip_close(self.h)

    # keep script running for n seconds
    def hold_s(self, seconds):
        if seconds <= 0:
            return

        time.sleep(seconds)
