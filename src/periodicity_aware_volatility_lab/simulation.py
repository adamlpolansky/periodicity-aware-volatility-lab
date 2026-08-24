from __future__ import annotations

import math
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import psutil

from .aggregation import M
from .dm import diebold_mariano
from .metrics import evaluate_losses
from .models import HORIZONS, TRAINING_ROWS, paired_forecasts
from .periodicity import T, causal_periodicity_vintages

DISCLAIMER = (
    "Synthetic mechanism check — not empirical SPY evidence, trading evidence, "
    "or an exact paper replication."
)


@dataclass(frozen=True)
class SimulationSettings:
    master_seed: int
    replications: int
    burn_in_days: int
    usable_days: int
    oos_origins: int
    intraday_slots: int = M
    wsd_window: int = T
    training_rows: int = TRAINING_ROWS
    horizons: tuple[int, ...] = HORIZONS
    max_workers: int = 4
    omega: float = 0.05 * math.log(1e-4)
    daily_ar: float = 0.35
    weekly_ar: float = 0.30
    monthly_ar: float = 0.30
    innovation_scale: float = 0.25
    periodicity_amplitude: float = 0.6
    qlike_floor_multiplier: float = 1e-12
    qlike_invalid_fraction: float = 0.001
    dm_alpha: float = 0.05

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> SimulationSettings:
        dgp = payload["dgp"]
        protocol = payload["protocol"]
        inference = payload["inference"]
        return cls(
            master_seed=int(protocol["master_seed"]),
            replications=int(protocol["replications_per_scenario"]),
            burn_in_days=int(protocol["burn_in_days"]),
            usable_days=int(protocol["usable_days"]),
            oos_origins=int(protocol["common_oos_origins"]),
            max_workers=int(protocol["max_workers"]),
            omega=float(dgp["omega"]),
            daily_ar=float(dgp["daily_ar"]),
            weekly_ar=float(dgp["weekly_ar"]),
            monthly_ar=float(dgp["monthly_ar"]),
            innovation_scale=float(dgp["innovation_scale"]),
            periodicity_amplitude=float(dgp["periodicity_amplitude"]),
            qlike_floor_multiplier=float(inference["qlike_floor_multiplier"]),
            qlike_invalid_fraction=float(inference["qlike_invalid_fraction"]),
            dm_alpha=float(inference["dm_alpha"]),
        )


def smoke_settings() -> SimulationSettings:
    return SimulationSettings(
        master_seed=20250107342,
        replications=2,
        burn_in_days=30,
        usable_days=2076,
        oos_origins=3,
        max_workers=2,
    )


def periodicity_factors(amplitude: float = 0.6) -> dict[str, np.ndarray]:
    no_periodicity = np.ones(M)
    slot = np.arange(1, M + 1, dtype=float)
    squared = 1 + amplitude * np.cos(2 * np.pi * (slot - 0.5) / M)
    u_shaped = np.sqrt(squared / squared.mean())
    for factor in (no_periodicity, u_shaped):
        if not np.isclose(np.mean(factor**2), 1.0, atol=1e-15, rtol=0.0):
            raise AssertionError("Synthetic periodicity factor normalization failed")
    return {"no_periodicity": no_periodicity, "u_shaped_periodicity": u_shaped}


def _latent_variance(
    settings: SimulationSettings, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    total = settings.burn_in_days + settings.usable_days
    eta = rng.standard_normal(total)
    z = rng.standard_normal((total, M))
    anchor = math.log(1e-4)
    history = np.full(total + 22, anchor, dtype=float)
    for step in range(total):
        position = step + 22
        history[position] = (
            settings.omega
            + settings.daily_ar * history[position - 1]
            + settings.weekly_ar * history[position - 5 : position].mean()
            + settings.monthly_ar * history[position - 22 : position].mean()
            + settings.innovation_scale * eta[step]
        )
    latent = np.exp(history[22 + settings.burn_in_days :])
    return latent, z[settings.burn_in_days :]


def seed_records(master_seed: int, replications: int) -> list[dict[str, object]]:
    children = np.random.SeedSequence(master_seed).spawn(replications)
    return [
        {
            "replication": index,
            "master_entropy": master_seed,
            "spawn_key": list(child.spawn_key),
            "state_uint32": child.generate_state(4).tolist(),
        }
        for index, child in enumerate(children)
    ]


def _worker_peak_rss() -> int:
    info = psutil.Process(os.getpid()).memory_info()
    return int(max(info.rss, getattr(info, "peak_wset", 0) or 0))


def _one_replication(
    replication: int, seed_state: list[int], settings: SimulationSettings
) -> tuple[list[dict[str, object]], dict[str, object]]:
    started = time.perf_counter()
    rng = np.random.default_rng(np.random.SeedSequence(seed_state))
    latent, innovations = _latent_variance(settings, rng)
    maximum_horizon = max(settings.horizons)
    maximum_origin = settings.usable_days - maximum_horizon - 1
    minimum_origin = maximum_origin - settings.oos_origins + 1
    origins = np.arange(minimum_origin, maximum_origin + 1, dtype=np.int64)
    factors = periodicity_factors(settings.periodicity_amplitude)
    output: list[dict[str, object]] = []

    for scenario, factor in factors.items():
        returns = np.sqrt(latent / M)[:, None] * factor[None, :] * innovations
        rv = np.sum(returns**2, axis=1)
        vintages = causal_periodicity_vintages(returns)
        rvp = vintages.filtered_rv
        for horizon in settings.horizons:
            paired = paired_forecasts(rv, rvp, origins, horizon, settings.training_rows)
            har_losses = evaluate_losses(
                paired.har.actual, paired.har.forecast, paired.har.qlike_floor
            )
            harp_losses = evaluate_losses(
                paired.harp.actual, paired.harp.forecast, paired.harp.qlike_floor
            )
            for loss_name, har_values, harp_values in (
                ("MSE", har_losses.mse, harp_losses.mse),
                ("QLIKE", har_losses.qlike, harp_losses.qlike),
            ):
                dm = diebold_mariano(harp_values, har_values, horizon, settings.dm_alpha)
                output.append(
                    {
                        "replication": replication,
                        "scenario": scenario,
                        "horizon": horizon,
                        "loss": loss_name,
                        "har_mean_loss": float(har_values.mean()),
                        "harp_mean_loss": float(harp_values.mean()),
                        "loss_ratio_harp_over_har": float(harp_values.mean() / har_values.mean()),
                        "dm_mean_differential_harp_minus_har": dm.mean_differential,
                        "dm_bandwidth": dm.bandwidth,
                        "dm_hln_factor": dm.hln_factor,
                        "dm_statistic": dm.statistic,
                        "dm_p_value_two_sided": dm.p_value_two_sided,
                        "dm_rejection_direction": dm.rejection_direction,
                        "har_qlike_floor_count": har_losses.qlike_floor_count,
                        "harp_qlike_floor_count": harp_losses.qlike_floor_count,
                        "har_qlike_floor_fraction": har_losses.qlike_floor_fraction,
                        "harp_qlike_floor_fraction": harp_losses.qlike_floor_fraction,
                        "qlike_numerically_valid": (
                            har_losses.qlike_valid and harp_losses.qlike_valid
                            if loss_name == "QLIKE"
                            else True
                        ),
                        "oos_forecasts": len(origins),
                        "disclaimer": DISCLAIMER,
                    }
                )
    return output, {
        "replication": replication,
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_bytes": _worker_peak_rss(),
    }


def run_monte_carlo(
    settings: SimulationSettings, workers: int
) -> tuple[pd.DataFrame, list[dict[str, object]], list[dict[str, object]], float]:
    if workers < 1 or workers > settings.max_workers or workers > 4:
        raise ValueError("workers must be between 1 and the frozen maximum of 4")
    started = time.perf_counter()
    records = seed_records(settings.master_seed, settings.replications)
    tasks = [(item["replication"], item["state_uint32"], settings) for item in records]
    results: list[tuple[list[dict[str, object]], dict[str, object]]]
    if workers == 1:
        results = [_one_replication(*task) for task in tasks]
    else:
        context = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
            futures = [executor.submit(_one_replication, *task) for task in tasks]
            results = [future.result() for future in futures]
    rows = [row for result, _ in results for row in result]
    telemetry = [item for _, item in results]
    frame = (
        pd.DataFrame.from_records(rows)
        .sort_values(["replication", "scenario", "horizon", "loss"], kind="mergesort")
        .reset_index(drop=True)
    )
    return frame, records, telemetry, time.perf_counter() - started


def aggregate_replications(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (scenario, horizon, loss), group in frame.groupby(
        ["scenario", "horizon", "loss"], sort=True
    ):
        ratios = group["loss_ratio_harp_over_har"].to_numpy(float)
        rows.append(
            {
                "scenario": scenario,
                "horizon": int(horizon),
                "loss": loss,
                "replications": len(group),
                "median_loss_ratio": float(np.median(ratios)),
                "p2_5_loss_ratio": float(np.percentile(ratios, 2.5)),
                "p97_5_loss_ratio": float(np.percentile(ratios, 97.5)),
                "share_ratio_below_one": float(np.mean(ratios < 1.0)),
                "dm_rejection_rate_harp": float(np.mean(group["dm_rejection_direction"] == "HARP")),
                "dm_rejection_rate_har": float(np.mean(group["dm_rejection_direction"] == "HAR")),
                "total_har_qlike_floor_count": int(group["har_qlike_floor_count"].sum()),
                "total_harp_qlike_floor_count": int(group["harp_qlike_floor_count"].sum()),
                "share_qlike_numerically_valid": float(
                    group["qlike_numerically_valid"].astype(bool).mean()
                ),
                "disclaimer": DISCLAIMER,
            }
        )
    return pd.DataFrame.from_records(rows)


def settings_as_dict(settings: SimulationSettings) -> dict[str, object]:
    return asdict(settings)
