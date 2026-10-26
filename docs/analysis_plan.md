# Analysis plan (step 2) — fixed before any model is fitted

Written after the step-1 data audit (`docs/panel_audit.md`) and before any elasticity model has been run. Choices rest on
the audit (panel structure, sample sizes, promotion frequency), not on any estimated coefficient. All estimates are
**associations in observational data**; no estimate is read as the effect of changing a price.

## Data discipline
- Estimation uses weeks **8-85 only** (primary) or 2-85 (start-up sensitivity). The panel is read with a week filter so
  validation (86-93) and test (94-101) rows are never loaded during train estimation; this is asserted in code.
- Validation weeks are used once, for the stability check below. **Test weeks are not touched in this step.**
- Every fitted specification, kept or dropped, is appended to `evals/results/spec_log.csv` (spec, sample, term,
  estimate, SE, CI). No product ids or names appear in any output; per-commodity results use anonymised labels.
- Engine: `pyfixest` 0.60.0 (installed cleanly on Python 3.10 with unchanged pandas/numpy/scipy) for fixed-effects Poisson
  (`fepois`) and OLS (`feols`); `statsmodels` for per-commodity Poisson models.

## Variables
- `units` = sum of QUANTITY over the product-week (sample units from 2,500 households).
- **Primary price** `p = sales_value / units` (unit-weighted average price paid after the loyalty discount and coupon
  match, before the manufacturer coupon); regressor `log p`.
- **Secondary split** (exact decomposition `log p = x_base + x_promo`):
  `x_base = log(shelf_value / units)` (shelf/base price), `x_promo = log(sales_value / shelf_value) = log(1 - d)`, where
  `d = 1 - sales_value/shelf_value` is the observed loyalty-discount depth (no clipping, so the decomposition is exact).
- Controls: product FE, week FE, `any_display`, `any_mailer`, `share_stores_display`, `share_stores_mailer`,
  `share_units_coupon`. Display/mailer flags are measured only where the causal table has a record for a selling store
  (about 20% of selling product-store-weeks), so their coefficients are expected to be attenuated.
- Reference-based variants (robustness): with `depth_ref` = max-of-prior-8 or median-of-prior-13 depth from step 1,
  `x_promo = log(1 - depth_ref)` and `x_base = log p - x_promo` (= log of the larger of price and reference).

## Primary sample
Merchandise products (`non_merchandise = 0`) that, within weeks 8-85, have (i) at least **30 active weeks**, (ii) at least
**8 weeks with observed discount depth `d > 10%`** and (iii) at least **8 weeks with `d <= 10%`**. The product set is fixed
by these rules and re-used unchanged in every robustness variant and in the validation check. Only product-weeks with
positive sales exist in the panel, so every estimate is conditional on the product selling that week (weeks without sales are
missing, not zero); this is a limitation of the data, not corrected.

## Estimators (headline in bold)
1. **Poisson pseudo-maximum likelihood**: `units ~ log p + controls | product + week`, SEs clustered by product.
2. Log-log OLS cross-check: `log units ~ log p + controls | product + week`, SEs clustered by product.
The same two estimators are used for the secondary split (`x_base`, `x_promo` replace `log p`).
Headline estimates (primary PPML, primary OLS, secondary PPML, commodity-pooled PPML) also get a **pairs cluster
bootstrap**: 500 resamples of clusters with replacement, seed 20240601, percentile 95% intervals.

## Commodity level
- Commodity = `COMMODITY_DESC`; department = the department holding most of its products. Merchandise commodities with
  at least **60 active weeks** within weeks 8-85.
- **Fixed-weight price index**: `log P_ct = sum_i w_i log p_it / sum_i w_i`, summed over products sold in week t, with
  `w_i` = product i's share of the commodity's units over weeks 2-85 (fixed over time). Pack-size mix shifts then do not
  move the index. Quantity is total units of the commodity-week.
- Per-commodity Poisson (statsmodels GLM): `units_ct ~ log P_ct + share_stores_display + share_stores_mailer +
  share_units_coupon + cubic trend in week`, offset `log(active households in week)`, Newey-West (HAC, 4 lags) SEs.
- **Empirical-Bayes shrinkage**: DerSimonian-Laird random-effects estimate of the mean and between-commodity variance
  of the elasticities; shrunk estimate = mean + B_c (estimate_c - mean), B_c = tau^2 / (tau^2 + se_c^2).
  Summaries by department: counts, median, IQR, shrunk and unshrunk. Share of commodities whose 95% CI excludes 0 and
  excludes -1 (plus Benjamini-Hochberg q = 0.05 counts).
- Commodity-pooled model: `units_ct ~ log P_ct + controls | commodity + week`, clustered by commodity.

## Robustness list (fixed now; each reported next to the primary with its change)
1. Placebo leads: add `log p` at t+1 and t+2 (calendar weeks, within train; rows limited to weeks <= 83 so that no
   validation week is used). Compared with the primary re-fitted on the same rows. Lead coefficients should be near 0.
2. Include start-up weeks 2-7.
3. Drop display/mailer controls (flags and shares).
4. Reference-price discount definitions (max of prior 8 weeks; median of prior 13 weeks) in place of the observed discount.
5. Winsorise units at the 99th percentile of product-week units; separately drop the top 1% of products by train units.
6. Drop weeks whose active-household count is below the 10th percentile of weeks 8-85.

## Temporal stability (validation weeks 86-93, used for nothing else)
Re-estimate the primary PPML and OLS, the secondary split and the commodity-pooled model on the validation weeks alone, with
the same product set and no re-tuning, and compare with the train estimate (difference, and difference / sqrt(se_v^2 + se_t^2)).
Reading rule fixed now: "stable" means same sign and the validation 95% CI overlaps the train 95% CI; otherwise "not stable".
The test weeks will be used exactly once at the end of the project in the same way.

## Reporting rules
Wrong-looking results are reported as they are, with counts: positive point elasticities, estimates below -10 or above +5,
and failed fits. Nothing is trimmed from the primary results.

## Claims the data cannot support
- Profit or margin effects (no cost data).
- Causal effects: promotions and prices are not randomised and respond to demand and season.
- Fashion apparel behaviour (this is one grocery retailer).
- Store-level or market totals (only 2,500 sampled households; units are sample counts).
- Elasticities for products that never vary in price, never sell in a week (zero demand is unobserved), or lie outside the
  primary sample.
