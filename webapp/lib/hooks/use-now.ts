"use client";

import { useEffect, useState } from "react";

/**
 * Current time in epoch ms, refreshed every `intervalMs`.
 * Returns null during server rendering and the first client render
 * so the markup does not mismatch on hydration.
 */
export function useNow(intervalMs = 1_000): number | null {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const timer = setInterval(tick, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}
