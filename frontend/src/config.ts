/** The starting Hackcoin the setup form suggests. Each host sets their own event's amount. Matches the backend default. */
export const STARTING_BALANCE = 1000;

/** The spec's polling interval for the market, history and feed endpoints. No websockets tonight. */
export const POLL_MS = 5000;

export const STAKE_PRESETS = [50, 100, 250, 500];

/** How often Scout refreshes every team. Must match SCOUT_INTERVAL_MINUTES on the backend. */
export const SCOUT_INTERVAL_MS = 30 * 60 * 1000;

/** The Scout reports tab compares Scout's odds with the price in the event's market for this score. */
export const HEADLINE_SCORE_KEY = 'overall';
