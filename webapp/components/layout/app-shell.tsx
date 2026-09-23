"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { MobileTopBar, TabBar } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/lib/auth/auth-context";
import { RobotLinkProvider } from "@/lib/robot/robot-link";
import { routes } from "@/lib/routes";

/**
 * Decides what a page is allowed to show: the login screen on its own, or the
 * navigation and the robot link once an operator is signed in. Nothing renders
 * while the stored token is still being checked.
 *
 * Desktop gets the sidebar, phones a top bar and a bottom tab bar (below `lg`).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const onLoginScreen = pathname === routes.login;

  useEffect(() => {
    if (status === "signed-out" && !onLoginScreen) router.replace(routes.login);
    if (status === "signed-in" && onLoginScreen) router.replace(routes.dashboard);
  }, [status, onLoginScreen, router]);

  if (status === "loading") return <Splash>Checking session…</Splash>;

  if (onLoginScreen) {
    // The redirect above is already on its way.
    return status === "signed-in" ? <Splash>Signing in…</Splash> : <>{children}</>;
  }

  if (status === "signed-out") return <Splash>Redirecting to sign in…</Splash>;

  return (
    <RobotLinkProvider>
      <div className="flex min-h-screen flex-col bg-canvas lg:flex-row lg:p-3">
        <MobileTopBar />
        <Sidebar />
        <main className="min-w-0 flex-auto px-4 pt-5 pb-[calc(var(--tabbar-h)+env(safe-area-inset-bottom)+40px)] lg:max-w-[1280px] lg:px-[30px] lg:pt-[22px] lg:pb-[60px]">
          {children}
        </main>
        <TabBar />
      </div>
    </RobotLinkProvider>
  );
}

function Splash({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-3">
      <p className="text-sm leading-none text-text-subtle">{children}</p>
    </div>
  );
}
