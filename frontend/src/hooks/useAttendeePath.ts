import { useCallback } from 'react';
import { useEvent } from './useEvent';

/**
 * Builds links into an event's attendee app, which lives under /e/:slug.
 *
 *   const path = useAttendeePath();
 *   path()                 -> /e/ai-engineer-nyc-2026            (Markets)
 *   path('/reports/orbit') -> /e/ai-engineer-nyc-2026/reports/orbit
 *   path('?team=orbit')    -> /e/ai-engineer-nyc-2026?team=orbit
 *
 * The event is the one the current page is about (see useEvent). The slug decides which event's
 * markets, teams and players the attendee app loads. Before any event exists, every link goes home.
 */
export function useAttendeePath(): (suffix?: string) => string {
  const { slug } = useEvent();
  return useCallback((suffix = '') => (slug ? `/e/${slug}${suffix}` : '/'), [slug]);
}
