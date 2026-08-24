# Method protocol v0.2

Status: frozen public methodology and synthetic Monte Carlo mechanism study.

## Public scope

The project is a reproducible HAR/HARP implementation and Monte Carlo study of periodicity-aware realized-volatility forecasting. It is not an empirical replication, an alpha claim, or a trading strategy. The public surface contains no third-party market data or restricted-data-derived result.

## Paper-defined quantities

For `M=78` five-minute intraday returns and `Delta=1/M`:

- `RV[t] = sum_i r[t,i]^2`.
- `BV[t] = (M/(M-1)) * 1.57 * sum_{i=2}^M |r[t,i]| |r[t,i-1]|`.
- `rbar[t,i] = r[t,i] / sqrt(Delta * BV[t])`.
- With the standardized returns sorted independently by slot and `kappa=floor(T/2)+1`, `ShortH[i] = 0.741 * min_k(rbar_sorted[k+kappa-1,i]-rbar_sorted[k,i])`.
- `fShortH` normalizes `ShortH` so `Delta * sum_i fShortH[i]^2=1`.
- `chi[t,i]=1[((rbar[t,i]/fShortH[i])^2 <= 6.635)]`.
- `WSD[i]=sqrt(1.081 * sum_t chi[t,i] rbar[t,i]^2 / sum_t chi[t,i])`.
- `fWSD[i]=WSD[i]/sqrt(Delta * sum_j WSD[j]^2)` and therefore `Delta * sum_i fWSD[i]^2=1`.
- Filtered returns are `rP[t,i]=r[t,i]/fWSD_vintage[t,i]`; filtered realized variance is `RVP[t]=sum_i rP[t,i]^2`.

These definitions follow working-paper equations (2)-(6), PDF pp. 6-7, and final-paper equations (2)-(6), PDF pp. 2-3 plus Appendix B.1, PDF p. 16. The literal constants `1.57`, `0.741`, `6.635`, and `1.081` are not replaced or tuned.

## Frozen causal public implementation

The paper studies both a short rolling main specification and longer robustness windows. This project pre-specifies exactly `T=1008` immediately preceding completed days for every application day. The application day and all future days are excluded. Every historical `RVP[t]` is stored with the factor estimated at that time, whose index range is `[t-1008, t-1]`; later observations never revise it.

Canonical minute inputs, when independently supplied by a user with adequate rights, must contain a timezone-aware `timestamp`, `open`, `high`, `low`, `close`, and `volume`, optional `symbol`, and one row per observed minute bar. The adapter validates only. It does not download, fill, interpolate, or join sessions. A complete 390-minute session yields 78 five-minute buckets and 79 within-session endpoints: the session open followed by 78 bucket closes. No overnight endpoint or cross-session BV pair is permitted.

At forecast origin `t`, the direct target is always unfiltered:

`y[t,h] = (1/h) * sum_{j=1}^h RV[t+j]`, for `h in {1,5,22}`.

HAR uses `[1, RV[t], mean(RV[t-4:t]), mean(RV[t-21:t])]`. HARP substitutes the corresponding immutable vintage-specific `RVP` predictors. HARP never filters the target. A distinct OLS regression is re-fit at every origin and horizon using the last exactly 1,000 fully known rows. A training row indexed `s` is eligible only when `s+h <= t`; this is tested explicitly against off-by-one leakage.

## Frozen losses and inference

- `MSE=(y-forecast)^2`.
- `QLIKE=y/forecast-log(y/forecast)-1`.
- If and only if a forecast is nonpositive or nonfinite for QLIKE, replace it with `1e-12 * median(positive training targets)` and count the intervention.
- If interventions exceed 0.1% of forecasts, the corresponding QLIKE result is numerically invalid.
- `LossRatio=mean(L_HARP)/mean(L_HAR)`; below one favors HARP.
- The loss differential is always `d=L_HARP-L_HAR`; negative favors HARP.
- Bartlett/Newey-West bandwidth is `L=max(h-1, floor(4*(N/100)^(2/9)))`.
- The Diebold-Mariano statistic receives the Harvey-Leybourne-Newbold factor `sqrt((N+1-2h+h(h-1)/N)/N)` and a two-sided asymptotic-normal 5% test.

The bandwidth rule, HLN correction, exact 1,000-row embargo, QLIKE floor, and origin indexing are project pre-specifications rather than claims of author-exact implementation.

## Frozen synthetic mechanism study

The study has exactly two scenarios. `no_periodicity` uses `f[i]=1`. `u_shaped_periodicity` uses the pre-specified cosine formula in `config/monte_carlo_v0_1.yaml`, numerically normalized so `mean(f^2)=1`.

Latent log variance follows

`x[t]=omega+0.35*x[t-1]+0.30*mean(x[t-5:t-1])+0.30*mean(x[t-22:t-1])+0.25*eta[t]`,

with `omega=0.05*log(1e-4)`, `eta[t]~N(0,1)`, `V[t]=exp(x[t])`, and

`r[t,i]=sqrt(V[t]/78)*f[i]*z[t,i]`, `z[t,i]~N(0,1)`.

The mechanism study uses 500 burn-in days, 3,000 usable days, 200 paired replications per scenario, and the same latent and intraday innovations within every scenario pair. The last 500 origins with all h=22 outcomes available are common to all models and horizons. Child seeds come from `numpy.random.SeedSequence(20250107342)`. Windows use `spawn`, at most four processes, and deterministic result sorting independent of worker count. No oracle factor enters a headline forecasting model.

## Non-claims

Synthetic results establish only how this implementation behaves under the two frozen artificial mechanisms. They are not empirical market evidence, SPY evidence, trading evidence, profitability evidence, or an exact reproduction of the paper's Monte Carlo design.
