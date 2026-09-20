import lgpio, math, threading, time

class Stepper():
    def __init__(self,
                 pul_pin,
                 dir_pin,
                 ena_pin=None,
                 chip=4,
                 puls_us=20,
                 dir_setup_s=0.001,
                 ena_settle_s=0.2,
                 invert_dir=False,
                 ena_active_high=False,
                 steps_per_rev=200,
                 microsteps=8,
                 cruise_block_s=0.02,
                 ramp_segments=40,
                 start_speed=200.0,
                 max_speed=2000.0,
                 accel=400.0):

        # specify pin numbers
        self.pul_pin = pul_pin
        self.dir_pin = dir_pin
        self.ena_pin = ena_pin

        # specify driver timing
        self.puls_us      = puls_us       # how long the pulse is high
        self.dir_setup_s  = dir_setup_s   # break after direction high
        self.ena_settle_s = ena_settle_s  # break after enabled high

        # specify driver flags
        self.invert_dir      = invert_dir        # stepper direction inverted
        self.ena_active_high = ena_active_high   # stepper active on enabled high

        # specify steps
        self.full_steps_per_rev = steps_per_rev  # full steps per revolution
        self.microsteps         = microsteps     # microsteps per full step

        # one cruise block = one tx_pulse call => stop latency is ~2 blocks
        self.cruise_block_s = cruise_block_s

        # how many constant-speed segments a ramp is approximated with
        self.n_ramp_segments = ramp_segments

        # speed
        self.start_speed = start_speed
        self.max_speed   = max_speed
        self.accel       = accel

        # setup lgpio (no daemon, unlike pigpio)
        # chip 4 is the RP1 on the pi 5, chip 0 on older boards and newer kernels
        self.h = lgpio.gpiochip_open(chip)

        lgpio.gpio_claim_output(self.h, pul_pin, 0)
        lgpio.gpio_claim_output(self.h, dir_pin, 0)

        if ena_pin is not None:
            lgpio.gpio_claim_output(self.h, ena_pin, 0)
            self.disable()

        # runtime vars
        self._speed   = 0.0
        self._forward = True
        self.abort    = threading.Event()

        # position: every pulse is commanded, so the count is exact
        self._accum = 0

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

    # number of microsteps since last reset
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

    # high and low time in whole us for a given speed
    def pulse_times(self, v):
        period_us = int(round(1e6 / v))
        off_us    = period_us - self.puls_us
        if off_us < self.puls_us:
            off_us = self.puls_us
        return self.puls_us, off_us

    # ramp as a list of (speed, cycles) segments
    # lgpio wants a period plus a cycle count, not one entry per step,
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

    # bank cycles into the position counter, signed by direction
    def _count(self, cycles):
        self._accum += cycles if self._forward else -cycles

    # queue one block of pulses, blocks until there is room in the queue
    def _queue(self, v, cycles):
        on, off = self.pulse_times(v)
        while lgpio.tx_room(self.h, self.pul_pin, lgpio.TX_PWM) < 1:
            time.sleep(0.001)
        lgpio.tx_pulse(self.h, self.pul_pin, on, off, pulse_cycles=cycles)
        self._count(cycles)

    # tops up the queue while cruising, so cruise steps stay counted
    # keeps only one block ahead, otherwise a stop would sit behind the backlog
    def _feeder_loop(self):
        while not self._closing.is_set():
            v = self._cruise_speed
            if v > 0.0:
                cycles = max(1, int(self.cruise_block_s * v))
                if lgpio.tx_room(self.h, self.pul_pin, lgpio.TX_PWM) > 1:
                    on, off = self.pulse_times(v)
                    lgpio.tx_pulse(self.h, self.pul_pin, on, off, pulse_cycles=cycles)
                    self._count(cycles)
            time.sleep(self.cruise_block_s / 4.0)

    # blocks until every queued pulse has been sent
    def _wait_idle(self):
        while lgpio.tx_busy(self.h, self.pul_pin, lgpio.TX_PWM):
            time.sleep(0.001)

    # kill output, queued blocks still drain first (~2 blocks)
    def _silence(self):
        lgpio.tx_pulse(self.h, self.pul_pin, 0, 0)

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

    # ramp stepper to 0.0
    def stop(self):
        if not self.moving:
            return

        self._cruise_speed = 0.0   # feeder stops adding blocks first

        segments = self.ramp_segments(self._speed, 0.0)
        if segments:
            self._emit(segments)
            self._wait_idle()

        self._silence()
        self._speed = 0.0

    def close(self):
        try:
            self.stop()
        finally:
            self._closing.set()
            self._feeder.join(timeout=1.0)
            self._silence()
            lgpio.gpio_write(self.h, self.pul_pin, 0)
            self.disable()
            lgpio.gpiochip_close(self.h)

    # keep script running for n seconds
    def hold_s(self, seconds):
        if seconds <= 0:
            return

        time.sleep(seconds)