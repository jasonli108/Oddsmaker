import type { EventDraft } from '../../api/types';

/**
 * The event draft, carried from "paste your link" to "confirm details". It lives in
 * sessionStorage so a reload doesn't lose it; nothing reaches the server until Launch.
 */
const KEY = 'oddsmaker.setupDraft';

export function loadDraft(): EventDraft | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as EventDraft) : null;
  } catch {
    return null;
  }
}

export const saveDraft = (draft: EventDraft) => sessionStorage.setItem(KEY, JSON.stringify(draft));

export const clearDraft = () => sessionStorage.removeItem(KEY);

/** For a host with no event page: nothing filled in, and one empty prize category to start from. */
export function blankDraft(): EventDraft {
  return {
    name: '',
    hosted_by: null,
    location: null,
    starts_at: null,
    submissions_close_at: null,
    source_url: null,
    categories: [{ name: '', prize: null, market_id: null, create_market: true }],
    missing: [],
    is_sample: false,
  };
}
