"use client";

import Link from "next/link";
import { createContext, memo, useContext, useEffect, useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import { formatMetres } from "@/lib/format";

import { RopeOverview } from "./rope-overview";
import {
  INSET_PX,
  MIN_WIDTH_PX,
  PX_PER_M,
  layoutMarks,
  markFill,
  scaleTicks,
  type MarkBox,
  type StripMark,
} from "./strip-layout";

export type { StripMark };

/** The detector keeps nothing at or below 50%, so the fade spans 50-100% rather than 0-100%. */
const CONFIDENCE_FLOOR = 0.5;

/** How near the edge of the screen the robot may get before the strip moves on, as a share of the screen. */
const FOLLOW_MARGIN = 0.1;

/** How long the strip is left alone after the operator last moved it, before it may follow the robot again. */
const FOLLOW_RESUME_MS = 1000;

/** The strip glides to a new position, unless the system is set to show less motion. */
function glide(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

/** Strips that scroll as one. */
interface StripGroup {
  join: (strip: HTMLElement) => () => void;
  /** Brings the other strips to where this one has been scrolled. */
  align: (strip: HTMLElement) => void;
}

function createGroup(): StripGroup {
  const strips = new Set<HTMLElement>();
  return {
    join(strip) {
      strips.add(strip);
      return () => {
        strips.delete(strip);
      };
    },
    align(strip) {
      for (const other of strips) {
        // Moving a strip fires its own scroll event, which lands here again. Only a real
        // difference is passed on, or the strips would never settle.
        if (other !== strip && Math.abs(other.scrollLeft - strip.scrollLeft) >= 1) {
          other.scrollLeft = strip.scrollLeft;
        }
      }
    },
  };
}

const GroupContext = createContext<StripGroup | null>(null);

/** The strips inside scroll together, for two runs of one rope drawn above each other. */
export function RopeStripSync({ children }: { children: React.ReactNode }) {
  const [group] = useState(createGroup);
  return <GroupContext.Provider value={group}>{children}</GroupContext.Provider>;
}

/**
 * Unrolled rope: metre scale on top, defect marks and optional live position on the bar.
 * Drawn to scale (PX_PER_M), so a rope longer than the screen scrolls sideways and gets an
 * overview of its whole length underneath.
 */
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
      <div className="flex h-[70px] items-center justify-center rounded-row bg-white text-[13px] text-text-subtle">
        Rope length not set.
      </div>
    );
  }

  return <Strip length={length} marks={marks} livePos={livePos} />;
}

function Strip({
  length,
  marks,
  livePos,
}: {
  length: number;
  marks: StripMark[];
  livePos?: number | null;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const id = useId();
  const group = useContext(GroupContext);
  // Width of the part on screen, 0 until it has been measured, and how far it is scrolled.
  const [width, setWidth] = useState(0);
  const [left, setLeft] = useState(0);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const observer = new ResizeObserver(() => setWidth(el.clientWidth));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const el = scroller.current;
    if (!el || !group) return;
    return group.join(el);
  }, [group]);

  // A rope shorter than the screen is stretched to fill it, a longer one keeps PX_PER_M.
  const scale = Math.max(length * PX_PER_M, width - 2 * INSET_PX) / length;
  const scrolls = width > 0 && length * PX_PER_M + 2 * INSET_PX > width + 1;
  const clamp = (m: number) => Math.max(0, Math.min(length, m));
  const pct = (m: number) => `${(clamp(m) / length) * 100}%`;
  const metreAt = (px: number) => clamp((px - INSET_PX) / scale);

  // Scale labels are only drawn for the screen in view and the one on either side of it.
  const screen = width > 0 ? Math.floor(left / width) : 0;
  const ticks = useMemo(
    () =>
      scaleTicks(
        length,
        scale,
        ((screen - 1) * width - INSET_PX) / scale,
        ((screen + 2) * width - INSET_PX) / scale,
      ),
    [length, scale, screen, width],
  );
  const boxes = useMemo(() => layoutMarks(marks, length, scale), [marks, length, scale]);

  // Live view: the strip moves on when the robot nears the edge of the screen. While the
  // operator has hold of the strip it stays where they put it, and it only follows again
  // once they have let go of it with the robot on screen.
  const following = useRef(true);
  const touching = useRef(false);
  const resume = useRef<ReturnType<typeof setTimeout>>(undefined);
  const robotPx = typeof livePos === "number" ? INSET_PX + clamp(livePos) * scale : null;
  const robot = useRef(robotPx);
  useEffect(() => {
    robot.current = robotPx;
  });
  useEffect(() => () => clearTimeout(resume.current), []);

  const resumeSoon = () => {
    clearTimeout(resume.current);
    resume.current = setTimeout(() => {
      const el = scroller.current;
      const px = robot.current;
      if (!el || touching.current) return;
      following.current = px === null || (px >= el.scrollLeft && px <= el.scrollLeft + el.clientWidth);
    }, FOLLOW_RESUME_MS);
  };
  const hold = () => {
    following.current = false;
    resumeSoon();
  };

  useEffect(() => {
    const el = scroller.current;
    if (!el || !scrolls || robotPx === null || !following.current) return;
    const margin = width * FOLLOW_MARGIN;
    if (robotPx > el.scrollLeft + margin && robotPx < el.scrollLeft + width - margin) return;

    const target = Math.max(0, Math.min(el.scrollWidth - width, robotPx - width / 2));
    if (Math.abs(target - el.scrollLeft) < 1) return;
    // A glide only while the robot stays on screen through it. A browser does not run one
    // in a tab that is in the background, and the robot would drive out of sight meanwhile.
    const onScreen = robotPx >= el.scrollLeft && robotPx <= el.scrollLeft + width;
    el.scrollTo({ left: target, behavior: onScreen ? glide() : "auto" });
  }, [robotPx, scrolls, width]);

  return (
    <div
      className="w-full"
      onPointerDown={hold}
      onWheel={hold}
      onKeyDown={hold}
      onTouchStart={() => {
        touching.current = true;
        hold();
      }}
      onTouchEnd={() => {
        touching.current = false;
        resumeSoon();
      }}
      onTouchCancel={() => {
        touching.current = false;
        resumeSoon();
      }}
    >
      {/* The robot line and the focus ring of a mark reach past the bar. The padding keeps
          them from being cut off, the margin takes its height back. */}
      <div
        ref={scroller}
        id={id}
        onScroll={(e) => {
          const el = e.currentTarget;
          setLeft(el.scrollLeft);
          // Still moving under the operator's hand, or coasting after it.
          if (!following.current) resumeSoon();
          group?.align(el);
        }}
        className="-my-1.5 overflow-x-auto overscroll-x-contain py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        <div className="min-w-full" style={{ width: length * PX_PER_M + 2 * INSET_PX }}>
          <div className="relative h-3.5" style={{ marginInline: INSET_PX }}>
            {ticks.map((tick) => (
              <div key={tick.label} style={{ left: pct(tick.m) }} className={cn(labelClass, "-translate-x-1/2")}>
                {tick.label}
              </div>
            ))}
            {/* Centred on the end of the rope, as far as the room beside it allows. */}
            <div style={{ translate: `min(50%, ${INSET_PX}px)` }} className={cn(labelClass, "right-0")}>
              {formatMetres(length)}
            </div>
          </div>

          {/* The rope: white, so that it stands out from the grey panel a strip sits on. */}
          <div className="relative h-[34px] rounded-row bg-white">
            {/* Wider click margin on phones so a finger can hit a single detection. */}
            <div
              className="absolute inset-y-0 [--pad:10px] sm:[--pad:6px]"
              style={{ insetInline: INSET_PX }}
            >
              {width > 0 && <Marks boxes={boxes} length={length} />}

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
      </div>

      {scrolls && (
        <RopeOverview
          length={length}
          marks={marks}
          livePos={livePos}
          from={metreAt(left)}
          to={metreAt(left + width)}
          controls={id}
          onSeek={(m) => scroller.current?.scrollTo({ left: INSET_PX + m * scale - width / 2 })}
          onShift={(screens) => scroller.current?.scrollBy({ left: screens * width, behavior: glide() })}
        />
      )}
    </div>
  );
}

const labelClass =
  "absolute top-0 font-mono text-[11px] leading-none whitespace-nowrap text-text-subtle";

/** Kept apart from the strip, which renders again with every scrolled pixel while the marks stay. */
const Marks = memo(function Marks({ boxes, length }: { boxes: MarkBox[]; length: number }) {
  const share = (m: number) => (Math.max(0, Math.min(length, m)) / length) * 100;

  return (
    <>
      {boxes.map(({ mark, lane, room }) => {
        const bar = (
          <div
            style={{
              // Grey comparison marks are muted already, fading them twice hides them.
              opacity:
                mark.state === "unchanged" || mark.confidence == null
                  ? undefined
                  : 0.45 + 0.55 * Math.max(0, (mark.confidence - CONFIDENCE_FLOOR) / (1 - CONFIDENCE_FLOOR)),
            }}
            className={cn("w-full rounded-[3px]", lane ? "h-[11px]" : "h-6", markFill(mark))}
          />
        );
        // The box is as wide as the bar, the padding around it is the click margin. Two
        // marks on one spot each get half the height of the bar.
        const className = cn(
          "absolute box-content flex -translate-x-1/2 px-[var(--pad)]",
          lane === "upper"
            ? "top-0 h-4 items-end pb-px"
            : lane === "lower"
              ? "top-[17px] h-4 items-start pt-px"
              : "top-0 h-[34px] items-center",
        );
        const style = {
          left: `${share((mark.from + mark.to) / 2)}%`,
          // A finding that spreads over the rope is drawn over its whole extent, a single
          // detection collapses to the minimum width.
          width: `max(${share(mark.to) - share(mark.from)}%, ${MIN_WIDTH_PX[mark.state ?? "point"]}px)`,
          paddingInline: room === null ? undefined : `min(var(--pad), ${room}px)`,
        };
        const title = mark.title ?? formatMetres(mark.pos);

        return mark.href ? (
          <Link key={mark.id} href={mark.href} title={title} style={style} className={className}>
            {bar}
          </Link>
        ) : (
          <div key={mark.id} title={title} style={style} className={className}>
            {bar}
          </div>
        );
      })}
    </>
  );
});
