import { useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import type { Team } from '../api/types';
import { useAttendeePath } from '../hooks/useAttendeePath';
import { dateTime } from '../format';
import { useEvent, useEventSlug, useSubmissionsClosed } from '../hooks/useEvent';
import { useMyTeam } from '../hooks/useMyTeam';
import { useUser } from '../hooks/useUser';

const NAME_MAX = 60;
const IDEA_MAX = 200;

const FIELDS = ['name', 'idea', 'repo_url', 'demo_url'] as const;
type Field = (typeof FIELDS)[number];
type Errors = Partial<Record<Field, string>>;

function isHttpUrl(value: string): boolean {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}

/** Team sign-up: name, one-line idea, repo link, demo link. No design exists for this screen. */
export default function SignUpPage() {
  const { user, ready: userReady } = useUser();
  const myTeam = useMyTeam();
  const { submissionsClose } = useEvent();
  const submissionsClosed = useSubmissionsClosed();
  const [form, setForm] = useState<Record<Field, string>>({ name: '', idea: '', repo_url: '', demo_url: '' });
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Team | null>(null);
  const path = useAttendeePath();
  const eventSlug = useEventSlug();

  const set = (field: Field) => (e: { target: { value: string } }) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((errs) => ({ ...errs, [field]: undefined }));
  };

  function validate(): Errors {
    const found: Errors = {};
    if (!form.name.trim()) found.name = 'Enter your team name.';
    if (!form.idea.trim()) found.idea = 'Describe your idea in one line.';
    if (form.repo_url.trim() && !isHttpUrl(form.repo_url.trim())) found.repo_url = 'Enter a full link starting with https://';
    if (form.demo_url.trim() && !isHttpUrl(form.demo_url.trim())) found.demo_url = 'Enter a full link starting with https://';
    return found;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    const found = validate();
    setErrors(found);
    setFormError(null);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      const res = await api.createTeam({
        name: form.name.trim(),
        idea: form.idea.trim(),
        repo_url: form.repo_url.trim() || null,
        demo_url: form.demo_url.trim() || null,
        creator_user_id: user.id,
        event_slug: eventSlug,
      });
      try {
        const stored = JSON.parse(localStorage.getItem('oddsmaker.myTeams') || '[]');
        if (!stored.includes(res.id)) {
          localStorage.setItem('oddsmaker.myTeams', JSON.stringify([...stored, res.id]));
        }
      } catch {}
      setCreated(res);
    } catch (err) {
      // Show the server's complaint under the field it is about, or under the form if it names none of ours.
      const fromServer: Errors = {};
      if (err instanceof ApiError) for (const f of FIELDS) if (err.fields[f]) fromServer[f] = err.fields[f];
      if (Object.keys(fromServer).length > 0) setErrors(fromServer);
      else setFormError(`Couldn't sign your team up. ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <div className="container stack" style={{ paddingTop: 28, maxWidth: 560 }}>
        <h1>{created.name} is in.</h1>
        <div className="dim">
          Scout is writing its first report now. Your team shows up in every market as soon as it's done, usually within a
          minute.
        </div>
        <div className="row" style={{ gap: 10 }}>
          <Link className="btn primary" to={path(`/reports/${created.id}`)} style={{ display: 'grid', placeItems: 'center' }}>
            See your Scout report
          </Link>
          <Link className="btn" to={path('/summary')} style={{ display: 'grid', placeItems: 'center' }}>
            View in your summary
          </Link>
          <Link className="btn" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
            Go to the markets
          </Link>
        </div>
      </div>
    );
  }

  // One team per player: someone who has signed theirs up gets its links, not the form again.
  if (myTeam) {
    return (
      <div className="container stack" style={{ paddingTop: 28, maxWidth: 560 }}>
        <h1>You've signed up {myTeam.name}</h1>
        <div className="dim">
          Each person can sign up one team, and a team only needs adding once. Your teammates don't need to add it again.
        </div>
        <div className="row" style={{ gap: 10 }}>
          <Link className="btn primary" to={path(`/reports/${myTeam.id}`)} style={{ display: 'grid', placeItems: 'center' }}>
            See your Scout report
          </Link>
          <Link className="btn" to={path('/summary')} style={{ display: 'grid', placeItems: 'center' }}>
            View in your summary
          </Link>
          <Link className="btn" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
            Go to the markets
          </Link>
        </div>
      </div>
    );
  }

  if (submissionsClosed) {
    return (
      <div className="container stack" style={{ paddingTop: 28, maxWidth: 560 }}>
        <h1>Team sign-up is closed</h1>
        <div className="dim">
          Submissions closed{submissionsClose && <> at <span className="mono">{dateTime(submissionsClose)}</span></>}, so
          no more teams can be added. Betting is closed too; the markets pay out when the organiser picks the winners.
        </div>
        <div className="row" style={{ gap: 10 }}>
          <Link className="btn primary" to={path()} style={{ display: 'grid', placeItems: 'center' }}>
            Go to the markets
          </Link>
          <Link className="btn" to={path('/reports')} style={{ display: 'grid', placeItems: 'center' }}>
            Read the Scout reports
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form className="container stack" onSubmit={onSubmit} noValidate style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 560 }}>
      <h1>Sign up your team</h1>
      <div className="dim">
        Scout reads only the links you submit here, publishes a report on your project, and sets your opening odds.
      </div>
      <div className="card small" style={{ borderColor: 'var(--amber-border)' }}>
        <span style={{ color: 'var(--amber)', fontWeight: 500 }}>One person per team.</span> Pick a team rep to add your
        project: a team that is added twice shows up twice in every market. Each person can sign up one team.
        {submissionsClose && (
          <> Sign-up closes when submissions close, at <span className="mono">{dateTime(submissionsClose)}</span>.</>
        )}
      </div>
      {userReady && !user && (
        <div className="error" role="alert">
          Pick a display name at the top of the page first. Your team is signed up under it.
        </div>
      )}

      <FieldRow label="Team name" error={errors.name}>
        <input className="input" maxLength={NAME_MAX} aria-invalid={!!errors.name} value={form.name} onChange={set('name')} />
      </FieldRow>

      <FieldRow label="Your idea in one line" error={errors.idea} hint={`${form.idea.length}/${IDEA_MAX}`}>
        <input className="input" maxLength={IDEA_MAX} aria-invalid={!!errors.idea} value={form.idea} onChange={set('idea')} />
      </FieldRow>

      <FieldRow label="Repo link (optional)" error={errors.repo_url} note="Scout reads commits and contributors from it.">
        <input
          className="input"
          inputMode="url"
          placeholder="https://github.com/…"
          aria-invalid={!!errors.repo_url}
          value={form.repo_url}
          onChange={set('repo_url')}
        />
      </FieldRow>

      <FieldRow label="Demo link (optional)" error={errors.demo_url} note="Scout checks that it loads and reads the page.">
        <input
          className="input"
          inputMode="url"
          placeholder="https://…"
          aria-invalid={!!errors.demo_url}
          value={form.demo_url}
          onChange={set('demo_url')}
        />
      </FieldRow>

      {formError && <div className="error" role="alert">{formError}</div>}
      <button className="btn primary" type="submit" disabled={busy || !user}>
        {busy ? 'Signing up…' : 'Sign up'}
      </button>
    </form>
  );
}

type FieldRowProps = {
  label: string;
  /** Shown right-aligned beside the label, e.g. a character count. */
  hint?: string;
  /** Shown under the input when there is no error. */
  note?: string;
  error?: string;
  children: ReactNode;
};

function FieldRow({ label, hint, note, error, children }: FieldRowProps) {
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span className="row between dim small" style={{ flexWrap: 'nowrap' }}>
        <span>{label}</span>
        {hint && <span className="mono">{hint}</span>}
      </span>
      {children}
      {error ? <span className="error" role="alert">{error}</span> : note && <span className="dim small">{note}</span>}
    </label>
  );
}
