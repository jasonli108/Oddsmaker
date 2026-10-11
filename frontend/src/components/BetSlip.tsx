import { useState } from 'react';
import { api } from '../api/client';
import type { BetReceipt, MarketDetail, MarketTeam } from '../api/types';
import { STAKE_PRESETS } from '../config';
import { coin, multiple, pct } from '../format';
import { useUser } from '../hooks/useUser';

type Props = {
  market: MarketDetail;
  team: MarketTeam;
  /** Called after a bet is accepted so the page can refetch prices and the feed straight away. */
  onPlaced: () => void;
};

export default function BetSlip({ market, team, onPlaced }: Props) {
  const { user, refreshUser } = useUser();
  const [amountText, setAmountText] = useState('100');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<BetReceipt | null>(null);

  const balance = user?.balance ?? 0;
  const stake = Math.max(0, Math.round(Number(amountText) || 0));
  const closed = market.status !== 'open';
  const canBet = !!user && !closed && stake > 0 && stake <= balance && !busy;

  async function placeBet() {
    if (!user) return;
    setBusy(true);
    setError(null);
    try {
      setReceipt(await api.placeBet({ user_id: user.id, market_id: market.id, team_id: team.team_id, stake }));
      await refreshUser();
      onPlaced();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack" style={{ padding: 20, gap: 16 }}>
      <div>
        <div className="dim" style={{ fontSize: 12 }}>Your bet · {market.category}</div>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>{team.name} to win</div>
      </div>

      <div className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
        <Stat label="Current price" value={pct(team.price)} />
        <Stat label="Payout multiple" value={multiple(team.multiple)} />
      </div>

      <div className="stack" style={{ gap: 8 }}>
        <label htmlFor="stake" className="dim small">Hackcoin to stake</label>
        <input
          id="stake"
          className="input mono"
          style={{ height: 52, fontSize: 22 }}
          inputMode="numeric"
          value={amountText}
          onChange={(e) => setAmountText(e.target.value.replace(/[^0-9]/g, ''))}
        />
        <div className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
          {STAKE_PRESETS.map((n) => (
            <button
              key={n}
              className="btn mono"
              style={{ flex: 1, borderColor: n === stake ? 'var(--accent)' : undefined }}
              onClick={() => setAmountText(String(n))}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="stack" style={{ gap: 8, borderTop: '1px solid var(--border)', paddingTop: 14, fontSize: 14 }}>
        <Line label={`If ${team.name} wins`} value={`${coin(stake * team.multiple)} Hackcoin`} accent />
        <Line label="If they don't" value="0 Hackcoin" />
        <Line label="Balance after bet" value={user ? `${coin(balance - stake)} Hackcoin` : '–'} />
      </div>

      <button className="btn primary" style={{ minHeight: 52, fontSize: 16 }} disabled={!canBet} onClick={placeBet}>
        {busy ? 'Placing…' : 'Place bet'}
      </button>

      {!user && <div className="dim small">Pick a display name at the top to get your 1,000 Hackcoin.</div>}
      {closed && <div className="dim small">This market has been resolved.</div>}
      {user && stake > balance && <div className="error">That's more than your balance.</div>}
      {error && <div className="error">{error}</div>}
      {receipt && (
        <div className="small" style={{ color: 'var(--accent)' }}>
          Bet placed: {coin(receipt.stake)} Hackcoin at {pct(receipt.price_at_bet)}, locked at {multiple(receipt.multiple)}.
        </div>
      )}
      <div className="dim" style={{ fontSize: 12 }}>
        Fills instantly from the pool. Your bet moves the price for the next person.
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ flex: 1, background: 'var(--bg)', borderRadius: 8, padding: '10px 12px' }}>
      <div className="dim" style={{ fontSize: 12 }}>{label}</div>
      <div className="mono" style={{ fontSize: 20, fontWeight: 500 }}>{value}</div>
    </div>
  );
}

function Line({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="row between" style={{ flexWrap: 'nowrap' }}>
      <div className="dim">{label}</div>
      <div className="mono" style={accent ? { color: 'var(--accent)', fontWeight: 500 } : undefined}>{value}</div>
    </div>
  );
}
