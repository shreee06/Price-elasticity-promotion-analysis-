"""Synthetic-data tests for the elasticity step."""
import numpy as np
import pandas as pd
import pytest

from price_elasticity import config as C
from price_elasticity.commodity import eb_shrink, fixed_weights, price_index
from price_elasticity.data import PANEL_COLS, add_leads, assert_weeks, load_panel, select_primary_products
from price_elasticity.models import cluster_bootstrap, fit


def sim_panel(seed=0, n=300, T=40, beta=-1.5, count=True, lead_effect=0.0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"product_id": np.repeat(np.arange(n), T), "week": np.tile(np.arange(1, T + 1), n)})
    a = rng.normal(0, 1, n)[d.product_id]
    w = rng.normal(0, 0.3, T)[d.week - 1]
    lp = np.zeros(len(d))
    for p in range(n):  # persistent prices so leads are correlated with current price
        e = rng.normal(0, 0.15, T)
        x = np.zeros(T)
        for t in range(1, T):
            x[t] = 0.6 * x[t - 1] + e[t]
        lp[p * T:(p + 1) * T] = x
    d["lp"] = lp
    d["z"] = rng.normal(size=len(d))
    mu = 3 + a + w + beta * d.lp
    if count:
        d["units"] = rng.poisson(np.exp(mu))
        d = d[d.units > 0].copy()
        d["ly"] = np.log(d.units)
    else:
        d["ly"] = mu + rng.normal(0, 0.3, len(d))
        d["units"] = np.exp(d.ly)
    return d


def test_ppml_recovers_known_elasticity():
    d = sim_panel(count=True)
    res, n, ncl, _ = fit(d, "units", ["lp", "z"], "ppml")
    b, se, lo, hi = res["lp"]
    assert abs(b + 1.5) < 0.05 and lo < -1.5 < hi
    assert ncl == d.product_id.nunique()


def test_ols_recovers_known_elasticity():
    d = sim_panel(count=False, seed=1)
    res, *_ = fit(d, "ly", ["lp", "z"], "ols")
    b, se, lo, hi = res["lp"]
    assert abs(b + 1.5) < 0.05 and lo < -1.5 < hi


def test_fixed_weight_index_ignores_mix_shift():
    rows = []
    for w in range(1, 13):
        share_a = 0.1 + 0.07 * w  # units shift from product B to A, prices constant
        rows += [(1, w, 10 * share_a, np.log(2.0)), (2, w, 10 * (1 - share_a), np.log(8.0))]
    df = pd.DataFrame(rows, columns=["product_id", "week", "units", "lp"])
    p2c = pd.DataFrame({"product_id": [1, 2], "commodity": ["x", "x"]})
    w = fixed_weights(df, p2c)
    assert w.sum() == pytest.approx(1.0)
    idx = price_index(df, w, p2c)
    assert idx.lpi.nunique() == 1 or np.ptp(idx.lpi.to_numpy()) < 1e-12
    # a unit-weighted average price DOES move with the mix (this is what the index avoids)
    naive = df.assign(v=np.exp(df.lp) * df.units).groupby("week").v.sum() / df.groupby("week").units.sum()
    assert np.ptp(naive.to_numpy()) > 1.0
    # a genuine price rise in one product moves the index by weight * log change
    df2 = df.copy()
    df2.loc[(df2.product_id == 1) & (df2.week == 5), "lp"] += np.log(2)
    idx2 = price_index(df2, w, p2c).set_index("week").lpi
    assert idx2[5] - idx2[4] == pytest.approx(w[1] * np.log(2))


def test_lead_logic_and_placebo():
    d = pd.DataFrame({"product_id": [1, 1, 1, 1, 2, 2], "week": [1, 2, 3, 5, 1, 2], "lp": [0.1, 0.2, 0.3, 0.5, 1.0, 2.0]})
    out = add_leads(d).set_index(["product_id", "week"])
    assert out.loc[(1, 1), "lead1"] == 0.2 and out.loc[(1, 1), "lead2"] == 0.3
    assert np.isnan(out.loc[(1, 3), "lead1"]) and out.loc[(1, 3), "lead2"] == 0.5   # week 4 missing -> NaN lead1
    assert np.isnan(out.loc[(2, 2), "lead1"])
    # units depend on current price only: leads should not predict current units
    s = sim_panel(seed=4, n=400, T=40)
    s = add_leads(s[["product_id", "week", "lp", "units", "ly", "z"]]).dropna(subset=["lead1", "lead2"])
    res, *_ = fit(s, "units", ["lp", "lead1", "lead2"], "ppml")
    for t in ["lead1", "lead2"]:
        b, se, *_ = res[t]
        assert abs(b) < 3 * se and abs(b) < 0.1
    assert abs(res["lp"][0] + 1.5) < 0.1


def test_no_validation_or_test_rows_reach_train(tmp_path):
    n = 101
    rows = pd.DataFrame({c: np.ones(n) for c in PANEL_COLS})
    rows["week"] = np.arange(1, n + 1)
    rows["product_id"] = 1
    rows["non_merchandise"] = 0
    p = tmp_path / "panel.parquet"
    rows.to_parquet(p)
    df = load_panel(C.PRIMARY_WEEKS[0], C.PRIMARY_WEEKS[1], path=p)
    assert df.week.min() == 8 and df.week.max() == 85
    assert not df.week.between(*C.VAL_WEEKS).any() and not df.week.between(*C.TEST_WEEKS).any()
    with pytest.raises(AssertionError):
        assert_weeks(rows[rows.week <= 90], 8, 85)
    with pytest.raises(AssertionError):
        assert_weeks(rows[rows.week.between(94, 101)], 86, 101)  # inside range but test weeks
    assert C.TRAIN_WEEKS[1] < C.VAL_WEEKS[0] and C.VAL_WEEKS[1] < C.TEST_WEEKS[0]


def test_bootstrap_and_clustering_reproducible():
    d = sim_panel(seed=7, n=60, T=25)
    a, ma = cluster_bootstrap(d, "units", ["lp"], "ppml", 12, 123, n_jobs=1)
    b, mb = cluster_bootstrap(d, "units", ["lp"], "ppml", 12, 123, n_jobs=1)
    c, _ = cluster_bootstrap(d, "units", ["lp"], "ppml", 12, 124, n_jobs=1)
    assert a == b and ma == mb
    assert a["lp"]["boot_se"] != c["lp"]["boot_se"]
    par, _ = cluster_bootstrap(d, "units", ["lp"], "ppml", 12, 123, n_jobs=2, tasks_per_child=6)  # subprocess workers
    assert par["lp"]["boot_se"] == pytest.approx(a["lp"]["boot_se"], rel=1e-8)
    par, _ = cluster_bootstrap(d, "units", ["lp"], "ppml", 12, 123, n_jobs=2, tasks_per_child=6)
    assert par == a  # independent of the number of worker processes
    r1 = fit(d, "units", ["lp"], "ppml")[0]["lp"]
    r2 = fit(d, "units", ["lp"], "ppml")[0]["lp"]
    assert r1 == r2
    # clustered SE differs from iid SE when errors are clustered
    assert fit(d, "units", ["lp"], "ppml", cluster=None)[0]["lp"][1] != r1[1]


def test_eb_shrinkage():
    est = np.array([-3.0, -1.0, 0.0, -2.0])
    se = np.array([2.0, 0.1, 2.0, 0.1])
    sh, sse, mu, tau2 = eb_shrink(est, se)
    assert abs(sh[0] - mu) < abs(est[0] - mu)          # noisy estimates move toward the mean
    assert abs(sh[1] - est[1]) < 0.05                  # precise ones barely move
    sh2, _, _, t2 = eb_shrink(np.array([-1.0, -1.0, -1.0]), np.array([0.5, 0.5, 0.5]))
    assert t2 == 0 and np.allclose(sh2, -1.0)


def test_primary_selection_rule():
    rows = []
    for pid, (n_hi, n_lo) in {1: (10, 25), 2: (5, 40), 3: (10, 10), 4: (12, 20)}.items():
        dep = [0.2] * n_hi + [0.0] * n_lo
        rows += [(pid, w, d) for w, d in enumerate(dep)]
    df = pd.DataFrame(rows, columns=["product_id", "week", "depth_obs"])
    ids, counts = select_primary_products(df)
    assert sorted(ids) == [1, 4]  # 2: too few promo weeks; 3: fewer than 30 active weeks
