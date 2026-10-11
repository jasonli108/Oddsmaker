import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import type { HostMarketRow, ResolveResult } from '../api/types';
import Stat from '../components/Stat';
import { coin, dateTime, pct, plural } from '../format';
import { hostPassword } from '../host';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEvent, useEventSlug, useSubmissionsClosed } from '../hooks/useEvent';
import { usePolling } from '../hooks/usePolling';

/** The organiser's page for one event: how it is going, and where each market's winner is picked. */
export default function HostPage() {
  const [password, setPassword] = useState(() => hostPassword.get());
  const { notFound } = useEvent();

  function unlock(value: string) {
    hostPassword.set(value);
    setPassword(value);
  }

  function lock() {
    hostPassword.clear();
    setPassword(null);
  }

  return (
    <div className="container stack" style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 920, gap: 22 }}>
      {notFound ? (
        <div className="stack" style={{ maxWidth: 420, alignItems: 'flex-start' }}>
          <h1>We can't find that event</h1>
          <div className="dim">Check the host page link from the last setup screen.</div>
          <Link className="btn" to="/" style={{ display: 'grid', placeItems: 'center' }}>
            Go to Oddsmaker
          </Link>
        </div>
      ) : password ? (
        <Dashboard password={password} onLock={lock} />
      ) : (
        <PasswordGate onUnlock={unlock} />
      )}
    </div>
  );
}

function PasswordGate({ onUnlock }: { onUnlock: (password: string) => void }) {
  const eventSlug = useEventSlug();
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      // The summary is the cheapest host-only call, so it doubles as the password check.
      await api.getHostSummary(eventSlug, value);
      onUnlock(value);
    } catch (err) {
      const wrong = err instanceof ApiError && err.status === 401;
      setError(wrong ? "That's not the host password." : (err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={onSubmit} style={{ maxWidth: 420 }}>
      <h1>Host page</h1>
      <div className="dim">For the event's organisers. Enter the host password to see how it's going and pick winners.</div>
      <label className="stack" style={{ gap: 6 }}>
        <span className="dim small">Host password</span>
        <input
          className="input"
          type="password"
          autoComplete="current-password"
          autoFocus
          aria-invalid={!!error}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </label>
      {error && <div className="error" role="alert">{error}</div>}
      <button className="btn primary" type="submit" disabled={busy || !value}>
        {busy ? 'Checking…' : 'Open host page'}
      </button>
    </form>
  );
}

function Dashboard({ password, onLock }: { password: string; onLock: () => void }) {
  const eventSlug = useEventSlug();
  const { name: eventName, submissionsClose } = useEvent();
  // Winners can be picked once submissions close. An event with no deadline has no such wait.
  const submissionsClosed = useSubmissionsClosed();
  const canPick = !submissionsClose || submissionsClosed;
  const summary = usePolling(() => api.getHostSummary(eventSlug, password), `${eventSlug}-${password}`);
  const path = useAttendeePath();
  const s = summary.data;

  // The password was changed on the server while this tab was open.
  const rejected = summary.error instanceof ApiError && summary.error.status === 401;
  if (rejected) {
    return (
      <div className="stack" style={{ maxWidth: 420 }}>
        <h1>Host page</h1>
        <div className="error" role="alert">The host password is no longer accepted.</div>
        <button className="btn" onClick={onLock}>Enter it again</button>
      </div>
    );
  }

  return (
    <>
      <div className="row between">
        <div>
          <h1>Host page</h1>
          {eventName && <div className="dim">{eventName}</div>}
        </div>
        <div className="row">
          <Link className="btn" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
            Open the attendee app
          </Link>
          <button className="btn" onClick={onLock}>Lock</button>
        </div>
      </div>

      {!s && !summary.error && <div className="dim">Loading…</div>}
      {!s && summary.error && <div className="error">Could not load the host page: {summary.error.message}</div>}
      {s && summary.error && (
        <div className="small" style={{ color: 'var(--amber)' }}>Can't reach the server. Showing the last numbers we got.</div>
      )}

      {s && (
        <>
          <div className="card row" style={{ gap: 10 }}>
            <Stat label="Attendees joined" value={coin(s.attendees)} />
            <Stat label="Teams entered" value={coin(s.teams)} />
            <Stat label="Bets placed" value={coin(s.bets)} />
            <Stat label="Hackcoin traded" value={coin(s.hackcoin_traded)} />
          </div>

          <div className="stack" style={{ gap: 10 }}>
            <h2>Markets</h2>
            <div className="dim small">
              Pick a winner once the judges announce it. That closes the market and pays every bet on the winner; it can't
              be undone.
            </div>
            {submissionsClose && !canPick && (
              <div className="card small" style={{ borderColor: 'var(--amber-border)' }}>
                <span style={{ color: 'var(--amber)', fontWeight: 500 }}>Submissions are still open.</span> Teams can
                sign up and attendees can bet until they close at{' '}
                <span className="mono">{dateTime(submissionsClose)}</span>. You can pick winners after that.
              </div>
            )}
            {s.markets.map((m) => (
              <MarketRow key={m.id} market={m} password={password} canPick={canPick} onResolved={summary.refresh} />
            ))}
          </div>

          <div className="stack" style={{ gap: 10 }}>
            <h2>Top forecasters</h2>
            {s.top_forecasters.length === 0 && <div className="card dim">Nobody has joined yet.</div>}
            {s.top_forecasters.map((f) => (
              <div key={f.user_id} className="card row between" style={{ padding: '12px 18px', flexWrap: 'nowrap' }}>
                <div className="row" style={{ flexWrap: 'nowrap', minWidth: 0 }}>
                  <span className="mono dim" style={{ width: 28, flex: 'none' }}>{f.rank}</span>
                  <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.display_name}
                  </span>
                </div>
                <span className="mono" style={{ flex: 'none' }}>{coin(f.balance)} Hackcoin</span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

type MarketRowProps = {
  market: HostMarketRow;
  password: string;
  /** False until the event's submissions close: the market is still taking bets. */
  canPick: boolean;
  /** Called after a market is resolved so the numbers refresh straight away. */
  onResolved: () => void;
};

function MarketRow({ market, password, canPick, onResolved }: MarketRowProps) {
  // The summary only names the leader; the picker needs every team in the market.
  const detail = usePolling(() => api.getMarket(market.id), market.id);
  const teams = detail.data?.teams ?? [];

  const [pickedId, setPickedId] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResolveResult | null>(null);

  const open = market.status === 'open';
  const picked = teams.find((t) => t.team_id === pickedId);
  const winner = teams.find((t) => t.team_id === market.winner_team_id);

  async function resolve() {
    if (!picked) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.resolveMarket(market.id, picked.team_id, password));
      setConfirming(false);
      onResolved();
      detail.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack" style={{ borderColor: open ? undefined : 'var(--accent)' }}>
      <div className="row between" style={{ alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div className="row" style={{ gap: 10 }}>
            <span style={{ fontWeight: 600, fontSize: 16 }}>{market.category}</span>
            {open ? <span className="dim small">Open</span> : <span className="badge-accent">Resolved</span>}
          </div>
          <div className="dim small">
            {open
              ? market.leader_team_name && market.leader_price != null
                ? `${market.leader_team_name} leads at ${pct(market.leader_price)}`
                : 'No teams have signed up yet'
              : `${winner?.name ?? market.winner_team_id} won`}
          </div>
        </div>
        <div style={{ textAlign: 'right', flex: 'none' }}>
          <div className="mono" style={{ fontSize: 18, fontWeight: 500 }}>{coin(market.staked)}</div>
          <div className="dim" style={{ fontSize: 12 }}>Hackcoin staked</div>
        </div>
      </div>

      {open && canPick && teams.length > 0 && !confirming && (
        <div className="row" style={{ gap: 8 }}>
          <select
            className="input"
            style={{ flex: '1 1 220px', width: 'auto' }}
            aria-label={`Winner of ${market.category}`}
            value={pickedId}
            onChange={(e) => setPickedId(e.target.value)}
          >
            <option value="">Choose the winning team…</option>
            {teams.map((t) => (
              <option key={t.team_id} value={t.team_id}>
                {t.name} · {pct(t.price)}
              </option>
            ))}
          </select>
          <button className="btn" disabled={!picked} onClick={() => setConfirming(true)}>
            Pick winner
          </button>
        </div>
      )}

      {open && canPick && confirming && picked && (
        <div className="stack" style={{ gap: 10, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
          <div>
            Close <strong>{market.category}</strong> with <strong>{picked.name}</strong> as the winner? Every bet on{' '}
            {picked.name} is paid out and the rest pay nothing. This can't be undone.
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn primary" disabled={busy} onClick={resolve}>
              {busy ? 'Paying out…' : `Yes, ${picked.name} won`}
            </button>
            <button className="btn" disabled={busy} onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <div className="error" role="alert">Could not resolve this market: {error}</div>}
      {result && (
        <div className="small" style={{ color: 'var(--accent)' }}>
          Paid {coin(result.total_paid)} Hackcoin across {plural(result.bets_paid, 'winning bet')}.
        </div>
      )}
    </div>
  );
}
