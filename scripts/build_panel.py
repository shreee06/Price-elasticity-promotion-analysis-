"""Build product x week and commodity x week panels (memory-safe). Writes data/processed/*.parquet."""
import json
import numpy as np
import pandas as pd

from price_elasticity import config as C
from price_elasticity.memguard import MemGuard
from price_elasticity.panel import aggregate_sales, selling_cells, promo_counts, finish_promo, split_label
from price_elasticity.price import clean_transactions, add_row_values
from price_elasticity.reference import add_reference

P = C.PROCESSED_DIR
mg = MemGuard(P / "build_panel_memlog.txt")
mg.start_watchdog()

tx = pd.read_parquet(P / "transactions.parquet")
# WEEK_NO <-> DAY mapping check
assert ((tx["DAY"] + 1) // 7 + 1 == tx["WEEK_NO"]).all(), "WEEK_NO != (DAY+1)//7+1"
days_per_week = tx.groupby("WEEK_NO")["DAY"].agg(["min", "max"])
assert days_per_week.index.max() == 102 and days_per_week.loc[2:101].eval("max-min").eq(6).all()
mg.stage("transactions loaded")

clean, counts = clean_transactions(tx)
del tx
clean = add_row_values(clean)
prod = pd.read_parquet(P / "product.parquet")[["PRODUCT_ID", "COMMODITY_DESC", "DEPARTMENT"]]
prod["COMMODITY_DESC"] = prod["COMMODITY_DESC"].astype(str)
_sub = pd.read_parquet(P / "product.parquet", columns=["SUB_COMMODITY_DESC"])["SUB_COMMODITY_DESC"].astype(str)
prod["non_merchandise"] = (prod["COMMODITY_DESC"].isin(C.NON_MERCH_COMMODITIES)
                           | _sub.str.startswith(C.FUEL_SUBCOMMODITY_PREFIX)).astype("int8")
clean = clean.merge(prod[["PRODUCT_ID", "COMMODITY_DESC"]], on="PRODUCT_ID", how="left")
counts["rows_without_commodity"] = int(clean["COMMODITY_DESC"].isna().sum())
mg.stage("cleaned")

windows = {
    "week_definition": "WEEK_NO = (DAY + 1) // 7 + 1; week 1 = days 1-5 and week 102 = days 706-711 are partial",
    "first_full_week": C.FIRST_FULL_WEEK, "last_full_week": C.LAST_FULL_WEEK,
    "train": list(C.TRAIN_WEEKS), "validation": list(C.VAL_WEEKS), "test": list(C.TEST_WEEKS),
    "partial_weeks_flagged": [1, 102],
    "note": "Inclusive WEEK_NO ranges. No model is evaluated on test weeks in step 1.",
}
C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
(C.RESULTS_DIR / "windows.json").write_text(json.dumps(windows, indent=2))

prod_panel = aggregate_sales(clean, "PRODUCT_ID", "product_id")
mg.stage(f"product agg {len(prod_panel)}")
com_panel = aggregate_sales(clean, "COMMODITY_DESC", "commodity")
com_panel["n_products"] = clean.groupby(["COMMODITY_DESC", "WEEK_NO"])["PRODUCT_ID"].nunique().to_numpy()
mg.stage(f"commodity agg {len(com_panel)}")

cells = selling_cells(clean)
mg.stage(f"selling cells {len(cells)}")
pc = promo_counts(P / "causal.parquet", cells, prod_panel["product_id"].unique(), log=lambda s: None)
mg.stage("promo counts")
pc = pc.rename(columns={"PRODUCT_ID": "product_id", "WEEK_NO": "week"})

prod_panel = finish_promo(prod_panel.merge(pc, on=["product_id", "week"], how="left"))
pcc = pc.merge(prod[["PRODUCT_ID", "COMMODITY_DESC"]].rename(columns={"PRODUCT_ID": "product_id", "COMMODITY_DESC": "commodity"}),
               on="product_id", how="left")
pcc = pcc.groupby(["commodity", "week"], as_index=False).sum(numeric_only=True).drop(columns="product_id", errors="ignore")
com_panel = finish_promo(com_panel.merge(pcc, on=["commodity", "week"], how="left"))
# n_cells_display counts selling product-store-week cells: for commodities, n_stores is distinct stores, so the share
# is expressed per selling product-store cell instead.
cell_tot = cells.merge(prod[["PRODUCT_ID", "COMMODITY_DESC"]], on="PRODUCT_ID", how="left")
cell_tot = cell_tot.groupby(["COMMODITY_DESC", "WEEK_NO"]).size().rename("n_cells").reset_index()
cell_tot.columns = ["commodity", "week", "n_cells"]
com_panel = com_panel.merge(cell_tot, on=["commodity", "week"], how="left")
com_panel["share_stores_display"] = com_panel["n_cells_display"] / com_panel["n_cells"]
com_panel["share_stores_mailer"] = com_panel["n_cells_mailer"] / com_panel["n_cells"]
assert (prod_panel["n_cells_display"] <= prod_panel["n_stores"]).all(), "duplicate causal rows inflate counts"
mg.stage("promo merged")
del clean, cells

for df, ent in [(prod_panel, "product_id"), (com_panel, "commodity")]:
    df.sort_values([ent, "week"], inplace=True)
prod_panel = add_reference(prod_panel, "product_id")
com_panel = add_reference(com_panel, "commodity")
prod_panel["non_merchandise"] = prod_panel["product_id"].map(prod.set_index("PRODUCT_ID")["non_merchandise"]).astype("int8")
com_panel["non_merchandise"] = com_panel["commodity"].isin(C.NON_MERCH_COMMODITIES).astype("int8")
for df in (prod_panel, com_panel):
    df["split"] = split_label(df["week"], C.TEST_WEEKS, C.VAL_WEEKS, C.TRAIN_WEEKS, C.FIRST_FULL_WEEK, C.LAST_FULL_WEEK)
mg.stage("reference done")

prod_panel.to_parquet(P / "panel.parquet", index=False)
com_panel.to_parquet(P / "panel_commodity.parquet", index=False)
(C.RESULTS_DIR / "cleaning_counts.json").write_text(json.dumps(counts, indent=2))
print(json.dumps(counts, indent=2))
print(len(prod_panel), len(com_panel), "peak MB", mg.peak_mb())
