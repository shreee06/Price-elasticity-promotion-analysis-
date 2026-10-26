"""Weekly price/promotion panel builders (product x week and commodity x week, summed over stores)."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SUM_COLS = ["QUANTITY", "SALES_VALUE", "shelf_value", "paid_value", "retail_disc_amt", "units_retail_disc",
            "units_coupon", "units_match", "coupon_amt"]


def aggregate_sales(clean, key, key_name):
    """Aggregate cleaned, value-augmented transactions to key x week."""
    g = clean.groupby([key, "WEEK_NO"], sort=True, observed=True)
    out = g[SUM_COLS].sum()
    out["n_transactions"] = g.size()
    out["n_households"] = g["household_key"].nunique()
    out["n_stores"] = g["STORE_ID"].nunique()
    out = out.reset_index().rename(columns={key: key_name, "WEEK_NO": "week", "QUANTITY": "units",
                                            "SALES_VALUE": "sales_value"})
    out["avg_shelf_price"] = out["shelf_value"] / out["units"]
    out["avg_paid_price"] = out["paid_value"] / out["units"]
    out["share_units_retail_disc"] = out["units_retail_disc"] / out["units"]
    out["avg_retail_disc_depth"] = out["retail_disc_amt"] / out["shelf_value"]  # value-weighted
    out["share_units_coupon"] = out["units_coupon"] / out["units"]
    return out


def selling_cells(clean):
    """Unique (product, store, week) cells with at least one valid sale."""
    c = clean[["PRODUCT_ID", "STORE_ID", "WEEK_NO"]].drop_duplicates()
    return c.reset_index(drop=True)


def promo_counts(causal_path, cells, products, batch_rows=2_000_000, log=print):
    """Aggregate store-level causal flags to product x week.

    A flag is 'on' when display != '0' / mailer != '0'. Two views are returned:
      * *_cells: selling (product, store, week) cells that carry the flag (join to realised sales);
        n_cells_recorded = selling cells that have any causal record (missing record => flag treated as off).
      * chain_*: all stores in causal_data for that product-week, whether or not a sale occurred in the sample.
    Counts are additive, so they can be summed again for commodity level.
    """
    cells = cells.assign(sel=1)
    sold = set(products)
    parts_chain, parts_cell = [], []
    n = 0
    for b in pq.ParquetFile(causal_path).iter_batches(batch_size=batch_rows):
        df = b.to_pandas()
        n += len(df)
        df = df[df["PRODUCT_ID"].isin(sold)]
        d = (df["display"].astype(str) != "0")
        m = (df["mailer"].astype(str) != "0")
        df = df.assign(d=d.astype("int8"), m=m.astype("int8"), r=1)
        df = df.drop_duplicates(["PRODUCT_ID", "STORE_ID", "WEEK_NO"])  # within-batch guard
        ch = df.groupby(["PRODUCT_ID", "WEEK_NO"])[["r", "d", "m"]].sum().reset_index()
        parts_chain.append(ch)
        mc = df.merge(cells, on=["PRODUCT_ID", "STORE_ID", "WEEK_NO"], how="inner")
        parts_cell.append(mc.groupby(["PRODUCT_ID", "WEEK_NO"])[["r", "d", "m"]].sum().reset_index())
        log(f"  causal rows read {n}")
    ch = pd.concat(parts_chain).groupby(["PRODUCT_ID", "WEEK_NO"])[["r", "d", "m"]].sum().reset_index()
    ch.columns = ["PRODUCT_ID", "WEEK_NO", "chain_stores_recorded", "chain_stores_display", "chain_stores_mailer"]
    ce = pd.concat(parts_cell).groupby(["PRODUCT_ID", "WEEK_NO"])[["r", "d", "m"]].sum().reset_index()
    ce.columns = ["PRODUCT_ID", "WEEK_NO", "n_cells_recorded", "n_cells_display", "n_cells_mailer"]
    return ch.merge(ce, on=["PRODUCT_ID", "WEEK_NO"], how="outer").fillna(0)


def finish_promo(panel):
    for c in ["chain_stores_recorded", "chain_stores_display", "chain_stores_mailer",
              "n_cells_recorded", "n_cells_display", "n_cells_mailer"]:
        panel[c] = panel[c].fillna(0).astype("int32")
    panel["share_stores_display"] = panel["n_cells_display"] / panel["n_stores"]
    panel["share_stores_mailer"] = panel["n_cells_mailer"] / panel["n_stores"]
    panel["any_display"] = (panel["n_cells_display"] > 0).astype("int8")
    panel["any_mailer"] = (panel["n_cells_mailer"] > 0).astype("int8")
    panel["any_display_chain"] = (panel["chain_stores_display"] > 0).astype("int8")
    panel["any_mailer_chain"] = (panel["chain_stores_mailer"] > 0).astype("int8")
    return panel


def split_label(week, test, val, train, first_full, last_full):
    w = np.asarray(week)
    lab = np.full(w.shape, "excluded_partial", dtype=object)
    lab[(w >= train[0]) & (w <= train[1])] = "train"
    lab[(w >= val[0]) & (w <= val[1])] = "val"
    lab[(w >= test[0]) & (w <= test[1])] = "test"
    lab[(w < first_full) | (w > last_full)] = "partial_week"
    return lab
