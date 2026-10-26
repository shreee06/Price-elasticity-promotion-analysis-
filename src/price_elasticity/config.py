"""Paths and fixed settings. Raw data is read in place and never copied into the repo."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(os.environ.get("DUNNHUMBY_RAW_DIR", Path.home() / "Downloads" / "dunnhumby-raw"))
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "evals" / "results"
DOCS_DIR = ROOT / "docs"

# WEEK_NO = (DAY + 1) // 7 + 1 (verified in build_panel). Week 1 holds days 1-5 and week 102 holds days
# 706-711 (data ends at day 711), so both are partial; full weeks are 2..101.
FIRST_FULL_WEEK = 2
LAST_FULL_WEEK = 101
N_TEST_WEEKS = 8
N_VAL_WEEKS = 8
# Fixed evaluation windows (inclusive WEEK_NO ranges); also written to evals/results/windows.json.
TEST_WEEKS = (LAST_FULL_WEEK - N_TEST_WEEKS + 1, LAST_FULL_WEEK)                       # 94..101
VAL_WEEKS = (TEST_WEEKS[0] - N_VAL_WEEKS, TEST_WEEKS[0] - 1)                           # 86..93
TRAIN_WEEKS = (1, VAL_WEEKS[0] - 1)                                                    # 1..85

# Reference price definitions (history strictly before the current week).
REF_MAX_WINDOW = 8
REF_MEDIAN_WINDOW = 13
# Minimum number of OBSERVED (sold) weeks inside the window; otherwise the reference stays null.
MIN_OBS_MAX = 4
MIN_OBS_MEDIAN = 6

# Usability thresholds for promotion variation
MIN_ACTIVE_WEEKS = 30
MIN_DISCOUNT_WEEKS = 8
MIN_NONDISCOUNT_WEEKS = 8
DISCOUNT_DEPTH_THRESHOLD = 0.10

# Non-merchandise: fuel (QUANTITY is in thousandths of gallons, ~98.7% of all raw units), coupon and placeholder
# commodities. They stay in the panels (so totals reconcile) but carry non_merchandise=1 and are excluded from analyses.
NON_MERCH_COMMODITIES = ("FUEL", "COUPON", "COUPON/MISC ITEMS", "COUPONS/STORE & MFG", "NO COMMODITY DESCRIPTION")
FUEL_SUBCOMMODITY_PREFIX = "GASOLINE"
