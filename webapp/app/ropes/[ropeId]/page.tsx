import type { Metadata } from "next";

import { RopeView } from "@/features/rope/rope-view";

export const metadata: Metadata = { title: "Rope" };

export default async function RopePage(props: PageProps<"/ropes/[ropeId]">) {
  const { ropeId } = await props.params;
  return <RopeView ropeId={ropeId} />;
}
