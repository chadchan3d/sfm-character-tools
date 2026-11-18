# -*- coding: utf-8 -*-
"""F-01 Stage 1 (generic structural rig support): derive a stage E discovery fixture from a saved binary DMX session.

The S0 fixtures (f01_body_fixture.py) come from a native read-only observation. For Fox there is no such observation;
the existing evidence is the session file the Owner used in the RC1 smoke (the R2 fixture, never modified). This
reader takes one animation set of one shot from that file and writes the same fixture form
(f01-body-discovery-fixture-v1): element handles, names, parents, bindings, log and layer types, every key, the value
at the mapped tick, the channel clock, the transforms and the document-wide writer counts.

What a saved file cannot give, and how it is filled (stated in the fixture's "derivation" field):
- handles: the DMX element index + 1 (unique and stable for the file; not SFM's runtime handles);
- transforms: the stored local values; world values compose the stored locals down the scene hierarchy, without
  solving constraints (the fake scene re-evaluates every constraint itself, fake_sfm_body.World.evaluate);
- the value at the mapped tick: the layer's last key at or before it (the fake scene's hold evaluation);
- the channel clock: the mapped tick (Motion Editor);
- control groups: the animation set's group tree (paths and member control handles), for the Save dialog's review.
Nothing is interpreted: roles are left to CPM. The file is only read: its SHA-256, size and modification time must be
unchanged afterwards, and the parse must consume it exactly.

usage: python -I f01_dmx_body_fixture.py SESSION.dmx ANIMSET_GUID SHOT_NAME T_DOC_TICKS LABEL OUT.json
"""
from __future__ import print_function

import hashlib
import io
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "m06_w2_qualification", "tools"))
import scan_deferred_fixture as S  # noqa: E402  (the binary DMX format 5 reader already used for M-06 W2)

CONSTRAINTS = ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigIKConstraintOperator")
CHANNEL_ATTRS = ("positionChannel", "orientationChannel", "channel", "leftvaluechannel", "rightvaluechannel")
VALUE_ATTRS = ("valuePosition", "valueOrientation", "value")
SLOTS = ("slave", "startJoint", "midJoint", "endJoint")
SOLVER = ("startOffset", "midOffset", "poleVector", "mode")
BONE_RE = re.compile(r"^bone (\d+) \((.+)\)$")
OFFSET = 1


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def decode(t, v):
    """A DMX attribute value as plain data (vectors and quaternions as float lists)."""
    if t == 10:
        return list(struct.unpack("<3f", v))
    if t == 13:
        return list(struct.unpack("<4f", v))
    if t == 3:
        return f32(v)
    if t is not None and 15 <= t <= 28 and isinstance(v, list):       # arrays: element type t - 14
        return [decode(t - 14, x) for x in v]
    if isinstance(v, bytes):
        raise SystemExit("unsupported attribute type %r" % (t,))
    return v


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qrot(q, v):
    p = qmul(qmul(q, [v[0], v[1], v[2], 0.0]), [-q[0], -q[1], -q[2], q[3]])
    return p[:3]


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def compose(parent, local, scale=1.0):
    p, q = parent
    lp, lq = local
    r = qrot(q, [c * scale for c in lp])
    return [f32(p[i] + r[i]) for i in range(3)], [f32(c) for c in qnorm(qmul(q, lq))]


class Doc(object):
    def __init__(self, path):
        self.path = path
        self.before = S.identity(path)
        with io.open(path, "rb") as f:
            raw = f.read()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        _, self.E = S.parse(raw)

    def a(self, e, k):
        x = e["a"].get(k)
        return None if x is None else x[1]

    def t(self, e, k):
        x = e["a"].get(k)
        return None if x is None else x[0]

    def ref(self, e, k):
        v = self.a(e, k)
        return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None

    def refs(self, e, k):
        return [x for x in (self.a(e, k) or []) if isinstance(x, int) and x >= 0]

    def value(self, e, k):
        return decode(self.t(e, k), self.a(e, k))

    def field(self, e, k):
        if k not in e["a"]:
            return {"status": "ABSENT"}
        v = self.value(e, k)
        if self.t(e, k) == 1:
            return {"status": "READ", "value": None}
        return {"status": "READ", "value": v}

    def ident(self, i):
        if i is None:
            return None
        e = self.E[i]
        return {"handle": i + OFFSET, "type": e["type"], "name": e["name"]}

    def check_unchanged(self):
        if S.identity(self.path) != self.before:
            raise SystemExit("the session file changed while it was read")


def derive(doc, animset_guid, shot_name, t_doc, label):
    E = doc.E
    sets = [i for i, e in enumerate(E) if e["id"] == animset_guid]
    if len(sets) != 1 or E[sets[0]]["type"] != "DmeAnimationSet":
        raise SystemExit("animation set %s not found exactly once" % animset_guid)
    aset = sets[0]
    shots = [i for i, e in enumerate(E) if e["type"] == "DmeFilmClip" and e["name"] == shot_name and
             aset in doc.refs(e, "animationSets")]
    if len(shots) != 1:
        raise SystemExit("shot %s holding the animation set not found exactly once" % shot_name)
    shot = E[shots[0]]
    tf = E[doc.ref(shot, "timeFrame")]
    t_shot = t_doc - doc.a(tf, "start") + doc.a(tf, "offset")
    clips = []
    for tg in doc.refs(shot, "trackGroups"):
        for tr in doc.refs(E[tg], "tracks"):
            for c in doc.refs(E[tr], "children"):
                if E[c]["type"] == "DmeChannelsClip" and E[c]["name"] == E[aset]["name"]:
                    clips.append(c)
    if len(clips) != 1:
        raise SystemExit("the animation set's channels clip is not unique")
    clip = E[clips[0]]
    ctf = E[doc.ref(clip, "timeFrame")]
    t_chan = t_shot - doc.a(ctf, "start") + doc.a(ctf, "offset")
    # The scene hierarchy (parents by DAG children).
    scene_root = doc.ref(shot, "scene")
    parents, order, pending = {}, [], [scene_root]
    while pending:
        i = pending.pop(0)
        order.append(i)
        for c in doc.refs(E[i], "children"):
            parents.setdefault(c, []).append(i)
            if c not in order and c not in pending:
                pending.append(c)

    def local(i):
        tr = E[doc.ref(E[i], "transform")]
        return doc.value(tr, "position"), qnorm(doc.value(tr, "orientation"))

    def tscale(i):
        tr = E[doc.ref(E[i], "transform")]
        return doc.field(tr, "scale") if "scale" in tr["a"] else {"status": "ABSENT"}

    world = {scene_root: ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])}
    wscale = {scene_root: 1.0}
    for i in order[1:]:
        p = parents[i][0]
        if p not in world:
            continue
        s = tscale(p)
        own = float(s["value"]) if s["status"] == "READ" else 1.0
        world[i] = compose(world[p], local(i), wscale[p] if E[p]["type"] == "DmeDag" else 1.0)
        wscale[i] = wscale[p] * own

    def state(i):
        lp, lq = local(i)
        wp, wq = world.get(i, (lp, lq))
        return {"local_position": lp, "local_orientation": lq, "world_position": wp, "world_orientation": wq,
                "scale": tscale(i)}
    gm = doc.ref(E[aset], "gameModel")
    D = {"format": "f01-body-discovery-fixture-v1",
         "source": {"label": label, "sha256": doc.sha256, "shot": shot_name, "timeline_mode": "Motion Editor"},
         "derivation": "f01_dmx_body_fixture.py: a saved binary DMX session, read only (handles = element index + "
                       "1; worlds compose the stored locals without solving constraints; values at the mapped tick "
                       "by hold evaluation; clocks = the mapped tick). Not a native observation.",
         "t_chan": t_chan, "t_doc": t_doc, "t_shot": t_shot}
    gst = state(gm)
    D["model"] = dict(gst, handle=gm + OFFSET, transform=doc.ref(E[gm], "transform") + OFFSET,
                      model_ref=doc.a(E[gm], "modelName"))
    rigs = []
    for i in order:
        if E[i]["type"] == "DmeRig":
            for r in doc.refs(E[i], "animSetList"):
                if doc.ref(E[r], "animationSet") == aset:
                    rigs.append((i, r))
    if len(rigs) != 1:
        raise SystemExit("%d rig registrations for the animation set" % len(rigs))
    rig, reg = rigs[0]
    elements = doc.refs(E[reg], "elementList")
    D["rig"] = {"names": [E[rig]["name"]], "registrations": 1, "rig_handle": rig + OFFSET,
                "registration": reg + OFFSET, "elements": [x + OFFSET for x in elements], "handles": {}}
    for i in elements:
        if E[i]["type"] != "DmeRigHandle":
            continue
        ps = parents.get(i, [])
        D["rig"]["handles"][E[i]["name"]] = dict(
            state(i), handle=i + OFFSET, transform=doc.ref(E[i], "transform") + OFFSET, parent_count=len(ps),
            parent=doc.ident(ps[0]) if len(ps) == 1 else None)
    bone_transforms = doc.refs(E[gm], "bones")
    dag_of = {}
    for i in order:
        if E[i]["type"] == "DmeDag" and doc.ref(E[i], "transform") in bone_transforms:
            dag_of[doc.ref(E[i], "transform")] = i
    name_of_dag = {}
    for t in bone_transforms:
        m = BONE_RE.match(E[t]["name"])
        name_of_dag[dag_of[t]] = m.group(2)
    D["bones"] = {}
    for t in bone_transforms:
        m = BONE_RE.match(E[t]["name"])
        i = dag_of[t]
        ps = parents.get(i, [])
        D["bones"][m.group(2)] = dict(state(i), index=int(m.group(1)), handle=i + OFFSET, transform=t + OFFSET,
                                      parent=name_of_dag.get(ps[0]) if len(ps) == 1 else None,
                                      parent_count=len(ps), parent_dag=ps[0] + OFFSET if len(ps) == 1 else None)
    owned_set = doc.refs(E[aset], "operators")
    owned_shot = doc.refs(shot, "operators")
    D["operators"] = []
    for i in owned_set + [x for x in owned_shot if x not in owned_set]:
        op = E[i]
        owners = (["animation_set"] if i in owned_set else []) + (["shot"] if i in owned_shot else [])
        row = {"handle": i + OFFSET, "type": op["type"], "name": op["name"], "owners": owners, "slaves": {},
               "targets": [], "pole": None, "solver": {}}
        for slot in SLOTS:
            if slot in op["a"]:
                s = doc.ref(op, slot)
                row["slaves"][slot] = None if s is None else {
                    "slave": s + OFFSET, "target": (doc.ref(E[s], "target") + OFFSET)
                    if doc.ref(E[s], "target") is not None else None}
        for t in doc.refs(op, "targets"):
            row["targets"].append({"handle": t + OFFSET, "target": (doc.ref(E[t], "target") + OFFSET)
                                   if doc.ref(E[t], "target") is not None else None,
                                   "weight": doc.field(E[t], "targetWeight"), "oOffset": doc.field(E[t], "oOffset"),
                                   "vecOffset": doc.field(E[t], "vecOffset")})
        if doc.ref(op, "pvTarget") is not None:
            row["pole"] = doc.ref(op, "pvTarget") + OFFSET
        for k in SOLVER:
            if k in op["a"]:
                row["solver"][k] = doc.field(op, k)
        if op["type"] == "DmeExpressionOperator":
            row["attributes"] = dict((k, doc.field(op, k)) for k in ("expr", "value", "result", "name")
                                     if k in op["a"])
        D["operators"].append(row)
    D["controls"] = {}
    for i in doc.refs(E[aset], "controls"):
        c = E[i]
        refs = {}
        for k in CHANNEL_ATTRS:
            if k in c["a"]:
                r = doc.ref(c, k)
                refs[k] = r + OFFSET if r is not None else None
        values = dict((k, doc.value(c, k)) for k in VALUE_ATTRS if k in c["a"])
        D["controls"][c["name"]] = {"handle": i + OFFSET, "type": c["type"], "channels": refs, "values": values}
    # Document-wide writer counts: every channel in the file, by destination element and attribute.
    destinations = {}
    for i, e in enumerate(E):
        if e["type"] == "DmeChannel" and doc.ref(e, "toElement") is not None:
            key = "%d:%s" % (doc.ref(e, "toElement") + OFFSET, doc.a(e, "toAttribute"))
            destinations[key] = destinations.get(key, 0) + 1
    D["channels"], D["writers"] = {}, {}
    for i in doc.refs(clip, "channels"):
        ch = E[i]
        lg = doc.ref(ch, "log")
        log = E[lg] if lg is not None else None
        layers = [E[x] for x in doc.refs(log, "layers")] if log is not None else []
        keys = []
        if layers:
            times = doc.a(layers[0], "times") or []
            values = decode(doc.t(layers[0], "values"), doc.a(layers[0], "values") or [])
            keys = [[int(t), v] for t, v in zip(times, values)]
        value = None
        if keys and log["type"] in ("DmeVector3Log", "DmeQuaternionLog", "DmeFloatLog"):
            value = keys[0][1]
            for t, v in keys:
                if t <= t_chan:
                    value = v
        to = doc.ref(ch, "toElement")
        attr = doc.a(ch, "toAttribute")
        D["channels"][ch["name"]] = {
            "handle": i + OFFSET, "from": doc.ident(doc.ref(ch, "fromElement")),
            "from_attribute": doc.a(ch, "fromAttribute"), "to": doc.ident(to), "to_attribute": attr,
            "mode": doc.a(ch, "mode"), "log_type": log["type"] if log is not None else None,
            "log": lg + OFFSET if lg is not None else None, "layers": [L["type"] for L in layers],
            "layer": doc.refs(log, "layers")[0] + OFFSET if layers else None, "keys": keys, "value": value,
            "clock": t_chan, "curveinfo": {"status": "READ", "value": None}}
        if to is not None:
            key = "%d:%s" % (to + OFFSET, attr)
            D["writers"][key] = destinations.get(key, 0)
    D["slave_targets"] = {}
    for i, e in enumerate(E):
        if e["type"] == "DmeConstraintSlave" and doc.ref(e, "target") is not None:
            k = "%d" % (doc.ref(e, "target") + OFFSET)
            D["slave_targets"][k] = D["slave_targets"].get(k, 0) + 1
    # The animation set's control groups, breadth first (prod_scope_groups' form: organization only).
    D["groups"] = []
    root = doc.ref(E[aset], "rootControlGroup")
    pending, seen = ([(root, [])] if root is not None else []), set()
    while pending:
        g, path = pending.pop(0)
        if g in seen:
            raise SystemExit("control groups repeat")
        seen.add(g)
        here = path + [E[g]["name"]]
        D["groups"].append({"path": here, "controls": [c + OFFSET for c in doc.refs(E[g], "controls")]})
        for c in doc.refs(E[g], "children"):
            pending.append((c, here))
    types = set()
    for e in E:
        if e["type"] in ("DmeAnimationSet", "DmeFilmClip"):
            for x in doc.refs(e, "operators"):
                types.add(E[x]["type"])
    known = set(CONSTRAINTS + ("DmeExpressionOperator", "DmePackColorOperator"))
    D["unknown_operator_types"] = sorted(t for t in types if t not in known)
    return D


def main(argv):
    if len(argv) != 7:
        print(__doc__)
        return 2
    doc = Doc(argv[1])
    D = derive(doc, argv[2], argv[3], int(argv[4]), argv[5])
    doc.check_unchanged()
    data = (json.dumps(D, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with io.open(argv[6], "xb") as f:
        f.write(data)
    print(argv[6], len(data), hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
