import numpy as np
from smbus2 import SMBus, i2c_msg

# The 0.96" status display: 128x64 monochrome OLED on an SSD1306, I2C. It shares bus 1 with
# the distance sensor, which answers on another address

WIDTH  = 128
HEIGHT = 64

# 0x3C on every module seen so far, 0x3D on boards where the address pad is bridged
ADDRESS = 0x3C

# every transfer starts with a control byte saying what follows
CMD  = 0x00
DATA = 0x40

DISPLAY_OFF = 0xAE
DISPLAY_ON  = 0xAF
SET_COLUMN  = 0x21
SET_PAGE    = 0x22

# Panel setup, straight out of the SSD1306 datasheet's power-on sequence. The pairs are a
# command and its argument: clock, multiplex ratio, offset, charge pump, addressing mode,
# COM pin layout, contrast, pre-charge and VCOMH levels
SETUP = (
    0xD5, 0x80,     # display clock: no division, standard oscillator frequency
    0xA8, 0x3F,     # multiplex ratio, 64 rows
    0xD3, 0x00,     # no vertical offset
    0x40,           # start at line 0
    0x8D, 0x14,     # charge pump on, the panel makes its own 7.5 V
    0x20, 0x00,     # horizontal addressing: the frame is written as one run of bytes
    0xDA, 0x12,     # COM pins alternating, as a 128x64 panel is wired
    0x81, 0xCF,     # contrast
    0xD9, 0xF1,     # pre-charge periods
    0xDB, 0x40,     # VCOMH deselect level
    0xA4,           # show what is in RAM, not an all-on test pattern
    0xA6,           # normal, not inverted
    0x2E,           # no scrolling
)


class SSD1306:
    # The pixels are written eight rows at a time, so a frame is one byte per column per
    # eight-row page: 1024 bytes for the whole panel
    def __init__(self, bus=1, address=ADDRESS, flip=False):
        self.width   = WIDTH
        self.height  = HEIGHT
        self.address = address

        self._bus = SMBus(bus)
        try:
            self._command(DISPLAY_OFF)
            self._command(*SETUP)
            # which way round the panel is read: the second pair turns the picture over
            self._command(0xA0 if flip else 0xA1, 0xC0 if flip else 0xC8)
            self._command(DISPLAY_ON)
        except OSError:
            self._bus.close()
            raise

    def _command(self, *values):
        self._bus.i2c_rdwr(i2c_msg.write(self.address, bytes([CMD, *values])))

    # Draw a 1-bit image. Bit 0 of a byte is the top row of its page, so the rows are folded
    # into pages of eight and weighted by their position in the page
    def show(self, image):
        if image.size != (self.width, self.height):
            raise ValueError(f"image is {image.size}, the panel shows {self.width}x{self.height}")
        if image.mode != "1":
            image = image.convert("1")

        rows  = np.asarray(image, dtype=np.uint8).reshape(self.height // 8, 8, self.width)
        pages = (rows << np.arange(8, dtype=np.uint8).reshape(1, 8, 1)).sum(axis=1, dtype=np.uint8)

        self._command(SET_COLUMN, 0, self.width - 1)
        self._command(SET_PAGE, 0, self.height // 8 - 1)
        # one page per transfer, well inside what any I2C adapter carries in one go
        for page in pages:
            self._bus.i2c_rdwr(i2c_msg.write(self.address, bytes([DATA]) + page.tobytes()))

    # a dark panel is honest about the robot no longer running
    def close(self):
        try:
            self._command(DISPLAY_OFF)
        finally:
            self._bus.close()
