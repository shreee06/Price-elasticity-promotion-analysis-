# Test protocol (step 3) — fixed before any model or metric is run on weeks 94-101

All quantities are **associations**; nothing here is read as the effect of changing a price.

## What is frozen
- Train estimates come from commit `687875d` ("Elasticity estimation on train weeks"), weeks 8-85 only:
  - Product level: the primary PPML coefficient on log price paid (`evals/results/elasticity_train.json`,
    sha256 `1edefbfea88a8bf5019255bd0890db031ed998f43f46240d06ddd4fa882f1b47`), value -1.2535226959420256, applied to
    the 5,755 products of the train primary set.
  - Commodity level: the empirical-Bayes shrunk per-commodity elasticities for the 248 commodities
    (`evals/results/commodity_elasticities_train.csv`, sha256 `9a08a775a7afed0620b3ea9656eedd513d707fd4061d2516ea9176979aa4f82f`),
    with the fixed price-index weights (unit shares over weeks 2-85).
- The pipeline re-derives these from the train weeks and asserts that they equal the committed files; nothing is re-fitted
  with validation or test data. The product set and commodity set are the train ones.
- No coefficient, rule, threshold or setting is changed after test numbers are seen.

## Out-of-sample prediction task
For each product (and separately each commodity) and each week t in the evaluation window with the product observed in
both t-1 and t (consecutive calendar weeks):
- actual change `dY = log units_t - log units_{t-1}`;
- predicted change `dP = beta * (log p_t - log p_{t-1})`, with `p` = price paid (commodity: fixed-weight index) and `beta`
  the frozen elasticity (one value for all products; commodity-specific for commodities).
- **Common weekly shock removed**: in each week, subtract the cross-product mean of `dY` from `dY`, and the mean of `dP`
  from `dP`, taken over all product-weeks with a defined change in that week. Everything below uses these relative changes.
- Baselines: (1) zero relative change; (2) last week's relative actual change repeats. Comparisons are made on the
  **common sample** where baseline 2 is defined (the product is observed in t-2, t-1 and t). The lagged weeks before the
  window start (train weeks for validation, validation weeks for test) are used only as starting points.
- Metrics, each with a pairs cluster-bootstrap 95% CI (clusters = products, or commodities; 500 resamples; seed 20240601;
  numpy only, no worker processes):
  1. Pearson correlation of predicted vs actual relative change (baseline 1 has none);
  2. MAE of the relative log-change, model vs each baseline, and the MAE difference (baseline minus model; positive = model better);
  3. share of product-weeks with the predicted direction right (sign of prediction vs sign of actual; rows with a zero
     actual or a zero prediction excluded; baseline 1 has no direction).
- Reported separately for product-weeks with a promotional discount change above 10% (|depth_t - depth_{t-1}| > 0.10,
  depth = 1 - sales_value/shelf_value) and for the rest, and for all together.
- If the frozen elasticities do not beat the baselines, that is reported as found.

## Schedule
1. Validation weeks 86-93: run the task (`evals/results/oos_validation.json`). 
2. Dry run of the final script on the validation weeks must reproduce those numbers exactly.
3. Test weeks 94-101 are evaluated **once** by `scripts/run_test_final.py --i-am-done-tuning`; the script writes a run record
   and refuses a second run. It reports the prediction metrics above and re-estimates the primary coefficients (PPML and OLS
   log price, same product set) on the 8 test weeks, compared with the train estimate by the stability rule fixed in
   `docs/analysis_plan.md` (same sign and overlapping 95% CIs).

## Caveats stated in advance
- Only 2,500 sampled households: units are sample counts, not store totals; weekly changes are noisy.
- About 80% of selling product-store-weeks have no promotion record, so display/mailer controls are incomplete and part of
  what the discount coefficient captures may be unrecorded advertising or merchandising; removing the controls moved the
  train PPML estimate from -1.25 to -1.80.
- The regular-price elasticity was not stable on the validation weeks; no claim is made about it.
- Observed promotions are not randomised; weekly price changes respond to demand and season.
- Estimates are conditional on a product selling that week; the data say nothing about weeks with no sales.
- Revenue, not profit: there are no cost data.
