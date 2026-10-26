"""Step 2, Part C: re-estimate the primary specs on VALIDATION weeks 86-93 alone and compare with train."""
import json
import time

import numpy as np

from price_elasticity import config as C
from price_elasticity.analysis import COM_CTRL, commodity_frame, fit_pair, pooled_commodity
from price_elasticity.commodity import fixed_weights, price_index, product_meta
from price_elasticity.data import add_features, assert_weeks, load_panel, select_primary_products
from price_elasticity.memguard import MemGuard
from price_elasticity.models import SpecLog
from price_elasticity.report import render_validation

T0 = time.time()
mg = MemGuard(C.PROCESSED_DIR / "elasticity_validation_memlog.txt")
mg.start_watchdog()
LO, HI = C.PRIMARY_WEEKS
VLO, VHI = C.VAL_WEEKS
tr = json.loads((C.RESULTS_DIR / "elasticity_train.json").read_text())
log = SpecLog()

# product set and commodity weights come from TRAIN weeks only
train = add_features(load_panel(C.STARTUP_WEEKS[0], HI))
assert_weeks(train, C.STARTUP_WEEKS[0], HI)
core = train[train.week >= LO]
products, _ = select_primary_products(core)
assert len(products) == tr["sample"]["primary_products"], "product set differs from the train run"
prod2com, _ = product_meta()
w = fixed_weights(train, prod2com)
act = price_index(core, w, prod2com).groupby("commodity").size()
keep = act[act >= C.COMMODITY_MIN_ACTIVE_WEEKS].index
del train, core

val = add_features(load_panel(VLO, VHI))
assert_weeks(val, VLO, VHI)
V = {"stage": "validation", "weeks": [VLO, VHI]}
S = val[val.product_id.isin(products)].copy()
V["sample"] = {"rows": int(len(S)), "products": int(S.product_id.nunique()), "weeks": int(S.week.nunique())}
res = fit_pair(S, log, "validation", "primary_secondary", "main", "validation weeks, train primary set")
cdf = commodity_frame(VLO, VHI, price_index(val, w, prod2com), keep_commodities=keep)
assert_weeks(cdf, VLO, VHI)
pooled = pooled_commodity(cdf, log, "validation", "validation weeks, train commodity set")
V["commodity_sample"] = {"commodities": int(cdf.commodity.nunique()), "commodity_weeks": int(len(cdf))}


def cmp(name, t, v):
    if v is None:
        return None
    d = v[0] - t["estimate"]
    z = d / np.hypot(v[1], t["se"])
    ov = not (v[3] < t["ci_low"] or v[2] > t["ci_high"])
    same = np.sign(v[0]) == np.sign(t["estimate"])
    return {"name": name, "train": t["estimate"], "train_lo": t["ci_low"], "train_hi": t["ci_high"], "val": v[0],
            "val_lo": v[2], "val_hi": v[3], "val_se": v[1], "diff": d, "z": z, "same_sign": bool(same), "ci_overlap": bool(ov),
            "verdict": "stable" if (same and ov) else "not stable"}


rows = []
for est in ["ppml", "ols"]:
    rows.append(cmp(f"{est.upper()} log price", tr["primary"][est], res[("primary", est)]["coef"]["lp"] if res[("primary", est)] else None))
    for t in ["x_base", "x_promo"]:
        r = res[("secondary", est)]
        rows.append(cmp(f"{est.upper()} {t}", tr["secondary"][est][t], r["coef"][t] if r and t in r["coef"] else None))
    for t in C.CONTROLS:
        r = res[("primary", est)]
        if r and t in r["coef"] and t in tr["controls"][est]:
            rows.append(cmp(f"{est.upper()} {t}", tr["controls"][est][t], r["coef"][t]))
for est in ["ppml", "ols"]:
    if pooled[est] and tr["commodity_pooled"][est]:
        rows.append(cmp(f"commodity-pooled {est.upper()} log price index", tr["commodity_pooled"][est], pooled[est]["coef"]["lpi"]))
rows = [r for r in rows if r]
V["comparison"] = rows
V["n_total"] = len(rows)
V["n_stable"] = sum(r["verdict"] == "stable" for r in rows)
V["runtime_seconds"] = round(time.time() - T0, 1)
V["peak_memory_mb"] = mg.peak_mb()
(C.RESULTS_DIR / "elasticity_validation_stability.json").write_text(json.dumps(V, indent=2, default=float))
(C.RESULTS_DIR / "elasticity_validation_stability.md").write_text(render_validation(V))
import pandas as pd
old = pd.read_csv(C.RESULTS_DIR / "spec_log.csv")
pd.concat([old[old.stage != "validation"], log.frame()]).to_csv(C.RESULTS_DIR / "spec_log.csv", index=False)
print("done", V["runtime_seconds"], V["peak_memory_mb"])
