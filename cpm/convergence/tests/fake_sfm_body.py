# -*- coding: utf-8 -*-
"""F-01 full body (stage E): a fake native SFM scene built from an S0-derived discovery fixture.

Every element of the fixture's Krystal instance exists with its native handle, type, name and bindings: 156 bones,
22 rig handles, 290 controls, 505 channels with their keys, 39 operators with their slaves and targets, the rig
registration, the channels clip, the shot and the movie. Only the evaluation is modelled: channels (mode 3) write
their destinations at the channel time; rig handles compose down their hierarchy; point and orient constraints copy
their target's world transform (with offsets); IK solves two-bone chains toward the target in the plane of the pole;
FK bones compose with SFM's hierarchical bone scale; transforms are stored as float32. The model is a deterministic,
rigid-covariant stand-in for SFM's solver, not SFM's: it shows that CPM's capture, plan, transaction and
verification are consistent under one evaluator, never that SFM evaluates this way.

Mutating calls the tests watch: SetKeyValue, InsertKeyAtTime (journaled for Undo, Redo and Abort), StartUndo,
FinishUndo, AbortUndoableOperation, SetHeadTimeInSeconds. World switches inject failures and editor states.
"""
from __future__ import print_function

import copy
import math
import struct
import sys
import types

TICKS = 10000.0
try:
    _TEXT = unicode  # noqa: F821
    _INT = (int, long)  # noqa: F821
except NameError:
    _TEXT = str
    _INT = (int,)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


class Vector(object):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = f32(x), f32(y), f32(z)


class Quaternion(object):
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x, self.y, self.z, self.w = f32(x), f32(y), f32(z), f32(w)


def native(v, kind):
    if kind == "quat":
        return Quaternion(*v)
    if kind == "vec":
        return Vector(*v)
    return v


def plain(v):
    if isinstance(v, Quaternion):
        return [v.x, v.y, v.z, v.w]
    if isinstance(v, Vector):
        return [v.x, v.y, v.z]
    return v


class Time(object):
    def __init__(self, ticks):
        self.ticks = int(ticks)

    def GetTenthsOfMS(self):
        return self.ticks


def DmeTime_t(x):
    if isinstance(x, bool):
        raise TypeError("bool time")
    if isinstance(x, _INT):
        return Time(x)
    return Time(int(round(float(x) * TICKS)))


# --- quaternion and transform mathematics (double precision) --------------------------------------------------------

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qconj(q):
    return [-q[0], -q[1], -q[2], q[3]]


def qrot(q, v):
    return qmul(qmul(q, [v[0], v[1], v[2], 0.0]), qconj(q))[:3]


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def compose(parent, local, scale=1.0):
    (p, q), (lp, lq) = parent, local
    off = qrot(q, [c * scale for c in lp])
    return ([p[i] + off[i] for i in range(3)], qnorm(qmul(q, lq)))


def to_local(parent, world, scale=1.0):
    (p, q), (wp, wq) = parent, world
    d = qrot(qconj(q), [wp[i] - p[i] for i in range(3)])
    return ([c / scale for c in d], qnorm(qmul(qconj(q), wq)))


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def length(a):
    return math.sqrt(sum(c * c for c in a))


def unit(a):
    n = length(a) or 1.0
    return [c / n for c in a]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def m_to_q(m):
    """Rotation matrix (rows) to quaternion."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return qnorm([(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s])
    if m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        return qnorm([0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s])
    if m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        return qnorm([(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s])
    s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
    return qnorm([(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s])


def frame(a, b):
    """Orthonormal frame (columns) from a primary and a secondary direction."""
    x = unit(a)
    z = unit(cross(x, b))
    if length(z) < 1e-9:
        z = unit(cross(x, [0.0, 0.0, 1.0] if abs(x[2]) < 0.9 else [1.0, 0.0, 0.0]))
    y = cross(z, x)
    return [x, y, z]


def rotation_between_frames(local_frame, world_frame):
    """R with R*local_frame[i] = world_frame[i]."""
    lf, wf = local_frame, world_frame
    m = [[sum(wf[k][r] * lf[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
    return m_to_q(m)


# --- elements --------------------------------------------------------------------------------------------------------

class Attr(object):
    def __init__(self, owner, name):
        self.owner, self.name = owner, name

    def GetName(self):
        return self.name

    def GetValue(self):
        return self.owner.attrs[self.name]

    def NextAttribute(self):
        names = self.owner.order
        i = names.index(self.name) + 1
        return Attr(self.owner, names[i]) if i < len(names) else None


class Element(object):
    def __init__(self, world, handle, kind, name, **attrs):
        self.world, self.h, self.kind, self.name = world, int(handle), kind, name
        self.attrs, self.order = {}, []
        world.elements[self.h] = self
        for k in sorted(attrs):
            self.set(k, attrs[k])

    def set(self, name, value):
        if name not in self.attrs:
            self.order.append(name)
        self.attrs[name] = value

    def GetHandle(self):
        return self.h

    def GetTypeString(self):
        return self.kind

    def GetName(self):
        return self.name

    def GetId(self):
        return "id-%d" % self.h

    def HasAttribute(self, name):
        return name in self.attrs

    def GetAttribute(self, name):
        return Attr(self, name) if name in self.attrs else None

    def FirstAttribute(self):
        return Attr(self, self.order[0]) if self.order else None


class ElementArray(Element):
    def __init__(self, world, items):
        Element.__init__(self, world, world.new_handle(), "element_array", "")
        self.items = list(items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


class Dag(Element):
    def __init__(self, world, handle, kind, name, transform, **attrs):
        Element.__init__(self, world, handle, kind, name, transform=transform, children=ElementArray(world, []),
                         **attrs)
        self.wp, self.wq = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]

    def add(self, child):
        self.attrs["children"].items.append(child)

    def GetAbsPosition(self):
        return Vector(*self.wp)

    def GetAbsOrientation(self):
        return Quaternion(*self.wq)


class Layer(Element):
    def __init__(self, world, handle, kind, keys, value_kind):
        Element.__init__(self, world, handle, kind, "layer")
        self.keys = [[int(t), native(v, value_kind)] for t, v in keys]
        self.value_kind = value_kind

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, i):
        return Time(self.keys[i][0])

    def GetKeyValue(self, i):
        return self.keys[i][1]

    def SetKeyValue(self, i, value):
        self.world.calls.append(("SetKeyValue", self.h, i))
        self.world.check_write(self)
        old = self.keys[i][1]
        new = native(plain(value), self.value_kind)
        self.keys[i][1] = new
        self.world.journal(("set", self, i, old, new))

    def InsertKeyAtTime(self, *args):
        assert len(args) == 1, "CPM must call the one-argument overload (fake)"
        t = args[0].ticks
        self.world.calls.append(("InsertKeyAtTime", self.h, t))
        self.world.check_write(self)
        index = 0
        while index < len(self.keys) and self.keys[index][0] < t:
            index += 1
        if index < len(self.keys) and self.keys[index][0] == t:
            return index
        held = copy.deepcopy(self.keys[max(0, index - 1)][1]) if self.keys else native([0.0] * 3, self.value_kind)
        self.keys.insert(index, [t, held])
        self.world.journal(("insert", self, index, [t, held]))
        return index

    def IsUsingCurveTypes(self):
        return False

    def IsCompressed(self):
        return False


class Log(Element):
    def __init__(self, world, handle, kind, layer):
        Element.__init__(self, world, handle, kind, "log", layers=ElementArray(world, [layer]))
        self.layer = layer
        self.extra_layers = []

    def GetNumLayers(self):
        return 1 + len(self.extra_layers)

    def GetLayer(self, i):
        return self.layer if i == 0 else self.extra_layers[i - 1]

    def value_at(self, t):
        keys = self.layer.keys
        if not keys:
            return None
        v = keys[0][1]
        for k in keys:
            if k[0] <= t:
                v = k[1]
        return plain(v)

    def GetValue(self, t):
        v = self.value_at(t.ticks)
        return native(v, self.layer.value_kind) if v is not None else None

    def HasDefaultValue(self):
        return False

    def GetNumBookmarkComponents(self):
        return 0


class Channel(Element):
    def GetLog(self):
        return self.attrs["log"]

    def GetCurrentTime(self):
        w = self.world
        return Time(w.t_chan() if w.timeline_mode == 2 else w.stale_clock)


class Clip(Element):
    def __init__(self, world, handle, kind, name, offset, start, end, **attrs):
        Element.__init__(self, world, handle, kind, name, **attrs)
        self.offset, self.start, self.end = offset, start, end

    def ToChildMediaTime(self, t, clamp):
        return Time(t.ticks + self.offset)

    def FromChildMediaTime(self, t, clamp):
        return Time(t.ticks - self.offset)

    def GetStartTime(self):
        return Time(self.start)

    def GetEndTime(self):
        return Time(self.end)


class DataModel(object):
    def __init__(self, world):
        self.world = world
        self.current, self.stack, self.redo_stack, self.calls = None, [], [], []

    def IsUndoEnabled(self):
        return self.world.undo_enabled

    def CanUndo(self):
        return bool(self.stack)

    def CanRedo(self):
        return bool(self.redo_stack)

    def GetUndoDesc(self):
        return self.stack[-1]["label"] if self.stack else u""

    def GetRedoDesc(self):
        return self.redo_stack[-1]["label"] if self.redo_stack else u""

    def StartUndo(self, label, redo):
        self.calls.append(("StartUndo", label))
        assert self.current is None, "nested Undo (fake)"
        if self.world.start_raises == "before":           # fails without opening anything
            raise RuntimeError("StartUndo failed before opening (test)")
        self.current = {"label": label.decode("utf-8") if isinstance(label, bytes) else label, "items": []}
        if self.world.start_raises == "after":            # opened, then reported a failure
            raise RuntimeError("StartUndo failed after opening (test)")

    def ItemsAddedToCurrentUndo(self):
        return bool(self.current and self.current["items"])

    def FinishUndo(self):
        self.calls.append(("FinishUndo",))
        if self.world.finish_raises == "before":          # fails before committing: the transaction stays open
            raise RuntimeError("FinishUndo failed before commit (test)")
        if self.world.finish_raises:                      # True or "after": committed, then reported a failure
            entry, self.current = self.current, None
            self.stack.append(entry)
            self.redo_stack = []
            raise RuntimeError("FinishUndo failed (test)")
        self.stack.append(self.current)
        self.redo_stack = []
        self.current = None

    def AbortUndoableOperation(self):
        self.calls.append(("AbortUndoableOperation",))
        if self.world.abort_raises:
            raise RuntimeError("abort failed (test)")
        revert(self.current["items"])
        self.current = None

    def Undo(self):
        entry = self.stack.pop()
        revert(entry["items"])
        self.redo_stack.append(entry)
        self.world.evaluate()

    def Redo(self):
        entry = self.redo_stack.pop()
        for item in entry["items"]:
            if item[0] == "insert":
                item[1].keys.insert(item[2], copy.deepcopy(item[3]))
            else:
                item[1].keys[item[2]][1] = item[4]
        self.stack.append(entry)
        self.world.evaluate()

    def push_foreign(self, label):
        self.stack.append({"label": label, "items": []})


def revert(items):
    for item in reversed(items):
        if item[0] == "insert":
            del item[1].keys[item[2]]
        else:
            item[1].keys[item[2]][1] = item[3]


# --- the world -------------------------------------------------------------------------------------------------------

class World(object):
    """One SFM process with one shot holding the fixture's Krystal instance."""

    def __init__(self, fixture, handle_offset=0):
        self.fx = copy.deepcopy(fixture)
        self.elements = {}
        self.next_handle = 10 ** 8
        self.calls = []
        self.timeline_mode = 2
        self.stale_clock = 50299
        self.fail_on_write = None        # a channel name whose first write raises
        self.finish_raises = self.abort_raises = False
        self.start_raises = None                 # None, "before" or "after"
        self.undo_enabled = True
        self.evaluate_on_refresh = True
        self.refresh_calls = []
        self.dm = DataModel(self)
        self.build()
        self.evaluate()

    def new_handle(self):
        self.next_handle += 1
        return self.next_handle

    def journal(self, item):
        if self.dm.current is not None:
            self.dm.current["items"].append(item)

    def check_write(self, layer):
        name = self.layer_channel.get(layer.h)
        if self.fail_on_write is not None and name == self.fail_on_write:
            self.fail_on_write = None
            raise RuntimeError("native write failed on %s (test)" % name)

    def el(self, h, kind="DmElement", name="element"):
        if h is None:
            return None
        if int(h) not in self.elements:
            Element(self, h, kind, name)
        return self.elements[int(h)]

    def build(self):
        fx = self.fx
        self.t_doc0, self.t_shot0, self.t_chan0 = fx["t_doc"], fx["t_shot"], fx["t_chan"]
        self.head = self.t_doc0
        m = fx["model"]
        bones_tr = []
        self.bone_dag, self.handle_dag = {}, {}
        gm_t = Element(self, m["transform"], "DmeTransform", "krystal2020_GameModel",
                       position=Vector(*m["local_position"]), orientation=Quaternion(*m["local_orientation"]))
        self.gm = Dag(self, m["handle"], "DmeGameModel", "krystal2020_GameModel", gm_t, modelName=m["model_ref"],
                      bones=ElementArray(self, []))
        for n, b in sorted(fx["bones"].items(), key=lambda kv: kv[1]["index"]):
            t = Element(self, b["transform"], "DmeTransform", "bone %d (%s)" % (b["index"], n),
                        position=Vector(*b["local_position"]), orientation=Quaternion(*b["local_orientation"]))
            if b["scale"]["status"] == "READ":
                t.set("scale", float(b["scale"]["value"]))
            self.bone_dag[n] = Dag(self, b["handle"], "DmeDag", n, t)
            bones_tr.append(t)
        self.gm.attrs["bones"].items = bones_tr
        for n, b in fx["bones"].items():
            (self.bone_dag[b["parent"]] if b["parent"] else self.gm).add(self.bone_dag[n])
        r = fx["rig"]
        self.rig = Dag(self, r["rig_handle"], "DmeRig", r["names"][0],
                       Element(self, self.new_handle(), "DmeTransform", "rig"))
        for n, h in fx["rig"]["handles"].items():
            t = Element(self, h["transform"], "DmeTransform", n, position=Vector(*h["local_position"]),
                        orientation=Quaternion(*h["local_orientation"]))
            self.handle_dag[n] = Dag(self, h["handle"], "DmeRigHandle", n, t)
        for n, h in fx["rig"]["handles"].items():
            p = h["parent"]
            (self.rig if p["type"] == "DmeRig" else self.elements[p["handle"]]).add(self.handle_dag[n])
        scene = Dag(self, self.new_handle(), "DmeDag", "scene", Element(self, self.new_handle(), "DmeTransform", "s"))
        scene.add(self.gm)
        scene.add(self.rig)
        self.scene = scene
        # Operators, their slaves and targets.
        self.ops = []
        for op in fx["operators"]:
            attrs = {}
            for slot, s in op["slaves"].items():
                if s is None:
                    attrs[slot] = None
                    continue
                attrs[slot] = Element(self, s["slave"], "DmeConstraintSlave", "unnamed",
                                      target=self.el(s["target"]) if s["target"] is not None else None,
                                      position=Vector(), orientation=Quaternion())
            if op["type"] != "DmeExpressionOperator":
                targets = []
                for t in op["targets"]:
                    tgt = Element(self, t["handle"], "DmeConstraintTarget", "target", target=self.el(t["target"]),
                                  targetWeight=float(t["weight"]["value"]))
                    for k in ("oOffset", "vecOffset"):
                        if t[k]["status"] == "READ":
                            tgt.set(k, native(t[k]["value"], "quat" if len(t[k]["value"]) == 4 else "vec"))
                    targets.append(tgt)
                attrs["targets"] = ElementArray(self, targets)
            if op.get("pole") is not None:
                attrs["pvTarget"] = self.el(op["pole"])
            for k, f in (op.get("solver") or {}).items():
                if f["status"] == "READ":
                    v = f["value"]
                    attrs[k] = native(v, "quat" if isinstance(v, list) and len(v) == 4 else "vec") if isinstance(
                        v, list) else v
            if op["type"] == "DmeExpressionOperator":
                attrs.update({"expr": u"value", "value": 1.0, "result": 1.0})
            el = self.elements.get(op["handle"])
            if el is None:
                el = Element(self, op["handle"], op["type"], op["name"], **attrs)
            else:
                el.kind, el.name = op["type"], op["name"]
                for k in sorted(attrs):
                    el.set(k, attrs[k])
            self.ops.append((op, el))
        # Controls and channels.
        self.controls = []
        for cname, c in fx["controls"].items():
            el = self.el(c["handle"])
            el.kind, el.name = c["type"], cname
            for k, v in (c.get("values") or {}).items():
                if v is not None:
                    el.set(k, native(v, "quat" if isinstance(v, list) and len(v) == 4 else
                                     "vec" if isinstance(v, list) else None))
            self.controls.append(el)
        self.channels, self.layer_channel = {}, {}
        for name, ch in fx["channels"].items():
            kind = {"DmeVector3Log": "vec", "DmeQuaternionLog": "quat"}.get(ch["log_type"])
            layer = Layer(self, ch["layer"], ch["layers"][0], ch["keys"], kind)
            log = Log(self, ch["log"], ch["log_type"], layer)
            to = self.el(ch["to"]["handle"], ch["to"]["type"], ch["to"]["name"]) if ch["to"] else None
            frm = self.el(ch["from"]["handle"], ch["from"]["type"], ch["from"]["name"]) if ch["from"] else None
            el = self.elements.get(ch["handle"])
            attrs = dict(fromElement=frm, fromAttribute=ch["from_attribute"] or u"", toElement=to,
                         toAttribute=ch["to_attribute"], mode=ch["mode"], fromIndex=0, toIndex=0, log=log)
            if el is None:
                el = Channel(self, ch["handle"], "DmeChannel", name, **attrs)
            else:
                el.__class__ = Channel
                el.kind, el.name = "DmeChannel", name
                for k in sorted(attrs):
                    el.set(k, attrs[k])
            self.channels[name] = el
            self.layer_channel[layer.h] = name
        for cname, c in fx["controls"].items():
            el = self.elements[c["handle"]]
            for attr, h in c["channels"].items():
                el.set(attr, self.elements.get(h) if h is not None else None)
        self.animset = Element(self, self.new_handle(), "DmeAnimationSet", "Krystal", gameModel=self.gm,
                               controls=ElementArray(self, self.controls),
                               operators=ElementArray(self, [el for op, el in self.ops if "animation_set" in op["owners"]]))
        owned = [self.el(h) for h in fx["rig"]["elements"]]
        reg = Element(self, fx["rig"]["registration"], "DmeRigAnimSetElements", "rigElements_Krystal",
                      animationSet=self.animset, elementList=ElementArray(self, owned))
        self.rig.set("animSetList", ElementArray(self, [reg]))
        self.chan_clip = Clip(self, self.new_handle(), "DmeChannelsClip", "Krystal", offset=self.t_chan0 - self.t_shot0,
                              start=0, end=10 ** 7, channels=ElementArray(self, list(self.channels.values())))
        track = Element(self, self.new_handle(), "DmeTrack", "animSetEditorChannels",
                        children=ElementArray(self, [self.chan_clip]))
        group = Element(self, self.new_handle(), "DmeTrackGroup", "channelTrackGroup", tracks=ElementArray(self, [track]))
        self.shot = Clip(self, self.new_handle(), "DmeFilmClip", fx["source"]["shot"],
                         offset=self.t_shot0 - self.t_doc0, start=self.t_doc0 - 400, end=self.t_doc0 + 2000,
                         scene=scene, animationSets=ElementArray(self, [self.animset]),
                         operators=ElementArray(self, [el for op, el in self.ops if "shot" in op["owners"] and
                                                       "animation_set" not in op["owners"]]),
                         trackGroups=ElementArray(self, [group]))
        film = Element(self, self.new_handle(), "DmeTrack", "Film", children=ElementArray(self, [self.shot]))
        self.movie = Clip(self, self.new_handle(), "DmeFilmClip", "movie", offset=0, start=0, end=10 ** 7,
                          subClipTrackGroup=Element(self, self.new_handle(), "DmeTrackGroup", "subClipTrackGroup",
                                                    tracks=ElementArray(self, [film])))

    # --- time and evaluation ----------------------------------------------------------------------------------

    def t_chan(self):
        return self.head + (self.t_shot0 - self.t_doc0) + (self.t_chan0 - self.t_shot0)

    def channel(self, name):
        return self.channels[name]

    def keys(self, name):
        return [[k[0], plain(k[1])] for k in self.channels[name].attrs["log"].layer.keys]

    def evaluate(self):
        t = self.t_chan()
        for ch in self.channels.values():
            if ch.attrs["mode"] != 3 or ch.attrs["toElement"] is None:
                continue
            v = ch.attrs["log"].value_at(t)
            if v is None:
                continue
            kind = ch.attrs["log"].layer.value_kind
            ch.attrs["toElement"].set(ch.attrs["toAttribute"], native(v, kind) if kind else v)
        self.solve()

    def local(self, dag):
        t = dag.attrs["transform"]
        return (plain(t.attrs["position"]), qnorm(plain(t.attrs["orientation"])))

    def scale(self, dag):
        t = dag.attrs["transform"]
        return float(t.attrs.get("scale", 1.0))

    def set_world(self, dag, p, q, parent=None, parent_scale=1.0):
        dag.wp, dag.wq = list(p), qnorm(q)
        if parent is not None:
            lp, lq = to_local(parent, (p, q), parent_scale)
            dag.attrs["transform"].set("position", Vector(*lp))
            dag.attrs["transform"].set("orientation", Quaternion(*lq))

    def solve(self):
        def handle_world(dag, parent):
            p, q = compose(parent, self.local(dag))
            dag.wp, dag.wq = p, q
            for child in dag.attrs["children"].items:
                if child.kind == "DmeRigHandle":
                    handle_world(child, (p, q))
        for child in self.rig.attrs["children"].items:
            handle_world(child, ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]))
        by_slave = {}
        for op, el in self.ops:
            if op["type"] == "DmeExpressionOperator":
                continue
            for slot, s in op["slaves"].items():
                if s is not None and s["target"] is not None:
                    by_slave.setdefault(s["target"], []).append((op["type"], slot, el))
        for op_type, slot, el in by_slave.get(self.gm.h, []):
            self.constrain(self.gm, op_type, el, None, 1.0)
        self.walk(self.gm, (self.gm.wp, self.gm.wq), 1.0, by_slave)
        for n, dag in self.handle_dag.items():
            for op_type, slot, el in by_slave.get(dag.h, []):
                self.constrain(dag, op_type, el, None, 1.0)

    def target_world(self, el):
        t = el.attrs["targets"].items[0]
        tw = t.attrs["target"]
        p, q = list(tw.wp), list(tw.wq)
        if "vecOffset" in t.attrs:
            off = qrot(q, plain(t.attrs["vecOffset"]))
            p = [p[i] + off[i] for i in range(3)]
        if "oOffset" in t.attrs:
            q = qnorm(qmul(q, plain(t.attrs["oOffset"])))
        return p, q

    def constrain(self, dag, op_type, el, parent, parent_scale):
        p, q = self.target_world(el)
        if op_type == "DmeRigPointConstraintOperator":
            dag.wp = p
        elif op_type == "DmeRigOrientConstraintOperator":
            dag.wq = q
        if parent is not None:
            self.set_world(dag, dag.wp, dag.wq, parent, parent_scale)

    def walk(self, dag, world, scale, by_slave):
        for child in dag.attrs["children"].items:
            if child.kind == "DmeRigHandle":
                continue
            p, q = compose(world, self.local(child), scale)
            child.wp, child.wq = p, q
            drivers = by_slave.get(child.h, [])
            ik = [d for d in drivers if d[0] == "DmeRigIKConstraintOperator" and d[1] == "startJoint"]
            if ik:
                self.solve_ik(child, ik[0][2], world, scale)
            for op_type, slot, el in drivers:
                if op_type in ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator"):
                    self.constrain(child, op_type, el, world, scale)
            self.walk(child, (child.wp, child.wq), scale * self.scale(child), by_slave)

    def solve_ik(self, start, el, parent_world, parent_scale):
        """Two-bone IK: start and mid oriented so the chain reaches toward the target in the plane of the pole."""
        mid = el.attrs["midJoint"].attrs["target"]
        end = el.attrs["endJoint"].attrs["target"]
        s_start = parent_scale * self.scale(start)
        s_mid = s_start * self.scale(mid)
        lm = plain(mid.attrs["transform"].attrs["position"])
        le = plain(end.attrs["transform"].attrs["position"])
        l1, l2 = length(lm) * s_start, length(le) * s_mid
        p0 = list(start.wp)
        target = list(self.target_world(el)[0])
        pole = list(el.attrs["pvTarget"].wp)
        d = sub(target, p0)
        dist = max(1e-6, min(length(d), (l1 + l2) * 0.999999))
        a = unit(d)
        plane = sub(pole, p0)
        n = unit(cross(a, plane))
        if length(n) < 1e-9:
            n = unit(cross(a, [0.0, 0.0, 1.0]))
        up = cross(n, a)
        cos1 = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
        ang = math.acos(cos1)
        dir1 = [a[i] * math.cos(ang) + up[i] * math.sin(ang) for i in range(3)]
        pm = [p0[i] + dir1[i] * l1 for i in range(3)]
        pe = [p0[i] + a[i] * dist for i in range(3)]
        q0 = rotation_between_frames(frame(lm, [0.0, 0.0, 1.0] if abs(unit(lm)[2]) < 0.9 else [1.0, 0.0, 0.0]),
                                     frame(dir1, up))
        self.set_world(start, p0, q0, parent_world, parent_scale)
        q1 = rotation_between_frames(frame(le, [0.0, 0.0, 1.0] if abs(unit(le)[2]) < 0.9 else [1.0, 0.0, 0.0]),
                                     frame(sub(pe, pm), up))
        self.set_world(mid, pm, q1, (start.wp, start.wq), s_start)

    # --- the native modules --------------------------------------------------------------------------------------

    def modules(self):
        w = self
        sfm = types.ModuleType("sfmApp")
        sfm.GetHeadTimeInSeconds = lambda: w.head / TICKS
        sfm.GetMovie = lambda: w.movie
        sfm.GetShotAtCurrentTime = lambda: w.shot
        sfm.GetTimelineMode = lambda: w.timeline_mode

        def set_head(seconds):
            w.refresh_calls.append({"seconds": seconds, "in_undo": w.dm.current is not None})
            w.head = int(round(seconds * TICKS))
            if w.evaluate_on_refresh:
                w.evaluate()
        sfm.SetHeadTimeInSeconds = set_head
        vs = types.ModuleType("vs")
        vs.DmeTime_t = DmeTime_t
        vs.Vector = Vector
        vs.Quaternion = Quaternion
        vs.g_pDataModel = w.dm
        return sfm, vs
