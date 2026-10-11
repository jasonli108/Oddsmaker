import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import type { User } from '../api/types';

/** No real accounts: the user's id lives in this browser's localStorage and nowhere else. */
const STORAGE_KEY = 'oddsmaker.userId';

type UserContext = {
  user: User | null;
  /** Create a user with this display name and remember it in this browser. */
  join: (displayName: string) => Promise<void>;
  /** Re-read the balance, e.g. after placing a bet. */
  refreshUser: () => Promise<void>;
};

const Ctx = createContext<UserContext | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const refreshUser = useCallback(async () => {
    const id = localStorage.getItem(STORAGE_KEY);
    if (!id) return;
    try {
      setUser(await api.getUser(id));
    } catch {
      // The id no longer exists (e.g. the database was reset). Ask for a name again.
      localStorage.removeItem(STORAGE_KEY);
      setUser(null);
    }
  }, []);

  const join = useCallback(async (displayName: string) => {
    const created = await api.createUser(displayName);
    localStorage.setItem(STORAGE_KEY, created.id);
    setUser(created);
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  return <Ctx.Provider value={{ user, join, refreshUser }}>{children}</Ctx.Provider>;
}

export function useUser(): UserContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useUser must be used inside <UserProvider>');
  return ctx;
}
