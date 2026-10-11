import type {
  BetCreate,
  BetReceipt,
  FeedItem,
  LeaderboardEntry,
  MarketDetail,
  MarketHistory,
  MarketSummary,
  ResolveResult,
  Team,
  TeamCreate,
  TeamReport,
  User,
} from './types';

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api`;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) {
    // FastAPI puts a string in `detail` for our own errors and a list for validation errors.
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText || 'Request failed');
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown, headers?: HeadersInit) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body), headers });

export const api = {
  listMarkets: () => request<MarketSummary[]>('/markets'),
  getMarket: (id: string) => request<MarketDetail>(`/markets/${id}`),
  getHistory: (id: string) => request<MarketHistory>(`/markets/${id}/history`),
  getFeed: (id: string) => request<FeedItem[]>(`/markets/${id}/feed`),
  placeBet: (bet: BetCreate) => post<BetReceipt>('/bets', bet),
  resolveMarket: (id: string, winnerTeamId: string, hostPassword: string) =>
    post<ResolveResult>(`/markets/${id}/resolve`, { winner_team_id: winnerTeamId }, { 'X-Host-Password': hostPassword }),

  listTeams: () => request<Team[]>('/teams'),
  createTeam: (team: TeamCreate) => post<Team>('/teams', team),
  getTeamReport: (id: string) => request<TeamReport>(`/teams/${id}/report`),

  createUser: (displayName: string) => post<User>('/users', { display_name: displayName }),
  getUser: (id: string) => request<User>(`/users/${id}`),
  getLeaderboard: () => request<LeaderboardEntry[]>('/leaderboard'),
};
