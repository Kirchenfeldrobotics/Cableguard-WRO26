import { twMerge, type ClassNameValue } from "tailwind-merge";

/**
 * Joins class names and resolves Tailwind conflicts, so a `className` passed to a
 * component reliably overrides the component's defaults (last one wins).
 */
export function cn(...classes: ClassNameValue[]): string {
  return twMerge(...classes);
}
