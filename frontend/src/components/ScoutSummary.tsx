import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { MarketTeam } from '../api/types';
import { clock, pct } from '../format';
import { usePolling } from '../hooks/usePolling';
import Stat from './Stat';

/** The Scout panel under the bet slip: Scout's odds against the market price for the selected team. */
export default function ScoutSummary({ team }: { team: MarketTeam }) {
  const { data } = usePolling(() => api.getTeamReport(team.team_id), team.team_id, 30_000);
  const report = data?.report;

  const diff = Math.round(team.scout_odds * 100) - Math.round(team.price * 100);
  const gap =
    diff === 0
      ? 'Scout and market agree.'
      : `Scout rates this team ${Math.abs(diff)} points ${diff > 0 ? 'higher' : 'lower'} than the market does.`;

  return (
    <div className="card stack" style={{ padding: 20 }}>
      <div className="row between" style={{ flexWrap: 'nowrap', alignItems: 'baseline' }}>
        <h2>Scout report · {team.name}</h2>
        {data?.created_at && (
          <div className="dim" style={{ fontSize: 12, flex: 'none' }}>
            Updated {clock(data.created_at)}
            {data.stale && ' (stale)'}
          </div>
        )}
      </div>
      <div className="row" style={{ gap: 10, flexWrap: 'nowrap' }}>
        <Stat label="Scout's odds" value={pct(team.scout_odds)} />
        <Stat label="Market price" value={pct(team.price)} />
      </div>
      <div style={{ color: 'var(--amber)', fontSize: 14 }}>{gap}</div>
      {report ? (
        // The short label goes here; the full finding is on the Scout reports tab.
        <div style={{ fontSize: 14 }}>
          <Row label="Originality" value={report.originality.label} />
          <Row label="Build progress" value={report.build.label} />
          <Row label="Demo link" value={report.demo.label} />
          <Row label="Prize fit" value={report.prize_fit.label} />
        </div>
      ) : (
        <div className="dim small">{data ? 'Scout has not reported on this team yet.' : 'Loading…'}</div>
      )}
      <Link className="btn" to={`/reports/${team.team_id}`} style={{ display: 'grid', placeItems: 'center' }}>
        Read full report
      </Link>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="row between" style={{ flexWrap: 'nowrap', padding: '9px 0', borderTop: '1px solid var(--border)' }}>
      <div className="dim" style={{ flex: 'none' }}>{label}</div>
      <div style={{ textAlign: 'right' }}>{value}</div>
    </div>
  );
}
