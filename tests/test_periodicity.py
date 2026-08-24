from __future__ import annotations

import numpy as np

from periodicity_aware_volatility_lab.aggregation import DELTA
from periodicity_aware_volatility_lab.periodicity import (
    M,
    T,
    causal_periodicity_vintages,
    causal_window,
    compute_wsd_factor,
)


def test_wsd_normalization() -> None:
    rng = np.random.default_rng(20260823)
    shape = 0.8 + 0.7 * np.abs(np.linspace(-1, 1, M))
    returns = rng.normal(size=(T, M)) * shape[None, :] * 0.001
    result = compute_wsd_factor(returns)
    assert np.isclose(DELTA * np.sum(result.factor**2), 1.0, rtol=0.0, atol=1e-12)
    assert (result.factor > 0).all()


def test_causal_window_excludes_current_and_future() -> None:
    dates = list(range(1100))
    window = causal_window(dates, application_index=1050)
    assert len(window) == T
    assert window[0] == 42
    assert window[-1] == 1049
    assert 1050 not in window
    assert max(window) < 1050


def test_vintage_is_exact_and_historical_value_is_not_revised() -> None:
    rng = np.random.default_rng(7)
    returns = rng.normal(scale=0.001, size=(T + 3, M))
    original = causal_periodicity_vintages(returns, last_application=T + 2)
    poisoned = np.vstack([returns, np.full((5, M), 10.0)])
    extended = causal_periodicity_vintages(poisoned, last_application=T + 2)
    assert original.vintage_start[T] == 0
    assert original.vintage_end[T] == T - 1
    assert original.vintage_end[T + 1] == T
    assert np.array_equal(original.factors[T : T + 2], extended.factors[T : T + 2])
    assert np.array_equal(original.filtered_rv[T : T + 2], extended.filtered_rv[T : T + 2])
    assert not original.filtered_rv.flags.writeable


def test_rolling_vintage_matches_standalone_wsd() -> None:
    rng = np.random.default_rng(11)
    returns = rng.normal(scale=0.001, size=(T + 2, M))
    vintages = causal_periodicity_vintages(returns)
    expected = compute_wsd_factor(returns[1 : T + 1]).factor
    assert np.allclose(vintages.factors[T + 1], expected, rtol=0.0, atol=1e-14)


def test_application_day_return_does_not_affect_its_own_factor() -> None:
    rng = np.random.default_rng(47)
    returns = rng.normal(scale=0.001, size=(T + 1, M))
    baseline = causal_periodicity_vintages(returns)
    poisoned_returns = returns.copy()
    poisoned_returns[T, 0] *= 100
    poisoned = causal_periodicity_vintages(poisoned_returns)
    assert np.array_equal(baseline.factors[T], poisoned.factors[T])
    assert baseline.vintage_end[T] == T - 1
    assert baseline.filtered_rv[T] != poisoned.filtered_rv[T]
