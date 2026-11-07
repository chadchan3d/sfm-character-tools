# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage D: offline lifecycle qualification of the left-arm live layer in the CPM application
source. Design authority: F-01 M1 Implementation Addendum R2.1 sections 5.4-5.5, 6, 7 and 8; Owner authorization of
stage D (2026-11-02), including W2's source-independent persistence requirement.

Technique: the stage A, B, C and D blocks and CPM's helpers they call are extracted verbatim from the application
source and run against W2's accepted fake native API (real_sfm_qualification/checkpoint_f01_w2_persisted_pose/
accepted/tests/fake_sfm_w2.py, hash-verified, not modified), extended here only with the layer and log primitives
stage D uses that W2 did not (InsertKey with its Undo/Abort journal, the default curve type, curve-type,
compression, default-value and bookmark reads, FromChildMediaTime, the SWIG DmeTime_t(int ticks) overload).
Process B worlds poison the source shot: any read of a source pose value raises and is recorded.

Explicit boundaries (natively qualified M-06 functions, exercised by the W1 and stage C suites): prod_resolve_instance
and prod_instance_channels_clip are replaced by resolvers over the fake world's pinned shot; prod_validate_context_token
by a switch. Nothing here demonstrates native SFM behaviour; the native checkpoint does.

Usage: --phase=run (Python 2.7.5 and Python 3.10).
"""
from __future__ import print_function

import copy
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402

try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

FAKE_PATH = os.path.join(core.W2_DIR, "tests", "fake_sfm_w2.py")
FAKE_FILE = "tests/fake_sfm_w2.py"
BLOCKS = ((core.BLOCK_START, core.BLOCK_END), (u"# F-01 Pose Library M1, stage B: offline pose library",
                                               u"# === end of F-01 stage B block ==="),
          (u"# F-01 Pose Library M1, stage C: CPM integration seams", u"# === end of F-01 stage C block ==="),
          (u"# F-01 Pose Library M1, stage D: the left-arm live layer", u"# === end of F-01 stage D block ==="))
HELPERS = ("u", "dm", "prod_outcome", "prod_apply_deferred_unverified", "ProdRecoveryUnverifiedError",
           "PROD_INSTANCE_TOKEN_KIND", "prod_instance_token", "_PROD_PRIVATE_WINDLL", "prod_private_windll",
           "p02_ensure_dir", "p02_json_text", "p02_unique_temp", "p02_safe_write_json")
MODEL = u"models/fursonas/starfox/krystal/bodies/krystal2020.mdl"
IDENTITY = {"model": MODEL, "checksum": 1234, "animset_name": u"Krystal"}
RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def outcome(fn):
    try:
        return ("ok", fn())
    except Exception as exc:
        return (type(exc).__name__, getattr(exc, "code", None), _TEXT(exc))


def refused(name, result, code=None):
    check(name, result[0] != "ok" and (code is None or result[1] == code), result)


# ---------------------------------------------------------------------------
# The fake native API (W2, accepted) and its stage D extensions
# ---------------------------------------------------------------------------

def load_fake():
    sums = dict(line.split("  ", 1)[::-1] for line in core.read(os.path.join(core.W2_DIR, "SHA256SUMS.txt"))
                .decode("ascii").splitlines() if line.strip())
    check("fake.w2_fake_matches_checkpoint_sums", sums.get(FAKE_FILE) == core.sha(core.read(FAKE_PATH)))
    if sys.version_info[0] == 2:
        import imp
        F = imp.load_source("fake_sfm_w2_stage_d", FAKE_PATH)
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fake_sfm_w2_stage_d", FAKE_PATH)
        F = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(F)
    extend_fake(F)
    return F


class FakeNativeCrash(BaseException):
    """A call that crashes SFM natively: never catchable as an ordinary failure."""


def extend_fake(F):
    def insert_key(self, t, value, curve_type, ignore_tolerance):
        assert ignore_tolerance is True and isinstance(curve_type, int) and not isinstance(curve_type, bool)
        self.world.check_poison(self, "InsertKey")
        new = [F.f32(c) for c in F.as_list(value)]
        index = 0
        while index < len(self.keys) and self.keys[index][0] < t.ticks:
            index += 1
        if index < len(self.keys) and self.keys[index][0] == t.ticks:
            raise RuntimeError("a key already exists at this time (fake)")
        if self.world.raise_on_write:
            raise RuntimeError("native write failed (test)")
        self.keys.insert(index, [t.ticks, new])
        dmodel = self.world.dm
        if dmodel.current is not None:
            dmodel.current["items"].append(("insert", self, index, [t.ticks, list(new)]))
        return index
    F.Layer.InsertKey = insert_key

    def insert_key_at_time(self, *args):
        # The native one-argument overload InsertKeyAtTime(DmeTime_t nTime) -> int: a key at exactly nTime with the
        # layer's current value there (SFM's compiled default curve type); CPM then sets the value with SetKeyValue.
        assert len(args) == 1, "CPM must call the one-argument overload (no curve type) (fake)"
        t = args[0]
        self.world.check_poison(self, "InsertKeyAtTime")
        index = 0
        while index < len(self.keys) and self.keys[index][0] < t.ticks:
            index += 1
        if index < len(self.keys) and self.keys[index][0] == t.ticks:
            return index                      # an existing key at nTime: nothing inserted (CPM's checks must refuse)
        if self.world.raise_on_write:
            raise RuntimeError("native write failed (test)")
        held = list(self.keys[max(0, index - 1)][1])
        self.keys.insert(index, [t.ticks, held])
        dmodel = self.world.dm
        if dmodel.current is not None:
            dmodel.current["items"].append(("insert", self, index, [t.ticks, list(held)]))
        return index
    F.Layer.InsertKeyAtTime = insert_key_at_time

    def native_curve_type_crash(self):
        # NQ-1 run 2, process B (minidump): natively CDmeLogLayer.GetDefaultCurveType() reads the owner log's curve
        # info without a null check; every log CPM may write has none, so SFM crashed. A BaseException, so CPM's
        # `except Exception` cannot turn it into a recoverable failure, as the native crash could not be.
        raise FakeNativeCrash("GetDefaultCurveType on a log without curve info (native crash in SFM)")
    F.Layer.GetDefaultCurveType = native_curve_type_crash
    F.Log.GetDefaultCurveType = native_curve_type_crash
    F.Layer.IsUsingCurveTypes = lambda self: False
    F.Layer.IsCompressed = lambda self: False
    F.Log.HasDefaultValue = lambda self: self.get("defaultvalue") is not None
    F.Log.GetDefaultValue = lambda self: F.mk(F.as_list(self.get("defaultvalue")), "Quaternion" in self.kind)
    F.Log.GetNumBookmarkComponents = lambda self: 0
    F.Clip.FromChildMediaTime = lambda self, t, clamp: F.Time(t.ticks - self.offset + self.start)

    def revert(items):
        for item in reversed(items):
            if item[0] == "insert":
                del item[1].keys[item[2]]
            elif item[0] is not None:
                item[0].keys[item[1]][1] = item[2]

    def reapply(items):
        for item in items:
            if item[0] == "insert":
                item[1].keys.insert(item[2], list(item[3]))
            elif item[0] is not None:
                item[0].keys[item[1]][1] = item[3]

    def abort(self):
        self.calls.append(("AbortUndoableOperation",))
        if self.world.abort_raises:
            raise RuntimeError("abort failed (test)")
        if not self.world.abort_broken:
            revert(self.current["items"])
        self.current = None

    def undo(self):
        self.calls.append(("Undo",))
        entry = self.stack.pop()
        revert(entry["items"])
        self.redo.append(entry)

    def redo(self):
        self.calls.append(("Redo",))
        entry = self.redo.pop()
        reapply(entry["items"])
        self.stack.append(entry)
    F.DataModel.AbortUndoableOperation = abort
    F.DataModel.Undo = undo
    F.DataModel.Redo = redo

    # Astra S1 final: native Undo exception switches (world.start_raises / world.finish_raises: None, "before" or
    # "after"). Unset, the accepted W2 behaviour is unchanged.
    w2_start, w2_finish = F.DataModel.StartUndo, F.DataModel.FinishUndo

    def start_undo(self, undo, redo):
        when = getattr(self.world, "start_raises", None)
        if when == "before":                              # fails without opening anything
            self.calls.append(("StartUndo", F.key(undo), F.key(redo)))
            raise RuntimeError("StartUndo failed before opening (test)")
        w2_start(self, undo, redo)
        if when == "after":                               # opened, then reported a failure
            raise RuntimeError("StartUndo failed after opening (test)")

    def finish_undo(self):
        when = getattr(self.world, "finish_raises", None)
        if when == "before":                              # fails before closing: the transaction stays open
            self.calls.append(("FinishUndo",))
            raise RuntimeError("FinishUndo failed before commit (test)")
        w2_finish(self)
        if when == "after":                               # committed, then reported a failure
            raise RuntimeError("FinishUndo failed after commit (test)")
    F.DataModel.StartUndo = start_undo
    F.DataModel.FinishUndo = finish_undo

    def dme_time(x):
        # SWIG overloads: int -> tenths of a millisecond, float -> seconds.
        if isinstance(x, bool):
            raise TypeError("bool time")
        if isinstance(x, (int,) + ((long,) if sys.version_info[0] == 2 else ())):  # noqa: F821
            return F.Time(x)
        return F.Time(int(round(float(x) * F.TICKS)))
    F.stage_d_time = dme_time


class Pin(object):
    """The M-06 boundary: the pinned instance (a shot of the fake world) and its session."""
    world = None
    shot = None
    session = u"session-1"
    valid = [True]


def build_namespace(app, F):
    ns = {"__builtins__": __builtins__, "json": json, "hashlib": hashlib, "math": math, "os": os, "re": __import__("re"),
          "sys": sys, "binascii": __import__("binascii"), "datetime": __import__("datetime"),
          "ctypes": __import__("ctypes"), "traceback": traceback}
    if sys.version_info[0] >= 3:
        ns["unicode"] = str
        ns["long"] = int
    ns["LOG"] = []
    ns["log_line"] = lambda text: ns["LOG"].append(_TEXT(text))
    for name in HELPERS:
        route._run_source(app.top_text(name), "app:%s" % name, ns)
    for start, end in BLOCKS:
        block, _ = core.extract_block(route.APP_PATH, start, end)
        route._run_source(block, "block", ns)

    def resolve(token, identity=None):
        if not Pin.valid[0] or token.get("session") != Pin.session or Pin.world is None:
            raise RuntimeError("The selected character instance is no longer present (boundary).")
        S = Pin.world.shots.get(token.get("shot"))
        if S is None or S.animset is None:
            raise RuntimeError("The selected character instance is no longer present (boundary).")
        return {"shot": S.clip, "animset": S.animset, "gm": S.gm, "instance": token}

    def channels_clip(animset, shot):
        hits = [S for S in Pin.world.shots.values() if S.animset is animset and S.clip is shot]
        if len(hits) != 1:
            raise RuntimeError("channels clip not identified (boundary)")
        return hits[0].channels_clip
    ns["prod_resolve_instance"] = resolve
    ns["prod_instance_channels_clip"] = channels_clip
    ns["prod_validate_context_token"] = lambda token: Pin.valid[0] or (_ for _ in ()).throw(RuntimeError("stale"))
    ns["prod_context_token_matches"] = lambda token: Pin.valid[0] and token["instance"]["session"] == Pin.session
    return ns


def use_world(ns, F, world, shot):
    mods = world.modules()
    mods["vs"].DmeTime_t = F.stage_d_time
    # SFM's timeline mode (2 Motion Editor, the qualified Apply context) and the same-time head request, which
    # natively made SFM evaluate after a scripted write (FA-1, FA-2, FA-3b); recorded so tests can check it.
    mods["sfmApp"].GetTimelineMode = lambda: getattr(world, "timeline_mode", 2)
    world.refresh_calls = []

    def set_head(seconds):
        world.refresh_calls.append({"seconds": seconds, "in_undo": world.dm.current is not None})
        world.head = int(round(seconds * F.TICKS))
        if getattr(world, "evaluate_on_refresh", True) and world.current_shot() is not None:
            world.evaluate(world.current_shot())
    mods["sfmApp"].SetHeadTimeInSeconds = set_head
    ns["vs"], ns["sfmApp"] = mods["vs"], mods["sfmApp"]
    ns["QtCore"] = mods["PySide.QtCore"]
    Pin.world, Pin.shot = world, shot


def context(ns, shot):
    token = {"kind": ns["PROD_INSTANCE_TOKEN_KIND"], "session": Pin.session, "shot": shot}
    return {"instance": token, "library_identity": dict(IDENTITY)}


def registry(ns):
    raw = core.read(core.REGISTRY_PATH)
    return ns["prod_pose_registry_parse"](raw, ns["PROD_POSE_REGISTRY_SHA256"])


def experimental_registry(ns):
    """The shipped registry with its left-arm mapping returned to experimental (a test pin, not the product pin)."""
    draft = json.loads(core.read(core.REGISTRY_PATH).decode("utf-8"))
    draft["mappings"][0].update(status=u"experimental", evidence=None)
    raw = ns["prod_pose_canonical_bytes"](draft)
    return ns["prod_pose_registry_parse"](raw, core.sha(raw))


def library(root):
    char_dir = os.path.join(root, u"Characters", u"krystal2020")
    return {u"character_key": u"krystal2020", u"char_dir": char_dir, u"library_root": root, u"model_ref": MODEL}


def authorize(ns, reg, shot, label, item=None, mode=u"qualification"):
    return ns["prod_pose_authorize"](context(ns, shot), IDENTITY, reg, mode, label, item)


def live(ns, reg, shot):
    auth = authorize(ns, reg, shot, u"Save Pose")
    profile = ns["prod_pose_region_profile"](reg, auth, u"left_arm")
    row = ns["prod_resolve_instance"](context(ns, shot)["instance"])
    return ns["prod_pose_live_arm"](row, profile), profile


def authored(ns, reg, shot):
    L, _ = live(ns, reg, shot)
    return ns["prod_pose_capture_authored"](L)


def keys(world, shot, name):
    return [list(k) for k in world.channel(shot, name).log.layers[0].keys]


def save(ns, reg, lib, name, shot):
    auth = authorize(ns, reg, shot, u"Save Pose")
    pose = ns["prod_pose_capture"](IDENTITY, auth, [u"left_arm"], reg)
    return ns["prod_pose_save_new"](lib, name, pose, u"20261102-120000-000000", reg)


def apply_and_verify(ns, reg, world, item, shot=u"shot10", run=True, mode=u"qualification"):
    auth = authorize(ns, reg, shot, u"Apply Pose", item, mode=mode)
    phases = []
    result = ns["prod_pose_apply"](IDENTITY, auth, item, reg, phase_callback=lambda p, d=None: phases.append(p))
    verdict = None
    if result.get("phase") == u"verification-pending":
        pending = dict(result["pending"])
        pending[u"authorization"] = auth
        if run:
            world.run_events()
            world.evaluate(world.shots[shot])
        verdict = ns["prod_pose_deferred_verify"](pending)
    return result, verdict, phases


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def process_a(ns, F, reg, root):
    """Process A: capture the left arm of shot15's Krystal (frame 5) into the CPM library."""
    world = F.World(u"capture.dmx", handle_base=100000)
    use_world(ns, F, world, u"shot15")
    lib = library(root)
    before = authored(ns, reg, u"shot15")
    calls = list(world.dm.calls)
    saved = save(ns, reg, lib, u"Arms Out", u"shot15")
    check("D1.capture_is_read_only_no_undo_no_write", world.dm.calls == calls and authored(ns, reg, u"shot15") == before)
    record = json.loads(core.read(saved[u"path"]).decode("utf-8"))
    check("D1.saved_record_is_a_valid_left_arm_cpm_pose",
          sorted(record[u"pose"][u"regions"]) == [u"left_arm"] and record[u"kind"] == u"pose"
          and record[u"pose"][u"source"][u"t_doc_ticks"] == 2083 and record[u"pose"][u"source"][u"rig_class"] ==
          u"krystal-v1", record[u"pose"][u"source"])
    region = record[u"pose"][u"regions"][u"left_arm"]
    check("D1.descriptor_is_portable_no_handles", b"\"handle\"" not in core.read(saved[u"path"])
          and region[u"descriptor"][u"follow_the_arm_bones"] == [u"bip_finger_l"], region[u"descriptor"].get(
              u"follow_the_arm_bones"))
    # A second pose from a changed source arm (the update case later).
    layer = world.channel(u"shot15", u"Hand_l_p").log.layers[0]
    for k in layer.keys:
        if k[0] in (30000, 70415):
            k[1] = [k[1][0] + 1.5, k[1][1] - 1.0, k[1][2] + 0.5]
    world.evaluate(world.shots[u"shot15"])
    save(ns, reg, lib, u"Arms Moved", u"shot15")
    # Capture refusals: right arm (not in this build), a playhead change while the dialog was open.
    auth = authorize(ns, reg, u"shot15", u"Save Pose")
    refused("D1.right_arm_capture_refused", outcome(lambda: ns["prod_pose_capture"](IDENTITY, auth, [u"right_arm"],
                                                                                     reg)), u"not-qualified")
    pinned = ns["prod_pose_current_time"](IDENTITY, auth, reg, [u"left_arm"])
    world.head = 2500
    world.evaluate(world.shots[u"shot15"])
    refused("D1.time_changed_while_save_dialog_open_refused",
            outcome(lambda: ns["prod_pose_capture"](IDENTITY, auth, [u"left_arm"], reg, pinned_time=pinned)), u"stale")
    return lib


def process_b(ns, F, reg, lib):
    """Process B: a new SFM process (session), the source shot poisoned; apply at shot10 frame 10."""
    Pin.session = u"session-2"
    world = F.World(u"apply.dmx", handle_base=500000, poison_source=True)
    use_world(ns, F, world, u"shot10")
    world.set_frame(10)
    items = dict((i[u"name"], i) for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"])
    check("D2.poses_listed_from_disk_in_the_new_process", sorted(items) == [u"Arms Moved", u"Arms Out"])
    base = authored(ns, reg, u"shot10")
    base_keys = dict((n, keys(world, u"shot10", n)) for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p", u"Elbow_l_o"))
    # Production build: the qualified Krystal left-arm mapping is authorized; an experimental mapping never is.
    prod_auth = authorize(ns, reg, u"shot10", u"Apply Pose", items[u"Arms Out"], mode=u"production")
    check("D3.production_authorizes_only_the_qualified_left_arm_mapping",
          [(m[u"region"], m[u"from"], m[u"to"], m[u"status"]) for m in prod_auth[u"mappings"]] ==
          [(u"left_arm", u"krystal-v1", u"krystal-v1", u"qualified")], prod_auth[u"mappings"])
    draft = experimental_registry(ns)
    draft_auth = authorize(ns, draft, u"shot10", u"Apply Pose", items[u"Arms Out"], mode=u"production")
    refused("D3.production_mode_refuses_experimental_mapping",
            outcome(lambda: ns["prod_pose_apply"](IDENTITY, draft_auth, items[u"Arms Out"], draft)), u"not-qualified")
    check("D3.production_refusal_opened_no_undo", not world.dm.calls)
    # Insert, in the production mode: no key exists at the channel time (50208 ticks).
    result, verdict, phases = apply_and_verify(ns, reg, world, items[u"Arms Out"], mode=u"production")
    check("D4.insert_apply_commits_and_hands_over_to_p7", result.get("phase") == u"verification-pending"
          and "native-commit" in phases, (result.get("phase"), phases))
    check("D4.insert_verified_by_p7", verdict == {u"phase": u"committed-verified"}, verdict)
    check("D4.no_source_value_was_read_in_process_b", world.poison_hits == [], world.poison_hits[:4])
    after = dict((n, keys(world, u"shot10", n)) for n in base_keys)
    t = 50208
    inserted = all(len(after[n]) == len(base_keys[n]) + 1 and [k for k in after[n] if k[0] == t]
                   and [k for k in after[n] if k[0] != t] == base_keys[n] for n in (u"Hand_l_p", u"Hand_l_o",
                                                                                    u"Elbow_l_p"))
    check("D4.one_key_inserted_per_written_channel_neighbours_unchanged", inserted, after)
    check("D4.observed_elbow_orientation_untouched", after[u"Elbow_l_o"] == base_keys[u"Elbow_l_o"])
    check("D4.one_owned_undo_entry", world.dm.CanUndo() and world.dm.GetUndoDesc() == u"Apply Pose Arms Out"
          and len(world.dm.stack) == 1)
    expected = authored(ns, reg, u"shot10")
    world.dm.Undo()
    world.evaluate(world.shots[u"shot10"])
    check("D5.undo_restores_the_baseline_exactly", authored(ns, reg, u"shot10") == base)
    world.dm.Redo()
    world.evaluate(world.shots[u"shot10"])
    check("D5.redo_restores_the_applied_state_exactly", authored(ns, reg, u"shot10") == expected)
    # True no-op: the same pose again.
    calls = len(world.dm.calls)
    result, _, _ = apply_and_verify(ns, reg, world, items[u"Arms Out"])
    check("D6.true_no_op_opens_no_transaction", result == {u"phase": u"no-op"} and len(world.dm.calls) == calls, result)
    # Update: a different pose at the same time (keys now exist at t).
    result, verdict, _ = apply_and_verify(ns, reg, world, items[u"Arms Moved"])
    upd = dict((n, keys(world, u"shot10", n)) for n in base_keys)
    check("D7.update_verified", verdict == {u"phase": u"committed-verified"}, verdict)
    check("D7.update_changes_values_not_times_or_counts",
          [k[0] for k in upd[u"Hand_l_p"]] == [k[0] for k in after[u"Hand_l_p"]]
          and upd[u"Hand_l_p"] != after[u"Hand_l_p"], upd[u"Hand_l_p"])
    world.dm.Undo()
    world.evaluate(world.shots[u"shot10"])
    check("D7.undo_of_update_returns_to_the_previous_pose", authored(ns, reg, u"shot10") == expected)
    world.dm.Undo()
    world.evaluate(world.shots[u"shot10"])
    check("D7.second_undo_returns_to_the_baseline", authored(ns, reg, u"shot10") == base)
    return world, items, base


def section_abort(ns, F, reg, world, items, base):
    stack = list(world.dm.stack)
    redo = list(world.dm.redo)
    ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
    result, _, _ = apply_and_verify(ns, reg, world, items[u"Arms Out"], run=False)
    check("D8.injected_failure_after_writes_aborts_and_verifies_unchanged",
          result.get("phase") == u"not-applied" and authored(ns, reg, u"shot10") == base, result)
    check("D8.abort_left_the_undo_history_unchanged", world.dm.stack == stack and world.dm.redo == redo
          and world.dm.calls[-1] == ("AbortUndoableOperation",))
    ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
    auth = authorize(ns, reg, u"shot10", u"Apply Pose", items[u"Arms Out"], mode=u"production")
    check("D8.fault_hook_is_inert_outside_qualification", ns["PROD_POSE_QUAL_FAULT"][0] == u"after-writes"
          and outcome(lambda: ns["prod_pose_qualification_fault"](u"production", u"after-writes"))[0] == "ok")
    ns["PROD_POSE_QUAL_FAULT"][0] = None
    # An Abort that does not restore: recovery-unverified, never "nothing was changed".
    world.abort_broken = True
    ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
    r = outcome(lambda: apply_and_verify(ns, reg, world, items[u"Arms Out"], run=False))
    check("D9.unrestored_abort_is_recovery_unverified", r[0] == "ProdRecoveryUnverifiedError", r)
    world.abort_broken = False
    ns["PROD_POSE_QUAL_FAULT"][0] = None


def section_channel_clock(ns, F, reg, root):
    """Motion Editor Apply contract (FA-3b): Apply only in timeline mode 2 with every target channel clock at the
    mapped tick, the mode and clocks pinned through P2 and P7; after a confirmed commit one same-time head request
    outside the transaction, then the guarded deferred verification. Save New and Update Pose (Argon B.2): capture
    refuses unless every region channel's clock is the mapped tick, independent of the timeline mode."""
    os.makedirs(os.path.join(root, u"clock"))
    lib = library(os.path.join(root, u"clock"))
    Pin.session = u"session-clock-a"
    src = F.World(u"clock.dmx", handle_base=900000)
    use_world(ns, F, src, u"shot15")
    real_ticks = src.channel_ticks
    found = lambda: ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"]  # noqa: E731

    def clock(offset):
        src.channel_ticks = (lambda S: real_ticks(S) + offset) if offset else real_ticks
        src.evaluate(src.shots[u"shot15"])
    # (2) Mismatched clocks (the Clip Editor's clock, FA-1): Save refuses, before the name dialog and in capture,
    # and creates no record.
    clock(91)
    pinned = outcome(lambda: ns["prod_pose_current_time"](IDENTITY, authorize(ns, reg, u"shot15", u"Save Pose"), reg,
                                                           [u"left_arm"]))
    check("D13.save_refused_before_the_name_dialog_when_the_channel_clock_differs",
          pinned[0] == "ProdPoseError" and pinned[1] == u"capture-clock"
          and pinned[2] == ns["PROD_POSE_SAVE_CLOCK_COPY"], pinned)
    saved = outcome(lambda: save(ns, reg, lib, u"Clock Pose", u"shot15"))
    check("D13.save_refused_in_capture_when_the_channel_clock_differs_no_record",
          saved[0] == "ProdPoseError" and saved[1] == u"capture-clock" and not found()
          and not os.path.exists(os.path.join(lib[u"char_dir"], u"Poses")), saved)
    # (1) Matching clocks: capture succeeds.
    clock(0)
    saved = outcome(lambda: save(ns, reg, lib, u"Clock Pose", u"shot15"))
    check("D13.save_succeeds_when_every_channel_clock_is_the_mapped_tick",
          saved[0] == "ok" and [i[u"name"] for i in found()] == [u"Clock Pose"], saved)
    items = dict((i[u"name"], i) for i in found())
    # (3) Mismatched clocks: Update refuses before replacing the record (its capture refuses; the store is never
    # reached). The window's Update Pose copy for this refusal is checked in the integration suite.
    raw = core.read(items[u"Clock Pose"][u"path"])
    clock(91)
    auth = authorize(ns, reg, u"shot15", u"Save Pose")
    for label, fn in (("pinned_time", lambda: ns["prod_pose_current_time"](IDENTITY, auth, reg, [u"left_arm"])),
                      ("capture", lambda: ns["prod_pose_capture"](IDENTITY, auth, [u"left_arm"], reg))):
        r = outcome(fn)
        check("D13.update_%s_refused_when_the_channel_clock_differs" % label,
              r[0] == "ProdPoseError" and r[1] == u"capture-clock", r)
    check("D13.update_refusal_leaves_the_record_unchanged", core.read(items[u"Clock Pose"][u"path"]) == raw
          and [i[u"revision"] for i in found()] == [items[u"Clock Pose"][u"revision"]])
    # (4) Flat arm controllers with a moving collar: the arm channels hold one value, so their inputs match at any
    # time, but the collar (a parent of the captured arm) moves between the two clocks. Still refused.
    shot = src.shots[u"shot15"]
    for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p", u"Elbow_l_o"):   # hold each arm control at its current value
        layer = src.channel(u"shot15", n).log.layers[0]
        held = [k for k in layer.keys if k[0] <= real_ticks(shot)][-1][1]
        layer.keys[:] = [[k[0], list(held)] for k in layer.keys]
    flat = all(len(set(json.dumps(k[1]) for k in src.channel(u"shot15", n).log.layers[0].keys)) == 1
               for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p", u"Elbow_l_o"))
    collar = src.channel(u"shot15", u"CollarL_p").log.layers[0].keys
    collar.append([real_ticks(shot) + 91, [collar[0][1][0] + 3.0, collar[0][1][1], collar[0][1][2]]])
    collar.sort(key=lambda k: k[0])
    clock(0)
    at_tick = list(shot.handles[u"CollarL"].world_xf[0])
    clock(91)
    at_clock = list(shot.handles[u"CollarL"].world_xf[0])
    check("D13.fixture_flat_arm_controllers_and_a_moving_collar", flat and at_tick != at_clock, (at_tick, at_clock))
    saved = outcome(lambda: save(ns, reg, lib, u"Collar Pose", u"shot15"))
    check("D13.flat_arm_with_moving_collar_still_refused_when_the_clock_differs",
          saved[0] == "ProdPoseError" and saved[1] == u"capture-clock"
          and [i[u"name"] for i in found()] == [u"Clock Pose"], saved)
    # Control: with only the clock check disabled, the same capture passes every other check (the arm inputs match),
    # so the clock check is what refuses it.
    os.makedirs(os.path.join(root, u"clock-control"))
    real_check = ns["prod_pose_capture_clock_check"]
    ns["prod_pose_capture_clock_check"] = lambda L, t_chan: {}
    try:
        control = outcome(lambda: save(ns, reg, library(os.path.join(root, u"clock-control")), u"Collar Pose",
                                       u"shot15"))
    finally:
        ns["prod_pose_capture_clock_check"] = real_check
    check("D13.control_without_the_clock_check_the_flat_arm_capture_would_be_saved", control[0] == "ok", control)
    # (5) The Graph Editor with aligned clocks: capture remains permitted (no Motion Editor requirement on Save).
    clock(0)
    src.timeline_mode = 4
    saved = outcome(lambda: save(ns, reg, lib, u"Graph Pose", u"shot15"))
    check("D13.graph_editor_with_aligned_clocks_save_permitted",
          saved[0] == "ok" and sorted(i[u"name"] for i in found()) == [u"Clock Pose", u"Graph Pose"], saved)
    src.timeline_mode = 2

    def world(name, mode=2, offset=0):
        Pin.session = u"session-" + name
        w = F.World(name + u".dmx", handle_base=950000, poison_source=True)
        if offset:
            rt = w.channel_ticks
            w.channel_ticks = lambda S: rt(S) + offset
        use_world(ns, F, w, u"shot10")
        w.timeline_mode = mode
        w.set_frame(10)
        w.evaluate(w.shots[u"shot10"])
        return w

    def refused_before_write(label, w, code, mode=u"qualification"):
        base = keys(w, u"shot10", u"Hand_l_p")
        r = outcome(lambda: apply_and_verify(ns, reg, w, items[u"Clock Pose"], run=False, mode=mode))
        check(label, r[0] == "ProdPoseError" and r[1] == code and keys(w, u"shot10", u"Hand_l_p") == base
              and not w.dm.stack and not w.refresh_calls, r)
    refused_before_write("D14.clip_editor_refused_before_writing", world(u"clip", mode=3), u"editor-mode")
    refused_before_write("D14.graph_editor_refused_before_writing", world(u"graph", mode=4), u"editor-mode")
    # The same Motion Editor restriction in the production mode with the qualified mapping.
    refused_before_write("D14.production_clip_editor_refused_before_writing", world(u"prod-clip", mode=3),
                         u"editor-mode", mode=u"production")
    refused_before_write("D14.production_graph_editor_refused_before_writing", world(u"prod-graph", mode=4),
                         u"editor-mode", mode=u"production")
    refused_before_write("D14.clock_away_from_the_mapped_tick_refused_before_writing", world(u"offset", offset=91),
                         u"time-mapping")
    # The mode changes between P1 and P2: refused before StartUndo.
    w = world(u"mode-drift")
    real_log = ns["prod_pose_log"]

    def hook(phase, detail=None):
        if phase == u"P1":
            w.timeline_mode = 3
        return real_log(phase, detail)
    ns["prod_pose_log"] = hook
    try:
        refused_before_write("D15.mode_change_between_P1_and_P2_refused_before_writing", w, u"editor-mode")
    finally:
        ns["prod_pose_log"] = real_log
    # Automatic display: one same-time request after the commit, outside the transaction; P7 then verifies.
    w = world(u"auto")
    base = keys(w, u"shot10", u"Hand_l_p")
    result, verdict, _ = apply_and_verify(ns, reg, w, items[u"Clock Pose"], run=False)
    check("D16.apply_in_the_motion_editor_verifies_without_navigation",
          result.get("phase") == u"verification-pending" and verdict == {u"phase": u"committed-verified"},
          (result.get("phase"), verdict))
    check("D16.exactly_one_same_time_request_outside_the_transaction",
          w.refresh_calls == [{"seconds": w.head / float(F.TICKS), "in_undo": False}], w.refresh_calls)
    check("D16.inserted_at_the_mapped_tick", [k[0] for k in keys(w, u"shot10", u"Hand_l_p") if k not in base] == [50208])
    w.dm.Undo()
    w.evaluate(w.shots[u"shot10"])
    check("D16.undo_restores_the_baseline", keys(w, u"shot10", u"Hand_l_p") == base)
    # The request does not make SFM evaluate: committed-unverified, never undone or compensated.
    w = world(u"no-eval")
    w.evaluate_on_refresh = False
    result, verdict, _ = apply_and_verify(ns, reg, w, items[u"Clock Pose"], run=False)
    check("D17.no_evaluation_after_the_request_is_committed_unverified",
          verdict is not None and verdict.get(u"phase") == u"committed-unverified" and len(w.dm.stack) == 1
          and w.dm.GetUndoDesc() == u"Apply Pose Clock Pose" and len(w.refresh_calls) == 1, (verdict, w.refresh_calls))
    # The mode changes after the commit, before P7: unverified (context changed), keys kept.
    w = world(u"late-mode")
    result = ns["prod_pose_apply"](IDENTITY, authorize(ns, reg, u"shot10", u"Apply Pose", items[u"Clock Pose"]),
                                   items[u"Clock Pose"], reg)
    pending = dict(result["pending"])
    pending[u"authorization"] = authorize(ns, reg, u"shot10", u"Apply Pose", items[u"Clock Pose"])
    w.timeline_mode = 4
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("D18.mode_change_after_commit_is_committed_unverified",
          verdict.get(u"phase") == u"committed-unverified" and len(w.dm.stack) == 1, verdict)


def section_refusals(ns, F, reg, lib):
    def fresh(**kw):
        Pin.session = u"session-3"
        w = F.World(u"apply.dmx", handle_base=700000, poison_source=True, **kw)
        use_world(ns, F, w, u"shot10")
        w.set_frame(10)
        return w
    items = dict((i[u"name"], i) for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"])
    item = items[u"Arms Out"]

    def attempt(world):
        before = [list(k) for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p") for k in keys(world, u"shot10", n)]
        calls = list(world.dm.calls)
        r = outcome(lambda: apply_and_verify(ns, reg, world, item, run=False))
        after = [list(k) for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p") for k in keys(world, u"shot10", n)]
        unchanged = after == before and not [c for c in world.dm.calls[len(calls):] if c[0] == "StartUndo"]
        return r, unchanged
    w = fresh()
    w.add_channel(u"shot10", u"intruder", w.shots[u"shot10"].handles[u"Hand_l"].get("transform"), u"position",
                  mode=3)
    r, same = attempt(w)
    check("D10.second_writer_of_the_hand_refused_before_any_write", r[0] != "ok" and r[1] == u"shared-authority"
          and same, r)
    w = fresh()
    ik = [op for op in w.shots[u"shot10"].ops if op.kind == "DmeRigIKConstraintOperator"][0]
    ik.get("targets")[0].set("targetWeight", 0.5)
    r, same = attempt(w)
    check("D10.different_arm_rig_refused_rig_differs", r[0] != "ok" and r[1] == u"rig-differs" and same, r)
    w = fresh()
    w.head = 3751                                   # shot10's first tick: SFM reports no strictly-inside shot
    r, same = attempt(w)
    check("D10.boundary_playhead_refused_time_mapping", r[0] != "ok" and r[1] == u"time-mapping" and same, r)
    w = fresh()
    ch = w.channel(u"shot10", u"Hand_l_o")
    w.unreadable.add((ch.log.GetHandle(), "curveinfo"))
    r, same = attempt(w)
    check("D10.unreadable_metadata_refused_evidence_unreadable", r[0] != "ok" and r[1] == u"evidence-unreadable"
          and same, r)
    w = fresh()
    w.channel(u"shot10", u"Hand_l_o").log.layers[0].keys[:] = []
    r, same = attempt(w)
    check("D10.zero_key_channel_refused", r[0] != "ok" and same, r)
    w = fresh()
    # The scene changes between P1 and P2 (an unrelated key of the instance moves mid-operation).
    real_log = ns["prod_pose_log"]

    def log_and_change(phase, detail):
        real_log(phase, detail)
        if phase == u"P1":
            w.channel(u"shot10", u"Elbow_l_o").log.layers[0].keys[0][1] = [0.0, 0.0, 0.0, 1.0]
    ns["prod_pose_log"] = log_and_change
    try:
        r = outcome(lambda: apply_and_verify(ns, reg, w, item, run=False))
    finally:
        ns["prod_pose_log"] = real_log
    check("D10.change_between_preflight_and_write_refused_stale", r[0] != "ok" and r[1] == u"stale"
          and not [c for c in w.dm.calls if c[0] == "StartUndo"], r)
    # P7 context gate: the playhead moves before the deferred turn.
    w = fresh()
    auth = authorize(ns, reg, u"shot10", u"Apply Pose", item)
    result = ns["prod_pose_apply"](IDENTITY, auth, item, reg)
    pending = dict(result["pending"])
    pending[u"authorization"] = auth
    w.set_frame(11)
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("D11.playhead_moved_before_p7_is_committed_unverified", verdict.get("phase") == u"committed-unverified"
          and verdict.get("reason") == u"context-changed", verdict)
    w.set_frame(10)
    Pin.valid[0] = False
    verdict = ns["prod_pose_deferred_verify"](pending)
    Pin.valid[0] = True
    check("D11.instance_changed_before_p7_is_committed_unverified", verdict.get("reason") == u"context-changed",
          verdict)
    w.run_events()
    w.perturb_layer = None
    w.channel(u"shot10", u"Hand_l_p").log.layers[0].keys[1][1] = [0.0, 0.0, 0.0]
    w.evaluate(w.shots[u"shot10"])
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("D11.authored_change_after_commit_is_unverified_never_verified",
          verdict.get("phase") == u"committed-unverified", verdict)


# ---------------------------------------------------------------------------
# Astra S1 final: Undo exception uncertainty on the legacy version 1 Apply (U.1 ... U.7)
# ---------------------------------------------------------------------------

class LegacyWindow(object):
    """The ProdWindow seams pose_guard and apply_pose call; those two methods (and pose_registry_mode) are real."""

    def __init__(self, ctx):
        self.identity = dict(IDENTITY)
        self.operation = {"context": ctx, "operation_id": 1, "generation": 1}
        self.statuses, self.pending = [], []
        self.pose_recovery_blocked = False

    def guard(self, label, fn):
        try:
            return fn()
        except Exception as exc:
            self.statuses.append(("error", label, getattr(exc, "code", None), _TEXT(exc)))
            return None

    def current(self):
        return self.identity

    def operation_revalidate(self):
        pass

    def operation_mark_phase(self, phase, detail=None):
        pass

    def set_status(self, text, kind=None):
        self.statuses.append(("status", text, kind))

    def pose_begin_verification(self, label, pending):
        self.pending.append(pending)


def legacy_window(app, ns, reg, lib):
    methods = {}
    for name in ("pose_registry_mode", "pose_guard", "apply_pose"):
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, methods)
    for name, fn in methods.items():
        setattr(LegacyWindow, name, fn)
    ns["prod_pose_load_registry"] = lambda path=None: reg
    ns["prod_pose_selected_library"] = lambda ident: lib
    ns["prod_log_outcome"] = lambda *a, **k: None
    return LegacyWindow(context(ns, u"shot10"))


def section_final_undo(app, ns, F, reg, lib):
    real_load, real_selected = ns.get("prod_pose_load_registry"), ns.get("prod_pose_selected_library")
    name = u"Arms Out"
    label = u"Apply Pose %s" % name
    message = ns["PROD_POSE_MESSAGES"][u"recovery-unverified"] % {u"name": name}

    def destination(prepare=None):
        world = F.World(u"apply.dmx", handle_base=500000, poison_source=True)
        use_world(ns, F, world, u"shot10")
        world.set_frame(10)
        if prepare is not None:
            prepare(world)
        return world

    def item():
        return dict((i[u"name"], i) for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"],
                                                                      reg)[u"items"])[name]

    def direct(world):
        phases = []
        auth = authorize(ns, reg, u"shot10", u"Apply Pose", item(), mode=u"production")
        got = outcome(lambda: ns["prod_pose_apply"](IDENTITY, auth, item(), reg,
                                                    phase_callback=lambda p, d=None: phases.append(p)))
        return got, phases

    def through_guard(prepare=None):
        win = legacy_window(app, ns, reg, lib)
        world = destination(prepare)
        win.apply_pose(item())
        return win, world

    def writes(world):
        return [c for c in world.calls if c[0] in ("SetKeyValue", "InsertKeyAtTime", "InsertKey")] \
            if hasattr(world, "calls") else []

    def recovery_calls(world):
        return [c[0] for c in world.dm.calls if c[0] in ("AbortUndoableOperation", "Undo", "Redo")]

    def locked(win, world):
        return win.pose_recovery_blocked is True and not win.pending and bool(win.statuses) and \
            win.statuses[-1][0] == "error" and \
            win.statuses[-1][3] == message and not recovery_calls(world)

    def blocks_next(win):
        world = destination()
        before = authored(ns, reg, u"shot10")
        win.apply_pose(item())
        return bool(win.statuses) and win.statuses[-1][2] == u"recovery-blocked" and not world.dm.calls and \
            not win.pending and \
            authored(ns, reg, u"shot10") == before

    try:
        # U.1 StartUndo fails before native invocation (its arguments cannot be prepared): a plain refusal.
        real_name = ns["prod_pose_native_name"]

        def failing_name(text):
            if u"Apply Pose" in text:                  # only the Undo labels; attribute names still resolve
                raise RuntimeError("label preparation failed (test)")
            return real_name(text)
        ns["prod_pose_native_name"] = failing_name
        try:
            world = destination()
            before = authored(ns, reg, u"shot10")
            del ns["LOG"][:]
            got, phases = direct(world)
            reached = [x for x in ns["LOG"] if x.startswith(u"PROD_POSE_P1 ")]
            unchanged = authored(ns, reg, u"shot10") == before and not world.dm.calls
            win, gworld = through_guard()
        finally:
            ns["prod_pose_native_name"] = real_name
        check("U.1_failure_before_native_start_undo_is_a_plain_refusal",
              got[0] not in ("ok", "ProdRecoveryUnverifiedError") and unchanged and not phases and
              len(reached) == 1 and u"label preparation failed" in got[-1], got)
        check("U.1_guard_reports_it_without_lockout_or_undo", win.pose_recovery_blocked is False and
              win.statuses[-1][0] == "error" and not gworld.dm.calls, win.statuses[-1:])
        # U.2 the native StartUndo call raises, before and after simulated opening: uncertain, never not-applied.
        for when in ("before", "after"):
            world = destination(lambda w, when=when: setattr(w, "start_raises", when))
            before = authored(ns, reg, u"shot10")
            got, phases = direct(world)
            check("U.2_start_undo_raises_%s_opening_is_recovery_unverified" % when,
                  got[0] == "ProdRecoveryUnverifiedError" and authored(ns, reg, u"shot10") == before and
                  not phases and [c[0] for c in world.dm.calls] == ["StartUndo"] and
                  (world.dm.current is not None) == (when == "after"), (got, world.dm.calls))
            win, gworld = through_guard(lambda w, when=when: setattr(w, "start_raises", when))
            check("U.2_start_undo_raises_%s_opening_locks_out_through_pose_guard" % when, locked(win, gworld),
                  win.statuses[-1:])
        check("U.5_start_undo_lockout_refuses_the_next_apply", blocks_next(win), win.statuses[-1:])

        # U.3 Astra's counterexample: an older Undo entry has the identical description; FinishUndo raises before
        # closing the current transaction. The matching description is never evidence of commitment.
        def older_and_open(w):
            w.dm.stack.append({"undo": label, "redo": u"Redo " + label, "items": []})
            w.finish_raises = "before"
        world = destination(older_and_open)
        del ns["LOG"][:]
        got, phases = direct(world)
        evidence = [x for x in ns["LOG"] if u"PROD_POSE_finish-undo-uncertain" in x]
        check("U.3_finish_undo_raises_before_closure_with_an_identical_older_entry_is_recovery_unverified",
              got[0] == "ProdRecoveryUnverifiedError" and u"native-commit" not in phases and
              world.dm.current is not None and len(world.dm.stack) == 1 and world.dm.GetUndoDesc() == label,
              (got, phases))
        check("U.3_no_abort_or_undo_of_the_uncertain_operation", not recovery_calls(world) and
              [c[0] for c in world.dm.calls] == ["StartUndo", "FinishUndo"], world.dm.calls)
        check("U.3_diagnostic_evidence_keeps_the_exception_and_observed_undo_state",
              len(evidence) == 1 and u"FinishUndo failed before commit" in evidence[0] and
              u"undo_desc" in evidence[0] and u"pre_undo" in evidence[0], evidence)
        win, gworld = through_guard(older_and_open)
        check("U.3_locks_out_through_pose_guard_no_p7_scheduled", locked(win, gworld), win.statuses[-1:])
        check("U.5_finish_undo_lockout_refuses_the_next_apply", blocks_next(win), win.statuses[-1:])
        # U.4 FinishUndo raises after simulated commitment: still uncertain.
        world = destination(lambda w: setattr(w, "finish_raises", "after"))
        got, phases = direct(world)
        check("U.4_finish_undo_raises_after_commit_is_recovery_unverified",
              got[0] == "ProdRecoveryUnverifiedError" and u"native-commit" not in phases and
              len(world.dm.stack) == 1 and world.dm.GetUndoDesc() == label and not recovery_calls(world),
              (got, phases))
        win, gworld = through_guard(lambda w: setattr(w, "finish_raises", "after"))
        check("U.4_locks_out_through_pose_guard_no_p7_scheduled", locked(win, gworld), win.statuses[-1:])
        check("U.5_after_commit_lockout_refuses_the_next_apply", blocks_next(win), win.statuses[-1:])
        # U.6 no uncertain branch above performed an Abort or Undo (checked per case). U.7 the normal path.
        win, world = through_guard()
        check("U.7_normal_apply_commits_and_schedules_p7", len(win.pending) == 1 and
              [c[0] for c in world.dm.calls] == ["StartUndo", "FinishUndo"] and world.dm.GetUndoDesc() == label
              and win.pose_recovery_blocked is False, win.statuses[-1:])
        world.run_events()
        world.evaluate(world.shots[u"shot10"])
        verdict = ns["prod_pose_deferred_verify"](win.pending[0]) if win.pending else None
        check("U.7_p7_verifies", verdict == {u"phase": u"committed-verified"}, verdict)
        calls = len(world.dm.calls)
        win.apply_pose(item())
        check("U.7_repeat_is_a_true_noop", win.statuses[-1][1] == ns["PROD_POSE_MESSAGES"][u"no-op"] and
              len(world.dm.calls) == calls and len(win.pending) == 1, win.statuses[-1:])
        world = destination()
        before = authored(ns, reg, u"shot10")
        ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        result, _, _ = apply_and_verify(ns, reg, world, item(), run=False)
        check("U.7_owned_abort_restores_and_verifies", result.get("phase") == u"not-applied" and
              authored(ns, reg, u"shot10") == before and not world.dm.stack and world.dm.current is None and
              recovery_calls(world) == ["AbortUndoableOperation"], result)
    finally:
        ns["PROD_POSE_QUAL_FAULT"][0] = None
        ns["prod_pose_load_registry"], ns["prod_pose_selected_library"] = real_load, real_selected


def section_static(app):
    block, _ = core.extract_block(route.APP_PATH, BLOCKS[3][0], BLOCKS[3][1])
    writes = [t for t in ("SetKeyValue(", "InsertKeyAtTime(", "InsertKey(", "StartUndo(", "FinishUndo(",
                          "AbortUndoableOperation(") if t in block]
    check("D0.stage_d_has_exactly_the_planned_native_mutations", sorted(writes) == sorted(
        ["SetKeyValue(", "InsertKeyAtTime(", "StartUndo(", "FinishUndo(", "AbortUndoableOperation("]), writes)
    # NQ-1 run 2, process B: GetDefaultCurveType() crashed SFM natively (no curve info on any log CPM may write).
    code = "\n".join(line.split("#")[0] for line in block.splitlines())
    check("D0.never_calls_get_default_curve_type", "GetDefaultCurveType(" not in code)
    code_only = code
    refresh = block[block.index("def prod_pose_request_refresh"):block.index("def prod_pose_preflight")]
    check("D0.one_same_time_head_request_only_in_the_refresh_helper",
          code_only.count("SetHeadTimeInSeconds(") == 1 and "SetHeadTimeInSeconds(" in refresh
          and "SetHeadTimeInFrames(" not in code_only and "ProcessEvents" not in code_only)
    check("D0.timeline_mode_read_only", "SetTimelineMode" not in code_only and code_only.count("GetTimelineMode(") == 1)
    for banned in ("SetKey(", "RemoveKey", ".Undo(", ".Redo(", "SetCurrentTime", "ClearKeys"):
        check("D0.stage_d_never_calls_%s" % banned.strip("(.").lower(), banned not in block)
    check("D0.stage_d_never_reads_pose_source", u'[u"source"]' not in block.split("def prod_pose_capture")[0]
          and block.count(u'[u"source"]') == 1, block.count(u'[u"source"]'))
    check("D0.insert_is_insert_key_at_time_then_set_key_value",
          "index = int(layer.InsertKeyAtTime(prod_pose_time(plan[u\"t\"])))" in block
          and block.index("InsertKeyAtTime(prod_pose_time") < block.index("    layer.SetKeyValue(index, value)"))
    init = app.method_text("ProdWindow", "__init__")
    order = [init.index(s) for s in ('"Clothing Fit")', '"Poses")', '"Review",')]
    check("D12.poses_tab_after_clothing_fit_review_last", order == sorted(order), order)
    labels = [s for s in ("Apply Pose", "Save New", "Search poses") if s in init]
    check("D12.poses_page_labels_present_without_ellipses", len(labels) == 3 and "..." not in init.split(
        "# Poses (F-01")[1].split('"Poses")')[0] and u"…" not in init)
    check("D12.registry_mode_is_the_build_constant_only",
          "return PROD_POSE_REGISTRY_MODE" in app.method_text("ProdWindow", "pose_registry_mode")
          and not __import__("re").search(r"pose_mode", app.text(1, len(app.lines))))
    check("D12.production_source_mode_is_production",
          app.top_text("PROD_POSE_REGISTRY_MODE").strip() == u'PROD_POSE_REGISTRY_MODE = u"production"')


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 stage D live layer (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    if not core.w2_verified():
        print("RESULT: W2 oracle files do not verify; stopping")
        return 1
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01d_lib_")
    try:
        F = load_fake()
        ns = build_namespace(app, F)
        reg = registry(ns)
        section_static(app)
        lib = run("process_a", lambda: process_a(ns, F, reg, root))
        state = run("process_b", lambda: process_b(ns, F, reg, lib)) if lib else None
        if state:
            run("abort", lambda: section_abort(ns, F, reg, *state))
        if lib:
            run("refusals", lambda: section_refusals(ns, F, reg, lib))
            run("final_undo", lambda: section_final_undo(app, ns, F, reg, lib))
        run("channel_clock", lambda: section_channel_clock(ns, F, reg, root))
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


def run(label, fn):
    try:
        value = fn()
        check("section.%s.completed" % label, True)
        return value if value is not None else True
    except (Exception, FakeNativeCrash):
        check("section.%s.completed" % label, False, traceback.format_exc())
        return None


if __name__ == "__main__":
    sys.exit(main())
