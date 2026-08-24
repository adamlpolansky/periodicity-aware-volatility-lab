from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HORIZONS = (1, 5, 22)
FEATURE_LOOKBACK = 22
TRAINING_ROWS = 1000


@dataclass(frozen=True)
class ForecastPath:
    origins: np.ndarray
    actual: np.ndarray
    forecast: np.ndarray
    coefficients: np.ndarray
    training_start: np.ndarray
    training_end: np.ndarray
    qlike_floor: np.ndarray


@dataclass(frozen=True)
class PairedForecasts:
    har: ForecastPath
    harp: ForecastPath


def future_targets(realized_variance: np.ndarray, horizon: int) -> np.ndarray:
    """Unfiltered target: mean RV over days t+1 through t+h."""
    if horizon not in HORIZONS:
        raise ValueError(f"Unsupported horizon: {horizon}")
    rv = np.asarray(realized_variance, dtype=float)
    if rv.ndim != 1 or not np.isfinite(rv).all() or np.any(rv <= 0):
        raise ValueError("realized_variance must be a positive finite vector")
    target = np.full(len(rv), np.nan)
    cumulative = np.concatenate(([0.0], np.cumsum(rv)))
    valid = np.arange(0, len(rv) - horizon)
    target[valid] = (cumulative[valid + horizon + 1] - cumulative[valid + 1]) / horizon
    return target


def right_sided_design(series: np.ndarray) -> np.ndarray:
    """Intercept plus daily, 5-day, and 22-day right-sided predictors."""
    values = np.asarray(series, dtype=float)
    if values.ndim != 1:
        raise ValueError("Predictor series must be one-dimensional")
    design = np.full((len(values), 4), np.nan)
    cumulative = np.concatenate(([0.0], np.cumsum(np.nan_to_num(values, nan=0.0))))
    valid_value = np.isfinite(values)
    valid_count = np.concatenate(([0], np.cumsum(valid_value.astype(int))))
    for day in range(FEATURE_LOOKBACK - 1, len(values)):
        if valid_count[day + 1] - valid_count[day + 1 - FEATURE_LOOKBACK] != FEATURE_LOOKBACK:
            continue
        daily = values[day]
        weekly = (cumulative[day + 1] - cumulative[day - 4]) / 5
        monthly = (cumulative[day + 1] - cumulative[day - 21]) / 22
        design[day] = (1.0, daily, weekly, monthly)
    return design


def training_indices(origin: int, horizon: int, rows: int = TRAINING_ROWS) -> np.ndarray:
    """Last exact rows whose target end is no later than the forecast origin."""
    if horizon not in HORIZONS or rows <= 0:
        raise ValueError("Invalid horizon or training-row count")
    end = origin - horizon
    start = end - rows + 1
    if start < 0:
        raise ValueError("Insufficient training history")
    indices = np.arange(start, end + 1, dtype=np.int64)
    if len(indices) != rows or np.any(indices + horizon > origin):
        raise AssertionError("Training target-end embargo failed")
    return indices


def _prefix_cross_products(design: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    clean_x = np.nan_to_num(design, nan=0.0)
    clean_y = np.nan_to_num(target, nan=0.0)
    xx = np.einsum("ni,nj->nij", clean_x, clean_x)
    xy = clean_x * clean_y[:, None]
    return (
        np.concatenate((np.zeros((1, 4, 4)), np.cumsum(xx, axis=0))),
        np.concatenate((np.zeros((1, 4)), np.cumsum(xy, axis=0))),
    )


def rolling_direct_forecasts(
    predictor_series: np.ndarray,
    realized_variance: np.ndarray,
    origins: np.ndarray,
    horizon: int,
    rows: int = TRAINING_ROWS,
) -> ForecastPath:
    design = right_sided_design(predictor_series)
    target = future_targets(realized_variance, horizon)
    prefix_xx, prefix_xy = _prefix_cross_products(design, target)
    origin_values = np.asarray(origins, dtype=np.int64)
    forecasts = np.empty(len(origin_values))
    coefficients = np.empty((len(origin_values), 4))
    starts = np.empty(len(origin_values), dtype=np.int64)
    ends = np.empty(len(origin_values), dtype=np.int64)
    floors = np.empty(len(origin_values))

    for position, origin in enumerate(origin_values):
        indices = training_indices(int(origin), horizon, rows)
        start = int(indices[0])
        end = int(indices[-1])
        if not np.isfinite(design[start : end + 1]).all():
            raise ValueError("Training window contains unavailable right-sided predictors")
        if not np.isfinite(target[start : end + 1]).all():
            raise ValueError("Training window contains unavailable targets")
        if not np.isfinite(design[origin]).all() or not np.isfinite(target[origin]):
            raise ValueError("Forecast origin lacks predictors or future target")
        gram = prefix_xx[end + 1] - prefix_xx[start]
        cross = prefix_xy[end + 1] - prefix_xy[start]
        try:
            beta = np.linalg.solve(gram, cross)
        except np.linalg.LinAlgError:
            beta = np.linalg.lstsq(design[start : end + 1], target[start : end + 1], rcond=None)[0]
        coefficients[position] = beta
        forecasts[position] = float(design[origin] @ beta)
        starts[position] = start
        ends[position] = end
        positive = target[start : end + 1]
        positive = positive[positive > 0]
        if not len(positive):
            raise ValueError("QLIKE floor requires positive training targets")
        floors[position] = 1e-12 * float(np.median(positive))

    return ForecastPath(
        origins=origin_values,
        actual=target[origin_values],
        forecast=forecasts,
        coefficients=coefficients,
        training_start=starts,
        training_end=ends,
        qlike_floor=floors,
    )


def paired_forecasts(
    realized_variance: np.ndarray,
    filtered_realized_variance: np.ndarray,
    origins: np.ndarray,
    horizon: int,
    rows: int = TRAINING_ROWS,
) -> PairedForecasts:
    har = rolling_direct_forecasts(realized_variance, realized_variance, origins, horizon, rows)
    harp = rolling_direct_forecasts(
        filtered_realized_variance, realized_variance, origins, horizon, rows
    )
    if not np.array_equal(har.origins, harp.origins) or not np.array_equal(har.actual, harp.actual):
        raise AssertionError("HAR and HARP must share origins and unfiltered targets")
    return PairedForecasts(har=har, harp=harp)
