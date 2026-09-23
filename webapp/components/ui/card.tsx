import { cn } from "@/lib/cn";

/** Grey rounded surface that groups related content. */
export function Panel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card bg-surface", className)} {...props} />;
}

/**
 * Row of cards that wraps on narrow screens. Phones get two columns, and an odd last card
 * takes the full row.
 */
export function CardGrid({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "mt-[18px] grid grid-cols-2 gap-2.5 sm:flex sm:flex-wrap sm:gap-3.5",
        "[&>*:last-child:nth-child(odd)]:col-span-2",
        className,
      )}
      {...props}
    />
  );
}

export type Indicator = "success" | "danger" | "alert" | "warning" | "ring" | "solid" | "muted";

const indicators: Record<Indicator, string> = {
  success: "bg-success",
  danger: "bg-danger",
  alert: "bg-danger-soft border-[3px] border-danger sm:border-4",
  warning: "bg-warning-soft border-[3px] border-warning sm:border-4",
  ring: "border-[3px] border-ink sm:border-4",
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
      className="flex min-w-0 flex-col gap-3 rounded-card bg-surface px-3.5 pt-3.5 pb-3 sm:min-w-[190px] sm:flex-[1_1_210px] sm:gap-[18px] sm:px-5 sm:pt-[18px] sm:pb-4"
    >
      <div className="flex items-center gap-2 sm:gap-3.5">
        <div
          aria-hidden
          className={cn("size-5 flex-none rounded-full sm:size-[46px]", indicators[indicator])}
        />
        <div className="min-w-0 text-lg leading-[1.15] font-bold break-words sm:text-[22px]">{value}</div>
      </div>
      <div className="text-xs leading-[1.3] text-text-muted sm:text-[13px]">{label}</div>
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
      className="flex min-w-0 flex-col gap-2.5 rounded-card bg-surface px-3.5 pt-3.5 pb-3 sm:min-w-[180px] sm:flex-[1_1_200px] sm:gap-3.5 sm:px-5 sm:pt-[18px] sm:pb-4"
    >
      <div className={cn("text-lg leading-[1.15] font-bold break-words sm:text-xl", className)}>{value}</div>
      <div className="text-xs leading-[1.3] text-text-muted sm:text-[13px]">{label}</div>
    </div>
  );
}
