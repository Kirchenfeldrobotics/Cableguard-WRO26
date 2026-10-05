import type { Defect, DefectKind } from "@/lib/api/types";

export type Tone = "danger" | "warning" | "neutral";

/**
 * The backend has no severity yet, so defects are coloured by detector class: local faults
 * (lf) use the "action" red, loss of metallic area (lma) the "monitor" amber.
 */
export function kindTone(kind: DefectKind): Tone {
  return kind === "lf" ? "danger" : "warning";
}

export function byPosition(a: Defect, b: Defect): number {
  return a.pos_to_start - b.pos_to_start;
}

/**
 * The robot stores one row per detection: it runs the detector every two seconds on both
 * cameras and never merges the results, so one flaw on the rope arrives as a handful of rows
 * a few centimetres apart. Detections of the same kind closer than this are shown as one
 * finding. Wider than the robot travels between two detector runs, narrower than the gap
 * that would merge two real flaws.
 */
export const CLUSTER_GAP_M = 0.5;

/** Two findings closer than this are treated as the same flaw across runs. */
export const MATCH_TOLERANCE_M = 1.5;

/** One flaw on the rope: every detection that landed on the same spot. */
export interface Finding {
  /** Highest-confidence detection of the group, it identifies the finding and opens its page. */
  best: Defect;
  kind: DefectKind;
  /** Position of `best`, the clearest look at the flaw. */
  pos: number;
  /** How far the detections spread along the rope. */
  from: number;
  to: number;
  /** Best confidence of the group, null when no detection carries one. */
  confidence: number | null;
  /**
   * True once every detection of the group is reviewed. A detection that joins a reviewed
   * finding later, during a live run, opens it again.
   */
  reviewed: boolean;
  /** Sorted by position. */
  detections: Defect[];
}

function toFinding(kind: DefectKind, group: Defect[]): Finding {
  const best = group.reduce((a, b) => ((b.confidence ?? 0) > (a.confidence ?? 0) ? b : a));
  const scored = group.map((d) => d.confidence).filter((c): c is number => c !== null);

  return {
    best,
    kind,
    pos: best.pos_to_start,
    from: group[0].pos_to_start,
    to: group[group.length - 1].pos_to_start,
    confidence: scored.length ? Math.max(...scored) : null,
    reviewed: group.every((d) => d.reviewed),
    detections: group,
  };
}

/**
 * Groups the detections of one run into findings, sorted by position. Kinds are grouped
 * separately: wear and a broken wire at the same spot are two different flaws.
 */
export function clusterDefects(defects: Defect[]): Finding[] {
  const byKind = new Map<DefectKind, Defect[]>();
  for (const defect of defects) {
    const list = byKind.get(defect.kind);
    if (list) list.push(defect);
    else byKind.set(defect.kind, [defect]);
  }

  const findings: Finding[] = [];
  for (const [kind, list] of byKind) {
    let group: Defect[] = [];
    for (const defect of [...list].sort(byPosition)) {
      const previous = group[group.length - 1];
      if (previous && defect.pos_to_start - previous.pos_to_start > CLUSTER_GAP_M) {
        findings.push(toFinding(kind, group));
        group = [];
      }
      group.push(defect);
    }
    if (group.length) findings.push(toFinding(kind, group));
  }

  return findings.sort((a, b) => a.pos - b.pos);
}

function hasMatch(list: Finding[], finding: Finding): boolean {
  return list.some((f) => f.kind === finding.kind && Math.abs(f.pos - finding.pos) <= MATCH_TOLERANCE_M);
}

export interface RunComparison {
  /** In the compared run but not in the reference run. */
  added: Finding[];
  /** In both runs. */
  unchanged: Finding[];
  /** In the reference run but not in the compared run. */
  resolved: Finding[];
}

export function compareRuns(reference: Finding[], compared: Finding[]): RunComparison {
  return {
    added: compared.filter((f) => !hasMatch(reference, f)),
    unchanged: compared.filter((f) => hasMatch(reference, f)),
    resolved: reference.filter((f) => !hasMatch(compared, f)),
  };
}

/** The finding in `list` closest to `finding`, within the match tolerance. */
export function findMatch(list: Finding[], finding: Finding): Finding | undefined {
  let best: Finding | undefined;
  for (const f of list) {
    if (f.kind !== finding.kind) continue;
    const gap = Math.abs(f.pos - finding.pos);
    if (gap <= MATCH_TOLERANCE_M && (!best || gap < Math.abs(best.pos - finding.pos))) {
      best = f;
    }
  }
  return best;
}

/** How many of the findings the operator has not looked at yet. */
export function countUnreviewed(findings: Finding[]): number {
  return findings.filter((f) => !f.reviewed).length;
}

/** The finding a single detection belongs to. */
export function findingOf(findings: Finding[], defect: Defect): Finding | undefined {
  return findings.find((f) => f.detections.some((d) => d.id === defect.id));
}
