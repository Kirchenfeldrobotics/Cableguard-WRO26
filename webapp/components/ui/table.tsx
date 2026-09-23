"use client";

import { useRouter } from "next/navigation";

import { cn } from "@/lib/cn";

type Align = "left" | "right";

/**
 * How a cell shows on a phone, where every row is a card (`.stack-table` in globals.css):
 * `primary` spans the card as its title, `end` sits bottom right (row actions), `hide`
 * leaves the cell out. Cells without it get their `label` as a caption.
 */
type Phone = "primary" | "end" | "hide";

export function Table({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className="lg:overflow-x-auto">
      <table className={cn("stack-table w-full border-collapse", className)}>{children}</table>
    </div>
  );
}

export function Th({ align = "left", children }: { align?: Align; children?: React.ReactNode }) {
  return (
    <th
      className={cn(
        "border-b border-line-strong pr-3.5 pb-3 text-xs leading-none font-semibold text-text-subtle",
        align === "right" ? "text-right" : "text-left",
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  align = "left",
  mono = false,
  muted = false,
  strong = false,
  label,
  phone,
  className,
  children,
}: {
  align?: Align;
  mono?: boolean;
  muted?: boolean;
  strong?: boolean;
  /** Caption above the value on a phone, normally the column header. */
  label?: string;
  phone?: Phone;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <td
      data-label={phone ? undefined : label}
      data-primary={phone === "primary" || undefined}
      data-phone={phone}
      className={cn(
        "border-b border-line py-3.5 pr-3.5 text-[13px] leading-[1.3]",
        align === "right" && "text-right",
        mono ? "font-mono whitespace-nowrap" : "font-sans",
        muted && "text-text-muted",
        strong && (mono ? "font-medium" : "text-sm font-semibold"),
        className,
      )}
    >
      {children}
    </td>
  );
}

/** Table row that navigates to `href` on click or Enter. */
export function LinkRow({ href, children }: { href: string; children: React.ReactNode }) {
  const router = useRouter();
  return (
    <tr
      role="link"
      tabIndex={0}
      onClick={() => router.push(href)}
      onKeyDown={(e) => e.key === "Enter" && router.push(href)}
      className="cursor-pointer hover:bg-surface-hover"
    >
      {children}
    </tr>
  );
}
