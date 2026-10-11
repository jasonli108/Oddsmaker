import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { coin } from '../format';
import { usePolling } from '../hooks/usePolling';
import { useUser } from '../hooks/useUser';

export default function LeaderboardPage() {
  const { user } = useUser();
  const board = usePolling(api.getLeaderboard, 'leaderboard');
  const markets = usePolling(api.listMarkets, 'leaderboard-markets');

  const total = markets.data?.length ?? 0;
  const resolved = markets.data?.filter((m) => m.status === 'resolved').length ?? 0;
  const final = total > 0 && resolved === total;

  return (
    <div className="container stack" style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 720 }}>
      <div className="row" style={{ gap: 12 }}>
        <h1>Leaderboard</h1>
        {final && <span className="badge-accent">Final</span>}
      </div>
      <div className="dim">
        {final
          ? 'Every market has paid out. These are the final standings.'
          : `Ranked by Hackcoin balance.${
              markets.data ? ` ${resolved} of ${total} markets resolved so far.` : ''
            } Final once every market pays out.`}
      </div>

      {!board.data && !board.error && <div className="dim">Loading…</div>}
      {!board.data && board.error && <div className="error">Could not load the leaderboard: {board.error.message}</div>}
      {board.data && board.error && (
        <div className="small" style={{ color: 'var(--amber)' }}>Can't reach the server. Showing the last standings we got.</div>
      )}
      {board.data?.length === 0 && (
        <div className="card stack" style={{ alignItems: 'flex-start' }}>
          <div>Nobody has joined yet. Pick a display name at the top to be first.</div>
          <Link className="btn" to="/" style={{ display: 'grid', placeItems: 'center' }}>
            See the markets
          </Link>
        </div>
      )}

      {board.data?.map((row) => {
        const isYou = row.user_id === user?.id;
        return (
          <Link
            key={row.user_id}
            to={`/summary/${row.user_id}`}
            className={`card row between ${isYou ? 'selected' : ''}`}
            style={{ padding: '12px 18px', flexWrap: 'nowrap', textDecoration: 'none', color: 'inherit' }}
            title={`View ${row.display_name}'s summary and historical trades`}
          >
            <div className="row" style={{ flexWrap: 'nowrap', minWidth: 0 }}>
              <span className="mono dim" style={{ width: 28, flex: 'none' }}>{row.rank}</span>
              <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {row.display_name}
              </span>
              {isYou && <span className="badge-accent" style={{ flex: 'none' }}>You</span>}
            </div>
            <div className="row" style={{ gap: 14, flex: 'none' }}>
              <span className="mono">{coin(row.balance)} Hackcoin</span>
              <span className="dim small">Trades →</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
