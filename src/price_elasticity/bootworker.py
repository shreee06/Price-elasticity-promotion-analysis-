"""Worker for cluster_bootstrap: python -m price_elasticity.bootworker in.pkl out.json"""
import json
import pickle
import sys

from . import models

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        job = pickle.load(f)
    picks = job.pop("picks")
    models._BOOT.update(job)
    json.dump([models._one_draw(p) for p in picks], open(sys.argv[2], "w"))
