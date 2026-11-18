# -*- coding: utf-8 -*-
"""RC1S kit tests (offline, Python 3 -I): the production-mode equivalence check on the real RC1 CPM and registries,
and the analyzer's gates on synthetic evidence. usage: python -I test_rc1s.py"""
from __future__ import print_function

import copy
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
import rc1s_modes as M  # noqa: E402
import rc1s_analyze as A  # noqa: E402

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
TEMPLATE = read_json(os.path.join(KIT, "rc1s.template.json"))
PINS = TEMPLATE["pins"]


def section_modes():
    r = M.check(CPM, POSE_REG, BODY_REG, "p", "b")
    check("M.rc1_production_mode_equivalence_passes", r["pass"])
    check("M.generic_v3_usable_in_production", r["generic_v3"])
    check("M.carried_rule_unusable_in_both_modes", r["carried"])
    check("M.krystal_full_body_selected_in_production", r["krystal_v2"])
    check("M.only_the_experimental_right_arm_is_left_out", r["not_in_production"] ==
          [["right_arm", "krystal-v1", "krystal-v1", "experimental"]])
    qual = CPM.replace(b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"')
    check("M.a_qualification_build_fails_the_production_check", not M.check(qual, POSE_REG, BODY_REG, "p", "b")["pass"])
    exp = copy.deepcopy(BODY_REG)
    exp["mappings"][0]["status"], exp["mappings"][0]["evidence"] = "experimental", None
    r = M.check(CPM, POSE_REG, exp, "p", "b")
    check("M.an_experimental_full_body_registry_fails", not r["pass"] and not r["krystal_v2"])
    exp_rule = CPM.replace(b'{u"direct_fk_v1": {u"revision": 1, u"status": u"qualified"}}',
                           b'{u"direct_fk_v1": {u"revision": 1, u"status": u"experimental"}}')
    r = M.check(exp_rule, POSE_REG, BODY_REG, "p", "b")
    check("M.an_experimental_generic_rule_fails", exp_rule != CPM and not r["pass"] and not r["generic_v3"])
    on = CPM.replace(b"PROD_SCOPE_CARRIED_ENABLED = [False]", b"PROD_SCOPE_CARRIED_ENABLED = [True]")
    check("M.an_enabled_carried_rule_fails", on != CPM and not M.check(on, POSE_REG, BODY_REG, "p", "b")["carried"])


# --- synthetic evidence ------------------------------------------------------------------------------------------

KD, HD = TEMPLATE["character_dir"], TEMPLATE["heavy_dir"]
KR_ID, HV_ID = "a" * 32, "b" * 32
KR_FILE = "Characters/%s/Poses/RC1 Krystal--%s.json" % (KD, KR_ID[:12])
HV_FILE = "Characters/%s/Poses/RC1 Heavy--%s.json" % (HD, HV_ID[:12])


def line(n, text):
    return "2026-11-19T00:00:%02d.000Z #%06d s=x w=1 op=- | %s" % (n % 60, n, text)


def op(n, kind, animset, outcome, detail, label=None):
    ctx = "None" if animset is None else "{'animset_id': (u'DmeAnimationSet', u'%s', 1, 2L), 'document_file_id': 0}" % animset
    out = [line(n * 10, "PROD_OPERATION_BEGIN id=%d kind=u'%s' context=%s" % (n, kind, ctx))]
    if label:
        out.append(line(n * 10 + 1, "PROD_OPERATION_PHASE id=%d phase=u'native-commit' detail={u'label': u'%s'}"
                        % (n, label)))
    out.append(line(n * 10 + 2, "PROD_OPERATION_OUTCOME id=%d kind=u'%s' outcome=u'%s' detail=%s"
                    % (n, kind, outcome, detail)))
    return out


def applied():
    return "{'reason': None, 'verification': u'deferred', 'kind': u'pose', 'apply_phase': u'committed-verified'}"


def saved(pid):
    return "{'kind': u'pose', 'preset_id': u'%s'}" % pid


def default_logs():
    a = [op(1, "Refresh Models", None, "completed", "None"),
         op(2, "Pose Info", "Krystal", "completed", "None"),
         op(3, "Pose Info", "Krystal", "completed", "None"),
         op(4, "Apply Body Preset", "Krystal", "verified",
            "{'reason': None, 'verification': u'deferred', 'apply_phase': u'committed-verified'}", "Apply Body Preset"),
         op(5, "Save Pose", "Krystal", "verified", saved(KR_ID)),
         op(6, "Save Pose", "heavy1", "verified", saved(HV_ID)),
         op(7, "Apply Pose", "heavy2", "verified", applied(), "Apply Pose RC1 Heavy")]
    b = [op(1, "Pose Info", "Krystal", "completed", "None"),
         op(2, "Apply Pose", "Krystal", "verified", applied(), "Apply Pose RC1 Krystal"),
         op(3, "Apply Pose", "Krystal", "verified", applied(), "Apply Pose NQ1 Pose A")]
    return a, b


def default_records():
    kr = {"name": "RC1 Krystal", "preset_id": KR_ID,
          "pose": {"version": 2, "regions": {"full_body": {}}, "source": {"rig_class": "krystal-v1"}}}
    hv = {"name": "RC1 Heavy", "preset_id": HV_ID,
          "pose": {"version": 3, "engine": {"rule": "direct_fk_v1", "revision": 1, "carried_rule": None}}}
    return kr, hv


def write_run(root, logs=None, records=None, build=None, extra_diffs=(), restored=True, modes_pass=True):
    q = os.path.join(root, "run")
    os.makedirs(os.path.join(q, "staged"))
    os.makedirs(os.path.join(q, "evidence", "logs"))
    ids = {"qualification_cpm_sha256": PINS["rc1_cpm_sha256"], "profile_sha256": PINS["profile_sha256"],
           "body_profile_sha256": PINS["body_profile_sha256"], "mode_equivalence": {"pass": modes_pass}}
    dump = lambda path, d: io.open(path, "w", encoding="utf-8").write(json.dumps(d))  # noqa: E731
    dump(os.path.join(q, "staged", "IDENTITIES.json"), ids)
    dump(os.path.join(q, "evidence", "seed.json"), {"files": {}})
    a, b = logs or default_logs()
    files = {}
    for i, ops in enumerate((a, b)):
        if ops is None:
            continue
        name = "CPM - 2026-11-19_0%d-00-00Z - pid1 - x - 001.log" % i
        header = "SFM Character Preset Manager diagnostic log cpm-log-v1 | build_sha256=%s version=1.1.0" % (
            build or PINS["rc1_cpm_sha256"])
        with io.open(os.path.join(q, "evidence", "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join([header] + [x for o in ops for x in o]) + "\n")
        files[name] = "0" * 64
    dump(os.path.join(q, "evidence", "logs", "LOGS.json"), {"files": files})
    kr, hv = records or default_records()
    diffs = [{"status": "added", "path": "Characters/%s/Poses/K2 Pose--ac9d4962a2ae.json" % KD,
              "sha256": PINS["k2_pose_sha256"]},
             {"status": "added", "path": "Characters/%s/Poses/NQ1 Pose A--5273df2209ca.json" % KD,
              "sha256": PINS["legacy_pose_sha256"]},
             {"status": "added", "path": KR_FILE, "sha256": "1" * 64},
             {"status": "added", "path": HV_FILE, "sha256": "2" * 64},
             {"status": "added", "path": "Characters/%s/pose_sources.json" % KD, "sha256": "3" * 64},
             {"status": "added", "path": "Characters/%s/pose_sources.json" % HD, "sha256": "4" * 64}]
    diffs += list(extra_diffs)
    for rel, rec in ((KR_FILE, kr), (HV_FILE, hv)):
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
    root = tempfile.mkdtemp(prefix="rc1s-test-")
    try:
        c = write_run(root, **kw)
        stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            A.run(c)
        finally:
            sys.stdout = stdout
        return read_json(os.path.join(c["paths"]["Q"], "evidence", "RC1S_VERDICT.json"))
    finally:
        shutil.rmtree(root)


def failed(v):
    return sorted(x["check"] for x in v["checks"] if not x["pass"])


def section_analyzer():
    v = verdict_of()
    check("A.complete_run_is_automated_smoke_pass", v["verdict"] == "AUTOMATED SMOKE PASS" and not failed(v))
    a, b = default_logs()
    b[2] = op(3, "Apply Pose", "Krystal", "no-op", "{'kind': u'pose', 'apply_phase': u'no-op'}")
    check("A.selected_parts_no_op_still_passes", verdict_of(logs=(a, b))["verdict"] == "AUTOMATED SMOKE PASS")
    a, b = default_logs()
    b[1] = op(2, "Apply Pose", "Krystal", "refused", "{'kind': u'pose', 'reason': u'rig-driven'}")
    v = verdict_of(logs=(a, b))
    check("A.refused_krystal_apply_is_smoke_fail", v["verdict"] == "SMOKE FAIL" and
          "applied_in_process_b" in failed(v) and "no_refusal_failure_or_recovery" in failed(v))
    a, b = default_logs()
    a[6] = op(7, "Apply Pose", "heavy1", "verified", applied(), "Apply Pose RC1 Heavy")
    check("A.heavy_applied_to_its_source_fails", "applied_to_another_heavy" in failed(verdict_of(logs=(a, b))))
    a, b = default_logs()
    a[3] = op(4, "Apply Body Preset", "Krystal", "failed", "{'reason': u'x'}")
    check("A.failed_body_preset_is_smoke_fail", verdict_of(logs=(a, b))["verdict"] == "SMOKE FAIL")
    kr, hv = default_records()
    hv["pose"]["engine"]["carried_rule"] = "constant_channel_carried_v1"
    check("A.carried_rule_in_heavy_record_fails", "record_is_generic_v3" in failed(verdict_of(records=(kr, hv))))
    kr, hv = default_records()
    kr["pose"]["version"] = 3
    check("A.krystal_saved_as_generic_v3_fails", "record_is_version_2_full_body" in
          failed(verdict_of(records=(kr, hv))))
    check("A.another_build_is_incomplete", verdict_of(build="f" * 64)["verdict"] == "INCOMPLETE")
    check("A.unexpected_library_file_is_incomplete", verdict_of(extra_diffs=[
        {"status": "changed", "path": "Characters/%s/Body Presets/Body--preset-d1c94.json" % KD,
         "sha256": "9" * 64}])["verdict"] == "INCOMPLETE")
    check("A.unrestored_installation_is_incomplete", verdict_of(restored=False)["verdict"] == "INCOMPLETE")
    check("A.failed_mode_check_is_incomplete", verdict_of(modes_pass=False)["verdict"] == "INCOMPLETE")
    a, b = default_logs()
    check("A.one_log_only_is_incomplete", verdict_of(logs=(a + b, None))["verdict"] == "INCOMPLETE")
    a, b = default_logs()
    del a[2]
    check("A.missing_pose_info_fails_display", "pose_info_opened" in failed(verdict_of(logs=(a, b))))


def section_pins():
    import hashlib
    for rel, pin in (("tools/rc1s_analyze.py", "analyzer_sha256"), ("tools/rc1s_modes.py", "modes_sha256"),
                     ("PROCEDURE.md", "procedure_sha256")):
        with open(os.path.join(KIT, *rel.split("/")), "rb") as f:
            check("P.%s_is_pinned" % rel.replace("/", "_"), hashlib.sha256(f.read()).hexdigest() == PINS[pin])
    check("P.installed_build_is_the_rc1_cpm", PINS["qualification_cpm_sha256"] == PINS["rc1_cpm_sha256"] ==
          hashlib.sha256(CPM).hexdigest())


if __name__ == "__main__":
    section_modes()
    section_analyzer()
    section_pins()
    bad = [n for n, ok in RESULTS if not ok]
    print("%d/%d passed" % (len(RESULTS) - len(bad), len(RESULTS)))
    sys.exit(1 if bad else 0)
