import json
from price_elasticity import config as C
from price_elasticity.engineering import collect
(C.RESULTS_DIR / "engineering.json").write_text(json.dumps(collect(), indent=2))
