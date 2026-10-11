import { useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Team } from '../api/types';

/** Team sign-up: name, one-line idea, repo link, demo link. No design exists for this screen yet. */
export default function SignUpPage() {
  const [form, setForm] = useState({ name: '', idea: '', repo_url: '', demo_url: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Team | null>(null);

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setCreated(
        await api.createTeam({
          name: form.name.trim(),
          idea: form.idea.trim(),
          repo_url: form.repo_url.trim() || null,
          demo_url: form.demo_url.trim() || null,
        }),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <div className="container stack" style={{ paddingTop: 28, maxWidth: 560 }}>
        <h1>{created.name} is in.</h1>
        <div className="dim">Scout is writing its first report now. Your team shows up in every market as soon as it's done.</div>
        <Link className="btn primary" to={`/reports/${created.id}`} style={{ display: 'grid', placeItems: 'center' }}>
          See your Scout report
        </Link>
      </div>
    );
  }

  return (
    <form className="container stack" onSubmit={onSubmit} style={{ paddingTop: 28, paddingBottom: 48, maxWidth: 560 }}>
      <h1>Sign up your team</h1>
      <div className="dim">
        Scout reads only the links you submit here, publishes a report on your project, and sets your opening odds.
      </div>
      <Field label="Team name">
        <input className="input" required maxLength={60} value={form.name} onChange={set('name')} />
      </Field>
      <Field label="Your idea in one line">
        <input className="input" required maxLength={200} value={form.idea} onChange={set('idea')} />
      </Field>
      <Field label="Repo link">
        <input className="input" type="url" placeholder="https://github.com/…" value={form.repo_url} onChange={set('repo_url')} />
      </Field>
      <Field label="Demo link (add it later if it isn't live yet)">
        <input className="input" type="url" placeholder="https://…" value={form.demo_url} onChange={set('demo_url')} />
      </Field>
      {error && <div className="error">{error}</div>}
      <button className="btn primary" type="submit" disabled={busy}>
        {busy ? 'Signing up…' : 'Sign up'}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span className="dim small">{label}</span>
      {children}
    </label>
  );
}
