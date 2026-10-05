"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/brand/logo";
import { isActive, useNavItems } from "@/components/layout/nav";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";
import { formatAgo } from "@/lib/format";
import { useNow } from "@/lib/hooks/use-now";
import { useRobotConnected, useRobotLink } from "@/lib/robot/robot-link";

/** Desktop navigation. Phones get the top bar and tab bar in `mobile-nav.tsx` instead. */
export function Sidebar() {
  const pathname = usePathname();
  const { items } = useNavItems();

  return (
    <aside className="sticky top-3 hidden h-[calc(100vh-24px)] w-[236px] flex-none flex-col gap-[22px] rounded-shell bg-ink px-[18px] py-[26px] lg:flex">
      <Link href="/" aria-label="CableGuard dashboard">
        <Logo />
      </Link>
      <div className="h-px bg-ink-soft" />

      <nav className="flex flex-col gap-1">
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "rounded-control px-3.5 py-[11px] text-sm leading-none font-semibold whitespace-nowrap transition-colors",
                active ? "bg-white text-ink" : "text-text-inverse-muted hover:bg-ink-soft hover:text-white",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-2.5">
        <div className="h-px bg-ink-soft" />
        <LinkStatus />
        <div className="h-px bg-ink-soft" />
        <Operator />
      </div>
    </aside>
  );
}

/** Who is signed in, with the way out. */
function Operator() {
  const { user, signOut } = useAuth();

  return (
    <div className="flex items-center justify-between gap-2 px-1">
      <span className="truncate text-[13px] leading-none font-semibold text-white">
        {user?.username ?? "—"}
      </span>
      <button
        type="button"
        onClick={signOut}
        className="rounded-control px-2 py-1.5 text-xs leading-none font-semibold text-text-inverse-muted transition-colors hover:bg-ink-soft hover:text-white"
      >
        Sign out
      </button>
    </div>
  );
}

/** Robot link in words: the headline state and how fresh the last packet is. */
export function useLinkStatus() {
  const { socket, lastMessageAt } = useRobotLink();
  const connected = useRobotConnected();
  const now = useNow();

  const serverUp = socket === "open";
  const label = connected ? "Connected" : serverUp ? "Link lost" : "Server offline";
  const ago = serverUp && lastMessageAt && now ? formatAgo(Math.max(0, now - lastMessageAt)) : null;
  const detail = !serverUp
    ? socket === "connecting"
      ? "connecting to server…"
      : "retrying…"
    : ago
      ? `last packet ${ago}`
      : "waiting for data";

  // `brief` drops the caption, for the phone header where the full line never fits.
  return { connected, label, detail, brief: ago ?? detail, now };
}

function LinkStatus() {
  const { connected, label, detail, now } = useLinkStatus();

  return (
    <>
      <div className="flex items-center gap-2.5 px-1">
        <span
          aria-hidden
          className={cn("block size-2.5 rounded-full", connected ? "bg-success" : "bg-danger")}
        />
        <span className="text-[13px] leading-none font-semibold text-white">{label}</span>
      </div>
      <div className="px-1 font-mono text-[11px] leading-[1.4] text-text-faint">{detail}</div>
      <div className="px-1 pb-1 font-mono text-[11px] leading-[1.4] text-text-faint">
        {now ? formatClock(now) : " "}
      </div>
    </>
  );
}

function formatClock(ms: number) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).formatToParts(ms);
  const get = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} · ${get("hour")}:${get("minute")} ${get("timeZoneName")}`;
}
