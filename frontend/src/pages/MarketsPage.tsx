import { useState } from 'react';
import { api } from '../api/client';
import BetSlip from '../components/BetSlip';
import PriceChart from '../components/PriceChart';
import ScoutSummary from '../components/ScoutSummary';
import TeamRow from '../components/TeamRow';
import TradeFeed from '../components/TradeFeed';
import { coin } from '../format';
import { usePolling } from '../hooks/usePolling';

export default function MarketsPage() {
  const [marketId, setMarketId] = useState('overall');
  const [pickedTeamId, setPickedTeamId] = useState<string | null>(null);

  const markets = usePolling(api.listMarkets, 'markets', 0);
  const market = usePolling(() => api.getMarket(marketId), marketId);
  const history = usePolling(() => api.getHistory(marketId), marketId);
  const feed = usePolling(() => api.getFeed(marketId), marketId);

  const teams = market.data?.teams ?? [];
  const picked = teams.find((t) => t.team_id === pickedTeamId) ?? teams[0];

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
            {markets.data?.map((m) => (
              <button
                key={m.id}
                className={`btn pill ${m.id === marketId ? 'active' : ''}`}
                onClick={() => setMarketId(m.id)}
              >
                {m.category}
              </button>
            ))}
          </div>
          {market.error && !market.data && <div className="error">Could not load this market: {market.error.message}</div>}
          {market.data && (
            <>
              <h1>{market.data.title}</h1>
              <div className="row dim small" style={{ gap: 20 }}>
                <div>{market.data.totals.team_count} teams</div>
                <div>{coin(market.data.totals.hackcoin_traded)} Hackcoin traded</div>
                <div>{market.data.totals.forecaster_count} forecasters</div>
                <div>{market.data.status === 'open' ? 'Resolves when judges announce' : 'Resolved'}</div>
              </div>
            </>
          )}
        </div>

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
            />
          ))}
        </div>

        <TradeFeed feed={feed.data} />
      </div>

      <div className="side stack" style={{ gap: 18 }}>
        {market.data && picked && (
          <>
            <BetSlip market={market.data} team={picked} onPlaced={afterBet} />
            <ScoutSummary team={picked} />
          </>
        )}
      </div>
    </div>
  );
}
