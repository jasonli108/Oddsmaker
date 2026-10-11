import { useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useEvent } from './useEvent';

/**
 * Builds links into the attendee app, which lives under /e/:slug.
 *
 *   const path = useAttendeePath();
 *   path()                 -> /e/ai-engineer-nyc-2026            (Markets)
 *   path('/reports/orbit') -> /e/ai-engineer-nyc-2026/reports/orbit
 *   path('?team=orbit')    -> /e/ai-engineer-nyc-2026?team=orbit
 *
 * Inside the attendee app it keeps the slug already in the address; elsewhere (landing, host
 * page) it uses the saved event's slug. The slug is not used to fetch anything.
 */
export function useAttendeePath(): (suffix?: string) => string {
  const { slug: inAddress } = useParams();
  const { slug: fromEvent } = useEvent();
  const slug = inAddress ?? fromEvent;
  return useCallback((suffix = '') => `/e/${slug}${suffix}`, [slug]);
}
