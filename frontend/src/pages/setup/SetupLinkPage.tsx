import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { blankDraft, saveDraft } from './draft';

const PULLED = [
  { title: 'Name and location', body: 'So attendees recognise the event' },
  { title: 'Dates and deadline', body: 'Shown to attendees as a countdown' },
  { title: 'Prize categories', body: 'Matched to the markets attendees bet on' },
];

/** Setup step 1: paste the event page link and let Scout read it. */
export default function SetupLinkPage() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const link = url.trim();
    if (!link) {
      setError('Paste the link to your event page first.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      saveDraft(await api.extractEvent(link));
      navigate('/setup/review');
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  function byHand() {
    saveDraft(blankDraft());
    navigate('/setup/review');
  }

  return (
    <div className="stack" style={{ maxWidth: 720, margin: '0 auto', padding: '88px 24px 64px', gap: 28 }}>
      <div className="stack" style={{ gap: 12 }}>
        <h1 style={{ fontSize: 'clamp(32px, 5vw, 44px)', letterSpacing: '-0.025em', lineHeight: 1.08 }}>
          Start with your event page
        </h1>
        <div className="soft" style={{ fontSize: 18 }}>
          Paste the link to your hackathon's public page. We'll read it and fill in the details so you only have to
          check them.
        </div>
      </div>

      <form className="card stack" onSubmit={onSubmit} noValidate style={{ borderRadius: 16, padding: 24 }}>
        <label htmlFor="event-url" className="soft" style={{ fontSize: 14, fontWeight: 500 }}>Event page link</label>
        <div className="row" style={{ gap: 10 }}>
          <input
            id="event-url"
            className="input"
            inputMode="url"
            autoFocus
            placeholder="https://yourhackathon.com"
            aria-invalid={!!error}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{ flex: '1 1 320px', width: 'auto', height: 56, borderRadius: 10, fontSize: 17, borderColor: 'var(--accent)' }}
          />
          <button
            className="btn primary"
            type="submit"
            disabled={busy}
            style={{ minHeight: 56, padding: '0 24px', borderRadius: 10, fontSize: 17 }}
          >
            {busy ? 'Reading your page…' : 'Read my event page'}
          </button>
        </div>
        {error ? (
          <div className="error" role="alert">{error}</div>
        ) : (
          <div className="dim" style={{ fontSize: 14 }}>Any public event page works. Nothing behind a login is read.</div>
        )}
      </form>

      <div className="stack">
        <div className="soft" style={{ fontSize: 14, fontWeight: 500 }}>What we'll pull from the page</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          {PULLED.map((item) => (
            <div key={item.title} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
              <div style={{ fontWeight: 500 }}>{item.title}</div>
              <div className="dim" style={{ fontSize: 14 }}>{item.body}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="row dim" style={{ gap: 14, fontSize: 14, flexWrap: 'nowrap' }}>
        <span aria-hidden style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        <span>No event page yet?</span>
        <button
          type="button"
          onClick={byHand}
          style={{ minHeight: 44, background: 'none', border: 'none', padding: 0, color: 'var(--text)', fontSize: 14, fontWeight: 500, textDecoration: 'underline' }}
        >
          Enter the details by hand
        </button>
        <span aria-hidden style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </div>
    </div>
  );
}
