import { cn } from "@/lib/cn";

const titleClass = "m-0 text-2xl leading-none font-extrabold tracking-[-0.01em] uppercase sm:text-[30px]";

/** Page heading row: title, then badges and meta text, optional actions on the right. */
export function PageHeader({
  title,
  children,
  actions,
}: {
  title: React.ReactNode;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <h1 className={cn(titleClass, "break-all")}>{title}</h1>
      {children}
      {actions && <div className="ml-auto flex items-center gap-3">{actions}</div>}
    </div>
  );
}

export function SectionTitle({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <h2 className={cn(titleClass, "mt-8 mb-3.5 sm:mt-[38px] sm:mb-[18px]", className)}>{children}</h2>;
}

/** Secondary text next to a heading. */
export function HeadingMeta({ children }: { children: React.ReactNode }) {
  return <span className="text-sm leading-none font-medium text-text-muted">{children}</span>;
}
