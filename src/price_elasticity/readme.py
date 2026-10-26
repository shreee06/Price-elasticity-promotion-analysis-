"""Render README.md from the committed result files, so numbers cannot drift from the runs."""
import json

from . import config as C
from .simulator import load_tables, top_reliable


def _j(n):
    return json.loads((C.RESULTS_DIR / n).read_text())


def _ci(c, d=2):
    return f"{c['estimate']:.{d}f} (95% CI {c['ci_low']:.{d}f} to {c['ci_high']:.{d}f})"


def _rob(tr, variant, est="ppml", term="lp"):
    for r in tr["robustness"]:
        if r["variant"] == variant and r["estimator"] == est and r["term"] == term and "estimate" in r:
            return r
    raise KeyError(variant)


def render():
    tr, val, oos, test = _j("elasticity_train.json"), _j("elasticity_validation_stability.json"), _j("oos_validation.json"), _j("test_final.json")
    au, eng = _j("panel_audit.json"), _j("engineering.json")
    s, B, ce = tr["sample"], tr["bootstrap"], tr["commodity_each"]
    pp, po = tr["primary"]["ppml"], tr["primary"]["ols"]
    sec = tr["secondary"]["ppml"]
    nodisp = _rob(tr, "drop_display_mailer_controls")
    miss = au["panel"]["selling_cells_without_causal_record_share"]
    pk = oos["product"]["all"]["metrics"]
    tk = test["test"]["product"]["all"]["metrics"]
    ck = test["test"]["commodity"]["all"]["metrics"]
    ptp = test["test"]["product"]["promo_change_gt_10pct"]["metrics"]
    ptn = test["test"]["product"]["no_promo_change"]["metrics"]
    w = ce["wrong_sign_and_extremes"]
    tbl = load_tables()
    ex = top_reliable(tbl, 3)
    stable_names = [r["name"] for r in val["comparison"] if r["verdict"] != "stable"]
    f = lambda m, k, d=3: f"{m[k]['est']:.{d}f} ({m[k]['ci_low']:.{d}f} to {m[k]['ci_high']:.{d}f})"
    L = []
    a = L.append
    a("# Price elasticity and promotion analysis")
    a("")
    a("How does weekly unit demand move with the price paid and with promotions, in grocery retail? This project builds a weekly "
      "price/promotion panel from the dunnhumby *The Complete Journey* transactions, estimates elasticities with fixed-effects Poisson "
      "and log-log OLS models, checks them against pre-registered robustness, stability and out-of-sample tests, and offers a "
      "promotion what-if tool. **Everything here is an association in observational data, not a causal effect.**")
    a("")
    a("## Data")
    a("")
    a("Source: dunnhumby, *The Complete Journey* (transactions of 2,500 frequent shoppers of one retailer over two years, plus product, "
      "promotion, coupon and demographic tables). The copy used is the Kaggle mirror `frtgnn/dunnhumby-the-complete-journey`, which lists "
      "the licence as **DbCL-1.0**; check dunnhumby's own terms before reuse. **The data is not included in this repository**: download it, "
      "unzip it, and set `DUNNHUMBY_RAW_DIR` (default `~/Downloads/dunnhumby-raw`). The repo ships code and aggregate results only.")
    a("")
    a(f"Panel built in step 1 (`docs/panel_audit.md`): {au['source']['rows']:,} transaction rows, {au['source']['households']:,} households, "
      f"{au['panel']['products']:,} products, {au['panel']['commodities']} commodities, {au['source']['weeks']} weeks; panel totals reconcile exactly to the "
      f"source rows. Fuel, coupon and placeholder items are flagged and excluded from analysis. Weeks are split into train (1-85), validation (86-93) "
      f"and test (94-101); the test weeks were evaluated once.")
    a("")
    a("## Method and pre-registration")
    a("")
    a("- `docs/analysis_plan.md` (committed before any model was fitted) fixes the price variable, sample, estimators, robustness list and stability rule.")
    a("- `docs/test_protocol.md` (committed before any test-week row was read) freezes the train estimates and the out-of-sample task.")
    a("- Price = unit price paid after the loyalty discount, before the manufacturer coupon. Poisson pseudo-maximum-likelihood with product and week "
      "fixed effects, standard errors clustered by product, plus a 500-resample cluster bootstrap; log-log OLS as a cross-check.")
    a("- Commodity level: fixed-weight price index (so pack-size mix shifts do not look like price changes), per-commodity Poisson fits, empirical-Bayes shrinkage.")
    a("")
    a("## Results (train weeks 8-85)")
    a("")
    a(f"Primary sample: {s['primary_products']:,} products, {s['primary_rows']:,} product-weeks, with at least 30 active weeks and enough promotion variation.")
    a("")
    a("| Estimator | Elasticity of units to price paid | Bootstrap 95% CI |")
    a("|---|---|---|")
    a(f"| Poisson (PPML) | {_ci(pp)} | {B['primary_ppml']['terms']['lp']['lo']:.2f} to {B['primary_ppml']['terms']['lp']['hi']:.2f} |")
    a(f"| Log-log OLS | {_ci(po)} | {B['primary_ols']['terms']['lp']['lo']:.2f} to {B['primary_ols']['terms']['lp']['hi']:.2f} |")
    a("")
    a(f"A 1% lower price paid goes with roughly {abs(po['estimate']):.1f}% to {abs(pp['estimate']):.1f}% more units, depending on the estimator.")
    a("")
    a(f"Splitting price into regular (shelf) price and promotional discount (PPML): regular price {_ci(sec['x_base'])}, "
      f"promotional discount {_ci(sec['x_promo'])}. Units look more sensitive to promotional discounts than to regular price changes, "
      f"but the regular-price coefficient was not stable on the validation weeks (see below), so nothing is claimed about it.")
    a("")
    a(f"Commodity level ({ce['commodities_fitted']} commodities): pooled PPML {_ci(tr['commodity_pooled']['ppml'])}; per-commodity median "
      f"{ce['shrunk']['median']:.2f} after shrinkage ({ce['unshrunk']['median']:.2f} unshrunk). {w['positive_point_estimates']} commodities have a positive "
      f"point estimate ({w['positive_and_significant']} with an interval above 0), reported as found and not adjusted. "
      f"Per-commodity results by department are in `evals/results/elasticity_train.md`.")
    a("")
    a("## Robustness (PPML, primary term)")
    a("")
    a("| Variant | Estimate (SE) | Change vs primary |")
    a("|---|---|---|")
    a(f"| Primary | {pp['estimate']:.3f} ({pp['se']:.3f}) | |")
    for v, nm in [("include_startup_weeks_2_7", "Include start-up weeks 2-7"), ("drop_display_mailer_controls", "Drop display and mailer controls"),
                  ("winsorise_units_p99", "Winsorise units at p99"), ("drop_top1pct_volume_products", "Drop top 1% volume products"),
                  ("drop_low_household_weeks", "Drop low-household weeks")]:
        r = _rob(tr, v)
        a(f"| {nm} | {r['estimate']:.3f} ({r['se']:.3f}) | {r['change']:+.3f} |")
    pl = [r for r in tr["robustness"] if r["variant"] == "placebo_leads" and r["estimator"] == "ppml" and r["term"].startswith("lead")]
    a(f"| Placebo: future price, lead 1 / lead 2 | {pl[0]['estimate']:.3f} ({pl[0]['se']:.3f}) / {pl[1]['estimate']:.3f} ({pl[1]['se']:.3f}) | expected near 0 |")
    a("")
    a(f"## Stability across time ({val['n_stable']} of {val['n_total']} coefficients stable)")
    a("")
    pv = next(r for r in val["comparison"] if r["name"] == "PPML log price")
    bv = next(r for r in val["comparison"] if r["name"] == "PPML x_base")
    xv = next(r for r in val["comparison"] if r["name"] == "PPML x_promo")
    a(f"Re-estimating on validation weeks 86-93 alone (rule fixed in advance: same sign and overlapping 95% CIs): primary log price {pv['val']:.2f} vs {pv['train']:.2f} on train; "
      f"promotional discount {xv['val']:.2f} vs {xv['train']:.2f}; regular price {bv['val']:.2f} vs {bv['train']:.2f} (interval {bv['val_lo']:.2f} to {bv['val_hi']:.2f}). "
      f"Not stable: {', '.join(stable_names)}.")
    a("")
    a("## Out-of-sample check and one-time test evaluation")
    a("")
    a("Task: predict each product's (and commodity's) week-over-week change in log units from its change in log price paid, using the frozen train elasticities, "
      "after removing the common weekly change (cross-product mean subtracted from actual and predicted). Baselines: no relative change; last week's relative change repeats.")
    a("")
    a("| Product level | Validation 86-93 | Test 94-101 |")
    a("|---|---|---|")
    for k, n in [("corr_model", "Correlation, predicted vs actual"), ("mae_gain_vs_zero", "MAE gain vs zero baseline"),
                 ("mae_gain_vs_last_week", "MAE gain vs last-week baseline"), ("dir_model", "Direction right")]:
        a(f"| {n} | {f(pk, k)} | {f(tk, k)} |")
    a("")
    a(f"Commodity level on the test weeks: correlation {f(ck, 'corr_model')}, MAE gain vs zero {f(ck, 'mae_gain_vs_zero')}. "
      f"The gain is concentrated in product-weeks with a promotional discount change above 10% (test correlation {f(ptp, 'corr_model')}, MAE gain vs zero {f(ptp, 'mae_gain_vs_zero')}); "
      f"in the other weeks the correlation is {f(ptn, 'corr_model')} and the MAE gain vs zero is {f(ptn, 'mae_gain_vs_zero')}, i.e. no better than predicting no relative change. "
      f"The last-week-repeats baseline is much worse than predicting zero because weekly changes mean-revert.")
    a("")
    st = test["stability_test"]["comparison"]
    a("Primary coefficients re-estimated on the 8 test weeks: " + "; ".join(f"{r['name']} {r['window']:.2f} vs {r['train']:.2f} on train ({r['verdict']})" for r in st) + ". "
      "Nothing was changed after the test numbers were seen (`evals/results/test_run_record.json`).")
    a("")
    a("## Promotion what-if simulator")
    a("")
    a("For a commodity (anonymised label) and a discount depth inside its observed 5th-95th percentile range, the simulator returns the predicted change in units "
      "(depth d, elasticity e: units x (1-d)^e) and in revenue ((1-d)^(1+e)) relative to no discount, with an interval from the commodity's shrunk 95% elasticity interval. "
      "Commodities with a non-negative elasticity or an interval including 0 are flagged *not reliable* and not ranked. Revenue only: there are no cost or margin data. Example at 20% depth for the most reliable commodities:")
    a("")
    a("| Commodity | Department | Elasticity | Units | Revenue |")
    a("|---|---|---|---|---|")
    for r in ex:
        a(f"| {r['label']} | {r['department']} | {r['elasticity']:.2f} | {r['units_change_pct']:+.1f}% ({r['units_change_pct_ci'][0]:+.1f} to {r['units_change_pct_ci'][1]:+.1f}) | "
          f"{r['revenue_change_pct']:+.1f}% ({r['revenue_change_pct_ci'][0]:+.1f} to {r['revenue_change_pct_ci'][1]:+.1f}) |")
    a("")
    a("## App")
    a("")
    a("`streamlit run app/streamlit_app.py` opens a Results page (estimates, department chart, robustness, stability, out-of-sample and test results) and a What-if page. "
      "Both read only the committed files in `evals/results/`; no data is needed.")
    a("")
    a("## Limitations")
    a("")
    a("- Observational data: prices and promotions respond to demand and season and are not randomised. No causal claim is made.")
    a(f"- About {100*miss:.1f}% of selling product-store-weeks have no promotion record, so display and mailer controls are incomplete. They matter: dropping them moves the primary PPML estimate from {pp['estimate']:.2f} to {nodisp['estimate']:.2f}. Part of the promotional-discount coefficient may reflect unrecorded advertising or merchandising, so its magnitude may be overstated.")
    a("- The regular-price coefficient was not stable across time and should not be interpreted.")
    a(f"- Commodity-level estimates are noisy: {w['positive_point_estimates']} of {ce['commodities_fitted']} are positive.")
    a("- Only 2,500 sampled households of one retailer: units are sample counts, not store totals. Grocery, not fashion; findings do not transfer to apparel.")
    a("- Estimates are conditional on a product selling that week; weeks without sales are missing, not zero.")
    a("- Revenue, not profit: there are no cost data.")
    a("")
    a("## Engineering")
    a("")
    a("| Stage | Runtime (s) | Peak memory (MB) |")
    a("|---|---|---|")
    a(f"| Panel audit | | {eng['panel_audit']['peak_memory_mb']} |")
    a(f"| Elasticity estimation, train (incl. 500-resample bootstraps) | {eng['elasticity_train']['runtime_seconds']} | {eng['elasticity_train']['peak_memory_mb_parent']} (main process) |")
    a(f"| Validation stability | {eng['validation_stability']['runtime_seconds']} | {eng['validation_stability']['peak_memory_mb']} |")
    a(f"| Out-of-sample, validation | {eng['oos_validation']['runtime_seconds']} | {eng['oos_validation']['peak_memory_mb']} |")
    a(f"| Test evaluation | {eng['test_final']['runtime_seconds']} | {eng['test_final']['peak_memory_mb']} |")
    a("")
    a(f"{eng['note']} All scripts run a 1 GB available-memory watchdog. The suite has {eng['test_functions']} test functions (synthetic data only).")
    a("")
    a("## Reproduce")
    a("")
    a("```bash")
    a("python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
    a("export PYTHONPATH=src DUNNHUMBY_RAW_DIR=/path/to/dunnhumby-raw")
    a("python scripts/convert_raw.py && python scripts/build_panel.py && python scripts/audit_panel.py")
    a("python scripts/run_elasticity.py && python scripts/run_validation.py        # train estimates, validation stability")
    a("python scripts/freeze_estimates.py && python scripts/run_oos_validation.py   # frozen estimates, out-of-sample check")
    a("python scripts/run_test_final.py --dry-run-on-validation                      # must reproduce the validation numbers")
    a("python scripts/run_test_final.py --i-am-done-tuning                           # once only")
    a("python scripts/collect_engineering.py && python scripts/make_readme.py")
    a("python -m pytest")
    a("```")
    a("")
    a("## Licence")
    a("")
    a("Code: MIT (see `LICENSE`). The dunnhumby data is not covered by this licence and is not distributed here.")
    return "\n".join(L) + "\n"
