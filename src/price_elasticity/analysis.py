"""Shared specification runners for the train and validation scripts."""
import pandas as pd

from . import config as C
from .data import assert_weeks
from .models import run_and_log

PRIMARY = ["lp"]
SECONDARY = ["x_base", "x_promo"]
COM_CTRL = ["share_stores_display", "share_stores_mailer", "share_units_coupon"]


def fit_pair(df, log, stage, group, spec, sample, ctrl=None, yp="units", yo="ly"):
    """Run primary and secondary specs with both estimators. Returns {(kind, estimator): result}."""
    ctrl = C.CONTROLS if ctrl is None else ctrl
    out = {}
    for kind, terms in [("primary", PRIMARY), ("secondary", SECONDARY)]:
        for est, y in [("ppml", yp), ("ols", yo)]:
            out[(kind, est)] = run_and_log(log, df, y, terms + ctrl, est, stage, group, f"{spec}:{kind}", sample)
    return out


def commodity_frame(lo, hi, index_df, keep_commodities=None):
    """Commodity x week outcomes/controls merged with the fixed-weight price index."""
    cp = pd.read_parquet(C.PROCESSED_DIR / "panel_commodity.parquet",
                         columns=["commodity", "week", "units"] + COM_CTRL,
                         filters=[("week", ">=", lo), ("week", "<=", hi), ("non_merchandise", "==", 0)])
    assert_weeks(cp, lo, hi)
    cp = cp.merge(index_df, on=["commodity", "week"], how="inner")
    if keep_commodities is not None:
        cp = cp[cp.commodity.isin(keep_commodities)]
    import numpy as np
    cp["ly"] = np.log(cp["units"])
    return cp


def pooled_commodity(cdf, log, stage, sample):
    out = {}
    for est, y in [("ppml", "units"), ("ols", "ly")]:
        out[est] = run_and_log(log, cdf, y, ["lpi"] + COM_CTRL, est, stage, "commodity_pooled", "commodity_pooled", sample,
                               cluster="commodity", fe=("commodity", "week"))
    return out
