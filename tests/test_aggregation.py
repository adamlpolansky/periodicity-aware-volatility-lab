from __future__ import annotations

import numpy as np
import pandas as pd

from periodicity_aware_volatility_lab.aggregation import (
    aggregate_full_session,
    bipower_variation,
    returns_from_endpoint_prices,
)


def synthetic_session(
    day: str, open_price: float = 100.0, minute_log_return: float = 0.0001
) -> pd.DataFrame:
    times = pd.date_range(f"{day} 09:30", periods=390, freq="min")
    opens = open_price * np.exp(minute_log_return * np.arange(390))
    closes = open_price * np.exp(minute_log_return * np.arange(1, 391))
    return pd.DataFrame(
        {
            "datetime": times,
            "Open": opens,
            "High": np.maximum(opens, closes) * 1.00001,
            "Low": np.minimum(opens, closes) * 0.99999,
            "Close": closes,
            "Volume": np.arange(1, 391, dtype=np.int64),
            "source": "synthetic",
        }
    )


def test_390_to_78_open_anchor_telescoping_and_volume() -> None:
    frame = synthetic_session("2020-01-02")
    result = aggregate_full_session(frame)
    assert len(result.bars_5m) == 78
    assert len(result.returns) == 78
    assert np.isclose(result.returns[0], np.log(frame.iloc[4].Close / frame.iloc[0].Open))
    assert abs(result.telescoping_error) < 1e-14
    assert result.volume_difference == 0
    assert result.bars_5m.Volume.sum() == frame.Volume.sum()


def test_79_endpoint_prices_yield_78_returns() -> None:
    endpoints = 100 * np.exp(np.linspace(0, 0.02, 79))
    returns = returns_from_endpoint_prices(endpoints)
    assert returns.shape == (78,)
    assert np.isclose(returns.sum(), np.log(endpoints[-1] / endpoints[0]))


def test_no_overnight_return_and_no_cross_session_bv_pair() -> None:
    first = aggregate_full_session(synthetic_session("2020-01-02", 100.0))
    second_frame = synthetic_session("2020-01-03", 500.0)
    second = aggregate_full_session(second_frame)
    assert np.isclose(
        second.returns[0], np.log(second_frame.iloc[4].Close / second_frame.iloc[0].Open)
    )
    assert not np.isclose(
        second.returns[0], np.log(second_frame.iloc[4].Close / first.bars_5m.iloc[-1].Close)
    )
    assert np.isclose(second.bv, bipower_variation(second.returns))


def test_bipower_variation_uses_literal_1_57_and_adjacent_within_session_pairs() -> None:
    returns = np.linspace(-0.003, 0.004, 78)
    expected = (78 / 77) * 1.57 * np.sum(np.abs(returns[1:]) * np.abs(returns[:-1]))
    assert np.isclose(bipower_variation(returns), expected, rtol=0.0, atol=1e-18)


def test_missing_or_duplicate_bar_rejected() -> None:
    frame = synthetic_session("2020-01-02")
    missing = frame.drop(index=10).reset_index(drop=True)
    duplicate = pd.concat([frame, frame.iloc[[10]]], ignore_index=True)
    for invalid in (missing, duplicate):
        try:
            aggregate_full_session(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Incomplete or duplicate session must be rejected")
