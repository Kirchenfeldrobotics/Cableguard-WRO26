/**
 * Where the JWT from `POST /api/auth/login` lives in the browser.
 *
 * It is kept in localStorage so a reload stays signed in, and mirrored in a
 * module variable so `apiUrl` callers and `wsUrl` can read it synchronously.
 */

const STORAGE_KEY = "cableguard.token";

/** `undefined` means "not read from localStorage yet". */
let cached: string | null | undefined;

const listeners = new Set<() => void>();

export function getToken(): string | null {
  if (cached === undefined) {
    cached = typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY);
  }
  return cached;
}

export function setToken(token: string | null): void {
  cached = token;
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(STORAGE_KEY, token);
  else window.localStorage.removeItem(STORAGE_KEY);
}

/** Drops the token and tells the app to show the login screen again. */
export function clearToken(): void {
  if (getToken() === null) return;
  setToken(null);
  listeners.forEach((listener) => listener());
}

/** Subscribes to sign-outs, including the ones caused by a 401 answer. */
export function onSignedOut(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
