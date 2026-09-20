import { defectTypeLabel } from "@/lib/format";

/** Colour key for the rope strip. */
export function DefectLegend({ note }: { note?: React.ReactNode }) {
  return (
    <div className="mt-3.5 flex flex-wrap items-center gap-5">
      <LegendItem className="bg-danger" label={`${defectTypeLabel("lf")} (LF)`} />
      <LegendItem className="bg-warning" label={`${defectTypeLabel("lma")} (LMA)`} />
      {note && <span className="text-xs leading-none text-text-subtle">{note}</span>}
    </div>
  );
}

function LegendItem({ className, label }: { className: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span aria-hidden className={`block h-4 w-[5px] rounded-[3px] ${className}`} />
      <span className="text-xs leading-none font-medium text-text-muted">{label}</span>
    </div>
  );
}
