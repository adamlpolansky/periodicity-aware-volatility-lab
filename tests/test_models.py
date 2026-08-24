from __future__ import annotations

import numpy as np

from periodicity_aware_volatility_lab.models import (
    HORIZONS,
    TRAINING_ROWS,
    future_targets,
    paired_forecasts,
    right_sided_design,
    rolling_direct_forecasts,
    training_indices,
)
from periodicity_aware_volatility_lab.periodicity import M, T, causal_periodicity_vintages


def test_unfiltered_future_target_and_horizons() -> None:
    rv = np.arange(1, 40, dtype=float)
    for horizon in HORIZONS:
        target = future_targets(rv, horizon)
        assert np.isclose(target[5], rv[6 : 6 + horizon].mean())
    filtered = rv * 0.01
    assert np.isclose(future_targets(rv, 5)[5], rv[6:11].mean())
    assert not np.isclose(future_targets(rv, 5)[5], filtered[6:11].mean())


def test_target_end_embargo_and_exact_1000_training_rows() -> None:
    for horizon in HORIZONS:
        indices = training_indices(origin=2100, horizon=horizon)
        assert len(indices) == TRAINING_ROWS
        assert indices[-1] + horizon == 2100
        assert np.all(indices + horizon <= 2100)
        assert indices[-1] + horizon + 1 > 2100


def test_right_sided_features_use_current_and_past_only() -> None:
    values = np.arange(1, 50, dtype=float)
    design = right_sided_design(values)
    assert np.isclose(design[21, 1], values[21])
    assert np.isclose(design[21, 2], values[17:22].mean())
    assert np.isclose(design[21, 3], values[:22].mean())


def test_future_poisoning_does_not_change_earlier_features_or_forecast() -> None:
    rng = np.random.default_rng(19)
    n_days = 2074
    returns = rng.normal(scale=0.001, size=(n_days, M))
    rv = np.sum(returns**2, axis=1)
    vintages = causal_periodicity_vintages(returns)
    origin = 2050
    baseline = paired_forecasts(rv, vintages.filtered_rv, np.array([origin]), 22)

    poisoned_returns = returns.copy()
    poisoned_returns[origin + 1 :] *= 100
    poisoned_rv = np.sum(poisoned_returns**2, axis=1)
    poisoned_vintages = causal_periodicity_vintages(poisoned_returns)
    poisoned = paired_forecasts(poisoned_rv, poisoned_vintages.filtered_rv, np.array([origin]), 22)
    assert np.array_equal(
        vintages.filtered_rv[T : origin + 1], poisoned_vintages.filtered_rv[T : origin + 1]
    )
    assert baseline.har.forecast[0] == poisoned.har.forecast[0]
    assert baseline.harp.forecast[0] == poisoned.harp.forecast[0]
    assert baseline.har.training_end[0] + 22 == origin


def test_adjacent_origins_are_refit_on_advancing_exact_windows() -> None:
    rng = np.random.default_rng(20260823)
    rv = rng.lognormal(mean=-9.0, sigma=0.35, size=1100)
    origins = np.array([1030, 1031])
    path = rolling_direct_forecasts(rv, rv, origins, horizon=5)
    assert np.array_equal(path.training_start, np.array([26, 27]))
    assert np.array_equal(path.training_end, np.array([1025, 1026]))
    assert np.all(path.training_end + 5 == origins)
    assert path.coefficients.shape == (2, 4)
    assert not np.array_equal(path.coefficients[0], path.coefficients[1])
