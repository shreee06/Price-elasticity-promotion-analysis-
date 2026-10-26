"""Promotion what-if simulator (associations from observational data; revenue only, no cost or margin)."""
import numpy as np
import pandas as pd

from . import config as C

Z95 = 1.959964


def load_tables():
    e = pd.read_csv(C.RESULTS_DIR / "commodity_elasticities_train.csv")
    r = pd.read_csv(C.RESULTS_DIR / "commodity_depth_ranges.csv")
    t = e.merge(r, on="label")
    t["ci_low"] = t["shrunk"] - Z95 * t["shrunk_se"]
    t["ci_high"] = t["shrunk"] + Z95 * t["shrunk_se"]
    t["reliable"] = t["ci_high"] < 0   # negative and interval excludes 0
    t["z"] = t["shrunk"].abs() / t["shrunk_se"]
    return t.set_index("label")


def _ratio(depth, beta, extra=0.0):
    return (1.0 - depth) ** (beta + extra)


def simulate(label, depth, table):
    """Predicted change in units and revenue for a discount of `depth` vs no discount, constant-elasticity form:
    units ratio = (1 - depth) ** beta, revenue ratio = (1 - depth) ** (1 + beta).
    The interval maps the 95% interval of the (shrunk) elasticity through this monotone formula.
    Raises ValueError if depth lies outside the commodity's observed 5th-95th percentile range."""
    row = table.loc[label]
    if not (row["p05"] <= depth <= row["p95"]):
        raise ValueError(f"depth {depth:.3f} outside observed range [{row['p05']:.3f}, {row['p95']:.3f}] for {label}")
    b, lo, hi = row["shrunk"], row["ci_low"], row["ci_high"]
    out = {"label": label, "department": row["department"], "depth": float(depth), "elasticity": float(b),
           "elasticity_ci": [float(lo), float(hi)], "reliable": bool(row["reliable"]),
           "observed_range": [float(row["p05"]), float(row["p95"])]}
    for name, extra in [("units", 0.0), ("revenue", 1.0)]:
        r = sorted([_ratio(depth, lo, extra), _ratio(depth, hi, extra)])
        out[f"{name}_change_pct"] = float(100 * (_ratio(depth, b, extra) - 1))
        out[f"{name}_change_pct_ci"] = [float(100 * (r[0] - 1)), float(100 * (r[1] - 1))]
    if not out["reliable"]:
        out["note"] = "not reliable: elasticity is non-negative or its interval spans 0; not ranked"
    return out


def top_reliable(table, n=5, example_depth=0.20):
    """Reliable commodities ranked by |elasticity| / SE; example depth clipped into each commodity's observed range."""
    rel = table[table["reliable"]].sort_values("z", ascending=False).head(n)
    return [simulate(lab, float(np.clip(example_depth, r["p05"], r["p95"])), table) for lab, r in rel.iterrows()]
