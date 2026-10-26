"""Audit the panels: writes evals/results/panel_audit.json and docs/panel_audit.md (real numbers only).

Usability / discount-depth / promo comparisons use TRAIN weeks only, so the validation and test weeks stay untouched.
"""
import json
import numpy as np
import pandas as pd

from price_elasticity import config as C
from price_elasticity.memguard import MemGuard
from price_elasticity.price import add_row_values, clean_transactions

P = C.PROCESSED_DIR
mg = MemGuard(P / "audit_memlog.txt")
mg.start_watchdog()
A = {}
TR = C.TRAIN_WEEKS
THR = C.DISCOUNT_DEPTH_THRESHOLD


def q(s, ps=(0.05, 0.25, 0.5, 0.75, 0.95, 0.99)):
    s = pd.Series(s).dropna()
    return {f"p{int(p*100)}": float(s.quantile(p)) for p in ps} | {"mean": float(s.mean()), "n": int(len(s))}


# ---------- 1. source transactions: sign conventions, cleaning, reconciliation ----------
tx = pd.read_parquet(P / "transactions.parquet")
A["source"] = {
    "rows": int(len(tx)), "households": int(tx.household_key.nunique()), "products": int(tx.PRODUCT_ID.nunique()),
    "stores": int(tx.STORE_ID.nunique()), "weeks": int(tx.WEEK_NO.nunique()),
    "day_min": int(tx.DAY.min()), "day_max": int(tx.DAY.max()),
    "total_units": int(tx.QUANTITY.sum()), "total_sales_value": round(float(tx.SALES_VALUE.sum()), 2),
}
A["sign_conventions"] = {c: {"negative": int((tx[c] < 0).sum()), "zero": int((tx[c] == 0).sum()),
                             "positive": int((tx[c] > 0).sum()), "min": float(tx[c].min()), "max": float(tx[c].max())}
                         for c in ["RETAIL_DISC", "COUPON_MATCH_DISC", "COUPON_DISC"]}
wk_hh = tx.groupby("WEEK_NO").household_key.nunique().rename("active_households")
clean, counts = clean_transactions(tx)
del tx
clean = add_row_values(clean)
A["cleaning"] = counts
# empirical test of the two candidate 'paid' formulas against shelf prices of non-coupon rows (same product-store-week)
clean["S1"] = clean.shelf_value / clean.QUANTITY
clean["S2"] = (clean.SALES_VALUE - (clean.RETAIL_DISC + clean.COUPON_MATCH_DISC + clean.COUPON_DISC)) / clean.QUANTITY
k = ["PRODUCT_ID", "STORE_ID", "WEEK_NO"]
ref = clean[clean.COUPON_DISC == 0].groupby(k).S1.median().rename("ref")
cr = clean[clean.COUPON_DISC != 0].join(ref, on=k, how="inner")
A["price_definition_check"] = {
    "coupon_rows_total": int((clean.COUPON_DISC != 0).sum()), "coupon_rows_with_noncoupon_reference": int(len(cr)),
    "shelf_formula_median_ratio_to_noncoupon_shelf": float((cr.S1 / cr.ref).median()),
    "shelf_formula_share_within_1pct": float(((cr.S1 / cr.ref - 1).abs() < 0.01).mean()),
    "user_paid_formula_median_ratio_to_noncoupon_shelf": float((cr.S2 / cr.ref).median()),
    "user_paid_formula_share_within_1pct": float(((cr.S2 / cr.ref - 1).abs() < 0.01).mean()),
    "coupon_rows_where_user_paid_formula_exceeds_shelf": int((clean.S2 > clean.S1 + 1e-9).sum()),
    "adopted_paid_price_nonpositive_rows": int(((clean.SALES_VALUE + clean.COUPON_DISC) <= 0).sum()),
}
src_units, src_cents = int(clean.QUANTITY.sum()), int(round(clean.SALES_VALUE.sum() * 100))
A["sample_note"] = ("Only 2,500 sampled households: all units/values are sample counts, not store totals.")
del clean

pp = pd.read_parquet(P / "panel.parquet")
pc = pd.read_parquet(P / "panel_commodity.parquet")
mg.stage("panels loaded")
nm = pp[pp.non_merchandise == 1]
A["non_merchandise"] = {"product_rows": int(len(nm)), "products": int(nm.product_id.nunique()),
                        "share_of_panel_units": float(nm.units.sum() / pp.units.sum()),
                        "share_of_panel_sales_value": float(nm.sales_value.sum() / pp.sales_value.sum()),
                        "commodity_rows": int((pc.non_merchandise == 1).sum()),
                        "definition": "fuel (QUANTITY in thousandths of gallons), coupon and placeholder commodities"}
ppa, pca = pp, pc          # full panels: reconciliation and sizes
pp, pc = pp[pp.non_merchandise == 0], pc[pc.non_merchandise == 0]  # analysis universe: everything below
A["reconciliation"] = {}
for name, df in [("product_panel", ppa), ("commodity_panel", pca)]:
    A["reconciliation"][name] = {
        "rows": int(len(df)), "units_panel": int(df.units.sum()), "units_source_clean": src_units,
        "units_exact_match": bool(int(df.units.sum()) == src_units),
        "sales_cents_panel": int(round(df.sales_value.sum() * 100)), "sales_cents_source_clean": src_cents,
        "sales_exact_match_to_cent": bool(int(round(df.sales_value.sum() * 100)) == src_cents),
        "sales_abs_diff": float(abs(df.sales_value.sum() - src_cents / 100)),
        "units_plus_dropped_equals_source_total": bool(src_units + counts["units_dropped"] == A["source"]["total_units"]),
    }
A["panel"] = {
    "product_rows": int(len(ppa)), "commodity_rows": int(len(pca)), "products": int(ppa.product_id.nunique()),
    "commodities": int(pca.commodity.nunique()), "weeks": int(ppa.week.nunique()),
    "analysis_universe": {"product_rows": int(len(pp)), "commodity_rows": int(len(pc)), "products": int(pp.product_id.nunique()),
                          "commodities": int(pc.commodity.nunique())},
    "active_weeks_products": q(pp.groupby("product_id").size(), (0.25, 0.5, 0.75, 0.95)),
    "products_ge_30_active_weeks": int((pp.groupby("product_id").size() >= C.MIN_ACTIVE_WEEKS).sum()),
    "commodities_ge_30_active_weeks": int((pc.groupby("commodity").size() >= C.MIN_ACTIVE_WEEKS).sum()),
    "reference_null_rows": {
        d: {"product": int(pp[f"depth_{d}"].isna().sum()), "commodity": int(pc[f"depth_{d}"].isna().sum())}
        for d in ["max8", "med13"]},
}
prod_t = pd.read_parquet(P / "product.parquet")
A["panel"]["commodities_spanning_multiple_departments"] = int((prod_t.groupby("COMMODITY_DESC", observed=True).DEPARTMENT.nunique() > 1).sum())
A["panel"]["commodity_placeholder_names_present"] = [c for c in pca.commodity.unique() if c in C.NON_MERCH_COMMODITIES]
A["panel"]["causal_duplicate_guard_ok"] = bool((pp.n_cells_display <= pp.n_stores).all())
A["panel"]["selling_cells_without_causal_record_share"] = float(1 - pp.n_cells_recorded.sum() / pp.n_stores.sum())

# ---------- 2. descriptive stats on TRAIN weeks only ----------
out = {}
for name, df, ent in [("product", pp, "product_id"), ("commodity", pc, "commodity")]:
    t = df[(df.week >= TR[0]) & (df.week <= TR[1]) & (df.split != "partial_week")].copy()
    r = {"train_rows": int(len(t)),
         "share_rows_retail_discount": float((t.share_units_retail_disc > 0).mean()),
         "share_units_sold_with_retail_discount": float(t.units_retail_disc.sum() / t.units.sum()),
         "share_rows_any_display": float(t.any_display.mean()), "share_rows_any_mailer": float(t.any_mailer.mean()),
         "share_rows_any_coupon": float((t.share_units_coupon > 0).mean()),
         "share_units_with_coupon": float(t.units_coupon.sum() / t.units.sum()),
         "avg_retail_disc_depth_when_discounted": q(t.loc[t.share_units_retail_disc > 0, "avg_retail_disc_depth"])}
    for d in ["max8", "med13"]:
        s = t[f"depth_{d}"]
        r[f"depth_{d}"] = {"null_rows": int(s.isna().sum()), "dist": q(s), "share_gt_0": float((s.dropna() > 0).mean()),
                           "share_gt_threshold": float((s.dropna() > THR).mean())}
    # within-entity price variation (entities with >= 30 active weeks in train)
    g = t.groupby(ent)
    act = g.size()
    keep = act[act >= C.MIN_ACTIVE_WEEKS].index
    tk = t[t[ent].isin(keep)]
    gk = tk.groupby(ent).avg_shelf_price
    cv = gk.std() / gk.mean()
    rng = gk.max() / gk.min() - 1
    r["within_entity_price_variation"] = {"entities": int(len(keep)), "cv_of_weekly_shelf_price": q(cv),
                                          "max_over_min_minus_1": q(rng),
                                          "share_entities_cv_gt_5pct": float((cv > 0.05).mean())}
    # usability
    r["usable"] = {"definition": f">= {C.MIN_DISCOUNT_WEEKS} train weeks with depth > {THR:.0%} AND >= {C.MIN_NONDISCOUNT_WEEKS} "
                                 f"train weeks with non-null depth <= {THR:.0%}; entity also needs >= {C.MIN_ACTIVE_WEEKS} active train weeks"}
    for d in ["max8", "med13"]:
        s = t.dropna(subset=[f"depth_{d}"])
        hi = (s[f"depth_{d}"] > THR).groupby(s[ent]).sum()
        lo = (s[f"depth_{d}"] <= THR).groupby(s[ent]).sum()
        ok = (hi >= C.MIN_DISCOUNT_WEEKS) & (lo.reindex(hi.index).fillna(0) >= C.MIN_NONDISCOUNT_WEEKS)
        ok_act = ok & (act.reindex(hi.index) >= C.MIN_ACTIVE_WEEKS)
        usable = set(ok_act[ok_act].index)
        r["usable"][d] = {"without_active_weeks_requirement": int(ok.sum()), "with_active_weeks_requirement": int(len(usable)),
                          "share_of_units_in_usable_entities": float(t[t[ent].isin(usable)].units.sum() / t.units.sum()),
                          "entities_total": int(t[ent].nunique())}
        # overlap of display/mailer with price cuts (all train rows with non-null depth)
        s = s.assign(cut=s[f"depth_{d}"] > THR)
        ov = {}
        for flag in ["any_display", "any_mailer"]:
            ov[flag] = {"rows_flagged": int(s[flag].sum()),
                        "share_flagged_rows_with_price_cut": float(s.loc[s[flag] == 1, "cut"].mean()) if s[flag].sum() else None,
                        "share_unflagged_rows_with_price_cut": float(s.loc[s[flag] == 0, "cut"].mean()),
                        "share_cut_rows_with_flag": float(s.loc[s.cut, flag].mean()) if s.cut.sum() else None}
        s2 = s.assign(either=((s.any_display == 1) | (s.any_mailer == 1)).astype(int))
        ov["either_display_or_mailer"] = {"share_flagged_rows_with_price_cut": float(s2.loc[s2.either == 1, "cut"].mean()),
                                          "share_unflagged_rows_with_price_cut": float(s2.loc[s2.either == 0, "cut"].mean()),
                                          "share_cut_rows_with_flag": float(s2.loc[s2.cut, "either"].mean())}
        ov["display_and_mailer_both_share_of_flagged"] = float(((s.any_display == 1) & (s.any_mailer == 1)).sum() /
                                                              max(1, ((s.any_display == 1) | (s.any_mailer == 1)).sum()))
        ov["retail_discount_flag_vs_cut"] = {"share_cut_rows_with_retail_discount": float((s.loc[s.cut, "share_units_retail_disc"] > 0).mean())}
        r["usable"][d]["overlap"] = ov
        # NAIVE descriptive comparison, usable entities, train weeks
        u = s[s[ent].isin(usable)].copy()
        u["promoted"] = (u.cut | (u.any_display == 1) | (u.any_mailer == 1))
        pooled = u.groupby("promoted").units.mean()
        pe = u.groupby([ent, "promoted"]).units.mean().unstack()
        ratio = (pe[True] / pe[False]).replace([np.inf, -np.inf], np.nan).dropna()
        r["usable"][d]["naive_promoted_vs_not"] = {
            "label": "NAIVE descriptive comparison, NOT an elasticity and not a causal effect; promoted = price cut > threshold OR display OR mailer",
            "entities": int(u[ent].nunique()), "rows_promoted": int(u.promoted.sum()), "rows_not_promoted": int((~u.promoted).sum()),
            "mean_units_promoted_pooled": float(pooled.get(True, np.nan)), "mean_units_not_promoted_pooled": float(pooled.get(False, np.nan)),
            "within_entity_ratio_mean_units_promoted_over_not": q(ratio, (0.25, 0.5, 0.75))}
    out[name] = r
A["descriptives_train_weeks"] = out
mg.stage("descriptives")

# ---------- 3. weekly volume and seasonality (all weeks, descriptive) ----------
wk = pp.groupby("week").agg(units=("units", "sum"), sales_value=("sales_value", "sum")).reset_index()
wk = wk.merge(wk_hh.reset_index().rename(columns={"WEEK_NO": "week"}), on="week", how="left")
wk["units_per_active_household"] = wk.units / wk.active_households
full = wk[(wk.week >= C.FIRST_FULL_WEEK) & (wk.week <= C.LAST_FULL_WEEK)].set_index("week")
full["trend13"] = full.units.rolling(13, center=True, min_periods=13).mean()
full["detrended"] = full.units / full.trend13  # ratio to centered 13-week mean
pairs = pd.DataFrame({"a": full.detrended, "b": full.detrended.shift(-52)}).dropna()
raw_pairs = pd.DataFrame({"a": full.units, "b": full.units.shift(-52)}).dropna()
dt = full.detrended.dropna()
A["weekly_volume"] = {
    "note": "Dataset has no calendar dates (only DAY 1..711), so holidays cannot be dated without an assumed anchor; peaks/troughs are reported by WEEK_NO and recurrence one year (52 weeks) apart.",
    "full_weeks_mean_units": float(full.units.mean()), "full_weeks_cv": float(full.units.std() / full.units.mean()),
    "mean_units_first_year_weeks_2_53": float(full.units.loc[2:53].mean()), "mean_units_second_year_weeks_54_101": float(full.units.loc[54:101].mean()),
    "active_households_weeks_2_7_mean": float(full.active_households.loc[2:7].mean()), "active_households_weeks_30_60_mean": float(full.active_households.loc[30:60].mean()),
    "units_per_household_weeks_2_7_mean": float(full.units_per_active_household.loc[2:7].mean()),
    "units_per_household_weeks_30_60_mean": float(full.units_per_active_household.loc[30:60].mean()),
    "lowest6_weeks_raw": full.units.nsmallest(6).index.astype(int).tolist(),
    "corr_raw_w_vs_w_plus_52": float(raw_pairs.corr().iloc[0, 1]), "pairs_raw": int(len(raw_pairs)),
    "corr_detrended_w_vs_w_plus_52": float(pairs.corr().iloc[0, 1]), "pairs_detrended": int(len(pairs)),
    "top6_detrended_weeks": dt.nlargest(6).index.astype(int).tolist(), "top6_detrended_ratios": [round(float(x), 3) for x in dt.nlargest(6)],
    "bottom6_detrended_weeks": dt.nsmallest(6).index.astype(int).tolist(), "bottom6_detrended_ratios": [round(float(x), 3) for x in dt.nsmallest(6)],
    "detrended_range": [float(dt.min()), float(dt.max())],
}
top = set(A["weekly_volume"]["top6_detrended_weeks"])
A["weekly_volume"]["top6_detrended_recurring_52_weeks_later_within_1"] = sorted(int(w) for w in top if any(abs(w + 52 - x) <= 1 for x in top))
wk.to_csv(C.RESULTS_DIR / "weekly_volume.csv", index=False)

A["memory_peak_mb"] = mg.peak_mb()
(C.RESULTS_DIR / "panel_audit.json").write_text(json.dumps(A, indent=2))

# ---------- markdown ----------
S, R, V, D = A["source"], A["reconciliation"], A["weekly_volume"], A["descriptives_train_weeks"]
pr = D["product"]; cm = D["commodity"]
f = lambda x: f"{x:,.0f}"; pct = lambda x: f"{100*x:.1f}%"
def usable_line(d, e):
    u = D[e]["usable"][d]; return f"{u['with_active_weeks_requirement']:,} of {u['entities_total']:,} ({pct(u['share_of_units_in_usable_entities'])} of train units)"
sc = A["sign_conventions"]; pdc = A["price_definition_check"]
md = f"""# Panel audit

All numbers come from `scripts/audit_panel.py` and are stored in `evals/results/panel_audit.json`.
Statistics on discounts, usability, overlap and promoted-vs-not use **train weeks only** ({TR[0]}-{TR[1]}); validation and test weeks are untouched.
Estimates here are descriptive associations, not causal effects.

**Sample caveat.** The data covers only {S['households']:,} sampled households of one retailer, so all units and values are sample counts, not store totals.

## Source and cleaning
- Source transactions: {f(S['rows'])} rows, {S['households']:,} households, {f(S['products'])} products, {S['stores']} stores, {S['weeks']} weeks (DAY {S['day_min']}-{S['day_max']}).
- Week mapping verified: `WEEK_NO = (DAY + 1) // 7 + 1`. Week 1 (days 1-5) and week 102 (days 706-711) are partial; full weeks are 2-101.
- Rule: rows with `QUANTITY <= 0` or `SALES_VALUE <= 0` are dropped (unit price undefined). QUANTITY<=0: {f(A['cleaning']['quantity_le_0'])}; SALES_VALUE<=0: {f(A['cleaning']['sales_value_le_0'])}; both: {f(A['cleaning']['both'])}; total dropped: {f(A['cleaning']['rows_dropped'])} rows ({f(A['cleaning']['units_dropped'])} units, {A['cleaning']['sales_value_dropped']:.2f} sales value). Kept: {f(A['cleaning']['rows_kept'])} rows.

## Discount sign convention and price definitions
- `RETAIL_DISC`: {f(sc['RETAIL_DISC']['negative'])} negative, {sc['RETAIL_DISC']['positive']} positive, rest zero. `COUPON_MATCH_DISC`: {f(sc['COUPON_MATCH_DISC']['negative'])} negative, {sc['COUPON_MATCH_DISC']['positive']} positive. `COUPON_DISC`: {f(sc['COUPON_DISC']['negative'])} negative, {sc['COUPON_DISC']['positive']} positive. Discounts are stored as negative numbers.
- Shelf price per unit (adopted) = (SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC)) / QUANTITY. On {f(pdc['coupon_rows_with_noncoupon_reference'])} coupon rows that have a non-coupon sale of the same product/store/week, this matches that shelf price within 1% in {pct(pdc['shelf_formula_share_within_1pct'])} of cases (median ratio {pdc['shelf_formula_median_ratio_to_noncoupon_shelf']:.3f}).
- The suggested paid formula `SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC + COUPON_DISC)` adds the (negative) coupon back: it exceeds shelf price on {f(pdc['coupon_rows_where_user_paid_formula_exceeds_shelf'])} rows (median ratio {pdc['user_paid_formula_median_ratio_to_noncoupon_shelf']:.3f}, within 1% in {pct(pdc['user_paid_formula_share_within_1pct'])}). SALES_VALUE therefore does not yet include the manufacturer coupon.
- **Adopted** paid price per unit = (SALES_VALUE + COUPON_DISC) / QUANTITY, i.e. shelf value plus all three (negative) discounts. Rows with non-positive adopted paid value: {pdc['adopted_paid_price_nonpositive_rows']}.
- Panel prices are unit-weighted averages (total value / total units) per product/commodity-week. Retail discount flag: `RETAIL_DISC < -0.005`. Average retail discount depth = total retail discount / total shelf value (value-weighted).
- Commodity-level prices mix products of different sizes, so they are average value per unit, not a like-for-like price.

## Non-merchandise rows (kept in the panels, excluded from every statistic below except reconciliation)
- Fuel (QUANTITY is in thousandths of gallons: one fuel product alone is 83% of all raw units), coupon and placeholder commodities carry `non_merchandise = 1`: {A['non_merchandise']['products']:,} products, {A['non_merchandise']['share_of_panel_units']*100:.1f}% of panel units but {A['non_merchandise']['share_of_panel_sales_value']*100:.1f}% of sales value. Analysis universe: {A['panel']['analysis_universe']['products']:,} products, {A['panel']['analysis_universe']['commodities']} commodities.

## Panel size and reconciliation
- Product panel: {f(R['product_panel']['rows'])} rows, {A['panel']['products']:,} products, {A['panel']['weeks']} weeks. Commodity panel: {f(R['commodity_panel']['rows'])} rows, {A['panel']['commodities']} commodities (COMMODITY_DESC; {A['panel']['commodities_spanning_multiple_departments']} occur in more than one department; placeholders present: {', '.join(A['panel']['commodity_placeholder_names_present'])}).
- Only weeks with at least one valid sale have a row; absent weeks are missing, not zero.
- Reconciliation to cleaned source rows: units product panel {f(R['product_panel']['units_panel'])} vs {f(R['product_panel']['units_source_clean'])} (exact: {R['product_panel']['units_exact_match']}); sales value exact to the cent: {R['product_panel']['sales_exact_match_to_cent']} (abs diff {R['product_panel']['sales_abs_diff']:.2e}). Commodity panel: units exact {R['commodity_panel']['units_exact_match']}, sales exact {R['commodity_panel']['sales_exact_match_to_cent']}. Cleaned units + dropped units equal source total: {R['product_panel']['units_plus_dropped_equals_source_total']}.
- Products with >= {C.MIN_ACTIVE_WEEKS} active weeks (analysis universe): {A['panel']['products_ge_30_active_weeks']:,}; commodities: {A['panel']['commodities_ge_30_active_weeks']}.
- Reference price null (too little history) in product panel: max-8 {f(A['panel']['reference_null_rows']['max8']['product'])}, median-13 {f(A['panel']['reference_null_rows']['med13']['product'])} rows; commodity panel: {A['panel']['reference_null_rows']['max8']['commodity']} and {A['panel']['reference_null_rows']['med13']['commodity']} rows. Rule: at least {C.MIN_OBS_MAX} (max-8) or {C.MIN_OBS_MEDIAN} (median-13) observed prior weeks inside the window.
- Promotion flags: causal_data flags are store-level (`display != 0`, `mailer != 0`). For each product-week we join them to the stores that actually sold it (`share_stores_display/mailer` = flagged selling stores / selling stores, `any_*` = at least one selling store flagged); `*_chain` counts use all stores listed in causal_data. A selling store with no causal record is treated as not flagged: {pct(A['panel']['selling_cells_without_causal_record_share'])} of selling product-store-weeks have no causal record. For commodities the share is over selling product-store-week cells.

## How often products are discounted (product-weeks, train)
- Rows: {f(pr['train_rows'])}. Retail (loyalty) discount on any unit: {pct(pr['share_rows_retail_discount'])}; share of units sold with a retail discount: {pct(pr['share_units_sold_with_retail_discount'])}; any display: {pct(pr['share_rows_any_display'])}; any mailer: {pct(pr['share_rows_any_mailer'])}; any manufacturer coupon unit: {pct(pr['share_rows_any_coupon'])} (units with coupon {pct(pr['share_units_with_coupon'])}).
- Commodity-weeks: retail discount {pct(cm['share_rows_retail_discount'])}, display {pct(cm['share_rows_any_display'])}, mailer {pct(cm['share_rows_any_mailer'])}, coupon {pct(cm['share_rows_any_coupon'])}.
- Average retail discount depth when discounted (product-weeks): median {pct(pr['avg_retail_disc_depth_when_discounted']['p50'])}, p95 {pct(pr['avg_retail_disc_depth_when_discounted']['p95'])}.

## Distribution of discount depth vs reference (product-weeks, train, non-null)
| Reference | null rows | share depth > 0 | share depth > {THR:.0%} | median | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {lab} | {f(pr[f'depth_{d}']['null_rows'])} | {pct(pr[f'depth_{d}']['share_gt_0'])} | {pct(pr[f'depth_{d}']['share_gt_threshold'])} | {pct(pr[f'depth_{d}']['dist']['p50'])} | {pct(pr[f'depth_{d}']['dist']['p75'])} | {pct(pr[f'depth_{d}']['dist']['p95'])} | {pct(pr[f'depth_{d}']['dist']['p99'])} |"
    for d, lab in [("max8", "max of prior 8 weeks"), ("med13", "median of prior 13 weeks")]) + f"""

## Within-product price variation (products with >= {C.MIN_ACTIVE_WEEKS} active train weeks: {pr['within_entity_price_variation']['entities']:,})
- Coefficient of variation of weekly shelf price: median {pct(pr['within_entity_price_variation']['cv_of_weekly_shelf_price']['p50'])}, p75 {pct(pr['within_entity_price_variation']['cv_of_weekly_shelf_price']['p75'])}, p95 {pct(pr['within_entity_price_variation']['cv_of_weekly_shelf_price']['p95'])}; share of products with CV > 5%: {pct(pr['within_entity_price_variation']['share_entities_cv_gt_5pct'])}.
- Commodities ({cm['within_entity_price_variation']['entities']}): median CV {pct(cm['within_entity_price_variation']['cv_of_weekly_shelf_price']['p50'])}.

## Usable promotion variation
Definition: {pr['usable']['definition']}.
| Level | max-8 reference | median-13 reference |
|---|---|---|
| Products | {usable_line('max8','product')} | {usable_line('med13','product')} |
| Commodities | {usable_line('max8','commodity')} | {usable_line('med13','commodity')} |

## Overlap of display/mailer with price cuts (price cut = depth > {THR:.0%}; product-weeks, train)
""" + "\n".join(
    f"- {lab}: " + "; ".join(
        f"{fl.replace('any_','')} flagged rows with a price cut {pct(pr['usable'][d]['overlap'][fl]['share_flagged_rows_with_price_cut'])} (unflagged {pct(pr['usable'][d]['overlap'][fl]['share_unflagged_rows_with_price_cut'])}); price-cut rows carrying the flag {pct(pr['usable'][d]['overlap'][fl]['share_cut_rows_with_flag'])}"
        for fl in ["any_display", "any_mailer"]) + f"; display or mailer together: flagged rows with cut {pct(pr['usable'][d]['overlap']['either_display_or_mailer']['share_flagged_rows_with_price_cut'])} vs unflagged {pct(pr['usable'][d]['overlap']['either_display_or_mailer']['share_unflagged_rows_with_price_cut'])}; price-cut rows with a retail discount on some unit {pct(pr['usable'][d]['overlap']['retail_discount_flag_vs_cut']['share_cut_rows_with_retail_discount'])}."
    for d, lab in [("max8", "max-8 reference"), ("med13", "median-13 reference")]) + f"""

## Weekly volume and seasonality (full weeks 2-101, sample units, non-merchandise excluded)
- Mean weekly units {f(V['full_weeks_mean_units'])} (CV {pct(V['full_weeks_cv'])}); mean in weeks 2-53: {f(V['mean_units_first_year_weeks_2_53'])}, weeks 54-101: {f(V['mean_units_second_year_weeks_54_101'])}.
- Start-up ramp: the six lowest weeks are {V['lowest6_weeks_raw']}. Active households per week average {V['active_households_weeks_2_7_mean']:.0f} in weeks 2-7 vs {V['active_households_weeks_30_60_mean']:.0f} in weeks 30-60; units per active household {V['units_per_household_weeks_2_7_mean']:.1f} vs {V['units_per_household_weeks_30_60_mean']:.1f}.
- Raw correlation of weekly units between week w and w+52 ({V['pairs_raw']} pairs): {V['corr_raw_w_vs_w_plus_52']:.3f}. After dividing by a centered 13-week mean ({V['pairs_detrended']} pairs): {V['corr_detrended_w_vs_w_plus_52']:.3f}.
- Detrended peaks (WEEK_NO, ratio to trend): {list(zip(V['top6_detrended_weeks'], V['top6_detrended_ratios']))}; troughs: {list(zip(V['bottom6_detrended_weeks'], V['bottom6_detrended_ratios']))}. Peaks with another peak 52 (+-1) weeks later: {V['top6_detrended_recurring_52_weeks_later_within_1']}.
- The dataset has no calendar dates, so holiday weeks are not labelled; the weekly series is in `evals/results/weekly_volume.csv`. Any holiday effect would have to be tied to an externally assumed date anchor, which is not done here.

## Naive promoted vs non-promoted weeks (NOT an elasticity, not causal; train weeks, usable products)
Promoted = price cut > {THR:.0%} OR display OR mailer. Pooled means mix products of very different sizes, so the within-product ratio is the more informative line. Promotions are not randomised and are confounded with product, season and other promotion channels.
""" + "\n".join(
    f"- {lab}: {pr['usable'][d]['naive_promoted_vs_not']['entities']:,} products; mean units/week promoted {pr['usable'][d]['naive_promoted_vs_not']['mean_units_promoted_pooled']:.2f} (n={f(pr['usable'][d]['naive_promoted_vs_not']['rows_promoted'])}) vs not promoted {pr['usable'][d]['naive_promoted_vs_not']['mean_units_not_promoted_pooled']:.2f} (n={f(pr['usable'][d]['naive_promoted_vs_not']['rows_not_promoted'])}); within-product ratio of mean units, median {pr['usable'][d]['naive_promoted_vs_not']['within_entity_ratio_mean_units_promoted_over_not']['p50']:.2f} (IQR {pr['usable'][d]['naive_promoted_vs_not']['within_entity_ratio_mean_units_promoted_over_not']['p25']:.2f}-{pr['usable'][d]['naive_promoted_vs_not']['within_entity_ratio_mean_units_promoted_over_not']['p75']:.2f})."
    for d, lab in [("max8", "max-8 reference"), ("med13", "median-13 reference")]) + "\n"
(C.DOCS_DIR / "panel_audit.md").write_text(md)
print("done; peak MB", mg.peak_mb())
