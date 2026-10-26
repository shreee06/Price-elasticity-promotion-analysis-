"""Synthetic-data tests only; no dunnhumby data is needed."""
import numpy as np
import pandas as pd
import pytest

from price_elasticity.panel import aggregate_sales
from price_elasticity.price import (add_row_values, clean_transactions, paid_price_unit, shelf_price_unit)
from price_elasticity.reference import add_reference


def synth_panel(seed=0, n_ent=6, n_weeks=30, gap_prob=0.2):
    rng = np.random.default_rng(seed)
    rows = []
    for e in range(n_ent):
        for w in range(1, n_weeks + 1):
            if rng.random() > gap_prob:
                rows.append((e, w, round(float(rng.uniform(1, 5)), 2)))
    return pd.DataFrame(rows, columns=["product_id", "week", "avg_shelf_price"])


def test_reference_ignores_current_and_future_weeks():
    p = synth_panel()
    base = add_reference(p, "product_id")
    t0 = 18
    alt = p.copy()
    alt.loc[alt.week >= t0, "avg_shelf_price"] *= 7.3
    alt = add_reference(alt, "product_id")
    m = base.merge(alt, on=["product_id", "week"], suffixes=("_a", "_b"))
    early = m[m.week <= t0]  # reference at t0 only uses weeks < t0
    for c in ["ref_max8", "ref_med13"]:
        a, b = early[f"{c}_a"].to_numpy(), early[f"{c}_b"].to_numpy()
        assert np.array_equal(np.isnan(a), np.isnan(b))
        assert np.allclose(a[~np.isnan(a)], b[~np.isnan(b)])
    # and the reference really changes later, so the test is not vacuous
    late = m[m.week >= t0 + 9]
    assert not np.allclose(late["ref_max8_a"].fillna(-1), late["ref_max8_b"].fillna(-1))


def test_reference_values_hand_checked():
    p = pd.DataFrame({"product_id": 1, "week": np.arange(1, 11), "avg_shelf_price": [2, 4, 3, 5, 4, 2, 3, 4, 5, 1.0]})
    r = add_reference(p, "product_id").set_index("week")
    assert r.loc[6, "ref_max8"] == 5          # max of weeks 1-5
    assert r.loc[10, "ref_max8"] == 5         # max of weeks 2-9
    assert r.loc[10, "ref_med13"] == 4        # median of weeks 1-9: [2,4,3,5,4,2,3,4,5] -> 4
    assert np.isnan(r.loc[3, "ref_max8"])     # only 2 prior weeks (< MIN_OBS_MAX)
    assert r.loc[10, "depth_max8"] == pytest.approx(1 - 1 / 5)


def test_depth_bounds_and_null_without_history():
    p = add_reference(synth_panel(seed=3, n_ent=20, n_weeks=40), "product_id")
    for d in ["max8", "med13"]:
        dep = p[f"depth_{d}"]
        assert (dep.dropna() >= 0).all() and (dep.dropna() < 1).all()
        assert dep[p[f"ref_{d}"].isna()].isna().all()
    first = p[p.week == 1]
    assert first["depth_max8"].isna().all() and first["depth_med13"].isna().all()
    assert p["depth_max8"].isna().any() and p["depth_max8"].notna().any()


def test_shelf_and_paid_formula_hand_calculated():
    # no coupon: shelf = 1.39 + 0.60 = 1.99
    assert shelf_price_unit(1.39, -0.60, 0.0, 1) == pytest.approx(1.99)
    # manufacturer coupon: SALES_VALUE 2.99, retail -1.00, coupon -1.00 -> shelf 3.99, paid 1.99
    assert shelf_price_unit(2.99, -1.00, 0.0, 1) == pytest.approx(3.99)
    assert paid_price_unit(2.99, -1.00, 1) == pytest.approx(1.99)
    # coupon + match, quantity 1: shelf 1.10+0.69+0.40 = 2.19; paid 1.10-0.40 = 0.70
    assert shelf_price_unit(1.10, -0.69, -0.40, 1) == pytest.approx(2.19)
    assert paid_price_unit(1.10, -0.40, 1) == pytest.approx(0.70)
    # quantity 3: shelf (2.12+0.90+0.25)/3, paid (2.12-0.75)/3
    assert shelf_price_unit(2.12, -0.90, -0.25, 3) == pytest.approx(3.27 / 3)
    assert paid_price_unit(2.12, -0.75, 3) == pytest.approx(1.37 / 3)
    # paid never exceeds shelf when discounts are non-positive
    assert paid_price_unit(2.99, -1.0, 1) <= shelf_price_unit(2.99, -1.0, 0.0, 1)


def synth_tx():
    rows = [  # hh, product, store, week, qty, sales, retail, coupon, match
        (1, 10, 100, 1, 1, 2.99, -1.00, -1.00, 0.0),
        (2, 10, 100, 1, 2, 5.00, 0.0, 0.0, 0.0),
        (2, 10, 101, 1, 1, 1.10, -0.69, -0.40, -0.40),
        (3, 11, 100, 1, 3, 2.12, -0.90, -0.75, -0.25),
        (1, 10, 100, 2, 1, 3.99, 0.0, 0.0, 0.0),
        (1, 11, 101, 2, 0, 0.0, 0.0, 0.0, 0.0),     # QUANTITY = 0 -> dropped
        (1, 11, 101, 2, 1, 0.0, -1.0, 0.0, 0.0),    # SALES_VALUE = 0 -> dropped
        (4, 11, 101, 2, 2, 4.00, -0.50, 0.0, 0.0),
    ]
    return pd.DataFrame(rows, columns=["household_key", "PRODUCT_ID", "STORE_ID", "WEEK_NO", "QUANTITY", "SALES_VALUE",
                                       "RETAIL_DISC", "COUPON_DISC", "COUPON_MATCH_DISC"])


def test_panel_reconciles_exactly_to_source_rows():
    tx = synth_tx()
    clean, counts = clean_transactions(tx)
    assert counts["rows_dropped"] == 2 and counts["rows_kept"] == 6
    clean = add_row_values(clean)
    pan = aggregate_sales(clean, "PRODUCT_ID", "product_id")
    assert pan.units.sum() == clean.QUANTITY.sum() == tx.loc[tx.QUANTITY > 0, "QUANTITY"].sum() - 1  # the Q=1,S=0 row is dropped
    assert round(pan.sales_value.sum() * 100) == round(clean.SALES_VALUE.sum() * 100)
    row = pan[(pan.product_id == 10) & (pan.week == 1)].iloc[0]
    assert row.units == 4 and row.n_transactions == 3 and row.n_households == 2 and row.n_stores == 2
    assert row.avg_shelf_price == pytest.approx((3.99 + 5.00 + 2.19) / 4)
    assert row.avg_paid_price == pytest.approx((1.99 + 5.00 + 0.70) / 4)
    assert row.share_units_retail_disc == pytest.approx(2 / 4)
    # commodity-style regrouping over a different key also reconciles
    clean["grp"] = "all"
    com = aggregate_sales(clean, "grp", "commodity")
    assert com.units.sum() == pan.units.sum() and round(com.sales_value.sum() * 100) == round(pan.sales_value.sum() * 100)
