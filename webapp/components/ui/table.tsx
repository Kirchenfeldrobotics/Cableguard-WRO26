"use client";

import { useRouter } from "next/navigation";

import { cn } from "@/lib/cn";

type Align = "left" | "right";

export function Table({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full border-collapse", className)}>{children}</table>
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
  className,
  children,
}: {
  align?: Align;
  mono?: boolean;
  muted?: boolean;
  strong?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <td
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
