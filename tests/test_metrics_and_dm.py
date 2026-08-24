from __future__ import annotations

import math

import numpy as np

from periodicity_aware_volatility_lab.dm import diebold_mariano, hac_bandwidth
from periodicity_aware_volatility_lab.metrics import mse, qlike


def test_mse_and_qlike() -> None:
    actual = np.array([1.0, 2.0])
    forecast = np.array([1.0, 1.0])
    assert np.array_equal(mse(actual, forecast), np.array([0.0, 1.0]))
    values, count, fraction, valid = qlike(actual, forecast, np.array([1e-12, 1e-12]))
    assert np.isclose(values[0], 0.0)
    assert np.isclose(values[1], 2 - np.log(2) - 1)
    assert (count, fraction, valid) == (0, 0.0, True)


def test_qlike_floor_counter_and_validity_threshold() -> None:
    actual = np.ones(1000)
    forecast = np.ones(1000)
    forecast[0:2] = [0.0, -1.0]
    values, count, fraction, valid = qlike(actual, forecast, np.full(1000, 1e-12))
    assert np.isfinite(values).all()
    assert count == 2
    assert fraction == 0.002
    assert valid is False


def test_dm_sign_bandwidth_and_hln_correction() -> None:
    rng = np.random.default_rng(31)
    har = 1.0 + rng.normal(0, 0.05, 500)
    harp = har - 0.1 + rng.normal(0, 0.01, 500)
    result = diebold_mariano(harp, har, horizon=5)
    expected_bandwidth = max(4, math.floor(4 * (500 / 100) ** (2 / 9)))
    expected_hln = math.sqrt((500 + 1 - 10 + 5 * 4 / 500) / 500)
    assert hac_bandwidth(500, 5) == expected_bandwidth
    assert result.bandwidth == expected_bandwidth
    assert np.isclose(result.hln_factor, expected_hln)
    assert result.mean_differential < 0
    assert result.statistic < 0
    assert result.rejection_direction == "HARP"
