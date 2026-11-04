# -*- coding: utf-8 -*-
"""F-01 FA-1 Trial 2: derive the DIAGNOSTIC-ONLY qualification variant (Python 3, -I). Never touches the candidate.

usage: python -I fa2_variant.py <Q>\\nq1.json        (after nq1_tool.py ... build, before install)
Applies one anchored insertion to <Q>\\staged\\SFM_Character_Preset_Manager.py (the qualification build): after the
unchanged time decision, the write time is pinned to the target channels' clock (GetCurrentTime), only when all
three agree and the clock maps back through the verified channels clip inside the owning shot; the converted time is
kept in the record. Because the pinned time is part of the time record, the existing P1/P2/P7 equality checks refuse
if the clock changes during precommit or verification. Updates <Q>\\staged\\IDENTITIES.json with both hashes.
"""
from __future__ import print_function

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nq1_tool as T  # noqa: E402

ANCHOR = (b"    decided = prod_pose_time_decide(rec)\n"
          b"    decided[u\"seconds\"] = {u\"t_doc\": t_doc / 10000.0, u\"t_shot\": t_shot / 10000.0,\n")
INSERT = b'''    decided = prod_pose_time_decide(rec)
    # === F-01 FA-1 Trial 2 DIAGNOSTIC VARIANT (qualification only; never in the production candidate) ===
    fa2_clocks = sorted(set(c[u"reported"] for c in channels.values()))
    if len(fa2_clocks) != 1:
        raise ProdPoseError(u"time-mapping", u"FA-2: the target channel clocks disagree %r" % (fa2_clocks,))
    fa2_clock = fa2_clocks[0]
    fa2_shot = prod_pose_ticks_of(clip.FromChildMediaTime(prod_pose_time(fa2_clock), False))
    fa2_doc = prod_pose_ticks_of(shot.FromChildMediaTime(prod_pose_time(fa2_shot), False))
    if not prod_pose_ticks_of(shot.GetStartTime()) <= fa2_doc < prod_pose_ticks_of(shot.GetEndTime()):
        raise ProdPoseError(u"time-mapping", u"FA-2: the channel clock %d maps outside the owning shot (%d)" %
                            (fa2_clock, fa2_doc))
    decided[u"converted_t_chan"] = decided[u"t_chan"]
    decided[u"t_chan"] = fa2_clock
    decided[u"fa2_clock_document_ticks"] = fa2_doc
    # === end FA-2 diagnostic variant ===
    decided[u"seconds"] = {u"t_doc": t_doc / 10000.0, u"t_shot": t_shot / 10000.0,
'''


def main(argv):
    c = T.load(argv[1])
    staged = os.path.join(T.p(c, "Q"), "staged")
    ids_path = os.path.join(staged, "IDENTITIES.json")
    ids = T.read_json(ids_path)
    src = os.path.join(staged, "SFM_Character_Preset_Manager.py")
    if ids.get("fa2_variant"):
        raise SystemExit("REFUSED: the variant was already applied")
    if T.sha(src) != ids["qualification_cpm_sha256"]:
        raise SystemExit("REFUSED: the staged file is not the built qualification CPM")
    with open(src, "rb") as f:
        raw = f.read()
    if raw.count(ANCHOR) != 1 or b"FA-2" in raw:
        raise SystemExit("REFUSED: the anchor is not unique (found %d)" % raw.count(ANCHOR))
    out = raw.replace(ANCHOR, INSERT)
    a, b = raw.split(b"\n"), out.split(b"\n")
    added = len(b) - len(a)
    if b[:a.index(ANCHOR.split(b"\n")[0])] != a[:a.index(ANCHOR.split(b"\n")[0])] or added != INSERT.count(b"\n") - 2:
        raise SystemExit("REFUSED: the derivation changed more than the inserted block")
    tmp = src + ".fa2.tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, src)
    ids.update({"qualification_base_sha256": ids["qualification_cpm_sha256"], "qualification_cpm_sha256": T.sha(src),
                "fa2_variant": True, "fa2_inserted_lines": added})
    T.write_json(ids_path, ids)
    print(json.dumps(ids, indent=1))
    print("FA-2 VARIANT: %d lines inserted after the time decision; qualification build %s" % (added, ids[
        "qualification_cpm_sha256"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
