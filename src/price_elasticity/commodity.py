"""Commodity-level fixed-weight price index, per-commodity Poisson fits, empirical-Bayes shrinkage."""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from . import config as C


def product_meta():
    p = pd.read_parquet(C.PROCESSED_DIR / "product.parquet", columns=["PRODUCT_ID", "DEPARTMENT", "COMMODITY_DESC"])
    p["DEPARTMENT"] = p["DEPARTMENT"].astype(str)
    p["COMMODITY_DESC"] = p["COMMODITY_DESC"].astype(str)
    p = p.rename(columns={"PRODUCT_ID": "product_id", "COMMODITY_DESC": "commodity", "DEPARTMENT": "department"})
    dept = (p.groupby(["commodity", "department"]).size().rename("n").reset_index()
            .sort_values(["commodity", "n", "department"], ascending=[True, False, True]).drop_duplicates("commodity"))
    return p[["product_id", "commodity"]], dept.set_index("commodity")["department"]


def fixed_weights(train_df, prod2com):
    """Product weight = share of the commodity's units over the given (train) weeks."""
    u = train_df.groupby("product_id")["units"].sum().rename("u").reset_index().merge(prod2com, on="product_id")
    u["w"] = u["u"] / u.groupby("commodity")["u"].transform("sum")
    return u.set_index("product_id")["w"]


def price_index(df, weights, prod2com):
    """log P_ct = sum_i w_i log p_it / sum_i w_i over products observed in the week (weights fixed)."""
    d = df[["product_id", "week", "lp"]].merge(prod2com, on="product_id")
    d["w"] = d["product_id"].map(weights)
    d = d.dropna(subset=["w"])
    d["wl"] = d["w"] * d["lp"]
    g = d.groupby(["commodity", "week"])
    out = (g["wl"].sum() / g["w"].sum()).rename("lpi").reset_index()
    return out


def eb_shrink(est, se):
    """DerSimonian-Laird random-effects mean/variance and shrunk estimates with posterior SEs."""
    est, se = np.asarray(est, float), np.asarray(se, float)
    w = 1 / se**2
    mu_fe = (w * est).sum() / w.sum()
    Q = (w * (est - mu_fe) ** 2).sum()
    c = w.sum() - (w**2).sum() / w.sum()
    tau2 = max(0.0, (Q - (len(est) - 1)) / c)
    wr = 1 / (se**2 + tau2)
    mu = (wr * est).sum() / wr.sum()
    B = tau2 / (tau2 + se**2)
    return mu + B * (est - mu), np.sqrt(B * se**2), float(mu), float(tau2)


def bh_reject(p, q=0.05):
    p = np.asarray(p, float)
    n = len(p)
    o = np.argsort(p)
    ok = p[o] <= q * (np.arange(1, n + 1) / n)
    k = np.nonzero(ok)[0].max() + 1 if ok.any() else 0
    r = np.zeros(n, bool)
    r[o[:k]] = True
    return r


def per_commodity_fits(cdf, hh):
    """cdf: commodity, week, units, lpi, share_stores_display, share_stores_mailer, share_units_coupon."""
    rows, fails = [], []
    for com, g in cdf.groupby("commodity"):
        g = g.sort_values("week")
        t = (g["week"].to_numpy() - C.PRIMARY_WEEKS[0]) / (C.PRIMARY_WEEKS[1] - C.PRIMARY_WEEKS[0])
        X = pd.DataFrame({"const": 1.0, "lpi": g["lpi"].to_numpy(), "sd": g["share_stores_display"].to_numpy(),
                          "sm": g["share_stores_mailer"].to_numpy(), "cp": g["share_units_coupon"].to_numpy(),
                          "t": t, "t2": t**2, "t3": t**3})
        X = X.loc[:, [c for c in X.columns if c == "const" or X[c].std() > 1e-12]]
        if "lpi" not in X.columns:
            fails.append((com, "no variation in price index"))
            continue
        off = np.log(hh.reindex(g["week"]).to_numpy())
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = sm.GLM(g["units"].to_numpy(), X, family=sm.families.Poisson(), offset=off).fit(
                    cov_type="HAC", cov_kwds={"maxlags": C.HAC_LAGS})
            b, se = float(m.params["lpi"]), float(m.bse["lpi"])
            if not np.isfinite(b) or not np.isfinite(se) or se <= 0:
                fails.append((com, "non-finite estimate"))
                continue
            rows.append({"commodity": com, "n_weeks": len(g), "est": b, "se": se,
                         "p0": 2 * stats.norm.sf(abs(b / se)), "pm1": 2 * stats.norm.sf(abs((b + 1) / se))})
        except Exception as e:
            fails.append((com, f"{type(e).__name__}"))
    return pd.DataFrame(rows), fails
