from __future__ import annotations

import pandas as pd

from periodicity_aware_volatility_lab.data_adapter import (
    split_observed_sessions,
    validate_canonical_bars,
)


def synthetic_bars() -> pd.DataFrame:
    timestamps = pd.DatetimeIndex(
        [
            pd.Timestamp("2025-01-02 15:59", tz="America/New_York"),
            pd.Timestamp("2025-01-03 09:31", tz="America/New_York"),
        ]
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0, 110.0],
            "high": [101.0, 111.0],
            "low": [99.0, 109.0],
            "close": [100.5, 110.5],
            "volume": [1_000.0, 2_000.0],
            "symbol": ["SYN", "SYN"],
        }
    )


def test_canonical_adapter_preserves_observed_rows_without_fill_or_overnight_join() -> None:
    bars = validate_canonical_bars(synthetic_bars())
    sessions = split_observed_sessions(bars, "America/New_York")
    assert len(bars) == 2
    assert len(sessions) == 2
    assert [len(session) for session in sessions] == [1, 1]
    assert sessions[1].iloc[0]["open"] == 110.0


def test_canonical_adapter_requires_timezone_aware_timestamp() -> None:
    bars = synthetic_bars()
    bars["timestamp"] = pd.DatetimeIndex(bars["timestamp"]).tz_localize(None)
    try:
        validate_canonical_bars(bars)
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("Naive timestamps must be rejected")
