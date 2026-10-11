import type { MarketHistory } from '../api/types';
import { pct } from '../format';

/**
 * TODO(frontend): draw the chart. This is one of the three things the demo can't cut.
 *
 * `history.series` is one entry per team, each with per-minute `points` ({ time, price }),
 * oldest first, served from the Tiger Data continuous aggregate. The design draws a step
 * line per team in the team's colour on an 800x220 viewBox with dashed gridlines, a
 * percent axis on the right and a time axis below: see the <svg> in
 * brainstorming/Hackathon market screens – Markets tab.html.
 */
export default function PriceChart({ history }: { history: MarketHistory | null }) {
  return (
    <div className="card stack">
      <div className="row small" style={{ gap: 18 }}>
        {history?.series.map((s) => (
          <div key={s.team_id} className="row" style={{ gap: 7 }}>
            <span className="dot" style={{ background: s.color }} />
            <span className="dim">{s.name}</span>
            <span className="mono">{s.points.length ? pct(s.points[s.points.length - 1].price) : '–'}</span>
          </div>
        ))}
      </div>
      <div
        className="dim small"
        style={{ height: 220, display: 'grid', placeItems: 'center', border: '1px dashed var(--border)', borderRadius: 8 }}
      >
        {history ? `Price chart goes here (${history.series[0]?.points.length ?? 0} points per team loaded)` : 'Loading…'}
      </div>
    </div>
  );
}
