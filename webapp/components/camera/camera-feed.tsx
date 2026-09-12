"use client";

import { useState } from "react";

import { Pill } from "@/components/ui/pill";
import { cn } from "@/lib/cn";
import { formatAgo } from "@/lib/format";
import { useNow } from "@/lib/hooks/use-now";
import { VIDEO_STALE_MS, type VideoFeed } from "@/lib/robot/use-video-feeds";

/**
 * One camera tile: live JPEG stream, the last frame dimmed and marked stale once frames stop
 * arriving, or the striped placeholder before the first frame.
 */
export function CameraFeed({ code, caption, feed }: { code: string; caption: string; feed: VideoFeed }) {
  const [size, setSize] = useState<string | null>(null);
  const now = useNow(500);
  const age = feed.lastFrameAt !== null && now !== null ? Math.max(0, now - feed.lastFrameAt) : null;
  const stale = age !== null && age > VIDEO_STALE_MS;

  const status = !feed.src
    ? "no signal"
    : stale
      ? `last frame ${formatAgo(age ?? 0)}`
      : [size, `${Math.round(feed.fps)} fps`].filter(Boolean).join(" · ");

  return (
    <figure className="m-0 flex min-w-[290px] flex-[1_1_380px] flex-col gap-2.5">
      <div className="relative aspect-video max-h-[330px] overflow-hidden rounded-card bg-video-placeholder">
        {feed.src && (
          // Blob URLs from the socket cannot go through next/image.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={feed.src}
            alt={caption}
            className={cn("absolute inset-0 size-full object-contain", stale && "opacity-35")}
            onLoad={(e) => setSize(`${e.currentTarget.naturalWidth}×${e.currentTarget.naturalHeight}`)}
          />
        )}
        <div className="absolute top-3.5 left-4 font-mono text-[11px] leading-none text-video-text [text-shadow:0_1px_2px_rgb(0_0_0/.6)]">
          {code} · {status}
        </div>
        {stale && (
          <div className="absolute inset-x-0 bottom-3.5 flex justify-center">
            <Pill tone="live" variant="status">
              Not live
            </Pill>
          </div>
        )}
      </div>
      <figcaption className="text-[13px] leading-none text-text-muted">{caption}</figcaption>
    </figure>
  );
}
