import { useCallback, useEffect, useRef, useState } from 'react';
import { POLL_MS } from '../config';

/**
 * Fetch now, then again every `intervalMs` (pass 0 to fetch once). Refetches when `key` changes.
 * Keeps showing the last good data if a later poll fails.
 */
export function usePolling<T>(fetcher: () => Promise<T>, key: string, intervalMs = POLL_MS) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const liveKey = useRef(key);

  const refresh = useCallback(async () => {
    const requestedFor = liveKey.current;
    try {
      const next = await fetcherRef.current();
      if (liveKey.current === requestedFor) {
        setData(next);
        setError(null);
      }
    } catch (e) {
      if (liveKey.current === requestedFor) setError(e as Error);
    }
  }, []);

  useEffect(() => {
    liveKey.current = key;
    setData(null);
    setError(null);
    refresh();
    if (!intervalMs) return;
    const timer = setInterval(refresh, intervalMs);
    return () => clearInterval(timer);
  }, [key, intervalMs, refresh]);

  return { data, error, refresh };
}
