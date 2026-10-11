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
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEventSlug } from '../hooks/useEvent';
import { usePolling } from '../hooks/usePolling';

export default function MarketsPage() {
  // ?market=<id>&team=orbit opens that market with that team picked, e.g. from a Scout report.
  const [params] = useSearchParams();
  const path = useAttendeePath();
  const eventSlug = useEventSlug();
  const [chosenId, setMarketId] = useState(params.get('market'));
  const [pickedTeamId, setPickedTeamId] = useState(params.get('team'));

  const markets = usePolling(() => api.listMarkets(eventSlug), `markets-${eventSlug}`, 0);
  // Only ever one of this event's markets, whatever the address asks for. The first until one is chosen.
  const marketId = (markets.data?.find((mk) => mk.id === chosenId) ?? markets.data?.[0])?.id;
  const key = marketId ?? 'none';
  const market = usePolling(() => (marketId ? api.getMarket(marketId) : Promise.resolve(null)), key);
  const history = usePolling(() => (marketId ? api.getHistory(marketId) : Promise.resolve(null)), key);
  const feed = usePolling(() => (marketId ? api.getFeed(marketId) : Promise.resolve(null)), key);

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
          {markets.error && !markets.data && (
            <div className="error">Could not load this event's markets: {markets.error.message}</div>
          )}
          {markets.data?.length === 0 && <div className="dim">This event has no markets.</div>}
          {!m && !market.error && !markets.error && markets.data?.length !== 0 && <div className="dim">Loading market…</div>}
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
            <Link className="btn primary" to={path('/signup')} style={{ display: 'grid', placeItems: 'center' }}>
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
  const path = useAttendeePath();
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
      <Link className="btn" to={path('/leaderboard')} style={{ display: 'grid', placeItems: 'center' }}>
        See the leaderboard
      </Link>
    </div>
  );
}
