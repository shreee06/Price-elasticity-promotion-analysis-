"""Markdown renderers for the elasticity result files (numbers come straight from the JSON)."""


def ci(c):
    return f"{c['estimate']:.3f} (SE {c['se']:.3f}; 95% CI {c['ci_low']:.3f} to {c['ci_high']:.3f})"


def bci(b):
    return f"bootstrap SE {b['boot_se']:.3f}, 95% CI {b['lo']:.3f} to {b['hi']:.3f}"


def render_train(R):
    s, B = R["sample"], R["bootstrap"]
    L = ["# Elasticity estimates on TRAIN weeks", "",
         "Specified in `docs/analysis_plan.md` before fitting. Weeks 8-85 only (validation and test weeks were not loaded). "
         "All coefficients are **associations** between weekly price and units sold in a 2,500-household sample, conditional on a "
         "product selling that week; none is the effect of changing a price. Every fitted specification is in `evals/results/spec_log.csv`.", "",
         "## Sample sizes after each filter",
         f"- All products with rows in weeks 8-85: {s['all_products_with_rows_weeks_8_85']:,} ({s['all_product_weeks']:,} product-weeks)",
         f"- Merchandise products: {s['merchandise_products_with_rows_in_window']:,} ({s['merchandise_product_weeks_in_window']:,} product-weeks)",
         f"- At least 30 active weeks: {s['products_ge_30_active_weeks']:,}",
         f"- Plus at least 8 weeks with discount depth > 10%: {s['plus_ge_8_weeks_depth_gt_10pct']:,}",
         f"- Plus at least 8 weeks with depth <= 10% (primary set): {s['plus_ge_8_weeks_depth_le_10pct (primary set)']:,} products, "
         f"{s['primary_rows']:,} product-weeks over {s['primary_weeks']} weeks ({100*s['primary_share_of_merch_units']:.1f}% of merchandise units)", "",
         "## Primary: log price paid (after loyalty discount, before manufacturer coupon)",
         "| Estimator | Coefficient on log price | Bootstrap |", "|---|---|---|",
         f"| Poisson (PPML), product + week FE | {ci(R['primary']['ppml'])} | {bci(B['primary_ppml']['terms']['lp'])} |",
         f"| Log-log OLS, product + week FE | {ci(R['primary']['ols'])} | {bci(B['primary_ols']['terms']['lp'])} |", "",
         f"Bootstrap: {B['primary_ppml']['ok']}/{B['primary_ppml']['requested']} (PPML) and {B['primary_ols']['ok']}/{B['primary_ols']['requested']} (OLS) "
         f"valid resamples of products, seed {B['primary_ppml']['seed']}. Standard errors in the first column are clustered by product.", "",
         "## Secondary: base (shelf) price vs promotional discount",
         "`x_base` = log shelf price per unit; `x_promo` = log(1 - observed loyalty-discount depth). Their sum is log price paid.", "",
         "| Estimator | x_base (regular price) | x_promo (discount) |", "|---|---|---|"]
    for est, nm in [("ppml", "PPML")]:
        L.append(f"| {nm} | {ci(R['secondary'][est]['x_base'])} | {ci(R['secondary'][est]['x_promo'])} |")
        L.append(f"| {nm} bootstrap | {bci(B['secondary_ppml']['terms']['x_base'])} | {bci(B['secondary_ppml']['terms']['x_promo'])} |")
    L.append(f"| OLS | {ci(R['secondary']['ols']['x_base'])} | {ci(R['secondary']['ols']['x_promo'])} |")
    L += ["", "## Display, mailer and coupon coefficients (primary specification)",
          "| Term | PPML | OLS |", "|---|---|---|"]
    for t in R["controls"]["ppml"]:
        L.append(f"| {t} | {ci(R['controls']['ppml'][t])} | {ci(R['controls']['ols'][t]) if t in R['controls']['ols'] else 'dropped'} |")
    L.append("Display/mailer flags are only observed where the promotion table has a record for a selling store, so these coefficients are likely attenuated.")
    cs, ce = R["commodity_sample"], R["commodity_each"]
    L += ["", "## Commodity level (fixed-weight price index)",
          f"- {cs['commodities_ge_60_active_weeks']} commodities with >= 60 active weeks ({cs['commodity_weeks']:,} commodity-weeks); {ce['commodities_fitted']} per-commodity fits succeeded, {ce['fits_skipped_or_failed']} skipped/failed.",
          f"- Pooled model (commodity + week FE, clustered by commodity), PPML: {ci(R['commodity_pooled']['ppml'])}; {bci(R['commodity_pooled_bootstrap']['terms']['lpi'])} "
          f"({R['commodity_pooled_bootstrap']['ok']}/{R['commodity_pooled_bootstrap']['requested']} resamples).",
          f"- Pooled OLS: {ci(R['commodity_pooled']['ols']) if R['commodity_pooled']['ols'] else 'failed'}.",
          f"- Per-commodity elasticities, unshrunk: median {ce['unshrunk']['median']:.3f} (IQR {ce['unshrunk']['q25']:.3f} to {ce['unshrunk']['q75']:.3f}); "
          f"shrunk: median {ce['shrunk']['median']:.3f} (IQR {ce['shrunk']['q25']:.3f} to {ce['shrunk']['q75']:.3f}). "
          f"Empirical-Bayes mean {ce['eb']['mean']:.3f}, between-commodity SD {ce['eb']['tau']:.3f}.",
          f"- 95% CI excludes 0 for {100*ce['unshrunk']['share_ci_excludes_0']:.1f}% and excludes -1 for {100*ce['unshrunk']['share_ci_excludes_minus1']:.1f}% of commodities (unshrunk, no multiplicity adjustment); "
          f"after Benjamini-Hochberg (q = 0.05): {ce['unshrunk']['bh_reject_0']} differ from 0, {ce['unshrunk']['bh_reject_minus1']} differ from -1. "
          f"Shrunk intervals exclude 0 for {100*ce['shrunk']['share_interval_excludes_0']:.1f}% and -1 for {100*ce['shrunk']['share_interval_excludes_minus1']:.1f}%.", "",
          "| Department | n | median (unshrunk) | IQR (unshrunk) | median (shrunk) | IQR (shrunk) |", "|---|---|---|---|---|---|"]
    for d in R["commodity_by_department"]:
        L.append(f"| {d['department']} | {d['n']} | {d['median_unshrunk']:.3f} | {d['q25_unshrunk']:.3f} to {d['q75_unshrunk']:.3f} | "
                 f"{d['median_shrunk']:.3f} | {d['q25_shrunk']:.3f} to {d['q75_shrunk']:.3f} |")
    w = ce["wrong_sign_and_extremes"]
    L += ["", "### Signs that look wrong (commodity level, reported as found)",
          f"- Positive point estimates: {w['positive_point_estimates']} of {ce['commodities_fitted']} ({w['positive_and_significant']} of them with a 95% CI above 0).",
          f"- Below -10: {w['below_minus10']}; above +5: {w['above_plus5']}; range {w['min']:.2f} to {w['max']:.2f}; median SE {w['se_median']:.3f}.",
          "- Per-commodity estimates (anonymised labels, no names) are in `evals/results/commodity_elasticities_train.csv`.", "",
          "## Robustness (each next to the primary; change = variant minus comparator)",
          "| Variant | Estimator | Term | Estimate (SE) | N | Comparator | Change | Note |", "|---|---|---|---|---|---|---|---|"]
    for r in R["robustness"]:
        if "estimate" not in r:
            L.append(f"| {r['variant']} | {r['estimator']} | {r['term']} | {r.get('note','')} | | | | |")
            continue
        chg = f"{r['change']:+.3f}" if r.get("change") is not None else ""
        cmp_ = f"{r['comparator_estimate']:.3f}" if r.get("comparator_estimate") is not None else ""
        L.append(f"| {r['variant']} | {r['estimator']} | {r['term']} | {r['estimate']:.3f} ({r['se']:.3f}) | {r['n_obs']:,} | {cmp_} | {chg} | {r.get('note','')} |")
    n = R["robustness_notes"]
    L += ["", f"Details: units capped at {n['winsor_cap_units']:.1f}; {n['top1pct_products_dropped']} top-volume products dropped; "
          f"{n['low_household_weeks_dropped']} weeks below {n['low_household_cutoff']:.0f} active households dropped; placebo rows {n['placebo_rows']:,} (weeks 8-83).",
          "", "## Reading notes (no new numbers)",
          "- `any_*` flags and `share_stores_*` are strongly related, so their individual coefficients (especially in OLS, where they have opposite signs) should be read together, not one by one.",
          "- The reference-price variants define `x_base_r` as the log of the larger of price and reference and `x_promo_r` as the log of price relative to the reference (zero when price is at or above it), so they are not like-for-like with the observed split; the matched-baseline rows show the observed split on the same rows.",
          "- Placebo: lead coefficients are expected to be near 0; any non-zero lead is evidence that price paths are persistent or anticipate demand, which would also affect the main coefficient.",
          "- Estimates are conditional on the product selling that week (weeks without sales are missing, not zero).",
          "", f"Runtime {R['runtime_seconds']} s; peak memory {R['peak_memory_mb']} MB (parent process; bootstrap workers run separately)."]
    return "\n".join(L) + "\n"


def render_validation(V):
    L = ["# Temporal stability on VALIDATION weeks 86-93", "",
         "Specified in `docs/analysis_plan.md`. Same product set and specifications as the train estimates, no re-tuning, "
         "validation weeks alone. Rule fixed in advance: **stable** = same sign and the 95% CIs overlap. Associations only.", "",
         f"Validation sample: {V['sample']['rows']:,} product-weeks, {V['sample']['products']:,} products, {V['sample']['weeks']} weeks.", "",
         "| Coefficient | Train | Validation | Difference | z of difference | Verdict |", "|---|---|---|---|---|---|"]
    for r in V["comparison"]:
        L.append(f"| {r['name']} | {r['train']:.3f} ({r['train_lo']:.3f} to {r['train_hi']:.3f}) | {r['val']:.3f} ({r['val_lo']:.3f} to {r['val_hi']:.3f}) | "
                 f"{r['diff']:+.3f} | {r['z']:+.2f} | {r['verdict']} |")
    L += ["", f"{V['n_stable']} of {V['n_total']} compared coefficients are stable by the rule above.",
          "", f"Runtime {V['runtime_seconds']} s; peak memory {V['peak_memory_mb']} MB."]
    return "\n".join(L) + "\n"
