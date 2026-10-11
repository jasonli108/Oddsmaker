import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { ApiError, api } from '../../api/client';
import type { EventCategory, EventDraft } from '../../api/types';
import { hostPassword } from '../../host';
import { STARTING_BALANCE } from '../../config';
import { coin, plural } from '../../format';
import { clearDraft, loadDraft } from './draft';

const AMBER = 'var(--amber)';
const MAX_STARTING_BALANCE = 1_000_000; // the backend's limit

/** A prize category on this screen. `added` marks one the host added here, not one read from their page. */
type Category = EventCategory & { added?: boolean };

/** Until the host ticks or unticks the box, a category gets a market when Scout has a score that fits it. */
const wantsMarket = (c: EventCategory) => c.create_market ?? !!c.market_id;

/** An ISO time as the value a datetime-local input wants, in the host's own time zone. */
function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

const fromLocalInput = (value: string) => (value ? new Date(value).toISOString() : null);

/** "mlh.com/events/ai-engineer-nyc-2026" from the full link, for the banner. */
function shortLink(url: string): string {
  try {
    const u = new URL(url);
    return (u.host.replace(/^www\./, '') + u.pathname).replace(/\/$/, '');
  } catch {
    return url;
  }
}

/** Setup step 2: check what was read from the event page, fix it, and launch. */
export default function SetupReviewPage() {
  const draft = loadDraft();
  if (!draft) return <Navigate to="/setup" replace />;
  return <ReviewForm draft={draft} />;
}

function ReviewForm({ draft }: { draft: EventDraft }) {
  const navigate = useNavigate();

  const [name, setName] = useState(draft.name);
  const [hostedBy, setHostedBy] = useState(draft.hosted_by ?? '');
  const [location, setLocation] = useState(draft.location ?? '');
  const [startsAt, setStartsAt] = useState(toLocalInput(draft.starts_at));
  const [closesAt, setClosesAt] = useState(toLocalInput(draft.submissions_close_at));
  const [categories, setCategories] = useState<Category[]>(draft.categories ?? []);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [startingText, setStartingText] = useState(String(STARTING_BALANCE));
  const [startingError, setStartingError] = useState<string | null>(null);
  const [password, setPassword] = useState(hostPassword.get() ?? '');
  const [busy, setBusy] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [closesError, setClosesError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Typed in by hand: there was no page to read, so nothing can be "not found".
  const byHand = !draft.source_url;
  const readFailed = !byHand && !draft.is_sample && !draft.name && categories.length === 0;
  const notFound = (value: string) => !byHand && !value;
  const named = categories.filter((c) => c.name.trim());
  const marketCount = named.filter(wantsMarket).length;
  const startingBalance = Number(startingText);

  const changeCategories = (change: (list: Category[]) => Category[]) => {
    setCategories(change);
    setCategoriesError(null);
  };
  const setCategory = (index: number, change: Partial<Category>) =>
    changeCategories((list) => list.map((c, i) => (i === index ? { ...c, ...change } : c)));
  const addCategory = () =>
    changeCategories((list) => [...list, { name: '', prize: null, market_id: null, create_market: true, added: true }]);
  const removeCategory = (index: number) => changeCategories((list) => list.filter((_, i) => i !== index));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setNameError(null);
    setClosesError(null);
    setPasswordError(null);
    setStartingError(null);
    setCategoriesError(null);
    setFormError(null);
    if (!name.trim()) {
      setNameError('Your event needs a name.');
      return;
    }
    // Team sign-up and betting stop at this time, and winners are picked after it.
    if (!closesAt) {
      setClosesError('Set when submissions close. Team sign-up and betting stop then.');
      return;
    }
    if (new Date(closesAt).getTime() <= Date.now()) {
      setClosesError('That time has already passed. Nobody could sign up a team or bet.');
      return;
    }
    if (marketCount === 0) {
      setCategoriesError('Name at least one prize category and tick its market, so attendees have something to bet on.');
      return;
    }
    if (!Number.isInteger(startingBalance) || startingBalance < 1 || startingBalance > MAX_STARTING_BALANCE) {
      setStartingError(`Enter a whole number from 1 to ${coin(MAX_STARTING_BALANCE)}.`);
      return;
    }
    if (!password) {
      setPasswordError('Enter the host password to launch.');
      return;
    }
    setBusy(true);
    try {
      // Every launch is a new event with its own link, markets and players.
      const created = await api.createEvent(
        {
          name: name.trim(),
          hosted_by: hostedBy.trim() || null,
          location: location.trim() || null,
          starts_at: fromLocalInput(startsAt),
          submissions_close_at: fromLocalInput(closesAt),
          source_url: draft.source_url ?? null,
          categories: named.map((c) => ({
            name: c.name.trim(),
            prize: c.prize?.trim() || null,
            market_id: c.market_id ?? null,
            create_market: wantsMarket(c),
          })),
          starting_balance: startingBalance,
        },
        password,
      );
      hostPassword.set(password); // so the host page doesn't ask for it again in this tab
      clearDraft();
      navigate(`/setup/live/${created.slug}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setPasswordError("That's not the host password.");
      else if (err instanceof ApiError && err.fields.name) setNameError(err.fields.name);
      else if (err instanceof ApiError && err.fields.submissions_close_at) setClosesError(err.fields.submissions_close_at);
      else setFormError(`Couldn't launch. ${(err as Error).message}`);
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={onSubmit} noValidate style={{ maxWidth: 920, margin: '0 auto', padding: '48px 24px 64px', gap: 28 }}>
      <div className="stack" style={{ gap: 12 }}>
        <h1 style={{ fontSize: 'clamp(30px, 5vw, 40px)', letterSpacing: '-0.025em', lineHeight: 1.1 }}>
          {byHand ? 'Tell us about your event' : readFailed ? "We couldn't read that page" : "Here's what we found"}
        </h1>
        {!byHand && (
          <div className="card soft" style={{ borderColor: 'var(--amber-border)', borderRadius: 10, padding: '12px 16px', fontSize: 15 }}>
            {draft.is_sample ? (
              <>
                <span style={{ color: AMBER, fontWeight: 500 }}>Sample details.</span> Scout isn't set up on this
                server (it needs its Nimble and Gemini keys), so these are examples and were not read from{' '}
                {shortLink(draft.source_url!)}. Replace anything that isn't your event.
              </>
            ) : readFailed ? (
              <>
                <span style={{ color: AMBER, fontWeight: 500 }}>Nothing came back</span> from{' '}
                {shortLink(draft.source_url!)}. Fill in the details below, or go back and try another link.
              </>
            ) : (
              <>
                <span style={{ color: AMBER, fontWeight: 500 }}>Read from</span> {shortLink(draft.source_url!)}. Check
                each field and fix anything that's off.
              </>
            )}
          </div>
        )}
      </div>

      <Section title="Event">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
          <Field label="Event name" error={nameError} notFound={notFound(name) && !nameError}>
            {(look) => <input className="input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} {...look} />}
          </Field>
          <Field label="Hosted by" notFound={notFound(hostedBy)}>
            {(look) => <input className="input" value={hostedBy} onChange={(e) => setHostedBy(e.target.value)} {...look} />}
          </Field>
          <Field label="Location" notFound={notFound(location)}>
            {(look) => <input className="input" value={location} onChange={(e) => setLocation(e.target.value)} {...look} />}
          </Field>
          <Field label="Hacking starts" notFound={notFound(startsAt)}>
            {(look) => (
              <input className="input" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} {...look} />
            )}
          </Field>
          <Field
            label="Submissions close (required)"
            error={closesError}
            notFound={notFound(closesAt) && !closesError}
            hint="Team sign-up and betting stop at this time. You pick winners after it."
          >
            {(look) => (
              <input
                className="input"
                type="datetime-local"
                required
                value={closesAt}
                onChange={(e) => {
                  setClosesAt(e.target.value);
                  setClosesError(null);
                }}
                {...look}
              />
            )}
          </Field>
        </div>
      </Section>

      <Section
        title="Prize categories"
        aside={`${named.length} ${named.length === 1 ? 'category' : 'categories'}. ${plural(marketCount, 'market')} will go live.`}
      >
        <div className="dim" style={{ fontSize: 14 }}>
          Each category you tick becomes a market in your event. Scout scores the overall prize and the Nimble, Gemini
          and Tiger Data prizes directly; it prices any other category from each team's overall score.
        </div>
        {categories.length === 0 && (
          <div className="dim">
            {byHand ? 'No prize categories yet.' : 'No prize categories were found.'} Add one to open your first market.
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 14 }}>
          {categories.map((c, i) => (
            <CategoryCard
              key={i}
              index={i}
              category={c}
              byHand={byHand}
              onChange={(change) => setCategory(i, change)}
              onRemove={() => removeCategory(i)}
            />
          ))}
        </div>
        <button className="btn" type="button" onClick={addCategory} style={{ alignSelf: 'flex-start', minHeight: 44, padding: '0 18px' }}>
          Add a category
        </button>
        {categoriesError && <div className="error" role="alert">{categoriesError}</div>}
      </Section>

      <Section title="Game settings">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
          <label className="stack" style={{ gap: 6 }}>
            <span className="dim small">Hackcoin each attendee starts with</span>
            <input
              className="input mono"
              inputMode="numeric"
              aria-invalid={!!startingError}
              value={startingText}
              onChange={(e) => setStartingText(e.target.value.replace(/[^0-9]/g, ''))}
            />
            {startingError ? (
              <span className="error" role="alert">{startingError}</span>
            ) : (
              <span className="dim small">For this event only. It can't be changed after launch.</span>
            )}
          </label>
          {/* TODO(scout): make this adjustable once the Scout timer exists. Store the interval on the
              event, as starting_balance is, and have app/scout/scheduler.py read it instead of
              SCOUT_INTERVAL_MINUTES. Blocked until the pipeline that the timer runs is written. */}
          <Setting label="Scout refreshes its reports" value="Every 30 minutes" />
          <Setting label="Sign-up and betting close" value="When submissions close. You pick winners after that." />
        </div>
        <div className="dim" style={{ fontSize: 14 }}>Hackcoin is play money. It can't be bought, sold or cashed out.</div>
      </Section>

      <Section title="Host password">
        <div className="stack" style={{ gap: 6, maxWidth: 420 }}>
          <label htmlFor="host-password" className="dim small">The password set for this deployment</label>
          <input
            id="host-password"
            className="input"
            type="password"
            autoComplete="current-password"
            aria-invalid={!!passwordError}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {passwordError ? (
            <div className="error" role="alert">{passwordError}</div>
          ) : (
            <div className="dim small">You'll use it again on the host page to pick winners.</div>
          )}
        </div>
      </Section>

      {formError && <div className="error" role="alert">{formError}</div>}

      <div className="row between" style={{ gap: 16 }}>
        <Link
          className="btn"
          to="/setup"
          style={{ display: 'flex', alignItems: 'center', minHeight: 52, padding: '0 20px', borderRadius: 10, fontSize: 16 }}
        >
          Back
        </Link>
        <div className="row" style={{ gap: 16 }}>
          <div className="dim" style={{ fontSize: 14 }}>{plural(marketCount, 'market')} will go live</div>
          <button
            className="btn primary"
            type="submit"
            disabled={busy}
            style={{ minHeight: 52, padding: '0 26px', borderRadius: 10, fontSize: 17 }}
          >
            {busy ? 'Launching…' : 'Launch markets'}
          </button>
        </div>
      </div>
    </form>
  );
}

function Section({ title, aside, children }: { title: string; aside?: string; children: ReactNode }) {
  return (
    <section className="card stack" style={{ borderRadius: 16, padding: 24, gap: 18 }}>
      <div className="row between" style={{ alignItems: 'baseline' }}>
        <h2 style={{ fontSize: 20 }}>{title}</h2>
        {aside && <div className="dim" style={{ fontSize: 14 }}>{aside}</div>}
      </div>
      {children}
    </section>
  );
}

type FieldLook = { style?: { borderColor: string }; 'aria-invalid'?: boolean };

type FieldProps = {
  label: string;
  error?: string | null;
  /** The page was read and this field wasn't on it: amber, until the host fills it in. */
  notFound?: boolean;
  /** Shown under the field when there is nothing else to say about it. */
  hint?: string;
  children: (look: FieldLook) => ReactNode;
};

function Field({ label, error, notFound, hint, children }: FieldProps) {
  const look: FieldLook = error ? { 'aria-invalid': true } : notFound ? { style: { borderColor: AMBER } } : {};
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span className="dim small">{label}</span>
      {children(look)}
      {error && <span className="error" role="alert">{error}</span>}
      {!error && notFound && <span className="small" style={{ color: AMBER }}>We couldn't find this one.{hint && ` ${hint}`}</span>}
      {!error && !notFound && hint && <span className="dim small">{hint}</span>}
    </label>
  );
}

function Setting({ label, value }: { label: string; value: string }) {
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="dim small">{label}</div>
      <div style={{ fontSize: 16 }}>{value}</div>
    </div>
  );
}

type CategoryCardProps = {
  index: number;
  category: Category;
  byHand: boolean;
  onChange: (change: Partial<Category>) => void;
  onRemove: () => void;
};

function CategoryCard({ index, category, byHand, onChange, onRemove }: CategoryCardProps) {
  const hasMarket = wantsMarket(category);
  // Only a category read from the host's page can have a prize that "wasn't on the page".
  const prizeMissing = !byHand && !category.added && !category.prize;
  return (
    <div className="stack" style={{ background: 'var(--bg)', border: '1px solid var(--border-strong)', borderRadius: 12, padding: 16, gap: 12 }}>
      <div className="row between" style={{ flexWrap: 'nowrap', gap: 10 }}>
        <label className="row" style={{ gap: 10, minHeight: 44, flexWrap: 'nowrap', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={hasMarket}
            onChange={(e) => onChange({ create_market: e.target.checked })}
            style={{ width: 20, height: 20, margin: 0, accentColor: 'var(--accent)' }}
          />
          <span style={{ fontSize: 14, color: hasMarket ? 'var(--text)' : 'var(--text-dim)' }}>
            {hasMarket ? 'Open a market' : 'No market for this one'}
          </span>
        </label>
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove category ${index + 1}${category.name ? `, ${category.name}` : ''}`}
          className="dim"
          style={{ minHeight: 44, minWidth: 44, background: 'none', border: 'none', padding: '0 4px', fontSize: 14, textDecoration: 'underline' }}
        >
          Remove
        </button>
      </div>
      <label className="stack" style={{ gap: 6 }}>
        <span className="dim small">Category</span>
        <input
          className="input"
          aria-label={`Category ${index + 1} name`}
          placeholder="e.g. Best overall"
          value={category.name}
          // A new name may fit a different Scout score, so the server matches it again at launch.
          onChange={(e) => onChange({ name: e.target.value, market_id: null, create_market: hasMarket })}
        />
      </label>
      <label className="stack" style={{ gap: 6 }}>
        <span className="dim small">Prize</span>
        <input
          className="input"
          aria-label={`Category ${index + 1} prize`}
          placeholder={prizeMissing ? 'Not on the page, add a prize' : 'Optional'}
          value={category.prize ?? ''}
          onChange={(e) => onChange({ prize: e.target.value })}
          style={prizeMissing ? { borderColor: AMBER } : undefined}
        />
      </label>
    </div>
  );
}
