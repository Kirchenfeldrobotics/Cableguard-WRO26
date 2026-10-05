/*
 * Mirrors of the backend contracts. Keep in sync with:
 *   backend/app/schemas.py            (REST)
 *   backend/app/ws/hub.py             (UI socket events)
 *   shared/comm_protocols/messages.py (robot telemetry and commands)
 *   shared/comm_protocols/settings.py (the robot's settings)
 */

export type DefectKind = "lf" | "lma";

export interface AuthUser {
  id: string;
  username: string;
}

export interface LoginResult {
  access_token: string;
  token_type: "bearer";
  /** Lifetime of the token in seconds. */
  expires_in: number;
  user: AuthUser;
}

export interface Rope {
  id: string;
  name: string;
  /** Metres. Null only for a rope that was added before the length was asked for. */
  length_m: number | null;
  created_at: string;
}

export interface Run {
  id: string;
  name: string;
  rope_id: string;
  started_at: string;
  finished_at: string | null;
}

export interface Defect {
  id: string;
  run_id: string;
  kind: DefectKind;
  /** Distance from the start of the rope, in metres. */
  pos_to_start: number;
  created_at: string;
  /** Class name of the detector, e.g. `broken_wire`. Null for defects from another sensor. */
  label: string | null;
  /** 0..1, as the model reported it. */
  confidence: number | null;
  /** 0 or 1, the camera that saw it. */
  cam: number | null;
  /** Box in the detector frame, 0..1 of the frame's width and height. */
  box_x1: number | null;
  box_y1: number | null;
  box_x2: number | null;
  box_y2: number | null;
  /** Set when the frame the defect was found in is stored, see api.defects.frame. */
  frame_id: string | null;
}

export interface CurrentSelection {
  rope_id: string | null;
  run_id: string | null;
}

/**
 * One robot setting, exactly as `shared/comm_protocols/settings.py` defines it. The label,
 * the explanation and the bounds come from the server, so the settings page never has to
 * carry a second copy of them.
 */
export interface SettingField {
  key: string;
  /** Section it belongs to, see `SettingGroup`. */
  group: string;
  label: string;
  /** Shown after the input, e.g. `m` or `°/s`. Empty for a plain count. */
  unit: string;
  note: string;
  default: number;
  minimum: number;
  maximum: number;
  /** Increment of the number input. */
  step: number;
  /** Whole numbers only. */
  integer: boolean;
  /** Takes effect the next time the robot starts, not on the one that is running. */
  restart: boolean;
}

export interface SettingGroup {
  key: string;
  title: string;
  note: string;
}

/**
 * Every setting by name. The three the rest of the app reads directly are spelled out;
 * the settings page draws the others from `SettingsDocument.fields`.
 */
export interface RobotSettings {
  /** Angle the camera ring parks at while the robot is open for a rope socket. */
  turret_open_angle: number;
  /** How far below its calibrated reading the sensor opens the robot by itself, in metres. */
  socket_trigger_diff_m: number;
  /** Metres the robot drives from the socket before it closes again. */
  socket_clear_m: number;
  [key: string]: number;
}

export interface SettingsDocument {
  /**
   * Counts changes on the server. The robot reports the version it is actually running on
   * in its motion telemetry, and the two only match once a change has really taken.
   */
  version: number;
  updated_at: string;
  values: RobotSettings;
  fields: SettingField[];
  groups: SettingGroup[];
}

// Server -> UI over /api/ws/ui

export interface RobotStatusEvent {
  type: "robot_status";
  online: boolean;
}

/** Heartbeat relayed from the robot; carries no payload beyond its arrival time. */
export interface AliveEvent {
  type: "alive";
}

export interface MotionTelemetryEvent {
  type: "motion_telemetry";
  /** Drive speed in microsteps per second (see robot/src/motion/drive.py). */
  speed: number;
  /** The same speed in metres per second. The robot owns the drive geometry. */
  speed_mps: number;
  /** Exact step count since the origin was reset, for debugging the drive. */
  microsteps: number;
  /** Metres since the origin was reset, which happens when a run is selected. */
  metres: number;
  /** Speed the robot holds while scanning, derived from how fast its detector runs. */
  scan_speed_mps: number;
  /** Detector cycles per second the scan is paced for. */
  detect_fps: number;
  /** The camera ring is parked clear of a rope socket and the detector is off. */
  robot_open: boolean;
  /** The distance sensor is allowed to open the robot by itself. */
  socket_watch: boolean;
  /**
   * What the distance sensor reads with no socket in front of it, measured at startup.
   * Null until it is calibrated, and after a calibration that found nothing: the robot
   * turns `socket_watch` off in that case, since it has nothing to compare against.
   */
  socket_baseline_m?: number | null;
  /** Version of the settings the robot is really running on, see `SettingsDocument`. */
  settings_version: number;
  seq: number;
}

/** What the robot's distance sensor sees (robot/src/tof). Live only, nothing is stored. */
export interface DistanceTelemetryEvent {
  type: "distance_telemetry";
  /** Metres to the nearest object, null when nothing is within the sensor's range of about 2 m. */
  distance_m: number | null;
  seq: number;
}

/** One box from a vision_telemetry frame. */
export interface VisionDetection {
  label: string;
  /** Null when the robot cannot map the class name to a kind. */
  kind: DefectKind | null;
  confidence: number;
  /** x1, y1, x2, y2, 0..1 of the frame. */
  box: [number, number, number, number];
}

/**
 * What one camera saw in one frame, sent every DETECT_PERIOD (robot/src/app/main.py).
 * Arrives for every frame, also the empty ones, so it doubles as the detector's heartbeat.
 */
export interface VisionTelemetryEvent {
  type: "vision_telemetry";
  seq: number;
  cam: number;
  /** Unix epoch seconds on the robot. */
  captured_at: number;
  inference_ms: number;
  microsteps: number;
  distance_from_origin: number | null;
  frame_w: number;
  frame_h: number;
  detections: VisionDetection[];
}

export interface CurrentChangedEvent {
  type: "current_changed";
  rope_id: string | null;
  run_id: string | null;
}

/** Someone changed the robot's settings; reload them. */
export interface SettingsChangedEvent {
  type: "settings_changed";
  version: number;
}

export interface ErrorEvent {
  type: "error";
  detail: string;
}

export type ServerEvent =
  | RobotStatusEvent
  | AliveEvent
  | MotionTelemetryEvent
  | DistanceTelemetryEvent
  | VisionTelemetryEvent
  | CurrentChangedEvent
  | SettingsChangedEvent
  | ErrorEvent;

// UI -> Server over /api/ws/ui (forwarded to the robot)

/**
 * The operator picks the direction and when to run; the robot derives its own speed so the
 * detector frames cover the rope end to end (robot/src/vision/pacing.py).
 */
export type DriveDirection = "forward" | "reverse";

/**
 * Start and stop drive the run. `open` parks the camera ring clear of a rope socket and
 * stops the detector until `close`; `socket_watch` arms or disarms the robot's own trigger
 * for it, which opens on the distance sensor and closes once the socket is behind it.
 */
export type RobotCommand =
  | { type: "start"; direction: DriveDirection }
  | { type: "stop" }
  | { type: "open" }
  | { type: "close" }
  | { type: "socket_watch"; enabled: boolean };
