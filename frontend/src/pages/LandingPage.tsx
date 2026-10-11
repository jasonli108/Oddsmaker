import { Link } from 'react-router-dom';
import BrandBar from '../components/BrandBar';
import SampleMarket from '../components/SampleMarket';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { useEvent } from '../hooks/useEvent';

const navLink = { display: 'flex', alignItems: 'center', minHeight: 44, fontSize: 15 } as const;

const STEPS = [
  { title: 'Paste your event link', body: 'We read your event page and pull the name, dates and prize categories for you.' },
  { title: 'Confirm the details', body: 'Fix anything we got wrong and choose which prizes get a market.' },
  { title: 'Share one link', body: 'Put the QR code on the big screen. Teams add their projects and the room starts betting.' },
];

/** The front door for hackathon hosts. Attendees go straight to /e/:slug. */
export default function LandingPage() {
  const path = useAttendeePath();
  // The deployment's first event, if one has been launched. Each host's own link is on their setup screen.
  const { slug: liveEvent } = useEvent();

  return (
    <div style={{ fontSize: 16, lineHeight: 1.5 }}>
      <BrandBar>
        <a href="#how" style={navLink}>How it works</a>
        {liveEvent && <Link to={path()} style={navLink}>See a live market</Link>}
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
            {liveEvent && (
              <Link
                className="btn"
                to={path()}
                style={{ display: 'flex', alignItems: 'center', minHeight: 54, padding: '0 22px', borderRadius: 10, fontSize: 17 }}
              >
                See a live market
              </Link>
            )}
          </div>
          <div className="dim" style={{ fontSize: 14 }}>Takes about two minutes. Play money only, never real wagers.</div>
        </div>

        <SampleMarket />
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
