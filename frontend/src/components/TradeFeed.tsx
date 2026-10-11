import type { FeedItem } from '../api/types';
import { ago, coin, pct } from '../format';

export default function TradeFeed({ feed }: { feed: FeedItem[] | null }) {
  return (
    <div className="card">
      <div className="row between" style={{ marginBottom: 10 }}>
        <h2>Latest trades</h2>
        <div className="dim" style={{ fontSize: 12 }}>Live</div>
      </div>
      {feed && feed.length === 0 && <div className="dim small">No trades yet. Be the first.</div>}
      <div className="trades" tabIndex={0} role="group" aria-label="Latest trades, scroll sideways for older ones">
        {feed?.map((item) => <TradeCard key={item.id} item={item} />)}
      </div>
    </div>
  );
}

function TradeCard({ item }: { item: FeedItem }) {
  const isScout = item.kind === 'scout';
  const who = isScout ? 'Scout' : item.user_display_name;

  return (
    <div className={`trade stack ${isScout ? 'scout' : ''}`} style={{ gap: 10 }}>
      <div className="row between" style={{ flexWrap: 'nowrap', gap: 8 }}>
        <span style={{ fontWeight: 500, fontSize: 14, color: isScout ? 'var(--amber)' : undefined }}>{who}</span>
        <span className="mono dim" style={{ fontSize: 12 }}>{ago(item.time)}</span>
      </div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 500, lineHeight: 1.1 }}>
        {isScout ? `${pct(item.price_from)} to ${pct(item.price_to)}` : `${coin(item.stake)} Hackcoin`}
      </div>
      <div className="row small" style={{ gap: 7, flexWrap: 'nowrap' }}>
        <span className="dot" aria-hidden style={{ width: 8, height: 8, background: item.team_color }} />
        {isScout ? `${item.team_name}, ${item.note}` : `on ${item.team_name} at ${pct(item.price)}`}
      </div>
    </div>
  );
}
