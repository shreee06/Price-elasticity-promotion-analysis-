"""Re-derive the FROZEN train estimates (weeks <= 85 only) and check them against the committed step-2 files.

Writes untracked data/processed/frozen_estimates.json + frozen_context.pkl, and the aggregate, anonymised
evals/results/commodity_depth_ranges.csv used by the what-if simulator.
"""
import hashlib
import json
import pickle

import numpy as np
import pandas as pd

from price_elasticity import config as C
from price_elasticity.analysis import commodity_frame
from price_elasticity.commodity import eb_shrink, fixed_weights, per_commodity_fits, price_index, product_meta
from price_elasticity.data import add_features, assert_weeks, load_panel, select_primary_products, weekly_households
from price_elasticity.memguard import MemGuard
from price_elasticity.oos import FROZEN_JSON, FROZEN_PKL

mg = MemGuard(C.PROCESSED_DIR / "freeze_memlog.txt")
mg.start_watchdog()
LO, HI = C.PRIMARY_WEEKS
R = C.RESULTS_DIR
tr = json.loads((R / "elasticity_train.json").read_text())
csv = pd.read_csv(R / "commodity_elasticities_train.csv")

train = add_features(load_panel(C.STARTUP_WEEKS[0], HI))
assert_weeks(train, C.STARTUP_WEEKS[0], HI)
core = train[train.week >= LO]
products, _ = select_primary_products(core)
assert len(products) == tr["sample"]["primary_products"]
prod2com, dept = product_meta()
w = fixed_weights(train, prod2com)
cp_all = commodity_frame(LO, HI, price_index(core, w, prod2com))
act = cp_all.groupby("commodity").size()
keep = list(act[act >= C.COMMODITY_MIN_ACTIVE_WEEKS].index)
cdf = cp_all[cp_all.commodity.isin(keep)]
pc, fails = per_commodity_fits(cdf, weekly_households(HI))
shr, shr_se, mu, tau2 = eb_shrink(pc.est, pc.se)
pc["shrunk"], pc["shrunk_se"] = shr, shr_se
labels = np.random.default_rng(C.BOOTSTRAP_SEED).permutation(len(pc))
pc["label"] = [f"C{int(i):03d}" for i in labels]
pc["department"] = pc.commodity.map(dept)

chk = pc.merge(csv, on="label", suffixes=("", "_c"))
assert len(chk) == len(csv) == len(pc) == tr["commodity_each"]["commodities_fitted"]
for c in ["est", "se", "shrunk", "shrunk_se"]:
    assert np.allclose(chk[c], chk[c + "_c"], rtol=0, atol=1e-9), f"{c} differs from committed step-2 file"
assert (chk.department == chk.department_c).all()

frozen = {"source_commit": "687875d", "beta_product": tr["primary"]["ppml"]["estimate"],
          "sha256_elasticity_train_json": hashlib.sha256((R / "elasticity_train.json").read_bytes()).hexdigest(),
          "sha256_commodity_csv": hashlib.sha256((R / "commodity_elasticities_train.csv").read_bytes()).hexdigest(),
          "commodities": {r.commodity: {"label": r.label, "shrunk": float(r.shrunk), "shrunk_se": float(r.shrunk_se),
                                        "est": float(r.est), "se": float(r.se), "department": r.department} for r in pc.itertuples()}}
FROZEN_JSON.write_text(json.dumps(frozen))
FROZEN_PKL.write_bytes(pickle.dumps({"products": np.asarray(products), "weights": w, "prod2com": prod2com, "keep": keep}))

# observed discount-depth range per commodity (train weeks 8-85), anonymised
cp = pd.read_parquet(C.PROCESSED_DIR / "panel_commodity.parquet", columns=["commodity", "week", "sales_value", "shelf_value"],
                     filters=[("week", ">=", LO), ("week", "<=", HI), ("non_merchandise", "==", 0)])
assert_weeks(cp, LO, HI)
cp = cp[cp.commodity.isin(keep)]
cp["depth"] = (1.0 - cp.sales_value / cp.shelf_value).clip(lower=0)
g = cp.groupby("commodity")["depth"]
rng = pd.DataFrame({"p05": g.quantile(0.05), "p50": g.median(), "p95": g.quantile(0.95), "n_weeks": g.size()}).reset_index()
rng["label"] = rng.commodity.map({k: v["label"] for k, v in frozen["commodities"].items()})
rng.drop(columns="commodity").sort_values("label").to_csv(R / "commodity_depth_ranges.csv", index=False)
mg.stage(f"frozen {len(pc)} commodities, {len(products)} products; matches committed step-2 files")
