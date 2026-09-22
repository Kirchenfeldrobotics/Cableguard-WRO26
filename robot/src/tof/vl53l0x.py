# Driver for the VL53L0X time-of-flight sensor on the TOF200C board, over I2C.
#
# The register sequences are ST's VL53L0X API (BSD-3-Clause) as condensed by Pololu's
# vl53l0x-arduino library (MIT), checked against Adafruit's CircuitPython port (MIT).

import time

from smbus2 import SMBus

# address the sensor answers on after power-up
ADDRESS = 0x29

# registers, named as in ST's API
SYSRANGE_START                              = 0x00
SYSTEM_SEQUENCE_CONFIG                      = 0x01
SYSTEM_INTERRUPT_CONFIG_GPIO                = 0x0A
SYSTEM_INTERRUPT_CLEAR                      = 0x0B
RESULT_INTERRUPT_STATUS                     = 0x13
RESULT_RANGE_STATUS                         = 0x14
FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT = 0x44
MSRC_CONFIG_TIMEOUT_MACROP                  = 0x46
DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD         = 0x4E
DYNAMIC_SPAD_REF_EN_START_OFFSET            = 0x4F
PRE_RANGE_CONFIG_VCSEL_PERIOD               = 0x50
PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI          = 0x51
MSRC_CONFIG_CONTROL                         = 0x60
FINAL_RANGE_CONFIG_VCSEL_PERIOD             = 0x70
FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI        = 0x71
GPIO_HV_MUX_ACTIVE_HIGH                     = 0x84
GLOBAL_CONFIG_SPAD_ENABLES_REF_0            = 0xB0
GLOBAL_CONFIG_REF_EN_START_SELECT           = 0xB6
SOFT_RESET_GO2_SOFT_RESET_N                 = 0xBF
IDENTIFICATION_MODEL_ID                     = 0xC0

# what reads back from 0xC0, 0xC1 and 0xC2 on a VL53L0X
MODEL_IDS = (0xEE, 0xAA, 0x10)

# ST's default tuning settings (VL53L0X_DefaultTuningSettings), 0xFF switches register pages
TUNING = (
    (0xFF, 0x01), (0x00, 0x00), (0xFF, 0x00), (0x09, 0x00), (0x10, 0x00), (0x11, 0x00),
    (0x24, 0x01), (0x25, 0xFF), (0x75, 0x00), (0xFF, 0x01), (0x4E, 0x2C), (0x48, 0x00),
    (0x30, 0x20), (0xFF, 0x00), (0x30, 0x09), (0x54, 0x00), (0x31, 0x04), (0x32, 0x03),
    (0x40, 0x83), (0x46, 0x25), (0x60, 0x00), (0x27, 0x00), (0x50, 0x06), (0x51, 0x00),
    (0x52, 0x96), (0x56, 0x08), (0x57, 0x30), (0x61, 0x00), (0x62, 0x00), (0x64, 0x00),
    (0x65, 0x00), (0x66, 0xA0), (0xFF, 0x01), (0x22, 0x32), (0x47, 0x14), (0x49, 0xFF),
    (0x4A, 0x00), (0xFF, 0x00), (0x7A, 0x0A), (0x7B, 0x00), (0x78, 0x21), (0xFF, 0x01),
    (0x23, 0x34), (0x42, 0x00), (0x44, 0xFF), (0x45, 0x26), (0x46, 0x05), (0x40, 0x40),
    (0x0E, 0x06), (0x20, 0x1A), (0x43, 0x40), (0xFF, 0x00), (0x34, 0x03), (0x35, 0x44),
    (0xFF, 0x01), (0x31, 0x04), (0x4B, 0x09), (0x4C, 0x05), (0x4D, 0x04), (0xFF, 0x00),
    (0x44, 0x00), (0x45, 0x20), (0x47, 0x08), (0x48, 0x28), (0x67, 0x00), (0x70, 0x04),
    (0x71, 0x01), (0x72, 0xFE), (0x76, 0x00), (0x77, 0x00), (0xFF, 0x01), (0x0D, 0x01),
    (0xFF, 0x00), (0x80, 0x01), (0x01, 0xF8), (0xFF, 0x01), (0x8E, 0x01), (0x00, 0x01),
    (0xFF, 0x00), (0x80, 0x00),
)

# the range status of a measurement the sensor completed, everything else found no target
RANGE_COMPLETE = 11

# longer than any step of a measurement takes, past this the sensor counts as gone
IO_TIMEOUT_S = 0.5


# timeouts are stored as (LSB * 2^MSB) + 1 macro periods
def _decode_timeout(value):
    return (value & 0xFF) * (1 << (value >> 8)) + 1


def _encode_timeout(mclks):
    if mclks <= 0:
        return 0
    lsb, msb = mclks - 1, 0
    while lsb > 0xFF:
        lsb >>= 1
        msb += 1
    return msb << 8 | lsb


def _macro_period_ns(vcsel_pclks):
    return (2304 * vcsel_pclks * 1655 + 500) // 1000


def _mclks_to_us(mclks, vcsel_pclks):
    ns = _macro_period_ns(vcsel_pclks)
    return (mclks * ns + ns // 2) // 1000


def _us_to_mclks(us, vcsel_pclks):
    ns = _macro_period_ns(vcsel_pclks)
    return (us * 1000 + ns // 2) // ns


class VL53L0X:
    # raises OSError when nothing answers on the bus, RuntimeError when something else does
    def __init__(self, bus=1, address=ADDRESS):
        self._bus = SMBus(bus)
        self._address = address
        try:
            self.reset()
        except Exception:
            self._bus.close()
            raise

    def _read(self, reg):
        return self._bus.read_byte_data(self._address, reg)

    def _read16(self, reg):
        hi, lo = self._bus.read_i2c_block_data(self._address, reg, 2)
        return hi << 8 | lo

    def _write(self, reg, value):
        self._bus.write_byte_data(self._address, reg, value)

    def _write16(self, reg, value):
        self._bus.write_i2c_block_data(self._address, reg, [value >> 8, value & 0xFF])

    def _writes(self, pairs):
        for reg, value in pairs:
            self._write(reg, value)

    def _wait(self, ready, what):
        deadline = time.monotonic() + IO_TIMEOUT_S
        while not ready():
            if time.monotonic() > deadline:
                raise TimeoutError(f"VL53L0X did not finish {what}")

    # From whatever state the sensor is in to ready for single measurements. Called again after
    # the sensor dropped out, one that lost power has forgotten its setup
    def reset(self):
        ids = tuple(self._read(IDENTIFICATION_MODEL_ID + i) for i in range(3))
        if ids != MODEL_IDS:
            raise RuntimeError(f"no VL53L0X at 0x{self._address:02x}, ids read {ids}")

        # ST's soft reset: the model id reads 0 while the sensor is held in reset
        self._write(SOFT_RESET_GO2_SOFT_RESET_N, 0x00)
        self._wait(lambda: self._read(IDENTIFICATION_MODEL_ID) == 0x00, "entering reset")
        self._write(SOFT_RESET_GO2_SOFT_RESET_N, 0x01)
        self._wait(lambda: self._read(IDENTIFICATION_MODEL_ID) != 0x00, "booting")

        # I2C standard mode, then read the stop variable every measurement has to write back
        self._writes(((0x88, 0x00), (0x80, 0x01), (0xFF, 0x01), (0x00, 0x00)))
        self._stop_variable = self._read(0x91)
        self._writes(((0x00, 0x01), (0xFF, 0x00), (0x80, 0x00)))

        # no signal rate limit on the MSRC and pre-range steps, 0.25 MCPS on the final range
        self._write(MSRC_CONFIG_CONTROL, self._read(MSRC_CONFIG_CONTROL) | 0x12)
        self._write16(FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT, int(0.25 * (1 << 7)))
        self._write(SYSTEM_SEQUENCE_CONFIG, 0xFF)

        self._setup_reference_spads()
        self._writes(TUNING)

        # the new-sample interrupt, active low, which is how a finished measurement shows
        self._write(SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04)
        self._write(GPIO_HV_MUX_ACTIVE_HIGH, self._read(GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10)
        self._write(SYSTEM_INTERRUPT_CLEAR, 0x01)

        # Dropping the MSRC and TCC steps frees part of the timing budget. The final range
        # gets it, so a measurement keeps its length (about 33 ms) and gains accuracy
        budget_us = self._timing_budget_us()
        self._write(SYSTEM_SEQUENCE_CONFIG, 0xE8)
        self._set_timing_budget_us(budget_us)

        self._write(SYSTEM_SEQUENCE_CONFIG, 0x01)
        self._calibrate(0x40)                        # VHV
        self._write(SYSTEM_SEQUENCE_CONFIG, 0x02)
        self._calibrate(0x00)                        # phase
        self._write(SYSTEM_SEQUENCE_CONFIG, 0xE8)

    # enables as many reference SPADs as the factory calibration in NVM asks for
    def _setup_reference_spads(self):
        self._writes(((0x80, 0x01), (0xFF, 0x01), (0x00, 0x00), (0xFF, 0x06)))
        self._write(0x83, self._read(0x83) | 0x04)
        self._writes(((0xFF, 0x07), (0x81, 0x01), (0x80, 0x01), (0x94, 0x6B), (0x83, 0x00)))
        self._wait(lambda: self._read(0x83) != 0x00, "reading the SPAD calibration")
        self._write(0x83, 0x01)
        info = self._read(0x92)
        self._writes(((0x81, 0x00), (0xFF, 0x06)))
        self._write(0x83, self._read(0x83) & ~0x04)
        self._writes(((0xFF, 0x01), (0x00, 0x01), (0xFF, 0x00), (0x80, 0x00)))

        count = info & 0x7F
        first = 12 if info & 0x80 else 0             # aperture SPADs start at 12
        spads = self._bus.read_i2c_block_data(self._address, GLOBAL_CONFIG_SPAD_ENABLES_REF_0, 6)

        self._writes((
            (0xFF, 0x01),
            (DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00),
            (DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2C),
            (0xFF, 0x00),
            (GLOBAL_CONFIG_REF_EN_START_SELECT, 0xB4),
        ))

        enabled = 0
        for i in range(48):
            if i < first or enabled == count:
                spads[i // 8] &= ~(1 << (i % 8))
            elif spads[i // 8] >> (i % 8) & 1:
                enabled += 1
        self._bus.write_i2c_block_data(self._address, GLOBAL_CONFIG_SPAD_ENABLES_REF_0, spads)

    def _calibrate(self, vhv_init):
        self._write(SYSRANGE_START, 0x01 | vhv_init)
        self._wait(lambda: self._read(RESULT_INTERRUPT_STATUS) & 0x07, "calibrating")
        self._write(SYSTEM_INTERRUPT_CLEAR, 0x01)
        self._write(SYSRANGE_START, 0x00)

    def _vcsel_pclks(self, reg):
        return ((self._read(reg) + 1) & 0xFF) << 1

    # which of TCC, DSS, MSRC, pre-range and final range the sequence runs
    def _sequence_steps(self):
        config = self._read(SYSTEM_SEQUENCE_CONFIG)
        return config >> 4 & 1, config >> 3 & 1, config >> 2 & 1, config >> 6 & 1, config >> 7 & 1

    def _step_timeouts(self, pre_range):
        pre_pclks = self._vcsel_pclks(PRE_RANGE_CONFIG_VCSEL_PERIOD)
        msrc_us = _mclks_to_us((self._read(MSRC_CONFIG_TIMEOUT_MACROP) + 1) & 0xFF, pre_pclks)
        pre_mclks = _decode_timeout(self._read16(PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI))
        pre_us = _mclks_to_us(pre_mclks, pre_pclks)

        final_pclks = self._vcsel_pclks(FINAL_RANGE_CONFIG_VCSEL_PERIOD)
        final_mclks = _decode_timeout(self._read16(FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI))
        if pre_range:
            final_mclks -= pre_mclks                 # the register counts the pre-range in
        final_us = _mclks_to_us(final_mclks, final_pclks)
        return msrc_us, pre_us, final_us, final_pclks, pre_mclks

    # what the enabled steps take together, overheads from ST's API
    def _timing_budget_us(self):
        tcc, dss, msrc, pre_range, final_range = self._sequence_steps()
        msrc_us, pre_us, final_us, _, _ = self._step_timeouts(pre_range)
        budget = 1910 + 960
        if tcc:
            budget += msrc_us + 590
        if dss:
            budget += 2 * (msrc_us + 690)
        elif msrc:
            budget += msrc_us + 660
        if pre_range:
            budget += pre_us + 660
        if final_range:
            budget += final_us + 550
        return budget

    # gives the final range whatever the other steps leave of budget_us
    def _set_timing_budget_us(self, budget_us):
        tcc, dss, msrc, pre_range, final_range = self._sequence_steps()
        msrc_us, pre_us, _, final_pclks, pre_mclks = self._step_timeouts(pre_range)
        used = 1320 + 960
        if tcc:
            used += msrc_us + 590
        if dss:
            used += 2 * (msrc_us + 690)
        elif msrc:
            used += msrc_us + 660
        if pre_range:
            used += pre_us + 660
        if final_range:
            used += 550
            final_mclks = _us_to_mclks(budget_us - used, final_pclks)
            if pre_range:
                final_mclks += pre_mclks
            self._write16(FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI, _encode_timeout(final_mclks))

    # One measurement: metres to the nearest object, None when the sensor found no target.
    # Blocks for about 33 ms
    def read_m(self):
        self._writes((
            (0x80, 0x01), (0xFF, 0x01), (0x00, 0x00), (0x91, self._stop_variable),
            (0x00, 0x01), (0xFF, 0x00), (0x80, 0x00), (SYSRANGE_START, 0x01),
        ))
        self._wait(lambda: not self._read(SYSRANGE_START) & 0x01, "starting the measurement")
        self._wait(lambda: self._read(RESULT_INTERRUPT_STATUS) & 0x07, "measuring")

        result = self._bus.read_i2c_block_data(self._address, RESULT_RANGE_STATUS, 12)
        self._write(SYSTEM_INTERRUPT_CLEAR, 0x01)

        if (result[0] & 0x78) >> 3 != RANGE_COMPLETE:
            return None
        return (result[10] << 8 | result[11]) / 1000.0

    def close(self):
        self._bus.close()
