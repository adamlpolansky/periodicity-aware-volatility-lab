# Validation

The public test suite covers the numerical and causal contracts that matter for the synthetic evidence pack.

## Method invariants

- Realized variance and literal-constant bipower variation formulas are checked against hand calculations.
- Five-minute aggregation uses within-session endpoints only; no overnight return or cross-session BV pair is admitted.
- WSD factors satisfy the required `mean(f²) = 1` normalization and each application-day vintage uses only `[t-1008, t-1]`.
- Historical filtered realized variance remains immutable when later observations arrive.
- HAR and HARP use the same unfiltered direct target; only HARP's right-hand-side predictors are filtered.
- Each horizon-specific OLS model is re-fit at every origin on exactly 1,000 fully known rows.
- The last eligible training row satisfies `s + h <= t`; future-target perturbations do not change an earlier forecast.
- The QLIKE positive-forecast floor is explicit, counted, and subject to a validity threshold.
- The DM loss differential has the fixed sign `L_HARP - L_HAR`, with pre-specified HAC bandwidth and HLN correction.

## Simulation invariants

- Scenario pairs share latent and intraday innovations.
- Child seeds are deterministic and results are stable across worker counts.
- The no-periodicity factor is exactly flat; the U-shaped factor follows the frozen formula and normalization.
- All headline model paths estimate periodicity causally; no oracle factor enters a forecast model.

## Frozen artifact integrity

Tests independently reconstruct the summary from the replication rows, verify 12/12 complete cells with 200 replications each, enforce zero QLIKE floor hits, check the frozen config hash, and compare the committed CSV/seed/figure hashes against their recorded values.

The audited post-change full rerun reproduced both numerical CSV files and child seeds byte-for-byte. The only accepted figure change was the public labeling/metadata revision; no plotted data or model/numerical path changed.

## Run locally

```bash
python -m pytest
ruff check .
ruff format --check .
```

CI repeats those checks on Python 3.12 and compares serial and two-worker bounded smoke outputs byte-for-byte. It never downloads data and never launches the full 200-replication study.
