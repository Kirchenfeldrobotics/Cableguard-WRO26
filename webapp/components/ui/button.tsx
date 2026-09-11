import Link from "next/link";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "danger";
type Size = "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2.5 rounded-control font-semibold leading-none whitespace-nowrap transition-colors disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink-soft disabled:bg-neutral-soft disabled:text-text-faint",
  secondary:
    "border border-border bg-white text-ink hover:border-ink disabled:text-text-faint disabled:hover:border-border",
  danger: "bg-danger-strong text-white hover:bg-danger-deep disabled:opacity-60",
};

const sizes: Record<Size, string> = {
  md: "px-5 py-[13px] text-sm",
  lg: "h-[58px] px-5 text-base",
};

interface StyleProps {
  variant?: Variant;
  size?: Size;
  className?: string;
}

export function buttonClass({ variant = "primary", size = "md", className }: StyleProps = {}) {
  return cn(base, variants[variant], sizes[size], className);
}

export function Button({
  variant,
  size,
  className,
  type = "button",
  ...props
}: StyleProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type={type} className={buttonClass({ variant, size, className })} {...props} />;
}

export function ButtonLink({
  variant,
  size,
  className,
  ...props
}: StyleProps & React.ComponentProps<typeof Link>) {
  return <Link className={buttonClass({ variant, size, className })} {...props} />;
}

/** Hollow circle used as an icon inside the large action buttons. */
export function RingIcon({ className }: { className?: string }) {
  return <span aria-hidden className={cn("block size-[18px] rounded-full border-2", className)} />;
}
