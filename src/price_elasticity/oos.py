"""Out-of-sample check with FROZEN train elasticities (see docs/test_protocol.md)."""
import json
import pickle

import numpy as np
import pandas as pd

from . import config as C
from .analysis import commodity_frame, fit_pair
from .commodity import price_index
from .data import add_features, assert_weeks, load_panel

FROZEN_JSON = C.PROCESSED_DIR / "frozen_estimates.json"
FROZEN_PKL = C.PROCESSED_DIR / "frozen_context.pkl"
PROMO_CHANGE = 0.10
STAT_COLS = ["n", "sp", "sa", "spp", "saa", "spa", "sq", "sqq", "sqa", "e_m", "e_0", "e_1", "dn_m", "dok_m", "dn_1", "dok_1"]


def load_frozen():
    ctx = pickle.loads(FROZEN_PKL.read_bytes())
    ctx["frozen"] = json.loads(FROZEN_JSON.read_text())
    return ctx


def _changes(df, ent, price, units, depth):
    """Week-over-week changes for consecutive calendar weeks, plus the lagged relative change (baseline 2)."""
    d = df[[ent, "week", price, units, depth]].sort_values([ent, "week"])
    lag = d.assign(week=d["week"] + 1).rename(columns={price: "p0", units: "u0", depth: "d0"})
    m = d.merge(lag, on=[ent, "week"], how="inner")
    m["dY"] = np.log(m[units]) - np.log(m["u0"])
    m["dX"] = m[price] - m["p0"]
    m["ddepth"] = m[depth] - m["d0"]
    return m[[ent, "week", "dY", "dX", "ddepth"]]


def build_eval_table(level, lo, hi, ctx, allow_test=False):
    """Rows for weeks lo..hi: relative actual (a), relative predicted (p), lagged relative actual (q), promo flag."""
    if level == "product":
        df = add_features(load_panel(lo - 2, hi, allow_test=allow_test))
        df = df[df.product_id.isin(ctx["products"])]
        df["depth"] = df["depth_obs"]
        ent, beta = "product_id", float(ctx["frozen"]["beta_product"])
        ch = _changes(df, ent, "lp", "units", "depth")
        ch["beta"] = beta
    else:
        pl = load_panel(lo - 2, hi, allow_test=allow_test)
        pl = add_features(pl)
        idx = price_index(pl, ctx["weights"], ctx["prod2com"])
        cp = pd.read_parquet(C.PROCESSED_DIR / "panel_commodity.parquet", columns=["commodity", "week", "units", "sales_value", "shelf_value"],
                             filters=[("week", ">=", lo - 2), ("week", "<=", hi), ("non_merchandise", "==", 0)])
        assert_weeks(cp, lo - 2, hi, allow_test=allow_test)
        cp = cp.merge(idx, on=["commodity", "week"])
        cp = cp[cp.commodity.isin(ctx["keep"])]
        cp["depth"] = 1.0 - cp["sales_value"] / cp["shelf_value"]
        ent = "commodity"
        ch = _changes(cp, ent, "lpi", "units", "depth")
        ch["beta"] = ch[ent].map({k: v["shrunk"] for k, v in ctx["frozen"]["commodities"].items()})
        ch = ch.dropna(subset=["beta"])
    ch["dP"] = ch["beta"] * ch["dX"]
    ch["a"] = ch["dY"] - ch.groupby("week")["dY"].transform("mean")
    ch["p"] = ch["dP"] - ch.groupby("week")["dP"].transform("mean")
    prev = ch[[ent, "week", "a"]].assign(week=lambda x: x["week"] + 1).rename(columns={"a": "q"})
    out = ch.merge(prev, on=[ent, "week"], how="left")
    out = out[(out.week >= lo) & (out.week <= hi)]
    assert out.week.min() >= lo and out.week.max() <= hi
    out["promo"] = out["ddepth"].abs() > PROMO_CHANGE
    out = out.rename(columns={ent: "cluster"})
    return out.dropna(subset=["q"]).reset_index(drop=True), int(len(out))


def _stats(g):
    a, p, q = g["a"].to_numpy(), g["p"].to_numpy(), g["q"].to_numpy()
    dm = (a != 0) & (p != 0)
    d1 = (a != 0) & (q != 0)
    return pd.Series({"n": len(g), "sp": p.sum(), "sa": a.sum(), "spp": (p * p).sum(), "saa": (a * a).sum(), "spa": (p * a).sum(),
                      "sq": q.sum(), "sqq": (q * q).sum(), "sqa": (q * a).sum(), "e_m": np.abs(a - p).sum(), "e_0": np.abs(a).sum(),
                      "e_1": np.abs(a - q).sum(), "dn_m": dm.sum(), "dok_m": (np.sign(a[dm]) == np.sign(p[dm])).sum(),
                      "dn_1": d1.sum(), "dok_1": (np.sign(a[d1]) == np.sign(q[d1])).sum()})


def _corr(n, s1, s2, s11, s22, s12):
    den = np.sqrt(max(n * s11 - s1**2, 0) * max(n * s22 - s2**2, 0))
    return (n * s12 - s1 * s2) / den if den > 0 else np.nan


def metrics_from_sums(v):
    s = dict(zip(STAT_COLS, v))
    n = s["n"]
    m = {"corr_model": _corr(n, s["sp"], s["sa"], s["spp"], s["saa"], s["spa"]),
         "corr_last_week": _corr(n, s["sq"], s["sa"], s["sqq"], s["saa"], s["sqa"]),
         "mae_model": s["e_m"] / n, "mae_zero": s["e_0"] / n, "mae_last_week": s["e_1"] / n,
         "dir_model": s["dok_m"] / s["dn_m"] if s["dn_m"] else np.nan,
         "dir_last_week": s["dok_1"] / s["dn_1"] if s["dn_1"] else np.nan}
    m["mae_gain_vs_zero"] = m["mae_zero"] - m["mae_model"]
    m["mae_gain_vs_last_week"] = m["mae_last_week"] - m["mae_model"]
    return m


def evaluate(tab, B=C.BOOTSTRAP_B, seed=C.BOOTSTRAP_SEED):
    """Point estimates and cluster-bootstrap 95% CIs for all / promo-change / no-promo-change rows."""
    codes, uniq = pd.factorize(tab["cluster"])
    G = len(uniq)
    rng = np.random.default_rng(seed)
    draws = [np.bincount(rng.integers(0, G, G), minlength=G) for _ in range(B)]
    out = {}
    for name, mask in [("all", np.ones(len(tab), bool)), ("promo_change_gt_10pct", tab["promo"].to_numpy()),
                       ("no_promo_change", ~tab["promo"].to_numpy())]:
        sub = tab[mask].assign(_c=codes[mask])
        if len(sub) == 0:
            out[name] = {"n_rows": 0}
            continue
        per = sub.groupby("_c")[["a", "p", "q"]].apply(_stats).reindex(range(G)).fillna(0.0)
        M = per.to_numpy()
        point = metrics_from_sums(M.sum(axis=0))
        boots = pd.DataFrame([metrics_from_sums(w @ M) for w in draws])
        out[name] = {"n_rows": int(len(sub)), "n_clusters": int((per["n"] > 0).sum()),
                     "metrics": {k: {"est": float(point[k]), "ci_low": float(boots[k].quantile(0.025)),
                                     "ci_high": float(boots[k].quantile(0.975))} for k in point}}
    return out


def evaluate_window(lo, hi, ctx, allow_test=False):
    res = {"weeks": [lo, hi], "bootstrap": {"B": C.BOOTSTRAP_B, "seed": C.BOOTSTRAP_SEED, "workers": 0},
           "beta_product": ctx["frozen"]["beta_product"],
           "definition": "relative change = week-over-week log change minus the cross-product mean of that week; common sample "
                         "where last week's relative change is defined; promo change = |depth_t - depth_{t-1}| > 0.10"}
    for level in ["product", "commodity"]:
        tab, n_all = build_eval_table(level, lo, hi, ctx, allow_test=allow_test)
        res[level] = {"rows_with_defined_change": n_all, "rows_common_sample": int(len(tab)), **evaluate(tab)}
    return res


def stability_window(lo, hi, ctx, tr, allow_test=False):
    """Re-estimate the primary PPML and OLS log-price coefficients on weeks lo..hi (train product set)."""
    from .models import SpecLog
    df = add_features(load_panel(lo, hi, allow_test=allow_test))
    df = df[df.product_id.isin(ctx["products"])]
    assert_weeks(df, lo, hi, allow_test=allow_test)
    log = SpecLog()
    res = fit_pair(df, log, "window", "primary_secondary", "main", f"weeks {lo}-{hi}")
    rows = []
    for est in ["ppml", "ols"]:
        t = tr["primary"][est]
        r = res[("primary", est)]["coef"]["lp"]
        d = r[0] - t["estimate"]
        z = d / np.hypot(r[1], t["se"])
        same = bool(np.sign(r[0]) == np.sign(t["estimate"]))
        ov = bool(not (r[3] < t["ci_low"] or r[2] > t["ci_high"]))
        rows.append({"name": f"{est.upper()} log price", "train": t["estimate"], "train_lo": t["ci_low"], "train_hi": t["ci_high"],
                     "window": r[0], "window_lo": r[2], "window_hi": r[3], "window_se": r[1], "diff": d, "z": z,
                     "same_sign": same, "ci_overlap": ov, "verdict": "stable" if same and ov else "not stable",
                     "n_obs": res[("primary", est)]["n_obs"]})
    return {"weeks": [lo, hi], "products": int(df.product_id.nunique()), "rows": int(len(df)), "comparison": rows}
