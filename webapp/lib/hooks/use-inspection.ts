"use client";

import { useMemo } from "react";

import { api } from "@/lib/api/client";
import type { Defect, Rope, Run } from "@/lib/api/types";
import { CLUSTER_GAP_M, clusterDefects, type Finding } from "@/lib/defects";
import { useRobotLink } from "@/lib/robot/robot-link";
import { useApi, type ApiState } from "./use-api";
import { useRobotSettings } from "./use-settings";

/** A rope as the server stores it. */
export interface StoredHistory {
  rope: Rope | undefined;
  /** Newest first. */
  runs: Run[];
  /** Raw detections, one entry per row the robot stored. */
  defectsByRun: Record<string, Defect[]>;
}

export interface RopeHistory extends StoredHistory {
  /** The same detections grouped into flaws, sorted by position. This is what the UI shows. */
  findingsByRun: Record<string, Finding[]>;
}

async function loadRopeHistory(ropeId: string): Promise<StoredHistory> {
  const [ropes, runs] = await Promise.all([api.ropes.list(), api.runs.list(ropeId)]);
  const defectLists = await Promise.all(runs.map((run) => api.defects.list(run.id)));

  return {
    rope: ropes.find((r) => r.id === ropeId),
    runs: [...runs].sort((a, b) => b.started_at.localeCompare(a.started_at)),
    defectsByRun: Object.fromEntries(runs.map((run, i) => [run.id, defectLists[i]])),
  };
}

/** The detections of every run grouped into findings, at most `gap` metres from one to the next. */
export function withFindings(stored: StoredHistory, gap: number): RopeHistory {
  return {
    ...stored,
    findingsByRun: Object.fromEntries(
      Object.entries(stored.defectsByRun).map(([runId, defects]) => [runId, clusterDefects(defects, gap)]),
    ),
  };
}

/**
 * A rope with all of its runs and the defects of every run.
 *
 * Grouping is done here and not on the server: the distance is the operator's setting, and a
 * change regroups every run on screen at once, the stored ones included.
 */
export function useRopeHistory(
  ropeId: string | null,
  options?: { refreshMs?: number },
): ApiState<RopeHistory> {
  const stored = useApi(ropeId ? `rope-history:${ropeId}` : null, () => loadRopeHistory(ropeId!), options);
  const settings = useRobotSettings();

  // Nothing is grouped before the server has said what the distance is, or the findings
  // would be drawn once with the default and jump. A server that cannot say gets the
  // default, and so does one from before the setting, which sends no such value.
  const chosen: number | undefined = settings.data?.values.finding_gap_m;
  const gap = settings.data ? (chosen ?? CLUSTER_GAP_M) : settings.error ? CLUSTER_GAP_M : null;

  const data = useMemo(
    () => (stored.data && gap !== null ? withFindings(stored.data, gap) : undefined),
    [stored.data, gap],
  );

  return { ...stored, data, loading: stored.loading || (ropeId !== null && gap === null) };
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
