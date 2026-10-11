import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import type { MarketDetail, MarketTeam } from '../api/types';
import BetSlip from '../components/BetSlip';
import PriceChart from '../components/PriceChart';
import ScoutSummary from '../components/ScoutSummary';
import TeamRow from '../components/TeamRow';
import TradeFeed from '../components/TradeFeed';
import { coin, plural } from '../format';
import { usePolling } from '../hooks/usePolling';

export default function MarketsPage() {
  // /?market=gemini&team=orbit opens that market with that team picked, e.g. from a Scout report.
  const [params] = useSearchParams();
  const [marketId, setMarketId] = useState(params.get('market') ?? 'overall');
  const [pickedTeamId, setPickedTeamId] = useState(params.get('team'));

  const markets = usePolling(api.listMarkets, 'markets', 0);
  const market = usePolling(() => api.getMarket(marketId), marketId);
  const history = usePolling(() => api.getHistory(marketId), marketId);
  const feed = usePolling(() => api.getFeed(marketId), marketId);

  const m = market.data;
  const teams = m?.teams ?? [];
  const picked = teams.find((t) => t.team_id === pickedTeamId) ?? teams[0];
  const closed = m?.status === 'resolved';
  const winner = closed ? teams.find((t) => t.team_id === m?.winner_team_id) : undefined;

  function afterBet() {
    market.refresh();
    history.refresh();
    feed.refresh();
  }

  return (
    <div className="container two-col">
      <div className="main stack" style={{ gap: 22 }}>
        <div className="stack">
          <div className="row" style={{ gap: 8 }}>
            {markets.data?.map((mk) => (
              <button
                key={mk.id}
                className={`btn pill ${mk.id === marketId ? 'active' : ''}`}
                aria-pressed={mk.id === marketId}
                onClick={() => setMarketId(mk.id)}
              >
                {mk.category}
              </button>
            ))}
          </div>
          {!m && !market.error && <div className="dim">Loading market…</div>}
          {!m && market.error && <div className="error">Could not load this market: {market.error.message}</div>}
          {m && (
            <>
              <h1>{m.title}</h1>
              <div className="row dim small" style={{ gap: 20 }}>
                <div>{plural(m.totals.team_count, 'team')}</div>
                <div>{coin(m.totals.hackcoin_traded)} Hackcoin traded</div>
                <div>{plural(m.totals.forecaster_count, 'forecaster')}</div>
                <div>{closed ? 'Resolved' : 'Resolves when judges announce'}</div>
              </div>
              {market.error && (
                <div className="small" style={{ color: 'var(--amber)' }}>
                  Can't reach the server. Showing the last prices we got.
                </div>
              )}
            </>
          )}
        </div>

        {m && teams.length === 0 ? (
          <div className="card stack" style={{ alignItems: 'flex-start' }}>
            <div>No teams have signed up yet, so there is nothing to bet on.</div>
            <Link className="btn primary" to="/signup" style={{ display: 'grid', placeItems: 'center' }}>
              Sign up a team
            </Link>
          </div>
        ) : (
          <>
            <PriceChart history={history.data} pickedTeamId={picked?.team_id} />

            <div className="stack" style={{ gap: 8 }}>
              <div className="row between dim" style={{ fontSize: 12, padding: '0 18px' }}>
                <div>Team</div>
                <div>Chance to win · payout multiple</div>
              </div>
              {teams.map((t) => (
                <TeamRow
                  key={t.team_id}
                  team={t}
                  selected={t.team_id === picked?.team_id}
                  onSelect={() => setPickedTeamId(t.team_id)}
                  closed={closed}
                  isWinner={t.team_id === winner?.team_id}
                />
              ))}
            </div>

            <TradeFeed feed={feed.data} error={feed.error} />
          </>
        )}
      </div>

      <div className="side stack" style={{ gap: 18 }}>
        {m && picked && (
          <>
            {closed ? <Result market={m} winner={winner} /> : <BetSlip market={m} team={picked} onPlaced={afterBet} />}
            <ScoutSummary team={picked} />
          </>
        )}
      </div>
    </div>
  );
}

/** Takes the bet slip's place once the host has picked a winner. */
function Result({ market, winner }: { market: MarketDetail; winner: MarketTeam | undefined }) {
  return (
    <div className="card stack" style={{ padding: 20, borderColor: 'var(--accent)' }}>
      <div>
        <div className="dim" style={{ fontSize: 12 }}>Result · {market.category}</div>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>
          {winner ? `${winner.name} won` : 'This market is resolved'}
        </div>
      </div>
      <div className="dim" style={{ fontSize: 14 }}>
        Betting is closed. Bets on the winner paid their stake times the multiple locked in when the bet was placed.
        Every other bet paid nothing.
      </div>
      <Link className="btn" to="/leaderboard" style={{ display: 'grid', placeItems: 'center' }}>
        See the leaderboard
      </Link>
    </div>
  );
}
