import { apiUrl } from "@/lib/config";
import type { CurrentSelection, Defect, Rope, Run } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });

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
    remove: (runId: string) =>
      request<void>(`/api/runs/${encodeURIComponent(runId)}`, { method: "DELETE" }),
  },
  defects: {
    list: (runId: string) => request<Defect[]>(`/api/defects${query({ run_id: runId })}`),
  },
  current: {
    get: () => request<CurrentSelection>("/api/current"),
    set: (selection: CurrentSelection) =>
      request<CurrentSelection>("/api/current", { method: "POST", body: json(selection) }),
  },
};
