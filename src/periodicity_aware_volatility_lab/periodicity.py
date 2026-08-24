from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .aggregation import BV_CONSTANT, DELTA, M

T = 1008
KAPPA = T // 2 + 1


@dataclass(frozen=True)
class WSDResult:
    factor: np.ndarray
    short_h: np.ndarray
    wsd: np.ndarray
    retained_counts: np.ndarray
    normalization: float


@dataclass(frozen=True)
class CausalVintages:
    """Historical filtered RV values paired with their original information vintage."""

    factors: np.ndarray
    filtered_rv: np.ndarray
    vintage_start: np.ndarray
    vintage_end: np.ndarray


def standardized_returns(returns_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(returns_matrix, dtype=float)
    if values.ndim != 2 or values.shape[1] != M:
        raise ValueError("Return matrix must have 78 intraday columns")
    if not np.isfinite(values).all():
        raise ValueError("Return matrix contains nonfinite values")
    bv = (
        (M / (M - 1)) * BV_CONSTANT * np.sum(np.abs(values[:, 1:]) * np.abs(values[:, :-1]), axis=1)
    )
    if np.any(~np.isfinite(bv)) or np.any(bv <= 0):
        raise ValueError("BV_NONPOSITIVE_OR_NONFINITE")
    return values / np.sqrt(DELTA * bv[:, None]), bv


def _factor_from_standardized(rbar: np.ndarray, ordered: np.ndarray | None = None) -> WSDResult:
    if rbar.shape != (T, M):
        raise ValueError(f"WSD requires exactly {T} sessions by {M} slots")
    ordered = np.sort(rbar, axis=0) if ordered is None else ordered
    spans = ordered[KAPPA - 1 :, :] - ordered[: T - KAPPA + 1, :]
    short_h = 0.741 * np.min(spans, axis=0)
    if np.any(~np.isfinite(short_h)) or np.any(short_h <= 0):
        raise ValueError("SHORTH_NONPOSITIVE_OR_NONFINITE")
    short_norm = np.sqrt(DELTA * np.sum(short_h * short_h))
    if not np.isfinite(short_norm) or short_norm <= 0:
        raise ValueError("SHORTH_ZERO_DENOMINATOR")
    f_short = short_h / short_norm
    chi = (rbar / f_short[None, :]) ** 2 <= 6.635
    retained = chi.sum(axis=0)
    if np.any(retained == 0):
        raise ValueError("WSD_NO_RETAINED_WEIGHT")
    wsd = np.sqrt(1.081 * np.sum(np.where(chi, rbar * rbar, 0.0), axis=0) / retained)
    if np.any(~np.isfinite(wsd)) or np.any(wsd <= 0):
        raise ValueError("WSD_NONPOSITIVE_OR_NONFINITE")
    denominator = np.sqrt(DELTA * np.sum(wsd * wsd))
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("WSD_ZERO_DENOMINATOR")
    factor = wsd / denominator
    normalization = float(DELTA * np.sum(factor * factor))
    if not np.isclose(normalization, 1.0, rtol=0.0, atol=1e-12):
        raise AssertionError(f"WSD normalization failed: {normalization!r}")
    return WSDResult(factor, short_h, wsd, retained, normalization)


def compute_wsd_factor(returns_matrix: np.ndarray) -> WSDResult:
    values = np.asarray(returns_matrix, dtype=float)
    if values.shape != (T, M):
        raise ValueError(f"WSD requires exactly {T} sessions by {M} slots")
    rbar, _ = standardized_returns(values)
    return _factor_from_standardized(rbar)


def _roll_sorted_columns(ordered: np.ndarray, outgoing: np.ndarray, incoming: np.ndarray) -> None:
    """Update 78 sorted columns exactly after one rolling-window step."""
    for slot in range(M):
        column = ordered[:, slot]
        remove_at = int(np.searchsorted(column, outgoing[slot], side="left"))
        if remove_at >= T or column[remove_at] != outgoing[slot]:
            raise AssertionError("Outgoing standardized return is absent from rolling order")
        if remove_at < T - 1:
            column[remove_at:-1] = column[remove_at + 1 :]
        insert_at = int(np.searchsorted(column[:-1], incoming[slot], side="right"))
        if insert_at < T - 1:
            column[insert_at + 1 :] = column[insert_at:-1]
        column[insert_at] = incoming[slot]


def causal_periodicity_vintages(
    returns_matrix: np.ndarray,
    first_application: int = T,
    last_application: int | None = None,
) -> CausalVintages:
    """Compute past-only WSD vintages and never revise historical filtered RV."""
    values = np.asarray(returns_matrix, dtype=float)
    if values.ndim != 2 or values.shape[1] != M or not np.isfinite(values).all():
        raise ValueError("returns_matrix must contain finite rows of 78 intraday returns")
    n_days = len(values)
    stop = n_days if last_application is None else last_application
    if first_application < T or stop > n_days or first_application >= stop:
        raise ValueError("Invalid causal-vintage application range")
    standardized, _ = standardized_returns(values)
    factors = np.full((n_days, M), np.nan, dtype=float)
    filtered_rv = np.full(n_days, np.nan, dtype=float)
    vintage_start = np.full(n_days, -1, dtype=np.int64)
    vintage_end = np.full(n_days, -1, dtype=np.int64)

    ordered = np.sort(standardized[first_application - T : first_application], axis=0)
    for day in range(first_application, stop):
        window = standardized[day - T : day]
        result = _factor_from_standardized(window, ordered)
        factors[day] = result.factor
        filtered_rv[day] = float(np.sum((values[day] / result.factor) ** 2))
        vintage_start[day] = day - T
        vintage_end[day] = day - 1
        if day + 1 < stop:
            _roll_sorted_columns(ordered, standardized[day - T], standardized[day])

    for array in (factors, filtered_rv, vintage_start, vintage_end):
        array.setflags(write=False)
    return CausalVintages(factors, filtered_rv, vintage_start, vintage_end)


def causal_window(
    session_dates: list[object], application_index: int, window: int = T
) -> list[object]:
    if application_index < window:
        raise ValueError("Insufficient causal history")
    return list(session_dates[application_index - window : application_index])
