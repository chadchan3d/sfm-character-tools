# -*- coding: utf-8 -*-
# M-06 W2: deferred-verification fixture preparation. NATIVE SCRIPT - PREPARED, NOT EXECUTED.
# Run only in a separately authorized native session, on a NEW DISPOSABLE COPY of the accepted M-05 fixture.
#
# It changes exactly one authored value: the stored source ("value") of the one selected Body flex control, inside one
# labelled Undo entry. It never touches the key, the log, the channel, the graph or any other element, and never
# saves: the Owner saves the disposable copy with File > Save As to the configured persistence path afterwards.
#
# Refuses (nothing changed) unless:
#   * the open document is the configured disposable copy, its bytes on disk equal the recorded copy hash, and the
#     protected original still has its recorded hash and is a different file;
#   * a complete read-only observation of the target exists;
#   * the selected flex natively has mode 3, one layer, one key at time zero, a stored source equal to that key, and
#     coherent native evaluation (log value at the channel's current time == key == destination flexWeight);
#   * the configuration is the staged deferred configuration (config_name m06w2_deferred_config.json);
#   * the configured existing scale graph is the qualified mode-3 graph: exactly one graph on the configured bone,
#     every input channel and the output channel mode 3, the output writing that bone's "scale", the expression
#     operator and source control resolved (a graph with output mode 1 refuses).
# After the change it runs tools/compare_obs.py "prepared" (staged beside it) in-session against the before and
# after observations. Only on PASS is the Owner told to File > Save As; on any other verdict the stop record says
# DO NOT SAVE and the disposable copy must be closed without saving. The same comparison is repeated offline, and
# after reopening the saved copy, "reopened" (with static_play) re-verifies the representation and the mode-3 graph.

INSTRUMENT_DIR = u"<INSTRUMENT_DIR>"


def _m06w2_prepare_deferred_fixture():
    import io
    import json
    import os
    import time

    import sfmApp
    import vs

    core = {"__name__": "m06w2_core_private"}
    core_path = os.path.join(INSTRUMENT_DIR, u"m06w2_core.py")
    with open(core_path, "rb") as f:
        eval(compile(f.read(), core_path, "exec"), core)
    with io.open(os.path.join(INSTRUMENT_DIR, u"m06w2_deferred_config.json"), encoding="utf-8") as f:
        config = json.load(f)
    cmp_path = os.path.join(INSTRUMENT_DIR, u"compare_obs.py")
    compare = {"__name__": "m06w2_compare_private"}
    with open(cmp_path, "rb") as f:
        eval(compile(f.read(), cmp_path, "exec"), compare)
    prep = config["preparation"]
    out_dir = config["observation_dir"]

    def norm(p):
        return os.path.normcase(os.path.realpath(os.path.abspath(p)))

    def write(name, data):
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        path = os.path.join(out_dir, u"prep_%s_%s.json" % (time.strftime("%Y%m%dT%H%M%S"), name))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(core["dumps"](data).encode("ascii"))
        return path

    def stop(why, **data):
        data["stop"] = why
        path = write("stop", data)
        message(u"FIXTURE PREPARATION STOPPED (nothing changed):\n%s\n\n%s" % (why, path))

    def message(text):
        try:
            from PySide import QtGui
            QtGui.QMessageBox.information(None, u"M06 Deferred Fixture Preparation", text)
        except Exception:
            print(text)

    if config.get("config_name") != u"m06w2_deferred_config.json":
        return stop(u"The configuration is not the staged deferred configuration (config_name %r)" %
                    (config.get("config_name"),))
    doc = sfmApp.GetDocumentRoot()
    path = vs.g_pDataModel.GetFileName(doc.GetFileId())
    if norm(path) != norm(prep["disposable_copy"]) or norm(path) == norm(prep["protected_original"]):
        return stop(u"The open document is not the configured disposable copy: %s" % path)
    if core["sha256_file"](prep["disposable_copy"]) != prep["disposable_copy_sha256"]:
        return stop(u"The disposable copy's bytes on disk differ from the recorded copy")
    if core["sha256_file"](prep["protected_original"]) != prep["protected_original_sha256"]:
        return stop(u"The protected original's hash changed")
    before = core["observe"](sfmApp, vs, config, label=u"deferred-preparation-before",
                             config_name=u"m06w2_deferred_config.json")
    if not before["complete"]:
        return stop(u"The baseline observation is insufficient", before=before)
    try:
        compare["sufficiency"](before, u"before")
    except compare["Verdict"] as v:
        return stop(u"The baseline observation is insufficient: %s" % u"; ".join(v.reasons[:6]), before=before)
    lit = prep["literal"]
    side = (before["target"]["flex"].get(lit) or {}).get("mono")
    try:
        layers = side["log"]["v"]["layers"]
        keys = layers[0]["keys"]["v"]
        coherent = (side["mode"]["v"] == 3 and len(layers) == 1 and len(keys) == 1 and keys[0][0] == 0 and
                    keys[0][1] == side["log"]["v"]["evaluated"]["v"] == side["destination_value"]["v"] and
                    side["stored"]["v"] == keys[0][1] and side["representation"]["v"] == u"ONE_KEY_ZERO")
    except Exception as exc:
        coherent = False
        side = {"error": repr(exc)}
    if not coherent:
        return stop(u"%s does not have the required mode-3 one-key representation with coherent evaluation" % lit,
                    before=before)
    graphs = [g for g in before["target"]["graphs"] if g["bone"] == prep["graph_bone"]]
    graph_problems = compare["qualified_graph_problems"](before)
    if len(graphs) != 1 or not graphs[0]["inputs"] or graph_problems:
        return stop(u"The existing mode-3 scale graph on %s is not intact: %s" %
                    (prep["graph_bone"], u"; ".join(graph_problems) or u"%d graph(s)" % len(graphs)), before=before)
    if keys[0][1] == prep["stored"]:
        return stop(u"The declared stored value is not distinct from the key")
    shot = sfmApp.GetShotAtCurrentTime()
    sets = [a for a in core["read_list"](shot, "animationSets")[1] or []
            if core["ident"](a).get("v", {}).get("name") == config["target_animset"]]
    controls = [c for c in core["read_list"](sets[0], "controls")[1] or []
                if core["ident"](c).get("v", {}).get("name") == lit] if len(sets) == 1 else []
    if len(controls) != 1:
        return stop(u"The control %s could not be resolved uniquely" % lit, before=before)
    from PySide import QtGui
    answer = QtGui.QMessageBox.question(
        None, u"M06 Deferred Fixture Preparation",
        u"Change ONLY the stored source of %s from %r to %r in the disposable copy?\n%s" %
        (lit, side["stored"]["v"], prep["stored"], path), QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
    if answer != QtGui.QMessageBox.Yes:
        return stop(u"The Owner declined the change")
    dm = vs.g_pDataModel
    # Byte-str labels: SFM's SWIG StartUndo takes char* (production CPM passes b(label)).
    dm.StartUndo("M06W2 deferred fixture preparation", "M06W2 deferred fixture preparation redo")
    try:
        controls[0].GetAttribute("value").SetValue(prep["stored"])
    finally:
        dm.FinishUndo()
    after = core["observe"](sfmApp, vs, config, label=u"deferred-preparation-after",
                            config_name=u"m06w2_deferred_config.json")
    p_before, p_after = write("before", before), write("after", after)
    verdict, reasons = compare["compare"](u"prepared", before, after, {"literal": lit, "stored": prep["stored"]})
    if verdict != compare["PASS"]:
        path = write("stop", {"stop": u"prepared comparison %s: DO NOT SAVE" % verdict, "reasons": reasons,
                              "before_file": p_before, "after_file": p_after})
        message(u"PREPARED COMPARISON %s - DO NOT SAVE.\nClose the disposable copy WITHOUT saving.\n%s\n\n%s" %
                (verdict, u"\n".join(reasons[:8]), path))
        return
    write("verdict", {"verdict": verdict, "invariant": u"prepared", "before_file": p_before, "after_file": p_after})
    message(u"Stored source of %s set to %r; prepared comparison PASS.\nBefore: %s\nAfter: %s\n\n"
            u"Now File > Save As the disposable copy to\n%s\n"
            u"then quit SFM, reopen it, set the playhead and run the Deferred Observer." %
            (lit, prep["stored"], p_before, p_after, prep["save_as"]))


try:
    _m06w2_prepare_deferred_fixture()
finally:
    del _m06w2_prepare_deferred_fixture
