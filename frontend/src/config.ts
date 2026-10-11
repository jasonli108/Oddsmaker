/** Used until a host saves an event in setup; after that the saved event's details win (see useEvent). */
export const EVENT_NAME = 'AI Engineer NYC 2026';

/** 11:59 PM EDT on the day of the event. The header counts down to this. */
export const SUBMISSIONS_CLOSE = new Date('2026-10-11T23:59:00-04:00');

/** Hackcoin a new player gets until a host launches an event with its own amount. Matches the backend default. */
export const STARTING_BALANCE = 1000;

/** The spec's polling interval for the market, history and feed endpoints. No websockets tonight. */
export const POLL_MS = 5000;

export const STAKE_PRESETS = [50, 100, 250, 500];

/** How often Scout refreshes every team. Must match SCOUT_INTERVAL_MINUTES on the backend. */
export const SCOUT_INTERVAL_MS = 30 * 60 * 1000;

/** The Scout reports tab compares Scout's odds with the price in this market. */
export const HEADLINE_MARKET_ID = 'overall';
