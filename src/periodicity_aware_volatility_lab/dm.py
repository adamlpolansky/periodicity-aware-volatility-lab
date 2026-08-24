from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DMResult:
    mean_differential: float
    bandwidth: int
    statistic_unadjusted: float
    hln_factor: float
    statistic: float
    p_value_two_sided: float
    rejection_direction: str


def hac_bandwidth(sample_size: int, horizon: int) -> int:
    if sample_size <= 0 or horizon <= 0:
        raise ValueError("sample_size and horizon must be positive")
    return max(horizon - 1, math.floor(4 * (sample_size / 100) ** (2 / 9)))


def diebold_mariano(
    harp_loss: np.ndarray, har_loss: np.ndarray, horizon: int, alpha: float = 0.05
) -> DMResult:
    harp = np.asarray(harp_loss, dtype=float)
    har = np.asarray(har_loss, dtype=float)
    if harp.shape != har.shape or harp.ndim != 1 or len(harp) < 2:
        raise ValueError("DM requires matching one-dimensional loss vectors")
    if not np.isfinite(harp).all() or not np.isfinite(har).all():
        raise ValueError("DM losses must be finite")
    differential = harp - har
    sample_size = len(differential)
    bandwidth = hac_bandwidth(sample_size, horizon)
    centered = differential - differential.mean()
    long_run = float(centered @ centered / sample_size)
    for lag in range(1, bandwidth + 1):
        covariance = float(centered[lag:] @ centered[:-lag] / sample_size)
        long_run += 2 * (1 - lag / (bandwidth + 1)) * covariance
    if long_run <= 0 or not np.isfinite(long_run):
        statistic_unadjusted = 0.0 if np.allclose(differential, differential[0]) else float("nan")
    else:
        statistic_unadjusted = float(differential.mean() / math.sqrt(long_run / sample_size))
    hln_argument = (
        sample_size + 1 - 2 * horizon + horizon * (horizon - 1) / sample_size
    ) / sample_size
    if hln_argument <= 0:
        raise ValueError("HLN correction is undefined for this sample size and horizon")
    hln_factor = math.sqrt(hln_argument)
    statistic = statistic_unadjusted * hln_factor
    p_value = math.erfc(abs(statistic) / math.sqrt(2)) if np.isfinite(statistic) else float("nan")
    direction = ("HARP" if statistic < 0 else "HAR") if p_value < alpha else "NONE"
    return DMResult(
        mean_differential=float(differential.mean()),
        bandwidth=bandwidth,
        statistic_unadjusted=statistic_unadjusted,
        hln_factor=hln_factor,
        statistic=statistic,
        p_value_two_sided=p_value,
        rejection_direction=direction,
    )
