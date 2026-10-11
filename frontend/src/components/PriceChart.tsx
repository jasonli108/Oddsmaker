import type { MarketHistory, TeamSeries } from '../api/types';
import { clock, pct } from '../format';

// viewBox units. The SVG stretches to its container, so strokes use non-scaling-stroke.
const W = 800;
const H = 220;
const PAD = 10; // keeps the 0% and top gridlines off the edges
const GRID_STEPS = 4;
const Y_MAX_OPTIONS = [0.2, 0.4, 0.6, 0.8, 1];
const TOP_N = 4;

type Props = {
  history: MarketHistory | null;
  /** Always drawn, even when it isn't one of the top teams. */
  pickedTeamId?: string;
};

const latest = (s: TeamSeries) => s.points[s.points.length - 1].price;
const round = (n: number) => Math.round(n * 10) / 10;

/** Price history as one step line per team, from the per-minute continuous aggregate. */
export default function PriceChart({ history, pickedTeamId }: Props) {
  const ranked = (history?.series ?? []).filter((s) => s.points.length > 0).sort((a, b) => latest(b) - latest(a));
  const shown = ranked.filter((s, i) => i < TOP_N || s.team_id === pickedTeamId);

  if (shown.length === 0) {
    return (
      <div className="card dim small" style={{ height: 220, display: 'grid', placeItems: 'center' }}>
        {history ? 'No price history yet.' : 'Loading…'}
      </div>
    );
  }

  const start = Math.min(...shown.map((s) => Date.parse(s.points[0].time)));
  const end = Math.max(Date.now(), ...shown.map((s) => Date.parse(s.points[s.points.length - 1].time)));
  const span = Math.max(end - start, 60_000);
  const peak = Math.max(...shown.flatMap((s) => s.points.map((p) => p.price)));
  const yMax = Y_MAX_OPTIONS.find((m) => m >= peak) ?? 1;

  const x = (iso: string) => round(((Date.parse(iso) - start) / span) * W);
  const y = (price: number) => round(H - PAD - (price / yMax) * (H - 2 * PAD));

  // A price holds until the next tick, so each segment runs flat and then jumps.
  const path = (s: TeamSeries) =>
    s.points.reduce(
      (d, p, i) => (i === 0 ? `M${x(p.time)} ${y(p.price)}` : `${d} H${x(p.time)} V${y(p.price)}`),
      '',
    ) + ` H${W}`;

  const gridPrices = Array.from({ length: GRID_STEPS + 1 }, (_, i) => (yMax * (GRID_STEPS - i)) / GRID_STEPS);
  const timeLabels = [0, 1, 2].map((i) => clock(new Date(start + (span * i) / 3).toISOString()));
  const summary = shown.map((s) => `${s.name} ${Math.round(latest(s) * 100)} percent`).join(', ');

  return (
    <div className="card stack">
      <div className="row small" style={{ gap: 18 }}>
        {shown.map((s) => (
          <div key={s.team_id} className="row" style={{ gap: 7 }}>
            <span className="dot" aria-hidden style={{ width: 9, height: 9, background: s.color }} />
            <span className="dim">{s.name}</span>
            <span className="mono" style={{ fontWeight: 500 }}>{pct(latest(s))}</span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={`Price history since the market opened. Now: ${summary}.`}
            style={{ display: 'block', width: '100%', height: H }}
          >
            <g stroke="var(--border)" strokeWidth={1} strokeDasharray="2 5">
              {gridPrices.map((p) => (
                <line key={p} x1={0} x2={W} y1={y(p)} y2={y(p)} vectorEffect="non-scaling-stroke" />
              ))}
            </g>
            <g fill="none" strokeWidth={2} strokeLinejoin="round">
              {/* Lowest first so the leader's line sits on top. */}
              {[...shown].reverse().map((s) => (
                <path key={s.team_id} d={path(s)} stroke={s.color} vectorEffect="non-scaling-stroke" />
              ))}
            </g>
          </svg>
          <div className="row between dim" style={{ fontSize: 12, paddingTop: 8, flexWrap: 'nowrap' }}>
            {timeLabels.map((label, i) => (
              <div key={i}>{label}</div>
            ))}
            <div>Now</div>
          </div>
        </div>
        <div
          className="mono dim"
          aria-hidden
          style={{ height: H, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, textAlign: 'right' }}
        >
          {gridPrices.map((p) => (
            <div key={p}>{pct(p)}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
