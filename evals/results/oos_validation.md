# Out-of-sample check on VALIDATION weeks 86-93

Frozen train elasticities (weeks 8-85) predict week-over-week relative changes in log units from relative changes in log price paid. Compared with a zero-change baseline and a last-week-repeats baseline.

Weeks 86-93. Frozen product elasticity -1.254. relative change = week-over-week log change minus the cross-product mean of that week; common sample where last week's relative change is defined; promo change = |depth_t - depth_{t-1}| > 0.10. Cluster bootstrap: 500 resamples, seed 20240601, no worker processes. Associations only.

## Product level
Rows with a defined change: 23,322; common sample: 19,068.

| Metric | All | Promo change > 10% | No promo change |
|---|---|---|---|
| Rows (clusters) | 19,068 (4,205) | 3,400 (1,822) | 15,668 (4,047) |
| Correlation, frozen elasticity | 0.241 (0.216 to 0.264) | 0.500 (0.464 to 0.536) | 0.008 (-0.009 to 0.025) |
| Correlation, last week repeats | -0.463 (-0.475 to -0.451) | -0.483 (-0.509 to -0.456) | -0.459 (-0.472 to -0.446) |
| MAE, frozen elasticity | 0.669 (0.659 to 0.679) | 0.771 (0.746 to 0.795) | 0.647 (0.637 to 0.657) |
| MAE, zero baseline | 0.686 (0.676 to 0.695) | 0.885 (0.853 to 0.911) | 0.642 (0.633 to 0.652) |
| MAE, last-week baseline | 1.190 (1.172 to 1.208) | 1.404 (1.353 to 1.446) | 1.144 (1.125 to 1.161) |
| MAE gain vs zero (positive = model better) | 0.017 (0.013 to 0.020) | 0.113 (0.097 to 0.129) | -0.004 (-0.006 to -0.003) |
| MAE gain vs last week (positive = model better) | 0.521 (0.510 to 0.532) | 0.633 (0.600 to 0.665) | 0.497 (0.486 to 0.507) |
| Direction right, frozen elasticity | 0.550 (0.542 to 0.558) | 0.705 (0.688 to 0.723) | 0.517 (0.508 to 0.524) |
| Direction right, last week repeats | 0.333 (0.327 to 0.339) | 0.335 (0.319 to 0.352) | 0.333 (0.326 to 0.340) |

## Commodity level
Rows with a defined change: 1,911; common sample: 1,895.

| Metric | All | Promo change > 10% | No promo change |
|---|---|---|---|
| Rows (clusters) | 1,895 (245) | 202 (91) | 1,693 (245) |
| Correlation, frozen elasticity | 0.143 (0.050 to 0.231) | 0.345 (0.217 to 0.477) | 0.080 (-0.032 to 0.187) |
| Correlation, last week repeats | -0.417 (-0.463 to -0.371) | -0.515 (-0.634 to -0.363) | -0.398 (-0.451 to -0.342) |
| MAE, frozen elasticity | 0.315 (0.293 to 0.339) | 0.411 (0.336 to 0.505) | 0.304 (0.281 to 0.329) |
| MAE, zero baseline | 0.318 (0.296 to 0.343) | 0.455 (0.383 to 0.540) | 0.302 (0.279 to 0.325) |
| MAE, last-week baseline | 0.533 (0.492 to 0.574) | 0.709 (0.581 to 0.858) | 0.512 (0.472 to 0.550) |
| MAE gain vs zero (positive = model better) | 0.003 (-0.002 to 0.008) | 0.044 (0.025 to 0.063) | -0.002 (-0.007 to 0.003) |
| MAE gain vs last week (positive = model better) | 0.217 (0.196 to 0.235) | 0.298 (0.234 to 0.367) | 0.208 (0.187 to 0.227) |
| Direction right, frozen elasticity | 0.540 (0.516 to 0.563) | 0.673 (0.610 to 0.746) | 0.524 (0.499 to 0.548) |
| Direction right, last week repeats | 0.351 (0.329 to 0.371) | 0.332 (0.268 to 0.405) | 0.353 (0.330 to 0.376) |
