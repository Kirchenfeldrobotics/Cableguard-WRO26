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
 * The robot stores one row per detection and never merges them. It photographs the rope from
 * four sides and moves on by one photo of rope per cycle, so one flaw arrives as a handful
 * of rows a few centimetres apart, each at the position the robot stood at when the photo was
 * taken. Detections of the same kind nearer to each other than this are shown as one finding.
 *
 * The operator sets the distance (`finding_gap_m`, shared/comm_protocols/settings.py), and
 * this is that setting's default, for a server from before it had one. A little more than
 * the 6 cm of rope one photo covers: photos that touch or overlap are one finding. It was
 * 0.5 m while the detector ran every two seconds at a speed the operator chose, which made
 * one finding of any two flaws on a short rope.
 */
export const CLUSTER_GAP_M = 0.08;

/**
 * How far apart one flaw may be found in two runs. Each run counts from where the robot was
 * put on the rope, and the count drifts with every metre the wheel slips: an allowance for
 * the start, and a share of the distance driven on top of it. The share is a guess, slip has
 * not been measured. The cap is what every position was given before the allowance grew with
 * it, which on a rope shorter than that made one flaw of everything.
 */
const MATCH_START_M = 0.25;
const MATCH_PER_METRE = 0.01;
const MATCH_MAX_M = 1.5;

export function matchTolerance(pos: number): number {
  return Math.min(MATCH_MAX_M, MATCH_START_M + MATCH_PER_METRE * Math.max(0, pos));
}

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
 * Groups the detections of one run into findings, sorted by position. A finding ends where
 * the next detection of its kind is more than `gap` metres on. Kinds are grouped separately:
 * wear and a broken wire at the same spot are two different flaws.
 */
export function clusterDefects(defects: Defect[], gap: number = CLUSTER_GAP_M): Finding[] {
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
      if (previous && defect.pos_to_start - previous.pos_to_start > gap) {
        findings.push(toFinding(kind, group));
        group = [];
      }
      group.push(defect);
    }
    if (group.length) findings.push(toFinding(kind, group));
  }

  return findings.sort((a, b) => a.pos - b.pos);
}

/** A flaw found at `a` in one run can be the one found at `b` in the other. */
function withinReach(a: Finding, b: Finding): boolean {
  return Math.abs(a.pos - b.pos) <= matchTolerance((a.pos + b.pos) / 2);
}

/** Pairs two lists of one kind, both sorted by position, and notes each partner in `partners`. */
function pairInOrder(a: Finding[], b: Finding[], partners: Map<Finding, Finding>): void {
  // pairs[i][j] and apart[i][j]: the best pairing of the first i of a with the first j of b,
  // most pairs first and the least metres between partners among those. step[i][j] is how
  // it was reached: the last of a left alone, the last of b left alone, or the two paired.
  const cols = b.length + 1;
  const pairs = new Uint32Array((a.length + 1) * cols);
  const apart = new Float64Array((a.length + 1) * cols);
  const step = new Uint8Array((a.length + 1) * cols);
  const SKIP_A = 0;
  const SKIP_B = 1;
  const PAIR = 2;

  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const here = i * cols + j;
      const skipA = (i - 1) * cols + j;
      const skipB = i * cols + j - 1;
      const both = (i - 1) * cols + j - 1;

      let from = skipA;
      step[here] = SKIP_A;
      if (pairs[skipB] > pairs[from] || (pairs[skipB] === pairs[from] && apart[skipB] < apart[from])) {
        from = skipB;
        step[here] = SKIP_B;
      }
      pairs[here] = pairs[from];
      apart[here] = apart[from];

      if (!withinReach(a[i - 1], b[j - 1])) continue;
      const metres = apart[both] + Math.abs(a[i - 1].pos - b[j - 1].pos);
      if (pairs[both] + 1 > pairs[here] || (pairs[both] + 1 === pairs[here] && metres < apart[here])) {
        pairs[here] = pairs[both] + 1;
        apart[here] = metres;
        step[here] = PAIR;
      }
    }
  }

  let i = a.length;
  let j = b.length;
  while (i > 0 && j > 0) {
    const taken = step[i * cols + j];
    if (taken === PAIR) {
      partners.set(a[i - 1], b[j - 1]);
      partners.set(b[j - 1], a[i - 1]);
    }
    if (taken !== SKIP_B) i--;
    if (taken !== SKIP_A) j--;
  }
}

/**
 * Pairs the findings of two runs: the same flaw, found twice. Returns the partner of every
 * finding that has one, findings of both runs alike.
 *
 * A flaw is paired at most once and flaws keep their order along the rope, so pairs never
 * cross. Of all such pairings the one with the most pairs is taken, and among those the one
 * whose partners lie closest. Counting a finding as known because any finding of its kind is
 * within reach is not enough: a new flaw next to an old one would never show as new.
 */
export function matchFindings(reference: Finding[], compared: Finding[]): Map<Finding, Finding> {
  const partners = new Map<Finding, Finding>();
  const byPos = (a: Finding, b: Finding) => a.pos - b.pos;

  for (const kind of new Set([...reference, ...compared].map((f) => f.kind))) {
    pairInOrder(
      reference.filter((f) => f.kind === kind).sort(byPos),
      compared.filter((f) => f.kind === kind).sort(byPos),
      partners,
    );
  }
  return partners;
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
  const partners = matchFindings(reference, compared);
  return {
    added: compared.filter((f) => !partners.has(f)),
    unchanged: compared.filter((f) => partners.has(f)),
    resolved: reference.filter((f) => !partners.has(f)),
  };
}

/** How many of the findings the operator has not looked at yet. */
export function countUnreviewed(findings: Finding[]): number {
  return findings.filter((f) => !f.reviewed).length;
}

/** The finding a single detection belongs to. */
export function findingOf(findings: Finding[], defect: Defect): Finding | undefined {
  return findings.find((f) => f.detections.some((d) => d.id === defect.id));
}
