"use client";

import { useState } from "react";

import { Pill } from "@/components/ui/pill";
import { cn } from "@/lib/cn";
import { useNow } from "@/lib/hooks/use-now";
import { VIDEO_STALE_MS, type VideoFeed } from "@/lib/robot/use-video-feeds";

/** Frame shape the robot streams (640×480, robot/src/camera/camera.py), used until a frame arrives. */
const DEFAULT_ASPECT = 4 / 3;

/**
 * One camera tile, sized to the frame's own aspect ratio so the image fills it edge to edge:
 * live JPEG stream, the last frame dimmed and marked stale once frames stop arriving, or the
 * striped placeholder before the first frame.
 */
export function CameraFeed({ caption, feed }: { caption: string; feed: VideoFeed }) {
  const [aspect, setAspect] = useState(DEFAULT_ASPECT);
  const now = useNow(500);
  const stale = feed.lastFrameAt !== null && now !== null && now - feed.lastFrameAt > VIDEO_STALE_MS;

  return (
    <figure className="m-0 flex min-w-[290px] flex-[1_1_380px] flex-col gap-2.5">
      <div className="relative overflow-hidden rounded-card bg-video-placeholder" style={{ aspectRatio: aspect }}>
        {feed.src ? (
          // Blob URLs from the socket cannot go through next/image.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={feed.src}
            alt={caption}
            className={cn("absolute inset-0 size-full object-cover", stale && "opacity-35")}
            onLoad={(e) => {
              const { naturalWidth, naturalHeight } = e.currentTarget;
              if (naturalWidth > 0 && naturalHeight > 0) setAspect(naturalWidth / naturalHeight);
            }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center font-mono text-[11px] leading-none text-video-text">
            no signal
          </div>
        )}
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
