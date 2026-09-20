import { getToken } from "@/lib/auth/session";

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

/**
 * WebSocket URL for an API path such as `/api/ws/ui`. Browser only.
 *
 * A WebSocket cannot carry an Authorization header, so the access token goes
 * in the query string; `authenticate_ui` in backend/app/auth.py reads it there.
 */
export function wsUrl(path: string): string {
  const base = API_BASE_URL || window.location.origin;
  const url = `${base.replace(/^http/, "ws")}${path}`;
  const token = getToken();
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

/** Human-readable name of the server, shown on the settings screen. */
export function serverLabel(): string {
  return API_BASE_URL || (typeof window === "undefined" ? "same origin" : window.location.host);
}

