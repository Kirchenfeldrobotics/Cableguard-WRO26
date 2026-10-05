import type { Tone } from "@/lib/defects";

export interface StripMark {
  id: string;
  /** Metres from the start of the rope, the clearest detection of the finding. */
  pos: number;
  /** Extent of the finding. Equal to `pos` when it is a single detection. */
  from: number;
  to: number;
  tone: Tone;
  /** 0..1, fades the mark so a weak detection does not read like a certain one. */
  confidence?: number | null;
  /** Comparison state: new marks are wider, unchanged ones are grey. */
  state?: "new" | "unchanged";
  href?: string;
  title?: string;
}

/**
 * Pixels one metre of rope gets, at least: about 100 m across a desktop panel. Findings of
 * one type are never closer than CLUSTER_GAP_M (lib/defects.ts), and at this scale that gap
 * is wider than a mark, so two of them cannot land on each other on any screen.
 */
export const PX_PER_M = 10;

/** Room on either side of the rope, so a mark at its very start or end is not cut off. */
export const INSET_PX = 24;

/** Narrowest a mark may get, so a single detection stays clickable. */
export const MIN_WIDTH_PX: Record<string, number> = { new: 5, unchanged: 3, point: 4 };

/** Gap the scale labels keep between them, wide enough for `1,850`. */
const LABEL_GAP_PX = 64;

const toneFill: Record<Tone, string> = {
  danger: "bg-danger",
  warning: "bg-warning",
  neutral: "bg-text-subtle",
};

/** Colour of a mark. In a comparison, the ones the reference run has too are grey. */
export function markFill(mark: StripMark): string {
  return mark.state === "unchanged" ? "bg-mark-muted" : toneFill[mark.tone];
}

export interface Tick {
  m: number;
  label: string;
}

/**
 * Scale labels between `from` and `to` metres. The step is the smallest of 1, 2, 5, 10, ...
 * that keeps them apart at this scale, and the last ones give way to the length label that
 * closes the scale.
 */
export function scaleTicks(length: number, scale: number, from: number, to: number): Tick[] {
  const least = LABEL_GAP_PX / scale;
  const power = 10 ** Math.floor(Math.log10(least));
  const step = ([1, 2, 5].find((factor) => factor * power >= least) ?? 10) * power;
  const digits = Math.max(0, -Math.floor(Math.log10(step)));
  const format = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  const ticks: Tick[] = [];
  const last = Math.floor(Math.min(to, length - least) / step);
  for (let i = Math.max(0, Math.ceil(from / step)); i <= last; i++) {
    ticks.push({ m: i * step, label: format.format(i * step) });
  }
  return ticks;
}

type Lane = "upper" | "lower";

export interface MarkBox {
  mark: StripMark;
  /** Set where a mark of the other type sits on the same spot: the two share the bar height. */
  lane: Lane | null;
  /** Pixels of click margin the mark may take before it reaches its neighbour, null for all of it. */
  room: number | null;
}

interface Box extends MarkBox {
  left: number;
  right: number;
}

/** Two marks are in each other's way unless they sit in opposite halves of the bar. */
function clash(a: Box, b: Box): boolean {
  return !a.lane || !b.lane || a.lane === b.lane;
}

/**
 * Decides how the marks share the bar, sorted along the rope. `scale` is pixels per metre.
 *
 * Marks of one type never meet (see PX_PER_M), so two that do are a local fault and a loss
 * of metallic area on the same spot. They split the bar height, the fault on top.
 */
export function layoutMarks(marks: StripMark[], length: number, scale: number): MarkBox[] {
  const px = (m: number) => Math.max(0, Math.min(length, m)) * scale;

  const boxes: Box[] = marks
    .map((mark): Box => {
      const centre = (px(mark.from) + px(mark.to)) / 2;
      const half = Math.max(px(mark.to) - px(mark.from), MIN_WIDTH_PX[mark.state ?? "point"]) / 2;
      return { mark, lane: null, room: null, left: centre - half, right: centre + half };
    })
    .sort((a, b) => a.left - b.left);

  const laneOf = (box: Box): Lane => (box.mark.tone === "danger" ? "upper" : "lower");
  boxes.forEach((box, i) => {
    for (let j = i + 1; j < boxes.length && boxes[j].left < box.right + 1; j++) {
      if (boxes[j].mark.tone === box.mark.tone) continue;
      box.lane = laneOf(box);
      boxes[j].lane = laneOf(boxes[j]);
    }
  });

  // The click margin of a mark stops halfway to the nearest mark it could cover. The boxes
  // are sorted by their left edge: the nearest one after a box is the next that clashes
  // with it, the nearest one before it is whichever earlier one reaches furthest.
  const reach = { full: -Infinity, upper: -Infinity, lower: -Infinity };
  boxes.forEach((box, i) => {
    let gap = box.left - reach[box.lane ?? "full"];
    for (let j = i + 1; j < boxes.length; j++) {
      if (!clash(box, boxes[j])) continue;
      gap = Math.min(gap, boxes[j].left - box.right);
      break;
    }
    if (Number.isFinite(gap)) box.room = Math.max(0, gap / 2);

    reach.full = Math.max(reach.full, box.right);
    if (box.lane !== "lower") reach.upper = Math.max(reach.upper, box.right);
    if (box.lane !== "upper") reach.lower = Math.max(reach.lower, box.right);
  });

  return boxes;
}
