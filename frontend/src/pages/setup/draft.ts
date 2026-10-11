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

/** For a host with no event page: nothing filled in, and the four markets that always exist. */
export function blankDraft(): EventDraft {
  return {
    name: '',
    hosted_by: null,
    location: null,
    starts_at: null,
    submissions_close_at: null,
    source_url: null,
    categories: [
      { name: 'Best overall', prize: null, market_id: 'overall' },
      { name: 'Best use of Nimble', prize: null, market_id: 'nimble' },
      { name: 'Best use of Gemini', prize: null, market_id: 'gemini' },
      { name: 'Best use of Tiger Data', prize: null, market_id: 'tiger_data' },
    ],
    missing: [],
    is_sample: false,
  };
}
