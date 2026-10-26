"""Reference price and discount depth from history strictly before each week."""
import warnings
import numpy as np
import pandas as pd

from . import config


def _to_wide(panel, entity, price_col, weeks):
    ents = pd.Index(panel[entity].unique())
    ei = ents.get_indexer(panel[entity])
    wi = panel["week"].to_numpy() - weeks[0]
    A = np.full((len(ents), len(weeks)), np.nan, dtype="float64")
    A[ei, wi] = panel[price_col].to_numpy()
    return ents, A


def rolling_prior(A, window, how, min_obs):
    """For column j, statistic over columns [j-window, j) only (never column j or later)."""
    n, T = A.shape
    out = np.full((n, T), np.nan)
    for j in range(T):
        lo = max(0, j - window)
        if j - lo == 0:
            continue
        W = A[:, lo:j]
        cnt = np.isfinite(W).sum(axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            stat = np.nanmax(W, axis=1) if how == "max" else np.nanmedian(W, axis=1)
        stat[cnt < min_obs] = np.nan
        out[:, j] = stat
    return out


def discount_depth(price, ref):
    """max(0, 1 - price/ref); null when ref is null or not positive."""
    price = np.asarray(price, dtype="float64")
    ref = np.asarray(ref, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        d = np.maximum(0.0, 1.0 - price / ref)
    d[~(ref > 0)] = np.nan
    return d


def add_reference(panel, entity, price_col="avg_shelf_price",
                  max_window=config.REF_MAX_WINDOW, med_window=config.REF_MEDIAN_WINDOW,
                  min_obs_max=config.MIN_OBS_MAX, min_obs_med=config.MIN_OBS_MEDIAN):
    """Add ref_max8, ref_med13, depth_max8, depth_med13 to a long panel (columns: entity, week, price_col)."""
    panel = panel.copy()
    weeks = np.arange(panel["week"].min(), panel["week"].max() + 1)
    ents, A = _to_wide(panel, entity, price_col, weeks)
    ei = ents.get_indexer(panel[entity])
    wi = panel["week"].to_numpy() - weeks[0]
    for name, win, how, mo in [("max8", max_window, "max", min_obs_max), ("med13", med_window, "median", min_obs_med)]:
        R = rolling_prior(A, win, how, mo)
        panel[f"ref_{name}"] = R[ei, wi]
        panel[f"depth_{name}"] = discount_depth(panel[price_col].to_numpy(), panel[f"ref_{name}"].to_numpy())
    return panel
