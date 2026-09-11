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
  /** Request key the result belongs to. */
  for: string | null;
  data?: T;
  error?: Error;
}

/**
 * Loads data in the browser and re-runs whenever `key` changes.
 * Pass `null` as key to skip loading (e.g. while an id is unknown).
 * `refreshMs` re-polls in the background without clearing current data.
 */
export function useApi<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  { refreshMs }: { refreshMs?: number } = {},
): ApiState<T> {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<Result<T>>({ for: null });
  const requestKey = key === null ? null : `${key}#${nonce}`;

  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    if (requestKey === null) return;

    let cancelled = false;
    const load = () =>
      fetcherRef.current().then(
        (data) => {
          if (!cancelled) setResult({ for: requestKey, data });
        },
        (err: unknown) => {
          if (cancelled) return;
          const error = err instanceof Error ? err : new Error(String(err));
          setResult((prev) => ({ for: requestKey, data: prev.data, error }));
        },
      );

    load();
    const timer = refreshMs ? setInterval(load, refreshMs) : undefined;

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [requestKey, refreshMs]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return {
    data: result.data,
    error: result.error,
    loading: requestKey !== null && result.for !== requestKey,
    reload,
  };
}
