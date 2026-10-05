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

/**
 * A request the server refused or never got. The message is what the operator reads, so it
 * is a sentence and nothing else; the endpoint and the status are kept beside it.
 */
export class ApiError extends Error {
  constructor(
    /** HTTP status, 0 when the server could not be reached at all. */
    readonly status: number,
    readonly path: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** `wrong username or password` becomes `Wrong username or password.` */
function sentence(text: string): string {
  const capitalised = text.charAt(0).toUpperCase() + text.slice(1);
  return /[.!?…]$/.test(capitalised) ? capitalised : `${capitalised}.`;
}

/** The server words a refusal as text, and a refused field as a list with one entry per field. */
function errorDetail(body: unknown): string | null {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail ? sentence(detail) : null;
  if (!Array.isArray(detail)) return null;
  return detail
    .map((item: { loc?: unknown[]; msg?: string }) =>
      [item.loc?.[item.loc.length - 1], item.msg].filter(Boolean).join(": "),
    )
    .join(", ");
}

/** `anonymous` skips the access token, for the login call itself. */
async function send(
  path: string,
  init?: RequestInit,
  { anonymous = false }: { anonymous?: boolean } = {},
): Promise<Response> {
  const token = anonymous ? null : getToken();
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, path, "The server cannot be reached.");
  }

  // The token expired or the account is gone: back to the login screen.
  if (res.status === 401 && !anonymous) clearToken();

  if (!res.ok) {
    let detail: string | null = null;
    try {
      detail = errorDetail(await res.json());
    } catch {
      // Body is not JSON; the status has to do.
    }
    throw new ApiError(res.status, path, detail ?? `The server answered with an error (${res.status}).`);
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
    create: (name: string, lengthM: number) =>
      request<Rope>("/api/ropes", { method: "POST", body: json({ name, length_m: lengthM }) }),
    /** The length is the only thing about a rope that can be corrected. */
    update: (ropeId: string, lengthM: number) =>
      request<Rope>(`/api/ropes/${encodeURIComponent(ropeId)}`, {
        method: "PATCH",
        body: json({ length_m: lengthM }),
      }),
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
    /** A finding is several detections, so a review names all of them. */
    review: (defectIds: string[], reviewed: boolean) =>
      request<Defect[]>("/api/defects/review", {
        method: "POST",
        body: json({ defect_ids: defectIds, reviewed }),
      }),
    /** For a false positive: the detections are deleted, there is no way back. */
    remove: (defectIds: string[]) =>
      request<void>("/api/defects/remove", { method: "POST", body: json({ defect_ids: defectIds }) }),
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
