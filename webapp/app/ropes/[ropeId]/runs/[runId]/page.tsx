import type { Metadata } from "next";

import { RunView } from "@/features/run/run-view";

export const metadata: Metadata = { title: "Run" };

export default async function RunPage(props: PageProps<"/ropes/[ropeId]/runs/[runId]">) {
  const { ropeId, runId } = await props.params;
  return <RunView ropeId={ropeId} runId={runId} />;
}
