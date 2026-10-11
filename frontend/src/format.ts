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

/** Milliseconds as H:MM:SS, e.g. 11:42:08. */
export function countdown(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const two = (n: number) => String(n).padStart(2, '0');
  return `${Math.floor(total / 3600)}:${two(Math.floor((total % 3600) / 60))}:${two(total % 60)}`;
}

export const clock =(iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
