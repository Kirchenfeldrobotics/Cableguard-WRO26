"use client";

import { useCurrentSelection } from "@/lib/hooks/use-inspection";

export interface NavItem {
  href: string;
  /** Sidebar label. */
  label: string;
  /** Bottom bar label, short enough for five tabs on a phone. */
  short: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", short: "Status", icon: <StatusIcon /> },
  { href: "/live", label: "Live run", short: "Live", icon: <LiveIcon /> },
  { href: "/ropes", label: "Ropes", short: "Ropes", icon: <RopeIcon /> },
  { href: "/compare", label: "Compare runs", short: "Compare", icon: <CompareIcon /> },
  { href: "/settings", label: "Robot settings", short: "Robot", icon: <RobotIcon /> },
];

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/**
 * Navigation shared by the sidebar and the phone tab bar. The live screen is the drive
 * screen, and driving with no run recording stores nothing, so with none selected it is
 * not offered at all.
 */
export function useNavItems() {
  const current = useCurrentSelection();
  const recording = current.data?.run_id != null;
  const items = NAV_ITEMS.filter((item) => item.href !== "/live" || recording);
  return { items, recording };
}

/* Flat 24px stroke icons, drawn in the current text colour. */

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="block size-[22px]"
    >
      {children}
    </svg>
  );
}

function StatusIcon() {
  return (
    <Icon>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </Icon>
  );
}

function LiveIcon() {
  return (
    <Icon>
      <circle cx="12" cy="12" r="2.5" fill="currentColor" />
      <path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4" />
      <path d="M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2" />
    </Icon>
  );
}

/** The unrolled rope: a bar with a finding mark on it. */
function RopeIcon() {
  return (
    <Icon>
      <rect x="2.5" y="8.5" width="19" height="7" rx="2" />
      <path d="M9 6v12" />
    </Icon>
  );
}

/** Two rope strips above each other. */
function CompareIcon() {
  return (
    <Icon>
      <rect x="2.5" y="4" width="19" height="6" rx="2" />
      <rect x="2.5" y="14" width="19" height="6" rx="2" />
      <path d="M15 2.5v9M8 12.5v9" />
    </Icon>
  );
}

/** Sliders, for the drive and detection settings. */
function RobotIcon() {
  return (
    <Icon>
      <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12" />
      <circle cx="16" cy="6" r="2" />
      <circle cx="10" cy="12" r="2" />
      <circle cx="18" cy="18" r="2" />
    </Icon>
  );
}
