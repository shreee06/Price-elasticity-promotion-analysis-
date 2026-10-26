"""Convert the needed raw CSVs to Parquet with explicit dtypes (data/processed, untracked)."""
import pandas as pd
from price_elasticity.config import RAW_DIR, PROCESSED_DIR
from price_elasticity.memguard import MemGuard
from price_elasticity.config import RESULTS_DIR

mg = MemGuard(PROCESSED_DIR / "convert_memlog.txt")
mg.start_watchdog()
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

TX = dict(household_key="int32", BASKET_ID="int64", DAY="int16", PRODUCT_ID="int32", QUANTITY="int32",
          SALES_VALUE="float64", STORE_ID="int32", RETAIL_DISC="float64", TRANS_TIME="int16", WEEK_NO="int16",
          COUPON_DISC="float64", COUPON_MATCH_DISC="float64")
tx = pd.read_csv(RAW_DIR / "transaction_data.csv", dtype=TX)
tx.to_parquet(PROCESSED_DIR / "transactions.parquet", index=False)
mg.stage(f"transactions {len(tx)}")
del tx

prod = pd.read_csv(RAW_DIR / "product.csv", dtype=dict(PRODUCT_ID="int32", MANUFACTURER="int32"))
for c in ["DEPARTMENT", "BRAND", "COMMODITY_DESC", "SUB_COMMODITY_DESC"]:
    prod[c] = prod[c].astype("category")
prod["CURR_SIZE_OF_PRODUCT"] = prod["CURR_SIZE_OF_PRODUCT"].str.strip()
prod.to_parquet(PROCESSED_DIR / "product.parquet", index=False)
mg.stage(f"product {len(prod)}")

n = 0
parts = []
for ch in pd.read_csv(RAW_DIR / "causal_data.csv", dtype=dict(PRODUCT_ID="int32", STORE_ID="int32", WEEK_NO="int16",
                                                              display="string", mailer="string"), chunksize=3_000_000):
    ch["display"] = ch["display"].astype("category")
    ch["mailer"] = ch["mailer"].astype("category")
    parts.append(ch)
    n += len(ch)
    mg.stage(f"causal rows {n}")
causal = pd.concat(parts, ignore_index=True)
del parts
vc = {c: causal[c].value_counts(dropna=False).to_dict() for c in ["display", "mailer"]}
print(vc)
causal.to_parquet(PROCESSED_DIR / "causal.parquet", index=False)
mg.stage("causal done")

for name in ["coupon", "coupon_redempt", "campaign_table", "campaign_desc", "hh_demographic"]:
    pd.read_csv(RAW_DIR / f"{name}.csv").to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
