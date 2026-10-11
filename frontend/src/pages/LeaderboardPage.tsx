import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { coin, pct } from '../format';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEventSlug } from '../hooks/useEvent';
import { usePolling } from '../hooks/usePolling';
import { useUser } from '../hooks/useUser';

type LeaderboardTab = 'teams' | 'forecasters';

export default function LeaderboardPage() {
  const { user } = useUser();
  const path = useAttendeePath();
  const eventSlug = useEventSlug();
  const [activeTab, setActiveTab] = useState<LeaderboardTab>('teams');
  const [selectedMarketId, setSelectedMarketId] = useState<string>('all');

  const markets = usePolling(() => api.listMarkets(eventSlug), `leaderboard-markets-${eventSlug}`);
  const forecastersBoard = usePolling(() => api.getLeaderboard(eventSlug), `leaderboard-users-${eventSlug}`);

  const marketParam = selectedMarketId === 'all' ? undefined : selectedMarketId;
  const teamsBoard = usePolling(
    () => api.getTeamLeaderboard(eventSlug, marketParam),
    `leaderboard-teams-${eventSlug}-${selectedMarketId}`,
  );

  const total = markets.data?.length ?? 0;
  const resolved = markets.data?.filter((m) => m.status === 'resolved').length ?? 0;
  const final = total > 0 && resolved === total;

  const currentCategoryName =
    selectedMarketId === 'all'
      ? 'all prize categories (highest percentage)'
      : markets.data?.find((m) => m.id === selectedMarketId)?.category ?? 'this category';

  return (
    <div className="container stack" style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 840, gap: 20 }}>
      {/* Title & View Switcher */}
      <div className="row between" style={{ alignItems: 'flex-start', gap: 12 }}>
        <div className="stack" style={{ gap: 6 }}>
          <div className="row" style={{ gap: 12 }}>
            <h1>Leaderboard</h1>
            {final && <span className="badge-accent">Final</span>}
          </div>
          <div className="dim">
            {activeTab === 'teams'
              ? `Ranked by the highest percentage of Scout's odds in ${currentCategoryName}.`
              : final
              ? 'Every market has paid out. These are the final player standings.'
              : `Ranked by Hackcoin balance.${
                  markets.data ? ` ${resolved} of ${total} markets resolved so far.` : ''
                } Final once every market pays out.`}
          </div>
        </div>

        {/* View Switcher: Teams (Scout Odds) vs Forecasters */}
        <div className="row" style={{ gap: 6, background: 'var(--bg)', padding: 4, borderRadius: 'var(--radius-control)', border: '1px solid var(--border)' }}>
          <button
            className={`btn small pill ${activeTab === 'teams' ? 'active' : ''}`}
            onClick={() => setActiveTab('teams')}
            style={{ minHeight: 34, padding: '0 14px', fontSize: 13 }}
          >
            Teams (Scout's odds)
          </button>
          <button
            className={`btn small pill ${activeTab === 'forecasters' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecasters')}
            style={{ minHeight: 34, padding: '0 14px', fontSize: 13 }}
          >
            Forecasters (Balance)
          </button>
        </div>
      </div>

      {/* Teams Leaderboard View */}
      {activeTab === 'teams' && (
        <div className="stack" style={{ gap: 16 }}>
          {/* Category Filter Pills */}
          <div className="row" style={{ gap: 8 }}>
            <button
              className={`btn pill ${selectedMarketId === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedMarketId('all')}
              style={{ minHeight: 34, padding: '0 14px', fontSize: 13 }}
            >
              All (Highest Odds)
            </button>
            {markets.data?.map((m) => (
              <button
                key={m.id}
                className={`btn pill ${selectedMarketId === m.id ? 'active' : ''}`}
                onClick={() => setSelectedMarketId(m.id)}
                style={{ minHeight: 34, padding: '0 14px', fontSize: 13 }}
              >
                {m.category}
              </button>
            ))}
          </div>

          {!teamsBoard.data && !teamsBoard.error && <div className="dim">Loading teams by Scout's odds…</div>}
          {!teamsBoard.data && teamsBoard.error && (
            <div className="error">Could not load the team leaderboard: {teamsBoard.error.message}</div>
          )}
          {teamsBoard.data && teamsBoard.error && (
            <div className="small" style={{ color: 'var(--amber)' }}>
              Can't reach the server. Showing the last standings we got.
            </div>
          )}

          {teamsBoard.data?.length === 0 && (
            <div className="card stack" style={{ alignItems: 'flex-start' }}>
              <div>No teams have signed up yet. Sign up a team to see Scout's report and odds.</div>
              <Link className="btn primary" to={path('/signup')} style={{ display: 'grid', placeItems: 'center' }}>
                Sign up a team
              </Link>
            </div>
          )}

          {teamsBoard.data?.map((row) => (
            <div
              key={`${row.team_id}-${row.market_id}`}
              className="card row between"
              style={{ padding: '14px 20px', gap: 16, alignItems: 'center', flexWrap: 'nowrap' }}
            >
              {/* Rank & Team Details */}
              <div className="row" style={{ flexWrap: 'nowrap', gap: 14, minWidth: 0, flex: '1 1 auto' }}>
                <span
                  className="mono"
                  style={{
                    width: 32,
                    fontSize: 18,
                    fontWeight: 600,
                    color: row.rank === 1 ? 'var(--amber)' : row.rank <= 3 ? 'var(--text)' : 'var(--text-dim)',
                    flex: 'none',
                  }}
                >
                  #{row.rank}
                </span>

                <span className="dot" style={{ background: row.color, width: 12, height: 12, flex: 'none' }} />

                <div className="stack" style={{ gap: 3, minWidth: 0, overflow: 'hidden' }}>
                  <div className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
                    <Link
                      to={path(`/reports/${row.team_id}`)}
                      title="View Scout report"
                      style={{
                        fontWeight: 600,
                        fontSize: 16,
                        color: 'var(--text)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {row.name}
                    </Link>
                    {selectedMarketId === 'all' && (
                      <span className="badge-amber" style={{ flex: 'none', fontSize: 11, padding: '1px 8px' }}>
                        in {row.market_category}
                      </span>
                    )}
                  </div>
                  <div className="dim small" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {row.idea}
                  </div>
                </div>
              </div>

              {/* Scout Odds & Price Comparison */}
              <div className="row" style={{ gap: 20, flex: 'none', alignItems: 'center' }}>
                <div className="stack" style={{ gap: 2, alignItems: 'flex-end', minWidth: 90 }}>
                  <span className="mono" style={{ fontSize: 22, fontWeight: 600, color: 'var(--accent)', lineHeight: 1.1 }}>
                    {pct(row.scout_odds)}
                  </span>
                  <span className="dim small" style={{ fontSize: 11 }}>
                    Scout's odds
                  </span>
                </div>

                <div className="stack" style={{ gap: 2, alignItems: 'flex-end', minWidth: 80 }}>
                  <span className="mono" style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-soft)' }}>
                    {pct(row.market_price)}
                  </span>
                  <span className="dim small" style={{ fontSize: 11 }}>
                    market price
                  </span>
                </div>

                <div className="row" style={{ gap: 8 }}>
                  <Link
                    className="btn small"
                    to={path(`/reports/${row.team_id}`)}
                    title="View full Scout analysis"
                    style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}
                  >
                    Report →
                  </Link>
                  <Link
                    className="btn small primary"
                    to={path(`/?market=${row.market_id}&team=${row.team_id}`)}
                    title="Bet on this team in the market"
                    style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}
                  >
                    Bet →
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Forecasters Leaderboard View */}
      {activeTab === 'forecasters' && (
        <div className="stack" style={{ gap: 10 }}>
          {!forecastersBoard.data && !forecastersBoard.error && <div className="dim">Loading forecasters…</div>}
          {!forecastersBoard.data && forecastersBoard.error && (
            <div className="error">Could not load the leaderboard: {forecastersBoard.error.message}</div>
          )}
          {forecastersBoard.data && forecastersBoard.error && (
            <div className="small" style={{ color: 'var(--amber)' }}>
              Can't reach the server. Showing the last standings we got.
            </div>
          )}
          {forecastersBoard.data?.length === 0 && (
            <div className="card stack" style={{ alignItems: 'flex-start' }}>
              <div>Nobody has joined yet. Pick a display name at the top to be first.</div>
              <Link className="btn" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
                See the markets
              </Link>
            </div>
          )}

          {forecastersBoard.data?.map((row) => {
            const isYou = row.user_id === user?.id;
            return (
              <Link
                key={row.user_id}
                to={path(`/summary/${row.user_id}`)}
                className={`card row between ${isYou ? 'selected' : ''}`}
                style={{ padding: '12px 18px', flexWrap: 'nowrap', textDecoration: 'none', color: 'inherit' }}
                title={`View ${row.display_name}'s summary and historical trades`}
              >
                <div className="row" style={{ flexWrap: 'nowrap', minWidth: 0 }}>
                  <span className="mono dim" style={{ width: 28, flex: 'none' }}>
                    #{row.rank}
                  </span>
                  <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {row.display_name}
                  </span>
                  {isYou && (
                    <span className="badge-accent" style={{ flex: 'none' }}>
                      You
                    </span>
                  )}
                </div>
                <div className="row" style={{ gap: 14, flex: 'none' }}>
                  <span className="mono">{coin(row.balance)} Hackcoin</span>
                  <span className="dim small">Trades →</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
