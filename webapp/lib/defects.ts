import type { Defect, DefectKind } from "@/lib/api/types";

export type Tone = "danger" | "warning" | "neutral";

/**
 * The backend has no severity yet, so defects are coloured by detector class:
 * broken wires (lf) use the "action" red, corrosion (lma) the "monitor" amber.
 */
export function kindTone(kind: DefectKind): Tone {
  return kind === "lf" ? "danger" : "warning";
}

/** Two detections closer than this are treated as the same defect. */
export const MATCH_TOLERANCE_M = 1.5;

function hasMatch(list: Defect[], defect: Defect): boolean {
  return list.some((d) => Math.abs(d.pos_to_start - defect.pos_to_start) <= MATCH_TOLERANCE_M);
}

export interface RunComparison {
  /** In the compared run but not in the reference run. */
  added: Defect[];
  /** In both runs. */
  unchanged: Defect[];
  /** In the reference run but not in the compared run. */
  resolved: Defect[];
}

export function compareRuns(reference: Defect[], compared: Defect[]): RunComparison {
  return {
    added: compared.filter((d) => !hasMatch(reference, d)),
    unchanged: compared.filter((d) => hasMatch(reference, d)),
    resolved: reference.filter((d) => !hasMatch(compared, d)),
  };
}

/** The detection in `list` closest to `defect`, within the match tolerance. */
export function findMatch(list: Defect[], defect: Defect): Defect | undefined {
  let best: Defect | undefined;
  for (const d of list) {
    const gap = Math.abs(d.pos_to_start - defect.pos_to_start);
    if (gap <= MATCH_TOLERANCE_M && (!best || gap < Math.abs(best.pos_to_start - defect.pos_to_start))) {
      best = d;
    }
  }
  return best;
}

export function byPosition(a: Defect, b: Defect): number {
  return a.pos_to_start - b.pos_to_start;
}
