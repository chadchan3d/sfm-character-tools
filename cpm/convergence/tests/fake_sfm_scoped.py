# -*- coding: utf-8 -*-
"""F-01 SFP-1 (scoped poses): the stage E fake SFM scene (fake_sfm_body.World), extended for scoped-pose tests.

Additions only: an instance may have no rig (the TF2 Heavy of MC-01); the model's own transform is evaluated as its
world transform when no constraint drives it (the Heavy's rootTransform control places the model); the animation
set carries its control groups (rootControlGroup, children, controls) from the fixture; and synthetic() builds small
analytic skeletons in the same fixture form, so frame, bridge and scale expectations can be computed independently
of both CPM and this evaluator. The evaluator is still a deterministic stand-in for SFM, never SFM.
"""
from __future__ import print_function

import copy
import math

import fake_sfm_body as FB


class World(FB.World):
    """One SFM process with one shot holding one fixture instance (rig optional)."""

    def build(self):
        fx = self.fx
        if fx["rig"].get("rig_handle") is not None:
            FB.World.build(self)
            self.add_groups()
            return
        # No rig: the stage E builder without its rig part.
        self.t_doc0, self.t_shot0, self.t_chan0 = fx["t_doc"], fx["t_shot"], fx["t_chan"]
        self.head = self.t_doc0
        m = fx["model"]
        bones_tr = []
        self.bone_dag, self.handle_dag = {}, {}
        gm_t = FB.Element(self, m["transform"], "DmeTransform", "model_transform",
                          position=FB.Vector(*m["local_position"]), orientation=FB.Quaternion(*m["local_orientation"]))
        if m.get("scale", {}).get("status") == "READ":
            gm_t.set("scale", float(m["scale"]["value"]))
        self.gm = FB.Dag(self, m["handle"], "DmeGameModel", fx.get("animation_set") or "model", gm_t,
                         modelName=m["model_ref"], bones=FB.ElementArray(self, []))
        for n, b in sorted(fx["bones"].items(), key=lambda kv: kv[1]["index"]):
            t = FB.Element(self, b["transform"], "DmeTransform", "bone %d (%s)" % (b["index"], n),
                           position=FB.Vector(*b["local_position"]), orientation=FB.Quaternion(*b["local_orientation"]))
            if b["scale"]["status"] == "READ":
                t.set("scale", float(b["scale"]["value"]))
            self.bone_dag[n] = FB.Dag(self, b["handle"], "DmeDag", n, t)
            bones_tr.append(t)
        self.gm.attrs["bones"].items = bones_tr
        for n, b in fx["bones"].items():
            (self.bone_dag[b["parent"]] if b["parent"] else self.gm).add(self.bone_dag[n])
        self.rig = None
        scene = FB.Dag(self, self.new_handle(), "DmeDag", "scene",
                       FB.Element(self, self.new_handle(), "DmeTransform", "s"))
        scene.add(self.gm)
        self.scene = scene
        self.ops = []
        for op in fx["operators"]:
            attrs = {}
            for slot, s in op["slaves"].items():
                if s is None:
                    attrs[slot] = None
                    continue
                attrs[slot] = FB.Element(self, s["slave"], "DmeConstraintSlave", "unnamed",
                                         target=self.el(s["target"]) if s["target"] is not None else None,
                                         position=FB.Vector(), orientation=FB.Quaternion())
            if op["type"] != "DmeExpressionOperator":
                targets = []
                for t in op["targets"]:
                    tgt = FB.Element(self, t["handle"], "DmeConstraintTarget", "target", target=self.el(t["target"]),
                                     targetWeight=float(t["weight"]["value"]))
                    for k in ("oOffset", "vecOffset"):
                        if t[k]["status"] == "READ":
                            tgt.set(k, FB.native(t[k]["value"], "quat" if len(t[k]["value"]) == 4 else "vec"))
                    targets.append(tgt)
                attrs["targets"] = FB.ElementArray(self, targets)
            if op.get("pole") is not None:
                attrs["pvTarget"] = self.el(op["pole"])
            if op["type"] == "DmeExpressionOperator":
                attrs.update({"expr": u"value", "value": 1.0, "result": 1.0})
            el = self.elements.get(op["handle"])
            if el is None:
                el = FB.Element(self, op["handle"], op["type"], op["name"], **attrs)
            else:
                el.kind, el.name = op["type"], op["name"]
                for k in sorted(attrs):
                    el.set(k, attrs[k])
            self.ops.append((op, el))
        self.controls = []
        for cname, c in fx["controls"].items():
            el = self.el(c["handle"])
            el.kind, el.name = c["type"], cname
            for k, v in (c.get("values") or {}).items():
                if v is not None:
                    el.set(k, FB.native(v, "quat" if isinstance(v, list) and len(v) == 4 else
                                        "vec" if isinstance(v, list) else None))
            self.controls.append(el)
        self.channels, self.layer_channel = {}, {}
        for name, ch in fx["channels"].items():
            kind = {"DmeVector3Log": "vec", "DmeQuaternionLog": "quat"}.get(ch["log_type"])
            layer = FB.Layer(self, ch["layer"], ch["layers"][0], ch["keys"], kind)
            log = FB.Log(self, ch["log"], ch["log_type"], layer)
            to = self.el(ch["to"]["handle"], ch["to"]["type"], ch["to"]["name"]) if ch["to"] else None
            frm = self.el(ch["from"]["handle"], ch["from"]["type"], ch["from"]["name"]) if ch["from"] else None
            el = self.elements.get(ch["handle"])
            attrs = dict(fromElement=frm, fromAttribute=ch["from_attribute"] or u"", toElement=to,
                         toAttribute=ch["to_attribute"], mode=ch["mode"], fromIndex=0, toIndex=0, log=log)
            if el is None:
                el = FB.Channel(self, ch["handle"], "DmeChannel", name, **attrs)
            else:
                el.__class__ = FB.Channel
                el.kind, el.name = "DmeChannel", name
                for k in sorted(attrs):
                    el.set(k, attrs[k])
            self.channels[name] = el
            self.layer_channel[layer.h] = name
        for cname, c in fx["controls"].items():
            el = self.elements[c["handle"]]
            for attr, h in c["channels"].items():
                el.set(attr, self.elements.get(h) if h is not None else None)
        self.animset = FB.Element(self, self.new_handle(), "DmeAnimationSet", fx.get("animation_set") or "model",
                                  gameModel=self.gm, controls=FB.ElementArray(self, self.controls),
                                  operators=FB.ElementArray(self, [el for op, el in self.ops
                                                                   if "animation_set" in op["owners"]]))
        self.chan_clip = FB.Clip(self, self.new_handle(), "DmeChannelsClip", "channels",
                                 offset=self.t_chan0 - self.t_shot0, start=0, end=10 ** 7,
                                 channels=FB.ElementArray(self, list(self.channels.values())))
        track = FB.Element(self, self.new_handle(), "DmeTrack", "animSetEditorChannels",
                           children=FB.ElementArray(self, [self.chan_clip]))
        group = FB.Element(self, self.new_handle(), "DmeTrackGroup", "channelTrackGroup",
                           tracks=FB.ElementArray(self, [track]))
        self.shot = FB.Clip(self, self.new_handle(), "DmeFilmClip", fx["source"]["shot"],
                            offset=self.t_shot0 - self.t_doc0, start=self.t_doc0 - 400, end=self.t_doc0 + 2000,
                            scene=scene, animationSets=FB.ElementArray(self, [self.animset]),
                            operators=FB.ElementArray(self, [el for op, el in self.ops if "shot" in op["owners"] and
                                                             "animation_set" not in op["owners"]]),
                            trackGroups=FB.ElementArray(self, [group]))
        film = FB.Element(self, self.new_handle(), "DmeTrack", "Film", children=FB.ElementArray(self, [self.shot]))
        self.movie = FB.Clip(self, self.new_handle(), "DmeFilmClip", "movie", offset=0, start=0, end=10 ** 7,
                             subClipTrackGroup=FB.Element(self, self.new_handle(), "DmeTrackGroup", "subClipTrackGroup",
                                                          tracks=FB.ElementArray(self, [film])))
        self.add_groups()

    def add_groups(self):
        """The animation set's control groups from the fixture (path order: parents before children)."""
        rows = self.fx.get("groups") or []
        if not rows:
            return
        by_path = {}
        for row in rows:
            handle = row.get("handle") or self.new_handle()
            members = [self.elements[h] for h in row["controls"] if h in self.elements]
            g = FB.Element(self, handle, "DmeControlGroup", row["path"][-1], children=FB.ElementArray(self, []),
                           controls=FB.ElementArray(self, members))
            by_path[tuple(row["path"])] = g
            parent = by_path.get(tuple(row["path"][:-1]))
            if parent is not None:
                parent.attrs["children"].items.append(g)
        root = by_path[tuple(rows[0]["path"])]
        self.animset.set("rootControlGroup", root)

    def solve(self):
        constrained = False
        for op, el in self.ops:
            for s in op["slaves"].values():
                if s is not None and s.get("target") == self.gm.h:
                    constrained = True
        if not constrained:
            # The model's own transform (written by its placement channels) is its world transform.
            self.gm.wp, self.gm.wq = self.local(self.gm)
        if self.rig is None:
            by_slave = {}
            for op, el in self.ops:
                if op["type"] == "DmeExpressionOperator":
                    continue
                for slot, s in op["slaves"].items():
                    if s is not None and s["target"] is not None:
                        by_slave.setdefault(s["target"], []).append((op["type"], slot, el))
            self.walk(self.gm, (self.gm.wp, self.gm.wq), 1.0, by_slave)
            return
        FB.World.solve(self)


# --- synthetic analytic skeletons -------------------------------------------------------------------------------------

def axis_angle(axis, degrees):
    h = math.radians(degrees) / 2.0
    n = math.sqrt(sum(c * c for c in axis)) or 1.0
    return [axis[0] / n * math.sin(h), axis[1] / n * math.sin(h), axis[2] / n * math.sin(h), math.cos(h)]


class Handles(object):
    def __init__(self, start=500000):
        self.n = start

    def __call__(self):
        self.n += 1
        return self.n


def synthetic(spec, model_ref=u"models/synthetic/analytic.mdl", t_chan=50000, groups=None, model_position=None,
              model_orientation=None, model_scale=None, handles=None):
    """A fixture for an analytic skeleton: spec = [(name, parent, local_position, local_orientation, scale|None)].
    Every bone is direct FK (one transform control, its position and orientation channels, one key at tick 0).
    groups: {group label: [bone names]} under a root group (organization only). The model is placed by its own
    rootTransform control. Handles are deterministic."""
    h = handles or Handles()
    fx = {"format": "f01-scoped-discovery-fixture-v1", "source": {"label": "synthetic", "sha256": None,
                                                                  "shot": "shot1", "timeline_mode": "Motion Editor"},
          "t_chan": t_chan, "t_doc": 0, "t_shot": 0, "animation_set": "synthetic1", "unknown_operator_types": [],
          "rig": {"names": [], "registrations": 0, "rig_handle": None, "registration": None, "elements": [],
                  "handles": {}}, "operators": [], "controls": {}, "channels": {}, "bones": {}, "writers": {},
          "slave_targets": {}}
    mp = list(model_position or [0.0, 0.0, 0.0])
    mq = list(model_orientation or [0.0, 0.0, 0.0, 1.0])
    model = {"handle": h(), "transform": h(), "model_ref": model_ref,
             "scale": {"status": "READ", "value": model_scale} if model_scale is not None else {"status": "ABSENT"},
             "local_position": mp, "local_orientation": mq, "world_position": mp, "world_orientation": mq}
    fx["model"] = model
    for index, (name, parent, lp, lq, scale) in enumerate(spec):
        fx["bones"][name] = {"index": index, "handle": h(), "transform": h(), "parent": parent, "parent_count": 1,
                             "parent_dag": None, "local_position": [FB.f32(c) for c in lp],
                             "local_orientation": [FB.f32(c) for c in lq], "world_position": [0.0, 0.0, 0.0],
                             "world_orientation": [0.0, 0.0, 0.0, 1.0],
                             "scale": {"status": "READ", "value": float(scale)} if scale is not None else
                             {"status": "ABSENT"}}
    for name, b in fx["bones"].items():
        b["parent_dag"] = fx["bones"][b["parent"]]["handle"] if b["parent"] else model["handle"]

    def control(cname, to_handle, to_name, lp, lq):
        c = {"handle": h(), "type": "DmeTransformControl", "channels": {}, "values": {"valuePosition": list(lp),
                                                                                      "valueOrientation": list(lq)}}
        for attr, suffix, log_type, layer_type, value in (
                ("position", "_p", "DmeVector3Log", "DmeVector3LogLayer", lp),
                ("orientation", "_o", "DmeQuaternionLog", "DmeQuaternionLogLayer", lq)):
            ch = {"handle": h(), "from": {"handle": c["handle"], "type": "DmeTransformControl", "name": cname},
                  "from_attribute": "valuePosition" if attr == "position" else "valueOrientation",
                  "to": {"handle": to_handle, "type": "DmeTransform", "name": to_name}, "to_attribute": attr,
                  "mode": 3, "log_type": log_type, "log": h(), "layers": [layer_type], "layer": h(),
                  "keys": [[0, [FB.f32(x) for x in value]]], "value": [FB.f32(x) for x in value], "clock": t_chan,
                  "curveinfo": {"status": "READ", "value": None}}
            fx["channels"][cname + suffix] = ch
            c["channels"]["positionChannel" if attr == "position" else "orientationChannel"] = ch["handle"]
            fx["writers"]["%d:%s" % (to_handle, attr)] = 1
        fx["controls"][cname] = c
    control(u"rootTransform", model["transform"], "model_transform", mp, mq)
    for name, b in fx["bones"].items():
        control(name, b["transform"], "bone %d (%s)" % (b["index"], name), b["local_position"],
                b["local_orientation"])
    rows = [{"path": [u"unnamed"], "handle": h(), "controls": []}]
    for label, members in sorted((groups or {}).items()):
        rows.append({"path": [u"unnamed", label], "handle": h(),
                     "controls": [fx["controls"][m]["handle"] for m in members]})
    fx["groups"] = rows
    return fx


def set_key(fx, channel, value, t=0):
    """Replace a channel's keys by one key (fixture level, before building a World)."""
    ch = fx["channels"][channel]
    ch["keys"] = [[t, [FB.f32(c) for c in value]]]
    ch["value"] = [FB.f32(c) for c in value]


def rekey(world, channel, value):
    """Set every key of a channel in a built World to `value` (a distinct destination posture)."""
    layer = world.channels[channel].attrs["log"].layer
    for k in layer.keys:
        k[1] = FB.native(list(value), layer.value_kind)


def clone(fx):
    return copy.deepcopy(fx)
