import { cn } from "@/lib/cn";

const titleClass = "m-0 text-2xl leading-none font-extrabold tracking-[-0.01em] uppercase sm:text-[30px]";

/**
 * Page heading row: title, then badges and meta text, optional actions on the right. The
 * title line is as tall as a button whether or not one sits next to it, so the title is at
 * the same height on every page. On phones the actions go on a row of their own under it.
 */
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
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div className="flex min-h-control min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className={cn(titleClass, "wrap-anywhere")}>{title}</h1>
        {children}
      </div>
      {actions && <div className="flex items-center gap-3 max-sm:w-full sm:ml-auto">{actions}</div>}
    </div>
  );
}

/**
 * Section heading row: title, then meta text, optional actions on the right, and an optional
 * note underneath. The spacing around a section belongs to this row and to nothing inside it.
 */
export function SectionTitle({
  children,
  meta,
  actions,
  note,
}: {
  children: React.ReactNode;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  note?: React.ReactNode;
}) {
  return (
    <div className="mt-8 mb-3.5 sm:mt-section sm:mb-stack">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className={titleClass}>{children}</h2>
        {meta}
        {actions && <div className="ml-auto flex items-center gap-3">{actions}</div>}
      </div>
      {note && <p className="mt-2 mb-0 text-xs leading-normal text-text-subtle">{note}</p>}
    </div>
  );
}

/** Heading of a group inside a column, one size below a section title. */
export function SubTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="m-0 text-lg leading-none font-extrabold tracking-[-0.01em] uppercase">{children}</h2>;
}

/** Secondary text next to a heading. */
export function HeadingMeta({ children }: { children: React.ReactNode }) {
  return <span className="text-sm leading-none font-medium text-text-muted">{children}</span>;
}
