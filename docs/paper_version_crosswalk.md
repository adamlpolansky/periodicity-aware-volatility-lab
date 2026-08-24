# Working-paper/final-paper crosswalk

The implementation uses the 15 January 2021 working paper and the final *Journal of Banking & Finance* article (170, 2025, 107342). Local reference copies remain ignored and are not part of the public surface.

| Topic | Working paper | Final paper | Public v0.2 treatment |
|---|---|---|---|
| RV and BV | Sec. 2, equation (2), PDF p. 6 | Sec. 2, equation (2), PDF p. 2 | RV and literal-`1.57` BV implemented exactly at 78 intraday returns |
| Multiplicative periodicity and normalization | Equations (3a), (3b), and (4), PDF pp. 6-7 | Equations (3)-(4), PDF pp. 2-3 | `Delta*sum(f^2)=1` is a tested invariant |
| WSD factor and filtered returns | Equations (5)-(6), PDF p. 7; Appendix B.1, PDF p. 47 | Equations (5)-(6), PDF p. 3; Appendix B.1, PDF p. 16 | WSD, shortest-half weights, filtered returns, and filtered RV implemented; no jump extensions |
| HAR/HARP regressions | Equations (7)-(8), PDF p. 8 | Equations (7)-(8), PDF p. 3 | Direct HAR/HARP with unfiltered target and filtered right-sided HARP predictors |
| Forecast losses | Equation (20), PDF p. 17 | Equations (20)-(21), PDF p. 5 | MSE and QLIKE; pre-specified positive-forecast handling is explicit |
| Forecast horizons | PDF pp. 8 and 17 | PDF pp. 3, 5, and Tables 3-6 on pp. 9-11 | Separate direct models for 1, 5, and 22 days |
| Daily model refit and rolling regression window | PDF pp. 17 and 21; 1,000 days for empirical OOS on p. 21 | Sec. 4.1 and Sec. 4.3.2, PDF pp. 6 and 10 | Exactly 1,000 fully known rows and daily refit |
| Periodicity estimation window | Causal robustness from 22 through 1,008 days, PDF p. 24 and Table 7, PDF p. 43 | Main previous-20-day rule, PDF pp. 6 and 10-11; alternatives 40/125/250/500/1,000, PDF pp. 7 and 11 | Exactly 1,008 previous days is a frozen project extension grounded in the working-paper robustness window, not the final-paper main rule |
| DM sign | Equation (21) and discussion, PDF pp. 21-22 | Equation (22) and discussion, PDF pp. 5 and 10-11 | `d=L_HARP-L_HAR`; negative favors HARP |
| Intraday source construction | Tick data, previous-tick interpolation, 5-minute sampling, PDF p. 10 | Tick data, previous-tick interpolation, 5-minute sampling, PDF p. 6 | Public adapter is source-agnostic; synthetic tests use within-session endpoints and never claim tick equivalence |
| Paper Monte Carlo | SV1F/SV2F mechanisms, working-paper Secs. 3.2 and 5.1 | Final-paper Secs. 3.2 and 4.2 | Not reproduced; public study is a separately frozen two-scenario mechanism check |

## Indexing translation

Paper equations (7)-(8) write lagged predictors relative to a target interval beginning on day `t`. The public implementation names the last known predictor day the forecast origin `o` and defines its target as days `o+1` through `o+h`. This is an explicit index translation, not a different information set. A historical row `s` enters the origin-`o` fit only if its complete target ends by `o`, i.e. `s+h <= o`.

## Deliberate differences from the papers

- The 1,008-day causal WSD window is a pre-specified robustness-based extension, not the final paper's 20-day headline rule.
- The synthetic DGP is the user-frozen mechanism study, not the papers' SV1F/SV2F Monte Carlo.
- The DM HAC bandwidth and HLN correction are pre-specified here and are not represented as author-exact choices.
- Jumps, HAR-J, HAR-CJ, HAR-Q, VRP, return predictability, and trading applications are out of scope.
