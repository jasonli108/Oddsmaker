import { Link } from 'react-router-dom';
import BrandBar from '../components/BrandBar';
import { useAttendeePath } from '../hooks/useAttendeePath';

const navLink = { display: 'flex', alignItems: 'center', minHeight: 44, fontSize: 15 } as const;

// The preview card is an illustration, labelled as a sample; it is not read from the API.
const SAMPLE_TEAMS = [
  { name: 'Team Orbit', color: '#7DB8FF', price: '31%', multiple: '3.2x' },
  { name: 'Ledgerline', color: '#FFB454', price: '24%', multiple: '4.2x' },
  { name: 'Parsel', color: '#D2B8FF', price: '18%', multiple: '5.6x' },
];
const SAMPLE_LINES = [
  { color: '#D2B8FF', d: 'M0 62 H60 V70 H130 V66 H200 V74 H280 V70 H400' },
  { color: '#FFB454', d: 'M0 62 H70 V56 H140 V46 H220 V50 H300 V42 H400' },
  { color: '#7DB8FF', d: 'M0 62 H50 V50 H110 V38 H180 V28 H250 V34 H320 V18 H400' },
];

const STEPS = [
  { title: 'Paste your event link', body: 'We read your event page and pull the name, dates and prize categories for you.' },
  { title: 'Confirm the details', body: 'Fix anything we got wrong and choose which prizes get a market.' },
  { title: 'Share one link', body: 'Put the QR code on the big screen. Teams add their projects and the room starts betting.' },
];

/** The front door for hackathon hosts. Attendees go straight to /e/:slug. */
export default function LandingPage() {
  const path = useAttendeePath();

  return (
    <div style={{ fontSize: 16, lineHeight: 1.5 }}>
      <BrandBar>
        <a href="#how" style={navLink}>How it works</a>
        <Link to={path()} style={navLink}>See a live market</Link>
        <Link className="btn" to="/setup" style={{ ...navLink, padding: '0 18px', borderColor: 'var(--border-bold)' }}>
          Set up your hackathon
        </Link>
      </BrandBar>

      <div
        style={{ maxWidth: 1180, margin: '0 auto', padding: '56px 24px 64px', display: 'flex', flexWrap: 'wrap', gap: 56, alignItems: 'center' }}
      >
        <div className="stack" style={{ flex: '999 1 460px', minWidth: 0, gap: 24 }}>
          <div className="badge-amber" style={{ alignSelf: 'flex-start', fontSize: 13, padding: '4px 12px' }}>
            For hackathon hosts
          </div>
          <h1 style={{ fontSize: 'clamp(38px, 6vw, 60px)', letterSpacing: '-0.03em', lineHeight: 1.04 }}>
            Give everyone a stake in every project.
          </h1>
          <div className="soft" style={{ fontSize: 19, maxWidth: 520 }}>
            Oddsmaker is a play-money prediction market for your hackathon. Attendees bet Hackcoin on who wins each
            prize, and an AI scout reports on every team as they build.
          </div>
          <div className="row">
            <Link
              className="btn primary"
              to="/setup"
              style={{ display: 'flex', alignItems: 'center', minHeight: 54, padding: '0 26px', borderRadius: 10, fontSize: 17 }}
            >
              Set up your hackathon
            </Link>
            <Link
              className="btn"
              to={path()}
              style={{ display: 'flex', alignItems: 'center', minHeight: 54, padding: '0 22px', borderRadius: 10, fontSize: 17 }}
            >
              See a live market
            </Link>
          </div>
          <div className="dim" style={{ fontSize: 14 }}>Takes about two minutes. Play money only, never real wagers.</div>
        </div>

        <div className="card stack" style={{ flex: '1 1 400px', minWidth: 0, borderRadius: 16, padding: 22 }}>
          <div className="row between" style={{ flexWrap: 'nowrap', alignItems: 'baseline' }}>
            <div style={{ fontSize: 17, fontWeight: 600 }}>Who takes 1st place overall?</div>
            <div className="dim" style={{ fontSize: 12, flex: 'none' }}>Sample market</div>
          </div>
          <svg viewBox="0 0 400 110" preserveAspectRatio="none" aria-hidden style={{ display: 'block', width: '100%', height: 110 }}>
            <g fill="none" strokeWidth={2} strokeLinejoin="round">
              {SAMPLE_LINES.map((line) => (
                <path key={line.color} d={line.d} stroke={line.color} vectorEffect="non-scaling-stroke" />
              ))}
            </g>
          </svg>
          <div>
            {SAMPLE_TEAMS.map((t) => (
              <div key={t.name} className="row" style={{ flexWrap: 'nowrap', padding: '12px 0', borderTop: '1px solid var(--border)' }}>
                <span className="dot" aria-hidden style={{ background: t.color }} />
                <div style={{ flex: 1, minWidth: 0, fontWeight: 500 }}>{t.name}</div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 500 }}>{t.price}</div>
                <div className="mono dim" style={{ fontSize: 13, width: 44, textAlign: 'right' }}>{t.multiple}</div>
              </div>
            ))}
          </div>
          <div
            className="soft"
            style={{ background: 'var(--bg)', border: '1px solid var(--amber-border)', borderRadius: 10, padding: '12px 14px', fontSize: 14 }}
          >
            <span style={{ color: 'var(--amber)', fontWeight: 500 }}>Scout</span> moved Ledgerline from 22% to 24% after
            finding no similar project on the web.
          </div>
        </div>
      </div>

      <div id="how" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="stack" style={{ maxWidth: 1180, margin: '0 auto', padding: '48px 24px 64px', gap: 28 }}>
          <h2 style={{ fontSize: 28, letterSpacing: '-0.02em' }}>Live in three steps</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            {STEPS.map((step, i) => (
              <div key={step.title} className="card stack" style={{ padding: 22, gap: 10 }}>
                <div className="mono" style={{ fontSize: 14, color: 'var(--accent)' }}>{String(i + 1).padStart(2, '0')}</div>
                <h3 style={{ fontSize: 18 }}>{step.title}</h3>
                <div className="dim" style={{ fontSize: 15 }}>{step.body}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
