"""Collect runtime/memory figures from tracked result files into evals/results/engineering.json."""
import ast
import json

from . import config as C


def count_tests():
    n = 0
    for f in sorted((C.ROOT / "tests").glob("test_*.py")):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                n += 1
    return n


def collect():
    R = C.RESULTS_DIR
    j = lambda n: json.loads((R / n).read_text())
    return {
        "panel_audit": {"peak_memory_mb": j("panel_audit.json")["memory_peak_mb"]},
        "elasticity_train": {"runtime_seconds": j("elasticity_train.json")["runtime_seconds"],
                             "peak_memory_mb_parent": j("elasticity_train.json")["peak_memory_mb"]},
        "validation_stability": {k: j("elasticity_validation_stability.json")[k] for k in ("runtime_seconds", "peak_memory_mb")},
        "oos_validation": {k: j("oos_validation.json")[k] for k in ("runtime_seconds", "peak_memory_mb")},
        "test_final": {k: j("test_final.json")[k] for k in ("runtime_seconds", "peak_memory_mb")},
        "test_functions": count_tests(),
        "note": "Peak memory is the main process's high-water mark from /proc; the product bootstrap ran in separate worker processes "
                "(3 at a time, each short-lived). Runtimes are wall-clock on a 7.5 GB laptop. Panel build/convert timings were not recorded.",
    }
