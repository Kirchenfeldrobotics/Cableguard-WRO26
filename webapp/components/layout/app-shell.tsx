"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { useAuth } from "@/lib/auth/auth-context";
import { RobotLinkProvider } from "@/lib/robot/robot-link";
import { routes } from "@/lib/routes";

/**
 * Decides what a page is allowed to show: the login screen on its own, or the
 * sidebar and the robot link once an operator is signed in. Nothing renders
 * while the stored token is still being checked.
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
      <div className="flex min-h-screen flex-col gap-3 bg-canvas p-3 lg:flex-row lg:gap-0">
        <Sidebar />
        <main className="min-w-0 flex-auto px-4 pt-[22px] pb-[60px] lg:max-w-[1280px] lg:px-[30px]">
          {children}
        </main>
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
