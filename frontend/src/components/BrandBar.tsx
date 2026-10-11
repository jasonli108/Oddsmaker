import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

/** The plain top bar for pages outside the attendee app: landing, host setup, host page. */
export default function BrandBar({ children }: { children?: ReactNode }) {
  return (
    <header style={{ borderBottom: '1px solid var(--border)' }}>
      <div
        className="row between"
        style={{ maxWidth: 1180, margin: '0 auto', padding: '16px 24px', gap: 16 }}
      >
        <div className="row" style={{ gap: 14 }}>
          <Link to="/" style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--text)' }}>
            Oddsmaker
          </Link>
          <div className="badge-amber">Play money only</div>
        </div>
        <div className="row" style={{ gap: 24 }}>{children}</div>
      </div>
    </header>
  );
}
