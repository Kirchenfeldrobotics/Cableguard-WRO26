"use client";

import { useState } from "react";

/**
 * Two-step remove for a table row, so nothing is deleted by a stray click. It sits inside a
 * row that navigates, so its clicks and key presses stay with it.
 */
export function RemoveButton({ onConfirm }: { onConfirm: () => void }) {
  const [armed, setArmed] = useState(false);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        if (armed) onConfirm();
        setArmed(!armed);
      }}
      onBlur={() => setArmed(false)}
      onKeyDown={(e) => e.stopPropagation()}
      className={
        armed
          ? "text-xs leading-none font-semibold text-danger-strong max-lg:-m-2.5 max-lg:p-2.5"
          : "text-xs leading-none font-medium text-text-subtle hover:text-danger-strong max-lg:-m-2.5 max-lg:p-2.5"
      }
    >
      {armed ? "Confirm remove" : "Remove"}
    </button>
  );
}
