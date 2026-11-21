# -*- coding: utf-8 -*-
"""SFM Character Tools v1.1.0 release candidate 5: RC4 with the Owner-approved v1.1.0 README.txt. Builds the UNSIGNED
package and verifies its release readiness offline with RC1's tool unchanged (release/v1.1.0-rc1/rc_tool.py).

Nothing else changes against RC4: the same software spec (release/v1.1.0-rc4/SOFTWARE_SPEC.json), so the same CPM,
registries and unsigned inventory. README.txt sits at the ZIP root, outside usermod/, so it is not an inventory file and
the Workshop installer never installs it (workshop_installer/core.py _map_member).

This file adds, around RC1's tool:
  - README.txt (this folder's copy of the approved text, pinned by readme_sha256) as a fifth candidate entry;
  - the package manifest lists README.txt among the replaced entries;
  - RC1's package check expects README.txt among the changed entries, and requires the packaged README to be the
    approved bytes; RC1's rollback check counts README.txt as a candidate file rather than a kept v1.0.0 file.
Nothing here installs, signs, publishes or touches an SFM installation.

usage: python -I rc5_tool.py RC.json package | verify
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v1.1.0-rc1"))
import rc_tool as R  # noqa: E402

P, T = R.P, R.T
README_ENTRY = "README.txt"
README_SOURCE = os.path.join(HERE, "README.txt")

R.SPEC = os.path.join(os.path.dirname(HERE), "v1.1.0-rc4", "SOFTWARE_SPEC.json")
P.ZIP_NAME = "SFM.Character.Tools.v1.1.0-rc5-UNSIGNED.zip"

_candidate_sources = P.candidate_sources


def candidate_sources(c):
    return _candidate_sources(c) + [(README_ENTRY, README_SOURCE, c["pins"]["readme_sha256"])]


P.candidate_sources = candidate_sources

_cmd_package = P.cmd_package


def cmd_package(c):
    write_json = T.write_json

    def manifest_writer(path, data, exclusive=False):
        if isinstance(data, dict) and data.get("format") == "F01-PS2-package-v1":
            data["replaced"] = sorted(data["replaced"] + [README_ENTRY])
        return write_json(path, data, exclusive=exclusive)

    T.write_json = manifest_writer
    try:
        return _cmd_package(c)
    finally:
        T.write_json = write_json


P.cmd_package = cmd_package

_check_package = R.check_package


def check_package(c, Rv):
    files, v100 = _check_package(c, Rv)
    out = Rv["package"]
    want = (sorted([P.CPM_ENTRY, P.INV_ENTRY, README_ENTRY]), sorted(P.LIB + n for n in P.REGISTRIES), [P.SIG_ENTRY])
    readme = files.get(README_ENTRY)
    out["readme_sha256"] = R.sha_bytes(readme) if readme is not None else None
    out["readme_byte_length"] = len(readme) if readme is not None else None
    out["readme_is_approved"] = out["readme_sha256"] == c["pins"]["readme_sha256"]
    out["pass"] = (not out["problems"] and (out["changed"], out["added"], out["removed"]) == want and
                   out["readme_is_approved"])
    return files, v100


R.check_package = check_package

_check_rollback = R.check_rollback


def check_rollback(c, Rv, files, v100):
    kept = dict((n, b) for n, b in files.items() if n != README_ENTRY)
    _check_rollback(c, Rv, kept, v100)
    Rv["rollback"]["readme_replaced"] = README_ENTRY in v100 and files.get(README_ENTRY) != v100[README_ENTRY]


R.check_rollback = check_rollback

if __name__ == "__main__":
    sys.exit(R.main(sys.argv))
