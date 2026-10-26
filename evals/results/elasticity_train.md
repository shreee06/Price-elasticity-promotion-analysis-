# Elasticity estimates on TRAIN weeks

Specified in `docs/analysis_plan.md` before fitting. Weeks 8-85 only (validation and test weeks were not loaded). All coefficients are **associations** between weekly price and units sold in a 2,500-household sample, conditional on a product selling that week; none is the effect of changing a price. Every fitted specification is in `evals/results/spec_log.csv`.

## Sample sizes after each filter
- All products with rows in weeks 8-85: 81,965 (849,036 product-weeks)
- Merchandise products: 81,450 (846,232 product-weeks)
- At least 30 active weeks: 9,720
- Plus at least 8 weeks with discount depth > 10%: 7,185
- Plus at least 8 weeks with depth <= 10% (primary set): 5,755 products, 299,480 product-weeks over 78 weeks (54.2% of merchandise units)

## Primary: log price paid (after loyalty discount, before manufacturer coupon)
| Estimator | Coefficient on log price | Bootstrap |
|---|---|---|
| Poisson (PPML), product + week FE | -1.254 (SE 0.043; 95% CI -1.338 to -1.169) | bootstrap SE 0.042, 95% CI -1.337 to -1.179 |
| Log-log OLS, product + week FE | -0.897 (SE 0.018; 95% CI -0.932 to -0.862) | bootstrap SE 0.017, 95% CI -0.931 to -0.862 |

Bootstrap: 500/500 (PPML) and 500/500 (OLS) valid resamples of products, seed 20240601. Standard errors in the first column are clustered by product.

## Secondary: base (shelf) price vs promotional discount
`x_base` = log shelf price per unit; `x_promo` = log(1 - observed loyalty-discount depth). Their sum is log price paid.

| Estimator | x_base (regular price) | x_promo (discount) |
|---|---|---|
| PPML | -0.743 (SE 0.068; 95% CI -0.876 to -0.611) | -1.393 (SE 0.041; 95% CI -1.474 to -1.311) |
| PPML bootstrap | bootstrap SE 0.064, 95% CI -0.875 to -0.628 | bootstrap SE 0.040, 95% CI -1.470 to -1.315 |
| OLS | -0.452 (SE 0.031; 95% CI -0.512 to -0.391) | -1.016 (SE 0.015; 95% CI -1.045 to -0.987) |

## Display, mailer and coupon coefficients (primary specification)
| Term | PPML | OLS |
|---|---|---|
| any_display | 0.364 (SE 0.022; 95% CI 0.321 to 0.408) | 0.861 (SE 0.014; 95% CI 0.834 to 0.887) |
| any_mailer | 0.279 (SE 0.058; 95% CI 0.164 to 0.393) | 0.669 (SE 0.068; 95% CI 0.536 to 0.803) |
| share_stores_display | 0.076 (SE 0.046; 95% CI -0.014 to 0.167) | -0.791 (SE 0.023; 95% CI -0.837 to -0.745) |
| share_stores_mailer | 0.112 (SE 0.052; 95% CI 0.009 to 0.215) | -0.400 (SE 0.069; 95% CI -0.534 to -0.265) |
| share_units_coupon | 0.174 (SE 0.063; 95% CI 0.051 to 0.297) | 0.022 (SE 0.013; 95% CI -0.004 to 0.048) |
Display/mailer flags are only observed where the promotion table has a record for a selling store, so these coefficients are likely attenuated.

## Commodity level (fixed-weight price index)
- 248 commodities with >= 60 active weeks (19,104 commodity-weeks); 248 per-commodity fits succeeded, 0 skipped/failed.
- Pooled model (commodity + week FE, clustered by commodity), PPML: -0.608 (SE 0.103; 95% CI -0.810 to -0.406); bootstrap SE 0.102, 95% CI -0.804 to -0.405 (500/500 resamples).
- Pooled OLS: -0.286 (SE 0.055; 95% CI -0.395 to -0.177).
- Per-commodity elasticities, unshrunk: median -0.264 (IQR -0.709 to 0.021); shrunk: median -0.284 (IQR -0.560 to -0.105). Empirical-Bayes mean -0.355, between-commodity SD 0.441.
- 95% CI excludes 0 for 36.7% and excludes -1 for 62.9% of commodities (unshrunk, no multiplicity adjustment); after Benjamini-Hochberg (q = 0.05): 68 differ from 0, 143 differ from -1. Shrunk intervals exclude 0 for 37.9% and -1 for 68.1%.

| Department | n | median (unshrunk) | IQR (unshrunk) | median (shrunk) | IQR (shrunk) |
|---|---|---|---|---|---|
| GROCERY | 89 | -0.306 | -0.710 to 0.079 | -0.333 | -0.558 to -0.136 |
| DRUG GM | 65 | -0.191 | -0.463 to -0.011 | -0.224 | -0.436 to -0.045 |
| PRODUCE | 27 | -0.538 | -0.931 to -0.119 | -0.500 | -0.717 to -0.156 |
| NUTRITION | 16 | -0.794 | -1.010 to -0.205 | -0.609 | -0.816 to -0.275 |
| DELI | 12 | -0.153 | -0.246 to 0.162 | -0.212 | -0.297 to 0.043 |
| MEAT-PCKGD | 9 | -0.686 | -1.187 to -0.077 | -0.501 | -0.890 to -0.209 |
| PASTRY | 7 | -0.227 | -0.756 to 0.077 | -0.276 | -0.617 to 0.039 |
| FLORAL | 6 | -0.046 | -0.079 to 0.049 | -0.094 | -0.122 to -0.064 |
| MEAT | 6 | -0.242 | -0.524 to 0.553 | -0.256 | -0.498 to 0.071 |
| COSMETICS | 3 | -0.154 | -0.219 to -0.047 | -0.177 | -0.232 to -0.085 |
| SEAFOOD-PCKGD | 3 | -0.905 | -0.961 to -0.772 | -0.590 | -0.652 to -0.549 |
| FROZEN GROCERY | 1 | 0.030 | 0.030 to 0.030 | -0.019 | -0.019 to -0.019 |
| GARDEN CENTER | 1 | -1.139 | -1.139 to -1.139 | -0.750 | -0.750 to -0.750 |
| SALAD BAR | 1 | 0.414 | 0.414 to 0.414 | 0.202 | 0.202 to 0.202 |
| SEAFOOD | 1 | -0.133 | -0.133 to -0.133 | -0.172 | -0.172 to -0.172 |
| SPIRITS | 1 | -0.656 | -0.656 to -0.656 | -0.544 | -0.544 to -0.544 |

### Signs that look wrong (commodity level, reported as found)
- Positive point estimates: 65 of 248 (10 of them with a 95% CI above 0).
- Below -10: 0; above +5: 0; range -2.76 to 3.25; median SE 0.269.
- Per-commodity estimates (anonymised labels, no names) are in `evals/results/commodity_elasticities_train.csv`.

## Robustness (each next to the primary; change = variant minus comparator)
| Variant | Estimator | Term | Estimate (SE) | N | Comparator | Change | Note |
|---|---|---|---|---|---|---|---|
| placebo_leads | ppml | lp | -1.323 (0.055) | 175,532 | -1.340 | +0.017 | comparator = primary spec on the same rows |
| placebo_leads | ppml | lead1 | -0.018 (0.040) | 175,532 |  |  | should be ~0 |
| placebo_leads | ppml | lead2 | -0.057 (0.028) | 175,532 |  |  | should be ~0 |
| placebo_matched_baseline | ppml | lp | -1.340 (0.051) | 175,532 | -1.254 | -0.087 | primary spec on the lead-restricted rows |
| placebo_leads | ols | lp | -1.008 (0.025) | 175,532 | -1.041 | +0.033 | comparator = primary spec on the same rows |
| placebo_leads | ols | lead1 | -0.073 (0.014) | 175,532 |  |  | should be ~0 |
| placebo_leads | ols | lead2 | -0.014 (0.011) | 175,532 |  |  | should be ~0 |
| placebo_matched_baseline | ols | lp | -1.041 (0.024) | 175,532 | -0.897 | -0.144 | primary spec on the lead-restricted rows |
| include_startup_weeks_2_7 | ppml | lp | -1.250 (0.043) | 309,325 | -1.254 | +0.004 |  |
| include_startup_weeks_2_7 | ppml | x_base | -0.746 (0.065) | 309,325 | -0.743 | -0.003 |  |
| include_startup_weeks_2_7 | ppml | x_promo | -1.387 (0.041) | 309,325 | -1.393 | +0.006 |  |
| include_startup_weeks_2_7 | ols | lp | -0.886 (0.018) | 309,325 | -0.897 | +0.011 |  |
| include_startup_weeks_2_7 | ols | x_base | -0.475 (0.031) | 309,325 | -0.452 | -0.023 |  |
| include_startup_weeks_2_7 | ols | x_promo | -0.997 (0.015) | 309,325 | -1.016 | +0.019 |  |
| drop_display_mailer_controls | ppml | lp | -1.801 (0.054) | 299,480 | -1.254 | -0.548 |  |
| drop_display_mailer_controls | ppml | x_base | -0.990 (0.074) | 299,480 | -0.743 | -0.247 |  |
| drop_display_mailer_controls | ppml | x_promo | -1.960 (0.052) | 299,480 | -1.393 | -0.568 |  |
| drop_display_mailer_controls | ols | lp | -1.280 (0.021) | 299,480 | -0.897 | -0.383 |  |
| drop_display_mailer_controls | ols | x_base | -0.616 (0.036) | 299,480 | -0.452 | -0.165 |  |
| drop_display_mailer_controls | ols | x_promo | -1.417 (0.018) | 299,480 | -1.016 | -0.400 |  |
| ref_max8 | ppml | x_base_r | -1.406 (0.045) | 252,704 | -0.756 | -0.650 | comparator = observed split on the same rows |
| ref_max8 | ppml | x_promo_r | -0.645 (0.064) | 252,704 | -1.427 | +0.782 | comparator = observed split on the same rows |
| ref_max8_matched_baseline | ppml | x_base | -0.756 (0.067) | 252,704 | -0.743 | -0.013 | observed split on reference-available rows |
| ref_max8_matched_baseline | ppml | x_promo | -1.427 (0.044) | 252,704 | -1.393 | -0.034 | observed split on reference-available rows |
| ref_max8 | ols | x_base_r | -1.055 (0.017) | 252,704 | -0.462 | -0.593 | comparator = observed split on the same rows |
| ref_max8 | ols | x_promo_r | -0.428 (0.033) | 252,704 | -1.097 | +0.669 | comparator = observed split on the same rows |
| ref_max8_matched_baseline | ols | x_base | -0.462 (0.035) | 252,704 | -0.452 | -0.010 | observed split on reference-available rows |
| ref_max8_matched_baseline | ols | x_promo | -1.097 (0.017) | 252,704 | -1.016 | -0.080 | observed split on reference-available rows |
| ref_med13 | ppml | x_base_r | -1.407 (0.045) | 252,442 | -0.756 | -0.651 | comparator = observed split on the same rows |
| ref_med13 | ppml | x_promo_r | -0.423 (0.072) | 252,442 | -1.431 | +1.008 | comparator = observed split on the same rows |
| ref_med13_matched_baseline | ppml | x_base | -0.756 (0.073) | 252,442 | -0.743 | -0.013 | observed split on reference-available rows |
| ref_med13_matched_baseline | ppml | x_promo | -1.431 (0.044) | 252,442 | -1.393 | -0.039 | observed split on reference-available rows |
| ref_med13 | ols | x_base_r | -1.050 (0.017) | 252,442 | -0.446 | -0.604 | comparator = observed split on the same rows |
| ref_med13 | ols | x_promo_r | -0.249 (0.045) | 252,442 | -1.102 | +0.852 | comparator = observed split on the same rows |
| ref_med13_matched_baseline | ols | x_base | -0.446 (0.035) | 252,442 | -0.452 | +0.006 | observed split on reference-available rows |
| ref_med13_matched_baseline | ols | x_promo | -1.102 (0.016) | 252,442 | -1.016 | -0.085 | observed split on reference-available rows |
| winsorise_units_p99 | ppml | lp | -1.031 (0.028) | 299,480 | -1.254 | +0.223 |  |
| winsorise_units_p99 | ppml | x_base | -0.579 (0.042) | 299,480 | -0.743 | +0.164 |  |
| winsorise_units_p99 | ppml | x_promo | -1.156 (0.027) | 299,480 | -1.393 | +0.237 |  |
| winsorise_units_p99 | ols | lp | -0.876 (0.017) | 299,480 | -0.897 | +0.022 |  |
| winsorise_units_p99 | ols | x_base | -0.440 (0.030) | 299,480 | -0.452 | +0.012 |  |
| winsorise_units_p99 | ols | x_promo | -0.992 (0.014) | 299,480 | -1.016 | +0.024 |  |
| drop_top1pct_volume_products | ppml | lp | -1.150 (0.029) | 295,002 | -1.254 | +0.104 |  |
| drop_top1pct_volume_products | ppml | x_base | -0.588 (0.047) | 295,002 | -0.743 | +0.156 |  |
| drop_top1pct_volume_products | ppml | x_promo | -1.305 (0.026) | 295,002 | -1.393 | +0.088 |  |
| drop_top1pct_volume_products | ols | lp | -0.881 (0.018) | 295,002 | -0.897 | +0.016 |  |
| drop_top1pct_volume_products | ols | x_base | -0.429 (0.030) | 295,002 | -0.452 | +0.023 |  |
| drop_top1pct_volume_products | ols | x_promo | -1.001 (0.015) | 295,002 | -1.016 | +0.015 |  |
| drop_low_household_weeks | ppml | lp | -1.287 (0.044) | 275,853 | -1.254 | -0.033 |  |
| drop_low_household_weeks | ppml | x_base | -0.686 (0.070) | 275,853 | -0.743 | +0.057 |  |
| drop_low_household_weeks | ppml | x_promo | -1.443 (0.043) | 275,853 | -1.393 | -0.051 |  |
| drop_low_household_weeks | ols | lp | -0.921 (0.018) | 275,853 | -0.897 | -0.024 |  |
| drop_low_household_weeks | ols | x_base | -0.381 (0.031) | 275,853 | -0.452 | +0.070 |  |
| drop_low_household_weeks | ols | x_promo | -1.059 (0.015) | 275,853 | -1.016 | -0.043 |  |

Details: units capped at 44.0; 58 top-volume products dropped; 8 weeks below 1230 active households dropped; placebo rows 175,543 (weeks 8-83).

## Reading notes (no new numbers)
- `any_*` flags and `share_stores_*` are strongly related, so their individual coefficients (especially in OLS, where they have opposite signs) should be read together, not one by one.
- The reference-price variants define `x_base_r` as the log of the larger of price and reference and `x_promo_r` as the log of price relative to the reference (zero when price is at or above it), so they are not like-for-like with the observed split; the matched-baseline rows show the observed split on the same rows.
- Placebo: lead coefficients are expected to be near 0; any non-zero lead is evidence that price paths are persistent or anticipate demand, which would also affect the main coefficient.
- Estimates are conditional on the product selling that week (weeks without sales are missing, not zero).

Runtime 2076.3 s; peak memory 2043 MB (parent process; bootstrap workers run separately).
