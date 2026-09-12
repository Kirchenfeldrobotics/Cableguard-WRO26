import { clearToken, getToken } from "@/lib/auth/session";
import { apiUrl } from "@/lib/config";
import type { AuthUser, CurrentSelection, Defect, LoginResult, Rope, Run } from "./types";

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
async function request<T>(
  path: string,
  init?: RequestInit,
  { anonymous = false }: { anonymous?: boolean } = {},
): Promise<T> {
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
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }

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
  },
  defects: {
    list: (runId: string) => request<Defect[]>(`/api/defects${query({ run_id: runId })}`),
  },
  current: {
    get: () => request<CurrentSelection>("/api/current"),
  },
};
