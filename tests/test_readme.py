import json
import re

from price_elasticity import config as C
from price_elasticity.engineering import count_tests
from price_elasticity.readme import render


def test_readme_matches_result_files():
    assert (C.ROOT / "README.md").read_text() == render(), "README is stale: run scripts/make_readme.py"


def test_readme_numbers_come_from_results():
    txt = render()
    tr = json.loads((C.RESULTS_DIR / "elasticity_train.json").read_text())
    assert f"{tr['primary']['ppml']['estimate']:.2f}" in txt
    assert f"{tr['sample']['primary_products']:,}" in txt


def test_engineering_test_count_current():
    eng = json.loads((C.RESULTS_DIR / "engineering.json").read_text())
    assert eng["test_functions"] == count_tests(), "run scripts/collect_engineering.py"


def test_no_causal_wording_in_readme():
    txt = (C.ROOT / "README.md").read_text().lower()
    for bad in ["causes", "caused", "causal effect", "impact of", "leads to", "drives"]:
        assert bad not in txt.replace("not a causal effect", "").replace("no causal", ""), bad
