from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
OPTIONAL_COLUMNS = ("symbol",)


def validate_canonical_bars(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate a provider-agnostic observed-minute-bar table without filling gaps."""
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing canonical columns: {missing}")
    allowed = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
    unknown = sorted(set(frame.columns) - allowed)
    if unknown:
        raise ValueError(f"Unexpected canonical columns: {unknown}")
    result = frame.copy()
    timestamps = pd.DatetimeIndex(result["timestamp"])
    if timestamps.tz is None:
        raise ValueError("timestamp must be timezone-aware")
    if timestamps.hasnans or timestamps.duplicated().any():
        raise ValueError("timestamp must be non-null and unique")
    if not timestamps.is_monotonic_increasing:
        raise ValueError("canonical bars must be ordered by timestamp")
    values = result[["open", "high", "low", "close", "volume"]].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("OHLCV values must be finite")
    if (result[["open", "high", "low", "close"]].to_numpy(float) <= 0).any():
        raise ValueError("OHLC prices must be strictly positive")
    if (result["volume"].to_numpy(float) < 0).any():
        raise ValueError("volume must be nonnegative")
    if (
        (result["low"] > result["high"]).any()
        or (result["open"] < result["low"]).any()
        or (result["open"] > result["high"]).any()
        or (result["close"] < result["low"]).any()
        or (result["close"] > result["high"]).any()
    ):
        raise ValueError("OHLC cross-field constraints failed")
    return result


def split_observed_sessions(frame: pd.DataFrame, timezone: str) -> list[pd.DataFrame]:
    """Split observed bars by local date; never introduce overnight returns or fills."""
    clean = validate_canonical_bars(frame)
    local_dates = pd.DatetimeIndex(clean["timestamp"]).tz_convert(timezone).date
    work = clean.assign(_local_date=local_dates)
    return [group.drop(columns="_local_date").copy() for _, group in work.groupby("_local_date")]
