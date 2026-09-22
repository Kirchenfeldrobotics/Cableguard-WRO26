import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .st7789 import ST7789

log = logging.getLogger(__name__)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY  = (140, 140, 140)
GREEN = (0, 190, 80)
AMBER = (255, 170, 0)
RED   = (220, 40, 40)

# Pillow's built-in scalable font, no font file to install
SMALL = ImageFont.load_default(15)
FONT  = ImageFont.load_default(18)
BIG   = ImageFont.load_default(40)

# the Pi 5 throttles at 85 °C
WARM_C = 70.0
HOT_C  = 80.0

# the 1.69" panel has rounded corners, text closer to the side than this gets cut off there
MARGIN = 12


# what the robot knows about itself, taken fresh for every frame
@dataclass(frozen=True)
class Status:
    online: bool                    # control link to the backend is up
    backlog_bytes: int              # outbox not delivered yet
    speed_mps: float                # signed, forward is positive
    metres: float                   # from the run origin
    defects: int                    # found in the current run
    last_defect: str | None         # label and confidence of the latest one
    last_defect_at: float | None    # time.monotonic() of it
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


def _age(seconds):
    if seconds < 60:
        return f"{seconds:.0f} s"
    if seconds < 3600:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.0f} h"


# One frame: link, motion, detections, system, each under a line of its own. Laid out for
# the landscape 280x240, standing upright it keeps the same rows with room left below
def render(s: Status, ip, temp, load, width, height):
    img = Image.new("RGB", (width, height), BLACK)
    d = ImageDraw.Draw(img)
    left, right = MARGIN, width - MARGIN

    # the bar turns red once the backend is out of reach, the clock shows a frozen screen
    d.rectangle((0, 0, width, 26), fill=GREEN if s.online else RED)
    d.text((left, 4), "ONLINE" if s.online else "OFFLINE", font=FONT, fill=WHITE)
    d.text((right, 5), time.strftime("%H:%M:%S"), font=SMALL, fill=WHITE, anchor="ra")
    d.text((left, 32), f"IP {ip or 'no network'}", font=SMALL, fill=WHITE)
    if s.backlog_bytes:
        d.text((left, 52), f"outbox {_size(s.backlog_bytes)} unsent", font=SMALL, fill=AMBER)
    else:
        d.text((left, 52), "outbox empty", font=SMALL, fill=GREY)

    d.line((0, 76, width, 76), fill=GREY)
    if s.speed_mps > 0.0:
        state, colour = "FORWARD", GREEN
    elif s.speed_mps < 0.0:
        state, colour = "BACKWARD", AMBER
    else:
        state, colour = "STOPPED", GREY
    d.text((left, 82), state, font=FONT, fill=colour)
    d.text((right, 82), f"{abs(s.speed_mps):.3f} m/s", font=FONT, fill=WHITE, anchor="ra")
    d.text((left, 104), f"{s.metres:.2f} m", font=BIG, fill=WHITE)

    d.line((0, 152, width, 152), fill=GREY)
    d.text((left, 158), f"defects {s.defects}", font=FONT, fill=AMBER if s.defects else WHITE)
    if s.cycle_ms is not None:
        d.text((right, 160), f"cycle {s.cycle_ms:.0f} ms", font=SMALL, fill=GREY, anchor="ra")
    if s.last_defect:
        age = _age(time.monotonic() - s.last_defect_at)
        d.text((left, 182), f"{s.last_defect}  {age} ago", font=SMALL, fill=WHITE)
    else:
        d.text((left, 182), "none found yet", font=SMALL, fill=GREY)

    d.line((0, 206, width, 206), fill=GREY)
    if temp is None:
        d.text((left, 214), "CPU --", font=FONT, fill=GREY)
    else:
        colour = RED if temp >= HOT_C else AMBER if temp >= WARM_C else WHITE
        d.text((left, 214), f"CPU {temp:.0f} °C", font=FONT, fill=colour)
    d.text((right, 214), f"load {load:.1f}", font=FONT, fill=WHITE, anchor="ra")
    return img


class StatusScreen:
    # The robot runs without its display, a missing or unwired one costs a warning. SPI has to
    # be enabled (dtparam=spi=on) for the panel to be found
    def __init__(self, dc_pin, rst_pin, bl_pin, rotation=90):
        self._lock = threading.Lock()
        try:
            self._panel = ST7789(dc_pin, rst_pin, bl_pin, rotation=rotation)
        except Exception as exc:
            log.warning("no status display: %s", exc)
            self._panel = None

    def show(self, status: Status):
        panel = self._panel
        if panel is None:
            return
        img = render(status, local_ip(), cpu_temp(), os.getloadavg()[0], panel.width, panel.height)
        with self._lock:
            if self._panel is not None:
                self._panel.show(img)

    # a single line in the middle, for while there is no status yet
    def message(self, text):
        panel = self._panel
        if panel is None:
            return
        img = Image.new("RGB", (panel.width, panel.height), BLACK)
        ImageDraw.Draw(img).text((panel.width // 2, panel.height // 2), text, font=FONT, fill=WHITE, anchor="mm")
        with self._lock:
            if self._panel is not None:
                self._panel.show(img)

    def close(self):
        with self._lock:
            if self._panel is not None:
                self._panel.close()
                self._panel = None
