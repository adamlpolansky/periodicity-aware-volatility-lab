# Public claims and non-claims

## What the frozen synthetic study supports

This project is a provider-agnostic HAR/HARP implementation and a two-scenario synthetic Monte Carlo mechanism check. The public evidence supports only the following bounded statements:

- In the `no_periodicity` scenario, median HARP/HAR mean-loss ratios are approximately one across horizons 1, 5, and 22 under both MSE and QLIKE.
- In the pre-specified `u_shaped_periodicity` scenario, the six median ratios range from approximately 0.9903 to 0.9934. Under this synthetic mechanism, that is a small median forecast-loss reduction for HARP relative to HAR.
- Outcomes are not universal. Each central 95% cross-replication interval spans one, and some individual replications favor HAR.
- All 12 scenario/horizon/loss cells contain 200 valid replications. The frozen public run records zero QLIKE floor interventions.

The loss ratio is `mean(HARP loss) / mean(HAR loss)`, so a value below one favors HARP. The reported 2.5th and 97.5th percentiles are the endpoints of a **central 95% cross-replication interval** over the 200 realized ratios in a cell. They are not a confidence interval for the median, do not estimate uncertainty in the median, and are not a significance test.

## Complete frozen public summary

DM rates are the shares of the 200 replications in which the pre-specified two-sided 5% Diebold-Mariano test rejects in the stated direction. `HARP` is a significant negative `HARP-HAR` loss differential; `HAR` is a significant positive differential. These are simulation rejection frequencies, not one global test of the median ratio.

| Scenario | h | Loss | Valid replications | Median ratio | Central 95% p2.5 | Central 95% p97.5 | Ratio < 1 | DM reject HARP | DM reject HAR |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| no_periodicity | 1 | MSE | 200 | 1.000052 | 0.997780 | 1.002212 | 48.0% | 3.5% | 2.5% |
| no_periodicity | 1 | QLIKE | 200 | 1.000030 | 0.998145 | 1.002054 | 49.5% | 3.0% | 2.5% |
| no_periodicity | 5 | MSE | 200 | 1.000121 | 0.996006 | 1.004221 | 46.0% | 2.5% | 8.0% |
| no_periodicity | 5 | QLIKE | 200 | 1.000249 | 0.996529 | 1.003814 | 46.5% | 3.0% | 6.0% |
| no_periodicity | 22 | MSE | 200 | 1.000365 | 0.993367 | 1.007085 | 45.0% | 4.0% | 3.5% |
| no_periodicity | 22 | QLIKE | 200 | 1.000153 | 0.994162 | 1.005771 | 47.0% | 5.0% | 3.5% |
| u_shaped_periodicity | 1 | MSE | 200 | 0.993432 | 0.975368 | 1.008786 | 80.0% | 10.5% | 0.5% |
| u_shaped_periodicity | 1 | QLIKE | 200 | 0.993102 | 0.978529 | 1.005612 | 80.5% | 15.0% | 0.5% |
| u_shaped_periodicity | 5 | MSE | 200 | 0.991390 | 0.962267 | 1.022804 | 73.5% | 12.0% | 1.5% |
| u_shaped_periodicity | 5 | QLIKE | 200 | 0.990955 | 0.965880 | 1.018718 | 75.5% | 14.5% | 1.0% |
| u_shaped_periodicity | 22 | MSE | 200 | 0.991562 | 0.951434 | 1.040630 | 64.0% | 10.0% | 1.5% |
| u_shaped_periodicity | 22 | QLIKE | 200 | 0.990306 | 0.954082 | 1.037642 | 66.5% | 12.0% | 1.0% |

## What the project does not establish

- It is not an exact replication of either paper. In particular, the causal WSD estimator uses a pre-frozen 1,008-completed-day project extension rather than the final article's 20-day main window.
- It is not empirical market evidence, trading evidence, profitability evidence, or an investment result.
- It does not show that HARP always outperforms HAR, even under the U-shaped synthetic scenario.
- The cross-replication percentile interval is not evidence that a median differs significantly from one.
- DM rejection rates are design-specific simulation frequencies; they are not statistical power claims for real markets.
- No claim is made about jumps, market microstructure realism, time-varying periodicity, alternative models, or scenarios outside the two frozen mechanisms.
