from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Losses:
    mse: np.ndarray
    qlike: np.ndarray
    qlike_floor_count: int
    qlike_floor_fraction: float
    qlike_valid: bool


def mse(actual: np.ndarray, forecast: np.ndarray) -> np.ndarray:
    y = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)
    if y.shape != f.shape or not np.isfinite(y).all() or not np.isfinite(f).all():
        raise ValueError("MSE requires matching finite vectors")
    return (y - f) ** 2


def qlike(
    actual: np.ndarray, forecast: np.ndarray, floor: np.ndarray
) -> tuple[np.ndarray, int, float, bool]:
    y = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)
    floors = np.asarray(floor, dtype=float)
    if y.shape != f.shape or y.shape != floors.shape:
        raise ValueError("QLIKE inputs must have identical shapes")
    if (
        not np.isfinite(y).all()
        or np.any(y <= 0)
        or not np.isfinite(floors).all()
        or np.any(floors <= 0)
    ):
        raise ValueError("QLIKE actuals and floors must be finite and positive")
    hit = ~np.isfinite(f) | (f <= 0)
    adjusted = f.copy()
    adjusted[hit] = floors[hit]
    ratio = y / adjusted
    values = ratio - np.log(ratio) - 1.0
    count = int(hit.sum())
    fraction = count / len(y) if len(y) else 0.0
    return values, count, fraction, fraction <= 0.001


def evaluate_losses(actual: np.ndarray, forecast: np.ndarray, floor: np.ndarray) -> Losses:
    qlike_values, count, fraction, valid = qlike(actual, forecast, floor)
    return Losses(mse(actual, forecast), qlike_values, count, fraction, valid)
