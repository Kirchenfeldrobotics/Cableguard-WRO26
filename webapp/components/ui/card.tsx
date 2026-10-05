import { cn } from "@/lib/cn";

const pads = {
  /** Free content: a strip, controls, a chart, a form. */
  content: "p-4 sm:p-[22px]",
  /** Rows that bring their own vertical padding and the rule between them. */
  list: "px-4 py-2 sm:px-[22px]",
};

/** Grey rounded surface that groups related content. */
export function Panel({
  pad = "content",
  className,
  ...props
}: { pad?: keyof typeof pads } & React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card bg-surface", pads[pad], className)} {...props} />;
}

/**
 * Row of cards that wraps on narrow screens. Phones get two columns, and an odd last card
 * takes the full row.
 */
export function CardGrid({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "mt-stack grid grid-cols-2 gap-2.5 sm:flex sm:flex-wrap sm:gap-3.5",
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

/** Shared by both cards. The label sits on the bottom edge, so a row of cards keeps its labels in line when one value wraps. */
const cardClass =
  "flex min-w-0 flex-col gap-3 rounded-card bg-surface px-3.5 pt-3.5 pb-3 sm:gap-stack sm:px-[22px] sm:pt-[18px] sm:pb-4";
const valueClass = "min-w-0 text-lg leading-[1.15] font-bold break-words sm:text-[22px]";
const labelClass = "mt-auto text-xs leading-[1.3] text-text-muted sm:text-[13px]";

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
    <div title={title} className={cn(cardClass, "sm:min-w-[190px] sm:flex-[1_1_210px]")}>
      <div className="flex items-center gap-2 sm:gap-3.5">
        <div
          aria-hidden
          className={cn("size-5 flex-none rounded-full sm:size-[46px]", indicators[indicator])}
        />
        <div className={valueClass}>{value}</div>
      </div>
      <div className={labelClass}>{label}</div>
    </div>
  );
}

/** Plain value and label (rope, run and comparison summaries). `className` colours the value. */
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
    <div title={title} className={cn(cardClass, "sm:min-w-[180px] sm:flex-[1_1_200px]")}>
      <div className={cn(valueClass, className)}>{value}</div>
      <div className={labelClass}>{label}</div>
    </div>
  );
}
