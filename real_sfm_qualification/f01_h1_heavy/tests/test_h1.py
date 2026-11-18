# -*- coding: utf-8 -*-
"""F-01 H1 kit: offline tests of the template, the one-line build derivation and the analyzer (Python 3, -I).
Synthetic runs only; nothing here shows anything about SFM.

usage: python -I test_h1.py
"""
from __future__ import print_function

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(KIT, "tools"))
import h1_tool  # noqa: E402
import h1_analyze as A  # noqa: E402

RESULTS = []
H1_COMMIT = "7310171"           # the H1 candidate commit (CPM 3d31e721...)
HELPERS = ["hlp_forearm_L", "hlp_forearm_R"]
POSE = u"Heavy H1"


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(path):
    with open(path, "rb") as f:
        return sha_bytes(f.read())


# ---------------------------------------------------------------------------
# T. template and build derivation
# ---------------------------------------------------------------------------

def section_template():
    with open(os.path.join(KIT, "h1.template.json"), "rb") as f:
        t = json.loads(f.read().decode("utf-8"))
    check("T1 format and no placeholder pin", t["format"] == h1_tool.FORMAT and
          not any("<" in v for v in t["pins"].values()))
    raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                   "%s:cpm/app/SFM_Character_Preset_Manager.py" % H1_COMMIT])
    check("T2 candidate pin = the H1 candidate at commit %s" % H1_COMMIT,
          t["pins"]["candidate_cpm_sha256"] == sha_bytes(raw))
    for path, pin in h1_tool.pinned_kit_files(None):
        check("T2 %s pin = %s" % (pin, os.path.basename(path)), t["pins"][pin] == sha_file(path))
    for key, rel in (("profile_sha256", "cpm/pose_profiles/cpm_pose_profiles_v1.json"),
                     ("body_profile_sha256", "cpm/pose_profiles/cpm_body_profiles_v1.json"),
                     ("observer_sha256", "real_sfm_qualification/f01_full_body_s0/observer/F01_S0_Survey.py")):
        check("T2 pin %s = %s" % (key, rel), t["pins"][key] == sha_file(os.path.join(REPO, *rel.split("/"))))
    with open(os.path.join(KIT, "..", "f01_ot1_integration_smoke", "ot1s.template.json"), "rb") as f:
        o = json.loads(f.read().decode("utf-8"))
    for key in ("published_cpm_sha256", "r2_fixture_sha256", "destination_sha256", "legacy_pose_sha256",
                "profile_sha256", "body_profile_sha256"):
        check("T3 pin %s equals the OT1S kit's" % key, t["pins"][key] == o["pins"][key])
    check("T3 paths equal the OT1S kit's (without its Body preset)",
          dict((k, v) for k, v in o["paths"].items() if k != "BODY_PRESET") == t["paths"])
    S = h1_tool.S
    qual = raw.replace(S.MODE_PRODUCTION, S.MODE_QUALIFICATION)
    diff = [i for i, (x, y) in enumerate(zip(raw.split(b"\n"), qual.split(b"\n"))) if x != y]
    check("T4 one-line derivation gives the pinned qualification build", len(diff) == 1 and
          sha_bytes(qual) == t["pins"]["qualification_cpm_sha256"], diff)
    text = raw.decode("utf-8")
    needed = ["prod_scope_live", "prod_pose_channel_authored", "prod_pose_transform_state", "prod_scope_helper_evidence",
              "prod_scope_state", "get_game_model", "prod_pose_attr", "prod_pose_seq"]
    check("T5 every CPM function the capture calls exists in the candidate",
          all(("\ndef %s(" % n) in text for n in needed), [n for n in needed if ("\ndef %s(" % n) not in text])
    check("T6 the tool reuses the chain unchanged (identity substitutions only)",
          h1_tool.S.SESSIONS == ("H1_SESSION.dmx",) and h1_tool.S.DESTINATION == "H1_SPARE.dmx" and
          h1_tool.K.comparator().endswith("h1_analyze.py"))


# ---------------------------------------------------------------------------
# V. analyzer verdicts on synthetic runs
# ---------------------------------------------------------------------------

def set_state(role, moved=False):
    chans = {}
    for i, bone in enumerate([u"bip_pelvis", u"bip_upperArm_L", u"bip_lowerArm_L", u"bip_hand_L"]):
        for attr, suffix in ((u"orientation", u"_o"), (u"position", u"_p")):
            chans[bone + suffix] = {"sha256": "%s-%s-base" % (role, bone + suffix), "to": u"bone %d (%s)" % (i, bone),
                                    "to_attribute": attr}
    for i, bone in enumerate(HELPERS):
        for attr, suffix in ((u"orientation", u"_o"), (u"position", u"_p")):
            chans[bone + suffix] = {"sha256": "%s-%s-base" % (role, bone + suffix),
                                    "to": u"bone %d (%s)" % (77 + i, bone), "to_attribute": attr}
    chans[u"AH"] = {"sha256": "%s-AH" % role, "to": u"AH", "to_attribute": u"value"}
    if moved:
        for n in (u"bip_pelvis_o", u"bip_upperArm_L_o", u"bip_lowerArm_L_o", u"bip_pelvis_p"):
            chans[n] = dict(chans[n], sha256=chans[n]["sha256"].replace("base", "posed"))
    bones = dict((b, [[0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0], [1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0]])
                 for b in [u"bip_pelvis"] + HELPERS)
    declared = [[77, u"hlp_forearm_L", 11, 7172, 2], [78, u"hlp_forearm_R", 12, 7172, 2]]
    return {"name": u"heavy_" + role, "errors": [], "model": u"models/player/heavy.mdl", "channels": chans, "keys": 99,
            "bones": bones, "header": {"status": "READ", "reason": None, "bones": 79, "attachments": 13,
                                       "flex_drivers": 0, "declared": declared},
            "admission": {"helpers": list(HELPERS), "refusals": {}, "classes": {u"direct-fk": 77,
                                                                                u"carried-candidate": 2}}}


def capture(step, cfg, undo, redo, target_moved=False, selected=None):
    sets = dict((r, set_state(r)) for r in ("source", "target", "peer"))
    if target_moved:
        sets["target"] = set_state("target", moved=True)
    return {"format": "F01-H1-capture-v1", "step": step, "pid": 4242,
            "cpm_build_sha256": cfg["pins"]["qualification_cpm_sha256"], "registry_mode": u"qualification",
            "names": {}, "sets": sets, "errors": [],
            "session": {"undo": {"can_undo": True, "can_redo": bool(redo), "undo_desc": undo, "redo_desc": redo},
                        "head_seconds": 0.2083, "shot": u"shot15",
                        "document": u"E:\\run\\sessions\\H1_SESSION.dmx"},
            "selected_pose": selected}


def good_run():
    pins = {"qualification_cpm_sha256": "q" * 64, "candidate_cpm_sha256": "c" * 64}
    cfg = {"pins": pins, "paths": {}}
    sel = {"name": POSE, "version": 3, "kind": "full_body", "helpers": list(HELPERS)}
    apply_label = u"Apply Pose %s" % POSE
    caps = {"BASE": capture("BASE", cfg, u"Rotate", u""),
            "SAVED": capture("SAVED", cfg, u"Rotate", u"", selected=sel),
            "APPLY": capture("APPLY", cfg, apply_label, u"", True, sel),
            "UNDO": capture("UNDO", cfg, u"Rotate", u"Redo " + apply_label, False, sel),
            "REDO": capture("REDO", cfg, apply_label, u"", True, sel),
            "NOOP": capture("NOOP", cfg, apply_label, u"", True, sel)}
    record = {"name": POSE, "pose": {"version": 3, "engine": {"rule": "direct_fk_v1", "revision": 1,
                                                              "carried_rule": None},
                                     "source": {"model_ref": u"models/player/heavy.mdl"},
                                     "scope": {"kind": "full_body", "ledger": dict(
                                         [(b, "posed") for b in (u"bip_pelvis", u"bip_upperArm_L")] +
                                         [(h, "engine-helper") for h in HELPERS])}}}
    rel = u"Characters/heavy--abc/Poses/%s--1234.json" % POSE
    return {"cfg": cfg, "caps": caps, "record": record, "record_rel": rel,
            "cleanup": {"differences_kept_in_evidence": [
                {"status": "added", "path": u"Characters/heavy--abc/character.json", "sha256": "x"},
                {"status": "added", "path": rel, "sha256": "y"}], "files_equal_pre": True, "folders_equal_pre": True},
            "restore": {"restored": True, "inventory_problems": []},
            "logs": [u'PROD_POSE_SCOPE-P1 {"noop": false, "scope": "full_body"}',
                     u'PROD_POSE_SCOPE-P7-verified {"time": 1}',
                     u'PROD_POSE_SCOPE-P1 {"noop": true, "scope": "full_body"}'],
            "ids": {"qualification_cpm_sha256": pins["qualification_cpm_sha256"],
                    "candidate_cpm_sha256": pins["candidate_cpm_sha256"]},
            "sessions": {"H1_SESSION.dmx": b"session bytes", "H1_SPARE.dmx": b"spare bytes"}}


def write_run(run, root):
    q = tempfile.mkdtemp(prefix="h1_run_", dir=root)
    for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs")):
        os.makedirs(os.path.join(q, d))
    cfg = copy.deepcopy(run["cfg"])
    cfg["paths"]["Q"] = q
    for name, data in run["sessions"].items():
        with open(os.path.join(q, "sessions", name), "wb") as f:
            f.write(data)
    cfg["pins"]["r2_fixture_sha256"] = sha_bytes(run["sessions"]["H1_SESSION.dmx"])
    cfg["pins"]["destination_sha256"] = sha_bytes(run["sessions"]["H1_SPARE.dmx"])
    if run.get("tamper_session"):
        with open(os.path.join(q, "sessions", "H1_SESSION.dmx"), "wb") as f:
            f.write(b"saved by mistake")

    def dump(path, obj):
        with open(path, "wb") as f:
            f.write(json.dumps(obj).encode("utf-8"))
    dump(os.path.join(q, "staged", "IDENTITIES.json"), run["ids"])
    for step, data in run["caps"].items():
        dump(os.path.join(q, "observations", "H1-%s.json" % step), data)
    side = run.get("sidecar")
    if side:  # Save New's pose_sources.json, kept in library_after and recorded as an added difference
        obj = json.loads(json.dumps(side["obj"]).replace("<Q>", q.replace("\\", "\\\\")))
        path = os.path.join(q, "evidence", "library_after", *side["rel"].split("/"))
        os.makedirs(os.path.dirname(path))
        dump(path, obj)
        run["cleanup"]["differences_kept_in_evidence"].append(
            {"status": side.get("status", "added"), "path": side["rel"],
             "sha256": side.get("sha256") or sha_file(path)})
    dump(os.path.join(q, "evidence", "library_cleanup.json"), run["cleanup"])
    dump(os.path.join(q, "evidence", "restore.json"), run["restore"])
    if run["record"] is not None:
        path = os.path.join(q, "evidence", "library_after", *run["record_rel"].split("/"))
        os.makedirs(os.path.dirname(path))
        dump(path, run["record"])
    with open(os.path.join(q, "evidence", "logs", "CPM.log"), "wb") as f:
        f.write("\n".join(run["logs"]).encode("utf-8"))
    return cfg


def analyze(run, root):
    cfg = write_run(run, root)
    with open(os.devnull, "w") as null:
        old, sys.stdout = sys.stdout, null
        try:
            code = A.run(cfg)
        finally:
            sys.stdout = old
    with open(os.path.join(cfg["paths"]["Q"], "evidence", "H1_VERDICT.json"), "rb") as f:
        out = json.loads(f.read().decode("utf-8"))
    return out, code, cfg


def section_verdicts(root):
    out, code, cfg = analyze(good_run(), root)
    check("V1 the complete passing run -> AUTOMATED PASS (every gate), exit 0",
          out["verdict"] == "AUTOMATED PASS" and code == 0 and all(out["gates"].values()), out["failed"])
    with open(os.path.join(cfg["paths"]["Q"], "evidence", "H1_VERDICT.md"), "rb") as f:
        md = f.read().decode("utf-8")
    check("V1 the report requires the Owner's visual acceptance", "visual acceptance" in md)
    try:
        A.run(cfg)
        again = False
    except OSError:
        again = True
    check("V1 the verdict is written once (exclusive create)", again)

    def variant(label, change, verdict, gate=None):
        run = good_run()
        change(run)
        out, code, _ = analyze(run, root)
        ok = out["verdict"] == verdict and code == 1 and (gate is None or not out["gates"][gate])
        check("V2 %s -> %s%s" % (label, verdict, " at %s" % gate if gate else ""), ok, (out["verdict"], out["failed"]))

    def write_helper(run):
        for s in ("APPLY", "REDO", "NOOP"):
            run["caps"][s]["sets"]["target"]["channels"][u"hlp_forearm_L_o"]["sha256"] = "written"
    variant("a helper channel written", write_helper, "FAIL", "APPLY")

    def write_flex(run):
        for s in ("APPLY", "REDO", "NOOP"):
            run["caps"][s]["sets"]["target"]["channels"][u"AH"]["sha256"] = "written"
    variant("a non-bone channel written", write_flex, "FAIL", "APPLY")

    def no_change(run):
        for s in ("APPLY", "REDO", "NOOP"):
            run["caps"][s]["sets"]["target"] = set_state("target")
    variant("the target did not change", no_change, "FAIL", "APPLY")
    variant("no P7 verification in the log", lambda r: r["logs"].remove(u'PROD_POSE_SCOPE-P7-verified {"time": 1}'),
            "FAIL", "APPLY")

    def undo_partial(run):
        run["caps"]["UNDO"]["sets"]["target"]["channels"][u"bip_pelvis_o"]["sha256"] = "stale"
    variant("Undo leaves a key", undo_partial, "FAIL", "UNDO")

    def redo_wrong(run):
        run["caps"]["REDO"]["sets"]["target"] = set_state("target")
    variant("Redo not the applied state", redo_wrong, "FAIL", "UNDO")

    def noop_entry(run):
        run["caps"]["NOOP"]["session"]["undo"]["undo_desc"] = u"Apply Pose again"
    variant("the second Apply added a history entry", noop_entry, "FAIL", "UNDO")
    variant("no no-op reported", lambda r: r["logs"].remove(u'PROD_POSE_SCOPE-P1 {"noop": true, "scope": "full_body"}'),
            "FAIL", "UNDO")

    def peer_changed(run):
        run["caps"]["REDO"]["sets"]["peer"]["channels"][u"bip_hand_L_o"]["sha256"] = "moved"
    variant("the peer changed at Redo", peer_changed, "FAIL", "PEER")

    def peer_bone(run):
        run["caps"]["APPLY"]["sets"]["peer"]["bones"][u"bip_pelvis"][2] = [1.0, 2.0, 3.5]
    variant("a peer bone moved", peer_bone, "FAIL", "PEER")

    def source_changed(run):
        run["caps"]["APPLY"]["sets"]["source"]["channels"][u"bip_hand_L_o"]["sha256"] = "moved"
    variant("the source changed", source_changed, "FAIL", "PEER")

    def ledger_wrong(run):
        run["record"]["pose"]["scope"]["ledger"][u"hlp_forearm_R"] = "posed"
    variant("the record does not mark every helper", ledger_wrong, "FAIL", "SAVE")

    def save_wrote(run):
        run["caps"]["SAVED"]["sets"]["target"]["channels"][u"bip_hand_L_o"]["sha256"] = "x"
    variant("Save changed the scene", save_wrote, "FAIL", "SAVE")

    def rigged(run):
        for s in run["caps"].values():
            s["sets"]["target"]["admission"]["classes"][u"constrained"] = 10
    variant("a rigged target", rigged, "SAFE REFUSAL", "HEADER")

    # Safe refusals: reported as a limitation, never as compatibility.
    def unreadable(run):
        for s in list(run["caps"]):
            if s not in ("BASE", "SAVED"):
                del run["caps"][s]
            else:
                tgt = run["caps"][s]["sets"]["target"]
                tgt["header"] = {"status": "UNREADABLE", "reason": "AttributeError('numlocalattachments')"}
                tgt["admission"] = {"helpers": [], "refusals": dict((h, "unreadable") for h in HELPERS)}
        run["record"] = None
        run["cleanup"]["differences_kept_in_evidence"] = []
        run["logs"] = [u'PROD_POSE_SCOPE-refused {"code": "carried-unsupported"}']
    variant("the native header unreadable on the known Heavy", unreadable, "SAFE REFUSAL")

    def save_refused(run):
        for s in list(run["caps"]):
            if s not in ("BASE", "SAVED"):
                del run["caps"][s]
        run["record"] = None
        run["cleanup"]["differences_kept_in_evidence"] = []
    variant("Save refused (no record)", save_refused, "SAFE REFUSAL")
    run = good_run()
    unreadable(run)
    out, _, _ = analyze(run, root)
    check("V3 a safe refusal is stated as not a compatibility result",
          out["info"].get("refusal") and out["gates"]["HEADER"] is not None and out["verdict"] != "AUTOMATED PASS")

    # Incomplete evidence or restoration.
    variant("a missing capture", lambda r: r["caps"].pop("UNDO"), "INCOMPLETE", "EVIDENCE")
    variant("restoration failed", lambda r: r["restore"].update(restored=False), "INCOMPLETE", "EVIDENCE")
    variant("library not restored exactly", lambda r: r["cleanup"].update(files_equal_pre=False), "INCOMPLETE",
            "EVIDENCE")

    def extra_diff(run):
        run["cleanup"]["differences_kept_in_evidence"].append(
            {"status": "changed", "path": u"Characters/krystal2020--7d2aee52ef3a/Body Presets/Body.json", "sha256": "z"})
    variant("an unrelated library change", extra_diff, "INCOMPLETE", "EVIDENCE")
    section_pose_sources(root, variant)
    variant("a session saved", lambda r: r.update(tamper_session=True), "INCOMPLETE", "EVIDENCE")
    variant("an unverified result in the log", lambda r: r["logs"].append(u"PROD_POSE_SCOPE-P7-unverified {}"),
            "INCOMPLETE", "EVIDENCE")

    def two_processes(run):
        run["caps"]["REDO"]["pid"] = 9
    variant("two SFM processes", two_processes, "INCOMPLETE", "EVIDENCE")

    def wrong_build(run):
        run["caps"]["APPLY"]["cpm_build_sha256"] = "p" * 64
    variant("another CPM build loaded", wrong_build, "INCOMPLETE", "EVIDENCE")

    def moved_head(run):
        run["caps"]["NOOP"]["session"]["head_seconds"] = 1.0
    variant("the playhead moved", moved_head, "INCOMPLETE", "EVIDENCE")

    def not_heavy(run):
        for s in run["caps"].values():
            s["sets"]["peer"]["model"] = u"models/player/engineer.mdl"
    variant("a non-Heavy instance", not_heavy, "INCOMPLETE", "EVIDENCE")


PID = u"4cfe409f901e23e11c247ab7b5183507"


def with_sidecar(run, entries=None, rel=u"Characters/heavy--abc/pose_sources.json", **extra):
    """The native shape: Save New also adds pose_sources.json with the saved pose's one source-project entry."""
    run["record"]["preset_id"] = PID
    obj = {"entries": entries if entries is not None else
           {PID: {"project": u"<Q>\\sessions\\h1_session.dmx"}},
           "record_kind": "cpm-pose-sources", "schema_version": 1}
    run["sidecar"] = dict({"rel": rel, "obj": obj}, **extra)
    return run


def section_pose_sources(root, variant):
    """P: the analyzer correction after the native run. pose_sources.json is allowed only as the one exact H1 entry."""
    out, code, cfg = analyze(with_sidecar(good_run()), root)
    check("P1 the pose plus its one pose_sources.json entry -> AUTOMATED PASS",
          out["verdict"] == "AUTOMATED PASS" and code == 0, out["failed"])
    other = u"e:\\sourcefilmmaker sessions\\other.dmx"
    variant("pose_sources.json naming another project",
            lambda r: with_sidecar(r, {PID: {"project": other}}), "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json with a second entry", lambda r: with_sidecar(
        r, {PID: {"project": u"<Q>\\sessions\\h1_session.dmx"}, u"f" * 32: {"project": other}}),
        "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json keyed by another pose", lambda r: with_sidecar(
        r, {u"f" * 32: {"project": u"<Q>\\sessions\\h1_session.dmx"}}), "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json with an extra field", lambda r: with_sidecar(
        r, {PID: {"project": u"<Q>\\sessions\\h1_session.dmx", "note": u"x"}}), "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json in another character folder",
            lambda r: with_sidecar(r, rel=u"Characters/krystal2020--7d2aee52ef3a/pose_sources.json"),
            "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json changed, not added", lambda r: with_sidecar(r, status="changed"),
            "INCOMPLETE", "EVIDENCE")
    variant("pose_sources.json kept differs from the recorded difference",
            lambda r: with_sidecar(r, sha256="0" * 64), "INCOMPLETE", "EVIDENCE")
    run = with_sidecar(good_run())
    run["cleanup"]["differences_kept_in_evidence"].append(
        {"status": "added", "path": u"Characters/heavy--abc/library.json", "sha256": "z"})
    out, _, _ = analyze(run, root)
    check("P2 another new file beside pose_sources.json is still unexpected -> INCOMPLETE",
          out["verdict"] == "INCOMPLETE" and "library.changed_only_by_the_one_saved_heavy_pose" in out["failed"],
          out["failed"])
    out, code, cfg = analyze(with_sidecar(good_run()), root)
    original = sha_file(os.path.join(cfg["paths"]["Q"], "evidence", "H1_VERDICT.json"))
    with open(os.devnull, "w") as null:
        old, sys.stdout = sys.stdout, null
        try:
            A.run(cfg, replay=True)
        finally:
            sys.stdout = old
    with open(os.path.join(cfg["paths"]["Q"], "evidence", "H1_REPLAY_VERDICT.json"), "rb") as f:
        rep = json.loads(f.read().decode("utf-8"))
    check("P3 a replay writes H1_REPLAY_VERDICT beside the original, naming it, and leaves it unchanged",
          rep["replay_of_verdict_sha256"] == original and original == sha_file(
              os.path.join(cfg["paths"]["Q"], "evidence", "H1_VERDICT.json")) and rep["verdict"] == out["verdict"])


def main():
    root = tempfile.mkdtemp(prefix="h1_tests_")
    try:
        section_template()
        section_verdicts(root)
    finally:
        shutil.rmtree(root, True)
    passed = sum(1 for r in RESULTS if r[1])
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
