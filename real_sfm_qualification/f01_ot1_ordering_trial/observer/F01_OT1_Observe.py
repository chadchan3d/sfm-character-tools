# -*- coding: ascii -*-
"""F-01 OT1: the ordering trial's observer (Astra adjudication, ACCEPT WITH CONDITIONS; qualification only). Run from
SFM's Script Editor (Python 2.7) with Character Preset Manager open:

    OT1_DIR = r"<run folder>"; OT1_REPO = r"<repo>"
    OT1_STEP = "BASE"; execfile(OT1_REPO + r"\\real_sfm_qualification\\f01_ot1_ordering_trial\\observer\\F01_OT1_Observe.py")

It reuses, unchanged, the pinned Q1 observer's read-only functions (full saved-scale map with CPM's own predicates,
raw animation-set fields, plain JSON forms): F01_Q1_Observe.py is loaded only when its SHA-256 equals Q1_OBSERVER_SHA256
and never runs its own capture.

1. Hooks (installed by BASE, removed by ABORT; they live only in this SFM process). Each wrapper calls the original
   with the same arguments and returns its result unchanged (an exception is re-raised unchanged); it only records:
   - prod_apply: the operation and its outcome;
   - prod_bs_write_existing_scale: CPM's prod_bs_snapshot of the scale's binding immediately before and immediately
     after CPM's own write (inside the owned transaction, after the candidate's expression Operate(); the same
     read-only snapshot CPM itself takes there): the "precommit" read;
   - same_time_refresh: after CPM's existing refresh, the same snapshot of each scale written by the operation (the
     lightweight "after the refresh" read; nothing is read before the refresh);
   - prod_bs_index_verify_saved: after CPM's own deferred check returns, the full saved map on the snapshot CPM used;
   - prod_verify_apply_abort_baseline: its result (CPM's own abort verification).
2. The one controlled failure (armed by ARM; fires at most once): when the armed hook sees CPM's write of
   OT1_FAIL_BONE return normally (its input written and its expression operated and verified by the candidate), it
   records the event and raises RuntimeError("OT1 controlled failure after the operator call") from inside the owned
   transaction, so CPM's own abort-and-verify path runs. Nothing else is injected, retried, refreshed or undone.
3. Captures (each step once): session (document, shot, time, Undo/Redo descriptions and count), the selected
   character and instance, the raw fields of every animation set in the shot (Q1's reader), the settled full map of
   the selected instance against the `Body` record, and the hook events since the previous capture.

4. BASE preflight (read only; before the hooks are installed): for the selected instance's existing `bip_head` and
   `bip_tail00` scale graphs, CPM's own read-only prod_bs_index_snapshot and prod_bs_index_binding, then:
   - the candidate's own scan, prod_bs_expression_channels (the exact function the candidate calls before Operate()):
     its reader and writer counts and identities, or the error it raises (it stops at the first unreadable item);
   - a diagnostic enumeration over the same structure with the same strict primitives that continues past
     unreadable items and lists every unreadable track, clip, channel list or endpoint and every reader and writer;
   - the candidate's other pre-Operate graph checks that need no plan baseline (expression type and text, the four
     endpoints, static output mode 3);
   - which animation sets list the expression in their `operators` array (reported only; not part of the candidate);
   - Astra's DC1 condition with the DC2 correction, direct DataModel references: for each live expression the
     IDataModel iterator primitives on vs.g_pDataModel (FirstAttributeReferencingElement, GetAttributeFromIterator,
     NextAttributeReferencingElement; vsUtils is NOT imported) are traversed until the token equals
     vs.DMATTRIBUTE_REFERENCE_ITERATOR_INVALID (explicit comparison), recording every referring attribute's owner
     identity and name; it must return exactly the selected animation set's `operators`, the admitted input channel's
     `toElement` and the admitted output channel's `fromElement`, matched by live element identity (no names, no saved
     identities). A missing, extra, unexpected or unreadable reference, a repeated token, an API exception or a
     traversal that does not reach the sentinel fails. Before and after each traversal the class-dictionary entries
     CDmElement.__eq__/__hash__, Vector/QAngle/Quaternion.__hash__ (an explicit marker when absent) and sys.modules'
     vsUtils membership are snapshotted and must be identical objects;
   - "would_pass": the candidate's graph-uniqueness precondition and the direct-reference condition hold for both.
   The same preflight runs again at ARM, before arming; a failing ARM preflight leaves the injector unarmed.
   Undo state and playhead are read before and after the preflight and recorded. Nothing is operated, written,
   refreshed or moved, and no Undo action is opened.
   Coverage: the channel scan sees DmeChannel elements listed in the `channels` array of DmeChannelsClip children of
   the shot's channelTrackGroup / animSetEditorChannels track, by their fromElement and toElement; the DC1 traversal
   sees every direct DataModel attribute reference to each expression (any owner, element or element-array
   attribute). Not covered: indirect relationships, Python-side references and anything outside the DataModel.

Its only write is <OT1_DIR>\\observations\\OT1-<step>.json (exclusive create).

Steps: BASE (peer created, A selected; installs the hooks), APPLY (after Apply Body), UNDO (after Ctrl+Z), REDO (after
Ctrl+Y), UNDO2 (after Ctrl+Z), ARM (arms the controlled failure), ABORT (after the second Apply Body and its error
message; removes the hooks).
"""
import hashlib
import json
import os
import sys
import time

OT1_STEPS = ("BASE", "APPLY", "UNDO", "REDO", "UNDO2", "ARM", "ABORT")
OT1_HOOKED = ("prod_apply", "prod_bs_write_existing_scale", "same_time_refresh", "prod_bs_index_verify_saved",
              "prod_verify_apply_abort_baseline")
OT1_STATE = "_f01_ot1_state"
OT1_RECORD = u"Body"
OT1_FAIL_BONE = u"bip_tail00"
OT1_FAIL_TEXT = "OT1 controlled failure after the operator call"
Q1_OBSERVER_SHA256 = "f2eba1e0abce6e1e1e68202546e750b99dc0032f105d393bf0a40111824fca58"
OT1_PREFLIGHT_BONES = (u"bip_head", u"bip_tail00")
OT1_REF_EXPECTED = (("animset", "operators"), ("input_channel", "toElement"), ("output", "fromElement"))
OT1_REF_LIMIT = 4096
OT1_CLASS_ENTRIES = (("CDmElement", "__eq__"), ("CDmElement", "__hash__"), ("Vector", "__hash__"),
                     ("QAngle", "__hash__"), ("Quaternion", "__hash__"))
SNAP_FIELDS = ("source", "key_value", "key_count", "expr_input", "expr_result", "physical_scale", "input_mode",
               "output_mode", "output_key_count", "output_is_empty", "output_use_default_value", "lo", "hi",
               "expression_id", "output_id", "transform_id", "input_channel_id", "control_id")


def ot1_q1(repo):
    """The Q1 observer's functions, verified by SHA-256, loaded without running its capture."""
    path = os.path.join(repo, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer", "F01_Q1_Observe.py")
    with open(path, "rb") as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != Q1_OBSERVER_SHA256:
        raise RuntimeError("The Q1 observer is not the pinned %s." % Q1_OBSERVER_SHA256)
    g = {"__name__": "q1_observer_under_test"}
    exec(compile(raw, path, "exec"), g)
    return g


def ot1_state(cpm):
    return getattr(cpm, OT1_STATE, None)


def ot1_record(st, kind, **fields):
    try:
        st["seq"] += 1
        fields.update(seq=st["seq"], kind=kind, time=time.time())
        st["events"].append(fields)
    except Exception:
        pass


def ot1_snap(cpm, q1, binding):
    """CPM's own read-only prod_bs_snapshot of a binding, reduced to the fields the trial compares."""
    try:
        s = cpm.prod_bs_snapshot(binding)
        return dict((k, q1["q1_plain"](s.get(k))) for k in SNAP_FIELDS)
    except Exception as exc:
        return {"error": repr(exc)}


def ot1_install(cpm, q1):
    """Install the five recording wrappers once per SFM process. Returns the state."""
    st = ot1_state(cpm)
    if st is not None:
        return st
    st = {"events": [], "originals": dict((n, getattr(cpm, n)) for n in OT1_HOOKED), "op": None, "seq": 0,
          "written": [], "armed": False, "fired": 0, "installed_at": time.time()}
    orig = st["originals"]
    text = q1["q1_text"]
    plain = q1["q1_plain"]
    reraise = q1["q1_reraise"]

    def hooked_apply(identity, record, *args, **kwargs):
        prev = st["op"]
        try:
            st["op"] = {"identity": dict(identity), "record": json.loads(json.dumps(record)),
                        "context": kwargs.get("operation_context")}
            st["written"] = []
            ot1_record(st, "apply-begin", preset=text(record.get("name")), preset_kind=text(record.get("kind")),
                       identity=plain(dict(identity)),
                       instance=plain(cpm.prod_instance_token(kwargs.get("operation_context"))))
        except Exception:
            pass
        try:
            result = orig["prod_apply"](identity, record, *args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "apply-raised", error=repr(info[1]), error_type=type(info[1]).__name__)
            st["op"] = prev
            reraise(info)
        st["op"] = prev
        ot1_record(st, "apply-returned", result=plain(result))
        return result

    def hooked_write(item, *args, **kwargs):
        binding = (item or {}).get("binding")
        bone = text((item or {}).get("bone_name"))
        before = ot1_snap(cpm, q1, binding)
        try:
            result = orig["prod_bs_write_existing_scale"](item, *args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "scale-write-raised", bone=bone, error=repr(info[1]), before=before,
                       after=ot1_snap(cpm, q1, binding))
            reraise(info)
        after = ot1_snap(cpm, q1, binding)
        try:
            st["written"].append(binding)
        except Exception:
            pass
        ot1_record(st, "scale-write", bone=bone, desired_native=plain(item.get("desired_native")),
                   desired_physical=plain(item.get("desired_physical")),
                   static_output_mode=plain((binding or {}).get("static_output_mode")), before=before, after=after)
        if st["armed"] and bone == OT1_FAIL_BONE and st["fired"] == 0:
            st["armed"] = False
            st["fired"] += 1
            ot1_record(st, "injected-failure", bone=bone, text=OT1_FAIL_TEXT)
            raise RuntimeError(OT1_FAIL_TEXT)
        return result

    def hooked_refresh(head_time, label):
        try:
            result = orig["same_time_refresh"](head_time, label)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "refresh-raised", label=text(label), error=repr(info[1]))
            reraise(info)
        rows = []
        for binding in list(st["written"]):
            rows.append({"bone": text(((binding or {}).get("identity") or {}).get("bone_name")),
                         "after": ot1_snap(cpm, q1, binding)})
        ot1_record(st, "refresh-after", label=text(label), head_time=plain(head_time), scales=rows)
        return result

    def hooked_verify(record, snapshot):
        try:
            result = orig["prod_bs_index_verify_saved"](record, snapshot)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "deferred-verify-raised", error=repr(info[1]))
            reraise(info)
        try:
            fm = q1["q1_full_map"](cpm, record, snapshot)
            ot1_record(st, "deferred-verify", result=bool(result), record=text(record.get("name")), full_map=fm,
                       consistent=(fm.get("result") == bool(result)))
        except Exception as exc:
            ot1_record(st, "deferred-verify", result=bool(result), record=text(record.get("name")),
                       full_map={"error": repr(exc)}, consistent=None)
        return result

    def hooked_abort_verify(*args, **kwargs):
        try:
            result = orig["prod_verify_apply_abort_baseline"](*args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "abort-verify-raised", error=repr(info[1]))
            reraise(info)
        ot1_record(st, "abort-verify", result=plain(result))
        return result

    wrappers = {"prod_apply": hooked_apply, "prod_bs_write_existing_scale": hooked_write,
                "same_time_refresh": hooked_refresh, "prod_bs_index_verify_saved": hooked_verify,
                "prod_verify_apply_abort_baseline": hooked_abort_verify}
    for name, fn in wrappers.items():
        fn.ot1_original = orig[name]
        setattr(cpm, name, fn)
    setattr(cpm, OT1_STATE, st)
    return st


def ot1_uninstall(cpm):
    """Restore the five original functions and disarm. Returns True when every original is back in place."""
    st = ot1_state(cpm)
    if st is None:
        return True
    st["armed"] = False
    for name, fn in st["originals"].items():
        setattr(cpm, name, fn)
    ok = all(getattr(cpm, n) is st["originals"][n] for n in OT1_HOOKED)
    if ok:
        delattr(cpm, OT1_STATE)
    return ok


def ot1_enumerate(cpm, q1, binding):
    """Diagnostic: every reader and writer of the bound expression and every unreadable item, over the structure the
    candidate's prod_bs_expression_channels scans and with the same strict primitives, continuing past failures."""
    text, plain = q1["q1_text"], q1["q1_plain"]
    expression = binding["expression"]
    out = {"clips": 0, "channels": 0, "readers": [], "writers": [], "unreadable": []}

    def label(element):
        try:
            return text(element.GetName())
        except Exception:
            return None
    try:
        group = binding["shot"].FindTrackGroup("channelTrackGroup")
        track = group.FindTrack("animSetEditorChannels") if group is not None else None
    except Exception as exc:
        out["unreadable"].append({"what": "track", "error": repr(exc)})
        return out
    if track is None:
        out["unreadable"].append({"what": "track", "error": "unavailable"})
        return out
    try:
        children = cpm.prod_instance_strict_members(track, "children", "The shot's channels clips")
    except Exception as exc:
        out["unreadable"].append({"what": "track children", "error": repr(exc)})
        return out
    for index, clip in enumerate(children):
        try:
            kind = cpm.prod_instance_strict_text(clip, "GetTypeString", "A channels-clip type")
        except Exception as exc:
            out["unreadable"].append({"what": "clip type", "clip_index": index, "error": repr(exc)})
            continue
        if kind != u"DmeChannelsClip":
            continue
        clip_name = label(clip)
        try:
            channels = cpm.prod_instance_strict_members(clip, "channels", "A channels clip's channels")
        except Exception as exc:
            out["unreadable"].append({"what": "clip channels", "clip": clip_name, "clip_index": index,
                                      "error": repr(exc)})
            continue
        out["clips"] += 1
        for position, channel in enumerate(channels):
            out["channels"] += 1
            for attr_name, found, side in (("fromElement", out["readers"], "fromAttribute"),
                                           ("toElement", out["writers"], "toAttribute")):
                state, element = cpm.prod_flex_strict_read(channel, attr_name)
                if state == u"absent" or (state == u"present" and element is None):
                    continue
                if state != u"present":
                    out["unreadable"].append({"what": "endpoint", "clip": clip_name, "channel": label(channel),
                                              "position": position, "attribute": attr_name})
                    continue
                if cpm.same_dme(element, expression):
                    found.append({"clip": clip_name, "channel": plain(cpm.dme_id(channel)),
                                  "attribute": text(cpm.attr_value(channel, side))})
    return out


class _OT1Marker(object):
    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return self.label


OT1_ABSENT = _OT1Marker("<absent>")
OT1_UNREADABLE = _OT1Marker("<unreadable>")


def ot1_class_entries(vsmod):
    """The actual class-dictionary entries Astra's DC2 ruling names (OT1_ABSENT when the class has no own entry),
    compared later by object identity."""
    out = {}
    for cls_name, attr in OT1_CLASS_ENTRIES:
        key = "%s.%s" % (cls_name, attr)
        try:
            out[key] = getattr(vsmod, cls_name).__dict__.get(attr, OT1_ABSENT)
        except Exception:
            out[key] = OT1_UNREADABLE
    return out


def ot1_entries_plain(entries):
    return dict((k, "<absent>" if v is OT1_ABSENT else "<unreadable>" if v is OT1_UNREADABLE else
                 {"id": id(v), "repr": repr(v)[:160]}) for k, v in entries.items())


def ot1_entries_same(a, b):
    return (sorted(a) == sorted(b) and all(a[k] is b[k] for k in a) and
            not any(v is OT1_UNREADABLE for v in list(a.values()) + list(b.values())))


def ot1_direct_refs(cpm, q1, vsmod, binding):
    """Astra DC1/DC2: every direct DataModel reference to the bound expression, traversed with the IDataModel
    iterator primitives on vs.g_pDataModel (no vsUtils): FirstAttributeReferencingElement(handle), then
    GetAttributeFromIterator and NextAttributeReferencingElement until the token equals
    vs.DMATTRIBUTE_REFERENCE_ITERATOR_INVALID (explicit comparison, never truthiness). A repeated token, an unreadable
    attribute, owner or identity, an API exception or exceeding OT1_REF_LIMIT refuses; the enumeration is complete
    only after reaching the sentinel. Each reference's owner identity and attribute name are recorded and matched by
    live element identity against exactly three relationships: the selected animation set's `operators`, the
    admitted input channel's `toElement`, the admitted output channel's `fromElement`. The class entries in
    OT1_CLASS_ENTRIES and sys.modules' vsUtils membership are snapshotted before and after and must be identical."""
    text, plain = q1["q1_text"], q1["q1_plain"]
    expected = {"animset": binding.get("animset"), "input_channel": binding.get("input_channel"),
                "output": binding.get("output")}
    out = {"complete": False, "terminated_at_sentinel": False, "error": None, "references": [], "tokens": [],
           "repeated_token": False, "sentinel": None, "pass": False}
    entries_before = ot1_class_entries(vsmod)
    module_before = sys.modules.get("vsUtils", OT1_ABSENT)
    try:
        dm = vsmod.g_pDataModel
        sentinel = vsmod.DMATTRIBUTE_REFERENCE_ITERATOR_INVALID
        out["sentinel"] = repr(sentinel)
        handle = binding["expression"].GetHandle()
        token = dm.FirstAttributeReferencingElement(handle)
        seen = []
        while True:
            if token == sentinel:
                out["terminated_at_sentinel"] = True
                break
            if any(token == previous for previous in seen):
                out["repeated_token"] = True
                raise RuntimeError("repeated iterator token %r" % (token,))
            if len(seen) >= OT1_REF_LIMIT:
                raise RuntimeError("reference enumeration exceeded %d tokens" % OT1_REF_LIMIT)
            seen.append(token)
            out["tokens"].append(repr(token))
            row = {"role": None}
            attr = dm.GetAttributeFromIterator(token)
            owner = None
            if attr is None:
                row["unreadable"] = "attribute: none from iterator"
            else:
                try:
                    owner = attr.GetOwner()
                    if owner is None:
                        raise RuntimeError("no owner")
                    owner_handle = owner.GetHandle()
                    if isinstance(owner_handle, bool):
                        raise RuntimeError("boolean handle")
                    row.update(owner=plain(cpm.dme_id(owner)), owner_type=text(owner.GetTypeString()),
                               owner_name=text(owner.GetName()), owner_handle=int(owner_handle))
                except Exception as exc:
                    owner = None
                    row["unreadable"] = "owner: %r" % (exc,)
                try:
                    name = attr.GetName()
                    if not name:
                        raise RuntimeError("empty attribute name")
                    row["attribute"] = text(name)
                except Exception as exc:
                    row["unreadable"] = "attribute: %r" % (exc,)
            if owner is not None and "unreadable" not in row:
                for role, attr_name in OT1_REF_EXPECTED:
                    if row["attribute"] == attr_name and expected[role] is not None and \
                            cpm.same_dme(owner, expected[role]):
                        row["role"] = role
            out["references"].append(row)
            token = dm.NextAttributeReferencingElement(token)
        out["complete"] = out["terminated_at_sentinel"]
    except Exception as exc:
        out["error"] = repr(exc)
    entries_after = ot1_class_entries(vsmod)
    module_after = sys.modules.get("vsUtils", OT1_ABSENT)
    out["class_entries"] = {"before": ot1_entries_plain(entries_before), "after": ot1_entries_plain(entries_after),
                            "unchanged": ot1_entries_same(entries_before, entries_after)}
    out["vsutils_module"] = {"before": module_before is not OT1_ABSENT, "after": module_after is not OT1_ABSENT,
                             "unchanged": module_before is module_after}
    refs = out["references"]
    out["matched"] = dict((role, sum(1 for r in refs if r["role"] == role)) for role, _ in OT1_REF_EXPECTED)
    out["unexpected"] = [r for r in refs if r["role"] is None and "unreadable" not in r]
    out["unreadable"] = [r for r in refs if "unreadable" in r]
    out["pass"] = bool(out["complete"] and out["terminated_at_sentinel"] and out["error"] is None and
                       not out["repeated_token"] and len(refs) == len(OT1_REF_EXPECTED) and
                       all(n == 1 for n in out["matched"].values()) and not out["unexpected"] and
                       not out["unreadable"] and all(expected[r] is not None for r in expected) and
                       out["class_entries"]["unchanged"] and out["vsutils_module"]["unchanged"])
    return out


def ot1_preflight_bone(cpm, q1, snapshot, row, vsmod=None):
    text, plain = q1["q1_text"], q1["q1_plain"]
    out = {"would_pass": False, "error": None}
    if row is None:
        out["error"] = "bone not found in the selected instance"
        return out
    out["classification"] = text(row.get("classification"))
    try:
        binding = cpm.prod_bs_index_binding(snapshot, row)
    except Exception as exc:
        out["error"] = "binding: %r" % (exc,)
        return out
    expression, output = binding["expression"], binding["output"]
    input_channel, transform = binding["input_channel"], binding["transform"]
    out["static_output_mode"] = plain(binding.get("static_output_mode"))
    out["identities"] = dict((k, plain(cpm.dme_id(x))) for k, x in (
        ("expression", expression), ("output", output), ("input_channel", input_channel), ("transform", transform),
        ("control", binding.get("control")), ("animset", binding.get("animset"))))
    out["expression_type"] = text(cpm.typ(expression))
    out["expr"] = text(cpm.attr_value(expression, "expr") or u"")
    out["expression_ok"] = (out["expression_type"] == u"DmeExpressionOperator" and
                            out["expr"].replace(u" ", u"").lower() == u"lerp(value,lo,hi)")
    out["endpoints_ok"] = bool(
        cpm.same_dme(cpm.attr_value(output, "fromElement"), expression)
        and text(cpm.attr_value(output, "fromAttribute") or u"") == u"result"
        and cpm.same_dme(cpm.attr_value(output, "toElement"), transform)
        and text(cpm.attr_value(output, "toAttribute") or u"") == u"scale"
        and cpm.same_dme(cpm.attr_value(input_channel, "toElement"), expression)
        and text(cpm.attr_value(input_channel, "toAttribute") or u"") == u"value")
    try:
        readers, writers = cpm.prod_bs_expression_channels(binding)
        out["candidate_scan"] = {"error": None, "readers": len(readers), "writers": len(writers),
                                 "reader_ids": [plain(cpm.dme_id(x)) for x in readers],
                                 "writer_ids": [plain(cpm.dme_id(x)) for x in writers]}
        out["unique"] = (len(readers) == 1 and bool(cpm.same_dme(readers[0], output)) and len(writers) == 1 and
                         bool(cpm.same_dme(writers[0], input_channel)))
    except Exception as exc:
        out["candidate_scan"] = {"error": repr(exc)}
        out["unique"] = False
    out["enumeration"] = ot1_enumerate(cpm, q1, binding)
    lists = []
    try:
        for animset in q1["q1_seq"](q1["q1_attr"](binding["shot"], "animationSets")):
            if any(cpm.same_dme(x, expression) for x in q1["q1_seq"](q1["q1_attr"](animset, "operators"))):
                lists.append(text(animset.GetName()))
        out["operator_lists"] = lists
    except Exception as exc:
        out["operator_lists"] = {"error": repr(exc)}
    out["direct_refs"] = (ot1_direct_refs(cpm, q1, vsmod, binding) if vsmod is not None else
                          {"complete": False, "error": "vs unavailable", "references": [], "pass": False})
    out["would_pass"] = bool(out["unique"] and out["endpoints_ok"] and out["expression_ok"] and
                             out["static_output_mode"] == 3 and not out["enumeration"]["unreadable"] and
                             out["direct_refs"]["pass"])
    return out


def ot1_preflight(cpm, q1, identity, token, vsmod=None):
    """The read-only BASE graph scan of the two existing scales (see the docstring, part 4)."""
    out = {"bones": {}, "error": None, "would_pass": False}
    try:
        out["instance"] = q1["q1_plain"](cpm.prod_instance_token(token))
        snapshot = cpm.prod_bs_index_snapshot(identity, **cpm.prod_instance_kw(token))
    except Exception as exc:
        out["error"] = "snapshot: %r" % (exc,)
        return out
    try:
        rows = dict((q1["q1_text"](r.get("bone_name")), r) for r in snapshot["bone_index"].values())
        for bone in OT1_PREFLIGHT_BONES:
            try:
                out["bones"][bone] = ot1_preflight_bone(cpm, q1, snapshot, rows.get(bone), vsmod)
            except Exception as exc:
                out["bones"][bone] = {"would_pass": False, "error": repr(exc)}
    finally:
        if isinstance(snapshot, dict):
            snapshot.clear()
    out["would_pass"] = out["error"] is None and all(out["bones"].get(b, {}).get("would_pass") is True
                                                     for b in OT1_PREFLIGHT_BONES)
    return out


def ot1_guarded_preflight(cpm, q1, identity, token, probe, vsmod=None):
    """The preflight between two reads of the scene state probe() returns (Undo state, playhead)."""
    before = probe()
    result = ot1_preflight(cpm, q1, identity, token, vsmod)
    after = probe()
    result["side_effects"] = {"before": before, "after": after, "unchanged": before == after and "error" not in before}
    return result


def ot1_preflight_ok(pre):
    return bool(pre and pre.get("would_pass") is True and (pre.get("side_effects") or {}).get("unchanged") is True)


def ot1_arm(st, pre):
    """Arm the controlled failure only after a passing, unchanged ARM preflight (Astra DC1 ruling)."""
    if st["fired"] != 0 or st["armed"]:
        raise RuntimeError("The controlled failure was already armed or fired; nothing written.")
    if not ot1_preflight_ok(pre):
        return {"armed": False, "fired": 0, "refused": "ARM preflight failed: not armed"}
    st["armed"] = True
    return {"armed": True, "fired": 0, "bone": OT1_FAIL_BONE}


def ot1_events_payload(st):
    if st is None:
        return []
    return json.loads(json.dumps(list(st["events"]), default=repr))


def ot1_capture(g):
    root, step, repo = g.get("OT1_DIR"), g.get("OT1_STEP"), g.get("OT1_REPO")
    if not root or not repo or step not in OT1_STEPS:
        raise RuntimeError("Set OT1_DIR, OT1_REPO and OT1_STEP (one of %s) first; see the docstring."
                           % ", ".join(OT1_STEPS))
    path = os.path.join(root, "observations", "OT1-%s.json" % step)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each step is captured once." % path)
    q1 = ot1_q1(repo)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    if cpm is None:
        raise RuntimeError("CPM is not loaded: open Character Preset Manager first.")
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, cpm.PROD_APP_ATTR, None) if app is not None else None
    if win is None:
        raise RuntimeError("The CPM window is not open.")
    if getattr(win, "busy", False) or getattr(win, "operation", None) is not None:
        raise RuntimeError("CPM is busy; wait for the current operation to finish.")
    if step != "BASE" and ot1_state(cpm) is None:
        raise RuntimeError("The hooks are not installed in this SFM process: capture BASE first.")
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    text, plain = q1["q1_text"], q1["q1_plain"]
    data = {"format": "F01-OT1-capture-v1", "step": step, "pid": os.getpid(), "time": time.time(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None), "errors": {},
            "q1_observer_sha256": Q1_OBSERVER_SHA256}

    def attempt(key, fn):
        try:
            data[key] = fn()
        except Exception as exc:
            data[key] = None
            data["errors"][key] = repr(exc)

    def undo():
        out = {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()), "undo_desc": text(dm.GetUndoDesc()),
               "redo_desc": text(dm.GetRedoDesc())}
        try:
            out["count"] = int(dm.GetUndoItemCount())
        except Exception:
            out["count"] = None
        return out
    attempt("session", lambda: {
        "document": text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())),
        "shot": text(sfmApp.GetShotAtCurrentTime().GetName()),
        "head_seconds": float(sfmApp.GetHeadTimeInSeconds()),
        "timeline_mode": text(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode())),
        "undo": undo()})
    identity = win.current() if hasattr(win, "current") else None
    token = getattr(win, "selection_token", None)
    attempt("character", lambda: dict((text(k), plain(x)) for k, x in (identity or {}).items()))
    attempt("instance", lambda: plain(cpm.prod_instance_token(token)))
    attempt("animation_sets", lambda: [q1["q1_raw_set"](a) for a in q1["q1_seq"](q1["q1_attr"](
        sfmApp.GetShotAtCurrentTime(), "animationSets"))])
    record = None
    for item in list(getattr(win, "body_items", None) or []):
        rec = (item or {}).get("record") or {}
        if text(rec.get("name")) == OT1_RECORD:
            if record is not None:
                data["errors"]["record"] = "more than one Body record"
            record = rec
    data["record"] = None if record is None else {"preset_id": text(record.get("preset_id")),
                                                  "bone_scales": len(record.get("bone_scales") or [])}
    try:
        data["settled_full_map"] = (q1["q1_snapshot_map"](cpm, identity, token, record) if record is not None
                                    else {"error": "no Body record"})
    except Exception as exc:
        data["settled_full_map"] = {"error": repr(exc)}
    def probe():
        try:
            return {"undo": undo(), "head_seconds": float(sfmApp.GetHeadTimeInSeconds())}
        except Exception as exc:
            return {"error": repr(exc)}
    if step in ("BASE", "ARM"):
        data["environment"] = {"vsutils_in_sys_modules_at_capture": "vsUtils" in sys.modules}
        data["preflight"] = ot1_guarded_preflight(cpm, q1, identity, token, probe, vs)
    if step == "BASE":
        st = ot1_install(cpm, q1)
        data["hooks_installed"] = sorted(n for n in OT1_HOOKED if getattr(getattr(cpm, n), "ot1_original", None)
                                         is st["originals"][n])
    st = ot1_state(cpm)
    data["events"] = ot1_events_payload(st)
    if st is not None:
        del st["events"][:]
        data["injector"] = {"armed": st["armed"], "fired": st["fired"]}
    if step == "ARM":
        data["injector"] = ot1_arm(st, data["preflight"])
    if step == "ABORT":
        data["hooks_removed"] = ot1_uninstall(cpm)
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    fm = data["settled_full_map"] or {}
    line = "OT1 %s: %d events | settled map Body %s | undo %r redo %r | injector %s | errors %s | written" % (
        step, len(data["events"]), {True: "PASS", False: "FAIL"}.get(fm.get("result"), "UNREADABLE"),
        ((data.get("session") or {}).get("undo") or {}).get("undo_desc"),
        ((data.get("session") or {}).get("undo") or {}).get("redo_desc"),
        data.get("injector"), sorted(data["errors"]) or "none")
    pre = data.get("preflight")
    if pre is not None:
        ok = pre.get("would_pass") and pre["side_effects"]["unchanged"]
        line += " | preflight %s%s" % ("PASS" if ok else "FAIL",
                                       "" if pre["side_effects"]["unchanged"] else " (state changed)")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


if __name__ != "ot1_observer_under_test":
    ot1_capture(globals())
