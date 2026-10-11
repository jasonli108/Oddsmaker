import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAttendeePath } from '../../hooks/useAttendeePath';

const STEPS = ['Event link', 'Confirm details', 'Launch'];

/** The frame around the three setup screens: wordmark, where you are in the steps, a way out. */
export default function SetupLayout() {
  const { pathname } = useLocation();
  const path = useAttendeePath();
  const current = pathname.endsWith('/live') ? 2 : pathname.endsWith('/review') ? 1 : 0;

  return (
    <div style={{ fontSize: 16, lineHeight: 1.5 }}>
      <header style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="row between" style={{ maxWidth: 1180, margin: '0 auto', padding: '16px 24px', gap: 16 }}>
          <Link to="/" style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--text)' }}>
            Oddsmaker
          </Link>
          <ol className="row" aria-label="Setup steps" style={{ gap: 10, fontSize: 14, listStyle: 'none', margin: 0, padding: 0 }}>
            {STEPS.map((label, i) => (
              <li key={label} className="row" style={{ gap: 10 }} aria-current={i === current ? 'step' : undefined}>
                {i > 0 && <span aria-hidden style={{ width: 28, height: 1, background: 'var(--border-strong)' }} />}
                <span className="row" style={{ gap: 8 }}>
                  <StepNumber n={i + 1} state={i === current ? 'current' : i < current ? 'done' : 'upcoming'} />
                  <span
                    style={{
                      fontWeight: i === current ? 500 : 400,
                      color: i === current ? 'var(--text)' : i < current ? 'var(--text-soft)' : 'var(--text-dim)',
                    }}
                  >
                    {label}
                  </span>
                </span>
              </li>
            ))}
          </ol>
          <Link to={current === 2 ? path() : '/'} style={{ display: 'flex', alignItems: 'center', minHeight: 44, fontSize: 14 }}>
            {current === 2 ? 'Go to the market' : 'Exit setup'}
          </Link>
        </div>
      </header>
      <Outlet />
    </div>
  );
}

function StepNumber({ n, state }: { n: number; state: 'current' | 'done' | 'upcoming' }) {
  const look = {
    current: { background: 'var(--accent)', color: 'var(--on-accent)', border: '1px solid var(--accent)', fontWeight: 500 },
    done: { color: 'var(--accent)', border: '1px solid var(--accent)' },
    upcoming: { border: '1px solid var(--border-bold)' },
  }[state];
  return (
    <span
      className="mono"
      style={{ width: 26, height: 26, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 13, flex: 'none', ...look }}
    >
      {n}
    </span>
  );
}
