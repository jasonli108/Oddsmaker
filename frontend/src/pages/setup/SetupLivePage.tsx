import { QRCodeSVG } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { ApiError, api } from '../../api/client';
import { plural } from '../../format';
import { publicOrigin } from '../../host';
import { usePolling } from '../../hooks/usePolling';

const NEXT = [
  { when: 'Now', title: 'Teams add their project', body: 'A name, a one-line idea, a repo link and a demo link.' },
  { when: 'Every 30 minutes', title: 'Scout reports on each team', body: 'It checks originality, build progress and the demo, then moves the odds.' },
  { when: 'After judging', title: 'You pick the winners', body: 'Markets pay out and the leaderboard names your best forecaster.' },
];

/** Setup step 3: the event is saved. Hand the host the link and QR code to share. */
export default function SetupLivePage() {
  const event = usePolling(api.getEvent, 'setup-live', 0);
  const markets = usePolling(api.listMarkets, 'setup-live-markets', 0);
  const [copied, setCopied] = useState(false);
  const [bigQr, setBigQr] = useState(false);

  useEffect(() => {
    if (!bigQr) return;
    const close = (e: KeyboardEvent) => e.key === 'Escape' && setBigQr(false);
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [bigQr]);

  // Opened directly before any event was launched.
  if (event.error instanceof ApiError && event.error.status === 404) return <Navigate to="/setup" replace />;
  if (!event.data) {
    return (
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '56px 24px' }} className={event.error ? 'error' : 'dim'}>
        {event.error ? `Could not load your event: ${event.error.message}` : 'Loading…'}
      </div>
    );
  }

  const path = `/e/${event.data.slug}`;
  const link = publicOrigin() + path;
  const openMarkets = markets.data?.filter((m) => m.status === 'open').length;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be refused; the link is on screen to select by hand.
    }
  }

  return (
    <div className="stack" style={{ maxWidth: 1040, margin: '0 auto', padding: '56px 24px 64px', gap: 32 }}>
      <div className="stack" style={{ gap: 10 }}>
        {openMarkets != null && (
          <div
            style={{ alignSelf: 'flex-start', fontSize: 13, fontWeight: 500, color: 'var(--good)', border: '1px solid var(--good-border)', borderRadius: 999, padding: '4px 12px' }}
          >
            {plural(openMarkets, 'market')} live
          </div>
        )}
        <h1 style={{ fontSize: 'clamp(32px, 5.5vw, 48px)', letterSpacing: '-0.03em', lineHeight: 1.06 }}>
          {event.data.name} is live.
        </h1>
        <div className="soft" style={{ fontSize: 18 }}>
          Share the link below. A team shows up in every market as soon as it adds its project.
        </div>
      </div>

      <div className="row" style={{ gap: 20, alignItems: 'stretch' }}>
        <div className="card stack" style={{ flex: '999 1 420px', minWidth: 0, borderRadius: 16, padding: 24, gap: 18 }}>
          <h2 style={{ fontSize: 20 }}>For attendees</h2>
          <div className="stack" style={{ gap: 8 }}>
            <div className="dim small">Event link</div>
            <div className="row" style={{ gap: 10 }}>
              <div
                className="mono"
                style={{ flex: '1 1 240px', minWidth: 0, display: 'flex', alignItems: 'center', minHeight: 52, background: 'var(--bg)', border: '1px solid var(--border-strong)', borderRadius: 10, padding: '0 14px', fontSize: 15, overflowWrap: 'anywhere' }}
              >
                {link}
              </div>
              <button className="btn primary" onClick={copy} style={{ minHeight: 52, padding: '0 20px', borderRadius: 10, fontSize: 16 }}>
                {copied ? 'Copied' : 'Copy link'}
              </button>
            </div>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <Link className="btn" to={path} style={{ display: 'flex', alignItems: 'center', minHeight: 48, padding: '0 18px', borderRadius: 10, fontSize: 15 }}>
              Open the market
            </Link>
            <button className="btn" onClick={() => setBigQr(true)} style={{ minHeight: 48, padding: '0 18px', borderRadius: 10, fontSize: 15 }}>
              Show QR full screen
            </button>
          </div>
          <div className="stack" style={{ borderTop: '1px solid var(--border)', paddingTop: 16, gap: 8 }}>
            <div className="small" style={{ color: 'var(--amber)' }}>For you, the host</div>
            <div className="row" style={{ gap: 10 }}>
              <Link className="btn" to="/host" style={{ display: 'flex', alignItems: 'center', minHeight: 48, padding: '0 18px', borderRadius: 10, fontSize: 15 }}>
                Open the host page
              </Link>
            </div>
            <div className="dim" style={{ fontSize: 14 }}>
              Watch the numbers there and pick the winners when the judges announce. It asks for the host password, so
              keep that private: anyone with it can pay out a market.
            </div>
          </div>
        </div>

        <div className="card stack" style={{ flex: '1 1 280px', minWidth: 0, borderRadius: 16, padding: 24, alignItems: 'center' }}>
          <div style={{ width: '100%', maxWidth: 240, background: '#ECEFF1', borderRadius: 12, padding: 14 }}>
            <QRCodeSVG value={link} role="img" aria-label={`QR code for ${link}`} bgColor="#ECEFF1" fgColor="#0F1214" style={{ display: 'block', width: '100%', height: 'auto' }} />
          </div>
          <div style={{ fontSize: 15, fontWeight: 500, textAlign: 'center' }}>Scan to join and get 1,000 Hackcoin</div>
          <div className="dim small" style={{ textAlign: 'center' }}>Put this on the big screen at kickoff.</div>
        </div>
      </div>

      <div className="stack">
        <h2 style={{ fontSize: 20 }}>What happens next</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          {NEXT.map((step) => (
            <div key={step.when} className="stack" style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 18, gap: 6 }}>
              <div className="mono" style={{ fontSize: 13, color: 'var(--accent)' }}>{step.when}</div>
              <div style={{ fontWeight: 500 }}>{step.title}</div>
              <div className="dim" style={{ fontSize: 14 }}>{step.body}</div>
            </div>
          ))}
        </div>
      </div>

      {bigQr && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Event QR code"
          onClick={() => setBigQr(false)}
          style={{ position: 'fixed', inset: 0, zIndex: 10, background: 'var(--bg)', display: 'grid', placeItems: 'center', padding: 24, cursor: 'pointer' }}
        >
          <div className="stack" style={{ alignItems: 'center', gap: 24, maxWidth: '100%' }}>
            <div style={{ fontSize: 'clamp(24px, 4vw, 44px)', fontWeight: 600, letterSpacing: '-0.02em', textAlign: 'center' }}>
              Scan to join {event.data.name}
            </div>
            <div style={{ background: '#ECEFF1', borderRadius: 16, padding: 24, width: 'min(60vh, 80vw)' }}>
              <QRCodeSVG value={link} bgColor="#ECEFF1" fgColor="#0F1214" style={{ display: 'block', width: '100%', height: 'auto' }} />
            </div>
            <div className="mono soft" style={{ fontSize: 'clamp(14px, 2vw, 22px)', overflowWrap: 'anywhere', textAlign: 'center' }}>{link}</div>
            <button className="btn" autoFocus onClick={() => setBigQr(false)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
