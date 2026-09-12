import pigpio, math, threading, time

class Stepper(): 
    def __init__(self, 
                 pul_pin, 
                 dir_pin, 
                 ena_pin=None, 
                 puls_us=20, 
                 dir_setup_s=0.001, 
                 ena_settle_s=0.2, 
                 invert_dir=False, 
                 ena_active_high=False, 
                 steps_per_rev=200, 
                 microsteps=8, 
                 cruise_wave_s=0.02, 
                 start_speed=200.0, 
                 max_speed=2000.0, 
                 accel=400.0):

        # specfiy pin numbers
        self.pul_pin = pul_pin
        self.dir_pin = dir_pin
        self.ena_pin = ena_pin 

        # sepcify driver timing
        self.puls_us      = puls_us       # how long the pulse is high
        self.dir_setup_s  = dir_setup_s   # break after direction high
        self.ena_settle_s = ena_settle_s  # break after enabled high

        # specify driver flags 
        self.invert_dir      = invert_dir        # stepper direction inverted 
        self.ena_active_high = ena_active_high   # stepper active on enabled high

        # specify steps
        self.full_steps_per_rev = steps_per_rev  # full steps per revolution
        self.microsteps         = microsteps     # microsteps per full step

        # DMA limits 
        self.MAX_PULSES_PER_WAVE = 4000
        self.MAX_MICROS_PER_WAVE = 1500000

        # cruise wave length  
        self.cruise_wave_s = cruise_wave_s  # length of a cruise wave => latency of the cruise

        # speed 
        self.start_speed = start_speed
        self.max_speed   = max_speed
        self.accel       = accel

        # setup pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected: 
            raise RuntimeError("pigpio not connected")

        self.pi.set_mode(pul_pin, pigpio.OUTPUT)
        self.pi.write(pul_pin, 0)
        self.pi.set_mode(dir_pin, pigpio.OUTPUT)
        self.pi.write(dir_pin, 0)

        if ena_pin is not None: 
            self.pi.set_mode(ena_pin, pigpio.OUTPUT)
            self.disable()

        # runtime vars 
        self._speed      = 0.0
        self._forward    = True
        self._active_wid = None
        self.abort       = threading.Event()

        # position
        self._counter = self.pi.callback(self.pul_pin, pigpio.RISING_EDGE)
        self._accum   = 0 

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
        n = self._counter.tally()
        return self._accum + (n if self._forward else -n)

    # number of steps since last reset
    @property
    def full_steps_done(self): 
        return self.microsteps_done / self.microsteps

    # number of revolutions sicne last reset 
    def revolutions_done(self): 
        return self.full_steps_done / self.steps_per_rev

    # reset number of microsteps done 
    def reset_steps_done(self): 
        self._counter.reset_tally()
        self._accum = 0

    # enable stepper (ena pin required)
    def enable(self): 
        if self.ena_pin is None: 
            return 
        self.pi.write(self.ena_pin, 1 if self.ena_active_high else 0)
        time.sleep(self.ena_settle_s)

    # disable stepper (ena pin required)
    def disable(self): 
        if self.ena_pin is None: 
            return 
        self.pi.write(self.ena_pin, 0 if self.ena_active_high else 1)

    # set spin direction of stepper 
    def set_direction(self, forward): 
        self._fold_counter()    
        level = 1 if (forward != self.invert_dir) else 0 
        self.pi.write(self.dir_pin, level)
        time.sleep(self.dir_setup_s)

    # cruise wave values
    def cruise_delays(self, v): 
        n_steps = max(1, int(self.cruise_wave_s * v))
        n_steps = min(n_steps, self.MAX_PULSES_PER_WAVE // 2) 
        return [1.0 / v] * n_steps

    # rampe wave values
    def ramp_delays(self, v_from, v_to): 
        v_from = max(v_from, self.start_speed)
        v_to   = max(v_to, self.start_speed)

        n_steps = int(abs(v_to ** 2 - v_from ** 2) / (2. * self.accel)) 
        if n_steps <= 0: 
            return []

        delays = []
        for i in range(n_steps): 
            if v_from < v_to: 
                v = min(math.sqrt(v_from ** 2 + 2.0 * self.accel * i), v_to)
            else:
                v = max(math.sqrt(max(v_from ** 2 - 2.0 * self.accel * i, 0.0)), v_to)

            delays.append(1.0 / v)

        return delays 

    # split delay list into groups that fit into a wave
    def chunk_delays(self, delays): 
        chunk = []
        total_us = 0.0

        for d in delays: 
            us = d * 1e6
            if len(chunk) * 2 + 2 > self.MAX_PULSES_PER_WAVE or total_us + us > self.MAX_MICROS_PER_WAVE: 
                yield chunk 
                chunk, total_us = [], 0.0
            chunk.append(d)
            total_us += us 

        if chunk: 
            yield chunk

    # turn delays (chunked) into a wave
    def _build_wave(self, delays): 
        mask   = 1 << self.pul_pin 
        pulses = []

        for d in delays: 
            low_us = int(round(d * 1e6)) - self.puls_us
            if low_us < self.puls_us: 
                low_us = self.puls_us

            pulses.append(pigpio.pulse(mask, 0, self.puls_us))
            pulses.append(pigpio.pulse(0, mask, low_us))

        self.pi.wave_add_generic(pulses)
        return self.pi.wave_create()

    # blocks until wave is no longer being transmitted 
    def _wait_past(self, wid): 
        while self.pi.wave_tx_at() == wid: 
            time.sleep(0.0005) 

    # continiously transmits waves: 
        # if a wave is active: finish it and stop it afterwards
        # transmit chunks without gaps
        # if cruise != None: repeate cruise wave, else finish last chunk if there was one 
    def _stream(self, chunks, cruise=None, abortable=False):
        prev       = self._active_wid
        queued_any = False

        # transmit chunks
        for chunk in chunks:
            if abortable and self.abort.is_set():
                return False
            wid = self._build_wave(chunk)
            self.pi.wave_send_using_mode(wid, pigpio.WAVE_MODE_ONE_SHOT_SYNC)
            queued_any = True 
            if prev is not None: 
                self._wait_past(prev)
                self.pi.wave_delete(prev)
            prev = wid
            self._active_wid = wid
            self._speed = 1.0 / chunk[-1]

        if abortable and self.abort.is_set():
            return False

        # transmit repeated cruise wave
        if cruise is not None: 
            wid = self._build_wave(cruise)
            self.pi.wave_send_using_mode(wid, pigpio.WAVE_MODE_REPEAT_SYNC)
            if prev is not None: 
                self._wait_past(prev)
                self.pi.wave_delete(prev)
            self._active_wid = wid 

        # finish last chunk
        elif queued_any: 
            while self.pi.wave_tx_busy(): 
                time.sleep(0.001)
            if prev is not None: 
                self.pi.wave_delete(prev)
            self._active_wid = None
            self._speed = 0.0

        return True

    # ramp to speed and cruise there (if cruise flag is set)
    def ramp_to(self, speed, cruise=True): 
        target = min(abs(speed), self.max_speed)
        forward = speed >= 0

        if self.moving and forward != self._forward: 
            self.stop()

        if target < self.start_speed: 
            self.stop()
            return 

        if not self.moving: 
            self.set_direction(forward)
            self._forward = forward 

        delays = self.ramp_delays(self._speed, target)
        completed = self._stream(self.chunk_delays(delays), cruise=self.cruise_delays(target) if cruise else None, abortable=True)
        if completed and cruise:
            self._speed = target

    # ramp stepper to 0.0 
    def stop(self): 
        if not self.moving: 
            return 

        delays = self.ramp_delays(self._speed, 0.0)
        if delays: 
            self._stream(self.chunk_delays(delays))

        self.pi.wave_tx_stop()
        self.pi.wave_clear()
        self._active_wid = None 
        self._speed = 0.0

    def close(self): 
        try: 
            self.stop()
        finally: 
            self._counter.cancel()
            self.pi.wave_tx_stop()
            self.pi.wave_clear()
            self.pi.write(self.pul_pin, 0)
            self.disable()
            self.pi.stop()

    # keep script running for n seconds
    def hold_s(self, seconds): 
        if seconds <= 0: 
            return 

        time.sleep(seconds)

    # bank step counter based on direction
    def _fold_counter(self): 
        n = self._counter.tally()
        self._counter.reset_tally()
        self._accum += n if self._forward else -n