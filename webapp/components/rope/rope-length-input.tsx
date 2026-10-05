/** The typed length in metres, or null while it is not one the server takes. */
export function parseRopeLength(text: string): number | null {
  const value = text.trim() === "" ? NaN : Number(text);
  return Number.isFinite(value) && value > 0 ? value : null;
}

/** Number input for the length of a rope, with its unit behind it. */
export function RopeLengthInput({
  value,
  onChange,
  autoFocus,
}: {
  value: string;
  onChange: (value: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <div className="flex min-w-[120px] flex-1 items-center gap-2.5 sm:flex-none">
      <input
        type="number"
        inputMode="decimal"
        required
        min={0}
        step="any"
        autoFocus={autoFocus}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Length"
        aria-label="Rope length in metres"
        className="w-full min-w-0 rounded-control border border-border bg-white px-3.5 py-3 text-right font-mono text-base sm:w-32 sm:text-sm"
      />
      <span className="font-mono text-xs leading-none text-text-subtle">m</span>
    </div>
  );
}
