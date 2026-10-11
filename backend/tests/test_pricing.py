"""The build spec's worked example. Remove the xfail marks once app/market/pricing.py is implemented."""

import pytest

from app.market import pricing

FLOOR = 0.02
# Orbit holds 540 of the 2,000 seed; the other five teams share the rest.
WEIGHTS = {"orbit": 540, "ledger": 500, "parsel": 400, "night": 260, "kiln": 200, "tally": 100}


@pytest.mark.xfail(raises=NotImplementedError, reason="TODO(market)")
def test_opening_price_and_locked_multiple():
    prices = pricing.prices_from_weights(WEIGHTS, FLOOR)
    assert prices["orbit"] == pytest.approx(0.27)
    assert sum(prices.values()) == pytest.approx(1)
    assert pricing.multiple_for(prices["orbit"]) == pytest.approx(3.7, abs=0.01)


@pytest.mark.xfail(raises=NotImplementedError, reason="TODO(market)")
def test_a_bet_moves_the_price():
    after = pricing.prices_from_weights({**WEIGHTS, "orbit": 640}, FLOOR)
    assert after["orbit"] == pytest.approx(0.305, abs=0.0005)


@pytest.mark.xfail(raises=NotImplementedError, reason="TODO(market)")
def test_price_floor_caps_the_multiple_at_50x():
    prices = pricing.prices_from_weights({"a": 1999, "b": 1}, FLOOR)
    assert prices["b"] >= FLOOR
    assert pricing.multiple_for(prices["b"]) <= 50


@pytest.mark.xfail(raises=NotImplementedError, reason="TODO(market)")
def test_scores_become_odds_and_split_the_seed():
    odds = pricing.odds_from_scores({"orbit": 54, "ledger": 146})
    assert odds == pytest.approx({"orbit": 0.27, "ledger": 0.73})
    assert pricing.split_seed(odds, 2000) == pytest.approx({"orbit": 540, "ledger": 1460})
