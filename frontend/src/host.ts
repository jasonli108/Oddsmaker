/** Small helpers shared by the host-facing pages (setup and the host page). */

const PASSWORD_KEY = 'oddsmaker.hostPassword';

/**
 * The host password, kept for this browser tab only so closing the tab locks the host pages
 * again. Setup stores it at launch, which is why the host page doesn't ask for it a second time.
 */
export const hostPassword = {
  get: () => sessionStorage.getItem(PASSWORD_KEY),
  set: (value: string) => sessionStorage.setItem(PASSWORD_KEY, value),
  clear: () => sessionStorage.removeItem(PASSWORD_KEY),
};

/**
 * Where attendees reach the app, for the share link and QR code. Defaults to wherever this page
 * is being served from; set VITE_PUBLIC_URL when that differs (a tunnel, or a deployed domain).
 */
export function publicOrigin(): string {
  const configured = (import.meta.env.VITE_PUBLIC_URL as string | undefined)?.trim().replace(/\/+$/, '');
  return configured || window.location.origin;
}
