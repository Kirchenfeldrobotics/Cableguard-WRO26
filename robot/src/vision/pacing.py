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
HEADROOM = 2.2

# Rounds of frames in one cycle: the cameras look once, the ring turns them a quarter turn
# onto the two sides they cannot see, and they look again. One round, one turn, so this is
# the number of angles the cycle visits as well (app/main.py TURRET_ANGLES)
ROUNDS_PER_CYCLE = 2

# Cycles the benchmark averages over. The first one is thrown away, it still allocates
BENCHMARK_CYCLES = 9

# Speed and period are derived from each other, so multiplying them back out lands a few
# float bits either side of one frame. Anything under a tenth of a millimetre is that noise
GAP_EPSILON = 1e-4


@dataclass(frozen=True)
class ScanPlan:
    period: float           # seconds between two detector cycles
    speed_mps: float        # what the drive is asked to hold, already inside its limits
    turn_s: float           # seconds one quarter turn of the camera ring gets
    cycle_s: float          # what one cycle measured at startup
    metre_per_frame: float

    # detector cycles per second, one cycle is a frame from every camera at both angles
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


# Time the detector work of one full cycle: every camera is read once per round and the net
# runs on each frame. The ring is left alone, its turns are budgeted from its own limits
def measure_cycle(cams, detector, rounds: int = ROUNDS_PER_CYCLE, cycles: int = BENCHMARK_CYCLES) -> float:
    frames = 0

    def once():
        nonlocal frames
        started = time.monotonic()
        for _ in range(rounds):
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


def plan_scan(cycle_s, camera_fps, speed_limits, min_turn_s, metre_per_frame=METRE_PER_FRAME,
              headroom=HEADROOM, rounds=ROUNDS_PER_CYCLE):
    """Speed and cadence for a scan that covers the rope once, all the way round.

    A round is a frame from every camera and the net run on each of them. Only the shutter
    needs the ring standing still, so the ring turns to the next angle while the detector
    works on the frames just taken: a round lasts as long as the slower of the two, not as
    long as both. Holding one frame of rope per cycle is what makes the frames line up end
    to end.
    """
    detect_s     = cycle_s * headroom
    detect_round = detect_s / rounds            # the net's share of one round
    capture_s    = 1.0 / camera_fps             # the camera has to deliver a fresh frame first

    # the turn is never the thing that is rushed: it is stretched to cover the detector
    turn_s = max(min_turn_s, detect_round)
    period = rounds * (capture_s + turn_s)

    min_mps, max_mps = speed_limits
    ideal_mps = metre_per_frame / period
    speed_mps = min(max(ideal_mps, min_mps), max_mps)

    plan = ScanPlan(period=period, speed_mps=speed_mps, turn_s=turn_s, cycle_s=cycle_s,
                    metre_per_frame=metre_per_frame)

    if turn_s > detect_round:
        # the detector is done before the ring arrives, so the ring sets the pace
        log.info("camera ring sets the pace: %.0f ms per turn against %.0f ms of detector work",
                 turn_s * 1000.0, detect_round * 1000.0)
    else:
        log.info("detector sets the pace: %.0f ms per round, the ring is done in %.0f ms",
                 detect_round * 1000.0, min_turn_s * 1000.0)
    if plan.gap_m > 0.0:
        # the drive cannot crawl slowly enough to keep up with a detector this slow
        log.warning(
            "drive cannot go below %.3f m/s, %.0f mm of every %.0f mm stays unscanned",
            min_mps, plan.gap_m * 1000.0, plan.advance_m * 1000.0)
    elif speed_mps < ideal_mps:
        log.info("drive tops out at %.3f m/s, frames overlap by %.0f%%", max_mps, plan.overlap * 100.0)

    log.info("scan plan: %.2f cycles/s, %.3f m/s, %.0f mm per cycle of a %.0f mm frame, "
             "%d rounds of %.0f ms capture plus %.0f ms turn",
             plan.detect_fps, plan.speed_mps, plan.advance_m * 1000.0, metre_per_frame * 1000.0,
             rounds, capture_s * 1000.0, plan.turn_s * 1000.0)
    return plan
