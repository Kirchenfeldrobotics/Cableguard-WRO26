import struct
import time

import lgpio
import numpy as np
import spidev

# the ST7789 commands this driver uses
SLPOUT  = 0x11
NORON   = 0x13
INVON   = 0x21
DISPOFF = 0x28
DISPON  = 0x29
CASET   = 0x2A
RASET   = 0x2B
RAMWR   = 0x2C
MADCTL  = 0x36
COLMOD  = 0x3A

# the 1.54" panel is 240x240, its controller has RAM for 240x320
SIZE = 240

# MADCTL and RAM offset (x, y) per rotation. Rotations that run the RAM rows backwards start
# 80 rows in, that is where the first line of the panel then sits
ROTATIONS = {
    0:   (0x00, 0, 0),
    90:  (0x60, 0, 0),
    180: (0xC0, 0, 80),
    270: (0xA0, 80, 0),
}


class ST7789:
    def __init__(self, dc_pin, rst_pin, bl_pin, rotation=90, spi_bus=0, spi_dev=0, spi_hz=32_000_000, chip=4):
        self.width = self.height = SIZE
        madctl, self._dx, self._dy = ROTATIONS[rotation]
        self.dc_pin = dc_pin
        self.bl_pin = bl_pin

        # chip 4 is the RP1 on the pi 5, as in motion/stepper.py
        self.h = lgpio.gpiochip_open(chip)
        for pin in (dc_pin, rst_pin, bl_pin):
            lgpio.gpio_claim_output(self.h, pin, 0)

        # CS is the SPI's own chip select (CE0), the kernel drives it
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_dev)
        self.spi.mode = 0
        self.spi.max_speed_hz = spi_hz

        # hardware reset, the controller takes commands 120 ms after it
        lgpio.gpio_write(self.h, rst_pin, 0)
        time.sleep(0.01)
        lgpio.gpio_write(self.h, rst_pin, 1)
        time.sleep(0.12)

        self._command(SLPOUT)
        time.sleep(0.12)                  # sleep out needs this long before the next command
        self._command(COLMOD, 0x55)       # 16 bit colour, RGB565
        self._command(MADCTL, madctl)
        self._command(INVON)              # an IPS panel shows a negative without it
        self._command(NORON)
        self._command(DISPON)
        self.backlight(True)

    def _command(self, cmd, *params):
        lgpio.gpio_write(self.h, self.dc_pin, 0)
        self.spi.writebytes2(bytes([cmd]))
        if params:
            self._data(bytes(params))

    # bytes, not a list: spidev then sends straight from the buffer and releases the GIL
    def _data(self, data):
        lgpio.gpio_write(self.h, self.dc_pin, 1)
        self.spi.writebytes2(data)

    def backlight(self, on):
        lgpio.gpio_write(self.h, self.bl_pin, 1 if on else 0)

    # draws a PIL image of the panel's size
    def show(self, image):
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint16)
        pixels = ((rgb[..., 0] >> 3) << 11) | ((rgb[..., 1] >> 2) << 5) | (rgb[..., 2] >> 3)

        self._command(CASET, *struct.pack(">HH", self._dx, self._dx + self.width - 1))
        self._command(RASET, *struct.pack(">HH", self._dy, self._dy + self.height - 1))
        self._command(RAMWR)
        self._data(pixels.astype(">u2").tobytes())

    # dark and released, a lit screen would keep showing the last status as if it were current
    def close(self):
        self._command(DISPOFF)
        self.backlight(False)
        self.spi.close()
        lgpio.gpiochip_close(self.h)
