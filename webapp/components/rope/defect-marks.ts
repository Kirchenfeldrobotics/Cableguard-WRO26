import { kindTone, type Finding } from "@/lib/defects";
import { defectClassLabel, defectTypeLabel, formatConfidence, formatSpan } from "@/lib/format";
import { routes } from "@/lib/routes";

import type { StripMark } from "./rope-strip";

function markTitle(finding: Finding): string {
  const parts = [
    defectClassLabel(finding.best.label) || defectTypeLabel(finding.kind),
    formatConfidence(finding.confidence),
    formatSpan(finding.from, finding.to),
  ];
  if (finding.detections.length > 1) parts.push(`${finding.detections.length} detections`);
  return parts.join(" · ");
}

/** Turns the findings of one run into clickable marks for <RopeStrip>. */
export function findingMarks(
  ropeId: string,
  findings: Finding[],
  state?: StripMark["state"] | ((finding: Finding) => StripMark["state"]),
): StripMark[] {
  return findings.map((finding) => ({
    id: finding.best.id,
    pos: finding.pos,
    from: finding.from,
    to: finding.to,
    tone: kindTone(finding.kind),
    confidence: finding.confidence,
    state: typeof state === "function" ? state(finding) : state,
    href: routes.defect(ropeId, finding.best.run_id, finding.best.id),
    title: markTitle(finding),
  }));
}
