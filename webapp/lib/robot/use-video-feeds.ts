"use client";

import { useEffect, useState } from "react";

import { wsUrl } from "@/lib/config";

export interface VideoFeed {
  /** Object URL of the latest JPEG frame, or null before the first frame. */
  src: string | null;
  /** Frame rate measured when the latest frame arrived. */
  fps: number;
  /** Epoch ms when the latest frame arrived, or null before the first frame. */
  lastFrameAt: number | null;
}

/** A tile that receives no frame for this long marks its image stale. The robot streams at 8 fps. */
export const VIDEO_STALE_MS = 2_000;

const FPS_WINDOW_MS = 2_000;
const RETRY_MS = 3_000;

/**
 * Splits a binary message from /api/ws/video/ui into camera index and JPEG.
 * The robot prefixes each JPEG with one byte for the camera index
 * (robot/src/link/video.py).
 */
function parseFrame(buffer: ArrayBuffer): { camera: number; jpeg: Blob } | null {
  const bytes = new Uint8Array(buffer);
  if (bytes.length < 3 || bytes[1] !== 0xff || bytes[2] !== 0xd8) return null;
  return { camera: bytes[0], jpeg: new Blob([bytes.subarray(1)], { type: "image/jpeg" }) };
}

/** Live JPEG streams of the robot cameras. Only connects while mounted. */
export function useVideoFeeds(cameraCount: number): VideoFeed[] {
  const [feeds, setFeeds] = useState<VideoFeed[]>(() =>
    Array.from({ length: cameraCount }, () => ({ src: null, fps: 0, lastFrameAt: null })),
  );

  useEffect(() => {
    let disposed = false;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    const urls: (string | null)[] = Array(cameraCount).fill(null);
    const arrivals: number[][] = Array.from({ length: cameraCount }, () => []);

    const connect = () => {
      ws = new WebSocket(wsUrl("/api/ws/video/ui"));
      ws.binaryType = "arraybuffer";

      ws.onmessage = (e) => {
        if (!(e.data instanceof ArrayBuffer)) return;
        const frame = parseFrame(e.data);
        if (!frame || frame.camera >= cameraCount) return;

        const now = Date.now();
        const times = arrivals[frame.camera].filter((t) => now - t < FPS_WINDOW_MS);
        times.push(now);
        arrivals[frame.camera] = times;

        const previous = urls[frame.camera];
        const src = URL.createObjectURL(frame.jpeg);
        urls[frame.camera] = src;

        setFeeds((current) =>
          current.map((feed, i) =>
            i === frame.camera
              ? { src, fps: times.length / (FPS_WINDOW_MS / 1000), lastFrameAt: now }
              : feed,
          ),
        );
        if (previous) URL.revokeObjectURL(previous);
      };

      ws.onclose = () => {
        if (!disposed) retryTimer = setTimeout(connect, RETRY_MS);
      };
    };

    connect();

    return () => {
      disposed = true;
      clearTimeout(retryTimer);
      ws?.close();
      urls.forEach((url) => url && URL.revokeObjectURL(url));
    };
  }, [cameraCount]);

  return feeds;
}
