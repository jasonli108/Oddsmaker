import { Link } from 'react-router-dom';
import BrandBar from '../components/BrandBar';

/**
 * TODO(frontend): the three setup screens from the host flow brief go here: paste event link
 * (/setup), confirm details (/setup/review), markets are live (/setup/live). The backend is
 * ready: api.extractEvent and api.saveEvent. Designs are on the canvas under "Host setup flow".
 */
export default function SetupPage() {
  return (
    <>
      <BrandBar>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', minHeight: 44, fontSize: 14 }}>
          Exit setup
        </Link>
      </BrandBar>
      <div className="stack" style={{ maxWidth: 640, margin: '0 auto', padding: '48px 24px' }}>
        <h1>Set up your hackathon</h1>
        <div className="dim">
          Setup isn't built yet. Your markets are already running, and you can pick winners from the host page.
        </div>
        <div className="row">
          <Link className="btn primary" to="/host" style={{ display: 'grid', placeItems: 'center' }}>
            Open the host page
          </Link>
        </div>
      </div>
    </>
  );
}
