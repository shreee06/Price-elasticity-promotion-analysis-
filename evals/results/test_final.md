# Test-week evaluation (weeks 94-101), validation alongside

Frozen estimates, evaluated once; protocol in `docs/test_protocol.md`. Nothing was changed after seeing these numbers. Associations only.

## Product level, all rows

| Metric | Validation 86-93 | Test 94-101 |
|---|---|---|
| Rows (clusters) | 19,068 (4,205) | 19,934 (4,279) |
| Correlation, frozen elasticity | 0.241 (0.216 to 0.264) | 0.294 (0.273 to 0.316) |
| Correlation, last week repeats | -0.463 (-0.475 to -0.451) | -0.453 (-0.464 to -0.442) |
| MAE, frozen elasticity | 0.669 (0.659 to 0.679) | 0.654 (0.645 to 0.663) |
| MAE, zero baseline | 0.686 (0.676 to 0.695) | 0.678 (0.669 to 0.687) |
| MAE, last-week baseline | 1.190 (1.172 to 1.208) | 1.185 (1.167 to 1.203) |
| MAE gain vs zero (positive = model better) | 0.017 (0.013 to 0.020) | 0.023 (0.020 to 0.027) |
| MAE gain vs last week (positive = model better) | 0.521 (0.510 to 0.532) | 0.531 (0.520 to 0.541) |
| Direction right, frozen elasticity | 0.550 (0.542 to 0.558) | 0.568 (0.561 to 0.575) |
| Direction right, last week repeats | 0.333 (0.327 to 0.339) | 0.353 (0.346 to 0.358) |

Subgroups (product): promo change > 10% vs no promo change

| Metric | Val, promo | Test, promo | Val, no promo | Test, no promo |
|---|---|---|---|---|
| Correlation, frozen elasticity | 0.500 (0.464 to 0.536) | 0.541 (0.514 to 0.568) | 0.008 (-0.009 to 0.025) | 0.014 (-0.005 to 0.031) |
| MAE gain vs zero (positive = model better) | 0.113 (0.097 to 0.129) | 0.121 (0.108 to 0.135) | -0.004 (-0.006 to -0.003) | -0.004 (-0.006 to -0.002) |
| MAE gain vs last week (positive = model better) | 0.633 (0.600 to 0.665) | 0.638 (0.610 to 0.666) | 0.497 (0.486 to 0.507) | 0.500 (0.490 to 0.511) |
| Direction right, frozen elasticity | 0.705 (0.688 to 0.723) | 0.714 (0.699 to 0.728) | 0.517 (0.508 to 0.524) | 0.526 (0.519 to 0.535) |

## Commodity level, all rows

| Metric | Validation 86-93 | Test 94-101 |
|---|---|---|
| Rows (clusters) | 1,895 (245) | 1,881 (246) |
| Correlation, frozen elasticity | 0.143 (0.050 to 0.231) | 0.194 (0.096 to 0.281) |
| Correlation, last week repeats | -0.417 (-0.463 to -0.371) | -0.392 (-0.433 to -0.350) |
| MAE, frozen elasticity | 0.315 (0.293 to 0.339) | 0.276 (0.254 to 0.297) |
| MAE, zero baseline | 0.318 (0.296 to 0.343) | 0.282 (0.260 to 0.304) |
| MAE, last-week baseline | 0.533 (0.492 to 0.574) | 0.486 (0.447 to 0.524) |
| MAE gain vs zero (positive = model better) | 0.003 (-0.002 to 0.008) | 0.005 (0.000 to 0.011) |
| MAE gain vs last week (positive = model better) | 0.217 (0.196 to 0.235) | 0.210 (0.191 to 0.229) |
| Direction right, frozen elasticity | 0.540 (0.516 to 0.563) | 0.531 (0.507 to 0.557) |
| Direction right, last week repeats | 0.351 (0.329 to 0.371) | 0.358 (0.339 to 0.376) |

Subgroups (commodity): promo change > 10% vs no promo change

| Metric | Val, promo | Test, promo | Val, no promo | Test, no promo |
|---|---|---|---|---|
| Correlation, frozen elasticity | 0.345 (0.217 to 0.477) | 0.408 (0.228 to 0.551) | 0.080 (-0.032 to 0.187) | 0.068 (-0.005 to 0.135) |
| MAE gain vs zero (positive = model better) | 0.044 (0.025 to 0.063) | 0.053 (0.030 to 0.079) | -0.002 (-0.007 to 0.003) | -0.003 (-0.006 to 0.000) |
| MAE gain vs last week (positive = model better) | 0.298 (0.234 to 0.367) | 0.283 (0.224 to 0.344) | 0.208 (0.187 to 0.227) | 0.197 (0.178 to 0.216) |
| Direction right, frozen elasticity | 0.673 (0.610 to 0.746) | 0.692 (0.633 to 0.752) | 0.524 (0.499 to 0.548) | 0.504 (0.478 to 0.530) |

## Primary coefficients re-estimated on the 8 test weeks (same products) vs train

| Coefficient | Train | Validation | Test | Test vs train (z) | Verdict (test) |
|---|---|---|---|---|---|
| PPML log price | -1.254 (-1.338 to -1.169) | -1.373 (-1.515 to -1.231) | -1.270 (-1.390 to -1.151) | -0.22 | stable |
| OLS log price | -0.897 (-0.932 to -0.862) | -0.861 (-0.953 to -0.768) | -0.919 (-0.992 to -0.846) | -0.53 | stable |

Run record: `evals/results/test_run_record.json`. Runtime 6.1 s; peak memory 618 MB.
