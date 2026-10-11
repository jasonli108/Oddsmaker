"""Market rules as pure functions. No database, no I/O, so they are easy to test.

The rules (build spec, "Market rules"):
1. A team's weight in a market is Scout's seed for it plus all Hackcoin staked on it.
2. A team's price is its weight divided by the market's total weight. Prices sum to 1.
3. Each market holds `seed_per_market` Hackcoin of seed, split across teams by Scout's odds.
   Re-splitting the seed at each refresh is how Scout moves the price.
4. A bet locks a multiple of 1 / current price, then adds its stake to that team's weight.
5. Prices are floored at `price_floor` (2%), so no multiple goes above 50x.

Worked example: Orbit's seed is 540 of 2,000, so its price is 27%. A 100 stake locks 3.7x.
Orbit's weight becomes 640 of 2,100, so the next price is 30.5%.

tests/test_pricing.py encodes that example; it is marked xfail until these are implemented.
"""


def prices_from_weights(weights: dict[str, float], floor: float) -> dict[str, float]:
    """Map team_id -> price from team_id -> weight (seed + staked), applying the price floor."""
    raise NotImplementedError("TODO(market)")


def multiple_for(price: float) -> float:
    """The payout multiple locked in by a bet placed at `price`."""
    raise NotImplementedError("TODO(market)")


def split_seed(odds: dict[str, float], seed_total: float) -> dict[str, float]:
    """Split a market's seed across teams in proportion to Scout's odds."""
    raise NotImplementedError("TODO(market)")


def odds_from_scores(scores: dict[str, int]) -> dict[str, float]:
    """Turn Scout's per-team scores for one category into odds: score / sum of all teams' scores."""
    raise NotImplementedError("TODO(market)")
