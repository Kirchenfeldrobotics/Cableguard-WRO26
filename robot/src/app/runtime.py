import logging

from vision.pacing import plan_scan

log = logging.getLogger(__name__)


# The settings the robot is running on, the hardware they configure and the scan plan they
# work out to. Every task reads its numbers through here rather than off a constant, so a
# new set from the server reaches all of them on their next pass.
#
# A new set is never put in force while the robot works. The drive geometry is read inside
# a running ramp and the ring's angle is counted in microsteps, so both would be redefined
# underneath a move; and the ring has no endstop, so the only moment its counter can be
# seated again is while it rests at the angle the robot is calibrated against. A set that
# arrives at any other moment waits for that moment, and the version reported in the motion
# telemetry stays on the old one until it really is in force
class Runtime:
    def __init__(self, settings, measured, drive, turret, cams, detector, rope_socket):
        self.drive       = drive
        self.turret      = turret
        self.cams        = cams
        self.detector    = detector
        self.rope_socket = rope_socket

        self.settings = settings
        self.version  = 0        # the server's count of changes, echoed in the telemetry

        self._measured = measured    # what one cycle of detector work cost at startup
        self._pending  = None
        self.plan      = self._planned()

    # The angles one cycle visits: where the ring rests to scan, and the two blind sides a
    # sweep away from there
    @property
    def angles(self):
        return (0.0, self.settings.turret_sweep_deg)

    # where the ring waits while the robot is open, and rests whenever it is not scanning
    @property
    def open_angle(self):
        return self.settings.turret_open_angle

    # The pace the current settings work out to. The detector is not timed again: what it
    # costs per frame does not change with any of these numbers
    def _planned(self):
        s = self.settings
        return plan_scan(
            measured=self._measured,
            speed_limits=(self.drive.to_metres(self.drive.start_speed),
                          self.drive.to_metres(self.drive.max_speed)),
            sweep_deg=s.turret_sweep_deg,
            min_turn_s=self.turret.min_turn_s(s.turret_sweep_deg),
            metre_per_frame=s.metre_per_frame,
            headroom=s.headroom,
        )

    # A new set from the server. It is queued rather than applied, see flush
    def accept(self, version, settings):
        if version == self.version and self._pending is None:
            return
        log.info("settings version %d received", version)
        self._pending = (version, settings)
        self.flush()

    # Put a queued set in force if the robot is in a state to take one, and report whether
    # it did. Called once per pass of the detection cycle, which is where the robot rests
    def flush(self):
        if self._pending is None:
            return False
        if self.drive.moving or not self.turret.at(self.open_angle):
            return False

        version, settings = self._pending
        self._pending = None
        try:
            self._apply(settings)
        except Exception:
            # Half of a set is worse than none of it, but there is no taking back the half
            # that went through. The version is left alone, so the webapp keeps showing
            # these settings as not in force
            log.exception("settings version %d only partly took, the robot is between two sets",
                          version)
            return False

        self.version = version
        log.info("settings version %d in force: %.3f m/s, %.0f mm per frame, ring to %.0f deg",
                 version, self.plan.speed_mps, settings.metre_per_frame * 1000.0,
                 settings.turret_sweep_deg)
        return True

    def _apply(self, s):
        self.drive.configure(
            microsteps=s.drive_microsteps,
            gear_ratio=s.drive_gear_ratio,
            metres_per_rev=s.drive_metres_per_rev,
            start_speed=s.drive_start_speed,
            max_speed=s.drive_max_speed,
            accel=s.drive_accel,
        )
        self.turret.configure(
            microsteps=s.turret_microsteps,
            gear_ratio=s.turret_gear_ratio,
            max_deg_s=s.turret_max_deg_s,
            accel=s.turret_accel,
            settle_s=s.turret_settle_s,
            start_angle=s.turret_open_angle,
        )

        self.rope_socket.trigger_diff_m = s.socket_trigger_diff_m
        self.rope_socket.clear_m        = s.socket_clear_m
        # a new drive scale turns the microsteps already counted into a different number of
        # metres, and the clear distance is measured in metres from a mark
        self.rope_socket.rebase(self.drive.metres_done)

        self.detector.configure(s.detect_confidence, s.detect_iou)
        self.cams.configure(s.camera_fps, s.camera_exposure_us, s.camera_gain,
                            s.camera_focus_distance_m)

        self.settings = s
        self.plan     = self._planned()
