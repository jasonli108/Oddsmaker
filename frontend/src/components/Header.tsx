import { useState, type FormEvent } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { ApiError } from '../api/client';
import { coin, countdown } from '../format';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEvent } from '../hooks/useEvent';
import { useNow } from '../hooks/useNow';
import { useUser } from '../hooks/useUser';

// Paths inside the attendee app, which lives under /e/:slug.
const TABS = [
  { to: '', label: 'Markets' },
  { to: '/reports', label: 'Scout reports' },
  { to: '/leaderboard', label: 'Leaderboard' },
  { to: '/signup', label: 'Sign up a team' },
];

export default function Header() {
  const { user, ready } = useUser();
  const { name: eventName } = useEvent();
  const path = useAttendeePath();

  return (
    <header style={{ borderBottom: '1px solid var(--border)' }}>
      <div className="container row between" style={{ paddingTop: 16, paddingBottom: 16, gap: 16 }}>
        <div className="row" style={{ gap: 14 }}>
          <Link to={path()} style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--text)' }}>
            Oddsmaker
          </Link>
          <div className="dim" style={{ fontSize: 14 }}>{eventName}</div>
          {/* The submission checklist requires this on every screen. */}
          <div className="badge-amber">Play money only</div>
        </div>
        <div className="row" style={{ gap: 18 }}>
          <Countdown />
          {user ? (
            <div
              className="card small dim"
              title={`Playing as ${user.display_name}`}
              style={{ padding: '8px 14px', borderRadius: 'var(--radius-control)' }}
            >
              Your balance{' '}
              <span className="mono" style={{ color: 'var(--text)', fontWeight: 500, marginLeft: 6 }}>
                {coin(user.balance)} Hackcoin
              </span>
            </div>
          ) : (
            ready && <JoinForm />
          )}
        </div>
      </div>
      <nav className="container tabs">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={path(tab.to)} end={tab.to === ''}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

function Countdown() {
  const { submissionsClose } = useEvent();
  const left = submissionsClose.getTime() - useNow();
  if (left <= 0) return <div className="dim small">Submissions closed</div>;
  return (
    <div className="dim small">
      Submissions close in{' '}
      <span className="mono" style={{ color: 'var(--text)' }}>{countdown(left)}</span>
    </div>
  );
}

function JoinForm() {
  const { join } = useUser();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const displayName = name.trim();
    if (!displayName) {
      setError('Enter a display name first.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await join(displayName);
    } catch (err) {
      const fieldMessage = err instanceof ApiError ? err.fields.display_name : undefined;
      setError(fieldMessage ? `Display name: ${fieldMessage}` : `Couldn't set you up. ${(err as Error).message}`);
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={onSubmit} style={{ gap: 6, alignItems: 'flex-end' }} noValidate>
      <div className="row" style={{ gap: 8 }}>
        <input
          className="input"
          style={{ width: 180 }}
          placeholder="Your display name"
          aria-label="Your display name"
          aria-invalid={!!error}
          maxLength={40}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="btn primary" type="submit" disabled={busy}>
          {busy ? 'Setting up…' : 'Get 1,000 Hackcoin'}
        </button>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
    </form>
  );
}
