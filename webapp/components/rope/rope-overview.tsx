"use client";

import { memo, useRef } from "react";

import { cn } from "@/lib/cn";
import { formatMetres } from "@/lib/format";

import { INSET_PX, markFill, type StripMark } from "./strip-layout";

/** Narrowest the frame may get, so it can still be grabbed on a rope of several kilometres. */
const FRAME_MIN_PX = 14;

/** Screens the strip moves per key press. */
const KEY_SHIFT: Record<string, number | undefined> = {
  ArrowLeft: -0.1,
  ArrowRight: 0.1,
  PageUp: -1,
  PageDown: 1,
};

function share(m: number, length: number): string {
  return `${(Math.max(0, Math.min(length, m)) / length) * 100}%`;
}

/** Kept apart from the frame, which moves with every scrolled pixel while the marks stay. */
const OverviewMarks = memo(function OverviewMarks({
  marks,
  length,
}: {
  marks: StripMark[];
  length: number;
}) {
  return (
    <>
      {marks.map((mark) => (
        <div
          key={mark.id}
          style={{ left: share(mark.pos, length) }}
          className={cn("absolute top-1/2 h-2 w-0.5 -translate-x-1/2 -translate-y-1/2", markFill(mark))}
        />
      ))}
    </>
  );
});

/**
 * The whole rope in one line under a strip that scrolls: a tick per mark and a frame around
 * the part on screen. It is the strip's scrollbar, dragging or clicking it moves the strip.
 */
export function RopeOverview({
  length,
  marks,
  livePos,
  from,
  to,
  controls,
  onSeek,
  onShift,
}: {
  length: number;
  marks: StripMark[];
  livePos?: number | null;
  /** Metres of rope on screen. */
  from: number;
  to: number;
  /** Id of the strip it scrolls. */
  controls: string;
  /** Centres the strip on this metre. */
  onSeek: (m: number) => void;
  /** Moves the strip by this many screens. */
  onShift: (screens: number) => void;
}) {
  // Where on the frame the pointer took hold, so the frame does not jump when dragged.
  const grab = useRef(0);
  const centre = (from + to) / 2;

  const metreAt = (e: React.PointerEvent<HTMLDivElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    return ((e.clientX - box.left) / box.width) * length;
  };

  return (
    <div
      role="scrollbar"
      tabIndex={0}
      aria-label="Part of the rope on screen"
      aria-controls={controls}
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={Math.round(length)}
      aria-valuenow={Math.round(from)}
      aria-valuetext={`${formatMetres(from)} to ${formatMetres(to)}`}
      onPointerDown={(e) => {
        const m = metreAt(e);
        grab.current = m >= from && m <= to ? m - centre : 0;
        e.currentTarget.setPointerCapture(e.pointerId);
        onSeek(m - grab.current);
      }}
      onPointerMove={(e) => {
        if (e.currentTarget.hasPointerCapture(e.pointerId)) onSeek(metreAt(e) - grab.current);
      }}
      onKeyDown={(e) => {
        const shift = KEY_SHIFT[e.key];
        if (shift !== undefined) onShift(shift);
        else if (e.key === "Home") onSeek(0);
        else if (e.key === "End") onSeek(length);
        else return;
        e.preventDefault();
      }}
      style={{ marginInline: INSET_PX }}
      // Taller than the line it draws, so a finger can take hold of it.
      className="relative mt-1.5 h-6 cursor-pointer touch-pan-y before:absolute before:inset-x-0 before:top-1/2 before:h-2 before:-translate-y-1/2 before:rounded-full before:bg-white"
    >
      <OverviewMarks marks={marks} length={length} />

      {typeof livePos === "number" && (
        <div
          style={{ left: share(livePos, length) }}
          className="absolute top-1/2 h-3.5 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-[1px] bg-ink"
        />
      )}

      <div
        style={{
          left: share(centre, length),
          width: `max(${((to - from) / length) * 100}%, ${FRAME_MIN_PX}px)`,
        }}
        className="absolute top-1/2 h-4 -translate-x-1/2 -translate-y-1/2 rounded-[5px] border-2 border-ink"
      />
    </div>
  );
}
