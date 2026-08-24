from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from periodicity_aware_volatility_lab.simulation import (
    _one_replication,
    periodicity_factors,
    run_monte_carlo,
    seed_records,
    smoke_settings,
)


def test_synthetic_factor_normalization() -> None:
    for factor in periodicity_factors().values():
        assert np.isclose(np.mean(factor**2), 1.0, rtol=0.0, atol=1e-15)


def test_seedsequence_child_seeds_are_deterministic_and_distinct() -> None:
    first = seed_records(20250107342, 5)
    second = seed_records(20250107342, 5)
    assert first == second
    assert len({tuple(item["state_uint32"]) for item in first}) == 5


def test_small_serial_and_spawn_parallel_smoke_outputs_match() -> None:
    settings = replace(
        smoke_settings(), replications=1, usable_days=2075, oos_origins=2, max_workers=2
    )
    serial, serial_seeds, _, _ = run_monte_carlo(settings, workers=1)
    parallel, parallel_seeds, _, _ = run_monte_carlo(settings, workers=2)
    pd.testing.assert_frame_equal(serial, parallel, check_exact=True)
    assert serial_seeds == parallel_seeds


def test_one_replication_shares_latent_and_intraday_innovations_across_scenarios(
    monkeypatch,
) -> None:
    import periodicity_aware_volatility_lab.simulation as simulation

    captured_returns: list[np.ndarray] = []
    original = simulation.causal_periodicity_vintages

    def capture(returns: np.ndarray):
        captured_returns.append(returns.copy())
        return original(returns)

    monkeypatch.setattr(simulation, "causal_periodicity_vintages", capture)
    settings = replace(
        smoke_settings(), replications=1, usable_days=2075, oos_origins=2, max_workers=2
    )
    state = seed_records(settings.master_seed, 1)[0]["state_uint32"]
    _one_replication(0, state, settings)
    factors = periodicity_factors(settings.periodicity_amplitude)
    assert len(captured_returns) == 2
    base_flat = captured_returns[0] / factors["no_periodicity"][None, :]
    base_shaped = captured_returns[1] / factors["u_shaped_periodicity"][None, :]
    assert np.allclose(base_flat, base_shaped, rtol=0.0, atol=1e-18)
