import type { MarketTeam } from '../api/types';
import { multiple, pct } from '../format';

type Props = {
  team: MarketTeam;
  selected: boolean;
  onSelect: () => void;
  /** The market is resolved: no more bets, the row only selects a team to read about. */
  closed: boolean;
  isWinner: boolean;
};

export default function TeamRow({ team, selected, onSelect, closed, isWinner }: Props) {
  const label = closed ? (selected ? 'Viewing' : 'View') : selected ? 'Selected' : 'Bet';

  return (
    <div className={`card row ${selected ? 'selected' : ''}`} style={{ padding: '14px 18px', gap: '14px 18px' }}>
      <span className="dot" aria-hidden style={{ background: team.color }} />
      <div style={{ flex: '1 1 240px', minWidth: 0 }}>
        <div className="row" style={{ gap: 10 }}>
          <span style={{ fontWeight: 500, fontSize: 16 }}>{team.name}</span>
          {isWinner && <span className="badge-accent">Winner</span>}
        </div>
        <div className="dim small">{team.idea}</div>
      </div>
      <div className="dim" style={{ fontSize: 12, border: '1px solid var(--border-strong)', borderRadius: 6, padding: '4px 9px' }}>
        Scout says <span className="mono" style={{ color: 'var(--text)' }}>{pct(team.scout_odds)}</span>
      </div>
      <div style={{ width: 96, textAlign: 'right' }}>
        <div className="mono" style={{ fontSize: 22, fontWeight: 500, lineHeight: 1.1 }}>{pct(team.price)}</div>
        <div className="mono dim" style={{ fontSize: 12 }}>{multiple(team.multiple)} payout</div>
      </div>
      <button
        className={`btn ${selected ? 'primary' : ''}`}
        style={{ minWidth: 92, fontWeight: 600, borderColor: selected ? undefined : 'var(--border-bold)' }}
        aria-pressed={selected}
        onClick={onSelect}
      >
        {label}
      </button>
    </div>
  );
}
