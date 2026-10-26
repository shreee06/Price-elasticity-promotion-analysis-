from price_elasticity import config as C
from price_elasticity.readme import render
(C.ROOT / "README.md").write_text(render())
