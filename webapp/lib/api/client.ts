import { clearToken, getToken } from "@/lib/auth/session";
import { apiUrl } from "@/lib/config";
import type {
  AuthUser,
  CurrentSelection,
  Defect,
  LoginResult,
  Rope,
  Run,
  SettingsDocument,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** `anonymous` skips the access token, for the login call itself. */
async function send(
  path: string,
  init?: RequestInit,
  { anonymous = false }: { anonymous?: boolean } = {},
): Promise<Response> {
  const token = anonymous ? null : getToken();
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  // The token expired or the account is gone: back to the login screen.
  if (res.status === 401 && !anonymous) clearToken();

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Body is not JSON; keep the status text.
    }
    throw new ApiError(res.status, `${path} failed: ${res.status} ${detail || res.statusText}`);
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit, options?: { anonymous?: boolean }): Promise<T> {
  const res = await send(path, init, options);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);
const query = (params: Record<string, string>) => `?${new URLSearchParams(params)}`;

/** Typed access to every REST endpoint in backend/app/routers. */
export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<LoginResult>(
        "/api/auth/login",
        { method: "POST", body: json({ username, password }) },
        { anonymous: true },
      ),
    /** Signs in with the key from the robot's NFC tag. */
    nfcLogin: (key: string) =>
      request<LoginResult>("/api/auth/nfc", { method: "POST", body: json({ key }) }, { anonymous: true }),
    me: () => request<AuthUser>("/api/auth/me"),
  },
  ropes: {
    list: () => request<Rope[]>("/api/ropes"),
    create: (name: string) => request<Rope>("/api/ropes", { method: "POST", body: json({ name }) }),
    remove: (ropeId: string) =>
      request<void>(`/api/ropes/${encodeURIComponent(ropeId)}`, { method: "DELETE" }),
  },
  runs: {
    list: (ropeId: string) => request<Run[]>(`/api/runs${query({ rope_id: ropeId })}`),
    create: (ropeId: string, name: string) =>
      request<Run>("/api/runs", { method: "POST", body: json({ name, rope_id: ropeId }) }),
    finish: (runId: string) =>
      request<Run>(`/api/runs/${encodeURIComponent(runId)}/finish`, { method: "POST" }),
    remove: (runId: string) =>
      request<void>(`/api/runs/${encodeURIComponent(runId)}`, { method: "DELETE" }),
  },
  defects: {
    list: (runId: string) => request<Defect[]>(`/api/defects${query({ run_id: runId })}`),
    /** JPEG of the frame the defect was found in. Fetched, not linked: an <img> cannot send the token. */
    frame: (defectId: string) =>
      send(`/api/defects/${encodeURIComponent(defectId)}/frame`).then((res) => res.blob()),
  },
  settings: {
    get: () => request<SettingsDocument>("/api/settings"),
    /** Only the settings named here move, the rest keep the value they have. */
    update: (values: Record<string, number>) =>
      request<SettingsDocument>("/api/settings", { method: "PUT", body: json({ values }) }),
    /** Back to the constants the robot is built with. */
    reset: () => request<SettingsDocument>("/api/settings/reset", { method: "POST" }),
  },
  current: {
    get: () => request<CurrentSelection>("/api/current"),
    set: (selection: CurrentSelection) =>
      request<CurrentSelection>("/api/current", { method: "POST", body: json(selection) }),
  },
};
