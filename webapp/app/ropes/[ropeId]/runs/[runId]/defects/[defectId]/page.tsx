import type { Metadata } from "next";

import { DefectView } from "@/features/defect/defect-view";

export const metadata: Metadata = { title: "Defect" };

export default async function DefectPage(
  props: PageProps<"/ropes/[ropeId]/runs/[runId]/defects/[defectId]">,
) {
  const { ropeId, runId, defectId } = await props.params;
  return <DefectView ropeId={ropeId} runId={runId} defectId={defectId} />;
}
