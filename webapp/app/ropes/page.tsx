import type { Metadata } from "next";

import { RopesView } from "@/features/ropes/ropes-view";

export const metadata: Metadata = { title: "Ropes" };

export default function RopesPage() {
  return <RopesView />;
}
