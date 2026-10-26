# Price Elasticity & Promotion Analysis (dunnhumby The Complete Journey)

Portfolio project in Python: build a weekly price/promotion panel from retail transactions, audit it, and (in later
steps) study how units sold move with price and promotion. All estimates will be **associations in observational data,
not causal effects**.

Status: step 1 (setup, weekly panel, data audit). No elasticity model has been fitted yet.

## Data

Source: dunnhumby, *The Complete Journey* (household-level transactions of 2,500 frequent shoppers of one retailer over
two years, with product, causal/display/mailer, campaign, coupon and demographic tables). The copy used here is the
Kaggle mirror `frtgnn/dunnhumby-the-complete-journey`, which lists the licence as **DbCL-1.0**; please check dunnhumby's
own terms before reuse.

**The raw data is not included in this repository** (it is in `.gitignore`); the repo ships code and aggregate results
only. To reproduce: download the dataset from Kaggle (or dunnhumby), unzip it somewhere, and point the code to it:

```bash
export DUNNHUMBY_RAW_DIR=/path/to/dunnhumby-raw   # default: ~/Downloads/dunnhumby-raw
```

## Reproduce (step 1)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export PYTHONPATH=src
.venv/bin/python scripts/convert_raw.py     # raw CSV -> data/processed/*.parquet (untracked)
.venv/bin/python scripts/build_panel.py     # product- and commodity-level weekly panels, reference prices, windows
.venv/bin/python scripts/audit_panel.py     # docs/panel_audit.md + evals/results/panel_audit.json
.venv/bin/python -m pytest
```

The scripts stop cleanly if available memory falls below 1 GB (`src/price_elasticity/memguard.py`).

## Layout

`src/price_elasticity/` library (config, price definitions, panel, reference price) · `scripts/` pipeline ·
`tests/` synthetic-data tests · `evals/results/` aggregate results (windows, audit) · `docs/` write-ups · `app/` (later).

## Limitations

*Placeholder, to be completed:* household sample (2,500 households, so units are sample counts, not store totals), one
retailer, grocery rather than fashion, observational data, no cost data, promotions not randomised.

## Results

To be filled from real runs. See `docs/panel_audit.md` for the step-1 data audit.
