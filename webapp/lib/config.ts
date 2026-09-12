/**
 * Base URL of the FastAPI backend.
 *
 * Empty (default) means same origin: in production the reverse proxy serves
 * the webapp and `/api/*` from one domain. Set NEXT_PUBLIC_API_URL for local
 * development, e.g. `http://localhost:8021`.
 */
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

/** HTTP URL for an API path such as `/api/ropes`. */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/** WebSocket URL for an API path such as `/api/ws/ui`. Browser only. */
export function wsUrl(path: string): string {
  const base = API_BASE_URL || window.location.origin;
  return `${base.replace(/^http/, "ws")}${path}`;
}

/** Human-readable name of the server, shown on the settings screen. */
export function serverLabel(): string {
  return API_BASE_URL || (typeof window === "undefined" ? "same origin" : window.location.host);
}

/**
 * Drive limits in microsteps per second, mirrored from the robot so the controls can show
 * what it will actually do. The robot clamps every speed command to MAX_SPEED
 * (robot/src/app/main.py) and treats anything below start_speed
 * (robot/src/motion/stepper.py) as a stop.
 */
export const MAX_DRIVE_SPEED = 2_000;
export const MIN_DRIVE_SPEED = 200;
