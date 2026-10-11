import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, api } from '../api/client';
import type { User } from '../api/types';
import { POLL_MS } from '../config';
import { useEvent } from './useEvent';

/**
 * No real accounts: the player's id lives in this browser's localStorage and nowhere else.
 * A player belongs to one event, so each event remembers its own id.
 */
const STORAGE_KEY = 'oddsmaker.userId';
const keyFor = (eventSlug: string) => `${STORAGE_KEY}.${eventSlug}`;

type UserContext = {
  /** The player this browser is in the current event, if it has joined. */
  user: User | null;
  /** False until the first check for a remembered user has finished, so the header doesn't flash the join form. */
  ready: boolean;
  /** Join the current event with this display name and remember it in this browser. */
  join: (displayName: string) => Promise<void>;
  /** Re-read the balance now, e.g. straight after placing a bet. */
  refreshUser: () => Promise<void>;
};

const Ctx = createContext<UserContext | null>(null);

/** The id this browser plays under in an event, including one saved before events were separate. */
async function rememberedUser(eventSlug: string): Promise<User | null> {
  const id = localStorage.getItem(keyFor(eventSlug));
  if (id) return api.getUser(id);
  const old = localStorage.getItem(STORAGE_KEY);
  if (!old) return null;
  const user = await api.getUser(old);
  if (user.event_slug !== eventSlug) return null;
  localStorage.setItem(keyFor(eventSlug), old);
  return user;
}

export function UserProvider({ children }: { children: ReactNode }) {
  const { slug } = useEvent();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const liveSlug = useRef(slug);

  const refreshUser = useCallback(async () => {
    if (!slug) return;
    try {
      const found = await rememberedUser(slug);
      if (liveSlug.current === slug) setUser(found);
    } catch (e) {
      // Forget the user only if the server says they don't exist (e.g. the database was reset).
      // A dropped connection must not sign anyone out.
      if (e instanceof ApiError && e.status === 404 && liveSlug.current === slug) {
        localStorage.removeItem(keyFor(slug));
        setUser(null);
      }
    }
  }, [slug]);

  const join = useCallback(
    async (displayName: string) => {
      if (!slug) throw new Error('Open an event before joining.');
      const created = await api.createUser(displayName, slug);
      localStorage.setItem(keyFor(slug), created.id);
      setUser(created);
    },
    [slug],
  );

  // Poll the balance: a market resolving pays out without the user doing anything.
  useEffect(() => {
    liveSlug.current = slug;
    setUser(null);
    setReady(false);
    refreshUser().finally(() => liveSlug.current === slug && setReady(true));
    const timer = setInterval(refreshUser, POLL_MS);
    return () => clearInterval(timer);
  }, [slug, refreshUser]);

  return <Ctx.Provider value={{ user, ready, join, refreshUser }}>{children}</Ctx.Provider>;
}

export function useUser(): UserContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useUser must be used inside <UserProvider>');
  return ctx;
}
