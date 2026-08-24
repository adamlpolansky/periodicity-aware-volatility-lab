from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

M = 78
DELTA = 1.0 / M
BV_CONSTANT = 1.57


@dataclass(frozen=True)
class AggregatedSession:
    bars_5m: pd.DataFrame
    returns: np.ndarray
    rv: float
    bv: float
    telescoping_error: float
    volume_difference: int


def realized_variance(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=float)
    if values.shape != (M,) or not np.isfinite(values).all():
        raise ValueError("RV requires exactly 78 finite returns")
    return float(np.sum(values * values))


def returns_from_endpoint_prices(endpoint_prices: np.ndarray) -> np.ndarray:
    """Convert 79 strictly positive within-session endpoints into 78 log returns."""
    values = np.asarray(endpoint_prices, dtype=float)
    if values.shape != (M + 1,) or not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("Endpoint construction requires 79 finite positive prices")
    return np.diff(np.log(values))


def bipower_variation(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=float)
    if values.shape != (M,) or not np.isfinite(values).all():
        raise ValueError("BV requires exactly 78 finite within-session returns")
    return float((M / (M - 1)) * BV_CONSTANT * np.sum(np.abs(values[1:]) * np.abs(values[:-1])))


def aggregate_full_session(frame: pd.DataFrame) -> AggregatedSession:
    required = ["datetime", "Open", "High", "Low", "Close", "Volume"]
    if any(column not in frame.columns for column in required):
        raise ValueError("Missing required one-minute columns")
    ordered = frame.sort_values("datetime", kind="mergesort").reset_index(drop=True)
    if len(ordered) != 390 or ordered["datetime"].nunique() != 390:
        raise ValueError("A full session must have exactly 390 unique one-minute bars")
    expected = pd.date_range(ordered.loc[0, "datetime"], periods=390, freq="min")
    if not ordered["datetime"].equals(pd.Series(expected, name="datetime")):
        raise ValueError("One-minute timestamps do not form a gap-free grid")

    minute_number = np.arange(390)
    bucket = minute_number // 5
    grouped = ordered.assign(_bucket=bucket).groupby("_bucket", sort=True)
    bars = grouped.agg(
        datetime=("datetime", "first"),
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum"),
        source=("source", "first")
        if "source" in ordered.columns
        else ("Close", lambda _: "synthetic"),
        minute_count=("datetime", "size"),
    ).reset_index(drop=True)
    if len(bars) != M or not (bars["minute_count"] == 5).all():
        raise ValueError("Aggregation did not yield 78 five-minute buckets of five bars")

    endpoints = np.concatenate(([float(ordered.loc[0, "Open"])], bars["Close"].to_numpy(float)))
    returns = returns_from_endpoint_prices(endpoints)
    if returns.shape != (M,):
        raise AssertionError("Session-open endpoint construction must yield 78 returns")
    telescope = float(
        np.sum(returns) - np.log(float(ordered.loc[389, "Close"]) / float(ordered.loc[0, "Open"]))
    )
    volume_difference = int(bars["Volume"].sum() - ordered["Volume"].sum())
    return AggregatedSession(
        bars_5m=bars,
        returns=returns,
        rv=realized_variance(returns),
        bv=bipower_variation(returns),
        telescoping_error=telescope,
        volume_difference=volume_difference,
    )
