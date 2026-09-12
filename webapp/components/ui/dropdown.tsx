"use client";

import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";

export interface DropdownOption {
  value: string;
  label: string;
}

/**
 * Listbox shaped like the design system's controls, because a native `<select>`
 * cannot be styled to match. Focus stays on the trigger and the highlighted row
 * is announced through `aria-activedescendant`.
 *
 * Keyboard: Enter, Space or either arrow opens; Up and Down move; Home and End
 * jump; Enter or Space selects; Escape and Tab close.
 */
export function Dropdown({
  label,
  options,
  value,
  onChange,
  placeholder = "Select…",
  disabled = false,
  className,
}: {
  /** Accessible name for the trigger, e.g. "Selected rope". */
  label: string;
  options: DropdownOption[];
  value: string | null;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const optionRefs = useRef<(HTMLLIElement | null)[]>([]);
  const id = useId();

  const listId = `${id}-list`;
  const optionId = (index: number) => `${id}-option-${index}`;
  const selectedIndex = options.findIndex((option) => option.value === value);
  const selected = selectedIndex === -1 ? undefined : options[selectedIndex];
  const unusable = disabled || options.length === 0;

  // Close as soon as the pointer goes down anywhere else on the page.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Keep the highlighted row visible while arrowing through a long list.
  useEffect(() => {
    if (open) optionRefs.current[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  const openMenu = () => {
    if (unusable) return;
    setActiveIndex(selectedIndex === -1 ? 0 : selectedIndex);
    setOpen(true);
  };

  const choose = (index: number) => {
    const option = options[index];
    setOpen(false);
    if (option && option.value !== value) onChange(option.value);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
      case "ArrowUp": {
        e.preventDefault();
        if (!open) return openMenu();
        const step = e.key === "ArrowDown" ? 1 : -1;
        setActiveIndex((i) => (i + step + options.length) % options.length);
        break;
      }
      case "Home":
      case "End":
        if (!open) return;
        e.preventDefault();
        setActiveIndex(e.key === "Home" ? 0 : options.length - 1);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (open) choose(activeIndex);
        else openMenu();
        break;
      case "Escape":
        if (!open) return;
        e.preventDefault();
        setOpen(false);
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        // ARIA 1.2 select-only combobox: the role is what lets the trigger own
        // aria-activedescendant while keeping focus, and a plain button role
        // does not support that attribute.
        role="combobox"
        disabled={unusable}
        aria-disabled={unusable}
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-activedescendant={open ? optionId(activeIndex) : undefined}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={onKeyDown}
        className={cn(
          "flex w-full items-center justify-between gap-3 rounded-control border bg-white px-3.5 py-3 text-sm leading-none font-medium transition-colors",
          unusable ? "cursor-not-allowed border-border text-text-faint" : "hover:border-ink",
          open ? "border-ink" : "border-border",
        )}
      >
        <span className={cn("truncate", !selected && !unusable && "text-text-subtle")}>
          {selected?.label ?? placeholder}
        </span>
        <Chevron open={open} />
      </button>

      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          className="absolute z-20 mt-1.5 max-h-[264px] w-full overflow-auto rounded-control border border-border bg-white py-1.5"
        >
          {options.map((option, i) => (
            <li
              key={option.value}
              id={optionId(i)}
              ref={(el) => {
                optionRefs.current[i] = el;
              }}
              role="option"
              aria-selected={option.value === value}
              onPointerEnter={() => setActiveIndex(i)}
              onClick={() => choose(i)}
              className={cn(
                "cursor-pointer truncate px-3.5 py-2.5 text-sm leading-none",
                i === activeIndex && "bg-surface-hover",
                option.value === value ? "font-semibold" : "font-medium text-text-muted",
              )}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Border-drawn chevron, in the same flat style as `RingIcon`. */
function Chevron({ open }: { open: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "block size-[7px] flex-none border-r-2 border-b-2 border-current transition-transform",
        open ? "translate-y-[2px] -rotate-[135deg]" : "-translate-y-[2px] rotate-45",
      )}
    />
  );
}
