"""Smoke tests: the app reads only committed result files, no raw or processed data."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from price_elasticity.simulator import load_tables

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.mark.parametrize("page", ["streamlit_app.py", "pages/1_Results.py", "pages/2_What_if.py"])
def test_page_runs(page):
    at = AppTest.from_file(str(APP / page), default_timeout=60).run()
    assert not at.exception
    assert len(at.title) == 1


def test_what_if_flags_unreliable_and_reliable():
    t = load_tables()
    for want in (True, False):
        lab = t[t.reliable == want].index[0]
        at = AppTest.from_file(str(APP / "pages/2_What_if.py"), default_timeout=60).run()
        at.selectbox[0].set_value(t.loc[lab, "department"]).run()
        at.selectbox[1].set_value(lab).run()
        assert not at.exception
        assert bool(at.warning) == (not want)
        assert (len(at.metric) == 2) == want
