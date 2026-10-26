import json
from price_elasticity import config as C
from price_elasticity.report import render_train
R = json.loads((C.RESULTS_DIR / "elasticity_train.json").read_text())
(C.RESULTS_DIR / "elasticity_train.md").write_text(render_train(R))
