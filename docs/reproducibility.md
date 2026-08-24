# Reproducibility

## Frozen study identity

- Configuration: `config/monte_carlo_v0_1.yaml`
- Configuration SHA-256: `c4cb3db23563b7aa022abb7d80bbfc7bea0e320d20072e3f82efb28b5c13154a`
- Master seed: `20250107342`
- Scenarios: `no_periodicity`, `u_shaped_periodicity`
- Replications: 200 paired replications per scenario
- Forecast origins: 500 common origins per replication
- Horizons: 1, 5, and 22 days
- Losses: MSE and QLIKE

`numpy.random.SeedSequence` derives immutable child seeds, stored in `artifacts/synthetic/child_seeds.json`. Results are sorted deterministically, so the numerical CSV files are independent of worker count. Within each replication, scenario pairs share the same latent and intraday innovations.

## Environment

The package targets Python 3.12 and pins numerical, plotting, test, and lint dependencies in `pyproject.toml`. Create a fresh environment from the repository root:

```bash
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Bounded smoke run

```bash
python scripts/run_monte_carlo.py --root reproductions/smoke-serial --workers 1 --smoke
python scripts/run_monte_carlo.py --root reproductions/smoke-parallel --workers 2 --smoke
```

The two replication CSVs below should be byte-for-byte identical:

```text
reproductions/smoke-serial/.private_audit/h1_smoke/replications_workers_1.csv
reproductions/smoke-parallel/.private_audit/h1_smoke/replications_workers_2.csv
```

The smoke configuration is intentionally small and does not reproduce the headline table.

## Full frozen run

The full run is CPU-intensive and is intentionally excluded from CI:

```bash
python scripts/run_monte_carlo.py --root reproductions/full --config config/monte_carlo_v0_1.yaml --workers 4
```

It writes the same result/artifact/figure layout beneath `reproductions/full`. On the audited Windows reference run, the 200-replication study completed in 132.23 seconds and peak worker RSS was 124,358,656 bytes; these telemetry values are environment-specific and are not reproducibility criteria.

## Frozen artifact checksums

| Artifact | SHA-256 |
|---|---|
| `results/synthetic/monte_carlo_replications.csv` | `0b4438de766310936f3454774019f30e4010b681594c4d900e2309999b837606` |
| `results/synthetic/monte_carlo_summary.csv` | `4364029b52714a85a6191e5a43377e754b49e48f83f8447818dcb9990597dce0` |
| `artifacts/synthetic/child_seeds.json` | `d299cc16db52ff14e65933fdce2fbf238852f61ee985ac510a63e629b851545a` |
| `figures/synthetic/periodicity_factors.png` | `f9b0487e548aaedd70fa0205ecd8eddb89d56bfa8db1cbcae60ca6a269086933` |
| `figures/synthetic/loss_ratio_distributions.png` | `469fa435e865ceba37679ed99f75ccf934f4d3326fc6f5854ae7f5b48359002c` |

Use a local SHA-256 utility or Python's `hashlib.sha256(path.read_bytes()).hexdigest()` to compare outputs. Runtime fields in a newly generated run manifest and non-data PNG metadata may differ; the numerical CSVs and child-seed file are the frozen reproducibility criteria.

## Verify the release

```bash
python -m pytest
ruff check .
ruff format --check .
```

See [Validation](validation.md) for the invariants these commands cover.
