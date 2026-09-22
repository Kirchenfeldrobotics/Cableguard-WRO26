"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api/client";
import type { AuthUser, LoginResult } from "@/lib/api/types";
import { clearToken, getToken, onSignedOut, setToken } from "@/lib/auth/session";

export type AuthStatus = "loading" | "signed-in" | "signed-out";

export interface AuthValue {
  /** `loading` while the stored token is being checked against the server. */
  status: AuthStatus;
  user: AuthUser | null;
  /** Rejects with the ApiError from `POST /api/auth/login`. */
  signIn: (username: string, password: string) => Promise<void>;
  /** Rejects with the ApiError from `POST /api/auth/nfc`. */
  signInWithNfc: (key: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

/** Holds the signed-in operator for the whole app. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  // A token in localStorage only counts once the server accepts it, so an
  // expired or revoked one lands on the login screen instead of on errors.
  // The status starts as `loading` on both sides of hydration and is only
  // resolved here, once the browser can read localStorage.
  useEffect(() => {
    let cancelled = false;
    const restore = async () => (getToken() === null ? null : await api.auth.me());

    restore().then(
      (me) => {
        if (cancelled) return;
        setUser(me);
        setStatus(me ? "signed-in" : "signed-out");
      },
      (err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          setUser(null);
          setStatus("signed-out");
          return;
        }
        // The server is unreachable, which is not the same as being signed out:
        // keep the token and let each view report the connection error instead.
        setStatus("signed-in");
      },
    );

    return () => {
      cancelled = true;
    };
  }, []);

  // A 401 on any later request clears the token; follow it here.
  useEffect(
    () =>
      onSignedOut(() => {
        setUser(null);
        setStatus("signed-out");
      }),
    [],
  );

  const accept = useCallback((result: LoginResult) => {
    setToken(result.access_token);
    setUser(result.user);
    setStatus("signed-in");
  }, []);

  const signIn = useCallback(
    async (username: string, password: string) => accept(await api.auth.login(username, password)),
    [accept],
  );

  const signInWithNfc = useCallback(
    async (key: string) => accept(await api.auth.nfcLogin(key)),
    [accept],
  );

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus("signed-out");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, signIn, signInWithNfc, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
