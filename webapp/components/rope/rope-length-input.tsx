import { Input } from "@/components/ui/input";

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
      <Input
        mono
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
        className="w-full sm:w-32"
      />
      <span className="font-mono text-xs leading-none text-text-subtle">m</span>
    </div>
  );
}
