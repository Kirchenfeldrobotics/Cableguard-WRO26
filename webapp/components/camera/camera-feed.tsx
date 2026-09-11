"use client";

import { useState } from "react";

import type { VideoFeed } from "@/lib/robot/use-video-feeds";

/** One camera tile: live JPEG stream, or the striped placeholder while there is no signal. */
export function CameraFeed({ code, caption, feed }: { code: string; caption: string; feed: VideoFeed }) {
  const [size, setSize] = useState<string | null>(null);
  const status = feed.src ? [size, `${Math.round(feed.fps)} fps`].filter(Boolean).join(" · ") : "no signal";

  return (
    <figure className="m-0 flex min-w-[290px] flex-[1_1_380px] flex-col gap-2.5">
      <div className="relative aspect-video max-h-[330px] overflow-hidden rounded-card bg-video-placeholder">
        {feed.src && (
          // Blob URLs from the socket cannot go through next/image.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={feed.src}
            alt={caption}
            className="absolute inset-0 size-full object-contain"
            onLoad={(e) => setSize(`${e.currentTarget.naturalWidth}×${e.currentTarget.naturalHeight}`)}
          />
        )}
        <div className="absolute top-3.5 left-4 font-mono text-[11px] leading-none text-video-text [text-shadow:0_1px_2px_rgb(0_0_0/.6)]">
          {code} · {status}
        </div>
      </div>
      <figcaption className="text-[13px] leading-none text-text-muted">{caption}</figcaption>
    </figure>
  );
}
