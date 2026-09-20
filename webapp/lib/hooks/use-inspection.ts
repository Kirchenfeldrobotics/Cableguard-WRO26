"use client";

import { api } from "@/lib/api/client";
import type { Defect, Rope, Run } from "@/lib/api/types";
import { clusterDefects, type Finding } from "@/lib/defects";
import { useRobotLink } from "@/lib/robot/robot-link";
import { useApi } from "./use-api";

export interface RopeHistory {
  rope: Rope | undefined;
  /** Newest first. */
  runs: Run[];
  /** Raw detections, one entry per row the robot stored. */
  defectsByRun: Record<string, Defect[]>;
  /** The same detections grouped into flaws, sorted by position. This is what the UI shows. */
  findingsByRun: Record<string, Finding[]>;
}

async function loadRopeHistory(ropeId: string): Promise<RopeHistory> {
  const [ropes, runs] = await Promise.all([api.ropes.list(), api.runs.list(ropeId)]);
  const defectLists = await Promise.all(runs.map((run) => api.defects.list(run.id)));

  return {
    rope: ropes.find((r) => r.id === ropeId),
    runs: [...runs].sort((a, b) => b.started_at.localeCompare(a.started_at)),
    defectsByRun: Object.fromEntries(runs.map((run, i) => [run.id, defectLists[i]])),
    findingsByRun: Object.fromEntries(runs.map((run, i) => [run.id, clusterDefects(defectLists[i])])),
  };
}

/** A rope with all of its runs and the defects of every run. */
export function useRopeHistory(ropeId: string | null, options?: { refreshMs?: number }) {
  return useApi(ropeId ? `rope-history:${ropeId}` : null, () => loadRopeHistory(ropeId!), options);
}

/**
 * The rope/run currently selected on the server (GET /api/current).
 * Reloads whenever the server announces a `current_changed` event.
 */
export function useCurrentSelection() {
  const { currentVersion } = useRobotLink();
  return useApi(`current:${currentVersion}`, api.current.get);
}

/** Most recent run that has finished, if any. */
export function lastFinishedRun(runs: Run[]): Run | undefined {
  return runs.find((run) => run.finished_at !== null);
}
