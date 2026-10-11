import { useCallback, useEffect, useRef, useState } from 'react';
import { POLL_MS } from '../config';

/**
 * Fetch now, then again every `intervalMs` (pass 0 to fetch once). Refetches when `key` changes.
 * Keeps showing the last good data if a later poll fails.
 *
 * What it returns always belongs to the current `key`: straight after the key changes, `data`
 * and `error` are null until the new fetch answers, never the previous key's result.
 */
export function usePolling<T>(fetcher: () => Promise<T>, key: string, intervalMs = POLL_MS) {
  const [result, setResult] = useState<{ key: string; data: T | null; error: Error | null }>({ key, data: null, error: null });
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const liveKey = useRef(key);

  const refresh = useCallback(async () => {
    const requestedFor = liveKey.current;
    try {
      const data = await fetcherRef.current();
      if (liveKey.current === requestedFor) setResult({ key: requestedFor, data, error: null });
    } catch (e) {
      if (liveKey.current === requestedFor) {
        setResult((last) => ({ key: requestedFor, data: last.key === requestedFor ? last.data : null, error: e as Error }));
      }
    }
  }, []);

  useEffect(() => {
    liveKey.current = key;
    refresh();
    if (!intervalMs) return;
    const timer = setInterval(refresh, intervalMs);
    return () => clearInterval(timer);
  }, [key, intervalMs, refresh]);

  const current = result.key === key ? result : null;
  return { data: current?.data ?? null, error: current?.error ?? null, refresh };
}
