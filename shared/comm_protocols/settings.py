# Every constant of the robot the operator may change from the webapp, in one place.
#
# The defaults here are the robot's own: it boots from them and runs on them with no link
# to a server at all. The backend keeps the operator's values in its database and sends
# them to the robot as a SettingsCmd; anything that command does not carry falls back to
# the default below, so a robot ahead of the server, or behind it, still starts.
#
# The bounds and the prose are read off these fields by the backend and rendered by the
# settings page, so a new setting is added here and nowhere else.

from typing import Literal

from pydantic import BaseModel, Field

# What the settings page draws as a section, in the order it draws them
GROUPS = (
    ("drive",     "Drive",       "The stepper that moves the robot along the rope."),
    ("turret",    "Camera ring", "The stepper that swings both cameras around the rope."),
    ("scan",      "Scan pacing", "How fast the robot may walk the rope and still see all of it."),
    ("detection", "Detection",   "What the vision model reports and what is kept of it."),
    ("socket",    "Rope socket", "When the robot opens to let a rope socket pass."),
    ("camera",    "Cameras",     "How both cameras are exposed and how often they are read."),
    ("timing",    "Reporting",   "How often the robot reports and checks on itself."),
)

GroupKey = Literal["drive", "turret", "scan", "detection", "socket", "camera", "timing"]


# One setting. Its type and default are the field's own, the rest is what the settings page
# needs to draw a row for it
def setting(default, *, group: GroupKey, label: str, unit: str, note: str,
            ge: float, le: float, step: float, restart: bool = False):
    return Field(default, ge=ge, le=le, description=note,
                 json_schema_extra={"group": group, "label": label, "unit": unit,
                                    "step": step, "restart": restart})


class RobotSettings(BaseModel):
    # -- drive -------------------------------------------------------------------------
    drive_microsteps: int = setting(
        8, group="drive", label="Microstepping", unit="/step", ge=1, le=256, step=1,
        note="Microsteps the driver makes of one full step, as the DIP switches on the driver "
             "are set. Change it together with the microsteps per metre below: the two "
             "describe the same gearing, and only that one is what distances are measured in.")
    drive_microsteps_per_metre: float = setting(
        10186.0, group="drive", label="Microsteps per metre", unit="/m", ge=1.0, le=1e6, step=1.0,
        note="How far the robot travels for one microstep. Every distance it reports is "
             "measured with this number, so it is the one to check against a tape measure.")
    drive_start_speed: float = setting(
        200.0, group="drive", label="Start speed", unit="1/s", ge=1.0, le=20000.0, step=10.0,
        note="Slowest the drive is pulsed, in microsteps per second. Every ramp starts and "
             "ends here; asked for less than this the drive stands still.")
    drive_max_speed: float = setting(
        2000.0, group="drive", label="Maximum speed", unit="1/s", ge=1.0, le=50000.0, step=50.0,
        note="Fastest the drive may run, whatever speed the scan plan works out. A plan that "
             "wants more than this makes the camera frames overlap instead.")
    drive_accel: float = setting(
        4000.0, group="drive", label="Acceleration", unit="1/s²", ge=1.0, le=500000.0, step=100.0,
        note="How hard the drive ramps, in microsteps per second squared. Too hard and the "
             "motor slips, which loses the position the whole run is measured against.")

    # -- camera ring -------------------------------------------------------------------
    turret_microsteps: int = setting(
        8, group="turret", label="Microstepping", unit="/step", ge=1, le=256, step=1,
        note="Microsteps the ring's driver makes of one full step, as its DIP switches are set.")
    turret_gear_ratio: float = setting(
        1.0, group="turret", label="Gear ratio", unit="x", ge=0.01, le=100.0, step=0.1,
        note="Motor turns for one turn of the ring. 1.0 means the motor sits on the ring axis, "
             "a reduction between the two makes it larger.")
    turret_max_deg_s: float = setting(
        200.0, group="turret", label="Maximum rotation speed", unit="°/s", ge=1.0, le=2000.0,
        step=5.0,
        note="Fastest the ring may swing. The camera cables set this, not the motor: asked for "
             "more, the robot slows its whole scan down rather than hurry the ring.")
    turret_accel: float = setting(
        20000.0, group="turret", label="Acceleration", unit="1/s²", ge=1.0, le=1000000.0, step=500.0,
        note="How hard the ring ramps, in microsteps per second squared. The ring is light and "
             "takes far more of it than the drive.")
    turret_settle_s: float = setting(
        0.05, group="turret", label="Settle time", unit="s", ge=0.0, le=2.0, step=0.01,
        note="Time the cameras get to stop swinging after a turn. Cut it too fine and the rope "
             "is smeared across the frame the detector has to read.")
    turret_sweep_deg: float = setting(
        90.0, group="turret", label="Sweep", unit="°", ge=1.0, le=180.0, step=5.0,
        note="How far the ring swings between the two halves of a cycle. Two cameras facing "
             "each other see two sides of the rope, the blind two are a quarter turn away.")
    turret_open_angle: float = setting(
        -45.0, group="turret", label="Open angle", unit="°", ge=-180.0, le=180.0, step=5.0,
        note="Where the ring parks while the robot is open, and where it rests whenever the "
             "robot stands. The ring has no endstop, so leaving it here is the calibration.")

    # -- scan pacing -------------------------------------------------------------------
    metre_per_frame: float = setting(
        0.06, group="scan", label="Rope per frame", unit="m", ge=0.001, le=2.0, step=0.005,
        note="How much rope one camera frame covers along the rope. The drive speed follows "
             "from it: the robot travels exactly one frame of rope per detector cycle.")
    headroom: float = setting(
        1.5, group="scan", label="Detector headroom", unit="x", ge=1.0, le=5.0, step=0.1,
        note="Safety factor on the detector time measured at startup. Inference is slower on a "
             "frame with something in it than on the clean rope the benchmark ran on, and a "
             "cycle that overruns leaves a stretch of rope unscanned.")
    benchmark_cycles: int = setting(
        9, group="scan", label="Benchmark cycles", unit="", ge=1, le=60, step=1, restart=True,
        note="Cycles the startup benchmark averages the detector over before it picks a speed.")

    # -- detection ---------------------------------------------------------------------
    detect_confidence: float = setting(
        0.1, group="detection", label="Confidence threshold", unit="", ge=0.01, le=0.99, step=0.01,
        note="Boxes the model is less sure of than this are dropped and never reported.")
    detect_iou: float = setting(
        0.5, group="detection", label="Overlap threshold", unit="", ge=0.01, le=0.99, step=0.01,
        note="Two boxes that overlap more than this are counted as one detection.")
    defect_jpeg_quality: int = setting(
        85, group="detection", label="Evidence quality", unit="%", ge=10, le=100, step=5,
        note="JPEG quality the frame a defect was found in is stored at. It is the evidence for "
             "the finding, so it has to stay sharp enough to show a single wire.")

    # -- rope socket -------------------------------------------------------------------
    socket_distance_m: float = setting(
        0.30, group="socket", label="Sensor trigger", unit="m", ge=0.02, le=2.0, step=0.01,
        note="A distance reading closer than this counts as a rope socket ahead. Far enough "
             "that the robot opens before it arrives, close enough that the rope itself and the "
             "odd branch do not keep opening it.")
    socket_clear_m: float = setting(
        0.50, group="socket", label="Clear distance", unit="m", ge=0.05, le=10.0, step=0.05,
        note="Driven from where the sensor last saw the socket before the robot closes again. "
             "It runs from the last sighting, so a long socket is passed whole.")

    # -- cameras -----------------------------------------------------------------------
    camera_fps: float = setting(
        15.0, group="camera", label="Frame rate", unit="/s", ge=1.0, le=120.0, step=1.0,
        note="Rate both cameras run at. The detector and the live stream each take what they "
             "need from it, so it only has to stay above the stream rate.")
    stream_fps: float = setting(
        8.0, group="camera", label="Live stream rate", unit="/s", ge=1.0, le=60.0, step=1.0,
        note="How often a frame of each camera is encoded and sent to the live view. This is "
             "the whole cost of the stream, the detector does not use these frames.")
    camera_exposure_us: int = setting(
        20000, group="camera", label="Exposure", unit="µs", ge=100, le=200000, step=500,
        note="Shutter time of both cameras. Longer is brighter and smears a rope moving under "
             "it, which is the image the detector has to read.")
    camera_gain: float = setting(
        2.0, group="camera", label="Gain", unit="x", ge=1.0, le=16.0, step=0.1,
        note="Analogue gain of both cameras. It brightens a dark rope without the smear of a "
             "longer exposure, at the price of noise.")
    camera_focus_distance_m: float = setting(
        0.05, group="camera", label="Focus distance", unit="m", ge=0.01, le=5.0, step=0.005,
        note="Distance the lenses are locked at: how far the rope sits in front of them. A "
             "fixed focus lens ignores it.")

    # -- reporting ---------------------------------------------------------------------
    telemetry_period: float = setting(
        0.5, group="timing", label="Telemetry period", unit="s", ge=0.05, le=10.0, step=0.05,
        note="How often the robot reports speed and position. The live view counts telemetry "
             "older than two seconds as gone, so this has to stay well under that.")
    distance_period: float = setting(
        0.5, group="timing", label="Distance period", unit="s", ge=0.05, le=10.0, step=0.05,
        note="How often the distance sensor is read. It is what spots a rope socket ahead, so "
             "reading it rarely means meeting the socket later.")
    display_period: float = setting(
        1.0, group="timing", label="Display period", unit="s", ge=0.1, le=10.0, step=0.1,
        note="How often the status display on the robot is redrawn.")
    guard_period: float = setting(
        0.5, group="timing", label="Link check period", unit="s", ge=0.05, le=10.0, step=0.05,
        note="How often the robot checks that its control link is still up. It stops itself as "
             "soon as it finds the link gone.")
    open_poll: float = setting(
        0.25, group="timing", label="Open check period", unit="s", ge=0.05, le=5.0, step=0.05,
        note="How often an open robot looks at whether the socket is behind it and it may close "
             "again.")


# One setting as the settings page needs it, all of it read off the field above
class SettingInfo(BaseModel):
    key: str
    group: GroupKey
    label: str
    unit: str
    note: str
    default: float
    minimum: float
    maximum: float
    step: float
    integer: bool
    restart: bool       # takes effect at the next robot start, not on the running robot


class SettingGroup(BaseModel):
    key: GroupKey
    title: str
    note: str


# a bound the field carries as an annotation, ge or le
def _bound(field, name):
    for mark in field.metadata:
        value = getattr(mark, name, None)
        if value is not None:
            return float(value)
    raise ValueError(f"setting without a {name} bound")


def describe_settings() -> list[SettingInfo]:
    described = []
    for key, field in RobotSettings.model_fields.items():
        extra = field.json_schema_extra
        described.append(SettingInfo(
            key=key,
            group=extra["group"],
            label=extra["label"],
            unit=extra["unit"],
            note=field.description,
            default=field.default,
            minimum=_bound(field, "ge"),
            maximum=_bound(field, "le"),
            step=extra["step"],
            integer=field.annotation is int,
            restart=extra["restart"],
        ))
    return described


def describe_groups() -> list[SettingGroup]:
    return [SettingGroup(key=key, title=title, note=note) for key, title, note in GROUPS]
