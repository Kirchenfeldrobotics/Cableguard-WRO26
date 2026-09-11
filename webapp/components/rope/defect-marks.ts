import type { Defect } from "@/lib/api/types";
import { kindTone } from "@/lib/defects";
import { defectTypeLabel, formatMetres, shortId } from "@/lib/format";
import { routes } from "@/lib/routes";

import type { StripMark } from "./rope-strip";

/** Turns defects of one run into clickable marks for <RopeStrip>. */
export function defectMarks(
  ropeId: string,
  defects: Defect[],
  state?: StripMark["state"] | ((d: Defect) => StripMark["state"]),
): StripMark[] {
  return defects.map((d) => ({
    id: d.id,
    pos: d.pos_to_start,
    tone: kindTone(d.kind),
    state: typeof state === "function" ? state(d) : state,
    href: routes.defect(ropeId, d.run_id, d.id),
    title: `${shortId(d.id)} · ${defectTypeLabel(d.kind)} · ${formatMetres(d.pos_to_start)}`,
  }));
}
