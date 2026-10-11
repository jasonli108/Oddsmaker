import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { UserBet } from '../api/types';
import Stat from '../components/Stat';
import { ago, clock, coin, multiple, pct } from '../format';
import { usePolling } from '../hooks/usePolling';
import { publicOrigin } from '../host';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEvent } from '../hooks/useEvent';
import { useUser } from '../hooks/useUser';

type Filter = 'all' | 'open' | 'won' | 'lost';

export default function SummaryPage() {
  const { userId: routeUserId } = useParams<{ userId?: string }>();
  const { user: currentUser } = useUser();
  const path = useAttendeePath();
  const { startingBalance } = useEvent();
  const [filter, setFilter] = useState<Filter>('all');
  const [copied, setCopied] = useState(false);

  const activeUserId = routeUserId || currentUser?.id;
  const isOwnProfile = !routeUserId || (currentUser && routeUserId === currentUser.id);

  const pollKey = activeUserId ? `user-summary-${activeUserId}` : 'no-user';
  const summaryPoll = usePolling(
    () => (activeUserId ? api.getUserSummary(activeUserId) : Promise.resolve(null)),
    pollKey,
  );

  const summary = summaryPoll.data;
  const error = summaryPoll.error;
  const loading = activeUserId && !summary && !error;

  function onCopyLink() {
    if (!activeUserId) return;
    const url = publicOrigin() + path(`/summary/${activeUserId}`);
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  if (!activeUserId) {
    return (
      <div className="container stack" style={{ paddingTop: 40, maxWidth: 640 }}>
        <h1>Individual Summary</h1>
        <div className="card stack" style={{ gap: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 500 }}>No forecaster selected</div>
          <div className="dim">
            Pick a display name at the top to receive {coin(startingBalance)} Hackcoin, place bets on teams, and view your summary here.
          </div>
          <div className="row" style={{ gap: 12 }}>
            <Link className="btn primary" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
              Explore Markets
            </Link>
            <Link className="btn" to={path('/leaderboard')} style={{ display: 'grid', placeItems: 'center' }}>
              View Leaderboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const allBets = summary?.bets ?? [];
  const filteredBets = allBets.filter((b) => {
    if (filter === 'all') return true;
    return b.status === filter;
  });

  const shareUrl = publicOrigin() + path(`/summary/${activeUserId}`);

  return (
    <div className="container stack" style={{ paddingTop: 28, paddingBottom: 60, maxWidth: 960, gap: 28 }}>
      {/* Page Header */}
      <div className="row between" style={{ alignItems: 'flex-start', gap: 16 }}>
        <div className="stack" style={{ gap: 6 }}>
          <div className="row" style={{ gap: 10 }}>
            <h1>{summary?.user.display_name ?? (loading ? 'Loading profile…' : 'Player profile')}</h1>
            {isOwnProfile && <span className="badge-accent">You</span>}
            {summary?.rank && <span className="badge-amber">Rank #{summary.rank}</span>}
          </div>
          <div className="dim small">
            {isOwnProfile
              ? 'Your personal prediction summary, teams signed up, and trade history.'
              : `Forecaster profile and historical trades for ${summary?.user.display_name ?? 'this player'}.`}
          </div>
        </div>

        {/* Shareable Link button */}
        <div className="stack" style={{ gap: 6, alignItems: 'flex-end' }}>
          <button
            className={`btn ${copied ? 'pill active' : ''}`}
            onClick={onCopyLink}
            title="Copy link to this individual's historical trades"
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <span>{copied ? '✓ Link copied' : 'Copy link to historical trades'}</span>
          </button>
          <div className="mono dim" style={{ fontSize: 11, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {shareUrl}
          </div>
        </div>
      </div>

      {loading && <div className="dim">Loading profile and historical trades…</div>}
      {error && <div className="error">Could not load summary: {error.message}</div>}

      {summary && (
        <>
          {/* Key Metrics Stats */}
          <div className="row" style={{ gap: 12 }}>
            <Stat label="Current balance" value={`${coin(summary.user.balance)} HC`} />
            <div style={{ flex: '1 1 120px', background: 'var(--bg)', borderRadius: 8, padding: '10px 12px' }}>
              <div className="dim" style={{ fontSize: 12 }}>Net Profit / Loss</div>
              <div
                className="mono"
                style={{
                  fontSize: 20,
                  fontWeight: 500,
                  color: summary.net_profit >= 0 ? 'var(--good)' : 'var(--danger)',
                }}
              >
                {summary.net_profit >= 0 ? '+' : ''}
                {coin(summary.net_profit)} HC
              </div>
            </div>
            <Stat label="Total staked" value={`${coin(summary.total_staked)} HC`} />
            <Stat label="Total bets placed" value={String(summary.bet_count)} />
            <Stat label="Winnings paid" value={`${coin(summary.total_payout)} HC`} />
          </div>

          {/* Section: Teams Signed Up */}
          <div className="stack" style={{ gap: 14 }}>
            <div className="row between">
              <h2>{isOwnProfile ? 'Teams you signed up' : `Teams signed up by ${summary.user.display_name}`}</h2>
              {isOwnProfile && (
                <Link className="btn small" to={path('/signup')} style={{ display: 'grid', placeItems: 'center', minHeight: 34 }}>
                  + Sign up another team
                </Link>
              )}
            </div>

            {summary.teams.length === 0 ? (
              <div className="card stack" style={{ gap: 10, padding: 18 }}>
                <div className="dim">
                  {isOwnProfile
                    ? "You haven't signed up a team yet. Enter your project in the hackathon market so Scout can report on it and attendees can bet."
                    : `${summary.user.display_name} has not signed up any teams yet.`}
                </div>
                {isOwnProfile && (
                  <div>
                    <Link className="btn primary" to={path('/signup')} style={{ display: 'inline-grid', placeItems: 'center' }}>
                      Sign up a team
                    </Link>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                {summary.teams.map((t) => (
                  <div key={t.id} className="card stack" style={{ gap: 10, padding: 16 }}>
                    <div className="row between" style={{ flexWrap: 'nowrap', gap: 8 }}>
                      <div className="row" style={{ flexWrap: 'nowrap', gap: 8, minWidth: 0 }}>
                        <span className="dot" style={{ background: t.color, width: 12, height: 12 }} />
                        <span style={{ fontWeight: 600, fontSize: 16, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {t.name}
                        </span>
                      </div>
                      <Link
                        className="badge-accent"
                        to={path(`?team=${t.id}`)}
                        title="View team in markets"
                        style={{ flex: 'none', textDecoration: 'none' }}
                      >
                        In markets
                      </Link>
                    </div>

                    <div className="dim small" style={{ minHeight: 36 }}>{t.idea}</div>

                    <div className="row" style={{ gap: 8, paddingTop: 6, borderTop: '1px solid var(--border)' }}>
                      <Link className="btn small" to={path(`/reports/${t.id}`)} style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}>
                        Scout Report
                      </Link>
                      {t.demo_url && (
                        <a
                          className="btn small"
                          href={t.demo_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}
                        >
                          Demo ↗
                        </a>
                      )}
                      {t.repo_url && (
                        <a
                          className="btn small"
                          href={t.repo_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}
                        >
                          Repo ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section: Bets Placed & Historical Trades */}
          <div className="stack" style={{ gap: 14 }}>
            <div className="row between" style={{ flexWrap: 'wrap', gap: 12 }}>
              <div className="row" style={{ gap: 10 }}>
                <h2>Historical Trades</h2>
                <span className="dim small">({allBets.length} total)</span>
              </div>

              {/* Filters */}
              <div className="row" style={{ gap: 6 }}>
                <button
                  className={`btn pill ${filter === 'all' ? 'active' : ''}`}
                  onClick={() => setFilter('all')}
                  style={{ minHeight: 32, padding: '0 12px', fontSize: 12 }}
                >
                  All ({allBets.length})
                </button>
                <button
                  className={`btn pill ${filter === 'open' ? 'active' : ''}`}
                  onClick={() => setFilter('open')}
                  style={{ minHeight: 32, padding: '0 12px', fontSize: 12 }}
                >
                  Open ({summary.open_bets_count})
                </button>
                <button
                  className={`btn pill ${filter === 'won' ? 'active' : ''}`}
                  onClick={() => setFilter('won')}
                  style={{ minHeight: 32, padding: '0 12px', fontSize: 12 }}
                >
                  Won ({summary.won_bets_count})
                </button>
                <button
                  className={`btn pill ${filter === 'lost' ? 'active' : ''}`}
                  onClick={() => setFilter('lost')}
                  style={{ minHeight: 32, padding: '0 12px', fontSize: 12 }}
                >
                  Lost ({allBets.filter((b) => b.status === 'lost').length})
                </button>
              </div>
            </div>

            {filteredBets.length === 0 ? (
              <div className="card stack" style={{ gap: 10, padding: 20 }}>
                <div className="dim">
                  {filter === 'all'
                    ? 'No trades placed yet. Place your first bet on the markets tab.'
                    : `No ${filter} trades found.`}
                </div>
                {filter === 'all' && (
                  <div>
                    <Link className="btn primary" to={path()} style={{ display: 'inline-grid', placeItems: 'center' }}>
                      Browse Markets
                    </Link>
                  </div>
                )}
              </div>
            ) : (
              <div className="stack" style={{ gap: 8 }}>
                <div
                  className="row between dim small"
                  style={{ padding: '0 18px', fontSize: 12, flexWrap: 'nowrap' }}
                >
                  <div style={{ flex: '1 1 240px' }}>Market & Team</div>
                  <div style={{ flex: '0 0 120px', textAlign: 'right' }}>Stake & Price</div>
                  <div style={{ flex: '0 0 120px', textAlign: 'right' }}>Multiple / Return</div>
                  <div style={{ flex: '0 0 120px', textAlign: 'right' }}>Status</div>
                  <div style={{ flex: '0 0 80px', textAlign: 'right' }}>Action</div>
                </div>

                {filteredBets.map((bet) => (
                  <TradeRow key={bet.id} bet={bet} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function TradeRow({ bet }: { bet: UserBet }) {
  const path = useAttendeePath();
  const isWon = bet.status === 'won';
  const isLost = bet.status === 'lost';
  const isOpen = bet.status === 'open';

  return (
    <div
      className="card row between"
      style={{
        padding: '14px 18px',
        gap: 12,
        alignItems: 'center',
        flexWrap: 'nowrap',
      }}
    >
      {/* Market and Team */}
      <div className="stack" style={{ flex: '1 1 240px', gap: 4, minWidth: 0 }}>
        <div className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
          <span className="dot" style={{ background: bet.team_color, flex: 'none' }} />
          <Link
            to={path(`/reports/${bet.team_id}`)}
            title="View Scout report"
            style={{
              fontWeight: 600,
              color: 'var(--text)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {bet.team_name}
          </Link>
          <span className="dim small" style={{ flex: 'none' }}>in</span>
          <span className="small soft" style={{ flex: 'none' }}>{bet.market_category}</span>
        </div>
        <div className="dim small" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span title={new Date(bet.created_at).toLocaleString()}>{ago(bet.created_at)}</span>
          <span>·</span>
          <span>{clock(bet.created_at)}</span>
        </div>
      </div>

      {/* Stake & Price */}
      <div className="stack" style={{ flex: '0 0 120px', alignItems: 'flex-end', gap: 2 }}>
        <div className="mono" style={{ fontWeight: 500 }}>{coin(bet.stake)} HC</div>
        <div className="mono dim small">at {pct(bet.price_at_bet)}</div>
      </div>

      {/* Multiple & Potential Return */}
      <div className="stack" style={{ flex: '0 0 120px', alignItems: 'flex-end', gap: 2 }}>
        <div className="mono" style={{ fontWeight: 500 }}>{multiple(bet.multiple)}</div>
        <div className="mono dim small">
          {isOpen && `pot. ${coin(bet.potential_payout)} HC`}
          {isWon && <span style={{ color: 'var(--good)' }}>+{coin(bet.payout ?? bet.potential_payout)} HC</span>}
          {isLost && <span style={{ color: 'var(--danger)' }}>- {coin(bet.stake)} HC</span>}
        </div>
      </div>

      {/* Status Badge */}
      <div style={{ flex: '0 0 120px', display: 'flex', justifyContent: 'flex-end' }}>
        {isOpen && <span className="badge-accent">Open</span>}
        {isWon && (
          <span
            className="badge-accent"
            style={{
              color: 'var(--good)',
              borderColor: 'var(--good)',
            }}
          >
            Won
          </span>
        )}
        {isLost && (
          <span
            className="dim small"
            style={{
              border: '1px solid var(--border-strong)',
              borderRadius: 999,
              padding: '2px 8px',
            }}
          >
            Lost
          </span>
        )}
      </div>

      {/* Action Link to Market */}
      <div style={{ flex: '0 0 80px', display: 'flex', justifyContent: 'flex-end' }}>
        <Link
          className="btn small"
          to={path(`?market=${bet.market_id}&team=${bet.team_id}`)}
          title="Open market chart and order book"
          style={{ minHeight: 32, padding: '0 10px', fontSize: 12, display: 'grid', placeItems: 'center' }}
        >
          Market →
        </Link>
      </div>
    </div>
  );
}
