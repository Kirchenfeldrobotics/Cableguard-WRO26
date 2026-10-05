import { cn } from "@/lib/cn";

/**
 * The text field of the app, as tall as a button. `mono` is for a number that is read as a
 * measurement. Phones get 16px text, anything smaller makes iOS zoom the page on focus.
 */
export function Input({
  mono = false,
  className,
  ...props
}: { mono?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-control min-w-0 rounded-control border border-border bg-white px-3.5 text-base text-ink sm:text-sm",
        "disabled:cursor-not-allowed disabled:bg-surface disabled:text-text-faint",
        mono && "text-right font-mono font-medium sm:text-[13px]",
        className,
      )}
      {...props}
    />
  );
}

/** A control under its caption. Pass `htmlFor` when the control is an input with that id. */
export function Field({
  label,
  htmlFor,
  className,
  children,
}: {
  label: string;
  htmlFor?: string;
  className?: string;
  children: React.ReactNode;
}) {
  const caption = "text-[13px] leading-none font-semibold text-text-muted";
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {htmlFor ? (
        <label htmlFor={htmlFor} className={caption}>
          {label}
        </label>
      ) : (
        <span className={caption}>{label}</span>
      )}
      {children}
    </div>
  );
}
