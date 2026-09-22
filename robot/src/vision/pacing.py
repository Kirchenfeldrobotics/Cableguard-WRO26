import logging
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

# How much rope one frame covers along the rope axis. Placeholder until the optics are
# measured: the lens is focused at 50 mm and sees a few centimetres of rope
METRE_PER_FRAME = 0.06

# The detector is never run at the edge of what it manages. Inference gets slower the more
# boxes a frame holds, and the benchmark runs on a clean rope, so a cycle in the field is
# slower than a cycle at startup. A cycle that overruns leaves a gap in the rope
HEADROOM = 1.7

# Cycles the benchmark averages over. The first one is thrown away, it still allocates
BENCHMARK_CYCLES = 9

# Speed and period are derived from each other, so multiplying them back out lands a few
# float bits either side of one frame. Anything under a tenth of a millimetre is that noise
GAP_EPSILON = 1e-4


@dataclass(frozen=True)
class ScanPlan:
    period: float           # seconds between two detector cycles
    speed_mps: float        # what the drive is asked to hold, already inside its limits
    cycle_s: float          # what one cycle measured at startup
    metre_per_frame: float

    # detector cycles per second, one cycle is a frame from every camera
    @property
    def detect_fps(self):
        return 1.0 / self.period

    # rope the robot travels between two cycles
    @property
    def advance_m(self):
        return self.speed_mps * self.period

    # rope nobody ever looks at, zero while the frames meet or overlap
    @property
    def gap_m(self):
        gap = self.advance_m - self.metre_per_frame
        return gap if gap > GAP_EPSILON else 0.0

    # share of a frame that repeats the frame before it, zero when they meet edge to edge
    @property
    def overlap(self):
        return max(0.0, 1.0 - self.advance_m / self.metre_per_frame)


# time one full cycle: a frame from every camera and the net run on each of them
def measure_cycle(cams, detector, cycles: int = BENCHMARK_CYCLES) -> float:
    frames = 0

    def once():
        nonlocal frames
        started = time.monotonic()
        for _, frame in cams.capture():
            detector.detect(frame)
            frames += 1
        return time.monotonic() - started

    once()                                        # still allocating, not counted
    frames = 0
    samples = [once() for _ in range(cycles)]
    cycle_s = sum(samples) / len(samples)

    log.info("detector cycle: %.0f ms for %d frames (%s ms)", cycle_s * 1000.0, frames // cycles,
             ", ".join(f"{s * 1000.0:.0f}" for s in samples))
    return cycle_s


def plan_scan(cycle_s, camera_fps, speed_limits, metre_per_frame=METRE_PER_FRAME, headroom=HEADROOM):
    """Speed and cadence for a scan that covers the rope once.

    The detector sets the pace: it can be run every `cycle_s * headroom` seconds at best,
    and never faster than the camera delivers frames. Holding one frame of rope per cycle
    is what makes the frames line up end to end.
    """
    slowest_frame = 1.0 / camera_fps
    period = max(cycle_s * headroom, slowest_frame)

    min_mps, max_mps = speed_limits
    ideal_mps = metre_per_frame / period
    speed_mps = min(max(ideal_mps, min_mps), max_mps)

    plan = ScanPlan(period=period, speed_mps=speed_mps, cycle_s=cycle_s, metre_per_frame=metre_per_frame)

    if period == slowest_frame:
        log.info("detector is faster than the camera, capped at %.1f fps", camera_fps)
    if plan.gap_m > 0.0:
        # the drive cannot crawl slowly enough to keep up with a detector this slow
        log.warning(
            "drive cannot go below %.3f m/s, %.0f mm of every %.0f mm stays unscanned",
            min_mps, plan.gap_m * 1000.0, plan.advance_m * 1000.0)
    elif speed_mps < ideal_mps:
        log.info("drive tops out at %.3f m/s, frames overlap by %.0f%%", max_mps, plan.overlap * 100.0)

    log.info("scan plan: %.2f fps, %.3f m/s, %.0f mm per cycle of a %.0f mm frame",
             plan.detect_fps, plan.speed_mps, plan.advance_m * 1000.0, metre_per_frame * 1000.0)
    return plan
