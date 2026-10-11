/**
 * How Scout's labels and source kinds are shown.
 *
 * The labels are the ones Scout's prompt asks Gemini for (REPORT_PROMPT in
 * backend/app/scout/gemini.py). Keep the two in step: a label not listed here renders in the
 * neutral colour, which is also where the middling ones ("Some overlap", "Fair") belong.
 */

// originality: Fresh | build: On pace | demo: Live | prize fit: Strong
const GOOD = ['fresh', 'on pace', 'live', 'strong'];
// originality: Crowded | build: Slowing, Stalled, No repo | demo: Slow, Down, Missing | prize fit: Weak
const CAUTION = ['crowded', 'slowing', 'stalled', 'no repo', 'slow', 'down', 'missing', 'weak'];

export function labelColor(label: string): string {
  const key = label.trim().toLowerCase();
  if (GOOD.includes(key)) return 'var(--good)';
  if (CAUTION.includes(key)) return 'var(--amber)';
  return 'var(--text-soft)';
}

// Scout emits repo, demo and similar today (build_report in backend/app/scout/gemini.py).
const SOURCE_KINDS: Record<string, string> = {
  repo: 'Repo',
  demo: 'Deployed demo',
  similar: 'Similar project',
  event: 'Judging criteria',
};

export function sourceKindLabel(kind: string): string {
  return SOURCE_KINDS[kind.trim().toLowerCase()] ?? kind.charAt(0).toUpperCase() + kind.slice(1);
}
