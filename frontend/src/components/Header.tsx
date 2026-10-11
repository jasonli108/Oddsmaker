import { useState, type FormEvent } from 'react';
import { NavLink } from 'react-router-dom';
import { EVENT_NAME } from '../config';
import { coin } from '../format';
import { useUser } from '../hooks/useUser';

const TABS = [
  { to: '/', label: 'Markets' },
  { to: '/reports', label: 'Scout reports' },
  { to: '/leaderboard', label: 'Leaderboard' },
  { to: '/signup', label: 'Sign up a team' },
];

export default function Header() {
  const { user } = useUser();

  return (
    <header style={{ borderBottom: '1px solid var(--border)' }}>
      <div className="container row between" style={{ paddingTop: 16, paddingBottom: 16, gap: 16 }}>
        <div className="row" style={{ gap: 14 }}>
          <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em' }}>Oddsmaker</div>
          <div className="dim" style={{ fontSize: 14 }}>{EVENT_NAME}</div>
          {/* The submission checklist requires this on every screen. */}
          <div className="badge-amber">Play money only</div>
        </div>
        {user ? (
          <div className="card small dim" style={{ padding: '8px 14px', borderRadius: 'var(--radius-control)' }}>
            {user.display_name}'s balance{' '}
            <span className="mono" style={{ color: 'var(--text)', fontWeight: 500, marginLeft: 6 }}>
              {coin(user.balance)} Hackcoin
            </span>
          </div>
        ) : (
          <JoinForm />
        )}
      </div>
      <nav className="container tabs">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.to === '/'}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

function JoinForm() {
  const { join } = useUser();
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await join(name.trim());
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="row" onSubmit={onSubmit} style={{ gap: 8 }}>
      <input
        className="input"
        style={{ width: 180 }}
        placeholder="Your display name"
        aria-label="Your display name"
        maxLength={40}
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button className="btn primary" type="submit">
        Get 1,000 Hackcoin
      </button>
      {error && <span className="error">{error}</span>}
    </form>
  );
}
