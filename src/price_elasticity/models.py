"""Fixed-effects Poisson (PPML) and log-log OLS with clustered SEs, cluster bootstrap and the spec log."""
import numpy as np
import pandas as pd
import pyfixest as pf

COLS = ["stage", "group", "spec", "estimator", "sample", "n_obs", "n_clusters", "term", "estimate", "se",
        "ci_low", "ci_high", "note"]


class SpecLog:
    def __init__(self):
        self.rows = []

    def add(self, **kw):
        self.rows.append({c: kw.get(c) for c in COLS})

    def frame(self):
        return pd.DataFrame(self.rows, columns=COLS)


def fit(df, y, terms, estimator, cluster="product_id", fe=("product_id", "week")):
    """Return dict(term -> (est, se, lo, hi)), n_obs, n_clusters, dropped. estimator in {'ppml','ols'}."""
    fml = f"{y} ~ {' + '.join(terms)} | {' + '.join(fe)}"
    vcov = {"CRV1": cluster} if cluster else "iid"
    m = pf.fepois(fml, data=df, vcov=vcov) if estimator == "ppml" else pf.feols(fml, data=df, vcov=vcov)
    t = m.tidy()
    res = {str(k): (float(r["Estimate"]), float(r["Std. Error"]), float(r["2.5%"]), float(r["97.5%"])) for k, r in t.iterrows()}
    ncl = int(df[cluster].nunique()) if cluster else None
    return res, int(m._N), ncl, list(getattr(m, "_collin_vars", []) or [])


def run_and_log(log, df, y, terms, estimator, stage, group, spec, sample, **kw):
    """Fit, append every coefficient to the spec log (also failures), return the result dict or None."""
    try:
        res, n, ncl, dropped = fit(df, y, terms, estimator, **kw)
    except Exception as e:  # logged, not hidden
        log.add(stage=stage, group=group, spec=spec, estimator=estimator, sample=sample, n_obs=len(df),
                term="(fit failed)", note=f"{type(e).__name__}: {str(e)[:120]}")
        return None
    for term, (b, se, lo, hi) in res.items():
        log.add(stage=stage, group=group, spec=spec, estimator=estimator, sample=sample, n_obs=n, n_clusters=ncl,
                term=term, estimate=b, se=se, ci_low=lo, ci_high=hi, note=("collinear dropped: " + ",".join(dropped)) if dropped else "")
    return {"coef": res, "n_obs": n, "n_clusters": ncl, "dropped": dropped}


_BOOT = {}


def _one_draw(pick):
    d, order, bounds = _BOOT["d"], _BOOT["order"], _BOOT["bounds"]
    G = len(pick)
    idx = np.concatenate([order[bounds[g]:bounds[g + 1]] for g in pick])
    sizes = bounds[pick + 1] - bounds[pick]
    b = d.iloc[idx].copy()
    b["_bc"] = np.repeat(np.arange(G), sizes)
    try:
        res, *_ = fit(b, _BOOT["y"], _BOOT["terms"], _BOOT["est"], cluster=None, fe=("_bc",) + _BOOT["fe_other"])
        return {t: res[t][0] for t in _BOOT["report"] if t in res}
    except Exception:
        return None


def _run_in_subprocesses(picks, n_jobs, chunk):
    import json
    import pickle
    import subprocess
    import sys
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    chunks = [picks[i:i + chunk] for i in range(0, len(picks), chunk)]
    with tempfile.TemporaryDirectory(prefix="boot_") as tmp:
        tmp = Path(tmp)

        def work(i):
            inp, outp = tmp / f"in{i}.pkl", tmp / f"out{i}.json"
            with open(inp, "wb") as f:
                pickle.dump({**{k: _BOOT[k] for k in ["d", "order", "bounds", "y", "terms", "est", "fe_other", "report"]},
                             "picks": chunks[i]}, f)
            import os
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
            subprocess.run([sys.executable, "-m", "price_elasticity.bootworker", str(inp), str(outp)], check=True, env=env)
            return json.loads(outp.read_text())

        with ThreadPoolExecutor(n_jobs) as ex:
            parts = list(ex.map(work, range(len(chunks))))
    return [o for part in parts for o in part]


def cluster_bootstrap(df, y, terms, estimator, B, seed, cluster="product_id", fe_other=("week",), report=None,
                      n_jobs=3, tasks_per_child=5):
    """Pairs cluster bootstrap: resample clusters with replacement; each draw's duplicated cluster gets its own FE id.
    The resampled cluster indices are drawn up front from the seed, so results do not depend on n_jobs.
    Draws run in short-lived worker processes (the FE backend is not fork-safe and grows memory across fits).
    Returns dict term -> {boot_se, lo, hi (percentile 95%)} and draw counts."""
    rng = np.random.default_rng(seed)
    d = df.reset_index(drop=True)
    codes, uniq = pd.factorize(d[cluster])
    order = np.argsort(codes, kind="stable")
    bounds = np.searchsorted(codes[order], np.arange(len(uniq) + 1))
    G = len(uniq)
    picks = [rng.integers(0, G, G) for _ in range(B)]
    _BOOT.update(d=d, order=order, bounds=bounds, y=y, terms=terms, est=estimator, fe_other=tuple(fe_other),
                 report=report or terms)
    if n_jobs <= 1:
        out = [_one_draw(p) for p in picks]
    else:
        out = _run_in_subprocesses(picks, n_jobs, tasks_per_child)
    draws = [o for o in out if o is not None]
    D = pd.DataFrame(draws)
    # rounded to 10 decimals: float noise (~1e-16) from different processes/threads must not change the output
    res = {t: {"boot_se": round(float(D[t].std(ddof=1)), 10), "lo": round(float(D[t].quantile(0.025)), 10),
               "hi": round(float(D[t].quantile(0.975)), 10)}
           for t in D.columns}
    return res, {"requested": B, "ok": int(len(D)), "failed": B - len(D), "seed": seed}
