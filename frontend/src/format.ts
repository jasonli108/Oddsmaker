/** Prices and odds arrive as fractions (0.27). These turn them into what the design shows. */

export const pct = (fraction: number) => `${Math.round(fraction * 100)}%`;

export const multiple = (m: number) => `${m.toFixed(1)}x`;

export const coin = (n: number) => Math.round(n).toLocaleString('en-US');

export function ago(iso: string, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

/** Milliseconds as H:MM:SS, e.g. 11:42:08, or MM:SS under an hour. */
export function countdown(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const two = (n: number) => String(n).padStart(2, '0');
  const hours = Math.floor(total / 3600);
  const rest = `${two(Math.floor((total % 3600) / 60))}:${two(total % 60)}`;
  return hours > 0 ? `${hours}:${rest}` : rest;
}

/** A gap between two fractions in whole percentage points, e.g. points(0.27, 0.31) is -4. */
export const points = (a: number, b: number) => Math.round(a * 100) - Math.round(b * 100);

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** "Oct 11, 11:59 PM", in the viewer's own time zone. */
export const dateTime = (date: Date) =>
  date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

export const clock =(iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
