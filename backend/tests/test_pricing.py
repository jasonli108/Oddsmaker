"""The market rules, starting with the build spec's worked example."""

import pytest

from app.market import pricing

FLOOR = 0.02
# Orbit holds 540 of the 2,000 seed; the other five teams share the rest.
WEIGHTS = {"orbit": 540, "ledger": 500, "parsel": 400, "night": 260, "kiln": 200, "tally": 100}


def test_opening_price_and_locked_multiple():
    prices = pricing.prices_from_weights(WEIGHTS, FLOOR)
    assert prices["orbit"] == pytest.approx(0.27)
    assert sum(prices.values()) == pytest.approx(1)
    assert pricing.multiple_for(prices["orbit"]) == pytest.approx(3.7, abs=0.01)


def test_a_bet_moves_the_price():
    after = pricing.prices_from_weights({**WEIGHTS, "orbit": 640}, FLOOR)
    assert after["orbit"] == pytest.approx(0.305, abs=0.0005)


def test_price_floor_caps_the_multiple_at_50x():
    prices = pricing.prices_from_weights({"a": 1999, "b": 1}, FLOOR)
    assert prices["b"] >= FLOOR
    assert pricing.multiple_for(prices["b"]) <= 50


def test_floored_prices_still_sum_to_one():
    # Lifting c to the floor shrinks b from just above 2% to below it, so b must be floored too.
    prices = pricing.prices_from_weights({"a": 9790, "b": 201, "c": 9}, FLOOR)
    assert prices["b"] == pytest.approx(FLOOR)
    assert prices["c"] == pytest.approx(FLOOR)
    assert sum(prices.values()) == pytest.approx(1)


def test_a_team_with_no_weight_gets_the_floor_not_zero():
    prices = pricing.prices_from_weights({"a": 1000, "b": 1000, "new": 0}, FLOOR)
    assert prices["new"] == pytest.approx(FLOOR)
    assert prices["a"] == pytest.approx(0.49)


def test_empty_and_weightless_markets():
    assert pricing.prices_from_weights({}, FLOOR) == {}
    assert pricing.prices_from_weights({"a": 0, "b": 0}, FLOOR) == {"a": 0.5, "b": 0.5}


def test_more_teams_than_the_floor_allows_splits_evenly_at_worst():
    prices = pricing.prices_from_weights({f"t{i}": 1 for i in range(100)}, FLOOR)
    assert sum(prices.values()) == pytest.approx(1)
    assert all(p == pytest.approx(0.01) for p in prices.values())


def test_scores_become_odds_and_split_the_seed():
    odds = pricing.odds_from_scores({"orbit": 54, "ledger": 146})
    assert odds == pytest.approx({"orbit": 0.27, "ledger": 0.73})
    assert pricing.split_seed(odds, 2000) == pytest.approx({"orbit": 540, "ledger": 1460})
