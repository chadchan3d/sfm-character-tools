# -*- coding: ascii -*-
"""A small fake of the SFM object model for the S0 survey observer's offline tests (Python 2.7 and 3).

It models only what the observer reads. Every mutating call the observer must never make is defined here, records
itself in World.mutations and raises, so a read-only violation fails a test even if the observer swallowed the
exception. The rig is a reduced biped shaped like the natively recorded Krystal structure (PS-1b5 OBS-03; the Pose B
descriptor): point/orient constraints from rig handles to the pelvis, an IK leg with a pole, an orient-constrained
foot, dormant channels on constrained bones, a foot helper under the foot handle, FK toes and tail with position
channels (one a constant offset, one animated), an expression-driven twist bone, a bone with no writer, a bone
slaved by an unknown operator type, a bone with two competing writers, and a constraint-weight channel.
"""
import types

MUTATORS = ("SetValue", "SetKeyValue", "InsertKeyAtTime", "InsertKey", "RemoveKey", "SetHeadTimeInSeconds",
            "StartUndo", "FinishUndo", "AbortUndoableOperation", "Undo", "Redo", "SetTimelineMode", "SetName",
            "AddAttribute", "RemoveAttribute", "SetCurrentTime", "SaveDocument")


class Mutation(Exception):
    pass


class World(object):
    def __init__(self):
        self.mutations = []
        self.next_handle = 1000
        self.head = 0.2083
        self.mode = 2
        self.doc_path = "e:\\fake\\sessions\\s0_survey.dmx"
        self.unreadable_channel = None

    def handle(self):
        self.next_handle += 1
        return self.next_handle


def _trap(name):
    def method(self, *args, **kwargs):
        world = getattr(self, "world", None) or WORLD[0]
        world.mutations.append(name)
        raise Mutation(name)
    return method


class Attr(object):
    def __init__(self, owner, name):
        self.owner, self.name = owner, name

    def GetName(self):
        return self.name

    def GetValue(self):
        return self.owner.attrs[self.name]

    def NextAttribute(self):
        names = list(self.owner.attrs)
        i = names.index(self.name) + 1
        return Attr(self.owner, names[i]) if i < len(names) else None


for _m in MUTATORS:
    setattr(Attr, _m, _trap(_m))


class El(object):
    def __init__(self, world, kind, name, **attrs):
        self.world, self.kind, self.name = world, kind, name
        self.h = world.handle()
        self.attrs = {}
        self.order = []
        for k in sorted(attrs):
            self.attrs[k] = attrs[k]

    def GetHandle(self):
        return self.h

    def GetId(self):
        return "id-%d" % self.h

    def GetTypeString(self):
        return self.kind

    def GetName(self):
        return self.name

    def HasAttribute(self, name):
        return name in self.attrs

    def GetAttribute(self, name):
        return Attr(self, name) if name in self.attrs else None

    def FirstAttribute(self):
        return Attr(self, list(self.attrs)[0]) if self.attrs else None


for _m in MUTATORS:
    setattr(El, _m, _trap(_m))


class Array(El):
    def __init__(self, world, items):
        El.__init__(self, world, "element_array", "")
        self.items = list(items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


class Vector(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Quaternion(object):
    def __init__(self, x, y, z, w):
        self.x, self.y, self.z, self.w = float(x), float(y), float(z), float(w)


def vec(v):
    return Quaternion(*v) if len(v) == 4 else Vector(*v)


class Time(object):
    def __init__(self, t):
        self.t = int(t)

    def GetTenthsOfMS(self):
        return self.t


def DmeTime_t(value):
    if isinstance(value, float):
        return Time(int(round(value * 10000)))
    return Time(value)


class Dag(El):
    def __init__(self, world, kind, name, pos=(0, 0, 0), rot=(0, 0, 0, 1), world_pos=None, **attrs):
        t = El(world, "DmeTransform", attrs.pop("transform_name", name), position=Vector(*pos),
               orientation=Quaternion(*rot), scale=1.0)
        El.__init__(self, world, kind, name, transform=t, children=Array(world, []), **attrs)
        self.world_pos = world_pos or pos

    def add(self, child):
        self.attrs["children"].items.append(child)
        return child

    def GetAbsPosition(self):
        return Vector(*self.world_pos)

    def GetAbsOrientation(self):
        return Quaternion(0, 0, 0, 1)


class Layer(El):
    def __init__(self, world, kind, keys):
        El.__init__(self, world, kind, "layer")
        self.keys = keys

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, i):
        return Time(self.keys[i][0])

    def GetKeyValue(self, i):
        v = self.keys[i][1]
        return vec(v) if isinstance(v, (list, tuple)) else v


class Log(El):
    def __init__(self, world, kind, layers):
        El.__init__(self, world, kind, "log", usedefaultvalue=False, curveinfo=None)
        self.layers = layers

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, i):
        return self.layers[i]

    def GetValue(self, t):
        keys = self.layers[-1].keys
        best = keys[0]
        for k in keys:
            if k[0] <= t.GetTenthsOfMS():
                best = k
        v = best[1]
        return vec(v) if isinstance(v, (list, tuple)) else v


class Channel(El):
    def __init__(self, world, name, log, clock, **attrs):
        El.__init__(self, world, "DmeChannel", name, mode=3, fromIndex=0, toIndex=0, **attrs)
        self.log, self.clock = log, clock

    def GetLog(self):
        if self.world.unreadable_channel == self.name:
            raise RuntimeError("log unreadable")
        return self.log

    def GetCurrentTime(self):
        return Time(self.clock)


class Clip(El):
    def __init__(self, world, kind, name, offset, start=0, end=0, **attrs):
        El.__init__(self, world, kind, name, **attrs)
        self.offset, self.start, self.end = offset, start, end

    def ToChildMediaTime(self, t, clamp):
        return Time(t.GetTenthsOfMS() + self.offset)

    def GetStartTime(self):
        return Time(self.start)

    def GetEndTime(self):
        return Time(self.end)

    def FindTrackGroup(self, name):
        for g in self.attrs.get("trackGroups", Array(self.world, [])).items:
            if g.name == name:
                return g
        return None


class TrackGroup(El):
    def FindTrack(self, name):
        for t in self.attrs["tracks"].items:
            if t.name == name:
                return t
        return None


class DataModel(object):
    def __init__(self, world):
        self.world = world

    def GetFileName(self, file_id):
        return self.world.doc_path

    def CanUndo(self):
        return True

    def CanRedo(self):
        return False

    def GetUndoDesc(self):
        return "Change Timeline Mode"

    def GetRedoDesc(self):
        return ""


for _m in MUTATORS:
    setattr(DataModel, _m, _trap(_m))

WORLD = [None]
T_CHAN = 50208
T_DOC = 2083


def build(world, stale=(), competing=False):
    """The reduced biped. `stale` names channels whose GetCurrentTime() is not the mapped tick."""
    w = world
    S = {}
    shot = Clip(w, "DmeFilmClip", "shot15", offset=-1875, start=1667, end=2917)
    chan_clip = Clip(w, "DmeChannelsClip", "Krystal", offset=T_CHAN - (T_DOC - 1875), channels=Array(w, []))
    S["shot"], S["clip"] = shot, chan_clip
    scene = Dag(w, "DmeDag", "scene")
    gm = Dag(w, "DmeGameModel", "krystal2020", modelName="models/krystal2020.mdl", bones=Array(w, []))
    scene.add(gm)
    bones = {}
    spec = [("bip_pelvis", None, (0, 0, 40)), ("bip_hip_l", "bip_pelvis", (4, 0, -2)),
            ("bip_knee_l", "bip_hip_l", (0, 0, -18)), ("bip_foot_l", "bip_knee_l", (0, 0, -17)),
            ("bip_toe_l", "bip_foot_l", (0, 5, -3)), ("bip_tail00", "bip_pelvis", (0, -4, 0)),
            ("bip_hair", "bip_pelvis", (0, 0, 30)), ("bip_hip_twist2_l", "bip_hip_l", (0, 0, -9)),
            ("bip_wing_l", "bip_pelvis", (3, -2, 10)), ("bip_ear_l", "bip_pelvis", (2, 0, 35))]
    for i, (name, parent, pos) in enumerate(spec):
        d = Dag(w, "DmeDag", name, pos=pos, transform_name="bone %d (%s)" % (i, name))
        (bones[parent] if parent else gm).add(d)
        gm.attrs["bones"].items.append(d.attrs["transform"])
        bones[name] = d
    S["bones"] = bones
    handles = {}
    rig_root = Dag(w, "DmeRigHandle", "rig_root")
    scene.add(rig_root)
    handles["rig_root"] = rig_root
    for name, parent, pos in (("Hip", "rig_root", (0, 0, 40)), ("Foot_l", "rig_root", (4, 0, 3)),
                              ("Knee_l", "rig_root", (4, 20, 20)), ("rig_footHelper0", "Foot_l", (4, 6, 0))):
        handles[name] = handles[parent].add(Dag(w, "DmeRigHandle", name, pos=pos))
    S["handles"] = handles
    animset = El(w, "DmeAnimationSet", "Krystal", gameModel=gm, controls=Array(w, []), operators=Array(w, []))
    S["animset"] = animset
    reg = El(w, "DmeRigAnimSetElements", "Krystal", animationSet=animset,
             elementList=Array(w, list(handles.values())))
    rig = Dag(w, "DmeRig", "rig_biped_Krystal45", animSetList=Array(w, [reg]))
    scene.add(rig)

    def channel(name, target, attr_name, keys, kind="Vector3", control=None, from_attr=None, from_el=None):
        layer = Layer(w, "Dme%sLogLayer" % kind, keys)
        log = Log(w, "Dme%sLog" % kind, [layer])
        clock = T_CHAN + 91 if name in stale else T_CHAN
        ch = Channel(w, name, log, clock, toElement=target, toAttribute=attr_name,
                     fromElement=from_el if from_el is not None else control,
                     fromAttribute=from_attr or ("valuePosition" if attr_name == "position" else "valueOrientation"))
        chan_clip.attrs["channels"].items.append(ch)
        return ch

    def control(name, target, pos_keys, rot_keys):
        c = El(w, "DmeTransformControl", name, valuePosition=Vector(*pos_keys[0][1]),
               valueOrientation=Quaternion(*rot_keys[0][1]))
        c.attrs["positionChannel"] = channel(name + "_p", target, "position", pos_keys, control=c)
        c.attrs["orientationChannel"] = channel(name + "_o", target, "orientation", rot_keys, "Quaternion",
                                                control=c)
        animset.attrs["controls"].items.append(c)
        return c

    still = lambda v: [[0, v], [80000, v]]  # noqa: E731
    for name in ("rig_root", "Hip", "Foot_l", "Knee_l", "rig_footHelper0"):
        t = handles[name].attrs["transform"]
        control(name, t, still([1, 2, 3]), [[0, [0, 0, 0, 1]], [T_CHAN, [0, 0.1, 0, 0.995]]])
    for name in ("bip_pelvis", "bip_hip_l", "bip_knee_l", "bip_foot_l"):  # dormant: their bones are constrained
        control(name, bones[name].attrs["transform"], still([0, 0, 0]), still([0, 0, 0, 1]))
    control("bip_toe_l", bones["bip_toe_l"].attrs["transform"], still([0, 5, -3]),
            [[0, [0, 0, 0, 1]], [T_CHAN, [0.2, 0, 0, 0.98]]])
    control("bip_tail00", bones["bip_tail00"].attrs["transform"], [[0, [0, -4, 0]], [T_CHAN, [0, -5, 1]]],
            [[0, [0, 0, 0, 1]], [T_CHAN, [0, 0.3, 0, 0.95]]])
    control("bip_wing_l", bones["bip_wing_l"].attrs["transform"], still([3, -2, 10]), still([0, 0, 0, 1]))
    ear = control("bip_ear_l", bones["bip_ear_l"].attrs["transform"], still([2, 0, 35]), still([0, 0, 0, 1]))
    flex = El(w, "DmeGlobalFlexControllerOperator", "smile", flexWeight=0.0)
    fc = El(w, "DmeCombinationInputControl", "smile", value=0.25)
    fc.attrs["channel"] = channel("smile_channel", flex, "flexWeight", [[0, 0.25]], "Float", control=fc,
                                  from_attr="value")
    animset.attrs["controls"].items.append(fc)
    S["ear_control"] = ear

    def target(handle, weight=1.0):
        return El(w, "DmeConstraintTarget", handle.name, target=handle, targetWeight=weight, oOffset=Quaternion(
            0, 0, 0, 1), vecOffset=Vector(0, 0, 0))

    def slave(bone):
        return El(w, "DmeConstraintSlave", bone.name, target=bone, basePosition=Vector(0, 0, 0))

    ops = animset.attrs["operators"].items
    hip_t = target(handles["Hip"])
    ops.append(El(w, "DmeRigPointConstraintOperator", "pointConstraint_bip_pelvis", slave=slave(bones["bip_pelvis"]),
                  targets=Array(w, [hip_t])))
    ops.append(El(w, "DmeRigOrientConstraintOperator", "orientConstraint_bip_pelvis",
                  slave=slave(bones["bip_pelvis"]), targets=Array(w, [target(handles["Hip"])])))
    foot_t = target(handles["Foot_l"])
    ops.append(El(w, "DmeRigIKConstraintOperator", "ikConstraint_Foot_l", startJoint=slave(bones["bip_hip_l"]),
                  midJoint=slave(bones["bip_knee_l"]), endJoint=slave(bones["bip_foot_l"]),
                  targets=Array(w, [foot_t]), pvTarget=handles["Knee_l"], startOffset=Vector(0, 0, 0),
                  midOffset=Vector(0, 0, 0), poleVector=Vector(0, 1, 0), mode=0))
    ops.append(El(w, "DmeRigOrientConstraintOperator", "orientConstraint_bip_foot_l",
                  slave=slave(bones["bip_foot_l"]), targets=Array(w, [target(handles["Foot_l"])])))
    ops.append(El(w, "DmeRigWingOperator", "wingSolver", slave=slave(bones["bip_wing_l"]),
                  targets=Array(w, [])))
    expr = El(w, "DmeExpressionOperator", "twist_l", expr="hip*0.5", result=Quaternion(0, 0, 0, 1))
    ops.append(expr)
    channel("twist_l_out", bones["bip_hip_twist2_l"].attrs["transform"], "orientation", still([0, 0, 0, 1]),
            "Quaternion", from_el=expr, from_attr="result")
    channel("ikConstraint_Foot_l - Foot_l targetWeight", foot_t, "targetWeight", [[0, 1.0]], "Float",
            control=El(w, "DmeCombinationInputControl", "weight_source"), from_attr="value")
    if competing:
        channel("tail_override", bones["bip_tail00"].attrs["transform"], "orientation", still([0, 0, 0, 1]),
                "Quaternion", from_el=El(w, "DmeTransformControl", "other"), from_attr="valueOrientation")
    tg = TrackGroup(w, "DmeTrackGroup", "channelTrackGroup", tracks=Array(w, [
        El(w, "DmeTrack", "animSetEditorChannels", children=Array(w, [chan_clip]))]))
    shot.attrs.update(trackGroups=Array(w, [tg]), animationSets=Array(w, [animset]), scene=scene,
                      operators=Array(w, []))
    shot.attrs["subClipTrackGroup"] = TrackGroup(w, "DmeTrackGroup", "sub", tracks=Array(w, []))
    movie = Clip(w, "DmeFilmClip", "movie", offset=0, subClipTrackGroup=TrackGroup(
        w, "DmeTrackGroup", "subClipTrackGroup", tracks=Array(w, [El(w, "DmeTrack", "Film", children=Array(
            w, [shot]))])))
    S["movie"] = movie
    return S


def install(stale=(), competing=False):
    """Fresh fake `sfmApp` and `vs` modules (returned; the caller puts them in sys.modules)."""
    world = World()
    WORLD[0] = world
    S = build(world, stale, competing)
    sfm = types.ModuleType("sfmApp")
    doc = El(world, "DmElement", "root")
    doc.GetFileId = lambda: 7
    sfm.GetDocumentRoot = lambda: doc
    sfm.GetHeadTimeInSeconds = lambda: world.head
    sfm.GetTimelineMode = lambda: world.mode
    sfm.GetNameForTimelineMode = lambda m: {2: "Motion Editor", 3: "Clip Editor", 4: "Graph Editor"}[m]
    sfm.GetMovie = lambda: S["movie"]
    sfm.GetShotAtCurrentTime = lambda: S["shot"]
    for name in ("SetHeadTimeInSeconds", "SetTimelineMode", "SaveDocument"):
        setattr(sfm, name, (lambda n: lambda *a: _trap(n)(world))(name))
    vs = types.ModuleType("vs")
    vs.DmeTime_t = DmeTime_t
    vs.g_pDataModel = DataModel(world)
    return world, S, sfm, vs
