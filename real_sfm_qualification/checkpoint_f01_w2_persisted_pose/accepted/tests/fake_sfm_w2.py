# -*- coding: ascii -*-
"""Offline stand-ins for the SFM native modules (sfmApp, vs, PySide) and for
Windows process identity, used by the F-01 W2 tests. Python 2.7 and 3.

The fake document is built from tests/fixtures/synthetic_scene.json only: a
self-contained synthetic Krystal left-arm rig with the R2 fixture's element
types, names, bindings, bracket ticks and shot timing, and invented transforms.
No private capture is used.

The arm is evaluated by a deterministic analytic solver written in the CollarL
frame (rotation matrices; independent of the harness code): the upper arm points
from its origin at the elbow input, the arm plane contains the hand input, the
lower arm points at the hand input, the hand takes the Hand_l orientation. The
bone lengths are fixed, so the hand bone generally misses the Hand_l handle (a
hand-target residual, as in the native rig). The tests therefore exercise the
harness's control flow, evidence and verdicts against a rig whose collar-relative
behaviour is known; they do not demonstrate native SFM behaviour.

Process B worlds can poison the source shot: every read of a source-pose value
(stored control values, rig-handle and bone transforms, key times and values, log
evaluation, channel clocks, evaluated world transforms) raises and is recorded,
while binding and graph metadata stay readable.
"""
import json
import math
import os
import struct
import types

TICKS = 10000
HERE = os.path.dirname(os.path.abspath(__file__))
SCENE_PATH = os.path.join(HERE, 'fixtures', 'synthetic_scene.json')
FRAME_TICKS = {5: 2083, 10: 4167, 11: 4583}
POSE_ATTRS = ('position', 'orientation', 'valuePosition', 'valueOrientation', 'value', 'defaultvalue',
              'flexWeight', 'targetWeight')


class PoisonedRead(Exception):
    """A process-B read of a source-pose value (test detector)."""


def load_scene():
    with open(SCENE_PATH, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def key(name):
    if isinstance(name, bytes) and not isinstance(name, str):
        return name.decode('utf-8')
    if isinstance(name, bytes):
        return name.decode('utf-8')
    return name


# --------------------------------------------------------------------------
# Value types
# --------------------------------------------------------------------------

class Time(object):
    def __init__(self, ticks):
        self.ticks = int(ticks)

    def GetTenthsOfMS(self):
        return self.ticks

    def GetSeconds(self):
        return self.ticks / float(TICKS)


def DmeTime_t(seconds):
    return Time(int(round(float(seconds) * TICKS)))


class Vector(object):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Quaternion(object):
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x, self.y, self.z, self.w = float(x), float(y), float(z), float(w)


def as_list(v):
    if isinstance(v, Quaternion):
        return [v.x, v.y, v.z, v.w]
    if isinstance(v, Vector):
        return [v.x, v.y, v.z]
    return float(v)


def mk(value, quaternion=None):
    if isinstance(value, list):
        if len(value) == 4 and quaternion is not False:
            return Quaternion(*value)
        if len(value) == 3:
            return Vector(*value)
    return value


# --------------------------------------------------------------------------
# Rigid math for the fake rig (3x3 matrices; independent of the harness)
# --------------------------------------------------------------------------

def q_to_m(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def m_to_q(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def mt(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def xf(pos, q):
    return (list(pos), q_to_m(q))


def xf_mul(a, b):
    return ([a[0][i] + mv(a[1], b[0])[i] for i in range(3)], mm(a[1], b[1]))


def xf_inv(a):
    r = mt(a[1])
    return ([-c for c in mv(r, a[0])], r)


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def add(a, b):
    return [a[i] + b[i] for i in range(3)]


def scale(a, s):
    return [c * s for c in a]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    n = math.sqrt(sum(c * c for c in a))
    if n < 1e-9:
        raise ValueError('degenerate vector in fake solver')
    return [c / n for c in a]


def columns(x, y, z):
    return [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]


def rotate_about_x(q, degrees):
    h = math.radians(degrees) / 2.0
    r = [math.sin(h), 0.0, 0.0, math.cos(h)]
    x1, y1, z1, w1 = q
    x2, y2, z2, w2 = r
    return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]


def solve_arm_collar_frame(u0, len1, len2, hand_c, hand_rot_c, elbow_c):
    """Collar-frame arm: returns {bone: (position, rotation matrix)}."""
    x = norm(sub(elbow_c, u0))
    z = norm(cross(x, sub(hand_c, u0)))
    y = cross(z, x)
    upper = (list(u0), columns(x, y, z))
    lower_p = add(u0, scale(x, len1))
    x2 = norm(sub(hand_c, lower_p))
    y2 = cross(z, x2)
    lower = (lower_p, columns(x2, y2, z))
    hand = (add(lower_p, scale(x2, len2)), hand_rot_c)
    return {'bip_UpperArm_l': upper, 'bip_lowerArm_l': lower, 'bip_hand_l': hand}


# --------------------------------------------------------------------------
# Elements
# --------------------------------------------------------------------------

class Attr(object):
    def __init__(self, owner, name, value):
        self.owner = owner
        self.name = name
        self.value = value

    def GetName(self):
        return self.name

    def GetValue(self):
        world = self.owner.world
        if (self.owner.GetHandle(), self.name) in world.unreadable:
            raise RuntimeError('unreadable attribute (test)')
        if self.name in POSE_ATTRS:
            world.check_poison(self.owner, 'attribute ' + self.name)
        return self.value

    def GetValueUntyped(self):
        raise RuntimeError('untyped read unavailable')

    def NextAttribute(self):
        order = self.owner.order
        i = order.index(self.name)
        return self.owner.attrs[order[i + 1]] if i + 1 < len(order) else None


class ElementArray(object):
    def __init__(self, world, items):
        self.items = list(items)
        self.h = world.new_handle()

    def GetHandle(self):
        return self.h

    def GetTypeString(self):
        return 'element_array'

    def GetName(self):
        return 'array'

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


class El(object):
    def __init__(self, world, kind, name, **attrs):
        self.world = world
        self.kind = kind
        self.name = name
        self.h = world.new_handle()
        world.by_handle[self.h] = self
        self.attrs = {}
        self.order = []
        for k in sorted(attrs):
            self.set(k, attrs[k])

    def GetHandle(self):
        return self.h

    def GetTypeString(self):
        return self.kind

    def GetName(self):
        return self.name

    def HasAttribute(self, name):
        return key(name) in self.attrs

    def GetAttribute(self, name):
        return self.attrs.get(key(name))

    def FirstAttribute(self):
        return self.attrs[self.order[0]] if self.order else None

    def set(self, name, value):
        if isinstance(value, list) and value and all(isinstance(x, El) for x in value):
            value = ElementArray(self.world, value)
        if name in self.attrs:
            self.attrs[name].value = value
        else:
            self.attrs[name] = Attr(self, name, value)
            self.order.append(name)

    def get(self, name):
        v = self.attrs[name].value
        return v.items if isinstance(v, ElementArray) else v


class Dag(El):
    def __init__(self, world, kind, name, **attrs):
        El.__init__(self, world, kind, name, **attrs)
        if 'children' not in self.attrs:
            self.set('children', ElementArray(world, []))
        self.world_xf = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])

    def add_child(self, child):
        self.attrs['children'].value.items.append(child)

    def GetAbsPosition(self):
        self.world.check_poison(self, 'GetAbsPosition')
        return Vector(*self.world_xf[0])

    def GetAbsOrientation(self):
        self.world.check_poison(self, 'GetAbsOrientation')
        return Quaternion(*self.world_xf[1])


class Layer(El):
    def __init__(self, world, kind, name, keys):
        El.__init__(self, world, kind, name)
        self.keys = [[int(t), v] for t, v in keys]

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, i):
        self.world.check_poison(self, 'GetKeyTime')
        return Time(self.keys[i][0])

    def GetKeyValue(self, i):
        self.world.check_poison(self, 'GetKeyValue')
        return mk(self.keys[i][1], 'Quaternion' in self.kind)

    def SetKeyValue(self, i, value):
        self.world.set_key(self, int(i), value)


class Log(El):
    def __init__(self, world, kind, name, layers, **attrs):
        El.__init__(self, world, kind, name, **attrs)
        self.layers = layers
        self.set('layers', ElementArray(world, layers))

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, i):
        return self.layers[i]

    def GetValue(self, t):
        self.world.check_poison(self, 'Log.GetValue')
        keys = self.layers[0].keys
        ticks = t.ticks
        quaternion = 'Quaternion' in self.kind
        if not keys:
            return mk(self.get('defaultvalue'), quaternion)
        if ticks <= keys[0][0]:
            return mk(keys[0][1], quaternion)
        for i in range(len(keys) - 1):
            a, b = keys[i], keys[i + 1]
            if a[0] <= ticks <= b[0]:
                if a[1] == b[1] or b[0] == a[0]:
                    return mk(a[1], quaternion)
                u = (ticks - a[0]) / float(b[0] - a[0])
                if isinstance(a[1], list):
                    return mk([a[1][k] + (b[1][k] - a[1][k]) * u for k in range(len(a[1]))], quaternion)
                return a[1] + (b[1] - a[1]) * u
        return mk(keys[-1][1], quaternion)


class Channel(El):
    def __init__(self, world, name, shot, log, **attrs):
        El.__init__(self, world, 'DmeChannel', name, log=log, **attrs)
        self.log = log
        self.shot = shot

    def GetLog(self):
        return self.log

    def GetCurrentTime(self):
        self.world.check_poison(self, 'GetCurrentTime')
        return Time(self.world.channel_ticks(self.shot))


class Clip(El):
    def __init__(self, world, kind, name, offset_ticks, start_ticks=0, end_ticks=0, **attrs):
        El.__init__(self, world, kind, name, **attrs)
        self.offset = offset_ticks
        self.start = start_ticks
        self.end = end_ticks

    def ToChildMediaTime(self, t, clamp):
        assert clamp is False
        return Time(t.ticks - self.start + self.offset)

    def GetStartTime(self):
        return Time(self.start)

    def GetEndTime(self):
        return Time(self.end)


# --------------------------------------------------------------------------
# Data model with a journalled Undo stack (W1 fake semantics)
# --------------------------------------------------------------------------

class DataModel(object):
    def __init__(self, world):
        self.world = world
        self.enabled = True
        self.stack = []
        self.redo = []
        self.current = None
        self.calls = []

    def GetFileName(self, file_id):
        return self.world.doc_path

    def IsUndoEnabled(self):
        return self.enabled

    def UndoEnabledForElement(self, element):
        return self.enabled

    def CanUndo(self):
        return bool(self.stack)

    def CanRedo(self):
        return bool(self.redo)

    def GetUndoDesc(self):
        if self.world.mangle_undo_desc and self.stack:
            return 'something else'
        return self.stack[-1]['undo'] if self.stack else ''

    def GetRedoDesc(self):
        return self.redo[-1]['redo'] if self.redo else ''

    def GetUndoItemCount(self):
        return sum(len(e['items']) for e in self.stack)

    def ItemsAddedToCurrentUndo(self):
        return bool(self.current and self.current['items'])

    def StartUndo(self, undo, redo):
        self.calls.append(('StartUndo', key(undo), key(redo)))
        assert self.current is None, 'nested transaction in test'
        self.current = {'undo': key(undo), 'redo': key(redo), 'items': []}

    def record(self, layer, index, old, new):
        if self.current is not None:
            self.current['items'].append((layer, index, old, new))
            if self.world.unreadable_after_writes and \
                    len(self.current['items']) == self.world.unreadable_after_writes[0]:
                self.world.unreadable |= self.world.unreadable_after_writes[1]

    def FinishUndo(self):
        self.calls.append(('FinishUndo',))
        if self.current['items']:
            self.stack.append(self.current)
            self.redo = []
        self.current = None

    def AbortUndoableOperation(self):
        self.calls.append(('AbortUndoableOperation',))
        if self.world.abort_raises:
            raise RuntimeError('abort failed (test)')
        self.world.unreadable |= self.world.unreadable_on_abort
        if not self.world.abort_broken:
            for layer, index, old, new in reversed(self.current['items']):
                layer.keys[index][1] = old
        self.current = None

    def Undo(self):
        self.calls.append(('Undo',))
        self.world.unreadable |= self.world.unreadable_on_undo
        entry = self.stack.pop()
        if not self.world.undo_broken:
            for layer, index, old, new in reversed(entry['items']):
                if layer is not None:
                    layer.keys[index][1] = old
        self.redo.append(entry)

    def Redo(self):
        self.calls.append(('Redo',))
        self.world.unreadable |= self.world.unreadable_on_redo
        entry = self.redo.pop()
        for layer, index, old, new in entry['items']:
            if layer is not None:
                layer.keys[index][1] = new
        self.stack.append(entry)

    def push_foreign(self, desc):
        """A user's own Undo entry with no authored effect (test helper)."""
        self.stack.append({'undo': desc, 'redo': desc + ' redo', 'items': [(None, None, None, None)]})
        self.redo = []


# --------------------------------------------------------------------------
# Qt
# --------------------------------------------------------------------------

class Signal(object):
    def __init__(self):
        self.slots = []

    def connect(self, fn):
        self.slots.append(fn)


def make_qt(world):
    class QTimer(object):
        def __init__(self):
            self.timeout = Signal()
            self.single = False

        def setSingleShot(self, flag):
            self.single = flag

        def start(self, ms):
            world.queue.append(self)

    class QThread(object):
        @staticmethod
        def currentThread():
            return 'main'

    class App(object):
        def thread(self):
            return 'main'

        def activeModalWidget(self):
            return world.modal

        def topLevelWidgets(self):
            return []

    class QApplication(object):
        @staticmethod
        def instance():
            return App()

    core = types.ModuleType('PySide.QtCore')
    core.QTimer = QTimer
    core.QThread = QThread
    gui = types.ModuleType('PySide.QtGui')
    gui.QApplication = QApplication
    pkg = types.ModuleType('PySide')
    pkg.QtCore = core
    pkg.QtGui = gui
    return pkg, core, gui


# --------------------------------------------------------------------------
# Process identity (fake kernel32)
# --------------------------------------------------------------------------

class FakeProcesses(object):
    """pid -> {'creation_filetime', 'running', 'image'}; a shared monotonic clock."""
    name = 'offline-fake'

    def __init__(self, table, current_pid, clock):
        self.table = table
        self.current_pid = current_pid
        self.clock = clock

    def now(self):
        self.clock[0] += 1
        return self.clock[0]

    def current(self):
        row = dict(self.table[self.current_pid])
        row['pid'] = self.current_pid
        return row

    def lookup(self, pid):
        """Strict lookup, as WindowsProcesses: None only for an absent id; a row marked 'denied' raises (an
        unresolved query, like OpenProcess ERROR_ACCESS_DENIED)."""
        row = self.table.get(pid)
        if row is None:
            return None
        if row.get('denied'):
            raise RuntimeError('OpenProcess(%d) failed (5); the process state is unknown (offline fake)' % pid)
        row = dict(row)
        row['pid'] = pid
        return row

    def images(self):
        """Best effort, as WindowsProcesses: running processes that can be opened."""
        return [(pid, row['image']) for pid, row in sorted(self.table.items())
                if row['running'] and not row.get('denied')]


# --------------------------------------------------------------------------
# World: the synthetic document
# --------------------------------------------------------------------------

class ShotData(object):
    pass


class World(object):
    def __init__(self, doc_path, handle_base=900000, poison_source=False, scene=None):
        self.scene_spec = scene or load_scene()
        self.by_handle = {}
        self.next_handle = [handle_base]
        self.unreadable = set()
        self.queue = []
        self.modal = None
        self.policy = 'idle'
        self.abort_broken = False
        self.abort_raises = False
        self.undo_broken = False
        self.mangle_undo_desc = False
        self.ignore_writes = False
        self.perturb_layer = None
        self.raise_on_write = False
        self.oracle_disagreement = False
        self.shift_unrelated_bone = None
        self.unreadable_on_abort = set()
        self.unreadable_on_undo = set()
        self.unreadable_on_redo = set()
        self.unreadable_after_writes = None
        self.poisoned = set()
        self.poison_hits = []
        # Every pose-value read passes check_poison: read_hook(n) runs after the
        # n-th such read (used to change the scene in the middle of a step).
        self.read_count = 0
        self.read_hook = None
        # (shot, offset): Hand_l handle position corrupted AFTER evaluation, so
        # the rig input no longer equals its log (effective/log disagreement).
        self.input_offset = None
        self.doc_path = doc_path
        self.model = self.scene_spec['model']
        self.dm = DataModel(self)
        self.shots = {}
        for name in ('shot15', 'shot10'):
            self.shots[name] = self.build_shot(name)
        self.head = self.shots['shot15'].frame_head
        track = El(self, 'DmeTrack', 'Film', children=[self.shots['shot15'].clip, self.shots['shot10'].clip])
        group = El(self, 'DmeTrackGroup', 'subClipTrackGroup', tracks=[track])
        self.movie = Clip(self, 'DmeFilmClip', 'movie', 0, subClipTrackGroup=group,
                          trackGroups=ElementArray(self, []))
        self.document = El(self, 'DmElement', 'session')
        self.document.GetFileId = lambda: 7
        for s in self.shots.values():
            self.evaluate(s)
        if poison_source:
            self.poisoned = set(e.h for e in self.shots['shot15'].pose_elements)
            assert len(self.poisoned) == len(self.shots['shot15'].pose_elements)

    def new_handle(self):
        self.next_handle[0] += 1
        return self.next_handle[0]

    def check_poison(self, element, what):
        self.read_count += 1
        if self.read_hook is not None:
            hook, self.read_hook = self.read_hook, None
            if not hook(self.read_count):
                self.read_hook = hook
        if element.h in self.poisoned:
            self.poison_hits.append((element.kind, element.name, what))
            raise PoisonedRead('source-pose read in process B: %s %s %s' % (element.kind, element.name, what))

    # ---- construction --------------------------------------------------------
    def build_shot(self, name):
        spec = self.scene_spec['shots'][name]
        S = ShotData()
        S.name = name
        S.spec = spec
        S.frame_head = spec['frame_ticks']
        S.pose_elements = []
        bones = self.scene_spec['bones']
        S.bone_specs = dict((b['name'], b) for b in bones)
        S.bone_transforms, S.bone_dags = {}, {}
        for b in bones:
            q = spec['spine_orientations'].get(b['name'], [0.0, 0.0, 0.0, 1.0])
            t = El(self, 'DmeTransform', 'bone %d (%s)' % (b['index'], b['name']),
                   position=Vector(*b['local_position']), orientation=Quaternion(*q))
            dag = Dag(self, 'DmeDag', b['name'], transform=t)
            S.bone_transforms[b['name']] = t
            S.bone_dags[b['name']] = dag
            S.pose_elements += [t, dag]
        gm_t = El(self, 'DmeTransform', 'krystal2020_GameModel', position=Vector(), orientation=Quaternion())
        gm = Dag(self, 'DmeGameModel', 'krystal2020_GameModel', transform=gm_t, modelName=self.model,
                 bones=ElementArray(self, [S.bone_transforms[b['name']] for b in bones]))
        S.gm = gm
        S.pose_elements += [gm, gm_t]
        for b in bones:
            parent = gm if b['parent'] is None else S.bone_dags[b['parent']]
            parent.add_child(S.bone_dags[b['name']])
        rig_t = El(self, 'DmeTransform', 'rig_transform', position=Vector(), orientation=Quaternion())
        rig = Dag(self, 'DmeRig', 'rig_Krystal', transform=rig_t)
        S.handles = {}
        for hname in ('rig_root', 'spine_4', 'CollarL', 'Hand_l', 'Elbow_l'):
            h = spec['handles'][hname]
            t = El(self, 'DmeTransform', hname, position=Vector(*h['position']),
                   orientation=Quaternion(*h['orientation']))
            S.handles[hname] = Dag(self, 'DmeRigHandle', hname, transform=t)
            S.pose_elements += [t, S.handles[hname]]
        rig.add_child(S.handles['rig_root'])
        S.handles['rig_root'].add_child(S.handles['spine_4'])
        S.handles['spine_4'].add_child(S.handles['CollarL'])
        S.handles['rig_root'].add_child(S.handles['Hand_l'])
        S.handles['rig_root'].add_child(S.handles['Elbow_l'])
        S.handle_parent = {'rig_root': None, 'spine_4': 'rig_root', 'CollarL': 'spine_4', 'Hand_l': 'rig_root',
                           'Elbow_l': 'rig_root'}
        scene = Dag(self, 'DmeDag', 'scene')
        scene.add_child(gm)
        scene.add_child(rig)
        # Controls and channels (bracket keys at 30000 / 70415 hold the spec value).
        S.channels, controls = [], []
        for owner in ('Hand_l', 'Elbow_l', 'CollarL', 'spine_4'):
            h = spec['handles'][owner]
            control = El(self, 'DmeTransformControl', owner, valuePosition=Vector(*h['position']),
                         valueOrientation=Quaternion(*h['orientation']))
            controls.append(control)
            S.pose_elements.append(control)
            for suffix, attr_name, src, value, kind in (('_p', 'position', 'valuePosition', h['position'], 'Vector3'),
                                                        ('_o', 'orientation', 'valueOrientation',
                                                         h['orientation'], 'Quaternion')):
                cname = owner + suffix
                keys = [[30000, list(value)], [70415, list(value)]]
                keys += [[t, list(v)] for t, v in spec.get('extra_keys', {}).get(cname, [])]
                keys.sort(key=lambda k: k[0])
                layer = Layer(self, 'Dme%sLogLayer' % kind, cname + '_layer', keys)
                log = Log(self, 'Dme%sLog' % kind, cname + '_log', [layer], usedefaultvalue=False,
                          defaultvalue=mk(list(value)), curveinfo=None)
                ch = Channel(self, cname, S, log, fromElement=control, fromAttribute=src, fromIndex=0,
                             toElement=S.handles[owner].get('transform'), toAttribute=attr_name, toIndex=0, mode=3)
                control.set(('positionChannel' if suffix == '_p' else 'orientationChannel'), ch)
                S.channels.append(ch)
                S.pose_elements += [layer, log, ch]
        flex_target = El(self, 'DmElement', 'Muscles_flex', flexWeight=0.25)
        flex_control = El(self, 'DmElement', 'Muscles', value=0.25)
        flex_layer = Layer(self, 'DmeFloatLogLayer', 'Muscles_layer', [[30000, 0.25], [70415, 0.25]])
        flex_log = Log(self, 'DmeFloatLog', 'Muscles_log', [flex_layer], usedefaultvalue=False, defaultvalue=0.0,
                       curveinfo=None)
        flex_ch = Channel(self, 'Muscles', S, flex_log, fromElement=flex_control, fromAttribute='value',
                          fromIndex=0, toElement=flex_target, toAttribute='flexWeight', toIndex=0, mode=3)
        flex_control.set('channel', flex_ch)
        controls.append(flex_control)
        S.channels.append(flex_ch)
        S.pose_elements += [flex_target, flex_control, flex_layer, flex_log, flex_ch]
        # Constraint operators.
        ops = []

        def slave(target):
            return El(self, 'DmeConstraintSlave', 'slave', target=target)

        def target_of(handle_name, weight=1.0):
            return El(self, 'DmeConstraintTarget', handle_name, target=S.handles[handle_name], targetWeight=weight,
                      oOffset=Quaternion(), vecOffset=Vector())
        ik = El(self, 'DmeRigIKConstraintOperator', 'ik_Hand_l', slave=slave(None),
                startJoint=slave(S.bone_dags['bip_UpperArm_l']), midJoint=slave(S.bone_dags['bip_lowerArm_l']),
                endJoint=slave(S.bone_dags['bip_hand_l']), pvTarget=S.handles['Elbow_l'],
                startOffset=Quaternion(), midOffset=Quaternion(), poleVector=Vector(0.0, 0.0, 1.0), mode=0)
        ik.set('targets', [target_of('Hand_l')])
        hand_orient = El(self, 'DmeRigOrientConstraintOperator', 'orient_hand_l', slave=slave(S.bone_dags['bip_hand_l']))
        hand_orient.set('targets', [target_of('Hand_l')])
        collar_point = El(self, 'DmeRigPointConstraintOperator', 'point_collar_l',
                          slave=slave(S.bone_dags['bip_collar_l']))
        collar_point.set('targets', [target_of('CollarL')])
        collar_orient = El(self, 'DmeRigOrientConstraintOperator', 'orient_collar_l',
                           slave=slave(S.bone_dags['bip_collar_l']))
        collar_orient.set('targets', [target_of('CollarL')])
        other = El(self, 'DmeRigOrientConstraintOperator', 'orient_collar_r', slave=slave(S.bone_dags['bip_collar_r']))
        other.set('targets', [target_of('spine_4')])
        ops = [ik, hand_orient, collar_point, collar_orient, other]
        S.ops = ops
        S.controls = controls
        animset = El(self, 'DmeAnimationSet', self.scene_spec['animation_set'], gameModel=gm,
                     controls=ElementArray(self, controls), operators=ElementArray(self, ops))
        owned = list(S.handles.values()) + list(S.channels) + controls
        reg = El(self, 'DmeRigAnimSetElements', 'Krystal_registration', animationSet=animset,
                 elementList=ElementArray(self, owned))
        rig.set('animSetList', ElementArray(self, [reg]))
        clip = Clip(self, 'DmeChannelsClip', 'Krystal', 50000, channels=ElementArray(self, list(S.channels)))
        track = El(self, 'DmeTrack', 'animSetEditorChannels', children=[clip])
        group = El(self, 'DmeTrackGroup', 'channelTrackGroup', tracks=[track])
        S.clip = Clip(self, 'DmeFilmClip', name, -208, spec['start_ticks'], spec['end_ticks'],
                      animationSets=ElementArray(self, [animset]), scene=scene, trackGroups=[group],
                      operators=ElementArray(self, []))
        S.channels_clip = clip
        S.animset = animset
        S.extra_channels = []
        return S

    # ---- evaluation ----------------------------------------------------------
    def current_shot(self):
        for S in self.shots.values():
            if S.spec['start_ticks'] < self.head < S.spec['end_ticks']:
                return S
        return None

    def channel_ticks(self, S):
        head = self.head if self.current_shot() is S else S.frame_head
        return head - S.clip.start - 208 + 50000

    def evaluate(self, S):
        for ch in S.channels + S.extra_channels:
            if int(ch.get('mode')) != 3:
                continue
            ticks = self.channel_ticks(S)
            value = ch.log.GetValue(Time(ticks)) if ch.h not in self.poisoned else self.raw_value(ch.log, ticks)
            target = ch.get('toElement')
            if target is not None:
                target.set(ch.get('toAttribute'), value)
        world_of = {}

        def handle_world(name):
            if name in world_of:
                return world_of[name]
            t = S.handles[name].get('transform')
            local = xf(as_list(t.get('position')), as_list(t.get('orientation')))
            parent = S.handle_parent[name]
            w = local if parent is None else xf_mul(handle_world(parent), local)
            world_of[name] = w
            S.handles[name].world_xf = (w[0], m_to_q(w[1]))
            return w
        for name in S.handles:
            handle_world(name)
        bone_world = {}
        gm_world = xf([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
        C = world_of['CollarL']
        arm = self.solve_arm(S, C, world_of)

        def bone(name):
            if name in bone_world:
                return bone_world[name]
            b = S.bone_specs[name]
            parent_w = gm_world if b['parent'] is None else bone(b['parent'])
            t = S.bone_transforms[name]
            # Constrained bones: the spine_4 bone follows the spine_4 rig handle
            # and the collar bone follows CollarL (point + orient), so their
            # model-defined local offsets are preserved as in the native rig.
            if name == 'bip_spine_4':
                w = world_of['spine_4']
            elif name == 'bip_collar_l':
                w = C
            elif name in arm:
                w = xf_mul(C, arm[name])
            else:
                w = xf_mul(parent_w, xf(as_list(t.get('position')), as_list(t.get('orientation'))))
            local = xf_mul(xf_inv(parent_w), w)
            if name in arm or name in ('bip_collar_l', 'bip_spine_4'):
                t.set('orientation', Quaternion(*m_to_q(local[1])))
                t.set('position', Vector(*local[0]))
            bone_world[name] = w
            S.bone_dags[name].world_xf = (w[0], m_to_q(w[1]))
            return w
        for name in S.bone_specs:
            bone(name)
        if self.input_offset is not None and S.name == self.input_offset[0]:
            t = S.handles['Hand_l'].get('transform')
            p = as_list(t.get('position'))
            t.set('position', Vector(p[0] + self.input_offset[1], p[1], p[2]))
        if self.shift_unrelated_bone and S.name == 'shot10':
            # An unrelated bone's local position moves while the arm is transferred.
            t = S.bone_transforms[self.shift_unrelated_bone]
            base = S.bone_specs[self.shift_unrelated_bone]['local_position']
            t.set('position', Vector(*(add(base, [0.5, 0.0, 0.0]) if self.transferred(S) else base)))
        if self.oracle_disagreement and S.name == 'shot10' and self.transferred(S):
            dag = S.bone_dags['bip_lowerArm_l']
            dag.world_xf = (add(dag.world_xf[0], [0.2, 0.0, 0.0]), dag.world_xf[1])

    def raw_value(self, log, ticks):
        saved = self.poisoned
        self.poisoned = set()
        try:
            return log.GetValue(Time(ticks))
        finally:
            self.poisoned = saved

    def solve_arm(self, S, C, world_of):
        inv_c = xf_inv(C)
        hand_c = xf_mul(inv_c, world_of['Hand_l'])
        elbow_c = xf_mul(inv_c, world_of['Elbow_l'])
        u0 = S.bone_specs['bip_UpperArm_l']['local_position']
        len1 = S.bone_specs['bip_lowerArm_l']['local_position'][0]
        len2 = S.bone_specs['bip_hand_l']['local_position'][0]
        return solve_arm_collar_frame(u0, len1, len2, hand_c[0], hand_c[1], elbow_c[0])

    def transferred(self, S):
        t = S.handles['Hand_l'].get('transform')
        return as_list(t.get('position')) != S.spec['handles']['Hand_l']['position']

    # ---- native writes -------------------------------------------------------
    def set_key(self, layer, index, value):
        if self.raise_on_write:
            raise RuntimeError('native write failed (test)')
        if self.ignore_writes:
            return
        new = as_list(value)
        new = [f32(c) for c in new] if isinstance(new, list) else f32(new)
        if self.perturb_layer is not None and layer.h == self.perturb_layer:
            new = [c + 0.25 for c in new]
        old = layer.keys[index][1]
        layer.keys[index][1] = new
        self.dm.record(layer, index, old, new)

    # ---- test helpers --------------------------------------------------------
    def add_channel(self, shot, name, to_element, to_attribute, mode=0):
        S = self.shots[shot]
        layer = Layer(self, 'DmeVector3LogLayer', name + '_layer', [[30000, [0.0, 0.0, 0.0]]])
        log = Log(self, 'DmeVector3Log', name + '_log', [layer], usedefaultvalue=False,
                  defaultvalue=Vector(), curveinfo=None)
        source = El(self, 'DmElement', name + '_source', value=Vector())
        ch = Channel(self, name, S, log, fromElement=source, fromAttribute='value', fromIndex=0,
                     toElement=to_element, toAttribute=to_attribute, toIndex=0, mode=mode)
        S.channels_clip.attrs['channels'].value.items.append(ch)
        return ch

    def channel(self, shot, name):
        return [c for c in self.shots[shot].channels if c.name == name][0]

    def set_frame(self, frame):
        self.head = FRAME_TICKS[frame]
        if self.policy in ('idle', 'retime'):
            self.evaluate(self.current_shot())

    def run_events(self):
        while self.queue:
            timer = self.queue.pop(0)
            if self.policy == 'idle' and self.current_shot() is not None:
                self.evaluate(self.current_shot())
            for slot in timer.timeout.slots:
                slot()

    def modules(self):
        world = self
        sfm = types.ModuleType('sfmApp')
        sfm.HasDocument = lambda: True
        sfm.GetDocumentRoot = lambda: world.document
        sfm.GetMovie = lambda: world.movie
        sfm.GetShotAtCurrentTime = lambda: (world.current_shot().clip if world.current_shot() else None)
        sfm.GetHeadTimeInSeconds = lambda: world.head / float(TICKS)
        vs = types.ModuleType('vs')
        vs.g_pDataModel = world.dm
        vs.DmeTime_t = DmeTime_t
        vs.Vector = Vector
        vs.Quaternion = Quaternion
        pkg, core, gui = make_qt(world)
        return {'sfmApp': sfm, 'vs': vs, 'PySide': pkg, 'PySide.QtCore': core, 'PySide.QtGui': gui}
