"""List raw files with sizes, columns, dtypes and first 3 rows (read-only on raw dir)."""
import os
import pandas as pd
from price_elasticity.config import RAW_DIR

for f in sorted(os.listdir(RAW_DIR)):
    p = RAW_DIR / f
    print(f"\n=== {f}  ({p.stat().st_size / 1e6:.2f} MB)")
    if f.endswith(".csv"):
        df = pd.read_csv(p, nrows=200000)
        print(df.dtypes.to_string())
        print(df.head(3).to_string())
