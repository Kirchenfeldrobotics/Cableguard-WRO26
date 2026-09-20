import { cn } from "@/lib/cn";

export type FactTone = "ink" | "muted" | "success" | "danger";

const tones: Record<FactTone, string> = {
  ink: "text-ink",
  muted: "text-text-muted",
  success: "text-success-ink",
  danger: "text-danger-strong",
};

export interface Fact {
  label: React.ReactNode;
  value: React.ReactNode;
  tone?: FactTone;
}

/** Label / value rows on a grey panel (defect facts, connection details). */
export function FactList({ facts, className }: { facts: Fact[]; className?: string }) {
  return (
    <dl className={cn("rounded-card bg-surface px-5 py-2", className)}>
      {facts.map((fact, i) => (
        <div
          key={i}
          className="flex items-center justify-between gap-4 border-b border-surface-strong py-[13px] last:border-b-0"
        >
          <dt className="text-[13px] leading-[1.3] text-text-muted">{fact.label}</dt>
          <dd className={cn("m-0 text-right font-mono text-[13px] leading-[1.3] font-medium", tones[fact.tone ?? "muted"])}>
            {fact.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
