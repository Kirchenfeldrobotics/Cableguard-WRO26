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

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return NOT_AVAILABLE;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
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

/** Human label used by the design for each detector class. */
export function defectTypeLabel(kind: DefectKind): string {
  return kind === "lf" ? "Broken wire" : "Corrosion";
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
