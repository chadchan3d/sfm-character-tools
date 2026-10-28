# -*- coding: ascii -*-
"""Offline stand-ins for the SFM native modules (sfmApp, vs, PySide) used by the
F-01 W1 harness tests. Python 2.7 and 3.

The fake document is built from the actual R3 shot15/shot10 captures: real
bone, rig-handle, control, constraint and channel identities, transforms, key
times and key values. A small rig solver stands in for SFM evaluation. It is a
lookup (baseline inputs -> captured skeleton; transferred inputs -> the test's
independently computed transferred skeleton; anything else -> a perturbed arm),
so the tests exercise the harness's control flow, evidence and verdicts. They do
not demonstrate native SFM behaviour.
"""
import math
import struct
import types

TICKS = 10000
FRAME_TICKS = {5: 2083, 10: 4167, 11: 4583}


def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def key(name):
    if isinstance(name, bytes) and not isinstance(name, str):
        return name.decode('utf-8')
    if isinstance(name, bytes):  # Python 2 str
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
# Rigid math for the fake rig (independent of the harness implementation:
# 3x3 rotation matrices)
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
        return [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    if m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        return [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]
    if m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        return [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]
    s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
    return [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]


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


def rotate_about_x(q, degrees):
    h = math.radians(degrees) / 2.0
    r = [math.sin(h), 0.0, 0.0, math.cos(h)]
    x1, y1, z1, w1 = q
    x2, y2, z2, w2 = r
    return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]


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
        if (self.owner.GetHandle(), self.name) in self.owner.world.unreadable:
            raise RuntimeError('unreadable attribute (test)')
        return self.value

    def GetValueUntyped(self):
        raise RuntimeError('untyped read unavailable')

    def NextAttribute(self):
        order = self.owner.order
        i = order.index(self.name)
        return self.owner.attrs[order[i + 1]] if i + 1 < len(order) else None


class ElementArray(object):
    """The native element_array wrapper: its own handle, list semantics."""

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
    def __init__(self, world, kind, name, h=None, **attrs):
        self.world = world
        self.kind = kind
        self.name = name
        self.h = world.new_handle() if h is None else int(h)
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
    def __init__(self, world, kind, name, h=None, world_pos=None, world_quat=None, **attrs):
        El.__init__(self, world, kind, name, h, **attrs)
        if 'children' not in self.attrs:
            self.set('children', ElementArray(world, []))
        self.world_xf = (list(world_pos or [0.0, 0.0, 0.0]), list(world_quat or [0.0, 0.0, 0.0, 1.0]))
        self.parent = None

    def add_child(self, child):
        arr = self.attrs['children'].value
        arr.items.append(child)
        child.parent = self

    def GetAbsPosition(self):
        return Vector(*self.world_xf[0])

    def GetAbsOrientation(self):
        return Quaternion(*self.world_xf[1])


class Layer(El):
    def __init__(self, world, kind, name, h, keys):
        El.__init__(self, world, kind, name, h)
        self.keys = [[int(t), v] for t, v in keys]

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, i):
        return Time(self.keys[i][0])

    def GetKeyValue(self, i):
        return mk(self.keys[i][1], 'Quaternion' in self.kind)

    def SetKeyValue(self, i, value):
        self.world.set_key(self, int(i), value)


class Log(El):
    def __init__(self, world, kind, name, h, layers, **attrs):
        El.__init__(self, world, kind, name, h, **attrs)
        self.layers = layers
        self.set('layers', ElementArray(world, layers))

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, i):
        return self.layers[i]

    def IsEmpty(self):
        return all(not l.keys for l in self.layers)

    def GetValue(self, t):
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
    def __init__(self, world, name, h, shot, log, current_offset, **attrs):
        El.__init__(self, world, 'DmeChannel', name, h, log=log, **attrs)
        self.log = log
        self.shot = shot
        self.current_offset = current_offset

    def GetLog(self):
        return self.log

    def GetCurrentTime(self):
        return Time(self.world.channel_ticks(self.shot) + self.current_offset)


class Clip(El):
    def __init__(self, world, kind, name, offset_ticks, start_ticks=0, end_ticks=0, h=None, **attrs):
        El.__init__(self, world, kind, name, h, **attrs)
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
# Data model with a journalled Undo stack
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
        if self.world.offset_after_finish is not None:
            self.world.input_offset = self.world.offset_after_finish
        if self.current['items']:
            self.stack.append(self.current)
            self.redo = []
        self.current = None

    def AbortUndoableOperation(self):
        self.calls.append(('AbortUndoableOperation',))
        if self.world.offset_after_abort is not None:
            self.world.input_offset = self.world.offset_after_abort
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
                layer.keys[index][1] = old
        self.redo.append(entry)

    def Redo(self):
        self.calls.append(('Redo',))
        self.world.unreadable |= self.world.unreadable_on_redo
        entry = self.redo.pop()
        for layer, index, old, new in entry['items']:
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
# World: the fake document built from R3 captures
# --------------------------------------------------------------------------

def rv(record):
    return record.get('value') if isinstance(record, dict) and 'status' in record else record


class ShotData(object):
    pass


class World(object):
    def __init__(self, r3_source, r3_destination, doc_path, model):
        self.by_handle = {}
        self.next_handle = [900000]
        self.unreadable = set()
        self.queue = []
        self.modal = None
        self.policy = 'idle'
        self.abort_broken = False
        self.undo_broken = False
        self.mangle_undo_desc = False
        self.ignore_writes = False
        self.perturb_layer = None
        self.eval_on_write = False
        self.oracle_disagreement = False
        self.shift_unrelated_bone = None
        self.raise_on_write = False
        # Rig-input corruption applied AFTER the solver (skeleton unaffected): a
        # Hand_l handle position offset, optionally activated by the first abort.
        self.input_offset = None
        self.offset_after_abort = None
        self.offset_after_finish = None
        self.unreadable_on_abort = set()
        self.unreadable_on_undo = set()
        self.unreadable_on_redo = set()
        # (n, attributes): the attributes become unreadable once an open transaction holds n writes.
        self.unreadable_after_writes = None
        self.doc_path = doc_path
        self.model = model
        self.dm = DataModel(self)
        self.head = FRAME_TICKS[5]
        self.shots = {}
        self.shots['shot15'] = self.build_shot(r3_source, 'shot15', 1667, 2917)
        self.shots['shot10'] = self.build_shot(r3_destination, 'shot10', 3751, 5001)
        track = El(self, 'DmeTrack', 'Film', children=[self.shots['shot15'].clip, self.shots['shot10'].clip])
        group = El(self, 'DmeTrackGroup', 'subClipTrackGroup', tracks=[track])
        self.movie = Clip(self, 'DmeFilmClip', 'movie', 0, subClipTrackGroup=group,
                          trackGroups=ElementArray(self, []))
        self.document = El(self, 'DmElement', 'session')
        self.document.GetFileId = lambda: 0
        for s in self.shots.values():
            self.evaluate(s)

    def new_handle(self):
        self.next_handle[0] += 1
        return self.next_handle[0]

    # ---- construction from an R3 capture --------------------------------
    def build_shot(self, r3, name, start, end):
        st = r3['state']
        S = ShotData()
        S.name = name
        S.frame_head = FRAME_TICKS[5] if name == 'shot15' else FRAME_TICKS[10]
        S.r3 = st
        bones_t = []
        for b in st['bone_transforms']:
            attrs = {'position': mk(rv(b['fields']['position'])),
                     'orientation': mk(rv(b['fields']['orientation']))}
            if b['fields']['scale'].get('status') == 'READ':
                attrs['scale'] = rv(b['fields']['scale'])
            bones_t.append(El(self, 'DmeTransform', b['identity']['name'], b['identity']['handle'], **attrs))
        S.bone_dags = {}
        for d in st['skeletal_dags']:
            t = self.by_handle[d['transform']['handle']]
            dag = Dag(self, 'DmeDag', d['identity']['name'], d['identity']['handle'],
                      rv(d['absolute_position']), rv(d['absolute_orientation']), transform=t)
            S.bone_dags[d['identity']['handle']] = (dag, d)
        mp = st['model_placement']
        gm_t = El(self, 'DmeTransform', mp['transform']['name'], mp['transform']['handle'],
                  position=mk(rv(mp['local']['position'])), orientation=mk(rv(mp['local']['orientation'])))
        gm = Dag(self, 'DmeGameModel', mp['identity']['name'], mp['identity']['handle'],
                 rv(mp['absolute_position']), rv(mp['absolute_orientation']),
                 transform=gm_t, modelName=self.model, bones=ElementArray(self, bones_t))
        S.gm = gm
        for h, (dag, d) in S.bone_dags.items():
            parent = d['parents'][0] if d['parents'] else None
            if parent in S.bone_dags:
                S.bone_dags[parent][0].add_child(dag)
            else:
                gm.add_child(dag)
        rt = st['rig_transforms'][0]
        rig = Dag(self, 'DmeRig', rt['identity']['name'], rt['identity']['handle'],
                  transform=El(self, 'DmeTransform', 'unnamed', rt['transform']['handle'],
                               position=Vector(), orientation=Quaternion()))
        S.handles = {}
        for r in st['rig_handles']:
            t = El(self, 'DmeTransform', r['transform']['name'], r['transform']['handle'],
                   position=mk(rv(r['local']['position'])), orientation=mk(rv(r['local']['orientation'])))
            S.handles[r['identity']['name']] = Dag(self, 'DmeRigHandle', r['identity']['name'],
                                                   r['identity']['handle'], rv(r['absolute_position']),
                                                   rv(r['absolute_orientation']), transform=t)
        by_h = dict((d.h, d) for d in S.handles.values())
        for r in st['rig_handles']:
            dag = S.handles[r['identity']['name']]
            parent = r['parents'][0] if r['parents'] else None
            (by_h[parent] if parent in by_h else rig).add_child(dag)
        scene = Dag(self, 'DmeDag', 'scene', None, children=ElementArray(self, []))
        scene.add_child(gm)
        scene.add_child(rig)
        # Constraint dependencies (first pass: elements; refs resolved below).
        pending = []
        for d in st['constraint_dependencies']:
            el = El(self, d['identity']['type'], d['identity']['name'], d['identity']['handle'])
            pending.append((el, d['fields']))
        ops = []
        for o in st['operators']:
            el = El(self, o['identity']['type'], o['identity']['name'], o['identity']['handle'])
            ops.append(el)
            pending.append((el, o['fields']))
        # Weight channel names identify each operator's targets.
        op_targets = dict((o.name, []) for o in ops)
        for c in st['channels']:
            to = rv(c['binding']['toElement'])
            if to and to['type'] == 'DmeConstraintTarget' and ' - ' in c['identity']['name']:
                op_targets.setdefault(c['identity']['name'].split(' - ')[0], []).append(to['handle'])
        # Controls.
        controls = []
        for c in st['control_inventory']:
            el = El(self, c['identity']['type'], c['identity']['name'], c['identity']['handle'])
            controls.append(el)
            pending.append((el, c['fields']))
        # Channels, logs and layers.
        S.channels = []
        for c in st['channels']:
            layers = []
            for l in c['layers']:
                keys = [[int(round(rv(k['time'])['seconds'] * TICKS)), rv(k['value'])] for k in l['keys']]
                layers.append(Layer(self, l['identity']['type'], l['identity']['name'], l['identity']['handle'],
                                    keys))
            lf = c['log_fields']
            log = Log(self, c['log']['type'], c['log']['name'], c['log']['handle'], layers,
                      usedefaultvalue=rv(lf['usedefaultvalue']), defaultvalue=rv(lf['defaultvalue']),
                      curveinfo=None)
            nominal = int(round(c['nominal_mapping']['seconds'] * TICKS))
            current = int(round(rv(c['channel_time'])['seconds'] * TICKS))
            ch = Channel(self, c['identity']['name'], c['identity']['handle'], S, log, current - nominal)
            b = c['binding']
            for k in ('fromAttribute', 'fromIndex', 'toAttribute', 'toIndex', 'mode'):
                ch.set(k, rv(b[k]))
            S.channels.append((ch, b, c))
        S.pending = pending
        S.controls = controls
        S.ops = ops
        S.op_targets = op_targets
        S.scene = scene
        S.rig = rig
        # Second pass: resolve element references.
        for el, fields in pending:
            for k, rec in fields.items():
                if rec.get('status') != 'READ':
                    continue
                el.set(k, self.resolve_value(k, rv(rec), el))
        for o in ops:
            if o.kind in ('DmeRigIKConstraintOperator', 'DmeRigOrientConstraintOperator',
                          'DmeRigPointConstraintOperator'):
                o.set('targets', ElementArray(self, [self.by_handle[h] for h in op_targets.get(o.name, [])]))
        for ch, b, c in S.channels:
            for side in ('from', 'to'):
                ref = rv(b[side + 'Element'])
                el = self.by_handle.get(ref['handle']) if ref else None
                if ref and el is None:
                    el = El(self, ref['type'], ref['name'], ref['handle'])
                attr_name = rv(b[side + 'Attribute'])
                if el is not None and not el.HasAttribute(attr_name):
                    el.set(attr_name, mk(rv(c[side == 'from' and 'source_value' or 'destination_value'])))
                ch.set(side + 'Element', el)
        animset = El(self, 'DmeAnimationSet', st['animation_set']['name'], st['animation_set']['handle'],
                     gameModel=gm, controls=ElementArray(self, controls), operators=ElementArray(self, ops))
        reg_id = st['registration']['identity']
        owned = list(S.handles.values()) + [c for c, _, _ in S.channels] + controls
        reg = El(self, reg_id['type'], reg_id['name'], reg_id['handle'], animationSet=animset,
                 elementList=ElementArray(self, owned))
        rig.set('animSetList', ElementArray(self, [reg]))
        clip = Clip(self, 'DmeChannelsClip', 'Krystal', 50000,
                    channels=ElementArray(self, [c for c, _, _ in S.channels]))
        track = El(self, 'DmeTrack', 'animSetEditorChannels', children=[clip])
        group = El(self, 'DmeTrackGroup', 'channelTrackGroup', tracks=[track])
        S.clip = Clip(self, 'DmeFilmClip', name, -208, start, end, animationSets=ElementArray(self, [animset]),
                      scene=scene, trackGroups=[group], operators=ElementArray(self, []))
        S.channels_clip = clip
        S.animset = animset
        S.extra_channels = []
        # Solver tables: captured baseline arm.
        names = dict((d['identity']['name'], d) for d in st['skeletal_dags'])
        S.arm = {}
        for bone in ('bip_UpperArm_l', 'bip_lowerArm_l', 'bip_hand_l'):
            d = [x for n, x in names.items() if n.endswith('(%s)' % bone)][0]
            S.arm[bone] = d['identity']['handle']
        S.baseline_arm = dict((b, (rv(self.r3_local(st, h)), list(self.by_handle[h].world_xf[0]),
                                   list(self.by_handle[h].world_xf[1]))) for b, h in S.arm.items())
        S.baseline_inputs = self.inputs(S)
        S.transfer_inputs = None
        S.transfer_arm = None
        return S

    def r3_local(self, st, dag_handle):
        dag = self.by_handle[dag_handle]
        return as_list(dag.get('transform').get('orientation'))

    def resolve_value(self, name, value, owner):
        if isinstance(value, dict) and 'handle' in value and 'type' in value:
            if value['type'] == 'element_array':
                return None  # rebuilt explicitly (targets)
            el = self.by_handle.get(value['handle'])
            if el is None:
                el = El(self, value['type'], value['name'], value['handle'])
            return el
        if isinstance(value, list):
            quaternion = name in ('orientation', 'valueOrientation', 'oOffset', 'startOffset', 'midOffset')
            if len(value) == 4 and quaternion:
                return Quaternion(*value)
            if len(value) == 3 and name in ('position', 'valuePosition', 'vecOffset', 'poleVector'):
                return Vector(*value)
            if len(value) in (3, 4):
                return mk(value, quaternion)
        return value

    # ---- evaluation ----------------------------------------------------------
    def current_shot(self):
        if 1667 < self.head < 2917:
            return self.shots['shot15']
        if 3751 < self.head < 5001:
            return self.shots['shot10']
        return None

    def channel_ticks(self, S):
        # A shot that is not under the playhead keeps its last evaluated time.
        head = self.head if self.current_shot() is S else S.frame_head
        return head - S.clip.start - 208 + 50000

    def inputs(self, S):
        h, e = S.handles['Hand_l'].get('transform'), S.handles['Elbow_l'].get('transform')
        return (as_list(h.get('position')), as_list(h.get('orientation')), as_list(e.get('position')))

    def evaluate(self, S):
        for ch, _, _ in S.channels + [(c, None, None) for c in S.extra_channels]:
            if int(ch.get('mode')) != 3:
                continue
            value = ch.log.GetValue(ch.GetCurrentTime())
            target = ch.get('toElement')
            if target is not None:
                target.set(ch.get('toAttribute'), value)
        root = S.handles['rig_root']
        rig_world = xf([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])

        def recompute(dag, parent_world):
            t = dag.get('transform')
            local = xf(as_list(t.get('position')), as_list(t.get('orientation')))
            w = xf_mul(parent_world, local)
            dag.world_xf = (w[0], m_to_q(w[1]))
            for child in dag.get('children'):
                if child.kind == 'DmeRigHandle':
                    recompute(child, w)
        recompute(root, rig_world)
        self.solve_arm(S)
        if self.input_offset is not None and S.name == 'shot10':
            t = S.handles['Hand_l'].get('transform')
            p = as_list(t.get('position'))
            t.set('position', Vector(p[0] + self.input_offset, p[1], p[2]))

    def solve_arm(self, S):
        now = self.inputs(S)

        def close(a, b):
            return all(abs(a[i] - b[i]) <= 1e-4 for i in range(len(a))) or (
                len(a) == 4 and all(abs(a[i] + b[i]) <= 1e-4 for i in range(4)))
        if S.transfer_inputs and all(close(now[i], S.transfer_inputs[i]) for i in range(3)):
            table = S.transfer_arm
        elif all(close(now[i], S.baseline_inputs[i]) for i in range(3)):
            table = S.baseline_arm
        else:
            table = dict((b, (rotate_about_x(v[0], 2.0), v[1], v[2])) for b, v in S.baseline_arm.items())
        for bone, (local_q, wp, wq) in table.items():
            dag = self.by_handle[S.arm[bone]]
            dag.get('transform').set('orientation', Quaternion(*local_q))
            dag.world_xf = (list(wp), list(wq))
        if self.shift_unrelated_bone and S.name == 'shot10' and table is S.transfer_arm:
            dag = self.by_handle[self.shift_unrelated_bone]
            p = as_list(dag.get('transform').get('position'))
            dag.get('transform').set('position', Vector(p[0] + 0.5, p[1], p[2]))

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
        if self.eval_on_write:
            self.evaluate(self.current_shot())

    # ---- test helpers ----------------------------------------------------------
    def add_channel(self, shot, name, to_element, to_attribute, mode=0):
        S = self.shots[shot]
        layer = Layer(self, 'DmeVector3LogLayer', name + '_layer', None, [[30000, [0.0, 0.0, 0.0]]])
        log = Log(self, 'DmeVector3Log', name + '_log', None, [layer], usedefaultvalue=False,
                  defaultvalue=[0.0, 0.0, 0.0], curveinfo=None)
        source = El(self, 'DmElement', name + '_source', value=Vector())
        ch = Channel(self, name, None, S, log, 0, fromElement=source, fromAttribute='value', fromIndex=0,
                     toElement=to_element, toAttribute=to_attribute, toIndex=0, mode=mode)
        S.channels_clip.attrs['channels'].value.items.append(ch)
        return ch

    def channel(self, shot, name):
        return [c for c, _, _ in self.shots[shot].channels if c.name == name][0]

    # ---- operator actions --------------------------------------------------
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

    # ---- modules ---------------------------------------------------------------
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
