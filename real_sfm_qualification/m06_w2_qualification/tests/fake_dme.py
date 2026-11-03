# -*- coding: utf-8 -*-
"""Offline fake DME for the M-06 W2 instrument tests (synthetic; not SFM).

Native wrapper semantics that the instruments depend on are modelled explicitly:
- GetAttribute(name) raises AttributeError for a missing attribute (SFM's vs wrapper), HasAttribute returns bool;
- an attribute can be made unreadable (GetValue raises) or its presence can disagree (HasAttribute lies);
- GetId() returns an opaque id whose str() is a stable content rendering, distinct per element.
"""
import itertools

_HANDLES = itertools.count(5000)


class UniqueId(object):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class Time(object):
    def __init__(self, ticks):
        self.ticks = int(ticks)

    def GetTenthsOfMS(self):
        return self.ticks

    def GetSeconds(self):
        return self.ticks / 10000.0


class Vector(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Attr(object):
    def __init__(self, owner, name, value):
        self.owner, self.name, self.value = owner, name, value

    def GetValue(self):
        if self.name in self.owner.unreadable:
            raise RuntimeError("unreadable attribute (fake) %s" % self.name)
        return self.value

    def SetValue(self, value):          # used only by the native fixture-preparation script under test
        self.owner.attrs[self.name] = value
        self.value = value


class El(object):
    def __init__(self, world, kind, name, **attrs):
        self.world = world
        self.kind, self.name = kind, name
        self.h = next(_HANDLES)
        self.uid = UniqueId("%08x-fake-%d" % (self.h * 2654435761 % (1 << 32), self.h))
        self.attrs = dict(attrs)
        self.unreadable = set()
        self.lying_presence = set()
        self.broken = set()
        world.elements[self.h] = self

    def GetHandle(self):
        if "handle" in self.broken:
            raise RuntimeError("handle unreadable (fake)")
        return self.h

    def GetTypeString(self):
        if "type" in self.broken:
            raise RuntimeError("type unreadable (fake)")
        return self.kind

    def GetName(self):
        if "name" in self.broken:
            raise RuntimeError("name unreadable (fake)")
        return self.name

    def GetId(self):
        if "id" in self.broken:
            raise RuntimeError("id unreadable (fake)")
        return self.uid

    def HasAttribute(self, name):
        has = name in self.attrs
        return (not has) if name in self.lying_presence else has

    def GetAttribute(self, name):
        if name not in self.attrs:
            raise AttributeError(name)
        return Attr(self, name, self.attrs[name])

    def set(self, name, value):
        self.attrs[name] = value

    def drop(self, name):
        self.attrs.pop(name, None)


class Layer(El):
    def __init__(self, world, name, keys):
        El.__init__(self, world, "DmeFloatLogLayer", name, compressed=b"", curvetypes=[])
        self.keys = [list(k) for k in keys]

    # The raw key arrays, derived from the keys as natively (times in ticks, values).
    def HasAttribute(self, name):
        if name in ("times", "values"):
            return (name not in self.lying_presence)
        return El.HasAttribute(self, name)

    def GetAttribute(self, name):
        if name == "times":
            return Attr(self, name, [Time(k[0]) for k in self.keys])
        if name == "values":
            return Attr(self, name, [k[1] for k in self.keys])
        return El.GetAttribute(self, name)

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, i):
        return Time(self.keys[i][0])

    def GetKeyValue(self, i):
        return self.keys[i][1]


class Log(El):
    def __init__(self, world, name, keys):
        El.__init__(self, world, "DmeFloatLog", name, usedefaultvalue=False, defaultvalue=0.0)
        self.layers = [Layer(world, name, keys)]

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, i):
        return self.layers[i]

    def IsEmpty(self):
        if "is_empty" in self.broken:
            raise RuntimeError("IsEmpty unreadable (fake)")
        return not self.layers[0].keys

    def GetValue(self, t):
        keys = self.layers[0].keys
        if not keys:
            return self.attrs["defaultvalue"]
        best = keys[0]
        for k in keys:
            if k[0] <= t.GetTenthsOfMS():
                best = k
        return best[1]


class Channel(El):
    def __init__(self, world, name, frm, from_attr, to, to_attr, mode, keys):
        El.__init__(self, world, "DmeChannel", name, fromElement=frm, fromAttribute=from_attr, toElement=to,
                    toAttribute=to_attr, mode=mode)
        self.log = Log(world, name, keys)
        self.attrs["log"] = self.log

    def GetLog(self):
        return self.log

    def GetCurrentTime(self):
        return Time(self.world.media_ticks)


class GameModel(El):
    def __init__(self, world, name, model, checksum, bones):
        El.__init__(self, world, "DmeGameModel", name, modelName=model, bones=bones)
        self.checksum = checksum

    def GetStudioHdr(self):
        return type("Hdr", (object,), {"checksum": self.checksum})()


class DataModel(object):
    def __init__(self, world):
        self.world = world
        self.undo = {"enabled": True, "can_undo": False, "can_redo": False, "undo_desc": "", "redo_desc": "",
                     "count": 0}
        self.broken = set()

    def _get(self, k):
        if k in self.broken:
            raise RuntimeError("%s unreadable (fake)" % k)
        return self.undo[k]

    def IsUndoEnabled(self):
        return self._get("enabled")

    def CanUndo(self):
        return self._get("can_undo")

    def CanRedo(self):
        return self._get("can_redo")

    def GetUndoDesc(self):
        return self._get("undo_desc")

    def GetRedoDesc(self):
        return self._get("redo_desc")

    def GetUndoItemCount(self):
        return self._get("count")

    def GetFileName(self, file_id):
        return self.world.doc_path

    def GetElement(self, handle):
        return self.world.elements.get(handle)

    def GetElementId(self, handle):
        el = self.world.elements.get(handle)
        return UniqueId(el.uid.text) if el is not None else UniqueId("")


class Tier1(object):
    @staticmethod
    def IsUniqueIdValid(uid):
        return isinstance(uid, UniqueId) and bool(uid.text)

    @staticmethod
    def IsUniqueIdEqual(a, b):
        return isinstance(a, UniqueId) and isinstance(b, UniqueId) and a.text == b.text


MODEL = "models/synthetic/krystal_twin.mdl"
CHECKSUM = 4242


class World(object):
    def __init__(self, doc_path="C:\\qual\\fixture.dmx", file_id=7):
        self.elements = {}
        self.doc_path = doc_path
        self.media_ticks = 1250
        self.head = 0.125
        self.dm = DataModel(self)
        self.document = El(self, "DmElement", "session")
        self.file_id = file_id
        self.document.GetFileId = lambda: self.file_id
        self.group = El(self, "DmeTrackGroup", "channelTrackGroup", tracks=[])
        self.track = El(self, "DmeTrack", "animSetEditorChannels", children=[])
        self.group.attrs["tracks"] = [self.track]
        self.shot = El(self, "DmeFilmClip", "shot12", trackGroups=[self.group], animationSets=[])
        self.shot.GetFileId = lambda: self.file_id
        self.shot.FindTrackGroup = lambda n: self.group if n == "channelTrackGroup" else None
        self.group.FindTrack = lambda n: self.track if n == "animSetEditorChannels" else None
        self.instances = {}

    # ---- construction --------------------------------------------------------
    def instance(self, name, with_scale_graph=False, muscles_key=0.6995, legsize=0.4, extra_empty=(),
                 graph_output_mode=3, graph_output_log="empty"):
        bones = [El(self, "DmeTransform", "bone %d (%s)" % (i, b), position=Vector(0, 0, i),
                    orientation=Vector(0, 0, 0)) for i, b in enumerate(("bip_pelvis", "bip_head", "bip_hand_l"))]
        gm = GameModel(self, name + "_model", MODEL, CHECKSUM, bones)
        clip = El(self, "DmeChannelsClip", name, channels=[])
        controls, operators = [], []
        inst = {"name": name, "gm": gm, "bones": dict((b.name.split("(")[1][:-1], b) for b in bones), "clip": clip,
                "controls": controls, "operators": operators, "channels": clip.attrs["channels"], "flex": {}}

        def flex_mono(literal, stored, key, mode=3):
            ctl = El(self, "DmElement", literal, value=stored)
            op = El(self, "DmeGlobalFlexControllerOperator", literal, flexWeight=stored if key is None else key)
            ch = Channel(self, literal, ctl, "value", op, "flexWeight", mode, [] if key is None else [[0, key]])
            if key is None:
                ch.log.attrs["defaultvalue"] = stored          # EMPTY: the log evaluates its default
            ctl.set("channel", ch)
            controls.append(ctl)
            operators.append(op)
            clip.attrs["channels"].append(ch)
            inst["flex"][literal] = (ctl, ch, op)
            return ctl

        def flex_stereo(literal, left, right):
            ctl = El(self, "DmElement", literal, leftValue=left, rightValue=right, value=0.5)
            for side, v in (("left", left), ("right", right)):
                op = El(self, "DmeGlobalFlexControllerOperator", literal + "_" + side, flexWeight=v)
                ch = Channel(self, literal + "_" + side, ctl, side + "Value", op, "flexWeight", 3, [[0, v]])
                ctl.set(side + "valuechannel", ch)
                operators.append(op)
                clip.attrs["channels"].append(ch)
            controls.append(ctl)
            return ctl

        flex_mono("Muscles", 0.0, muscles_key)          # STATIC_PLAY_ONE_KEY_ZERO
        flex_mono("Legsize", legsize, legsize)           # ONE_KEY_ZERO
        flex_stereo("Breastsize", 0.3, 0.35)
        flex_mono("smile", 0.2, 0.2)                     # non-Body
        for literal, stored in extra_empty:
            flex_mono(literal, stored, None)             # EMPTY log
        head = inst["bones"]["bip_head"]
        tc = El(self, "DmeTransformControl", "bip_head", valuePosition=Vector(0, 0, 1),
                valueOrientation=Vector(0, 0, 0))
        for attr, to_attr in (("positionChannel", "position"), ("orientationChannel", "orientation")):
            ch = Channel(self, "bip_head_" + to_attr, tc, "value" + to_attr.capitalize(), head, to_attr, 3,
                         [[0, 1.0]])
            tc.set(attr, ch)
            clip.attrs["channels"].append(ch)
        controls.append(tc)
        if with_scale_graph:
            self.scale_graph(inst, "bip_head", control_value=0.113, physical=1.13, output_mode=graph_output_mode,
                             output_log=graph_output_log)
        root = El(self, "DmeControlGroup", "root", controls=list(controls), children=[])
        aset = El(self, "DmeAnimationSet", name, gameModel=gm, controls=controls, operators=operators,
                  rootControlGroup=root)
        inst.update({"animset": aset, "root": root})
        self.shot.attrs["animationSets"].append(aset)
        self.track.attrs["children"].append(clip)
        self.instances[name] = inst
        return inst

    def scale_graph(self, inst, bone_name, control_value, physical, output_mode=1, output_log="keyed"):
        bone = inst["bones"][bone_name]
        ctl = El(self, "DmElement", bone_name + "_scale", value=control_value, defaultValue=0.1)
        expr = El(self, "DmeExpressionOperator", bone_name + "_scale_expr", expr="lerp(value, lo, hi)", lo=0.0,
                  hi=10.0, value=control_value, result=physical)
        cin = Channel(self, bone_name + "_scale", ctl, "value", expr, "value", 3, [[0, control_value]])
        cout = Channel(self, bone_name + "_scale_out", expr, "result", bone, "scale", output_mode,
                       [[0, physical]] if output_log == "keyed" else [])
        if output_log == "empty":                        # M-05: empty output log, usedefaultvalue False
            cout.log.attrs.update(usedefaultvalue=False, defaultvalue=0.0)
        ctl.set("channel", cin)
        bone.set("scale", physical)
        inst["controls"].append(ctl)
        inst["operators"].append(expr)
        inst["channels"].extend([cin, cout])
        if "root" in inst:
            inst["root"].attrs["controls"].append(ctl)
        inst["graph"] = {"control": ctl, "expr": expr, "in": cin, "out": cout, "bone": bone}
        return inst["graph"]

    def remove_graph(self, inst, keep=(), keep_resolvable=()):
        """Undo/abort of a created graph; keep names the attachments to leave behind (incomplete cleanup);
        keep_resolvable names graph parts (control, expr, in, out, in_log, out_log, in_layer, out_layer) whose
        elements stay resolvable through the data model although detached."""
        g = inst.pop("graph")
        if "control" not in keep:
            inst["controls"].remove(g["control"])
        if "group" not in keep:
            inst["root"].attrs["controls"].remove(g["control"])
        if "operator" not in keep:
            inst["operators"].remove(g["expr"])
        if "channels" not in keep:
            inst["channels"].remove(g["in"])
            inst["channels"].remove(g["out"])
        if "scale" not in keep:
            g["bone"].drop("scale")
        if "elements" not in keep:
            parts = {"control": g["control"], "expr": g["expr"], "in": g["in"], "out": g["out"],
                     "in_log": g["in"].log, "out_log": g["out"].log, "in_layer": g["in"].log.layers[0],
                     "out_layer": g["out"].log.layers[0]}
            for part, el in parts.items():
                if part not in keep_resolvable:
                    self.elements.pop(el.h, None)
        return g

    # ---- authored edits used by the comparator tests ----------------------------
    def write_side(self, inst, literal, desired):
        """CPM's write_side for a mono flex, as production performs it (same log and layer)."""
        ctl, ch, op = inst["flex"][literal]
        layer = ch.log.layers[0]
        ctl.set("value", desired)
        if not layer.keys:
            layer.keys[:] = [[0, desired]]                # ClearAndAddSampleAtTime(local zero) of the source
        else:
            layer.keys[0][1] = desired                     # SetKeyValue(0, desired)
        op.set("flexWeight", desired)                      # channel.Operate()

    def set_flex(self, inst, literal, key, stored=None):
        ctl, ch, op = inst["flex"][literal]
        ch.log.layers[0].keys[0][1] = key
        op.set("flexWeight", key)
        if stored is not None:
            ctl.set("value", stored)

    # ---- native module fakes ------------------------------------------------------
    def modules(self):
        world = self
        sfm = type("sfmApp", (object,), {})()
        sfm.HasDocument = lambda: True
        sfm.GetDocumentRoot = lambda: world.document
        sfm.GetShotAtCurrentTime = lambda: world.shot
        sfm.GetHeadTimeInSeconds = lambda: world.head
        vs = type("vs", (object,), {})()
        vs.g_pDataModel = world.dm
        vs.tier1 = Tier1
        return sfm, vs


def twin_world(**kw):
    w = World(**kw)
    w.instance("krystal_target", with_scale_graph=True)
    w.instance("krystal_peer", muscles_key=0.5, legsize=0.25)
    return w


import os as _os
W1_APP = _os.environ.get("M06W2_W1_APP") or _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))),
    "cpm", "app", "SFM_Character_Preset_Manager.py")
W1_SHA256 = "fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
CONFIG = {"cpm": {"path": W1_APP, "sha256": W1_SHA256}, "shot": "shot12", "target_animset": "krystal_target", "peers": ["krystal_peer"],
          "body": ["Muscles", "Legsize", "Breastsize"], "nonbody": ["smile"], "transform_controls": "all"}
