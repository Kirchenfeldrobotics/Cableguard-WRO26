import type { Metadata } from "next";

import { LiveView } from "@/features/live/live-view";

export const metadata: Metadata = { title: "Live run" };

export default function LivePage() {
  return <LiveView />;
}
