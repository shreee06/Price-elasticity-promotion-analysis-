"""Part B: out-of-sample check with FROZEN train elasticities on VALIDATION weeks 86-93."""
import json
import time

from price_elasticity import config as C
from price_elasticity.memguard import MemGuard
from price_elasticity.oos import evaluate_window, load_frozen
from price_elasticity.report import render_oos

T0 = time.time()
mg = MemGuard(C.PROCESSED_DIR / "oos_validation_memlog.txt")
mg.start_watchdog()
res = evaluate_window(C.VAL_WEEKS[0], C.VAL_WEEKS[1], load_frozen())
res["runtime_seconds"] = round(time.time() - T0, 1)
res["peak_memory_mb"] = mg.peak_mb()
(C.RESULTS_DIR / "oos_validation.json").write_text(json.dumps(res, indent=2))
(C.RESULTS_DIR / "oos_validation.md").write_text(render_oos(
    res, "Out-of-sample check on VALIDATION weeks 86-93",
    "Frozen train elasticities (weeks 8-85) predict week-over-week relative changes in log units from relative changes in log price paid. "
    "Compared with a zero-change baseline and a last-week-repeats baseline."))
print("done", res["runtime_seconds"], res["peak_memory_mb"])
