import importlib.util
import sys

import numpy as np
import pandas as pd
import pytest

from price_elasticity import config as C
from price_elasticity.oos import STAT_COLS, _changes, _stats, evaluate, metrics_from_sums


def synth_tab(seed=0, n=40, T=6):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"cluster": np.repeat(np.arange(n), T), "week": np.tile(np.arange(T), n)})
    d["p"] = rng.normal(size=len(d))
    d["a"] = 0.5 * d["p"] + rng.normal(size=len(d))
    d["q"] = rng.normal(size=len(d))
    d["promo"] = rng.random(len(d)) < 0.2
    return d


def test_metrics_match_numpy():
    t = synth_tab()
    m = metrics_from_sums(_stats(t[["a", "p", "q"]])[STAT_COLS].to_numpy())
    assert m["corr_model"] == pytest.approx(np.corrcoef(t.p, t.a)[0, 1])
    assert m["corr_last_week"] == pytest.approx(np.corrcoef(t.q, t.a)[0, 1])
    assert m["mae_zero"] == pytest.approx(t.a.abs().mean())
    assert m["mae_model"] == pytest.approx((t.a - t.p).abs().mean())
    assert m["mae_last_week"] == pytest.approx((t.a - t.q).abs().mean())
    assert m["dir_model"] == pytest.approx((np.sign(t.a) == np.sign(t.p)).mean())


def test_evaluate_reproducible_and_ci_contains_point():
    t = synth_tab(seed=2)
    a, b = evaluate(t, B=60, seed=5), evaluate(t, B=60, seed=5)
    assert a == b
    for k, v in a["all"]["metrics"].items():
        assert v["ci_low"] <= v["est"] <= v["ci_high"], k
    assert a["all"]["metrics"]["corr_model"]["est"] > 0.3
    assert a["all"]["n_rows"] == len(t)


def test_changes_need_consecutive_weeks():
    df = pd.DataFrame({"product_id": [1, 1, 1, 2, 2], "week": [1, 2, 4, 1, 2], "lp": [0.0, 0.1, 0.5, 1.0, 0.9],
                       "units": [10, 20, 30, 5, 5], "depth": [0, 0, 0.3, 0, 0]})
    ch = _changes(df, "product_id", "lp", "units", "depth")
    assert sorted(zip(ch.product_id, ch.week)) == [(1, 2), (2, 2)]     # week 4 has no week 3: no change defined
    r = ch[ch.product_id == 1].iloc[0]
    assert r.dY == pytest.approx(np.log(2)) and r.dX == pytest.approx(0.1)


def _load_script():
    spec = importlib.util.spec_from_file_location("run_test_final", C.ROOT / "scripts" / "run_test_final.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_test_script_refuses_without_flag_and_second_run(tmp_path, monkeypatch):
    m = _load_script()
    monkeypatch.setattr(sys, "argv", ["x"])
    with pytest.raises(SystemExit):
        m.main()
    rec = tmp_path / "test_run_record.json"
    rec.write_text("{}")
    monkeypatch.setattr(m, "RECORD", rec)
    monkeypatch.setattr(sys, "argv", ["x", "--i-am-done-tuning"])
    monkeypatch.setattr(m, "load_frozen", lambda: {"frozen": {"sha256_elasticity_train_json": m.sha(m.R / "elasticity_train.json"),
                                                              "sha256_commodity_csv": m.sha(m.R / "commodity_elasticities_train.csv")}})
    monkeypatch.setattr(m, "MemGuard", lambda *a, **k: type("G", (), {"start_watchdog": lambda s: None})())
    with pytest.raises(SystemExit) as e:
        m.main()
    assert "already evaluated" in str(e.value)
