# -*- coding: utf-8 -*-
# M-06 W2 native qualification: ONE-SHOT precommit failure injector v3. TEMPORARY qualification instrument.
#
# Installed (temporarily, by an authorized native session) as:
#   <SFM game>\usermod\scripts\sfm\mainmenu\M06 Qualification\M06_Qualification_Abort_Injector.py
# with m06w2_core.py and m06w2_config.json in INSTRUMENT_DIR.
#
# Pinned to the accepted W1 candidate fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d. Any other
# installed CPM refuses to arm (fail closed). Order inside that candidate's owned Body Apply transaction:
#   prod_apply 28995 StartUndo -> 29005 prod_bs_create_graph (each missing scale graph) -> existing-scale writes
#   -> 29025 write_side (flex) -> precommit verification -> 29086 FinishUndo; any exception before FinishUndo ->
#   29105 prod_abort_apply_and_verify (AbortUndoableOperation, then CPM's own verification).
#
# Arming (CPM open and idle): one complete read-only baseline observation is taken; an incomplete baseline refuses to
# arm. The wrapper around the loaded CPM module's write_side then waits for the target literal. When it fires it
#   1. performs the real write (CPM's own call),
#   2. takes one complete read-only in-transaction observation,
#   3. records, independently of CPM, every created control, operator and channel (with endpoints), each new
#      animation-set, channel-container and control-group membership, each created scale attribute with its physical
#      value, and the nonselected peer state,
#   4. writes the watch list read by the post-abort Observer, restores write_side and raises, so CPM's own
#      abort-and-verify path runs. It fires at most once and shows no dialog inside the transaction.
# Running the script again while armed disarms it. It writes nothing to the scene and is gone when SFM exits.

INSTRUMENT_DIR = u"<INSTRUMENT_DIR>"     # replaced by tools/stage_instruments.py when the run is prepared


def _m06w2_abort_injector():
    import hashlib
    import io
    import json
    import os
    import sys
    import time

    CANDIDATE_SHA256 = u"fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
    CONFIG_NAME = u"m06w2_config.json"       # the ordinary configuration, shared with M06_Qualification_Observer
    MARK = "_m06w2_qualification_injector"

    core = {"__name__": "m06w2_core_private"}
    core_path = os.path.join(INSTRUMENT_DIR, u"m06w2_core.py")
    with open(core_path, "rb") as f:
        eval(compile(f.read(), core_path, "exec"), core)
    with io.open(os.path.join(INSTRUMENT_DIR, CONFIG_NAME), encoding="utf-8") as f:
        config = json.load(f)
    record_dir = config["observation_dir"]
    target_literal = config["injector"]["target_literal"]

    def message(text):
        try:
            from PySide import QtGui
            QtGui.QMessageBox.information(None, u"M06 Qualification Abort Injector", text)
        except Exception:
            print(text)

    def record(event, data):
        if not os.path.isdir(record_dir):
            os.makedirs(record_dir)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        row = {"event": event, "taken_local": stamp, "injector": u"v3", "candidate_sha256": CANDIDATE_SHA256}
        row.update(data)
        path = os.path.join(record_dir, u"injector_%s_%s.json" % (stamp, event))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(core["dumps"](row).encode("ascii"))
        return path

    module = sys.modules.get("chadchan3d_cpm_app")
    if module is None or not callable(getattr(module, "write_side", None)):
        message(u"CPM is not loaded. Open the Character Preset Manager first. Nothing was armed.")
        return
    current = module.write_side
    if getattr(current, MARK, False):
        module.write_side = getattr(current, "real")
        record("disarmed-by-operator", {"fired": False})
        message(u"Injector DISARMED (it had not fired). write_side restored.")
        return
    if config.get("config_name") != CONFIG_NAME:
        # The staged configuration records its own name; the injector's observations carry exactly that verified
        # identity, so the comparator can require one configuration across Observer and injector evidence.
        message(u"The configuration %s names itself %r: not the staged ordinary configuration. Nothing was armed." %
                (CONFIG_NAME, config.get("config_name")))
        return
    installed = core["sha256_file"](config["cpm"]["path"])
    if installed != CANDIDATE_SHA256:
        message(u"The installed CPM is not the accepted W1 candidate (%s). Nothing was armed." % installed[:16])
        return

    import sfmApp
    import vs
    baseline = core["observe"](sfmApp, vs, config, label=u"injector-armed-baseline", config_name=CONFIG_NAME)
    if not baseline["complete"]:
        record("arm-refused", {"baseline": baseline})
        message(u"The baseline observation is INSUFFICIENT; nothing was armed:\n" +
                u"\n".join(baseline["insufficient"][:8]))
        return
    real = current
    state = {"fired": False}

    def injected(binding, side, origin, desired):
        result = real(binding, side, origin, desired)
        literal = binding.get("literal") if isinstance(binding, dict) else None
        if not state["fired"] and literal == target_literal:
            state["fired"] = True
            module.write_side = real
            try:
                during = core["observe"](sfmApp, vs, config, label=u"injector-in-transaction",
                                         config_name=CONFIG_NAME)
                created = core["created_elements"](baseline, during)
                evidence = {"in_transaction": during, "created": created["created"],
                            "scale_attributes_created": created["scale_attributes_created"],
                            "memberships_added": created["memberships_added"],
                            "peer_changes": created["peer_changes"]}
            except Exception as exc:
                created = {"created": []}
                evidence = {"evidence_error": repr(exc), "created": []}
            watch_path = config.get("watch_path")
            if watch_path:
                with io.open(watch_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps({"created": created["created"]}, indent=1, sort_keys=True,
                                       ensure_ascii=True).encode("ascii").decode("ascii"))
            record("fired", dict(evidence, literal=literal, side=repr(side), origin=repr(origin),
                                 desired=float(desired), baseline=baseline))
            raise RuntimeError("M06 QUALIFICATION INJECTED PRECOMMIT FAILURE after scale-graph creation and the "
                               "%s write" % literal)
        return result

    setattr(injected, MARK, True)
    injected.real = real
    module.write_side = injected
    record("armed", {"target": target_literal, "cpm_sha256": installed, "baseline": baseline})
    message(u"Injector ARMED for one Body Apply (target %s). Inside that Apply's transaction it records the created "
            u"graph elements after the real write, then fails the transaction before commit.\n\n"
            u"Run this script again to disarm without firing." % target_literal)


try:
    _m06w2_abort_injector()
finally:
    del _m06w2_abort_injector
