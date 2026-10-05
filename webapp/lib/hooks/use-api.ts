"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | undefined;
  error: Error | undefined;
  /** True until the first response for the current key has arrived. */
  loading: boolean;
  reload: () => void;
}

interface Result<T> {
  /** Key the result belongs to. */
  for: string | null;
  data?: T;
  error?: Error;
}

/**
 * Loads data in the browser and re-runs whenever `key` changes.
 * Pass `null` as key to skip loading (e.g. while an id is unknown).
 * `refreshMs` re-polls and `reload` fetches again, both in the background: the data on
 * screen stays until the new answer replaces it.
 */
export function useApi<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  { refreshMs }: { refreshMs?: number } = {},
): ApiState<T> {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<Result<T>>({ for: null });

  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    if (key === null) return;

    let cancelled = false;
    const load = () =>
      fetcherRef.current().then(
        (data) => {
          if (!cancelled) setResult({ for: key, data });
        },
        (err: unknown) => {
          if (cancelled) return;
          const error = err instanceof Error ? err : new Error(String(err));
          setResult((prev) => ({ for: key, data: prev.data, error }));
        },
      );

    load();
    const timer = refreshMs ? setInterval(load, refreshMs) : undefined;

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // `nonce` is not read in here, a new one is what makes the effect load again.
  }, [key, nonce, refreshMs]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return {
    data: result.data,
    error: result.error,
    loading: key !== null && result.for !== key,
    reload,
  };
}
