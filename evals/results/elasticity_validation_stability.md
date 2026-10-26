# Temporal stability on VALIDATION weeks 86-93

Specified in `docs/analysis_plan.md`. Same product set and specifications as the train estimates, no re-tuning, validation weeks alone. Rule fixed in advance: **stable** = same sign and the 95% CIs overlap. Associations only.

Validation sample: 30,276 product-weeks, 5,458 products, 8 weeks.

| Coefficient | Train | Validation | Difference | z of difference | Verdict |
|---|---|---|---|---|---|
| PPML log price | -1.254 (-1.338 to -1.169) | -1.373 (-1.515 to -1.231) | -0.120 | -1.42 | stable |
| PPML x_base | -0.743 (-0.876 to -0.611) | -0.138 (-0.326 to 0.049) | +0.605 | +5.16 | not stable |
| PPML x_promo | -1.393 (-1.474 to -1.311) | -1.590 (-1.732 to -1.448) | -0.198 | -2.37 | stable |
| PPML any_display | 0.364 (0.321 to 0.408) | 0.367 (0.306 to 0.427) | +0.002 | +0.06 | stable |
| PPML any_mailer | 0.279 (0.164 to 0.393) | 0.044 (-0.103 to 0.190) | -0.235 | -2.48 | stable |
| PPML share_stores_display | 0.076 (-0.014 to 0.167) | -0.106 (-0.234 to 0.023) | -0.182 | -2.26 | not stable |
| PPML share_stores_mailer | 0.112 (0.009 to 0.215) | 0.268 (0.110 to 0.425) | +0.156 | +1.62 | stable |
| PPML share_units_coupon | 0.174 (0.051 to 0.297) | 0.027 (-0.076 to 0.131) | -0.147 | -1.79 | stable |
| OLS log price | -0.897 (-0.932 to -0.862) | -0.861 (-0.953 to -0.768) | +0.037 | +0.72 | stable |
| OLS x_base | -0.452 (-0.512 to -0.391) | 0.026 (-0.088 to 0.140) | +0.478 | +7.26 | not stable |
| OLS x_promo | -1.016 (-1.045 to -0.987) | -1.123 (-1.204 to -1.042) | -0.107 | -2.43 | stable |
| OLS any_display | 0.861 (0.834 to 0.887) | 0.812 (0.762 to 0.862) | -0.049 | -1.68 | stable |
| OLS any_mailer | 0.669 (0.536 to 0.803) | 0.462 (0.244 to 0.679) | -0.207 | -1.59 | stable |
| OLS share_stores_display | -0.791 (-0.837 to -0.745) | -0.859 (-0.949 to -0.768) | -0.068 | -1.30 | stable |
| OLS share_stores_mailer | -0.400 (-0.534 to -0.265) | -0.211 (-0.430 to 0.008) | +0.188 | +1.44 | stable |
| OLS share_units_coupon | 0.022 (-0.004 to 0.048) | 0.072 (-0.008 to 0.152) | +0.050 | +1.16 | stable |
| commodity-pooled PPML log price index | -0.608 (-0.810 to -0.406) | -0.139 (-0.335 to 0.057) | +0.469 | +3.26 | not stable |
| commodity-pooled OLS log price index | -0.286 (-0.395 to -0.177) | -0.144 (-0.276 to -0.012) | +0.142 | +1.64 | stable |

14 of 18 compared coefficients are stable by the rule above.

Runtime 2.8 s; peak memory 815 MB.
