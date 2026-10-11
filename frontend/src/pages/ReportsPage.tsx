import { NavLink, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { ScoutReport } from '../api/types';
import { clock } from '../format';
import { usePolling } from '../hooks/usePolling';

/**
 * Scout reports tab: one report per team, with sources.
 *
 * TODO(frontend): this is a plain rendering of the data. The design for this screen is the
 * "Reports" page in the Oddsmaker design canvas (linked from the build spec); `odds_history`
 * on the report response is there for a small chart of Scout's odds over time.
 */
export default function ReportsPage() {
  const { teamId } = useParams();
  const teams = usePolling(api.listTeams, 'teams', 60_000);
  const selectedId = teamId ?? teams.data?.[0]?.id;

  return (
    <div className="container two-col">
      <nav className="side stack" style={{ gap: 8, flex: '0 1 260px' }}>
        {teams.data?.map((t) => (
          <NavLink key={t.id} to={`/reports/${t.id}`} className="card row" style={{ padding: '12px 16px', flexWrap: 'nowrap' }}>
            <span className="dot" style={{ background: t.color }} />
            <span style={{ color: t.id === selectedId ? 'var(--text)' : undefined, fontWeight: 500 }}>{t.name}</span>
          </NavLink>
        ))}
      </nav>
      <div className="main">{selectedId && <Report teamId={selectedId} />}</div>
    </div>
  );
}

function Report({ teamId }: { teamId: string }) {
  const { data, error } = usePolling(() => api.getTeamReport(teamId), teamId, 30_000);

  if (error && !data) return <div className="error">Could not load this report: {error.message}</div>;
  if (!data) return <div className="dim">Loading…</div>;

  const { team, report } = data;
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div>
        <h1>{team.name}</h1>
        <div className="dim">{team.idea}</div>
        {data.created_at && (
          <div className="dim small">
            Scout report from {clock(data.created_at)}
            {data.stale && ' · some sources could not be reached, showing the last good report'}
          </div>
        )}
      </div>
      {report ? <ReportBody report={report} /> : <div className="card dim">Scout has not reported on this team yet.</div>}
    </div>
  );
}

function ReportBody({ report }: { report: ScoutReport }) {
  const sections = [
    { title: 'Originality', ...report.originality },
    { title: 'Build progress', ...report.build },
    { title: 'Demo', ...report.demo },
    { title: 'Prize fit', ...report.prize_fit },
  ];
  return (
    <>
      <div className="card" style={{ borderColor: 'var(--amber-border)' }}>
        <div className="small" style={{ color: 'var(--amber)' }}>Scout's read · {report.change_note}</div>
        <div style={{ fontSize: 17 }}>{report.read}</div>
      </div>

      <div className="quad">
        {sections.map((s) => (
          <div key={s.title} className="card">
            <div className="row between" style={{ flexWrap: 'nowrap' }}>
              <h2>{s.title}</h2>
              <span className="badge-amber" style={{ flex: 'none' }}>{s.label}</span>
            </div>
            <div className="soft" style={{ marginTop: 8, fontSize: 14 }}>{s.finding}</div>
          </div>
        ))}
      </div>

      {report.originality.similar && report.originality.similar.length > 0 && (
        <div className="card">
          <h2>Similar projects found</h2>
          <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
            {report.originality.similar.map((p) => (
              <li key={p.url}>
                <a href={p.url} target="_blank" rel="noreferrer">{p.title}</a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>Scores by prize</h2>
        <div className="row" style={{ gap: 24, marginTop: 8 }}>
          {Object.entries(report.scores).map(([category, score]) => (
            <div key={category}>
              <div className="dim small">{category.replace('_', ' ')}</div>
              <div className="mono" style={{ fontSize: 22 }}>{score}</div>
            </div>
          ))}
        </div>
      </div>

      {report.sources && report.sources.length > 0 && (
        <div className="card">
          <h2>Sources</h2>
          <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
            {report.sources.map((s) => (
              <li key={s.url}>
                <span className="dim small">{s.kind}</span>{' '}
                <a href={s.url} target="_blank" rel="noreferrer">{s.url}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
