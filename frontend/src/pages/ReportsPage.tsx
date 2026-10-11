import { Link, NavLink, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { MarketTeam, ScoutReport, TeamReport } from '../api/types';
import Stat from '../components/Stat';
import { HEADLINE_MARKET_ID, SCOUT_INTERVAL_MS } from '../config';
import { clock, countdown, pct, plural, points } from '../format';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useNow } from '../hooks/useNow';
import { usePolling } from '../hooks/usePolling';
import { labelColor, sourceKindLabel } from '../scout';

/** A gap this wide between Scout and the market is worth calling out in amber. */
const NOTABLE_GAP_POINTS = 5;

/** Scout reports tab: one report per team, with sources, against the headline market's price. */
export default function ReportsPage() {
  const { teamId } = useParams();
  const path = useAttendeePath();
  const market = usePolling(() => api.getMarket(HEADLINE_MARKET_ID), 'reports-market');
  const teams = market.data?.teams ?? [];

  // A team that has just signed up has a report page before it shows up in the market.
  const selectedId = teamId ?? teams[0]?.team_id;
  const report = usePolling(
    () => (selectedId ? api.getTeamReport(selectedId) : Promise.resolve(null)),
    selectedId ?? 'none',
    30_000,
  );

  return (
    <div className="container two-col">
      <nav className="stack" aria-label="Teams" style={{ flex: '1 1 300px', minWidth: 0, gap: 8 }}>
        <NextRefresh report={report.data} />
        {teams.map((t) => (
          <TeamLink key={t.team_id} team={t} selected={t.team_id === selectedId} />
        ))}
      </nav>

      <div className="main">
        {!market.data && market.error && <div className="error">Could not load teams: {market.error.message}</div>}
        {market.data && teams.length === 0 && !teamId && (
          <div className="card stack" style={{ alignItems: 'flex-start' }}>
            <div>No teams have signed up yet, so Scout has nothing to report on.</div>
            <Link className="btn primary" to={path('/signup')} style={{ display: 'grid', placeItems: 'center' }}>
              Sign up a team
            </Link>
          </div>
        )}
        {selectedId && !report.data && !report.error && <div className="dim">Loading report…</div>}
        {selectedId && !report.data && report.error && (
          <div className="error">Could not load this report: {report.error.message}</div>
        )}
        {report.data && (
          <Report
            data={report.data}
            marketTeam={teams.find((t) => t.team_id === report.data?.team.id)}
            marketOpen={market.data?.status === 'open'}
          />
        )}
      </div>
    </div>
  );
}

function NextRefresh({ report }: { report: TeamReport | null }) {
  const now = useNow();
  if (!report?.created_at) return null;
  const left = new Date(report.created_at).getTime() + SCOUT_INTERVAL_MS - now;
  return (
    <div className="dim" style={{ fontSize: 12, padding: '0 4px 4px' }}>
      {left > 0 ? (
        <>
          Next refresh in <span className="mono" style={{ color: 'var(--text)' }}>{countdown(left)}</span>
        </>
      ) : (
        'Refresh due any moment'
      )}
    </div>
  );
}

function gapText(gap: number): string {
  if (gap === 0) return 'Scout agrees with the market';
  return `Scout ${plural(Math.abs(gap), 'point')} ${gap > 0 ? 'above' : 'below'} market`;
}

function TeamLink({ team, selected }: { team: MarketTeam; selected: boolean }) {
  const gap = points(team.scout_odds, team.price);
  const path = useAttendeePath();
  return (
    <NavLink
      to={path(`/reports/${team.team_id}`)}
      className={`card row between ${selected ? 'selected' : ''}`}
      style={{ padding: '14px 16px', minHeight: 64, flexWrap: 'nowrap', color: 'var(--text)' }}
    >
      <span style={{ minWidth: 0 }}>
        <span className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
          <span className="dot" aria-hidden style={{ width: 8, height: 8, background: team.color }} />
          <span style={{ fontWeight: 500 }}>{team.name}</span>
        </span>
        <span
          style={{
            display: 'block',
            fontSize: 12,
            color: Math.abs(gap) >= NOTABLE_GAP_POINTS ? 'var(--amber)' : 'var(--text-dim)',
          }}
        >
          {gapText(gap)}
        </span>
      </span>
      <span className="mono" style={{ fontSize: 13, textAlign: 'right', flex: 'none' }}>
        <span style={{ display: 'block' }}>{pct(team.scout_odds)} scout</span>
        <span className="dim" style={{ display: 'block' }}>{pct(team.price)} market</span>
      </span>
    </NavLink>
  );
}

type ReportProps = {
  data: TeamReport;
  /** Missing while a newly signed-up team is not in the market yet. */
  marketTeam: MarketTeam | undefined;
  marketOpen: boolean;
};

function Report({ data, marketTeam, marketOpen }: ReportProps) {
  const { team, report } = data;
  const history = data.odds_history.filter((p) => p.market_id === HEADLINE_MARKET_ID);
  const path = useAttendeePath();

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="row between" style={{ gap: 16, alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div className="dim" style={{ fontSize: 12 }}>
            Scout report
            {data.created_at && ` · updated ${clock(data.created_at)}`}
            {data.stale && ' · some sources could not be reached, showing the last good report'}
          </div>
          <h1 style={{ margin: '4px 0 6px' }}>{team.name}</h1>
          <div className="soft">{team.idea}</div>
        </div>
        {marketTeam && marketOpen && (
          <Link
            className="btn primary"
            to={path(`?team=${team.id}`)}
            style={{ display: 'grid', placeItems: 'center', minHeight: 48, padding: '0 22px', fontSize: 15 }}
          >
            Bet on {team.name} at {pct(marketTeam.price)}
          </Link>
        )}
      </div>

      {report ? (
        <ReportBody report={report} marketTeam={marketTeam} history={history} hasDemo={!!team.demo_url} />
      ) : (
        <div className="card dim">Scout is writing its first report on this team. Check back in a minute.</div>
      )}
    </div>
  );
}

type BodyProps = {
  report: ScoutReport;
  marketTeam: MarketTeam | undefined;
  history: TeamReport['odds_history'];
  hasDemo: boolean;
};

function ReportBody({ report, marketTeam, history, hasDemo }: BodyProps) {
  const sections = [
    { title: 'Originality', ...report.originality, how: 'Checked with web search across project galleries and product sites.' },
    { title: 'Build progress', ...report.build, how: 'Read from the public repo the team submitted.' },
    { title: 'Demo link', ...report.demo, how: hasDemo ? 'Extracted from the deployed page the team submitted.' : null },
    { title: 'Prize fit', ...report.prize_fit, how: 'Compared against the prize criteria on the event page.' },
  ];

  // Scout lists the similar projects it found separately; they are sources too.
  const listed = new Set((report.sources ?? []).map((s) => s.url));
  const sources = [
    ...(report.sources ?? []).map((s) => ({ url: s.url, text: s.url, kind: sourceKindLabel(s.kind) })),
    ...(report.originality.similar ?? [])
      .filter((p) => !listed.has(p.url))
      .map((p) => ({ url: p.url, text: p.title, kind: sourceKindLabel('similar') })),
  ];

  const latest = history[history.length - 1];
  const previous = history[history.length - 2];
  const change = latest && previous ? points(latest.odds, previous.odds) : null;

  return (
    <>
      <div className="card stack" style={{ padding: '20px 22px' }}>
        <h2>Scout's read</h2>
        <div style={{ fontSize: 17, lineHeight: 1.5 }}>{report.read}</div>
        <div className="row" style={{ gap: 10 }}>
          <Stat label="Scout's odds" value={marketTeam ? pct(marketTeam.scout_odds) : '–'} />
          <Stat label="Market price" value={marketTeam ? pct(marketTeam.price) : '–'} />
          <Stat
            label="Change since last report"
            value={change === null ? '–' : `${change > 0 ? '+' : ''}${change} ${change === 1 || change === -1 ? 'pt' : 'pts'}`}
          />
        </div>
      </div>

      <div className="quad">
        {sections.map((s) => (
          <div key={s.title} className="card stack" style={{ gap: 10 }}>
            <div className="row between" style={{ flexWrap: 'nowrap', alignItems: 'baseline', gap: 10 }}>
              <h3>{s.title}</h3>
              <div style={{ fontSize: 12, fontWeight: 500, flex: 'none', color: labelColor(s.label) }}>{s.label}</div>
            </div>
            <div className="soft" style={{ fontSize: 14 }}>{s.finding}</div>
            {s.how && <div className="dim small">{s.how}</div>}
          </div>
        ))}
      </div>

      {sources.length > 0 && (
        <div className="card">
          <h2 style={{ marginBottom: 8 }}>Sources Scout read</h2>
          <div style={{ fontSize: 14 }}>
            {sources.map((s) => (
              <div key={s.url} className="row between" style={tableRow}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: 'var(--text)', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {s.text}
                </a>
                <div className="dim" style={{ flex: 'none' }}>{s.kind}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="card">
          <h2 style={{ marginBottom: 8 }}>How Scout's odds have moved</h2>
          <div style={{ fontSize: 14 }}>
            {[...history].reverse().map((p) => (
              <div key={p.time} className="row" style={{ ...tableRow, gap: 16 }}>
                <div className="mono dim" style={{ flex: '0 0 76px' }}>{clock(p.time)}</div>
                <div className="mono" style={{ flex: '0 0 44px' }}>{pct(p.odds)}</div>
                <div className="soft" style={{ minWidth: 0 }}>{p.note}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

const tableRow = { flexWrap: 'nowrap', padding: '9px 0', borderTop: '1px solid var(--border)' } as const;
