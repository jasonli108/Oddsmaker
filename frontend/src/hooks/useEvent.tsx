import { createContext, useContext, type ReactNode } from 'react';
import { api } from '../api/client';
import type { EventInfo } from '../api/types';
import { EVENT_NAME, STARTING_BALANCE, SUBMISSIONS_CLOSE } from '../config';
import { usePolling } from './usePolling';

type EventContext = {
  /** The event the host saved in setup, or null before setup has been run. */
  event: EventInfo | null;
  /** False until we know whether an event has been saved, so `event: null` can be trusted. */
  ready: boolean;
  /** Always usable: the saved event's details, falling back to the defaults in config.ts. */
  name: string;
  slug: string;
  submissionsClose: Date;
  /** Hackcoin a new player starts with. Fixed once an event is launched. */
  startingBalance: number;
  /** Re-read the event now, e.g. straight after the host launches it. */
  refreshEvent: () => Promise<void>;
};

const slugify = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'event';

const Ctx = createContext<EventContext | null>(null);

export function EventProvider({ children }: { children: ReactNode }) {
  // A 404 just means setup hasn't been run; the defaults cover that.
  const { data, error, refresh } = usePolling(api.getEvent, 'event', 60_000);

  const value: EventContext = {
    event: data,
    ready: data !== null || error !== null,
    name: data?.name ?? EVENT_NAME,
    slug: data?.slug ?? slugify(EVENT_NAME),
    submissionsClose: data?.submissions_close_at ? new Date(data.submissions_close_at) : SUBMISSIONS_CLOSE,
    startingBalance: data?.starting_balance ?? STARTING_BALANCE,
    refreshEvent: refresh,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useEvent(): EventContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useEvent must be used inside <EventProvider>');
  return ctx;
}
