from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FROZEN_CONFIG_SHA256 = "c4cb3db23563b7aa022abb7d80bbfc7bea0e320d20072e3f82efb28b5c13154a"


def test_frozen_config_hash_is_unchanged() -> None:
    payload = (ROOT / "config/monte_carlo_v0_1.yaml").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == FROZEN_CONFIG_SHA256


def test_frozen_public_results_have_complete_valid_replications_and_zero_qlike_floors() -> None:
    replications = pd.read_csv(ROOT / "results/synthetic/monte_carlo_replications.csv")
    summary = pd.read_csv(ROOT / "results/synthetic/monte_carlo_summary.csv")
    keys = ["scenario", "horizon", "loss"]
    grouped = replications.groupby(keys, sort=True)
    assert len(replications) == 2400
    assert len(summary) == 12
    assert (grouped.size() == 200).all()
    assert (grouped["replication"].nunique() == 200).all()
    assert replications["qlike_numerically_valid"].astype(bool).all()
    assert int(replications["har_qlike_floor_count"].sum()) == 0
    assert int(replications["harp_qlike_floor_count"].sum()) == 0

    for key, group in grouped:
        row = summary.loc[
            (summary["scenario"] == key[0])
            & (summary["horizon"] == key[1])
            & (summary["loss"] == key[2])
        ].iloc[0]
        ratios = group["loss_ratio_harp_over_har"].to_numpy(float)
        assert int(row["replications"]) == 200
        assert np.isclose(row["median_loss_ratio"], np.median(ratios), rtol=1e-14)
        assert np.isclose(row["p2_5_loss_ratio"], np.percentile(ratios, 2.5), rtol=1e-14)
        assert np.isclose(row["p97_5_loss_ratio"], np.percentile(ratios, 97.5), rtol=1e-14)
