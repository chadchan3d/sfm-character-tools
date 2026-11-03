# -*- coding: utf-8 -*-
"""M-06 W2: stage the native instruments for a later, separately authorized native session (offline only).

usage: python -I stage_instruments.py CONFIG.json OUT_DIR [DEFERRED_CONFIG.json]

Copies the instruments and native scripts into a NEW staging folder (never into SFM), substitutes the planned
INSTRUMENT_DIR (the config's instrument_dir), writes the configs, records each staged file's planned installed path
in instrument_files (so every observation hashes the instruments it ran), and writes STAGED_SHA256SUMS.txt. Refuses
when OUT_DIR exists, when a config still holds a "<...>" placeholder, when the CPM pin is not the accepted W1
candidate, or when a staged script still holds a placeholder. Installing the staged files into SFM is a separate,
authorized native step.

Configuration selection: one Observer is staged per configuration, with CONFIG_NAME substituted (OBSERVERS below),
and each staged configuration records its own config_name, which the Observer and the deferred preparation verify.
The deferred preparation runs tools/compare_obs.py in-session, so compare_obs.py is staged beside it.
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W1_SHA256 = "fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
FILES = (("instruments", "m06w2_core.py"), ("instruments", "M06_Qualification_Abort_Injector.py"),
         ("native", "M06_Native_Probe.py"), ("native", "M06_Deferred_Fixture_Preparation.py"),
         ("tools", "compare_obs.py"))
OBSERVER = ("instruments", "M06_Qualification_Observer.py")
CONFIGS = ("m06w2_config.json", "m06w2_deferred_config.json")
OBSERVERS = {"m06w2_config.json": "M06_Qualification_Observer.py",
             "m06w2_deferred_config.json": "M06_Deferred_Observer.py"}
PLACEHOLDER = re.compile(r"<[^<>]+>")


def placeholders(value, path=""):
    if isinstance(value, dict):
        return [p for k, v in sorted(value.items()) for p in placeholders(v, path + "/" + k)]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in placeholders(v, "%s/%d" % (path, i))]
    if isinstance(value, str) or type(value).__name__ == "unicode":
        return [path] if PLACEHOLDER.search(value) else []
    return []


def stage(config_path, out_dir, deferred_path=None):
    configs = {}
    for name, path in zip(CONFIGS, (config_path, deferred_path)):
        if path is None:
            continue
        with io.open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        left = placeholders(cfg)
        if left:
            raise SystemExit("%s still has placeholders: %s" % (path, left[:8]))
        if cfg["cpm"]["sha256"] != W1_SHA256:
            raise SystemExit("%s does not pin the accepted W1 candidate" % path)
        configs[name] = cfg
    install = configs["m06w2_config.json"]["instrument_dir"]
    if os.path.exists(out_dir):
        raise SystemExit("refusing to reuse %s" % out_dir)
    os.makedirs(out_dir)
    if "m06w2_deferred_config.json" in configs and \
            configs["m06w2_deferred_config.json"]["instrument_dir"] != install:
        raise SystemExit("the two configurations name different instrument directories")
    staged = [(folder, name, name, None) for folder, name in FILES]
    staged += [(OBSERVER[0], OBSERVER[1], OBSERVERS[c], c) for c in CONFIGS if c in configs]
    for folder, name, out_name, config_name in staged:
        with open(os.path.join(ROOT, folder, name), "rb") as f:
            data = f.read()
        if b'u"<INSTRUMENT_DIR>"' in data:
            data = data.replace(b'u"<INSTRUMENT_DIR>"', ("u" + json.dumps(install)).encode("utf-8"))
        if config_name is not None:
            data = data.replace(b'u"<CONFIG_NAME>"', ("u" + json.dumps(config_name)).encode("utf-8"))
        if b'u"<INSTRUMENT_DIR>"' in data or b'u"<CONFIG_NAME>"' in data:
            raise SystemExit("%s still holds a placeholder" % out_name)
        with open(os.path.join(out_dir, out_name), "wb") as f:
            f.write(data)
    for name, cfg in configs.items():
        cfg = dict(cfg, config_name=name,
                   instrument_files=dict((n, os.path.join(install, n)) for _, _, n, _ in staged))
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(json.dumps(cfg, indent=1, sort_keys=True, ensure_ascii=True).encode("ascii"))
    rows = []
    for name in sorted(os.listdir(out_dir)):
        with open(os.path.join(out_dir, name), "rb") as f:
            rows.append("%s  %s\n" % (hashlib.sha256(f.read()).hexdigest(), name))
    with open(os.path.join(out_dir, "STAGED_SHA256SUMS.txt"), "wb") as f:
        f.write("".join(rows).encode("ascii"))
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(2)
    print("staged: " + stage(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
