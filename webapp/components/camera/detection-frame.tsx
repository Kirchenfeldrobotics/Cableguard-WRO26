import type { Defect } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { kindTone } from "@/lib/defects";
import { formatConfidence, defectClassLabel } from "@/lib/format";

const boxColor = { danger: "border-danger", warning: "border-warning", neutral: "border-text-subtle" };

/**
 * Where in the camera view the detection sat. The frame itself is not stored, only the box,
 * so the tile stays the striped placeholder and shows the detector's 640x640 frame shape
 * (robot/src/camera/camera.py) rather than the 4:3 tile of the live stream.
 */
export function DetectionFrame({ defect }: { defect: Defect }) {
  const { box_x1: x1, box_y1: y1, box_x2: x2, box_y2: y2 } = defect;
  const box =
    x1 !== null && y1 !== null && x2 !== null && y2 !== null
      ? { left: `${x1 * 100}%`, top: `${y1 * 100}%`, width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%` }
      : null;

  return (
    <div className="relative aspect-square w-full rounded-card bg-video-placeholder">
      <div className="absolute top-3.5 left-4 font-mono text-[11px] leading-none text-video-text">
        {box ? "frame not stored, box only" : "no box stored"}
      </div>

      {box && (
        <div style={box} className={cn("absolute rounded-[3px] border-2", boxColor[kindTone(defect.kind)])}>
          <span className="absolute -top-[19px] left-0 font-mono text-[11px] leading-none whitespace-nowrap text-video-text">
            {defectClassLabel(defect.label)} {formatConfidence(defect.confidence)}
          </span>
        </div>
      )}
    </div>
  );
}
