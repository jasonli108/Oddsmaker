import { useEffect, useState } from 'react';

/**
 * The landing page's market preview: a made-up market that trades by itself.
 *
 * Nothing here comes from the API. Teams, bettors, prices and Scout's reasons are invented, and
 * the card says "Sample market". It follows the real market's shape (a bet lifts one team and
 * the rest give way; Scout moves a price with a reason) so a host sees what attendees will see.
 */

const TEAMS = [
  { name: 'Team Orbit', color: '#7DB8FF', base: 31 },
  { name: 'Ledgerline', color: '#FFB454', base: 24 },
  { name: 'Parsel', color: '#D2B8FF', base: 18 },
];
const BETTORS = ['Maya', 'Dev', 'Priya', 'Jonah', 'Aiko', 'Sam'];
const STAKES = [25, 40, 50, 75, 120, 200];
const SCOUT_UP = ['finding no similar project on the web', 'its demo went live', 'six commits in the last half hour'];
const SCOUT_DOWN = ['finding three similar projects', 'its demo stopped loading', 'no commits in the last hour'];

const TICK_MS = 2400;
const POINTS = 22; // how many steps of history the chart shows
const W = 400;
const H = 120;
const LOW = 12; // the chart's price range, in percent
const HIGH = 38;

type Trade = {
  id: number;
  team: number;
  delta: number;
  /** Who moved the price and why, split so "Scout" can be coloured. */
  who: string;
  text: string;
};

const pick = <T,>(list: T[]) => list[Math.floor(Math.random() * list.length)];
const clamp = (n: number) => Math.min(HIGH - 3, Math.max(LOW + 2, n));
const y = (price: number) => H - 8 - ((price - LOW) / (HIGH - LOW)) * (H - 16);
const x = (i: number) => (i / (POINTS - 1)) * W;

/** A short invented run-up so the chart doesn't start as three flat lines. */
function openingHistory(): number[][] {
  return TEAMS.map((t, team) =>
    Array.from({ length: POINTS }, (_, i) => {
      const drift = [-9, -4, 3][team] * (1 - i / (POINTS - 1)); // each team walks to its base price
      const wobble = Math.sin(i * 1.7 + team * 2) * 1.2 * (i < POINTS - 1 ? 1 : 0);
      return Math.round(clamp(t.base + drift + wobble));
    }),
  );
}

const FIRST_TRADE: Trade = { id: 0, team: 1, delta: 2, who: 'Scout', text: 'moved Ledgerline from 22% to 24% after finding no similar project on the web.' };

function nextTrade(prices: number[], id: number): Trade {
  const team = Math.floor(Math.random() * TEAMS.length);
  const price = prices[team];
  const { name, base } = TEAMS[team];
  if (id % 3 === 0) {
    // Scout pulls a price back toward where it "should" be, so the market never runs away.
    const up = price < base - 3 ? true : price > base + 3 ? false : Math.random() < 0.5;
    const delta = (up ? 1 : -1) * (2 + Math.floor(Math.random() * 3));
    const to = clamp(price + delta);
    return { id, team, delta: to - price, who: 'Scout', text: `moved ${name} from ${price}% to ${to}% after ${pick(up ? SCOUT_UP : SCOUT_DOWN)}.` };
  }
  const stake = pick(STAKES);
  const to = clamp(price + Math.max(1, Math.round(stake / 50)));
  return { id, team, delta: to - price, who: pick(BETTORS), text: `staked ${stake} Hackcoin on ${name} at ${price}%.` };
}

export default function SampleMarket() {
  // One piece of state, so the chart and the trade that moved it can never disagree.
  const [{ history, trade }, setMarket] = useState(() => ({ history: openingHistory(), trade: FIRST_TRADE }));

  useEffect(() => {
    // Someone who asked their system for less motion gets the still version.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = setInterval(() => {
      setMarket((prev) => {
        const prices = prev.history.map((series) => series[series.length - 1]);
        const next = nextTrade(prices, prev.trade.id + 1);
        const history = prev.history.map((series, team) => {
          // The team traded moves; the others each give up a little, as in the real market.
          const moved = team === next.team ? prices[team] + next.delta : prices[team] - Math.sign(next.delta) * (Math.random() < 0.5 ? 1 : 0);
          return [...series.slice(1), clamp(moved)];
        });
        return { history, trade: next };
      });
    }, TICK_MS);
    return () => clearInterval(timer);
  }, []);

  const prices = history.map((series) => series[series.length - 1]);
  const order = TEAMS.map((_, i) => i).sort((a, b) => prices[b] - prices[a]);
  const leader = order[0];
  const stepPath = (series: number[]) => series.reduce((d, p, i) => (i === 0 ? `M0 ${y(p)}` : `${d} H${x(i)} V${y(p)}`), '');

  return (
    <div className="card stack sample-market" style={{ flex: '1 1 400px', minWidth: 0, borderRadius: 16, padding: 22 }}>
      <div className="row between" style={{ flexWrap: 'nowrap', alignItems: 'baseline' }}>
        <div style={{ fontSize: 17, fontWeight: 600 }}>Who takes 1st place overall?</div>
        <div className="row dim" style={{ fontSize: 12, flex: 'none', gap: 6, flexWrap: 'nowrap' }}>
          <span className="pulse-dot" aria-hidden />
          Sample market
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden style={{ display: 'block', width: '100%', height: H, overflow: 'visible' }}>
        <defs>
          <linearGradient id="sample-leader-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={TEAMS[leader].color} stopOpacity="0.22" />
            <stop offset="1" stopColor={TEAMS[leader].color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <g stroke="var(--border)" strokeWidth={1} strokeDasharray="2 5">
          {[15, 20, 25, 30, 35].map((p) => (
            <line key={p} x1={0} x2={W} y1={y(p)} y2={y(p)} vectorEffect="non-scaling-stroke" />
          ))}
        </g>
        <path d={`${stepPath(history[leader])} V${H} H0 Z`} fill="url(#sample-leader-fill)" />
        <g fill="none" strokeWidth={2} strokeLinejoin="round">
          {[...order].reverse().map((team) => (
            <path key={team} d={stepPath(history[team])} stroke={TEAMS[team].color} vectorEffect="non-scaling-stroke" />
          ))}
        </g>
        {/* Where each price is right now. */}
        {order.map((team) => (
          <g key={team} fill={TEAMS[team].color}>
            <circle cx={W} cy={y(prices[team])} r={7} opacity={0.18} />
            <circle cx={W} cy={y(prices[team])} r={3.5} />
          </g>
        ))}
      </svg>

      <div>
        {order.map((team) => {
          const moved = trade.team === team && trade.delta !== 0;
          return (
            <div key={team} className="row" style={{ flexWrap: 'nowrap', padding: '12px 0', borderTop: '1px solid var(--border)' }}>
              <span className="dot" aria-hidden style={{ background: TEAMS[team].color }} />
              <div style={{ flex: 1, minWidth: 0, fontWeight: 500 }}>{TEAMS[team].name}</div>
              {moved && (
                <span key={trade.id} className="mono tick-flash" style={{ fontSize: 12, color: trade.delta > 0 ? 'var(--good)' : 'var(--danger)' }}>
                  {trade.delta > 0 ? '▲' : '▼'} {Math.abs(trade.delta)}
                </span>
              )}
              <div className="mono" style={{ fontSize: 18, fontWeight: 500 }}>{prices[team]}%</div>
              <div className="mono dim" style={{ fontSize: 13, width: 44, textAlign: 'right' }}>{(100 / prices[team]).toFixed(1)}x</div>
            </div>
          );
        })}
      </div>

      <div
        key={trade.id}
        className="soft fade-in"
        style={{ background: 'var(--bg)', border: `1px solid ${trade.who === 'Scout' ? 'var(--amber-border)' : 'var(--border)'}`, borderRadius: 10, padding: '12px 14px', fontSize: 14, minHeight: 68 }}
      >
        <span style={{ color: trade.who === 'Scout' ? 'var(--amber)' : 'var(--text)', fontWeight: 500 }}>{trade.who}</span> {trade.text}
      </div>
    </div>
  );
}
