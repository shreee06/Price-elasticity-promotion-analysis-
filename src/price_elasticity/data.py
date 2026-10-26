"""Window-safe loaders and feature construction for the elasticity step."""
import numpy as np
import pandas as pd

from . import config as C

PANEL_COLS = ["product_id", "week", "units", "sales_value", "shelf_value", "share_units_coupon", "share_stores_display",
              "share_stores_mailer", "any_display", "any_mailer", "depth_max8", "depth_med13"]


def assert_weeks(df, lo, hi, col="week", allow_test=False):
    """Hard guard: every row must lie inside [lo, hi]; also never inside the test window unless allow_test
    (only the one-time test script sets it)."""
    w = df[col]
    assert len(df) == 0 or (w.min() >= lo and w.max() <= hi), f"weeks outside [{lo},{hi}]: {w.min()}..{w.max()}"
    if not allow_test:
        assert not ((w >= C.TEST_WEEKS[0]) & (w <= C.TEST_WEEKS[1])).any(), "TEST weeks reached estimation"


def load_panel(lo, hi, path=None, merchandise_only=True, allow_test=False):
    """Read panel rows with lo <= week <= hi (filter applied at read time, so other weeks are never loaded)."""
    path = path or (C.PROCESSED_DIR / "panel.parquet")
    flt = [("week", ">=", lo), ("week", "<=", hi)]
    if merchandise_only:
        flt.append(("non_merchandise", "==", 0))
    df = pd.read_parquet(path, columns=PANEL_COLS, filters=flt)
    assert_weeks(df, lo, hi, allow_test=allow_test)
    return df


def add_features(df):
    df = df.copy()
    df["lp"] = np.log(df["sales_value"] / df["units"])
    df["x_base"] = np.log(df["shelf_value"] / df["units"])
    df["x_promo"] = np.log(df["sales_value"] / df["shelf_value"])
    df["depth_obs"] = 1.0 - df["sales_value"] / df["shelf_value"]
    df["ly"] = np.log(df["units"])
    for c in ["any_display", "any_mailer"]:
        df[c] = df[c].astype("float64")
    return df


def select_primary_products(df):
    """Products with >= 30 active weeks, >= 8 weeks depth > 10% and >= 8 weeks depth <= 10% inside df's window.
    Returns (product ids, filter-chain counts)."""
    g = df.groupby("product_id")
    act = g.size()
    hi = (df["depth_obs"] > C.PROMO_DEPTH).groupby(df["product_id"]).sum()
    lo = (df["depth_obs"] <= C.PROMO_DEPTH).groupby(df["product_id"]).sum()
    ok1 = act[act >= C.MIN_ACTIVE_WEEKS_PRIMARY].index
    ok2 = hi.index[(hi >= C.MIN_PROMO_WEEKS) & hi.index.isin(ok1)]
    ok3 = lo.index[(lo >= C.MIN_NONPROMO_WEEKS) & lo.index.isin(ok2)]
    counts = {"merchandise_products_with_rows_in_window": int(len(act)),
              "merchandise_product_weeks_in_window": int(len(df)),
              "products_ge_30_active_weeks": int(len(ok1)),
              "plus_ge_8_weeks_depth_gt_10pct": int(len(ok2)),
              "plus_ge_8_weeks_depth_le_10pct (primary set)": int(len(ok3))}
    return np.asarray(ok3), counts


def add_leads(df, n=2):
    """lp_lead{k} = log price paid k calendar weeks later for the same product (NaN if not observed)."""
    out = df.copy()
    key = df[["product_id", "week", "lp"]]
    for k in range(1, n + 1):
        sh = key.assign(week=key["week"] - k).rename(columns={"lp": f"lead{k}"})
        out = out.merge(sh, on=["product_id", "week"], how="left")
    return out


def add_reference_terms(df, which):
    """Reference-price version of the split: x_promo = log(1 - depth_ref), x_base = lp - x_promo."""
    df = df.dropna(subset=[f"depth_{which}"]).copy()
    df["x_promo_r"] = np.log(1.0 - df[f"depth_{which}"])
    df["x_base_r"] = df["lp"] - df["x_promo_r"]
    return df


def weekly_households(hi):
    w = pd.read_csv(C.RESULTS_DIR / "weekly_volume.csv", usecols=["week", "active_households"])
    w = w[w.week <= hi].set_index("week")["active_households"]
    assert w.index.max() <= hi
    return w
