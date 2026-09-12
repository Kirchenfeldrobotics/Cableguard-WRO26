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
  microsteps: number;
  seq: number;
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
  | CurrentChangedEvent
  | ErrorEvent;

// UI -> Server over /api/ws/ui (forwarded to the robot)

export type RobotCommand = { type: "speed"; value: number } | { type: "stop" };
