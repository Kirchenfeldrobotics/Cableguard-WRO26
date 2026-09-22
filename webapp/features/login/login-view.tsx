"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/heading";
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

        <form className="mt-3.5 rounded-card bg-surface p-[26px]" onSubmit={submit}>
          <PageHeader title="Sign in" />
          <p className="mt-[18px] text-sm leading-normal text-text-muted">
            Operator access to the rope inspection console.
          </p>

          <div className="mt-[22px] flex flex-col gap-3.5">
            <Field
              id="username"
              label="Username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={setUsername}
            />
            <Field
              id="password"
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={setPassword}
            />
          </div>

          {error && <Notice>{error}</Notice>}

          <Button
            type="submit"
            size="lg"
            className="mt-[22px] w-full"
            disabled={submitting || !username.trim() || !password}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  ...props
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value" | "id">) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-[13px] leading-none font-semibold text-text-muted">
        {label}
      </label>
      <input
        id={id}
        name={id}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-control border border-border bg-white px-3.5 py-3 text-sm"
        {...props}
      />
    </div>
  );
}
