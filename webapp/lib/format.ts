import type { DefectKind, Run } from "@/lib/api/types";

/** Placeholder for values the backend does not provide yet. */
export const NOT_AVAILABLE = "—";

const metres = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatMetres(value: number | null | undefined): string {
  return value == null ? NOT_AVAILABLE : `${metres.format(value)} m`;
}

/** `0.42 m` to the nearest object. Null is a reading as well: nothing within the sensor's range. */
export function formatDistance(value: number | null): string {
  return value === null ? "nothing in range" : `${value.toFixed(2)} m`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return NOT_AVAILABLE;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

/** `0.11 m/s forward`. The sign of `value` is the drive direction. */
export function formatDriveSpeed(value: number | null | undefined): string {
  if (value == null) return NOT_AVAILABLE;
  const direction = value > 0 ? " forward" : value < 0 ? " reverse" : "";
  return `${Math.abs(value).toFixed(2)} m/s${direction}`;
}

/** `1.8 /s`, how often the detector runs a frame from both cameras, at both ring angles. */
export function formatDetectRate(fps: number | null | undefined): string {
  return fps == null ? NOT_AVAILABLE : `${fps.toFixed(1)} /s`;
}

const pad = (n: number) => String(n).padStart(2, "0");

/** `2026-09-04` */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return NOT_AVAILABLE;
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** `2026-09-04 06:12` */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return NOT_AVAILABLE;
  const d = new Date(iso);
  return `${formatDate(iso)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function formatRunDuration(run: Run): string {
  if (!run.finished_at) return "in progress";
  const minutes = Math.round(
    (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 60_000,
  );
  return `${minutes} min`;
}

export function isRunActive(run: Run | undefined): boolean {
  return !!run && run.finished_at === null;
}

/**
 * The two buckets the robot sorts its detector classes into. The model knows eight classes
 * and seven of them are local faults, so the bucket is the severity, not the flaw: use
 * `defectClassLabel` wherever the actual flaw matters.
 */
export function defectTypeLabel(kind: DefectKind): string {
  return kind === "lf" ? "Local fault" : "Loss of metallic area";
}

/** Classes whose name does not read well once the underscores are gone. */
const CLASS_LABELS: Record<string, string> = {
  bird_caging: "Birdcaging",
  unknown_defect: "Unclassified",
};

/**
 * `broken_wire` becomes `Broken wire`. The class list comes from whatever model is on the
 * robot, so anything a retrained model adds still gets a readable name.
 */
export function defectClassLabel(label: string | null | undefined): string {
  if (!label) return NOT_AVAILABLE;
  if (CLASS_LABELS[label]) return CLASS_LABELS[label];
  const words = label.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** `82%`. The detector drops anything at or below 50%, so the scale starts there. */
export function formatConfidence(value: number | null | undefined): string {
  return value == null ? NOT_AVAILABLE : `${Math.round(value * 100)}%`;
}

/** The robot numbers its cameras, the operator knows them as A and B. */
export function formatCamera(cam: number | null | undefined): string {
  if (cam == null) return NOT_AVAILABLE;
  return `Camera ${String.fromCharCode(65 + cam)}`;
}

/** `12.4 m` for one detection, `12.1 - 12.7 m` for a group that spreads. */
export function formatSpan(from: number, to: number): string {
  return to - from < 0.05 ? formatMetres(from) : `${metres.format(from)} - ${formatMetres(to)}`;
}

/** Short, readable form of a UUID for headings and tables. */
export function shortId(id: string): string {
  return id.length > 12 ? id.slice(0, 8).toUpperCase() : id;
}

export function formatAgo(ms: number): string {
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)} s ago`;
  const m = Math.floor(s / 60);
  return m < 60 ? `${m} min ago` : `${Math.floor(m / 60)} h ago`;
}
