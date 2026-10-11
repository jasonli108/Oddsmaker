import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { ApiError, api } from '../api/client';
import type { User } from '../api/types';
import { POLL_MS } from '../config';

/** No real accounts: the user's id lives in this browser's localStorage and nowhere else. */
const STORAGE_KEY = 'oddsmaker.userId';

type UserContext = {
  user: User | null;
  /** False until the first check for a remembered user has finished, so the header doesn't flash the join form. */
  ready: boolean;
  /** Create a user with this display name and remember it in this browser. */
  join: (displayName: string) => Promise<void>;
  /** Re-read the balance now, e.g. straight after placing a bet. */
  refreshUser: () => Promise<void>;
};

const Ctx = createContext<UserContext | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const refreshUser = useCallback(async () => {
    const id = localStorage.getItem(STORAGE_KEY);
    if (!id) return;
    try {
      setUser(await api.getUser(id));
    } catch (e) {
      // Forget the user only if the server says they don't exist (e.g. the database was reset).
      // A dropped connection must not sign anyone out.
      if (e instanceof ApiError && e.status === 404) {
        localStorage.removeItem(STORAGE_KEY);
        setUser(null);
      }
    }
  }, []);

  const join = useCallback(async (displayName: string) => {
    const created = await api.createUser(displayName);
    localStorage.setItem(STORAGE_KEY, created.id);
    setUser(created);
  }, []);

  // Poll the balance: a market resolving pays out without the user doing anything.
  useEffect(() => {
    refreshUser().finally(() => setReady(true));
    const timer = setInterval(refreshUser, POLL_MS);
    return () => clearInterval(timer);
  }, [refreshUser]);

  return <Ctx.Provider value={{ user, ready, join, refreshUser }}>{children}</Ctx.Provider>;
}

export function useUser(): UserContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useUser must be used inside <UserProvider>');
  return ctx;
}
