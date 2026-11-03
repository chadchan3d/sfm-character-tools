# -*- coding: utf-8 -*-
"""M-06 W2: Astra's counterexamples, reproduced against a W2 instrument tree (offline; fakes only, not native).

usage: python -B counterexamples.py W2_ROOT RESULTS.json SCAN_FIXTURE.dmx

W2_ROOT is either the previous W2 instruments (package a9619ee1) or the corrected candidate. Each scenario is built
with that tree's own fake scene, core, comparator, probe and scripts, and reports the outcome that tree produces.
A previous-tree outcome of PASS / PROCEED is the reproduced defect; the corrected tree must refuse each one.
Run once per tree; tools are never imported from this file's own directory. SCAN_FIXTURE.dmx is a synthetic
fixture whose scale graph has output mode 1; when it does not exist it is written with the tree's own fixture
writer (only the corrected tree's writer can set the output mode), so run the corrected tree first.
"""
from __future__ import print_function

import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import traceback
import types
import hashlib

ROOT = os.path.abspath(sys.argv[1])
RESULTS, SCAN_FIXTURE = os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
sys.argv = [sys.argv[0]]
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "tests")):
    sys.path.insert(0, p)
import test_m06w2 as T  # noqa: E402  (the tree's own suite module: fakes, core loader and helpers)

F, C, CP = T.F, T.C, T.CP
W1_SHA256 = "fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
SPEC = {"undo_desc": "Apply Body Preset", "flex": {"Muscles": {"mono": {"effective": 0.8}}},
        "bones": {"bip_head": {"scale": 1.5, "control_value": 0.15, "graph": "existing"}}}


ORDINARY = "m06w2_config.json"


def observe(w, cfg=None, watch=None, ordinary=False):
    if ordinary:
        try:
            return T.observe(w, cfg, watch=watch, config_name=ORDINARY)
        except TypeError:
            pass
    return T.observe(w, cfg, watch=watch)


def fired_record(w, baseline):
    during = observe(w, ordinary=True)
    created = T.CORE_NS["created_elements"](baseline, during)
    return {"event": "fired", "injector": "v3", "candidate_sha256": W1_SHA256, "baseline": baseline,
            "in_transaction": during, "created": created["created"],
            "memberships_added": created["memberships_added"],
            "scale_attributes_created": created["scale_attributes_created"],
            "peer_changes": created["peer_changes"]}


def applied():
    w = F.twin_world()
    a = observe(w)
    T.apply_change(w)
    return w, a


LAST = {"reasons": []}


def v(inv, a, b, spec=None):
    """The comparator's decision and the first reason it gives. Every reason is kept, so main() can report whether
    the safeguard a scenario targets (TARGETED below) is among them: an unrelated earlier refusal cannot stand in for
    the check under test."""
    verdict, reasons = C.compare(inv, a, b, spec)
    LAST["reasons"] = list(reasons)
    return verdict + (" [%s]" % reasons[0][:150] if reasons else "")


# ---- Finding 1 -----------------------------------------------------------------------------------------------------

def f1a_unreadable_curveinfo():
    w = F.twin_world()
    a = observe(w)
    T.target(w)["flex"]["Legsize"][1].log.layers[0].lying_presence.add("curveinfo")
    b = observe(w)
    return "complete=%s; unchanged %s" % (b["complete"], v("unchanged", a, b))


def f1b_omitted_log_layers():
    w = F.twin_world()
    a = observe(w)
    b = copy.deepcopy(a)
    for o in (a, b):
        o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["layers"][0].pop("keys")
        o["target"]["flex"]["Legsize"]["mono"]["log"]["v"].pop("log")
    return "complete=%s; unchanged %s" % (a["complete"], v("unchanged", a, b))


def f1c_omitted_evaluation():
    w = F.twin_world()
    a = observe(w)
    b = copy.deepcopy(a)
    for o in (a, b):
        o["target"]["flex"]["Legsize"]["mono"]["log"]["v"].pop("evaluated")
        o["target"]["graphs"][0]["inputs"][0]["log"]["v"].pop("evaluated")
    return "complete=%s; unchanged %s" % (a["complete"], v("unchanged", a, b))


def f1d_mismatching_cpm():
    w = F.twin_world()
    d = tempfile.mkdtemp()
    try:
        other = os.path.join(d, "other_cpm.py")
        with open(other, "wb") as f:
            f.write(b"not the accepted candidate")
        cfg = dict(F.CONFIG, cpm={"path": other, "sha256": W1_SHA256})
        a, b = observe(w, cfg), observe(w, cfg)
    finally:
        shutil.rmtree(d, True)
    return "complete=%s; unchanged %s" % (b["complete"], v("unchanged", a, b))


# ---- Finding 2 -----------------------------------------------------------------------------------------------------

def f2a_evaluated_flex_value():
    w, a = applied()
    b = observe(w)
    side = b["target"]["flex"]["Muscles"]["mono"]
    side["log"]["v"]["evaluated"]["v"] = 0.81
    side["representation"]["v"] = "OTHER"
    return "apply %s" % v("apply", a, b, SPEC)


def f2b_log_default():
    w, a = applied()
    T.target(w)["flex"]["Muscles"][1].log.attrs["defaultvalue"] = 0.9
    return "apply %s" % v("apply", a, observe(w), SPEC)


def f2c_log_identity():
    w, a = applied()
    ch = T.target(w)["flex"]["Muscles"][1]
    ch.log = F.Log(w, ch.name, [list(k) for k in ch.log.layers[0].keys])
    ch.attrs["log"] = ch.log
    return "apply %s" % v("apply", a, observe(w), SPEC)


def f2d_undeclared_stereo_side():
    w = F.twin_world()
    a = observe(w)
    T.apply_change(w)
    ctl = [c for c in T.target(w)["controls"] if c.name == "Breastsize"][0]
    for side, val in (("left", 0.4), ("right", 0.45)):
        ch = ctl.attrs[side + "valuechannel"]
        ch.log.layers[0].keys[0][1] = val
        ch.attrs["toElement"].set("flexWeight", val)
    spec = dict(SPEC, flex={"Muscles": {"mono": {"effective": 0.8}}, "Breastsize": {"left": {"effective": 0.4}}})
    return "apply %s" % v("apply", a, observe(w), spec)


def f2e_scale_expression():
    w, a = applied()
    T.target(w)["graph"]["expr"].set("expr", "lerp(value, lo, hi) * 2")
    return "apply %s" % v("apply", a, observe(w), SPEC)


def f2f_scale_control_source():
    w, a = applied()
    T.target(w)["graph"]["control"].set("value", 0.16)
    return "apply %s" % v("apply", a, observe(w), SPEC)


# ---- Finding 3 -----------------------------------------------------------------------------------------------------

def aborted_world():
    w = F.twin_world()
    a = observe(w, ordinary=True)
    g = w.scale_graph(T.target(w), "bip_hand_l", control_value=0.2, physical=2.0)
    fired = fired_record(w, a)
    w.remove_graph(T.target(w))
    return w, a, g, fired


def f3a_missing_creation_entry():
    w, a, g, fired = aborted_world()
    w.elements[g["expr"].h] = g["expr"]                       # the operator survives, resolvable
    fired["created"] = [r for r in fired["created"] if r["role"] != "operator"]
    return "aborted %s" % v("aborted", a, observe(w, watch=fired["created"], ordinary=True), fired)


def f3b_surviving_log_and_layer():
    w, a, g, fired = aborted_world()
    for el in (g["out"].log, g["out"].log.layers[0]):
        w.elements[el.h] = el                                 # created log and layer survive, resolvable
    return "aborted %s" % v("aborted", a, observe(w, watch=fired["created"], ordinary=True), fired)


def f3c_incomplete_fired_record():
    w, a, g, fired = aborted_world()
    return "aborted %s" % v("aborted", a, observe(w, watch=fired["created"], ordinary=True), {"created": fired["created"]})


def f3d_contradictory_identities():
    w, a, g, fired = aborted_world()
    fired["baseline"] = observe(F.twin_world(), ordinary=True)      # another instance; same configuration
    return "aborted %s" % v("aborted", a, observe(w, watch=fired["created"], ordinary=True), fired)


def f3e_recorded_peer_mutation():
    w, a, g, fired = aborted_world()
    fired["peer_changes"] = ["krystal_peer"]
    return "aborted %s" % v("aborted", a, observe(w, watch=fired["created"], ordinary=True), fired)


# ---- Finding 4 -----------------------------------------------------------------------------------------------------

class ProbeRunner(T.TestProbes):
    def runTest(self):
        pass


def probe_pair(after_change):
    runner = ProbeRunner()
    if hasattr(ProbeRunner, "setUpClass"):
        ProbeRunner.setUpClass()
    try:
        w = F.twin_world()
        before = runner.probe(w)
        after_change(w)
        after = runner.probe(w)
    finally:
        if hasattr(ProbeRunner, "tearDownClass"):
            ProbeRunner.tearDownClass()
    d = tempfile.mkdtemp()
    try:
        pa, pb = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        for path, p in ((pa, before), (pb, after)):
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(p).encode("ascii").decode("ascii"))
        out = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            code = CP.main(["x", pa, pb])
        finally:
            sys.stdout = out
    finally:
        shutil.rmtree(d, True)
    return "PROBE ACCEPTANCE %s" % ("PASS" if code == 0 else "FAIL")


def f4a_unreadable_file_id():
    def broken():
        raise RuntimeError("GetFileId unreadable (fake)")

    def change(w):
        w.document.GetFileId = broken
        w.shot.GetFileId = broken
    return probe_pair(change)


def f4b_peer_only_change():
    def change(w):
        p = T.peer(w)
        sets = w.shot.attrs["animationSets"]
        sets[sets.index(p["animset"])] = F.El(w, "DmeAnimationSet", "krystal_peer", **p["animset"].attrs)
    return probe_pair(change)


def f4c_empty_presence_coverage():
    def change(w):
        for inst in w.instances.values():
            inst["animset"].attrs["controls"] = []          # nothing examined after the reopen
        for inst in w.instances.values():
            inst["animset"].uid = F.UniqueId(inst["animset"].uid.text + "-reopened")
    return probe_pair(change)


# ---- Finding 5 -----------------------------------------------------------------------------------------------------

def f5a_config_selection():
    with open(os.path.join(ROOT, "instruments", "M06_Qualification_Observer.py"), "rb") as f:
        src = f.read()
    import stage_instruments as ST
    d = tempfile.mkdtemp()
    try:
        paths = []
        for tpl in ("m06w2_config.template.json", "m06w2_deferred_config.template.json"):
            with io.open(os.path.join(ROOT, "config", tpl), encoding="utf-8") as f:
                text = f.read()
            for a, b in (("<SFM game>", "G:/SFM"), ("<QUAL_DIR>", "G:/Q"), ("<protected original session>", "G:/o.dmx"),
                         ("<protected M-05 fixture>", "G:/m05.dmx"), ("<sha256>", "0" * 64)):
                text = text.replace(a, b)
            paths.append(os.path.join(d, tpl))
            with io.open(paths[-1], "w", encoding="utf-8") as f:
                f.write(text)
        out = ST.stage(paths[0], os.path.join(d, "out"), paths[1])
        staged = sorted(n for n in os.listdir(out) if n.endswith("Observer.py"))
        reads = []
        for n in staged:
            with open(os.path.join(out, n), "rb") as f:
                s = f.read()
            reads.append("%s reads %s" % (n, "m06w2_deferred_config.json" if b'"m06w2_deferred_config.json"' in s
                                          else "m06w2_config.json"))
    finally:
        shutil.rmtree(d, True)
    return "; ".join(reads) + ("" if b"<CONFIG_NAME>" in src else "; no deferred-configuration Observer")


class PrepRunner(T.TestDeferredFixture):
    def runTest(self):
        pass


def run_preparation(world, finish_extra=None):
    r = PrepRunner()
    r.setUp()
    try:
        idir, cfg, saved = r.prep_env(world)
        cmp_src = os.path.join(ROOT, "tools", "compare_obs.py")
        if not os.path.isfile(os.path.join(idir, "compare_obs.py")):
            shutil.copy2(cmp_src, os.path.join(idir, "compare_obs.py"))
        if finish_extra is not None:
            finish = world.dm.FinishUndo

            def stray():
                finish_extra(world)
                finish()
            world.dm.FinishUndo = stray
        shown = []
        sys.modules["PySide.QtGui"].QMessageBox.information = staticmethod(lambda *a: shown.append(a[2]))
        r.run_prep(idir, saved)
        out = r.outputs(cfg)
    finally:
        r.tearDown()
    said_save = any("Save As" in m for m in shown)
    return out, said_save


def f5b_output_mode_1_graph():
    w = F.World()
    try:
        w.instance("krystal_target", with_scale_graph=True, graph_output_mode=1)
    except TypeError:
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True)   # the previous fake's graph output mode is 1
    w.instance("krystal_peer", muscles_key=0.5, legsize=0.25)
    mode = w.instances["krystal_target"]["graph"]["out"].attrs["mode"]
    out, said_save = run_preparation(w)
    return "graph output mode %r: %s" % (mode, ("STOP: " + out["stop"]["stop"][:70]) if "stop" in out else
                                         "PROCEEDED (stored source changed; Save As instructed=%s)" % said_save)


def f5c_scanner_output_mode_1():
    import scan_deferred_fixture as SCAN
    if not os.path.isfile(SCAN_FIXTURE):
        T.fixture_dmx(SCAN_FIXTURE, graph_output_mode=1)
    r = SCAN.scan(SCAN_FIXTURE, "shot10", "Krystal", ["Muscles"])
    return "intact graphs %d; stop %s" % (sum(1 for g in r.get("scale_graphs", []) if g["intact"]), r["stop"] or "none")


def f5d_save_as_before_prepared_pass():
    w = F.twin_world()
    out, said_save = run_preparation(w, finish_extra=lambda w: w.set_flex(T.target(w), "Muscles", 0.5))
    return "%s; Save As instructed=%s" % (("STOP: " + out["stop"]["stop"][:60]) if "stop" in out else "no stop record",
                                         said_save)


# ---- Finding 6 -----------------------------------------------------------------------------------------------------

def f6_empty_log_preset():
    w = F.twin_world()
    ctl, ch, op = T.target(w)["flex"]["Legsize"]
    ch.log.layers[0].keys[:] = []                          # a valid EMPTY log: evaluates its default = stored
    ch.log.attrs["defaultvalue"] = ctl.attrs["value"]
    op.set("flexWeight", ctl.attrs["value"])
    o = observe(w)
    rows = [{"bone_index": b["index"], "bone_name": b["name"],
             "value": b["scale"]["v"] if b["scale"]["s"] == "present" else 1.0} for b in o["target"]["bones"]]
    values = {}
    for lit, row in o["target"]["flex"].items():
        sides = ("mono",) if row["shape"] == "MONO" else ("left", "right")
        vals = {}
        for s in sides:
            keys = row[s]["log"]["v"]["layers"][0]["keys"]["v"]
            vals[s] = keys[0][1] if keys else row[s]["stored"]["v"]
        values["flex." + lit] = vals
    return "representation %s; preset %s" % (o["target"]["flex"]["Legsize"]["mono"]["representation"]["v"],
                                             v("preset", o, {"bone_scales": rows, "values": values}))


# ---- Astra's final W2 review: R1 compressed data, R2A empty output log, R2B EMPTY -> one key, R3 configuration ------

INVALID_COMPRESSED = bytes(bytearray(range(231, 256)))          # 25 invalid compressed-data bytes


def production_apply(w, muscles=0.8, control_value=0.15, scale=1.5):
    """A Body Apply as W1 fd853661 performs it: write_side for Muscles; prod_bs_write_existing_scale() for bip_head
    (input key 0 and source control value, then the input channel operates; the expression evaluates and the bone
    takes the result). The output log is never written."""
    t = T.target(w)
    w.set_flex(t, "Muscles", muscles)
    g = t["graph"]
    g["in"].log.layers[0].keys[0][1] = control_value
    g["control"].set("value", control_value)
    g["expr"].set("value", control_value)
    g["expr"].set("result", scale)
    g["bone"].set("scale", scale)
    w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset", can_redo=False, redo_desc="")


def m05_world():
    """The accepted M-05 graph topology on the twin scene: the mode-3 output log is empty with usedefaultvalue False
    (built directly on the tree's own fake, so the previous tree's fake can carry it too)."""
    w = F.twin_world()
    g = T.target(w)["graph"]
    g["out"].set("mode", 3)
    g["out"].log.layers[0].keys[:] = []
    g["out"].log.attrs.update(usedefaultvalue=False, defaultvalue=0.0)
    return w


FLEX_SPEC = {"undo_desc": "Apply Body Preset", "flex": {"Muscles": {"mono": {"effective": 0.8, "stored": 0.8}}},
             "bones": {}}


def flex_apply():
    w = F.twin_world()
    a = observe(w)
    w.set_flex(T.target(w), "Muscles", 0.8, stored=0.8)        # write_side: key 0 and the stored source
    w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset", can_redo=False, redo_desc="")
    return w, a


def g1a_compressed_injection():
    w, a = flex_apply()
    T.target(w)["flex"]["Muscles"][1].log.layers[0].attrs["compressed"] = INVALID_COMPRESSED
    return "apply %s" % v("apply", a, observe(w), FLEX_SPEC)


def g1b_compressed_record_edit():
    w, a = flex_apply()
    b = observe(w)
    b["target"]["flex"]["Muscles"]["mono"]["log"]["v"]["layers"][0]["compressed"] = {"s": "present", "v": {
        "length": 25, "sha256": hashlib.sha256(INVALID_COMPRESSED).hexdigest()}}
    b = json.loads(json.dumps(b))                    # as an observation file is read: JSON text, one string type
    return "apply %s" % v("apply", a, b, FLEX_SPEC)


def g1c_valid_apply():
    w, a = flex_apply()
    return "apply %s" % v("apply", a, observe(w), FLEX_SPEC)


def g2a_empty_output_log_apply():
    w = m05_world()
    a = observe(w)
    production_apply(w)
    b = observe(w)
    out = b["target"]["graphs"][0]["output"]["log"]["v"]
    return "output evaluated %r, physical 1.5; apply %s" % (out["evaluated"]["v"], v("apply", a, b, SPEC))


def g2a_neg_physical():
    w = m05_world()
    a = observe(w)
    production_apply(w)
    T.target(w)["graph"]["bone"].set("scale", 1.6)
    return "apply %s" % v("apply", a, observe(w), SPEC)


def g2a_neg_output_key():
    w = m05_world()
    a = observe(w)
    production_apply(w)
    T.target(w)["graph"]["out"].log.layers[0].keys[:] = [[0, 1.5]]
    return "apply %s" % v("apply", a, observe(w), SPEC)


def empty_legsize_world():
    w = m05_world()
    ctl, ch, op = T.target(w)["flex"]["Legsize"]
    ch.log.layers[0].keys[:] = []                             # admitted EMPTY: evaluates its default = stored
    ch.log.attrs["defaultvalue"] = ctl.attrs["value"]
    op.set("flexWeight", ctl.attrs["value"])
    return w


def empty_write(w, desired, key_time=0):
    ctl, ch, op = T.target(w)["flex"]["Legsize"]               # CPM write_side, EMPTY origin
    ctl.set("value", desired)
    ch.log.layers[0].keys[:] = [[key_time, desired]]
    op.set("flexWeight", desired)
    w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset", can_redo=False, redo_desc="")


EMPTY_SPEC = {"undo_desc": "Apply Body Preset", "flex": {"Legsize": {"mono": {"effective": 0.55, "stored": 0.55}}},
              "bones": {}}


def g2b_empty_to_one_key():
    w = empty_legsize_world()
    a = observe(w)
    empty_write(w, 0.55)
    origin = C.representation_of(a["target"]["flex"]["Legsize"]["mono"]) if hasattr(C, "representation_of") \
        else a["target"]["flex"]["Legsize"]["mono"]["representation"].get("v")
    return "origin %s; apply %s" % (origin, v("apply", a, observe(w), EMPTY_SPEC))


def g2b_neg_extra_key():
    w = empty_legsize_world()
    a = observe(w)
    empty_write(w, 0.55)
    T.target(w)["flex"]["Legsize"][1].log.layers[0].keys.append([100, 0.55])
    return "apply %s" % v("apply", a, observe(w), EMPTY_SPEC)


def g2b_neg_time():
    w = empty_legsize_world()
    a = observe(w)
    empty_write(w, 0.55, key_time=5)
    return "apply %s" % v("apply", a, observe(w), EMPTY_SPEC)


def g2b_neg_undeclared():
    w = empty_legsize_world()
    a = observe(w)
    empty_write(w, 0.55)
    return "apply %s" % v("apply", a, observe(w), dict(EMPTY_SPEC, flex={}))


def filled_template(d, template, name):
    with io.open(os.path.join(ROOT, "config", template), encoding="utf-8") as f:
        text = f.read()
    for a, b in (("<SFM game>", "G:/SFM"), ("<QUAL_DIR>", "G:/Q"), ("<protected original session>", "G:/o.dmx"),
                 ("<protected M-05 fixture>", "G:/m05.dmx"), ("<sha256>", "0" * 64)):
        text = text.replace(a, b)
    path = os.path.join(d, name)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def handoff(work):
    """This tree's real staged chain: ordinary Observer (A) -> Abort Injector armed and fired inside the Apply ->
    abort -> ordinary Observer (B, with the watch list)."""
    import stage_instruments as ST
    w = F.twin_world()
    out = ST.stage(filled_template(work, "m06w2_config.template.json", "main.json"), os.path.join(work, "staged"),
                   filled_template(work, "m06w2_deferred_config.template.json", "deferred.json"))
    obs = os.path.join(work, "obs")
    for cname in ("m06w2_config.json", "m06w2_deferred_config.json"):
        p = os.path.join(out, cname)
        with io.open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.update(observation_dir=obs, cpm={"path": T.W1_APP, "sha256": W1_SHA256}, shot="shot12",
                   target_animset="krystal_target", peers=["krystal_peer"], body=F.CONFIG["body"],
                   nonbody=F.CONFIG["nonbody"], protected={}, watch_path=os.path.join(obs, "watch.json"),
                   injector={"target_literal": "Muscles"}, instrument_files={})
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
    sfm, vs = w.modules()
    cpm = types.ModuleType("chadchan3d_cpm_app")

    def write_side(binding, side, origin, desired):
        w.set_flex(T.target(w), binding["literal"], desired)
    cpm.write_side = write_side
    mods = {"sfmApp": types.ModuleType("sfmApp"), "vs": types.ModuleType("vs"), "PySide": types.ModuleType("PySide"),
            "chadchan3d_cpm_app": cpm}
    mods["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
    mods["vs"].g_pDataModel, mods["vs"].tier1 = vs.g_pDataModel, vs.tier1

    def run(name):
        path = os.path.join(out, name)
        with open(path, "rb") as f:
            src = re.sub(b'INSTRUMENT_DIR = u"[^"\\n]*"', b"INSTRUMENT_DIR = u" + repr(out).lstrip("u").encode("utf-8")
                         .replace(b"\\\\", b"\\\\\\\\"), f.read())
        saved = dict((k, sys.modules.get(k)) for k in list(mods) + ["PySide.QtGui"])
        sys.modules.update(mods)
        sys.modules.pop("PySide.QtGui", None)
        stdout = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
            return sys.stdout.getvalue()
        finally:
            sys.stdout = stdout
            for k, val in saved.items():
                if val is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = val

    def latest(prefix, suffix=".json"):
        names = sorted(n for n in os.listdir(obs) if n.startswith(prefix) and n.endswith(suffix))
        with io.open(os.path.join(obs, names[-1]), encoding="utf-8") as f:
            return json.load(f)
    run("M06_Qualification_Observer.py")
    a = latest("obs_")
    armed = run("M06_Qualification_Abort_Injector.py")
    if "ARMED" not in armed:
        return None, None, None, "injector did not arm: " + armed.strip()[:120]
    w.scale_graph(T.target(w), "bip_hand_l", control_value=0.2, physical=2.0)
    try:
        cpm.write_side({"literal": "Muscles"}, "mono", 0.6995, 0.8)
    except RuntimeError:
        pass
    w.remove_graph(T.target(w))
    w.set_flex(T.target(w), "Muscles", 0.6995)
    run("M06_Qualification_Observer.py")
    return a, latest("obs_"), latest("injector_", "_fired.json"), None


def g3_config_handoff():
    work = tempfile.mkdtemp(prefix="cx_handoff_")
    try:
        a, b, fired, problem = handoff(work)
        if problem:
            return problem
        names = [a.get("config_name"), fired["baseline"].get("config_name"),
                 fired["in_transaction"].get("config_name"), b.get("config_name")]
        return "config_name A/baseline/in-transaction/B %r; aborted %s" % (names, v("aborted", a, b, fired))
    finally:
        shutil.rmtree(work, True)


def g3_neg_omitted():
    work = tempfile.mkdtemp(prefix="cx_handoff_")
    try:
        a, b, fired, problem = handoff(work)
        if problem:
            return problem
        fired = copy.deepcopy(fired)
        fired["in_transaction"]["config_name"] = None
        return "aborted %s" % v("aborted", a, b, fired)
    finally:
        shutil.rmtree(work, True)


# ---- Astra's configuration-digest ruling: config_sha256 must be a genuine SHA-256 text in every observation --------

def digest_case(mutate):
    """The real staged handoff evidence (A, injector baseline, in-transaction, B) with config_sha256 rewritten."""
    work = tempfile.mkdtemp(prefix="cx_digest_")
    try:
        a, b, fired, problem = handoff(work)
        if problem:
            return problem
        four = [a, fired["baseline"], fired["in_transaction"], b]
        mutate(four)
        return "digests %r; aborted %s" % ([o.get("config_sha256") if not isinstance(o.get("config_sha256"), str) or
                                            len(o.get("config_sha256")) < 20 else o.get("config_sha256")[:8] + "..."
                                            for o in four], v("aborted", a, b, fired))
    finally:
        shutil.rmtree(work, True)


def set_all(value):
    def mutate(four):
        for o in four:
            o["config_sha256"] = value
    return mutate


def h4_one_contradictory(four):
    d = four[0]["config_sha256"]
    four[2]["config_sha256"] = ("f" if d[0] != "f" else "e") + d[1:]      # valid format, contradicts the others


def h5_actual(four):
    pass


TARGETED = {
    "F1a": "curveinfo", "F1b": "required field missing", "F1c": "evaluated", "F1d": "cpm",
    "F2a": "evaluated 0.81", "F2b": "defaultvalue", "F2c": "channel_log_attribute", "F2d": "Breastsize/right",
    "F2e": "operator_attributes/expr", "F2f": "scale control source", "F3a": "does not reconcile",
    "F3b": "still resolvable", "F3c": "complete fired record", "F3d": "identity differs",
    "F3e": "peer changed", "G1a": "/compressed/", "G1b": "/compressed/", "G2a-n1": "physical scale",
    "G2a-n2": "output log", "G2b-n1": "exactly one key", "G2b-n2": "time zero", "G2b-n3": "undeclared",
    "G3-n1": "configuration identity",
    "H1": "is not a SHA-256 digest", "H2": "is not a SHA-256 digest", "H3": "is not a SHA-256 digest",
    "H4": "taken with different configurations",
}

SCENARIOS = [
    ("F1a", "unreadable curveinfo", f1a_unreadable_curveinfo),
    ("F1b", "omitted nested log/layer records", f1b_omitted_log_layers),
    ("F1c", "omitted evaluation records", f1c_omitted_evaluation),
    ("F1d", "mismatching CPM identity", f1d_mismatching_cpm),
    ("F2a", "changed evaluated flex value", f2a_evaluated_flex_value),
    ("F2b", "changed log default", f2b_log_default),
    ("F2c", "changed log identity", f2c_log_identity),
    ("F2d", "undeclared stereo side changed", f2d_undeclared_stereo_side),
    ("F2e", "changed scale expression", f2e_scale_expression),
    ("F2f", "scale control source value not the declared value", f2f_scale_control_source),
    ("F3a", "missing creation entry (operator survives)", f3a_missing_creation_entry),
    ("F3b", "created log and layer survive the abort", f3b_surviving_log_and_layer),
    ("F3c", "incomplete fired record", f3c_incomplete_fired_record),
    ("F3d", "contradictory baseline identity", f3d_contradictory_identities),
    ("F3e", "recorded peer mutation", f3e_recorded_peer_mutation),
    ("F4a", "GetFileId() unreadable after reopen", f4a_unreadable_file_id),
    ("F4b", "peer-only change", f4b_peer_only_change),
    ("F4c", "empty presence coverage", f4c_empty_presence_coverage),
    ("F5a", "configuration selection", f5a_config_selection),
    ("F5b", "preparation on an output-mode-1 graph", f5b_output_mode_1_graph),
    ("F5c", "scanner on an output-mode-1 graph", f5c_scanner_output_mode_1),
    ("F5d", "Save As before a prepared PASS", f5d_save_as_before_prepared_pass),
    ("F6", "valid EMPTY log preset", f6_empty_log_preset),
    ("G1a", "R1: 25 invalid compressed bytes in the changed flex layer", g1a_compressed_injection),
    ("G1b", "R1: compressed record edited in B (self-consistent)", g1b_compressed_record_edit),
    ("G1c", "R1 positive: valid authorized Apply", g1c_valid_apply),
    ("G2a", "R2A positive: Apply on the M-05 empty output log", g2a_empty_output_log_apply),
    ("G2a-n1", "R2A negative: physical scale not lerp(control)", g2a_neg_physical),
    ("G2a-n2", "R2A negative: a key written into the output log", g2a_neg_output_key),
    ("G2b", "R2B positive: EMPTY origin -> one key at zero", g2b_empty_to_one_key),
    ("G2b-n1", "R2B negative: extra key", g2b_neg_extra_key),
    ("G2b-n2", "R2B negative: key not at time zero", g2b_neg_time),
    ("G2b-n3", "R2B negative: EMPTY write undeclared", g2b_neg_undeclared),
    ("G3", "R3 positive: real Observer -> Injector -> comparator", g3_config_handoff),
    ("G3-n1", "R3 negative: in-transaction configuration omitted", g3_neg_omitted),
    ("H1", "R4: all four config digests null", lambda: digest_case(set_all(None))),
    ("H2", "R4: all four config digests empty", lambda: digest_case(set_all(""))),
    ("H3", "R4: all four config digests 'fabricated'", lambda: digest_case(set_all("fabricated"))),
    ("H4", "R4: one contradictory (valid-format) digest", lambda: digest_case(h4_one_contradictory)),
    ("H5", "R4 positive: actual staged handoff digests", lambda: digest_case(h5_actual)),
]


def main(results):
    rows = []
    for sid, title, fn in SCENARIOS:
        try:
            outcome = fn()
        except Exception as exc:
            outcome = "ERROR %r" % (exc,)
            traceback.print_exc()
        row = {"id": sid, "scenario": title, "outcome": outcome, "reasons": LAST["reasons"][:12]}
        if sid in TARGETED:
            row["targeted_check"] = TARGETED[sid]
            row["targeted_check_fired"] = any(TARGETED[sid] in r for r in LAST["reasons"])
            outcome += "  {targeted %r: %s}" % (TARGETED[sid], "FIRED" if row["targeted_check_fired"] else "not fired")
        LAST["reasons"] = []
        rows.append(row)
        print("%-6s %-52s %s" % (sid, title, outcome))
    with io.open(results, "w", encoding="utf-8") as f:
        f.write(json.dumps({"root": os.path.basename(os.path.dirname(ROOT)) + "/" + os.path.basename(ROOT),
                            "python": sys.version.split()[0], "native_execution": False, "scenarios": rows},
                           indent=1).encode("ascii").decode("ascii"))


if __name__ == "__main__":
    main(RESULTS)
