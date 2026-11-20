# -*- coding: utf-8 -*-
"""RC3S kit tests (offline, Python 3 -I): the production-mode check on the real RC3 CPM and registries, the analyzer's
gates on synthetic evidence, and the kit's pins. usage: python -I test_rc3s.py"""
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
import rc3s_modes as M  # noqa: E402
import rc3s_analyze as A  # noqa: E402

RESULTS = []


def check(name, ok):
    RESULTS.append((name, bool(ok)))
    print("%s %s" % ("PASS" if ok else "FAIL", name))


def read_json(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


CPM = open(os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py"), "rb").read()
POSE_REG = read_json(os.path.join(REPO, "cpm", "pose_profiles", "cpm_pose_profiles_v1.json"))
BODY_REG = read_json(os.path.join(REPO, "cpm", "pose_profiles", "cpm_body_profiles_v1.json"))
TEMPLATE = read_json(os.path.join(KIT, "rc3s.template.json"))
PINS = TEMPLATE["pins"]


def section_modes():
    r = M.check(CPM, POSE_REG, BODY_REG, "p", "b")
    check("M.rc3_production_mode_check_passes", r["pass"])
    check("M.rc1_checks_still_hold", all(r[k] for k in ("production", "generic_v3", "carried", "krystal_v2",
                                                         "left_arm", "only_unqualified")))
    check("M.structural_adapter_qualified_and_usable_in_production", r["structural_status"] and
          r["structural_production"] and r["structural_bounded"])
    exp = CPM.replace(b'PROD_BODY_RIG_STATUS = u"qualified"', b'PROD_BODY_RIG_STATUS = u"experimental"')
    r = M.check(exp, POSE_REG, BODY_REG, "p", "b")
    check("M.the_rc2_experimental_gate_fails", exp != CPM and not r["pass"] and not r["structural_production"])
    qual = CPM.replace(b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"')
    check("M.a_qualification_build_fails", qual != CPM and not M.check(qual, POSE_REG, BODY_REG, "p", "b")["pass"])
    one = CPM.replace(b"PROD_BODY_RIG_REVISIONS = (PROD_BODY_RIG_REVISION, PROD_BODY_RIG_LEAF_REVISION)",
                      b"PROD_BODY_RIG_REVISIONS = (PROD_BODY_RIG_REVISION,)")
    check("M.tails_revision_not_usable_fails", one != CPM and not M.check(one, POSE_REG, BODY_REG, "p", "b")["pass"])
    loose = CPM.replace(b'    return mode == u"production" and PROD_BODY_RIG_STATUS == u"qualified"',
                        b'    return True')
    check("M.an_unbounded_gate_fails", loose != CPM and
          not M.check(loose, POSE_REG, BODY_REG, "p", "b")["structural_bounded"])


# --- synthetic evidence ------------------------------------------------------------------------------------------

FD, TD = TEMPLATE["fox_dir"], TEMPLATE["tails_dir"]
FOX_ID, TAILS_ID = "a" * 32, "b" * 32
FOX_FILE = "Characters/%s/Poses/RC3 Fox--%s.json" % (FD, FOX_ID[:12])
TAILS_FILE = "Characters/%s/Poses/RC3 Tails--%s.json" % (TD, TAILS_ID[:12])


def line(n, text, op_id="-"):
    return "2026-11-19T00:00:%02d.000Z #%06d s=x w=1 op=%s | %s" % (n % 60, n, op_id, text)


def op(n, kind, animset, outcome, detail, label=None, rig=None):
    ctx = "None" if animset is None else "{'animset_id': (u'DmeAnimationSet', u'%s', 1, 2L), 'document_file_id': 0}" % animset
    out = [line(n * 10, "PROD_OPERATION_BEGIN id=%d kind=u'%s' context=%s" % (n, kind, ctx), n)]
    if rig is not None:
        out.append(line(n * 10 + 1, "PROD_POSE_BODY-RIG-%s %s" % (rig[0], json.dumps(rig[1])), n))
    if label:
        out.append(line(n * 10 + 2, "PROD_OPERATION_PHASE id=%d phase=u'native-commit' detail={u'label': u'%s'}"
                        % (n, label), n))
    out.append(line(n * 10 + 3, "PROD_OPERATION_OUTCOME id=%d kind=u'%s' outcome=u'%s' detail=%s"
                    % (n, kind, outcome, detail), n))
    return out


def applied():
    return "{'reason': None, 'verification': u'deferred', 'kind': u'pose', 'apply_phase': u'committed-verified'}"


def saved(pid):
    return "{'kind': u'pose', 'preset_id': u'%s'}" % pid


def fox_rig():
    return ("available", {"constraints": 36, "handles": 23, "written": 214})


def tails_rig(leaves=None):
    return ("available", {"constraints": 36, "handles": 23, "written": 238,
                          "simulated_leaves": A.LEAVES if leaves is None else leaves})


def default_log():
    return [op(1, "Refresh Models", None, "completed", "None"),
            op(2, "Save Pose", "foxmccouldwm2", "verified", saved(FOX_ID), rig=fox_rig()),
            op(3, "Pose Info", "foxmccouldwm2", "completed", "None"),
            op(4, "Apply Pose", "foxmccouldwm3", "verified", applied(), "Apply Pose RC3 Fox"),
            op(5, "Save Pose", "milestailsprower2", "verified", saved(TAILS_ID), rig=tails_rig()),
            op(6, "Pose Info", "milestailsprower2", "completed", "None"),
            op(7, "Apply Pose", "milestailsprower3", "verified", applied(), "Apply Pose RC3 Tails")]


def region(leaves):
    return {"descriptor": {"bones": [{"name": "rig_spine_1", "class": "rig-handle"}] +
                           [{"name": n, "class": "simulated-leaf"} for n in leaves]},
            "orientations": {"rig_spine_1_o": [0, 0, 0, 1], "Tail5_L_o": [0, 0, 0, 1]},
            "positions": {"rig_root_p": [0, 0, 0]}}


def default_records():
    fox = {"name": "RC3 Fox", "preset_id": FOX_ID,
           "pose": {"version": 2, "adapter": {"rule": "structural_rig_v1", "revision": 1},
                    "regions": {"full_body": region([])},
                    "source": {"rig_class": "structural_rig_v1", "model_ref": "models/fursonas/foxmccouldwm.mdl"}}}
    tails = {"name": "RC3 Tails", "preset_id": TAILS_ID,
             "pose": {"version": 2, "adapter": {"rule": "structural_rig_v1", "revision": 2},
                      "regions": {"full_body": region(A.LEAVES)},
                      "source": {"rig_class": "structural_rig_v1",
                                 "model_ref": "models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"}}}
    return fox, tails


def write_run(root, logs=None, records=None, build=None, extra_diffs=(), restored=True, modes_pass=True):
    q = os.path.join(root, "run")
    os.makedirs(os.path.join(q, "staged"))
    os.makedirs(os.path.join(q, "evidence", "logs"))
    ids = {"qualification_cpm_sha256": PINS["rc3_cpm_sha256"], "profile_sha256": PINS["profile_sha256"],
           "body_profile_sha256": PINS["body_profile_sha256"], "mode_equivalence": {"pass": modes_pass}}
    dump = lambda path, d: io.open(path, "w", encoding="utf-8").write(json.dumps(d))  # noqa: E731
    dump(os.path.join(q, "staged", "IDENTITIES.json"), ids)
    files = {}
    for i, ops in enumerate(logs if logs is not None else [default_log()]):
        name = "CPM - 2026-11-19_0%d-00-00Z - pid1 - x - 001.log" % i
        header = "SFM Character Preset Manager diagnostic log cpm-log-v1 | build_sha256=%s version=1.1.0" % (
            build or PINS["rc3_cpm_sha256"])
        with io.open(os.path.join(q, "evidence", "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join([header] + [x for o in ops for x in o]) + "\n")
        files[name] = "0" * 64
    dump(os.path.join(q, "evidence", "logs", "LOGS.json"), {"files": files})
    fox, tails = records or default_records()
    diffs = [{"status": "added", "path": FOX_FILE, "sha256": "1" * 64},
             {"status": "added", "path": TAILS_FILE, "sha256": "2" * 64},
             {"status": "added", "path": "Characters/%s/pose_sources.json" % FD, "sha256": "3" * 64},
             {"status": "added", "path": "Characters/%s/pose_sources.json" % TD, "sha256": "4" * 64}]
    diffs += list(extra_diffs)
    for rel, rec in ((FOX_FILE, fox), (TAILS_FILE, tails)):
        path = os.path.join(q, "evidence", "library_after", *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        dump(path, rec)
    dump(os.path.join(q, "evidence", "library_cleanup.json"),
         {"differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True})
    dump(os.path.join(q, "evidence", "restore.json"),
         {"restored": restored, "installation": "published" if restored else "other"})
    c = copy.deepcopy(TEMPLATE)
    c["paths"]["Q"] = q
    return c


def verdict_of(**kw):
    root = tempfile.mkdtemp(prefix="rc3s-test-")
    try:
        c = write_run(root, **kw)
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            A.run(c)
        finally:
            sys.stdout = stdout
        return read_json(os.path.join(c["paths"]["Q"], "evidence", "RC3S_VERDICT.json"))
    finally:
        shutil.rmtree(root)


def failed(v):
    return sorted(x["check"] for x in v["checks"] if not x["pass"])


def with_op(index, new):
    log = default_log()
    log[index] = new
    return [log]


def section_analyzer():
    v = verdict_of()
    check("A.complete_run_is_automated_smoke_pass", v["verdict"] == "AUTOMATED SMOKE PASS" and not failed(v))
    check("A.every_gate_is_evaluated", sorted(set(x["gate"] for x in v["checks"])) ==
          ["CLEAN", "DISPLAY", "EVIDENCE", "FOX", "TAILS", "TARGET"])
    # Refusals and failures.
    v = verdict_of(logs=with_op(1, op(2, "Save Pose", "foxmccouldwm2", "refused", "{'reason': u'rig-driven'}",
                                      rig=("unavailable", {"reason": "rig-driven"}))))
    check("A.refused_fox_save_is_smoke_fail", v["verdict"] == "SMOKE FAIL" and "saved_once" in failed(v) and
          "no_refusal_failure_or_recovery" in failed(v))
    v = verdict_of(logs=with_op(6, op(7, "Apply Pose", "milestailsprower3", "recovery-unverified",
                                      "{'apply_phase': u'recovery-unverified'}", "Apply Pose RC3 Tails")))
    check("A.unverified_tails_apply_is_smoke_fail", v["verdict"] == "SMOKE FAIL" and
          "applied_and_verified" in failed(v))
    v = verdict_of(logs=with_op(3, op(4, "Apply Pose", "foxmccouldwm3", "verified",
                                      "{'apply_phase': u'committed-unverified'}", "Apply Pose RC3 Fox")))
    check("A.committed_unverified_apply_fails", "applied_and_verified" in failed(v) and
          "no_refusal_failure_or_recovery" in failed(v))
    # Admission evidence.
    v = verdict_of(logs=with_op(1, op(2, "Save Pose", "foxmccouldwm2", "verified", saved(FOX_ID))))
    check("A.fox_save_without_structural_admission_fails", "save_admitted_by_the_structural_adapter" in failed(v))
    v = verdict_of(logs=with_op(4, op(5, "Save Pose", "milestailsprower2", "verified", saved(TAILS_ID),
                                      rig=tails_rig(A.LEAVES[:6]))))
    check("A.tails_admitted_with_six_leaves_fails", "save_admitted_by_the_structural_adapter" in failed(v))
    # Targeting.
    v = verdict_of(logs=with_op(3, op(4, "Apply Pose", "foxmccouldwm2", "verified", applied(), "Apply Pose RC3 Fox")))
    check("A.fox_applied_to_its_source_fails", "fox_applied_to_another_instance_of_the_same_model" in failed(v))
    v = verdict_of(logs=with_op(6, op(7, "Apply Pose", "milestailsprower1", "verified", applied(),
                                      "Apply Pose RC3 Tails")))
    check("A.tails_applied_to_the_peer_fails", "tails_applied_to_another_instance_of_the_same_model" in failed(v))
    v = verdict_of(logs=with_op(3, op(4, "Apply Pose", "milestailsprower3", "verified", applied(),
                                      "Apply Pose RC3 Fox")))
    check("A.fox_applied_to_a_tails_fails", "fox_applied_to_another_instance_of_the_same_model" in failed(v))
    v = verdict_of(logs=with_op(1, op(2, "Save Pose", "foxmccouldwm1", "verified", saved(FOX_ID), rig=fox_rig())))
    check("A.fox_saved_from_the_peer_fails", "fox_applied_to_another_instance_of_the_same_model" in failed(v))
    # Records.
    fox, tails = default_records()
    tails["pose"]["adapter"]["revision"] = 1
    check("A.tails_record_at_revision_1_fails", "record_is_structural_full_body" in
          failed(verdict_of(records=(fox, tails))))
    fox, tails = default_records()
    fox["pose"]["version"], fox["pose"]["adapter"] = 3, None
    check("A.fox_saved_as_generic_v3_fails", "record_is_structural_full_body" in
          failed(verdict_of(records=(fox, tails))))
    fox, tails = default_records()
    tails["pose"]["regions"]["full_body"]["orientations"]["Tail6_L_o"] = [0, 0, 0, 1]
    check("A.a_saved_leaf_value_fails", "record_leaves_described_without_values" in
          failed(verdict_of(records=(fox, tails))))
    fox, tails = default_records()
    tails["pose"]["regions"]["full_body"] = region(A.LEAVES[1:])
    check("A.a_missing_leaf_description_fails", "record_leaves_described_without_values" in
          failed(verdict_of(records=(fox, tails))))
    fox, tails = default_records()
    fox["pose"]["regions"]["full_body"] = region([u"ear3_L"])
    check("A.a_fox_with_a_leaf_fails", "record_leaves_described_without_values" in
          failed(verdict_of(records=(fox, tails))))
    # Display.
    log = default_log()
    del log[5]
    check("A.missing_pose_info_fails_display", "pose_info_opened_for_both" in failed(verdict_of(logs=[log])))
    # Evidence.
    check("A.another_build_is_incomplete", verdict_of(build="f" * 64)["verdict"] == "INCOMPLETE")
    check("A.two_logs_are_incomplete", verdict_of(logs=[default_log(), default_log()])["verdict"] == "INCOMPLETE")
    check("A.unexpected_library_file_is_incomplete", verdict_of(extra_diffs=[
        {"status": "changed", "path": "Characters/krystal2020--7d2aee52ef3a/Body Presets/Body--preset-d1c94.json",
         "sha256": "9" * 64}])["verdict"] == "INCOMPLETE")
    check("A.a_second_fox_pose_is_incomplete", verdict_of(extra_diffs=[
        {"status": "added", "path": "Characters/%s/Poses/RC3 Fox--%s.json" % (FD, "c" * 12),
         "sha256": "8" * 64}])["verdict"] == "INCOMPLETE")
    check("A.unrestored_installation_is_incomplete", verdict_of(restored=False)["verdict"] == "INCOMPLETE")
    check("A.failed_mode_check_is_incomplete", verdict_of(modes_pass=False)["verdict"] == "INCOMPLETE")


def section_pins():
    for rel, pin in (("tools/rc3s_analyze.py", "analyzer_sha256"), ("tools/rc3s_modes.py", "modes_sha256"),
                     ("PROCEDURE.md", "procedure_sha256")):
        with open(os.path.join(KIT, *rel.split("/")), "rb") as f:
            check("P.%s_is_pinned" % rel.replace("/", "_"), hashlib.sha256(f.read()).hexdigest() == PINS[pin])
    check("P.installed_build_is_the_rc3_cpm", PINS["qualification_cpm_sha256"] == PINS["rc3_cpm_sha256"] ==
          hashlib.sha256(CPM).hexdigest())
    with open(os.path.join(KIT, "PROCEDURE.md"), "rb") as f:
        proc = f.read().decode("utf-8")
    check("P.procedure_names_the_rc3_cpm_and_package", PINS["rc3_cpm_sha256"][:8] in proc and
          PINS["rc3_zip_sha256"][:8] in proc)


if __name__ == "__main__":
    section_modes()
    section_analyzer()
    section_pins()
    bad = [n for n, ok in RESULTS if not ok]
    print("%d/%d passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    sys.exit(1 if bad else 0)
