import { createContext, useContext, type ReactNode } from 'react';
import { matchPath, useLocation } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import type { EventInfo } from '../api/types';
import { STARTING_BALANCE } from '../config';
import { useNow } from './useNow';
import { usePolling } from './usePolling';

type EventContext = {
  /**
   * The event this page is about: the one named in the address (/e/:slug, /host/:slug,
   * /setup/live/:slug). On pages that name none, the deployment's first event, which the landing
   * page offers as "See a live market". Null while loading, or when there is no such event.
   */
  event: EventInfo | null;
  /** False until we know whether the event exists, so `event: null` can be trusted. */
  ready: boolean;
  /** The address names an event that doesn't exist. */
  notFound: boolean;
  /** The slug in the address, else the first event's. Undefined when no event has been launched. */
  slug: string | undefined;
  name: string;
  /** Null when the host gave no deadline. */
  submissionsClose: Date | null;
  /** Hackcoin a new player of this event starts with. */
  startingBalance: number;
};

/** The routes whose address says which event they are about. */
const EVENT_ROUTES = ['/e/:slug/*', '/host/:slug', '/setup/live/:slug'];

function slugInAddress(pathname: string): string | undefined {
  for (const route of EVENT_ROUTES) {
    const slug = matchPath(route, pathname)?.params.slug;
    if (slug) return slug;
  }
  return undefined;
}

const Ctx = createContext<EventContext | null>(null);

export function EventProvider({ children }: { children: ReactNode }) {
  const inAddress = slugInAddress(useLocation().pathname);
  const { data, error } = usePolling(
    () => (inAddress ? api.getEvent(inAddress) : api.getFirstEvent()),
    inAddress ?? '',
    60_000,
  );

  const value: EventContext = {
    event: data,
    ready: data !== null || error !== null,
    notFound: !!inAddress && !data && error instanceof ApiError && error.status === 404,
    slug: inAddress ?? data?.slug,
    name: data?.name ?? '',
    submissionsClose: data?.submissions_close_at ? new Date(data.submissions_close_at) : null,
    startingBalance: data?.starting_balance ?? STARTING_BALANCE,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useEvent(): EventContext {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useEvent must be used inside <EventProvider>');
  return ctx;
}

/**
 * Whether the event's submission deadline has passed. From then on team sign-up and betting are
 * closed and the host may pick winners; before it, the reverse. Never true for an event with no
 * deadline (only the sample event): that one stays open until the host picks each winner. The
 * server enforces all of this; here it only decides what to show.
 */
export function useSubmissionsClosed(): boolean {
  const { submissionsClose } = useEvent();
  const now = useNow();
  return !!submissionsClose && now >= submissionsClose.getTime();
}

/** The event slug for a page under a route that names one (see EVENT_ROUTES). */
export function useEventSlug(): string {
  const { slug } = useEvent();
  if (!slug) throw new Error('useEventSlug must be used on a page whose address names an event');
  return slug;
}
