"""Shared loaders for the app: only committed result files are read (no raw or processed data)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RES = ROOT / "evals" / "results"


def load(name):
    return json.loads((RES / name).read_text())


CAVEAT = ("Associations in observational data from 2,500 sampled households of one grocery retailer, not causal effects "
          "and not store totals. Revenue only: there are no cost or margin data.")
