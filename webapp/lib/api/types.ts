/*
 * Mirrors of the backend contracts. Keep in sync with:
 *   backend/app/schemas.py            (REST)
 *   backend/app/ws/hub.py             (UI socket events)
 *   shared/comm_protocols/messages.py (robot telemetry and commands)
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
  /** Drive speed in microsteps per second (see robot/src/motion/stepper.py). */
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

export interface ErrorEvent {
  type: "error";
  detail: string;
}

export type ServerEvent =
  | RobotStatusEvent
  | AliveEvent
  | MotionTelemetryEvent
  | VisionTelemetryEvent
  | CurrentChangedEvent
  | ErrorEvent;

// UI -> Server over /api/ws/ui (forwarded to the robot)

/**
 * The operator picks the direction and when to run; the robot derives its own speed so the
 * detector frames cover the rope end to end (robot/src/vision/pacing.py).
 */
export type DriveDirection = "forward" | "reverse";

export type RobotCommand = { type: "start"; direction: DriveDirection } | { type: "stop" };
