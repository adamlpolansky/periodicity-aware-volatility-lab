from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psutil
import yaml

from periodicity_aware_volatility_lab.simulation import (
    DISCLAIMER,
    SimulationSettings,
    aggregate_replications,
    periodicity_factors,
    run_monte_carlo,
    settings_as_dict,
    smoke_settings,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def plot_factors(output: Path, amplitude: float) -> None:
    factors = periodicity_factors(amplitude)
    slot = np.arange(1, 79)
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=160)
    ax.plot(
        slot, factors["no_periodicity"], color="#6b7280", linestyle="--", label="no_periodicity"
    )
    ax.plot(slot, factors["u_shaped_periodicity"], color="#2864a8", label="u_shaped_periodicity")
    ax.set(
        xlim=(1, 78),
        xlabel="5-minute intraday slot",
        ylabel="Pre-specified synthetic periodicity factor",
    )
    fig.suptitle("Frozen synthetic periodicity factors", x=0.08, y=0.985, ha="left", weight="bold")
    ax.set_title(
        "Both satisfy mean(f²)=1 across 78 slots",
        loc="left",
        fontsize=10,
        color="#4b5563",
        pad=12,
    )
    ax.grid(axis="y", color="#d7dde5", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, DISCLAIMER, fontsize=8.5, color="#374151")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def plot_ratios(frame: pd.DataFrame, output: Path) -> None:
    scenarios = ["no_periodicity", "u_shaped_periodicity"]
    losses = ["MSE", "QLIKE"]
    colors = {"no_periodicity": "#6b7280", "u_shaped_periodicity": "#2864a8"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.8), dpi=160, sharey=False)
    for ax, loss in zip(axes, losses, strict=True):
        arrays = []
        positions = []
        box_colors = []
        labels = []
        position = 1
        for horizon in (1, 5, 22):
            for scenario in scenarios:
                group = frame.loc[
                    (frame["loss"] == loss)
                    & (frame["horizon"] == horizon)
                    & (frame["scenario"] == scenario),
                    "loss_ratio_harp_over_har",
                ]
                arrays.append(group.to_numpy(float))
                positions.append(position)
                box_colors.append(colors[scenario])
                labels.append(
                    f"h={horizon}\n{'none' if scenario == 'no_periodicity' else 'U-shape'}"
                )
                position += 1
            position += 0.6
        boxes = ax.boxplot(
            arrays, positions=positions, widths=0.65, patch_artist=True, showfliers=True
        )
        for patch, color in zip(boxes["boxes"], box_colors, strict=True):
            patch.set_facecolor(color)
            patch.set_alpha(0.72)
        ax.axhline(1.0, color="#111827", linewidth=1.0, linestyle="--")
        ax.set_xticks(positions, labels, fontsize=8)
        ax.set_ylabel("Synthetic HARP / HAR mean-loss ratio")
        ax.set_title(f"Synthetic {loss} ratio distributions", loc="left", weight="bold")
        ax.grid(axis="y", color="#e5e7eb", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("All paired synthetic Monte Carlo replications", x=0.02, ha="left", weight="bold")
    fig.text(
        0.02,
        0.945,
        "Focused ratio scale; dashed line at 1.0 marks equal mean loss.",
        fontsize=9,
        color="#4b5563",
    )
    fig.text(0.01, 0.01, DISCLAIMER, fontsize=8.5, color="#374151")
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.smoke:
        settings = smoke_settings()
        output = root / ".private_audit/h1_smoke"
        config_hash = None
    else:
        if args.config is None:
            raise ValueError("Full run requires --config")
        config_path = args.config.resolve()
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        settings = SimulationSettings.from_mapping(payload)
        output = root
        config_hash = sha256_file(config_path)

    frame, seeds, telemetry, runtime = run_monte_carlo(settings, args.workers)
    summary = aggregate_replications(frame)
    if args.smoke:
        output.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output / f"replications_workers_{args.workers}.csv", index=False)
        write_json(
            output / f"receipt_workers_{args.workers}.json",
            {
                "settings": settings_as_dict(settings),
                "runtime_seconds": runtime,
                "worker_telemetry": telemetry,
                "rows": len(frame),
                "disclaimer": DISCLAIMER,
            },
        )
    else:
        results = output / "results/synthetic"
        artifacts = output / "artifacts/synthetic"
        figures = output / "figures/synthetic"
        results.mkdir(parents=True, exist_ok=True)
        frame.to_csv(results / "monte_carlo_replications.csv", index=False, float_format="%.17g")
        summary.to_csv(results / "monte_carlo_summary.csv", index=False, float_format="%.17g")
        write_json(artifacts / "child_seeds.json", seeds)
        write_json(
            artifacts / "run_manifest.json",
            {
                "captured_utc": datetime.now(UTC).isoformat(),
                "config_sha256": config_hash,
                "settings": settings_as_dict(settings),
                "runtime_seconds": runtime,
                "peak_worker_rss_bytes": max(item["peak_rss_bytes"] for item in telemetry),
                "parent_rss_bytes": psutil.Process().memory_info().rss,
                "worker_telemetry": telemetry,
                "python": sys.version,
                "platform": platform.platform(),
                "workers": args.workers,
                "deterministic_sort": ["replication", "scenario", "horizon", "loss"],
                "disclaimer": DISCLAIMER,
            },
        )
        plot_factors(figures / "periodicity_factors.png", settings.periodicity_amplitude)
        plot_ratios(frame, figures / "loss_ratio_distributions.png")
    print(json.dumps({"rows": len(frame), "runtime_seconds": runtime, "output": str(output)}))


if __name__ == "__main__":
    main()
