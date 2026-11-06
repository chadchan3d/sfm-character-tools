# -*- coding: ascii -*-
"""F-01 full-body S0 survey observer: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    S0_DIR = r"E:\\SFM_U0B_Scratch\\f01-full-body-s0"; S0_LABEL = "S0-01"
    execfile(r"E:\\SFM-F01-Pose-Library\\real_sfm_qualification\\f01_full_body_s0\\observer\\F01_S0_Survey.py")

Writes <S0_DIR>\\observations\\<S0_LABEL>.json (exclusive create; an existing file is never replaced) and prints one
SUMMARY line. Optional: S0_ANIMSET (default "Krystal"), the animation set to survey in the shot at the playhead.

It records, with plain native reads only and independently of CPM's code: the session state (document, playhead,
timeline mode, Undo/Redo); the shot-to-channel time mapping; every scene element of the shot with its parents and,
for every DAG, its local and world transform; every model bone with its parent; the rig registration and every rig
handle; every control of the animation set with all its attributes; every channel of the set's channels clip with its
binding, log and layer structure, key summary, GetCurrentTime(), its value at that clock and at the mapped tick, and
its destination's current value; every operator of the set and the shot with its slaves, targets, weights, solver
settings and all other attributes; and a document-wide writer index (every channel's destination and every operator's
slave). A SHA-256 digest of every authored key of every channel in the document, and the session state, are taken
before and after; they prove the run changed nothing.

It never writes to the scene: no key, value, selection or playhead change, no Undo transaction, no rig or constraint
operation, no save. Its only file write is the observation file.
"""
import hashlib
import json
import os
import re
import sys
import traceback

import sfmApp
import vs

try:
    long, unicode  # noqa: B018 (Python 2.7, SFM)
except NameError:  # the offline tests (Python 3)
    long, unicode = int, str

FORMAT = "F01-S0-survey-v1"
MAX_NODES = 20000
MAX_ARRAY = 65536
MAX_DOC_NODES = 200000
MAX_ATTRS = 256
MAX_LAYERS = 16
FULL_KEYS = 64
DISTINCT_CAP = 64
SLAVE_ATTRS = ("slave", "startJoint", "midJoint", "endJoint")
SOLVER_FIELDS = ("startOffset", "midOffset", "poleVector", "mode")
CONTROL_CHANNEL_ATTRS = ("positionChannel", "orientationChannel", "channel", "leftvaluechannel",
                         "rightvaluechannel")
BONE_NAME_RE = re.compile(r"^bone (\d+) \((.+)\)$")


class Unreadable(Exception):
    pass


# --- strict native reads (the Stage D patterns: prod_pose_attr, prod_pose_field, prod_pose_plain) ---------------

def text(v):
    if v is None:
        return None
    if isinstance(v, bytes) and not isinstance(v, unicode):
        return v.decode("utf-8", "replace")
    return unicode(v)


def nat(name):
    if sys.version_info[0] == 2 and isinstance(name, unicode):
        return name.encode("utf-8")
    return name


def has(obj, name):
    return bool(obj.HasAttribute(nat(name)))


def attr(obj, name):
    if obj is None:
        raise Unreadable("no object for %s" % name)
    a = obj.GetAttribute(nat(name))
    if a is None:
        raise Unreadable("missing attribute %s" % name)
    for method in ("GetValue", "GetValueUntyped"):
        try:
            return getattr(a, method)()
        except Exception:
            pass
    raise Unreadable("%s unreadable" % name)


def opt(obj, name):
    if obj is None or not has(obj, name):
        return None
    return attr(obj, name)


def seq(value, cap=MAX_ARRAY):
    n = len(value)
    if n < 0 or n > cap:
        raise Unreadable("collection exceeds its bound (%d)" % n)
    return [value[i] for i in range(n)]


def h(obj):
    return int(obj.GetHandle())


def typ(obj):
    return text(obj.GetTypeString())


def ident(obj):
    if obj is None:
        return None
    return {"handle": h(obj), "type": typ(obj), "name": text(obj.GetName())}


def ticks(t):
    v = t.GetTenthsOfMS()
    if isinstance(v, bool):
        raise Unreadable("boolean time")
    return int(v)


def num(v):
    if isinstance(v, bool):
        raise Unreadable("boolean where a number is required")
    v = float(v)
    if v != v or v in (float("inf"), float("-inf")):
        raise Unreadable("non-finite number")
    return v


def comps(value, n):
    if n == 4 and all(hasattr(value, k) for k in ("x", "y", "z", "w")):
        return [num(getattr(value, k)) for k in ("x", "y", "z", "w")]
    if n == 3 and all(hasattr(value, k) for k in ("x", "y", "z")):
        return [num(getattr(value, k)) for k in ("x", "y", "z")]
    return [num(value[i]) for i in range(n)]


def plain(value, depth=0):
    """A lossless JSON form of a native value; element references become identities; unknown types are
    unreadable (recorded, never guessed)."""
    if depth > 4:
        raise Unreadable("value nesting exceeds its bound")
    if value is None or isinstance(value, (bool, unicode)):
        return value
    if isinstance(value, (int, long)):
        return int(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, float):
        return num(value)
    if hasattr(value, "GetHandle") and hasattr(value, "GetTypeString"):
        if typ(value).endswith("_array"):
            return [plain(x, depth + 1) for x in seq(value)]
        return ident(value)
    if hasattr(value, "GetTenthsOfMS"):
        return {"ticks": ticks(value)}
    name = type(value).__name__.lower()
    if "quaternion" in name or "vector4" in name:
        return comps(value, 4)
    if "vector2" in name:
        return comps(value, 2)
    if name in ("vector", "vectoraligned", "qangle"):
        return comps(value, 3)
    if name == "color":
        return {"color": [int(value.r()), int(value.g()), int(value.b()), int(value.a())]}
    if isinstance(value, (list, tuple)) or hasattr(value, "__len__"):
        return [plain(x, depth + 1) for x in seq(value)]
    raise Unreadable("no lossless form for %s" % type(value).__name__)


def field(obj, name):
    """{status: ABSENT | READ (value) | UNREADABLE (error)}: absence is distinguished from an unreadable read."""
    try:
        if not has(obj, name):
            return {"status": "ABSENT"}
    except Exception as exc:
        return {"status": "UNREADABLE", "error": repr(exc)}
    try:
        return {"status": "READ", "value": plain(attr(obj, name))}
    except Exception as exc:
        return {"status": "UNREADABLE", "error": repr(exc)}


def attribute_names(obj):
    names = []
    a = obj.FirstAttribute()
    while a is not None:
        name = text(a.GetName())
        if name in names or len(names) >= MAX_ATTRS:
            raise Unreadable("attribute walk repeated or exceeded its bound")
        names.append(name)
        a = a.NextAttribute()
    return names


def dump(obj, skip=()):
    """Every attribute of one element, each as a field record."""
    try:
        names = attribute_names(obj)
    except Exception as exc:
        return {"__walk__": {"status": "UNREADABLE", "error": repr(exc)}}
    return dict((n, field(obj, n)) for n in names if n not in skip)


def transform_state(dag):
    row = {}
    t = opt(dag, "transform")
    if t is not None:
        row["transform"] = ident(t)
        row["local_position"] = comps(attr(t, "position"), 3)
        row["local_orientation"] = comps(attr(t, "orientation"), 4)
        row["scale"] = field(t, "scale")
    if hasattr(dag, "GetAbsPosition"):
        row["world_position"] = comps(dag.GetAbsPosition(), 3)
        row["world_orientation"] = comps(dag.GetAbsOrientation(), 4)
    return row


# --- session state and the read-only proof ----------------------------------------------------------------------

def session_state():
    dm = vs.g_pDataModel
    head = float(sfmApp.GetHeadTimeInSeconds())
    out = {"head_seconds": head, "head_ticks": ticks(vs.DmeTime_t(head))}
    try:
        m = sfmApp.GetTimelineMode()
        out["timeline_mode"] = {"value": repr(m), "name": text(sfmApp.GetNameForTimelineMode(m))}
    except Exception as exc:
        out["timeline_mode"] = {"error": repr(exc)}
    out["undo"] = {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                   "undo_desc": text(dm.GetUndoDesc()), "redo_desc": text(dm.GetRedoDesc())}
    shot = sfmApp.GetShotAtCurrentTime()
    out["current_shot"] = text(shot.GetName()) if shot is not None else None
    return out


def film_clips(movie):
    out = []
    for track in seq(attr(attr(movie, "subClipTrackGroup"), "tracks")):
        for shot in seq(attr(track, "children")):
            if typ(shot) == "DmeFilmClip":
                out.append(shot)
    return out


def channels_clips(shot):
    out = []
    for g in seq(attr(shot, "trackGroups")):
        for t in seq(attr(g, "tracks")):
            for clip in seq(attr(t, "children")):
                if typ(clip) == "DmeChannelsClip":
                    out.append(clip)
    return out


def key_value(v):
    return plain(v)


def document_digest(problems):
    """SHA-256 over every authored key (all layers) of every channel of every channels clip in every shot, in
    document order, with each channel's name and handle. An unreadable channel is digested as such and reported."""
    digest, count, unreadable = hashlib.sha256(), 0, []
    for shot in film_clips(sfmApp.GetMovie()):
        for clip in channels_clips(shot):
            for ch in seq(attr(clip, "channels")):
                count += 1
                digest.update(("C%d:%s;" % (h(ch), text(ch.GetName()))).encode("utf-8"))
                try:
                    log = ch.GetLog()
                    for i in range(int(log.GetNumLayers())):
                        layer = log.GetLayer(i)
                        digest.update(("L%d:" % i).encode("ascii"))
                        for k in range(int(layer.GetKeyCount())):
                            digest.update(json.dumps([ticks(layer.GetKeyTime(k)),
                                                      key_value(layer.GetKeyValue(k))]).encode("utf-8"))
                except Exception as exc:
                    digest.update(b"unreadable")
                    unreadable.append("%s/%s: %r" % (text(shot.GetName()), text(ch.GetName()), exc))
    if unreadable:
        problems.append("document digest: %d unreadable channels (first: %s)" % (len(unreadable), unreadable[0]))
    return {"sha256": digest.hexdigest(), "channels": count, "unreadable": len(unreadable)}


# --- the survey -----------------------------------------------------------------------------------------------

def walk(root):
    nodes, parents, pending = {}, {}, [(root, None)]
    while pending:
        obj, parent = pending.pop()
        k = h(obj)
        parents.setdefault(k, [])
        if parent is not None and parent not in parents[k]:
            parents[k].append(parent)
        if k in nodes:
            continue
        if len(nodes) >= MAX_NODES:
            raise Unreadable("scene hierarchy exceeds its bound")
        nodes[k] = obj
        children = opt(obj, "children")
        if children is not None:
            for child in reversed(seq(children)):
                if child is not None:
                    pending.append((child, k))
    return nodes, parents


def instance_clip(shot, controls, problems):
    """The animation set's own channels clip, by channel membership (the M-06 rule: never by name alone)."""
    wanted = set()
    for c in controls:
        for name in CONTROL_CHANNEL_ATTRS:
            ch = opt(c, name)
            if ch is not None:
                wanted.add(h(ch))
    group = shot.FindTrackGroup("channelTrackGroup")
    track = group.FindTrack("animSetEditorChannels") if group is not None else None
    if track is None:
        problems.append("the shot has no channelTrackGroup/animSetEditorChannels track")
        return None, []
    candidates = []
    for clip in seq(attr(track, "children")):
        if typ(clip) != "DmeChannelsClip":
            continue
        members = set(h(ch) for ch in seq(attr(clip, "channels")))
        shared = len(members & wanted)
        if shared:
            candidates.append((clip, shared, len(wanted - members)))
    report = [{"clip": ident(c), "control_channels_held": n, "control_channels_missing": m}
              for c, n, m in candidates]
    owners = [c for c, n, m in candidates if m == 0]
    if len(owners) != 1 or len(candidates) != 1:
        problems.append("expected one channels clip holding every control channel; candidates %r" % (report,))
        return (owners[0] if len(owners) == 1 else None), report
    return owners[0], report


def layer_summary(layer, t_chan):
    count = int(layer.GetKeyCount())
    row = {"id": ident(layer), "type": typ(layer), "key_count": count, "key_at_mapped": None}
    digest, distinct, lo, hi, keys = hashlib.sha256(), [], None, None, []
    for k in range(count):
        t = ticks(layer.GetKeyTime(k))
        v = key_value(layer.GetKeyValue(k))
        digest.update(json.dumps([t, v]).encode("utf-8"))
        if t == t_chan:
            row["key_at_mapped"] = k
        if k == 0:
            row["first_ticks"] = t
        row["last_ticks"] = t
        if count <= FULL_KEYS:
            keys.append([t, v])
        flat = v if isinstance(v, list) else [v]
        if all(isinstance(x, float) for x in flat):
            rounded = [round(x, 6) for x in flat]
            if rounded not in distinct and len(distinct) < DISTINCT_CAP:
                distinct.append(rounded)
            lo = list(flat) if lo is None else [min(a, b) for a, b in zip(lo, flat)]
            hi = list(flat) if hi is None else [max(a, b) for a, b in zip(hi, flat)]
    row["keys_sha256"] = digest.hexdigest()
    row["distinct_values"] = len(distinct) if len(distinct) < DISTINCT_CAP else "%d+" % DISTINCT_CAP
    row["range"] = [lo, hi] if lo is not None else None
    row["keys"] = keys if count <= FULL_KEYS else None
    return row


def channel_record(ch, t_chan):
    row = {"id": ident(ch)}
    row["binding"] = dict((n, field(ch, n)) for n in ("fromElement", "fromAttribute", "fromIndex", "toElement",
                                                         "toAttribute", "toIndex", "mode"))
    try:
        row["current_ticks"] = ticks(ch.GetCurrentTime())
    except Exception as exc:
        row["current_ticks"] = None
        row["current_error"] = repr(exc)
    try:
        log = ch.GetLog()
    except Exception as exc:
        row["log"] = None
        row["log_error"] = repr(exc)
        return row
    row["log"] = ident(log)
    row["layers"] = []
    if log is None:
        return row
    row["log_fields"] = dict((n, field(log, n)) for n in ("usedefaultvalue", "defaultvalue", "curveinfo",
                                                          "useDefaultValue", "defaultValue", "curveInfo"))
    row["log_attributes"] = attribute_names(log)
    n = int(log.GetNumLayers())
    if n < 0 or n > MAX_LAYERS:
        raise Unreadable("layer count exceeds its bound")
    for i in range(n):
        row["layers"].append(layer_summary(log.GetLayer(i), t_chan))
    for key, when in (("value_at_clock", "clock"), ("value_at_mapped", "mapped")):
        try:
            t = ch.GetCurrentTime() if when == "clock" else vs.DmeTime_t(int(t_chan))
            if when == "mapped" and ticks(t) != int(t_chan):
                raise Unreadable("the mapped time could not be constructed exactly")
            row[key] = plain(log.GetValue(t))
        except Exception as exc:
            row[key] = None
            row[key + "_error"] = repr(exc)
    try:
        to, to_attr = opt(ch, "toElement"), opt(ch, "toAttribute")
        row["destination_value"] = field(to, text(to_attr)) if to is not None and to_attr else {"status": "ABSENT"}
    except Exception as exc:
        row["destination_value"] = {"status": "UNREADABLE", "error": repr(exc)}
    return row


def operator_record(op, owners):
    row = {"id": ident(op), "owners": owners, "slaves": {}, "targets": [], "solver": {}}
    for slot in SLAVE_ATTRS:
        if has(op, slot):
            slave = attr(op, slot)
            row["slaves"][slot] = {"slave": ident(slave),
                                   "target": ident(opt(slave, "target")) if slave is not None else None,
                                   "attributes": dump(slave) if slave is not None else None}
    if has(op, "pvTarget"):
        row["pvTarget"] = ident(attr(op, "pvTarget"))
    if has(op, "targets"):
        for t in seq(attr(op, "targets")):
            row["targets"].append({"id": ident(t), "target": ident(opt(t, "target")),
                                   "targetWeight": field(t, "targetWeight"), "oOffset": field(t, "oOffset"),
                                   "vecOffset": field(t, "vecOffset"), "attributes": dump(t)})
    for name in SOLVER_FIELDS:
        if has(op, name):
            row["solver"][name] = field(op, name)
    row["attributes"] = dump(op, skip=SLAVE_ATTRS + ("targets",))
    return row


def writer_index(problems):
    """Document-wide, binding metadata only: every channel's destination and every operator's slaves."""
    seen, stack, channels, operators, count = set(), [sfmApp.GetMovie()], {}, {}, 0
    while stack:
        el = stack.pop()
        if el is None:
            continue
        k = h(el)
        if k in seen:
            continue
        seen.add(k)
        count += 1
        if count > MAX_DOC_NODES:
            raise Unreadable("writer discovery exceeds its bound")
        kind = typ(el)
        if kind == "DmeChannel":
            channels[k] = el
        elif kind == "DmeFilmClip":
            sub = opt(el, "subClipTrackGroup")
            if sub is not None:
                stack.append(sub)
            for name in ("trackGroups",):
                v = opt(el, name)
                if v is not None:
                    stack.extend(seq(v))
            v = opt(el, "operators")
            if v is not None:
                for op in seq(v):
                    operators[h(op)] = op
            v = opt(el, "animationSets")
            if v is not None:
                for a in seq(v):
                    for op in seq(opt(a, "operators") or []):
                        operators[h(op)] = op
        elif kind == "DmeTrackGroup":
            stack.extend(seq(attr(el, "tracks")))
        elif kind == "DmeTrack":
            stack.extend(seq(attr(el, "children")))
        elif kind == "DmeChannelsClip":
            stack.extend(seq(attr(el, "channels")))
    destinations, slaves, operator_types = {}, {}, {}
    for k, op in operators.items():
        kind = typ(op)
        if kind == "DmeChannel":
            channels[k] = op
            continue
        operator_types[kind] = operator_types.get(kind, 0) + 1
        for slot in SLAVE_ATTRS:
            try:
                slave = opt(op, slot)
                target = opt(slave, "target") if slave is not None else None
            except Exception as exc:
                problems.append("operator %d %s unreadable: %r" % (k, slot, exc))
                continue
            if target is not None:
                slaves.setdefault(str(h(target)), []).append({"operator": k, "type": kind, "slot": slot})
    for k, ch in channels.items():
        try:
            to = opt(ch, "toElement")
            if to is None:
                continue
            frm = opt(ch, "fromElement")
            key = "%d:%s" % (h(to), text(opt(ch, "toAttribute")))
            destinations.setdefault(key, []).append({"channel": k, "name": text(ch.GetName()),
                                                     "from": ident(frm), "fromAttribute": text(opt(ch,
                                                                                                   "fromAttribute"))})
        except Exception as exc:
            problems.append("channel %d binding unreadable: %r" % (k, exc))
    return {"channels": len(channels), "operators": len(operators), "operator_types": operator_types,
            "destinations": destinations, "slave_targets": slaves}


def survey(out):
    problems = out["problems"]
    name = globals().get("S0_ANIMSET") or "Krystal"
    out["animation_set_name"] = name
    head = float(sfmApp.GetHeadTimeInSeconds())
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        problems.append("no shot at the playhead")
        return
    out["shot"] = {"id": ident(shot), "start_ticks": ticks(shot.GetStartTime()), "end_ticks": ticks(shot.GetEndTime())}
    out["shots"] = [{"name": text(s.GetName()), "start_ticks": ticks(s.GetStartTime()),
                     "end_ticks": ticks(s.GetEndTime()),
                     "animation_sets": [ident(a) for a in seq(attr(s, "animationSets"))]}
                    for s in film_clips(sfmApp.GetMovie())]
    sets = [a for a in seq(attr(shot, "animationSets")) if text(a.GetName()) == name]
    if len(sets) != 1:
        problems.append("expected exactly one animation set %r in the current shot, found %d" % (name, len(sets)))
        return
    animset = sets[0]
    out["animation_set"] = {"id": ident(animset), "element_id": text(str(animset.GetId())),
                            "attribute_names": attribute_names(animset)}
    controls = seq(attr(animset, "controls"))
    clip, candidates = instance_clip(shot, controls, problems)
    out["channels_clip"] = {"clip": ident(clip), "candidates": candidates}
    t_doc = vs.DmeTime_t(head)
    t_shot = shot.ToChildMediaTime(t_doc, False)
    out["time"] = {"t_doc": ticks(t_doc), "t_shot": ticks(t_shot)}
    t_chan = None
    if clip is not None:
        t_chan = ticks(clip.ToChildMediaTime(t_shot, False))
        out["time"]["t_chan"] = t_chan
    gm = attr(animset, "gameModel")
    out["model"] = {"id": ident(gm), "modelName": field(gm, "modelName"), "attribute_names": attribute_names(gm),
                    "state": transform_state(gm)}
    nodes, parents = walk(attr(shot, "scene"))
    if h(gm) not in nodes:
        problems.append("the model is not in the shot's scene")
    out["scene"] = {}
    for k in sorted(nodes):
        obj = nodes[k]
        row = {"type": typ(obj), "name": text(obj.GetName()), "parents": sorted(parents.get(k, []))}
        if has(obj, "transform"):
            try:
                row.update(transform_state(obj))
            except Exception as exc:
                row["transform_error"] = repr(exc)
        out["scene"][str(k)] = row
    by_transform = {}
    for k, obj in nodes.items():
        t = opt(obj, "transform") if has(obj, "transform") else None
        if t is not None:
            by_transform.setdefault(h(t), []).append(k)
    out["bones"] = {}
    bone_dags = {}
    for t in seq(attr(gm, "bones")):
        m = BONE_NAME_RE.match(text(t.GetName()) or "")
        bname = m.group(2) if m else text(t.GetName())
        dags = by_transform.get(h(t), [])
        if m is None:
            problems.append("unrecognised bone transform name %r" % text(t.GetName()))
        if len(dags) != 1:
            problems.append("bone %s has %d scene elements" % (bname, len(dags)))
        if bname in out["bones"]:
            problems.append("bone %s is duplicated" % bname)
        row = {"index": int(m.group(1)) if m else None, "transform": ident(t), "dag": dags[0] if len(dags) == 1
               else None}
        if len(dags) == 1:
            bone_dags[dags[0]] = bname
        out["bones"][bname] = row
    for bname, row in out["bones"].items():
        if row["dag"] is None:
            continue
        ps = parents.get(row["dag"], [])
        row["parent_dags"] = ps
        row["parent_bone"] = bone_dags.get(ps[0]) if len(ps) == 1 else None
        row.update(transform_state(nodes[row["dag"]]))
    out["rig"] = {"registrations": [], "handles": {}}
    regs = []
    for k in sorted(nodes):
        obj = nodes[k]
        if typ(obj) != "DmeRig":
            continue
        for reg in seq(attr(obj, "animSetList")):
            linked = opt(reg, "animationSet")
            if linked is not None and h(linked) == h(animset):
                regs.append((obj, reg))
    for rig, reg in regs:
        elements = seq(opt(reg, "elementList") or [])
        out["rig"]["registrations"].append({"rig": ident(rig), "registration": ident(reg),
                                            "attributes": dump(reg, skip=("elementList",)),
                                            "elements": [ident(e) for e in elements]})
        for e in elements:
            if typ(e) == "DmeRigHandle":
                hname = text(e.GetName())
                if hname in out["rig"]["handles"]:
                    problems.append("rig handle %s is duplicated" % hname)
                row = {"id": ident(e), "parents": parents.get(h(e), []), "in_scene": h(e) in nodes}
                row.update(transform_state(e))
                out["rig"]["handles"][hname] = row
    if len(regs) != 1:
        problems.append("expected one rig registration for the animation set, found %d" % len(regs))
    out["controls"] = [{"id": ident(c), "attributes": dump(c)} for c in controls]
    out["channels"] = []
    if clip is not None:
        for ch in seq(attr(clip, "channels")):
            try:
                out["channels"].append(channel_record(ch, t_chan))
            except Exception as exc:
                out["channels"].append({"id": ident(ch), "error": repr(exc)})
                problems.append("channel %s unreadable: %r" % (text(ch.GetName()), exc))
    out["operators"] = []
    owners = {}
    for owner, holder in (("animation_set", animset), ("shot", shot)):
        for op in seq(opt(holder, "operators") or []):
            owners.setdefault(h(op), [op, []])[1].append(owner)
    for k in sorted(owners):
        op, who = owners[k]
        try:
            out["operators"].append(operator_record(op, who))
        except Exception as exc:
            out["operators"].append({"id": ident(op), "owners": who, "error": repr(exc)})
            problems.append("operator %s unreadable: %r" % (text(op.GetName()), exc))
    out["writer_index"] = writer_index(problems)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    out["cpm_loaded"] = None if cpm is None else {"build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__",
                                                                          None)}


def observe(label):
    out = {"format": FORMAT, "label": label, "pid": os.getpid(), "python": sys.version.split()[0], "problems": []}
    doc = sfmApp.GetDocumentRoot()
    out["document"] = text(vs.g_pDataModel.GetFileName(doc.GetFileId()))
    before = session_state()
    digest_before = document_digest(out["problems"])
    try:
        survey(out)
    except Exception as exc:
        out["problems"].append("survey error %r" % (exc,))
        out["traceback"] = traceback.format_exc()
    after = session_state()
    digest_after = document_digest(out["problems"])
    out["session_before"], out["session_after"] = before, after
    out["readonly"] = {"digest_before": digest_before, "digest_after": digest_after,
                       "unchanged": digest_before == digest_after and before == after}
    if not out["readonly"]["unchanged"]:
        out["problems"].append("the document or session state changed during the observation")
    return out


def main():
    root = globals().get("S0_DIR")
    label = globals().get("S0_LABEL")
    if not root or not label or not re.match(r"^S0-\d\d[a-z]?$", label):
        raise RuntimeError("Set S0_DIR and S0_LABEL (for example S0_LABEL = \"S0-01\") first; see the docstring.")
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; it is never replaced. Use the next label." % path)
    data = observe(label)
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    s = data.get("session_after") or {}
    summary = ("SUMMARY %s  shot=%s head=%s mode=%s t_chan=%s bones=%d handles=%d channels=%d operators=%d "
          "readonly=%s problems=%d%s" % (
              label, s.get("current_shot"), s.get("head_seconds"), (s.get("timeline_mode") or {}).get("name"),
              (data.get("time") or {}).get("t_chan"), len(data.get("bones") or {}),
              len((data.get("rig") or {}).get("handles") or {}), len(data.get("channels") or []),
              len(data.get("operators") or []), data["readonly"]["unchanged"], len(data["problems"]),
              (" first: %s" % data["problems"][0]) if data["problems"] else ""))
    print(summary.encode("ascii", "replace") if sys.version_info[0] == 2 else summary)


main()
