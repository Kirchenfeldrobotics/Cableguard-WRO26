"use client";

import { Pill } from "@/components/ui/pill";
import { useRobotConnected } from "@/lib/robot/robot-link";

/** Header badge: Link lost, Live (run in progress) or Idle. */
export function RunStatePill({ running }: { running: boolean }) {
  const connected = useRobotConnected();

  if (!connected)
    return (
      <Pill tone="live" variant="status">
        Link lost
      </Pill>
    );
  if (running)
    return (
      <Pill tone="live" variant="status">
        Live
      </Pill>
    );
  return (
    <Pill tone="neutral" variant="status">
      Idle
    </Pill>
  );
}
