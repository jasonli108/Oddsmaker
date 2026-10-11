import type {
  BetCreate,
  BetReceipt,
  EventCreate,
  EventDraft,
  EventInfo,
  FeedItem,
  HostSummary,
  LeaderboardEntry,
  MarketDetail,
  MarketHistory,
  MarketSummary,
  ResolveResult,
  Team,
  TeamCreate,
  TeamReport,
  User,
  UserBet,
  UserSummary,
} from './types';

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api`;

export class ApiError extends Error {
  constructor(
    /** HTTP status, or 0 when the server could not be reached at all. */
    public status: number,
    message: string,
    /** Per-field messages from a validation error, keyed by the request field name. */
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (!res.ok) {
    // FastAPI puts a string in `detail` for our own errors and a list for validation errors.
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    if (Array.isArray(detail)) {
      const fields: Record<string, string> = {};
      for (const issue of detail) {
        const field = String(issue?.loc?.[issue.loc.length - 1] ?? '');
        if (field && !(field in fields)) fields[field] = String(issue?.msg ?? 'Not a valid value');
      }
      throw new ApiError(res.status, 'Some of what you entered needs fixing.', fields);
    }
    if (typeof detail === 'string') throw new ApiError(res.status, detail);
    // A 5xx with no message of ours is the dev proxy or a gateway saying the API is down.
    throw new ApiError(
      res.status,
      res.status >= 500 ? "The server isn't responding. Try again in a moment." : res.statusText || 'Request failed',
    );
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown, headers?: HeadersInit) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body), headers });

/** Host-only routes check this header against HOST_PASSWORD on the server. */
const asHost = (hostPassword: string) => ({ 'X-Host-Password': hostPassword });

export const api = {
  listMarkets: () => request<MarketSummary[]>('/markets'),
  getMarket: (id: string) => request<MarketDetail>(`/markets/${id}`),
  getHistory: (id: string) => request<MarketHistory>(`/markets/${id}/history`),
  getFeed: (id: string) => request<FeedItem[]>(`/markets/${id}/feed`),
  placeBet: (bet: BetCreate) => post<BetReceipt>('/bets', bet),
  resolveMarket: (id: string, winnerTeamId: string, hostPassword: string) =>
    post<ResolveResult>(`/markets/${id}/resolve`, { winner_team_id: winnerTeamId }, asHost(hostPassword)),

  listTeams: () => request<Team[]>('/teams'),
  createTeam: (team: TeamCreate) => post<Team>('/teams', team),
  getTeamReport: (id: string) => request<TeamReport>(`/teams/${id}/report`),
  /** Scout writes a new report on this team now. Takes up to a minute; 429 within 10 minutes of the last run. */
  runScout: (id: string) => post<TeamReport>(`/teams/${id}/scout`, {}),

  createUser: (displayName: string) => post<User>('/users', { display_name: displayName }),
  getUser: (id: string) => request<User>(`/users/${id}`),
  getUserSummary: (id: string) => request<UserSummary>(`/users/${id}/summary`),
  getUserBets: (id: string) => request<UserBet[]>(`/users/${id}/bets`),
  getLeaderboard: () => request<LeaderboardEntry[]>('/leaderboard'),

  getEvent: () => request<EventInfo>('/event'),
  saveEvent: (event: EventCreate, hostPassword: string) =>
    request<EventInfo>('/event', { method: 'PUT', body: JSON.stringify(event), headers: asHost(hostPassword) }),
  extractEvent: (url: string) => post<EventDraft>('/events/extract', { url }),
  getHostSummary: (hostPassword: string) => request<HostSummary>('/host/summary', { headers: asHost(hostPassword) }),
};
