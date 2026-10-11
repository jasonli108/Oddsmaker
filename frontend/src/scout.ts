/**
 * How Scout's free-text labels and source kinds are shown.
 *
 * TODO(frontend): these lists are a guess at what Gemini will return. Agree a fixed vocabulary
 * with stream C (or add a tone field to the report) so a new label can't land on the wrong colour.
 * Anything not listed here renders in the neutral colour.
 */

const GOOD = ['on pace', 'ahead', 'live', 'polished', 'working', 'strong', 'good', 'original', 'unique', 'novel'];
const CAUTION = ['crowded', 'behind', 'stalled', 'slow', 'missing', 'down', 'broken', 'not submitted', 'weak', 'poor'];

export function labelColor(label: string): string {
  const key = label.trim().toLowerCase();
  if (GOOD.includes(key)) return 'var(--good)';
  if (CAUTION.includes(key)) return 'var(--amber)';
  return 'var(--text-soft)';
}

const SOURCE_KINDS: Record<string, string> = {
  repo: 'Repo',
  demo: 'Deployed demo',
  similar: 'Similar project',
  gallery: 'Past hackathon gallery',
  event: 'Judging criteria',
};

export function sourceKindLabel(kind: string): string {
  return SOURCE_KINDS[kind.trim().toLowerCase()] ?? kind.charAt(0).toUpperCase() + kind.slice(1);
}
