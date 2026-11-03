# -*- coding: utf-8 -*-
# M-06 W2 native prerequisites probe. NATIVE SCRIPT - PREPARED, NOT EXECUTED. Read-only.
#
# Records, without changing anything, the native behaviour W1 depends on:
#   1. str(GetId()) rendering: stable across two reads and two wrappers, distinct between elements, content (not a
#      pointer repr);
#   2. vs.tier1.IsUniqueIdValid / IsUniqueIdEqual and vs.g_pDataModel.GetElementId / GetElement: availability,
#      return types and agreement;
#   3. the selected-instance token, recorded with W1's own components (document root key, the current shot's file
#      id, shot key, the configured target animation set's key and its game model's key, model and checksum), each
#      four-state: run once, then File > Open the same document in the same SFM session and run again;
#      tools/compare_probes.py decides whether that token is invalidated even though persisted element ids survive
#      (an unreadable component is never taken as invalidation; peers are not part of the token);
#   4. channels-clip topology: channelTrackGroup / animSetEditorChannels children, types, names, channels counts,
#      and which clip holds each selected-instance control channel;
#   6. HasAttribute() / GetAttribute() agreement for the optional channel attributes on every control of the target
#      and peers (return types, AttributeError versus None, presence disagreements);
#   plus the Undo bindings' False/empty forms (CanUndo, CanRedo, GetUndoDesc, GetRedoDesc) as observed.
# Item 5 (real render() with duplicate same-model instances) is a UI procedure, not a probe: see
# procedures/NATIVE_PROCEDURES.md.

INSTRUMENT_DIR = u"<INSTRUMENT_DIR>"


def _m06w2_native_probe():
    import hashlib
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
    with io.open(os.path.join(INSTRUMENT_DIR, u"m06w2_config.json"), encoding="utf-8") as f:
        config = json.load(f)
    call = core["strict_call"]
    probe = {"format": u"M06W2-native-probe-v2", "taken_local": time.strftime("%Y%m%dT%H%M%S"),
             "config_name": u"m06w2_config.json",
             "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()}

    def typed(ok, v):
        return {"ok": ok, "type": type(v).__name__, "repr": repr(v)[:200]}

    tier1 = getattr(vs, "tier1", None)
    dm = vs.g_pDataModel
    probe["api"] = dict((n, callable(getattr(obj, n, None))) for obj, names in
                        ((tier1, ("IsUniqueIdValid", "IsUniqueIdEqual")), (dm, ("GetElementId", "GetElement")))
                        for n in names)
    doc = sfmApp.GetDocumentRoot()
    shot = sfmApp.GetShotAtCurrentTime()
    sets = core["read_list"](shot, "animationSets")[1] or []
    samples = [(u"document_root", doc), (u"shot", shot)]
    for a in sets:
        samples.append((u"animset", a))
        gm = core["element_ref"](a, "gameModel")[1]
        if gm is not None:
            samples.append((u"game_model", gm))
    rows = []
    for role, el in samples:
        row = {"role": role, "ident": core["ident"](el)}
        ok1, id1 = call(el, "GetId")
        ok2, id2 = call(el, "GetId")
        row["str_twice"] = [repr(str(id1)) if ok1 else None, repr(str(id2)) if ok2 else None]
        ok_h, h = call(el, "GetHandle")
        row["handle"] = typed(ok_h, h)
        if probe["api"].get("GetElementId"):
            ok_r, reg = call(dm, "GetElementId", h)
            row["registered_str"] = repr(str(reg)) if ok_r else typed(ok_r, reg)
            if probe["api"].get("IsUniqueIdEqual"):
                row["equal_to_registered"] = typed(*call(tier1, "IsUniqueIdEqual", id1, reg))
        if probe["api"].get("IsUniqueIdValid"):
            row["valid"] = typed(*call(tier1, "IsUniqueIdValid", id1))
        if probe["api"].get("GetElement"):
            ok_e, live = call(dm, "GetElement", h)
            row["get_element_same_handle"] = ok_e and live is not None and call(live, "GetHandle")[1] == h
        rows.append(row)
    if len(samples) >= 2 and probe["api"].get("IsUniqueIdEqual"):
        a_id, b_id = call(samples[0][1], "GetId")[1], call(samples[1][1], "GetId")[1]
        probe["distinct_elements_equal"] = typed(*call(tier1, "IsUniqueIdEqual", a_id, b_id))
    probe["identities"] = rows
    # The selected-instance token, component by component as W1's prod_selection_token() builds it.
    ok_f, fid = call(shot, "GetFileId")
    if ok_f and not isinstance(fid, bool) and isinstance(fid, core["INTEGER_TYPES"]):
        file_id = core["present"](int(fid))
    else:
        file_id = core["unreadable"](u"GetFileId: %r" % (fid,))
    wanted = config.get("target_animset")
    named = [a for a in sets if call(a, "GetName")[0] and call(a, "GetName")[1] == wanted]
    token = {"target_animset": wanted, "document_key": core["ident"](doc), "document_file_id": file_id,
             "shot_key": core["ident"](shot)}
    if len(named) == 1:
        gm_rec, gm = core["element_ref"](named[0], "gameModel")
        token["animset_key"] = core["ident"](named[0])
        token["gm_key"] = gm_rec
        token["model"] = core["value"](gm, "modelName") if gm is not None else core["unreadable"](u"no game model")
        token["checksum"] = core["checksum_of"](gm) if gm is not None else core["unreadable"](u"no game model")
    else:
        for k in ("animset_key", "gm_key", "model", "checksum"):
            token[k] = core["unreadable"](u"%d animation sets named %r" % (len(named), wanted))
    token["complete"] = all(token[k].get("s") == u"present" for k in ("document_key", "document_file_id",
                                                                      "shot_key", "animset_key", "gm_key",
                                                                      "model", "checksum"))
    probe["selected_token"] = token
    probe["document_path"] = repr(call(dm, "GetFileName", fid)[1]) if ok_f else None
    topology = []
    group = call(shot, "FindTrackGroup", "channelTrackGroup")
    track = call(group[1], "FindTrack", "animSetEditorChannels") if group[0] and group[1] is not None else (False, None)
    probe["channel_track"] = {"group": typed(*group), "track": typed(*track)}
    if track[0] and track[1] is not None:
        kids_rec, kids = core["read_list"](track[1], "children")
        probe["channel_track"]["children"] = kids_rec
        for clip in kids or []:
            ch_rec, chans = core["read_list"](clip, "channels")
            topology.append({"clip": core["ident"](clip), "channels": ch_rec})
    probe["channels_clips"] = topology
    agreement = {}
    examined = 0
    probe["channel_attrs"] = list(core["CHANNEL_ATTRS"])
    for a in sets:
        c_rec, controls = core["read_list"](a, "controls")
        if c_rec.get("s") != u"present":
            probe.setdefault("controls_unreadable", []).append(core["ident"](a))
        for c in controls or []:
            examined += 1
            for attr in core["CHANNEL_ATTRS"]:
                ok_has, has = call(c, "HasAttribute", attr)
                try:
                    got = c.GetAttribute(attr)
                    outcome = u"attribute" if got is not None else u"None"
                except AttributeError:
                    outcome = u"AttributeError"
                except Exception as exc:
                    outcome = u"raised %s" % type(exc).__name__
                key = u"%s|has=%s(%s)|get=%s" % (attr, has if ok_has else u"error", type(has).__name__, outcome)
                agreement[key] = agreement.get(key, 0) + 1
    probe["has_get_agreement"] = agreement
    probe["controls_examined"] = examined
    probe["undo_bindings"] = dict((m, typed(*call(dm, m))) for m in ("IsUndoEnabled", "CanUndo", "CanRedo",
                                                                     "GetUndoDesc", "GetRedoDesc",
                                                                     "GetUndoItemCount"))
    out_dir = config["observation_dir"]
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    path = os.path.join(out_dir, u"probe_%s.json" % probe["taken_local"])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(probe, indent=1, sort_keys=True, default=repr).encode("utf-8"))
    try:
        from PySide import QtGui
        QtGui.QMessageBox.information(None, u"M06 Native Probe", u"Probe saved (read-only):\n" + path)
    except Exception:
        print(path)


try:
    _m06w2_native_probe()
finally:
    del _m06w2_native_probe
