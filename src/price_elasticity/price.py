"""Row-level price definitions for dunnhumby transactions.

Sign convention (verified on the data, see docs/panel_audit.md): RETAIL_DISC, COUPON_MATCH_DISC and
COUPON_DISC are stored as NEGATIVE numbers. SALES_VALUE is the amount after the retail (loyalty) discount
and the coupon match discount, but BEFORE the manufacturer coupon.
"""
import numpy as np

RETAIL_EPS = 0.005  # a retail discount counts only if it is below -0.5 cents (filters float noise)


def shelf_value(sales_value, retail_disc, coupon_match_disc):
    """Total value at shelf price before any discount: SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC)."""
    return sales_value - (retail_disc + coupon_match_disc)


def paid_value(sales_value, coupon_disc):
    """Total paid after the manufacturer coupon: SALES_VALUE + COUPON_DISC (COUPON_DISC is negative).

    Equivalent to shelf_value + RETAIL_DISC + COUPON_MATCH_DISC + COUPON_DISC. Note that the formula
    SALES_VALUE - (RETAIL_DISC + COUPON_MATCH_DISC + COUPON_DISC) would ADD the coupon back, yielding a price
    above shelf price; it is not used.
    """
    return sales_value + coupon_disc


def shelf_price_unit(sales_value, retail_disc, coupon_match_disc, quantity):
    return shelf_value(sales_value, retail_disc, coupon_match_disc) / quantity


def paid_price_unit(sales_value, coupon_disc, quantity):
    return paid_value(sales_value, coupon_disc) / quantity


def clean_transactions(tx):
    """Drop rows with QUANTITY <= 0 or SALES_VALUE <= 0 (unit price undefined). Returns (clean, counts)."""
    bad_q = tx["QUANTITY"] <= 0
    bad_s = tx["SALES_VALUE"] <= 0
    counts = {
        "rows_total": int(len(tx)),
        "quantity_le_0": int(bad_q.sum()),
        "sales_value_le_0": int(bad_s.sum()),
        "both": int((bad_q & bad_s).sum()),
        "rows_dropped": int((bad_q | bad_s).sum()),
        "units_dropped": int(tx.loc[bad_q | bad_s, "QUANTITY"].sum()),
        "sales_value_dropped": float(tx.loc[bad_q | bad_s, "SALES_VALUE"].sum()),
    }
    out = tx.loc[~(bad_q | bad_s)].copy()
    counts["rows_kept"] = int(len(out))
    return out, counts


def add_row_values(df):
    """Add row-level value columns used for aggregation (all totals, not per unit)."""
    df["shelf_value"] = shelf_value(df["SALES_VALUE"], df["RETAIL_DISC"], df["COUPON_MATCH_DISC"])
    df["paid_value"] = paid_value(df["SALES_VALUE"], df["COUPON_DISC"])
    df["retail_disc_amt"] = np.where(df["RETAIL_DISC"] < -RETAIL_EPS, -df["RETAIL_DISC"], 0.0)
    q = df["QUANTITY"]
    df["units_retail_disc"] = np.where(df["retail_disc_amt"] > 0, q, 0)
    df["units_coupon"] = np.where(df["COUPON_DISC"] < 0, q, 0)
    df["units_match"] = np.where(df["COUPON_MATCH_DISC"] < 0, q, 0)
    df["coupon_amt"] = -df["COUPON_DISC"]
    return df
