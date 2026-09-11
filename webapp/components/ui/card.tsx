import { cn } from "@/lib/cn";

/** Grey rounded surface that groups related content. */
export function Panel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card bg-surface", className)} {...props} />;
}

/** Row of cards that wraps on narrow screens. */
export function CardGrid({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-[18px] flex flex-wrap gap-3.5", className)} {...props} />;
}

export type Indicator = "success" | "danger" | "alert" | "warning" | "ring" | "solid" | "muted";

const indicators: Record<Indicator, string> = {
  success: "bg-success",
  danger: "bg-danger",
  alert: "bg-danger-soft border-4 border-danger",
  warning: "bg-warning-soft border-4 border-warning",
  ring: "border-4 border-ink",
  solid: "bg-ink",
  muted: "bg-surface-strong",
};

/** Headline number with a coloured status circle (dashboard, live run). */
export function StatCard({
  value,
  label,
  indicator,
  title,
}: {
  value: React.ReactNode;
  label: React.ReactNode;
  indicator: Indicator;
  title?: string;
}) {
  return (
    <div
      title={title}
      className="flex min-w-[190px] flex-[1_1_210px] flex-col gap-[18px] rounded-card bg-surface px-5 pt-[18px] pb-4"
    >
      <div className="flex items-center gap-3.5">
        <div aria-hidden className={cn("size-[46px] flex-none rounded-full", indicators[indicator])} />
        <div className="text-[22px] leading-[1.15] font-bold">{value}</div>
      </div>
      <div className="text-[13px] leading-[1.3] text-text-muted">{label}</div>
    </div>
  );
}

/** Plain value and label (rope, run and comparison summaries). */
export function FactCard({
  value,
  label,
  className,
  title,
}: {
  value: React.ReactNode;
  label: React.ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <div
      title={title}
      className="flex min-w-[180px] flex-[1_1_200px] flex-col gap-3.5 rounded-card bg-surface px-5 pt-[18px] pb-4"
    >
      <div className={cn("text-xl leading-[1.15] font-bold", className)}>{value}</div>
      <div className="text-[13px] leading-[1.3] text-text-muted">{label}</div>
    </div>
  );
}
