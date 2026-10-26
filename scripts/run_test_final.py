"""One-time evaluation of the FROZEN train estimates on the TEST weeks 94-101 (docs/test_protocol.md).

* Test mode needs --i-am-done-tuning and runs at most once: it writes evals/results/test_run_record.json BEFORE any
  test-week row is read, and refuses to run if that file exists.
* Nothing is fitted or tuned for the prediction task. The only estimation is the pre-registered re-estimate of the
  primary log-price coefficients on the test weeks, compared with the train estimate.
* --dry-run-on-validation runs the identical code path on weeks 86-93 (test rows can not be loaded), never writes the
  record, writes evals/results/validation_reference.json and stops with an error unless it reproduces
  oos_validation.json exactly and elasticity_validation_stability.json (primary coefficients) to 1e-9.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from price_elasticity import config as C
from price_elasticity.memguard import MemGuard
from price_elasticity.oos import FROZEN_JSON, evaluate_window, load_frozen, stability_window
from price_elasticity.report import render_test

R = C.RESULTS_DIR
RECORD = R / "test_run_record.json"
PROTOCOL = C.ROOT / "docs" / "test_protocol.md"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=C.ROOT, capture_output=True, text=True, check=True).stdout.strip()


def run_window(lo, hi, ctx, tr, allow_test):
    return evaluate_window(lo, hi, ctx, allow_test=allow_test), stability_window(lo, hi, ctx, tr, allow_test=allow_test)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-am-done-tuning", action="store_true")
    ap.add_argument("--dry-run-on-validation", action="store_true")
    a = ap.parse_args()
    if a.dry_run_on_validation == a.i_am_done_tuning:
        sys.exit("choose exactly one of --dry-run-on-validation or --i-am-done-tuning")
    T0 = time.time()
    mg = MemGuard(C.PROCESSED_DIR / ("test_final_memlog.txt" if a.i_am_done_tuning else "dry_run_memlog.txt"))
    mg.start_watchdog()
    ctx = load_frozen()
    tr = json.loads((R / "elasticity_train.json").read_text())
    assert ctx["frozen"]["sha256_elasticity_train_json"] == sha(R / "elasticity_train.json"), "frozen estimates changed"
    assert ctx["frozen"]["sha256_commodity_csv"] == sha(R / "commodity_elasticities_train.csv"), "frozen estimates changed"

    if a.dry_run_on_validation:
        oos, stab = run_window(*C.VAL_WEEKS, ctx, tr, allow_test=False)
        ref = json.loads((R / "oos_validation.json").read_text())
        for k in ("runtime_seconds", "peak_memory_mb"):
            ref.pop(k, None)
        assert json.loads(json.dumps(oos)) == ref, "dry run does not reproduce oos_validation.json exactly"
        old = {r["name"]: r for r in json.loads((R / "elasticity_validation_stability.json").read_text())["comparison"]}
        for r in stab["comparison"]:
            o = old[r["name"]]
            assert abs(r["window"] - o["val"]) < 1e-9 and abs(r["window_lo"] - o["val_lo"]) < 1e-9, f"{r['name']} differs"
        (R / "validation_reference.json").write_text(json.dumps({"oos": oos, "stability": stab,
                                                                  "reproduces_oos_validation_exactly": True,
                                                                  "reproduces_validation_stability_to_1e-9": True}, indent=2))
        print("dry run OK: reproduces oos_validation.json exactly and the validation stability coefficients")
        return

    if RECORD.exists():
        sys.exit(f"{RECORD.name} exists: the test weeks were already evaluated; refusing to run again")
    if not (R / "validation_reference.json").exists():
        sys.exit("run --dry-run-on-validation first")
    rec = {"started": datetime.now().isoformat(timespec="seconds"), "git_head": git("rev-parse", "HEAD"),
           "git_dirty": bool(git("status", "--porcelain")), "protocol_sha256": sha(PROTOCOL),
           "frozen_estimates_sha256": sha(FROZEN_JSON), "weeks": list(C.TEST_WEEKS),
           "command": "run_test_final.py --i-am-done-tuning"}
    RECORD.write_text(json.dumps(rec, indent=2))      # written before any test-week row is read
    oos, stab = run_window(*C.TEST_WEEKS, ctx, tr, allow_test=True)
    val = json.loads((R / "validation_reference.json").read_text())
    out = {**rec, "test": oos, "stability_test": stab, "validation": val["oos"], "stability_validation": val["stability"],
           "runtime_seconds": round(time.time() - T0, 1), "peak_memory_mb": mg.peak_mb()}
    (R / "test_final.json").write_text(json.dumps(out, indent=2))
    (R / "test_final.md").write_text(render_test(out))
    rec.update(finished=datetime.now().isoformat(timespec="seconds"), result_file="evals/results/test_final.json")
    RECORD.write_text(json.dumps(rec, indent=2))
    print("test evaluation written; runtime", out["runtime_seconds"], "s")


if __name__ == "__main__":
    main()
