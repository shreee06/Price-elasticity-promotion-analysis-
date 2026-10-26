"""Step 2, Part B: elasticity estimation on TRAIN weeks only (weeks 8-85; 2-85 for the start-up sensitivity)."""
import json
import time

import numpy as np
import pandas as pd

from price_elasticity import config as C
from price_elasticity.analysis import COM_CTRL, PRIMARY, SECONDARY, commodity_frame, fit_pair, pooled_commodity
from price_elasticity.commodity import (bh_reject, eb_shrink, fixed_weights, per_commodity_fits, price_index,
                                        product_meta)
from price_elasticity.data import (add_features, add_leads, add_reference_terms, assert_weeks, load_panel,
                                   select_primary_products, weekly_households)
from price_elasticity.memguard import MemGuard
from price_elasticity.models import SpecLog, cluster_bootstrap, run_and_log

T0 = time.time()
mg = MemGuard(C.PROCESSED_DIR / "elasticity_train_memlog.txt")
mg.start_watchdog()
LO, HI = C.PRIMARY_WEEKS
log = SpecLog()
R = {"plan": "docs/analysis_plan.md", "weeks_primary": [LO, HI], "stage": "train"}
ST, ST_LO = "train", C.STARTUP_WEEKS[0]


def coef(res, term):
    c = res["coef"][term]
    return {"estimate": c[0], "se": c[1], "ci_low": c[2], "ci_high": c[3]}


# ---------------- sample ----------------
all_rows = load_panel(LO, HI, merchandise_only=False)
R["sample"] = {"all_products_with_rows_weeks_8_85": int(all_rows.product_id.nunique()), "all_product_weeks": int(len(all_rows))}
del all_rows
train = add_features(load_panel(ST_LO, HI))            # weeks 2..85 merchandise, used for sensitivity/weights/leads
assert_weeks(train, ST_LO, HI)
core = train[train.week >= LO]
products, counts = select_primary_products(core)
R["sample"].update(counts)
S = core[core.product_id.isin(products)].copy()
assert_weeks(S, LO, HI)
R["sample"]["primary_rows"] = int(len(S))
R["sample"]["primary_products"] = int(len(products))
R["sample"]["primary_weeks"] = int(S.week.nunique())
R["sample"]["primary_share_of_merch_units"] = float(S.units.sum() / core.units.sum())
mg.stage("sample")

# ---------------- primary + secondary ----------------
prim = fit_pair(S, log, ST, "primary_secondary", "main", "weeks8-85 primary set")
mg.stage("primary fits")
R["primary"] = {"ppml": coef(prim[("primary", "ppml")], "lp"), "ols": coef(prim[("primary", "ols")], "lp")}
R["secondary"] = {est: {t: coef(prim[("secondary", est)], t) for t in SECONDARY} for est in ["ppml", "ols"]}
R["controls"] = {est: {t: coef(prim[("primary", est)], t) for t in C.CONTROLS if t in prim[("primary", est)]["coef"]}
                 for est in ["ppml", "ols"]}
R["controls_secondary_spec"] = {est: {t: coef(prim[("secondary", est)], t) for t in C.CONTROLS if t in prim[("secondary", est)]["coef"]}
                                for est in ["ppml", "ols"]}
R["dropped_collinear"] = {f"{k[0]}_{k[1]}": v["dropped"] for k, v in prim.items()}

# ---------------- bootstrap (headline) ----------------
boot = {}
for name, (kind, est, y, terms) in {
    "primary_ppml": ("primary", "ppml", "units", PRIMARY + C.CONTROLS),
    "primary_ols": ("primary", "ols", "ly", PRIMARY + C.CONTROLS),
    "secondary_ppml": ("secondary", "ppml", "units", SECONDARY + C.CONTROLS),
}.items():
    b, meta = cluster_bootstrap(S, y, terms, est, C.BOOTSTRAP_B, C.BOOTSTRAP_SEED, report=terms)
    boot[name] = {"terms": b, **meta}
    for t, v in b.items():
        log.add(stage=ST, group="bootstrap", spec=name, estimator=est, sample="weeks8-85 primary set", n_obs=len(S),
                n_clusters=len(products), term=t, se=v["boot_se"], ci_low=v["lo"], ci_high=v["hi"],
                note=f"cluster bootstrap B={meta['ok']}/{meta['requested']} seed={meta['seed']}")
    mg.stage(f"bootstrap {name}")
R["bootstrap"] = boot

# ---------------- robustness ----------------
rob = []


def add_rob(name, term, base_term, est, res, base_res, note=""):
    if res is None or term not in res["coef"]:
        rob.append({"variant": name, "estimator": est, "term": term, "note": "fit failed or term dropped"})
        return
    c = res["coef"][term]
    b = base_res["coef"][base_term][0] if base_res and base_term in base_res["coef"] else None
    rob.append({"variant": name, "estimator": est, "term": term, "estimate": c[0], "se": c[1], "ci_low": c[2],
                "ci_high": c[3], "n_obs": res["n_obs"], "comparator": base_term, "comparator_estimate": b,
                "change": (c[0] - b) if b is not None else None, "note": note})


def pair_variant(name, df, ctrl=None, yp="units", yo="ly", sample=""):
    out = fit_pair(df, log, ST, "robustness", name, sample or name, ctrl=ctrl, yp=yp, yo=yo)
    for est in ["ppml", "ols"]:
        add_rob(name, "lp", "lp", est, out[("primary", est)], prim[("primary", est)])
        for t in SECONDARY:
            add_rob(name, t, t, est, out[("secondary", est)], prim[("secondary", est)])


# 1 placebo leads (rows limited to weeks <= 83 so leads stay inside the train window)
SL = add_leads(train[train.product_id.isin(products)][["product_id", "week", "lp", "units", "ly"] + C.CONTROLS])
SL = SL[(SL.week >= LO) & (SL.week <= HI - 2)].dropna(subset=["lead1", "lead2"])
assert SL.week.max() <= HI - 2
for est, y in [("ppml", "units"), ("ols", "ly")]:
    base = run_and_log(log, SL, y, ["lp"] + C.CONTROLS, est, ST, "robustness", "placebo_matched_baseline", "weeks8-83 with leads")
    pl = run_and_log(log, SL, y, ["lp", "lead1", "lead2"] + C.CONTROLS, est, ST, "robustness", "placebo_leads", "weeks8-83 with leads")
    add_rob("placebo_leads", "lp", "lp", est, pl, base, "comparator = primary spec on the same rows")
    add_rob("placebo_leads", "lead1", "lp", est, pl, None, "should be ~0")
    add_rob("placebo_leads", "lead2", "lp", est, pl, None, "should be ~0")
    add_rob("placebo_matched_baseline", "lp", "lp", est, base, prim[("primary", est)], "primary spec on the lead-restricted rows")
# 2 start-up weeks
pair_variant("include_startup_weeks_2_7", train[train.product_id.isin(products)])
# 3 no display/mailer controls
pair_variant("drop_display_mailer_controls", S, ctrl=["share_units_coupon"])
# 4 reference-price discount definitions
for which in ["max8", "med13"]:
    Dr = add_reference_terms(S, which)
    for est, y in [("ppml", "units"), ("ols", "ly")]:
        base = run_and_log(log, Dr, y, SECONDARY + C.CONTROLS, est, ST, "robustness", f"ref_{which}_matched_baseline", f"rows with {which} reference")
        rr = run_and_log(log, Dr, y, ["x_base_r", "x_promo_r"] + C.CONTROLS, est, ST, "robustness", f"ref_{which}", f"rows with {which} reference")
        add_rob(f"ref_{which}", "x_base_r", "x_base", est, rr, base, "comparator = observed split on the same rows")
        add_rob(f"ref_{which}", "x_promo_r", "x_promo", est, rr, base, "comparator = observed split on the same rows")
        add_rob(f"ref_{which}_matched_baseline", "x_base", "x_base", est, base, prim[("secondary", est)], "observed split on reference-available rows")
        add_rob(f"ref_{which}_matched_baseline", "x_promo", "x_promo", est, base, prim[("secondary", est)], "observed split on reference-available rows")
# 5 winsorise / drop top 1% products
cap = float(S.units.quantile(0.99))
W = S.assign(units_w=S.units.clip(upper=cap))
W["ly_w"] = np.log(W.units_w)
pair_variant("winsorise_units_p99", W, yp="units_w", yo="ly_w", sample=f"units capped at p99 of product-weeks")
tot = S.groupby("product_id").units.sum()
top = tot[tot >= tot.quantile(0.99)].index
pair_variant("drop_top1pct_volume_products", S[~S.product_id.isin(top)], sample=f"dropped {len(top)} products")
# 6 low-household weeks
hh = weekly_households(HI)
cut = float(hh.loc[LO:HI].quantile(C.LOW_HOUSEHOLD_QUANTILE))
low_weeks = hh.loc[LO:HI][hh.loc[LO:HI] < cut].index
pair_variant("drop_low_household_weeks", S[~S.week.isin(low_weeks)], sample=f"dropped {len(low_weeks)} weeks with < {cut:.0f} active households")
R["robustness"] = rob
R["robustness_notes"] = {"winsor_cap_units": cap, "top1pct_products_dropped": int(len(top)),
                         "low_household_cutoff": cut, "low_household_weeks_dropped": int(len(low_weeks)),
                         "placebo_rows": int(len(SL))}
mg.stage("robustness")

# ---------------- commodity level ----------------
prod2com, dept = product_meta()
w = fixed_weights(train, prod2com)                      # weeks 2-85 unit shares, merchandise products
idx = price_index(core, w, prod2com)
cp_all = commodity_frame(LO, HI, idx)
act = cp_all.groupby("commodity").size()
keep = act[act >= C.COMMODITY_MIN_ACTIVE_WEEKS].index
cdf = cp_all[cp_all.commodity.isin(keep)].copy()
assert_weeks(cdf, LO, HI)
hh_ = weekly_households(HI)
R["commodity_sample"] = {"merchandise_commodities_with_index": int(act.size), "commodities_ge_60_active_weeks": int(len(keep)),
                         "commodity_weeks": int(len(cdf)), "products_without_weight": int((~core.product_id.isin(w.index)).sum())}
pooled = pooled_commodity(cdf, log, ST, "commodities >= 60 active weeks, weeks 8-85")
R["commodity_pooled"] = {est: (coef(r, "lpi") if r else None) for est, r in pooled.items()}
bp, bmeta = cluster_bootstrap(cdf, "units", ["lpi"] + COM_CTRL, "ppml", C.BOOTSTRAP_B, C.BOOTSTRAP_SEED, cluster="commodity",
                              fe_other=("week",), report=["lpi"])
R["commodity_pooled_bootstrap"] = {"terms": bp, **bmeta}
log.add(stage=ST, group="bootstrap", spec="commodity_pooled_ppml", estimator="ppml", sample="commodities >= 60 weeks", n_obs=len(cdf),
        n_clusters=len(keep), term="lpi", se=bp["lpi"]["boot_se"], ci_low=bp["lpi"]["lo"], ci_high=bp["lpi"]["hi"],
        note=f"cluster bootstrap B={bmeta['ok']}/{bmeta['requested']} seed={bmeta['seed']}")
mg.stage("commodity pooled")

pc, fails = per_commodity_fits(cdf, hh_)
shr, shr_se, mu, tau2 = eb_shrink(pc.est, pc.se)
pc["shrunk"], pc["shrunk_se"] = shr, shr_se
pc["department"] = pc.commodity.map(dept)
rng = np.random.default_rng(C.BOOTSTRAP_SEED)
labels = rng.permutation(len(pc))
pc["label"] = [f"C{int(i):03d}" for i in labels]
for _, r in pc.iterrows():
    log.add(stage=ST, group="commodity_each", spec="per_commodity_ppml", estimator="ppml", sample="weeks 8-85", n_obs=int(r.n_weeks),
            term="lpi", estimate=r.est, se=r.se, ci_low=r.est - 1.96 * r.se, ci_high=r.est + 1.96 * r.se,
            note=f"anon {r.label}; shrunk={r.shrunk:.3f}")
for com, why in fails:
    log.add(stage=ST, group="commodity_each", spec="per_commodity_ppml", estimator="ppml", term="lpi", note=f"fit failed/skipped ({why})")
z = 1.959964
sig0 = (pc.est.abs() > z * pc.se)
sigm1 = ((pc.est + 1).abs() > z * pc.se)
s_lo, s_hi = pc.shrunk - z * pc.shrunk_se, pc.shrunk + z * pc.shrunk_se
R["commodity_each"] = {
    "commodities_fitted": int(len(pc)), "fits_skipped_or_failed": int(len(fails)),
    "unshrunk": {"median": float(pc.est.median()), "q25": float(pc.est.quantile(.25)), "q75": float(pc.est.quantile(.75)),
                 "share_ci_excludes_0": float(sig0.mean()), "share_ci_excludes_minus1": float(sigm1.mean()),
                 "bh_reject_0": int(bh_reject(pc.p0)), "bh_reject_minus1": int(bh_reject(pc.pm1))} if False else
                {"median": float(pc.est.median()), "q25": float(pc.est.quantile(.25)), "q75": float(pc.est.quantile(.75)),
                 "share_ci_excludes_0": float(sig0.mean()), "share_ci_excludes_minus1": float(sigm1.mean()),
                 "bh_reject_0": int(bh_reject(pc.p0).sum()), "bh_reject_minus1": int(bh_reject(pc.pm1).sum())},
    "shrunk": {"median": float(pc.shrunk.median()), "q25": float(pc.shrunk.quantile(.25)), "q75": float(pc.shrunk.quantile(.75)),
               "share_interval_excludes_0": float(((s_lo > 0) | (s_hi < 0)).mean()),
               "share_interval_excludes_minus1": float(((s_lo > -1) | (s_hi < -1)).mean())},
    "eb": {"mean": mu, "tau2": tau2, "tau": float(np.sqrt(tau2))},
    "wrong_sign_and_extremes": {"positive_point_estimates": int((pc.est > 0).sum()),
                                "positive_and_significant": int(((pc.est > 0) & sig0).sum()),
                                "below_minus10": int((pc.est < -10).sum()), "above_plus5": int((pc.est > 5).sum()),
                                "min": float(pc.est.min()), "max": float(pc.est.max()),
                                "se_median": float(pc.se.median())},
}
by = []
for d, g in pc.groupby("department"):
    by.append({"department": d, "n": int(len(g)), "median_unshrunk": float(g.est.median()),
               "q25_unshrunk": float(g.est.quantile(.25)), "q75_unshrunk": float(g.est.quantile(.75)),
               "median_shrunk": float(g.shrunk.median()), "q25_shrunk": float(g.shrunk.quantile(.25)),
               "q75_shrunk": float(g.shrunk.quantile(.75))})
R["commodity_by_department"] = sorted(by, key=lambda r: -r["n"])
pc.drop(columns=["commodity"]).sort_values("label").to_csv(C.RESULTS_DIR / "commodity_elasticities_train.csv", index=False)
mg.stage("commodity each")

# ---------------- write ----------------
R["runtime_seconds"] = round(time.time() - T0, 1)
R["peak_memory_mb"] = mg.peak_mb()
(C.RESULTS_DIR / "elasticity_train.json").write_text(json.dumps(R, indent=2, default=float))
log.frame().to_csv(C.RESULTS_DIR / "spec_log.csv", index=False)
print("done", R["runtime_seconds"], "s, peak", R["peak_memory_mb"], "MB")
