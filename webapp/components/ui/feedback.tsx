import Link from "next/link";

import { cn } from "@/lib/cn";

/** Red banner for conditions that need the operator's attention. */
export function Notice({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      role="alert"
      className={cn(
        "mt-[18px] rounded-[12px] bg-danger-soft px-[18px] py-4 text-[15px] leading-normal font-medium text-danger-strong",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Loading, error and empty states inside a page. */
export function StatusMessage({
  children,
  tone = "muted",
}: {
  children: React.ReactNode;
  tone?: "muted" | "error";
}) {
  return (
    <p
      className={cn(
        "mt-[18px] text-sm leading-normal",
        tone === "error" ? "text-danger-strong" : "text-text-subtle",
      )}
    >
      {children}
    </p>
  );
}

export function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="mb-3.5 inline-block text-[13px] leading-none font-medium text-text-subtle hover:text-danger-strong"
    >
      ← {children}
    </Link>
  );
}
