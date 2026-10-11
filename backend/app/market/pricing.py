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
"""

_EPSILON = 1e-12


def prices_from_weights(weights: dict[str, float], floor: float) -> dict[str, float]:
    """Map team_id -> price from team_id -> weight (seed + staked), applying the price floor.

    Prices always sum to 1. A team below the floor is lifted to it, and the teams above the
    floor give up that share between them in proportion to their weight.
    """
    if not weights:
        return {}
    total = sum(weights.values())
    if total <= 0:
        return {team: 1 / len(weights) for team in weights}

    # With more than 1/floor teams the floor cannot hold for everyone; an even split is the cap.
    floor = min(floor, 1 / len(weights))
    floored: set[str] = set()
    while True:
        free = {team: w for team, w in weights.items() if team not in floored}
        share = 1 - floor * len(floored)
        free_total = sum(free.values())
        prices = {team: (w / free_total) * share for team, w in free.items()} if free_total > 0 else {}
        newly_below = [team for team in free if prices.get(team, 0) < floor - _EPSILON]
        if not newly_below:
            break
        # Lifting these teams shrinks everyone else, which can push another team under: go again.
        floored.update(newly_below)
    return {team: floor if team in floored else prices[team] for team in weights}


def multiple_for(price: float) -> float:
    """The payout multiple locked in by a bet placed at `price`."""
    return 1 / price


def payout(stake: float, multiple: float) -> float:
    """What one winning bet pays, to the cent.

    The bet receipt and the resolve step both call this, so the amount promised is the amount paid.
    """
    return round(stake * multiple, 2)


def split_seed(odds: dict[str, float], seed_total: float) -> dict[str, float]:
    """Split a market's seed across teams in proportion to Scout's odds."""
    if not odds:
        return {}
    total = sum(odds.values())
    if total <= 0:
        return {team: seed_total / len(odds) for team in odds}
    return {team: seed_total * o / total for team, o in odds.items()}


def odds_from_scores(scores: dict[str, int]) -> dict[str, float]:
    """Turn Scout's per-team scores for one category into odds: score / sum of all teams' scores."""
    if not scores:
        return {}
    total = sum(scores.values())
    if total <= 0:
        return {team: 1 / len(scores) for team in scores}
    return {team: s / total for team, s in scores.items()}
