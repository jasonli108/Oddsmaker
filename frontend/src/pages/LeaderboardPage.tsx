import { api } from '../api/client';
import { coin } from '../format';
import { usePolling } from '../hooks/usePolling';
import { useUser } from '../hooks/useUser';

export default function LeaderboardPage() {
  const { user } = useUser();
  const { data, error } = usePolling(api.getLeaderboard, 'leaderboard');

  return (
    <div className="container stack" style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 720 }}>
      <h1>Leaderboard</h1>
      <div className="dim">Ranked by Hackcoin balance. Final once every market resolves.</div>
      {error && !data && <div className="error">Could not load the leaderboard: {error.message}</div>}
      {data?.map((row) => (
        <div key={row.user_id} className={`card row between ${row.user_id === user?.id ? 'selected' : ''}`} style={{ padding: '12px 18px' }}>
          <div className="row">
            <span className="mono dim" style={{ width: 28 }}>{row.rank}</span>
            <span style={{ fontWeight: 500 }}>{row.display_name}</span>
          </div>
          <span className="mono">{coin(row.balance)} Hackcoin</span>
        </div>
      ))}
    </div>
  );
}
