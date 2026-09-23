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
    turn_deg_s: float       # the speed that works out to, averaged over the whole move
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


def plan_scan(cycle_s, camera_fps, speed_limits, sweep_deg, min_turn_s,
              metre_per_frame=METRE_PER_FRAME, headroom=HEADROOM, rounds=ROUNDS_PER_CYCLE):
    """Speed and cadence for a scan that covers the rope once, all the way round.

    The detector sets the cycle. A round is a frame from every camera and the net run on
    each of them; only the shutter needs the ring standing still, so the ring swings to the
    next angle while the net works on the frames just taken. That gives the cycle, and the
    cycle gives both the drive speed, one frame of rope per cycle, and the speed the ring
    has to swing at to be in place for the next round.

    The ring is the one thing that can refuse: if it cannot swing that fast it takes the
    time it needs and the cycle, and with it the robot, is slowed down to suit.
    """
    detect_s     = cycle_s * headroom
    detect_round = detect_s / rounds            # the net's share of one round
    capture_s    = 1.0 / camera_fps             # the camera has to deliver a fresh frame first

    # the cycle the detector asks for, and the time that leaves the ring to swing in
    turn_s = detect_round
    period = rounds * (capture_s + turn_s)

    if turn_s < min_turn_s:
        # the ring cannot keep up, so it takes what it needs and the cycle grows around it
        log.warning("ring cannot swing %.0f deg in %.0f ms (%.0f deg/s asked of it), it needs "
                    "%.0f ms: the cycle grows from %.2f s to %.2f s and the drive slows to suit",
                    sweep_deg, turn_s * 1000.0, sweep_deg / turn_s, min_turn_s * 1000.0,
                    period, rounds * (capture_s + min_turn_s))
        turn_s = min_turn_s
        period = rounds * (capture_s + turn_s)

    min_mps, max_mps = speed_limits
    ideal_mps = metre_per_frame / period
    speed_mps = min(max(ideal_mps, min_mps), max_mps)

    plan = ScanPlan(period=period, speed_mps=speed_mps, turn_s=turn_s,
                    turn_deg_s=sweep_deg / turn_s, cycle_s=cycle_s,
                    metre_per_frame=metre_per_frame)

    log.info("cycle set by the %s: the ring swings %.0f deg in %.0f ms, %.0f deg/s",
             "camera ring" if turn_s > detect_round else "detector",
             sweep_deg, turn_s * 1000.0, plan.turn_deg_s)
    if plan.gap_m > 0.0:
        # the drive cannot crawl slowly enough to keep up with a detector this slow
        log.warning(
            "drive cannot go below %.3f m/s, %.0f mm of every %.0f mm stays unscanned",
            min_mps, plan.gap_m * 1000.0, plan.advance_m * 1000.0)
    elif speed_mps < ideal_mps:
        log.info("drive tops out at %.3f m/s, frames overlap by %.0f%%", max_mps, plan.overlap * 100.0)

    log.info("scan plan: %.2f cycles/s, %.3f m/s, %.0f mm per cycle of a %.0f mm frame, "
             "%d rounds of %.0f ms capture plus %.0f ms of net behind the turn",
             plan.detect_fps, plan.speed_mps, plan.advance_m * 1000.0, metre_per_frame * 1000.0,
             rounds, capture_s * 1000.0, detect_round * 1000.0)
    return plan
