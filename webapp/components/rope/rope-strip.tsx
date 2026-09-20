import Link from "next/link";

import { cn } from "@/lib/cn";
import type { Tone } from "@/lib/defects";
import { formatMetres } from "@/lib/format";

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

const markColor: Record<Tone, string> = {
  danger: "bg-danger",
  warning: "bg-warning",
  neutral: "bg-text-subtle",
};

/** Narrowest a mark may get, so a single detection stays clickable. */
const minWidthPx: Record<string, number> = { new: 5, unchanged: 3, point: 4 };

/** Unrolled rope: metre scale on top, defect marks and optional live position on the bar. */
export function RopeStrip({
  length,
  marks,
  livePos,
}: {
  length: number | null;
  marks: StripMark[];
  livePos?: number | null;
}) {
  if (!length || length <= 0) {
    return (
      <div className="flex h-[70px] items-center justify-center rounded-[8px] bg-white/60 text-[13px] text-text-subtle">
        Rope length is not set, the strip cannot be scaled.
      </div>
    );
  }

  const share = (m: number) => (Math.max(0, Math.min(length, m)) / length) * 100;
  const pct = (m: number) => `${share(m)}%`;
  const step = length > 1600 ? 500 : 250;
  const ticks: { left: string; label: string }[] = [];
  for (let m = 0; m <= length - step * 0.4; m += step) {
    ticks.push({ left: pct(m), label: m.toLocaleString("en-US") });
  }
  ticks.push({ left: pct(length), label: formatMetres(length) });

  return (
    <div className="w-full">
      <div className="relative mx-6 h-3.5">
        {ticks.map((t) => (
          <div
            key={t.label}
            style={{ left: t.left }}
            className="absolute top-0 -translate-x-1/2 font-mono text-[11px] leading-none whitespace-nowrap text-text-subtle"
          >
            {t.label}
          </div>
        ))}
      </div>

      <div className="relative h-[34px] rounded-[8px] bg-surface">
        <div className="absolute inset-y-0 inset-x-6">
          {marks.map((mark) => {
            // A finding that spreads over the rope is drawn over its whole extent, a single
            // detection collapses to the minimum width.
            const spread = share(mark.to) - share(mark.from);
            const floor = minWidthPx[mark.state ?? "point"];
            const bar = (
              <div
                style={{
                  width: `max(${spread}%, ${floor}px)`,
                  // Grey comparison marks are muted already, fading them twice hides them.
                  opacity:
                    mark.state === "unchanged" || mark.confidence == null
                      ? undefined
                      : 0.45 + 0.55 * mark.confidence,
                }}
                className={cn(
                  "h-6 rounded-[3px]",
                  mark.state === "unchanged" ? "bg-mark-muted" : markColor[mark.tone],
                )}
              />
            );
            const className = "absolute top-0 flex h-[34px] -translate-x-1/2 items-center justify-center px-1.5";
            const title = mark.title ?? formatMetres(mark.pos);
            const left = pct((mark.from + mark.to) / 2);
            return mark.href ? (
              <Link key={mark.id} href={mark.href} title={title} style={{ left }} className={className}>
                {bar}
              </Link>
            ) : (
              <div key={mark.id} title={title} style={{ left }} className={className}>
                {bar}
              </div>
            );
          })}

          {typeof livePos === "number" && (
            <div
              aria-label={`Robot at ${formatMetres(livePos)}`}
              style={{ left: pct(livePos) }}
              className="absolute -top-[5px] h-11 w-0.5 rounded-[1px] bg-ink"
            />
          )}
        </div>
      </div>
    </div>
  );
}
