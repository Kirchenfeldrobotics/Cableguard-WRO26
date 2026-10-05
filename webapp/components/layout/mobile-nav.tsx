"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/brand/logo";
import { isActive, useNavItems } from "@/components/layout/nav";
import { useLinkStatus } from "@/components/layout/sidebar";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";
import { routes } from "@/lib/routes";

/**
 * Phone header: the robot link stays in sight on every screen, as it does in the sidebar
 * footer on desktop. Tapping it opens the connection details under Robot settings.
 */
export function MobileTopBar() {
  const { connected, label, detail, brief } = useLinkStatus();
  const { user, signOut } = useAuth();

  return (
    <header className="sticky top-0 z-30 bg-ink pt-[env(safe-area-inset-top)] lg:hidden">
      <div className="flex h-14 items-center gap-3 px-4">
        <Link href={routes.dashboard} aria-label="CableGuard dashboard" className="flex-none">
          <Logo className="mx-0 w-[104px]" />
        </Link>

        <Link
          href={routes.settings}
          aria-label={`Robot link: ${label}, ${detail}`}
          className="ml-auto flex min-w-0 items-center gap-2 rounded-control px-2 py-1.5"
        >
          <span
            aria-hidden
            className={cn("block size-2.5 flex-none rounded-full", connected ? "bg-success" : "bg-danger")}
          />
          <span className="flex min-w-0 flex-col gap-1">
            <span className="truncate text-[13px] leading-none font-semibold text-white">{label}</span>
            <span className="truncate font-mono text-[11px] leading-none text-text-faint">{brief}</span>
          </span>
        </Link>

        <button
          type="button"
          onClick={signOut}
          title={user ? `Signed in as ${user.username}` : undefined}
          className="flex-none rounded-control px-2 py-2 text-xs leading-none font-semibold text-text-inverse-muted active:bg-ink-soft"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}

/** Phone navigation: one thumb-reach tab per screen, fixed to the bottom edge. */
export function TabBar() {
  const pathname = usePathname();
  const { items, recording } = useNavItems();

  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-30 bg-ink pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="m-0 flex h-(--tabbar-h) list-none p-0 px-1">
        {items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-full flex-col items-center justify-center gap-1 text-[11px] leading-none font-semibold transition-colors",
                  active ? "text-white" : "text-text-faint",
                )}
              >
                <span
                  className={cn(
                    "relative rounded-full px-4 py-1 transition-colors",
                    active && "bg-ink-soft",
                  )}
                >
                  {item.icon}
                  {/* A run is recording: the live screen has something to show. */}
                  {item.href === routes.live && recording && (
                    <span
                      aria-hidden
                      className="absolute top-0.5 right-3 block size-2 rounded-full bg-danger ring-2 ring-ink"
                    />
                  )}
                </span>
                {item.short}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
