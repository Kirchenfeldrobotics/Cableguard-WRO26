import { cn } from "@/lib/cn";

export type PillTone = "live" | "danger" | "warning" | "neutral";

const tones: Record<PillTone, string> = {
  live: "bg-danger text-white",
  danger: "bg-danger-soft text-danger-strong",
  warning: "bg-warning-soft text-warning-ink",
  neutral: "bg-neutral-soft text-text-muted",
};

/**
 * `status` is the uppercase header badge (Live, Link lost, Idle).
 * `tag` is the smaller badge used inside tables.
 */
export function Pill({
  tone,
  variant = "tag",
  children,
}: {
  tone: PillTone;
  variant?: "status" | "tag";
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full leading-none whitespace-nowrap",
        variant === "status"
          ? "px-[13px] py-1.5 text-xs font-bold tracking-[.05em] uppercase"
          : "px-[11px] py-[5px] text-xs font-semibold",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
