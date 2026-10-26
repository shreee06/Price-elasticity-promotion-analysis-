import numpy as np
import pandas as pd
import pytest

from price_elasticity.simulator import simulate, top_reliable


def table(shrunk=-1.5, se=0.2, p05=0.05, p95=0.40):
    t = pd.DataFrame({"label": ["C000"], "shrunk": [shrunk], "shrunk_se": [se], "department": ["GROCERY"], "p05": [p05], "p95": [p95]})
    t["ci_low"] = t.shrunk - 1.959964 * t.shrunk_se
    t["ci_high"] = t.shrunk + 1.959964 * t.shrunk_se
    t["reliable"] = t.ci_high < 0
    t["z"] = t.shrunk.abs() / t.shrunk_se
    return t.set_index("label")


def test_known_elasticity_by_hand():
    r = simulate("C000", 0.20, table())
    assert r["units_change_pct"] == pytest.approx(100 * (0.8 ** -1.5 - 1))      # +39.75%
    assert r["revenue_change_pct"] == pytest.approx(100 * (0.8 ** -0.5 - 1))    # +11.80%
    assert round(r["units_change_pct"], 2) == 39.75 and round(r["revenue_change_pct"], 2) == 11.80
    assert r["reliable"]


def test_interval_widens_with_larger_se():
    a = simulate("C000", 0.20, table(se=0.1))
    b = simulate("C000", 0.20, table(se=0.3))
    wa = a["units_change_pct_ci"][1] - a["units_change_pct_ci"][0]
    wb = b["units_change_pct_ci"][1] - b["units_change_pct_ci"][0]
    assert wb > wa
    lo, hi = b["revenue_change_pct_ci"]
    assert lo <= b["revenue_change_pct"] <= hi


def test_range_restriction_enforced():
    with pytest.raises(ValueError):
        simulate("C000", 0.50, table())
    with pytest.raises(ValueError):
        simulate("C000", 0.01, table())
    simulate("C000", 0.05, table())
    simulate("C000", 0.40, table())


def test_unreliable_flagged_and_not_ranked():
    pos = simulate("C000", 0.2, table(shrunk=0.3))
    span = simulate("C000", 0.2, table(shrunk=-0.2, se=0.2))
    assert not pos["reliable"] and not span["reliable"] and "not reliable" in pos["note"]
    assert top_reliable(table(shrunk=0.3)) == [] and top_reliable(table(shrunk=-0.2, se=0.2)) == []
    assert len(top_reliable(table())) == 1
