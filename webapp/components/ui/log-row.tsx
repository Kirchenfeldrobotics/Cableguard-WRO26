import Link from "next/link";

import { cn } from "@/lib/cn";
import type { Tone } from "@/lib/defects";

const tones: Record<Tone, string> = {
  danger: "bg-danger-soft text-danger-strong",
  warning: "bg-warning-soft text-warning-ink",
  neutral: "bg-line text-text-muted",
};

/** Tinted row with a mono position on the left and a label on the right. */
export function LogRow({
  href,
  tone,
  position,
  children,
}: {
  href: string;
  tone: Tone;
  position: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center justify-between gap-4 rounded-row px-3.5 py-3 hover:brightness-[.97]",
        tones[tone],
      )}
    >
      <span className="font-mono text-xs leading-none">{position}</span>
      <span className="text-[13px] leading-none font-medium">{children}</span>
    </Link>
  );
}

/** Tinted row without navigation. */
export function InfoRow({
  tone,
  label,
  value,
}: {
  tone: Tone;
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-4 rounded-row px-3.5 py-3", tones[tone])}>
      <span className="text-[13px] leading-none font-medium">{label}</span>
      <span className="font-mono text-xs leading-none">{value}</span>
    </div>
  );
}
