# -*- coding: utf-8 -*-
"""F-01 SFP-1 (scoped poses): derive compact discovery fixtures from the native model compatibility survey.

The survey observations (real_sfm_qualification/f01_model_survey, MC-01 TF2 Heavy without a rig, MC-02 the Heavy with
rig_biped_simple; Owner's local archive, not committed) are converted exactly as f01_body_fixture.py converts the S0
observations, with two additions: an observation without a rig registration (MC-01) derives an empty rig, and the
animation set's control groups (the survey's mc.control_groups: path and member control handles) are kept for the
grouped picker. Nothing is interpreted. The derived fixtures (cpm/convergence/tests/fixtures/f01_scoped/) name their
source hash and are pinned in test_cpm_app_f01_scoped.py.

usage: python -I f01_scoped_fixture.py OBSERVATION.json OUT.json
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import f01_body_fixture as FX  # noqa: E402


def derive(obs, source_sha256):
    regs = obs["rig"]["registrations"]
    if regs:
        D = FX.derive(obs, source_sha256)
    else:
        o = copy.deepcopy(obs)
        o["rig"]["registrations"] = [{"rig": {"name": None, "handle": None}, "registration": {"handle": None},
                                      "elements": []}]
        D = FX.derive(o, source_sha256)
        D["rig"].update({"names": [], "registrations": 0, "rig_handle": None, "registration": None, "elements": []})
    D["format"] = "f01-scoped-discovery-fixture-v1"
    D["groups"] = [{"path": g["path"], "handle": g["id"]["handle"],
                    "controls": [c["handle"] for c in g["controls"]]}
                   for g in (obs.get("mc") or {}).get("control_groups") or []]
    D["animation_set"] = obs.get("animation_set_name")
    return D


def main(argv):
    with io.open(argv[1], "rb") as f:
        raw = f.read()
    D = derive(json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest())
    data = (json.dumps(D, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with io.open(argv[2], "wb") as f:
        f.write(data)
    print(argv[2], len(data), hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main(sys.argv)
