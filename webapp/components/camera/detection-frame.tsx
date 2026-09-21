"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { Defect } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { kindTone } from "@/lib/defects";
import { formatConfidence, defectClassLabel } from "@/lib/format";

const boxColor = { danger: "border-danger", warning: "border-warning", neutral: "border-text-subtle" };

/** The detector's frame is 640x640 (robot/src/camera/camera.py), used until the JPEG arrives. */
const DEFAULT_ASPECT = 1;

/**
 * The frame the defect was found in, with its box drawn where the detector put it. The box is
 * normalised to that frame, so the tile takes the image's own aspect ratio to keep them lined
 * up. Defects stored before frames were kept show the box on the striped placeholder.
 */
export function DetectionFrame({ defect }: { defect: Defect }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [aspect, setAspect] = useState(DEFAULT_ASPECT);

  useEffect(() => {
    if (!defect.frame_id) return;
    let url: string | null = null;
    let cancelled = false;
    api.defects.frame(defect.id).then(
      (blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setSrc(url);
      },
      () => {
        if (!cancelled) setFailed(true);
      },
    );
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [defect.id, defect.frame_id]);

  const { box_x1: x1, box_y1: y1, box_x2: x2, box_y2: y2 } = defect;
  const box =
    x1 !== null && y1 !== null && x2 !== null && y2 !== null
      ? { left: `${x1 * 100}%`, top: `${y1 * 100}%`, width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%` }
      : null;

  const status = !defect.frame_id
    ? "frame not stored, box only"
    : failed
      ? "frame could not be loaded"
      : src
        ? null
        : "loading frame…";

  return (
    <div
      className="relative w-full overflow-hidden rounded-card bg-video-placeholder"
      style={{ aspectRatio: aspect }}
    >
      {src && (
        // Blob URLs from an authenticated fetch cannot go through next/image.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={`Camera frame the ${defectClassLabel(defect.label)} was found in`}
          className="absolute inset-0 size-full"
          onLoad={(e) => {
            const { naturalWidth, naturalHeight } = e.currentTarget;
            if (naturalWidth > 0 && naturalHeight > 0) setAspect(naturalWidth / naturalHeight);
          }}
        />
      )}

      {status && (
        <div className="absolute top-3.5 left-4 font-mono text-[11px] leading-none text-video-text">{status}</div>
      )}

      {box && (
        <div style={box} className={cn("absolute rounded-[3px] border-2", boxColor[kindTone(defect.kind)])}>
          <span className="absolute -top-[21px] left-0 rounded-[3px] bg-video/80 px-1.5 py-[3px] font-mono text-[11px] leading-none whitespace-nowrap text-video-text">
            {defectClassLabel(defect.label)} {formatConfidence(defect.confidence)}
          </span>
        </div>
      )}
    </div>
  );
}
