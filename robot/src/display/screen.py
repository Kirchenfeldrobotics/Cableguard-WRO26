import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ssd1306 import SSD1306

log = logging.getLogger(__name__)

# the panel is monochrome: a pixel is lit or it is not
DARK = 0
LIT  = 1

# Pillow's built-in scalable font, no font file to install. Ten pixels is about as small as
# this panel stays readable at arm's length
SMALL = ImageFont.load_default(10)
BIG   = ImageFont.load_default(17)

# the Pi 5 throttles at 85 °C
WARM_C = 70.0

# Rows, top down: the filled header, then network, outbox, position and finally the state
# line. The position gets the big font, it is the number read from a distance
BAR_H    = 13
ROW_IP   = 14
ROW_LINK = 25
ROW_POS  = 34
ROW_FOOT = 53

MARGIN = 1


# what the robot knows about itself, taken fresh for every frame
@dataclass(frozen=True)
class Status:
    online: bool                    # control link to the backend is up
    backlog_bytes: int              # outbox not delivered yet
    speed_mps: float                # signed, forward is positive
    metres: float                   # from the run origin
    cycle_ms: float | None          # last detector cycle


# CPU temperature in °C, None where the kernel reports none
def cpu_temp():
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000.0
    except (OSError, ValueError):
        return None


# address on the interface with the default route. Connecting a UDP socket sends nothing,
# it only picks the route
def local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
        except OSError:
            return None


def _size(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    return f"{n / 1000:.0f} kB"


# there is no colour to warn with, so a hot CPU is marked with an exclamation mark
def _system(temp, load):
    reading = "--C" if temp is None else f"{temp:.0f}C{'!' if temp >= WARM_C else ''}"
    return f"{reading} {load:.1f}"


# One frame for the 128x64 panel: link and clock, network, outbox and detector, position,
# then speed and system. Drawn white on black, the header the other way round
def render(s: Status, ip, temp, load, width, height):
    img = Image.new("1", (width, height), DARK)
    d = ImageDraw.Draw(img)
    left, right = MARGIN, width - MARGIN

    # a filled bar reads as link state from further away than any text can
    d.rectangle((0, 0, width, BAR_H), fill=LIT)
    d.text((left + 1, 0), "ONLINE" if s.online else "OFFLINE", font=SMALL, fill=DARK)
    # the clock ticks, which is how a frozen screen gives itself away
    d.text((right, 0), time.strftime("%H:%M:%S"), font=SMALL, fill=DARK, anchor="ra")

    d.text((left, ROW_IP), ip or "no network", font=SMALL, fill=LIT)

    d.text((left, ROW_LINK), f"out {_size(s.backlog_bytes)}" if s.backlog_bytes else "out empty",
           font=SMALL, fill=LIT)
    d.text((right, ROW_LINK), "cyc --" if s.cycle_ms is None else f"cyc {s.cycle_ms:.0f}ms",
           font=SMALL, fill=LIT, anchor="ra")

    d.text((left, ROW_POS), f"{s.metres:.2f} m", font=BIG, fill=LIT)
    if s.speed_mps > 0.0:
        state = "FWD"
    elif s.speed_mps < 0.0:
        state = "REV"
    else:
        state = "STOP"
    d.text((right, ROW_POS + 4), state, font=SMALL, fill=LIT, anchor="ra")

    d.text((left, ROW_FOOT), f"{abs(s.speed_mps):.3f} m/s", font=SMALL, fill=LIT)
    d.text((right, ROW_FOOT), _system(temp, load), font=SMALL, fill=LIT, anchor="ra")
    return img


class StatusScreen:
    # The robot runs without its display, a missing or unwired one costs a warning. I2C has
    # to be enabled (dtparam=i2c_arm=on) for the panel to answer
    def __init__(self, bus, address, flip=False):
        self._lock = threading.Lock()
        self._failing = False
        try:
            self._panel = SSD1306(bus, address, flip=flip)
        except Exception as exc:
            log.warning("no status display: %s", exc)
            self._panel = None

    # Put a frame on the panel. A display knocked off its header would otherwise log a
    # stack trace every second, so it is reported once and then simply retried
    def _draw(self, img):
        with self._lock:
            if self._panel is None:
                return
            try:
                self._panel.show(img)
            except OSError as exc:
                if not self._failing:
                    log.warning("status display not answering: %s", exc)
                self._failing = True
            else:
                if self._failing:
                    log.info("status display answers again")
                self._failing = False

    def show(self, status: Status):
        panel = self._panel
        if panel is None:
            return
        self._draw(render(status, local_ip(), cpu_temp(), os.getloadavg()[0],
                          panel.width, panel.height))

    # a single line in the middle, for while there is no status yet
    def message(self, text):
        panel = self._panel
        if panel is None:
            return
        img = Image.new("1", (panel.width, panel.height), DARK)
        ImageDraw.Draw(img).text((panel.width // 2, panel.height // 2), text, font=BIG, fill=LIT,
                                 anchor="mm")
        self._draw(img)

    def close(self):
        with self._lock:
            if self._panel is None:
                return
            try:
                self._panel.close()
            except OSError as exc:
                log.warning("status display did not switch off: %s", exc)
            self._panel = None
