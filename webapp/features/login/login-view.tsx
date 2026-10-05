"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/card";
import { Notice } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/heading";
import { Field, Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth/auth-context";

export function LoginView() {
  const { signIn, signInWithNfc } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // The NFC tag on the robot opens /login#nfc=<key>. The key sits in the URL
  // fragment, which the browser never sends to a server, and is removed from
  // the address bar before it is used.
  useEffect(() => {
    const key = new URLSearchParams(window.location.hash.slice(1)).get("nfc");
    if (!key) return;
    window.history.replaceState(null, "", window.location.pathname);

    signInWithNfc(key).catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "NFC sign in failed"),
    );
  }, [signInWithNfc]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn(username.trim(), password);
      // The shell swaps in the console as soon as the status changes.
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-3">
      <div className="w-full max-w-[420px]">
        <div className="flex justify-center rounded-shell bg-ink px-[18px] py-[26px]">
          <Logo />
        </div>

        <form className="mt-3.5" onSubmit={submit}>
          <Panel>
            <PageHeader title="Sign in" />

            <div className="mt-stack flex flex-col gap-3.5">
              <Field label="Username" htmlFor="username">
                <Input
                  id="username"
                  name="username"
                  required
                  autoComplete="username"
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </Field>
              <Field label="Password" htmlFor="password">
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
            </div>

            {error && <Notice>{error}</Notice>}

            <Button
              type="submit"
              size="lg"
              className="mt-stack w-full"
              disabled={submitting || !username.trim() || !password}
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </Panel>
        </form>
      </div>
    </div>
  );
}
