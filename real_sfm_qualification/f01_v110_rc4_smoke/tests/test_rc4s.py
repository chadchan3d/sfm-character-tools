# -*- coding: utf-8 -*-
"""RC4S kit tests (offline, Python 3 -I): the production-mode check on the real RC4 CPM and registries, the
analyzer's gates on synthetic evidence, and the kit's pins. usage: python -I test_rc4s.py"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, "..", ".."))
sys.path.insert(0, os.path.join(KIT, "tools"))
sys.path.insert(0, os.path.join(KIT, "..", "f01_v110_rc3_smoke", "tests"))
import rc4s_analyze as A  # noqa: E402
import rc3s_modes as M  # noqa: E402
import test_rc3s as S3  # noqa: E402  (the RC3S tests' synthetic log helpers)

RESULTS = []
TEMPLATE = S3.read_json(os.path.join(KIT, "rc4s.template.json"))
PINS = TEMPLATE["pins"]
FD, TD = TEMPLATE["fox_dir"], TEMPLATE["tails_dir"]
FOX_ID, SIT_ID = "a" * 32, "b" * 32
FOX_FILE = "Characters/%s/Poses/RC4 Fox--%s.json" % (FD, FOX_ID[:12])
SIT_FILE = "Characters/%s/Poses/RC4 Sit--%s.json" % (TD, SIT_ID[:12])
REP = {"limits": {"position": 0.01, "angle_degrees": 0.1}, "outputs": 124, "max_distance": 0.000915,
       "max_angle_deg": 0.0199}
line, op, applied, saved = S3.line, S3.op, S3.applied, S3.saved


def check(name, ok):
    RESULTS.append((name, bool(ok)))
    print("%s %s" % ("PASS" if ok else "FAIL", name))


def body(n, tag, payload):
    return line(n * 10 + 5, "PROD_POSE_BODY-%s %s" % (tag, json.dumps(payload)), n)


def default_log(rep=REP, nowork="no-op", p6_at_repeat=False, cross_dest="milestailsprower2", adapted=True):
    cross = op(7, "Apply Pose", cross_dest, "verified", applied(), "Apply Pose RC4 Sit")
    if adapted:
        cross.insert(1, body(7, "RIG-adapted", {"converted": [{"bone": "bip_spine_3", "destination": "constrained"}]}))
    cross.insert(1, body(7, "P7-verified", {"reproduction": rep}))
    repeat = op(8, "Apply Pose", cross_dest, "no-op", "{'kind': u'pose', 'apply_phase': u'no-op'}")
    repeat.insert(1, body(8, "nowork", {"result": nowork}))
    if p6_at_repeat:
        repeat.insert(1, body(8, "P6", {"owned": True, "written": 0}))
    return [op(1, "Refresh Models", None, "completed", "None"),
            op(2, "Save Pose", "foxmccouldwm2", "verified", saved(FOX_ID), rig=S3.fox_rig()),
            op(3, "Pose Info", "foxmccouldwm2", "completed", "None"),
            op(4, "Apply Pose", "foxmccouldwm3", "verified", applied(), "Apply Pose RC4 Fox"),
            op(5, "Save Pose", "milestailsprower1", "verified", saved(SIT_ID), rig=S3.tails_rig()),
            op(6, "Pose Info", "milestailsprower1", "completed", "None"), cross, repeat]


def default_records():
    fox, tails = S3.default_records()
    fox["name"], tails["name"] = "RC4 Fox", "RC4 Sit"
    return fox, tails


def write_run(root, logs=None, records=None, build=None, extra_diffs=(), rigs=True):
    q = os.path.join(root, "run")
    os.makedirs(os.path.join(q, "staged"))
    os.makedirs(os.path.join(q, "evidence", "logs"))
    dump = lambda path, d: io.open(path, "w", encoding="utf-8").write(json.dumps(d))  # noqa: E731
    dump(os.path.join(q, "staged", "IDENTITIES.json"), {
        "qualification_cpm_sha256": PINS["rc4_cpm_sha256"], "profile_sha256": PINS["profile_sha256"],
        "body_profile_sha256": PINS["body_profile_sha256"], "mode_equivalence": {"pass": True}})
    files = {}
    for i, ops in enumerate(logs if logs is not None else [default_log()]):
        name = "CPM - 2026-11-20_0%d-00-00Z - pid1 - x - 001.log" % i
        header = "SFM Character Preset Manager diagnostic log cpm-log-v1 | build_sha256=%s version=1.1.0" % (
            build or PINS["rc4_cpm_sha256"])
        with io.open(os.path.join(q, "evidence", "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join([header] + [x for o in ops for x in o]) + "\n")
        files[name] = "0" * 64
    dump(os.path.join(q, "evidence", "logs", "LOGS.json"), {"files": files})
    fox, tails = records or default_records()
    diffs = [{"status": "added", "path": FOX_FILE}, {"status": "added", "path": SIT_FILE}]
    for folder, pid in ((FD, FOX_ID), (TD, SIT_ID)):
        diffs += [{"status": "added", "path": "Characters/%s/%s" % (folder, n)} for n in (
            "pose_sources.json", "pose_sources.json.bak", "pose_rigs.json", "pose_rigs.json.bak")]
        path = os.path.join(q, "evidence", "library_after", "Characters", folder, "pose_rigs.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        scene = u"rig_biped_%s" % (u"foxmccouldwm2" if folder == FD else u"milestailsprower1")
        dump(path, {"schema_version": 1, "record_kind": "cpm-pose-rigs", "entries": {pid: {
            "label": u"rig_biped", "scene": scene}} if rigs else {}})
    diffs += list(extra_diffs)
    for rel, rec in ((FOX_FILE, fox), (SIT_FILE, tails)):
        path = os.path.join(q, "evidence", "library_after", *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dump(path, rec)
    dump(os.path.join(q, "evidence", "library_cleanup.json"),
         {"differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True})
    dump(os.path.join(q, "evidence", "restore.json"), {"restored": True, "installation": "published"})
    c = copy.deepcopy(TEMPLATE)
    c["paths"]["Q"] = q
    return c


def verdict_of(**kw):
    root = tempfile.mkdtemp(prefix="rc4s-test-")
    try:
        c = write_run(root, **kw)
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            A.run(c)
        finally:
            sys.stdout = stdout
        return S3.read_json(os.path.join(c["paths"]["Q"], "evidence", "RC4S_VERDICT.json"))
    finally:
        shutil.rmtree(root)


def failed(v):
    return sorted(x["check"] for x in v["checks"] if not x["pass"])


def with_op(index, new):
    log = default_log()
    log[index] = new
    return [log]


def section_modes():
    cpm = open(os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py"), "rb").read()
    r = M.check(cpm, S3.POSE_REG, S3.BODY_REG, "p", "b")
    check("M.rc4_production_mode_check_passes", r["pass"] and r["structural_status"] and r["structural_production"])
    qual = cpm.replace(b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"')
    check("M.a_qualification_build_fails", qual != cpm and not M.check(qual, S3.POSE_REG, S3.BODY_REG, "p", "b")[
        "pass"])


def section_analyzer():
    v = verdict_of()
    check("A.complete_run_is_automated_smoke_pass", v["verdict"] == "AUTOMATED SMOKE PASS" and not failed(v))
    check("A.every_gate_is_evaluated", sorted(set(x["gate"] for x in v["checks"])) == [
        "CLEAN", "CROSS", "DISPLAY", "EVIDENCE", "FOX", "TAILS", "TARGET"])
    v = verdict_of(logs=with_op(4, op(5, "Save Pose", "milestailsprower1", "refused", "{'reason': u'x'}")))
    check("A.refused_sit_save_fails", v["verdict"] == "SMOKE FAIL" and "saved_once_from_the_original_tails" in
          failed(v))
    v = verdict_of(logs=with_op(4, op(5, "Save Pose", "milestailsprower2", "verified", saved(SIT_ID),
                                      rig=S3.tails_rig())))
    check("A.sit_saved_from_another_tails_fails", "saved_once_from_the_original_tails" in failed(v))
    check("A.cross_apply_without_adaptation_fails", "adapted_to_the_chest_rig" in failed(verdict_of(
        logs=[default_log(adapted=False)])))
    check("A.reproduction_beyond_the_envelope_fails", "reproduction_within_the_revised_envelope" in failed(
        verdict_of(logs=[default_log(rep=dict(REP, max_angle_deg=0.11))])))
    check("A.repeat_that_opened_undo_fails", "repeat_apply_is_a_no_op_without_undo" in failed(verdict_of(
        logs=[default_log(p6_at_repeat=True)])))
    check("A.repeat_mismatch_fails", "repeat_apply_is_a_no_op_without_undo" in failed(verdict_of(
        logs=[default_log(nowork="mismatch")])))
    check("A.cross_apply_to_the_original_fails", "applied_to_another_tails_and_verified" in failed(verdict_of(
        logs=[default_log(cross_dest="milestailsprower1")])))
    check("A.missing_rig_record_fails", "scene_rig_recorded_for_both_poses" in failed(verdict_of(rigs=False)))
    v = verdict_of(logs=with_op(6, op(7, "Apply Pose", "milestailsprower2", "committed-unverified",
                                      "{'apply_phase': u'committed-unverified'}", "Apply Pose RC4 Sit")))
    check("A.unverified_cross_apply_fails", v["verdict"] == "SMOKE FAIL" and "no_refusal_failure_or_recovery" in
          failed(v))
    check("A.another_build_is_incomplete", verdict_of(build="f" * 64)["verdict"] == "INCOMPLETE")
    check("A.unexpected_library_file_is_incomplete", verdict_of(extra_diffs=[
        {"status": "changed", "path": "Characters/krystal2020--7d2aee52ef3a/Body Presets/x.json"}])["verdict"] ==
        "INCOMPLETE")


def section_pins():
    for path, pin in ((os.path.join(KIT, "tools", "rc4s_analyze.py"), "analyzer_sha256"),
                      (os.path.join(KIT, "..", "f01_v110_rc3_smoke", "tools", "rc3s_modes.py"), "modes_sha256"),
                      (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256")):
        with open(path, "rb") as f:
            check("P.%s_is_pinned" % os.path.basename(path), hashlib.sha256(f.read()).hexdigest() == PINS[pin])
    cpm = open(os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py"), "rb").read()
    check("P.installed_build_is_the_rc4_cpm", PINS["qualification_cpm_sha256"] == PINS["rc4_cpm_sha256"] ==
          hashlib.sha256(cpm).hexdigest())
    proc = open(os.path.join(KIT, "PROCEDURE.md"), "rb").read().decode("utf-8")
    check("P.procedure_names_the_rc4_cpm_and_package", PINS["rc4_cpm_sha256"] in proc and PINS["rc4_zip_sha256"]
          in proc)


if __name__ == "__main__":
    section_modes()
    section_analyzer()
    section_pins()
    bad = [n for n, ok in RESULTS if not ok]
    print("%d/%d passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    sys.exit(1 if bad else 0)
