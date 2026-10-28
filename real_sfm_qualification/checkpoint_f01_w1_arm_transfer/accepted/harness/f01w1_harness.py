# -*- coding: ascii -*-
"""F-01 W1: one bounded, write-capable shot15 -> shot10 left-arm transfer experiment.

Controlling specification: Astra, F-01 Final Adjudication, 2026-10-27.

Owner-driven. Every step is ONE Script Editor submission of NEXT_STEP.txt. The
harness reads its own ledger (reports/), decides which single step is due,
verifies the playhead/shot that step requires, performs it and prints the exact
next instruction. Python 2.7 (SFM) and 3 syntax.

Native scene mutations used, and nowhere else:
  CDmeVector3LogLayer.SetKeyValue / CDmeQuaternionLogLayer.SetKeyValue
  IDataModel.StartUndo / FinishUndo / AbortUndoableOperation / Undo / Redo
No stored-control setters, Operate(), playhead changes, forced evaluation,
new keys, mode changes, skeletal writes, weight changes, graph edits, saves,
history clearing or compensating writes. Reports are new files only.
"""
import os
import sys
import json
import math
import re
import struct
import hashlib
import datetime
import traceback
import binascii

try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)

FORMAT = 'F01W1-v1'
BASE = os.path.dirname(os.path.abspath(__file__))
RUNTIME_MODULE = 'f01w1_runtime'
REPORT_RE = re.compile(r'^F01W1-(\d{2})-([A-Z0-9_]+)\.json$')

MAX_NODES = 4096
MAX_ARRAY = 8192
MAX_LAYER_KEYS = 50000
MAX_TOTAL_KEYS = 400000

ARM_BONES = ('bip_UpperArm_l', 'bip_lowerArm_l', 'bip_hand_l')
COLLAR_BONE = 'bip_collar_l'
HANDLE_NAMES = ('rig_root', 'CollarL', 'Hand_l', 'Elbow_l')
CONTROL_NAMES = ('Hand_l', 'Elbow_l', 'CollarL')
# (channel name, control/handle, control channel attribute, source attribute,
#  destination attribute, log type, layer type)
WRITE_CHANNELS = (
    ('Hand_l_p', 'Hand_l', 'positionChannel', 'valuePosition', 'position', 'DmeVector3Log', 'DmeVector3LogLayer'),
    ('Hand_l_o', 'Hand_l', 'orientationChannel', 'valueOrientation', 'orientation', 'DmeQuaternionLog',
     'DmeQuaternionLogLayer'),
    ('Elbow_l_p', 'Elbow_l', 'positionChannel', 'valuePosition', 'position', 'DmeVector3Log', 'DmeVector3LogLayer'),
)
# Observed, not written: the elbow orientation must stay exactly as it is.
OBSERVED_CHANNELS = (('Elbow_l_o', 'Elbow_l', 'orientationChannel'),)
KNOWN_OPERATORS = ('DmeExpressionOperator', 'DmePackColorOperator', 'DmeRigPointConstraintOperator',
                   'DmeRigOrientConstraintOperator', 'DmeRigIKConstraintOperator')
CONSTRAINT_OPERATORS = ('DmeRigPointConstraintOperator', 'DmeRigOrientConstraintOperator',
                        'DmeRigIKConstraintOperator')
SLAVE_ATTRS = ('slave', 'startJoint', 'midJoint', 'endJoint')
SOLVER_FIELDS = ('startOffset', 'midOffset', 'poleVector', 'mode')
# Attributes that are evaluated outputs rather than authored data.
EVALUATED_OPERATOR_OUTPUTS = {'DmeExpressionOperator': ('result',)}
STAGES = ('committed', 'undone', 'redone', 'final')
STAGE_EXPECT = {'committed': 'TRANSFERRED', 'undone': 'BASELINE', 'redone': 'TRANSFERRED', 'final': 'BASELINE'}


class Stop(Exception):
    """Invalid context, binding, ownership, integrity or authored-state failure."""


class Fail(Exception):
    """The experiment ran and its required result was not obtained."""


class Unresolved(Exception):
    """Required evidence could not be read: INCONCLUSIVE, never inferred."""


# ---------------------------------------------------------------------------
# Strict native reads (the read idioms of the reviewed R3C1 diagnostic)
# ---------------------------------------------------------------------------

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def native_name(name):
    # Python 2 SWIG char const* does not accept unicode.
    if sys.version_info[0] == 2 and isinstance(name, text_type):
        return name.encode('utf-8', 'strict')
    return name


def text(value):
    if value is None:
        return None
    if isinstance(value, bytes) and not isinstance(value, text_type):
        return value.decode('utf-8', 'strict')
    return text_type(value)


def has_attr(obj, name):
    return bool(obj.HasAttribute(native_name(name)))


def attr(obj, name):
    if obj is None:
        raise Unresolved('No object for ' + name)
    a = obj.GetAttribute(native_name(name))
    if a is None:
        raise Unresolved('Missing attribute ' + name)
    errors = []
    for method in ('GetValue', 'GetValueUntyped'):
        try:
            return getattr(a, method)()
        except Exception as exc:
            errors.append(repr(exc))
    raise Unresolved('%s unreadable: %s' % (name, errors))


def opt_attr(obj, name):
    """(present, value): absence is distinguished from an unreadable read."""
    if not has_attr(obj, name):
        return False, None
    return True, attr(obj, name)


def sequence(value, cap=MAX_ARRAY):
    n = len(value)
    if n < 0 or n > cap:
        raise Unresolved('Collection exceeds bound: %s' % n)
    return [value[i] for i in range(n)]


def handle(obj):
    if obj is None:
        raise Stop('Required native binding is null')
    return int(obj.GetHandle())


def type_of(obj):
    return text(obj.GetTypeString())


def ident(obj):
    if obj is None:
        return None
    return {'handle': handle(obj), 'type': type_of(obj), 'name': text(obj.GetName())}


def numeric(value):
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise Unresolved('Non-finite number')
    return value


def components(value, n):
    if 'quaternion' in type(value).__name__.lower():
        if n != 4:
            raise Unresolved('Quaternion must have four components')
        return [numeric(getattr(value, k)) for k in ('x', 'y', 'z', 'w')]
    if n == 3 and all(hasattr(value, k) for k in ('x', 'y', 'z')):
        return [numeric(getattr(value, k)) for k in ('x', 'y', 'z')]
    return [numeric(value[i]) for i in range(n)]


def vec3(value):
    return components(value, 3)


def quat(value):
    return components(value, 4)


def ticks_of(t):
    value = t.GetTenthsOfMS()
    if isinstance(value, bool) or not isinstance(value, integer_types):
        value = int(value)
    return int(value)


def plain(value):
    """Lossless JSON form of an authored value; unknown native types raise."""
    if value is None or isinstance(value, (bool,) + integer_types + (text_type,)):
        return value
    if isinstance(value, bytes):
        return value.decode('utf-8', 'strict')
    if isinstance(value, float):
        return numeric(value)
    if hasattr(value, 'GetHandle') and hasattr(value, 'GetTypeString'):
        # Native element arrays are wrappers with their own handle and the
        # type 'element_array'; their members, not the wrapper, are the data.
        if text(value.GetTypeString()).endswith('_array'):
            return [plain(x) for x in sequence(value)]
        return ident(value)
    if hasattr(value, 'GetTenthsOfMS'):
        return {'ticks': ticks_of(value)}
    name = type(value).__name__.lower()
    if 'quaternion' in name or 'vector4' in name:
        return components(value, 4)
    if 'vector2' in name:
        return components(value, 2)
    if name in ('vector', 'vectoraligned', 'qangle'):
        return components(value, 3)
    if name == 'color':
        return {'color': [int(value.r()), int(value.g()), int(value.b()), int(value.a())]}
    if isinstance(value, (list, tuple)) or hasattr(value, '__len__'):
        return [plain(x) for x in sequence(value)]
    raise Unresolved('No lossless serializer for ' + type(value).__name__)


def key_float(value):
    if isinstance(value, bool) or not isinstance(value, integer_types + (float,)):
        raise Unresolved('Float key value of type %s' % type(value).__name__)
    return numeric(value)


def key_color(value):
    rgba = [value.r(), value.g(), value.b(), value.a()]
    if any(isinstance(c, bool) or not isinstance(c, integer_types) or not 0 <= c <= 255 for c in rgba):
        raise Unresolved('Color key value is not four 8-bit channels')
    return [int(c) for c in rgba]


# Lossless key-value serializers for exactly the log-layer types present in
# the fixture's shot10/shot15 channels (offline DMX survey: Float, Vector3,
# Quaternion and two Color logs). Any other layer type refuses: preservation
# evidence is never replaced by a type marker.
KEY_SERIALIZERS = {'DmeFloatLogLayer': key_float, 'DmeVector3LogLayer': vec3,
                   'DmeQuaternionLogLayer': quat, 'DmeColorLogLayer': key_color}


def require_readable(value, label):
    """Every required evidence record must have been read (or verifiably be
    absent). An UNREADABLE record is never accepted as preserved evidence."""
    problems = []

    def walk(v, path):
        if len(problems) >= 8:
            return
        if isinstance(v, dict):
            if v.get('status') == 'UNREADABLE':
                problems.append(path)
            for k in sorted(v):
                walk(v[k], path + '/' + text_type(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, path + '/%d' % i)
    walk(value, '')
    if problems:
        raise Unresolved('%s evidence is unreadable: %s' % (label, problems))
    return value


def field(obj, name):
    try:
        if not has_attr(obj, name):
            return {'status': 'ABSENT'}
    except Exception as exc:
        return {'status': 'UNREADABLE', 'error': repr(exc)}
    try:
        return {'status': 'READ', 'value': plain(attr(obj, name))}
    except Exception as exc:
        return {'status': 'UNREADABLE', 'error': repr(exc)}


def attribute_names(obj):
    names = []
    a = obj.FirstAttribute()
    while a is not None:
        name = text(a.GetName())
        if name in names or len(names) >= 256:
            raise Unresolved('Attribute walk repeated or exceeded bound')
        names.append(name)
        a = a.NextAttribute()
    return names


def required(record, path):
    if record.get('status') != 'READ':
        raise Unresolved('Required evidence unreadable: %s %s' % (path, record))
    return record['value']


# ---------------------------------------------------------------------------
# Rigid-transform math (column vectors; quaternions x, y, z, w)
# ---------------------------------------------------------------------------

def unit(q):
    n = math.sqrt(sum(c * c for c in q))
    if n < 1e-9:
        raise Unresolved('Degenerate quaternion')
    return [c / n for c in q]


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz]


def qconj(q):
    return [-q[0], -q[1], -q[2], q[3]]


def qrot(q, v):
    return qmul(qmul(q, list(v) + [0.0]), qconj(q))[:3]


def compose(a, b):
    """a x b for rigid transforms (position, unit quaternion)."""
    qa = unit(a[1])
    return ([a[0][i] + qrot(qa, b[0])[i] for i in range(3)], unit(qmul(qa, unit(b[1]))))


def invert(a):
    qi = qconj(unit(a[1]))
    return ([-c for c in qrot(qi, a[0])], qi)


def distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def angle_deg(a, b):
    a, b = unit(a), unit(b)
    d = min(1.0, abs(sum(a[i] * b[i] for i in range(4))))
    return math.degrees(2.0 * math.acos(d))


def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


# ---------------------------------------------------------------------------
# Configuration, integrity and context
# ---------------------------------------------------------------------------

def load_config():
    path = os.path.join(BASE, 'config.json')
    with open(path, 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
    if config.get('format') != 'F01W1-config-v1':
        raise Stop('Unexpected config format')
    paths = [normalized(config[k]) for k in ('original_session', 'r2_fixture', 'disposable_session')]
    if len(set(paths)) != 3:
        raise Stop('Disposable session must differ from the original and the R2 fixture')
    return config


def integrity(config):
    values = {}
    for key in ('original_session', 'r2_fixture', 'disposable_session', 'cpm_source'):
        values[key] = digest(config[key])
    for key in ('original_session', 'r2_fixture', 'disposable_session'):
        if values[key] != config[key + '_sha256']:
            raise Stop('Protected file hash changed: %s; preserve evidence and stop' % key)
    values['harness'] = digest(os.path.join(BASE, 'f01w1_harness.py'))
    values['config'] = digest(os.path.join(BASE, 'config.json'))
    return values


def check_ui():
    from PySide import QtCore, QtGui
    app = QtGui.QApplication.instance()
    if app is None or QtCore.QThread.currentThread() != app.thread():
        raise Stop('Not on the SFM Qt application thread')
    if app.activeModalWidget() is not None:
        raise Stop('A modal dialog is open')
    cpm = sys.modules.get('chadchan3d_cpm_app')
    window_type = getattr(cpm, 'ProdWindow', None) if cpm is not None else None
    if window_type is not None:
        for w in app.topLevelWidgets():
            if isinstance(w, window_type) and any(getattr(w, k, False) for k in
                                                  ('busy', 'operation', 'closing_requested',
                                                   'scene_activity_suspended')):
                raise Stop('CPM is busy or scene access is suspended')


def context(sfmApp, vs, config, place):
    check_ui()
    spec = config['places'][place]
    if not sfmApp.HasDocument():
        raise Stop('No document open')
    doc = sfmApp.GetDocumentRoot()
    path = text(vs.g_pDataModel.GetFileName(doc.GetFileId()))
    if normalized(path) != normalized(config['disposable_session']):
        raise Stop('The open document is not the configured disposable session')
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None or text(shot.GetName()) != spec['shot']:
        raise Stop('This step requires %s at movie frame %d' % (spec['shot'], spec['movie_frame']))
    head = numeric(sfmApp.GetHeadTimeInSeconds())
    start = numeric(shot.GetStartTime().GetSeconds())
    end = numeric(shot.GetEndTime().GetSeconds())
    if not start < head < end:
        raise Stop('Playhead %.9f s is not strictly inside %s' % (head, spec['shot']))
    if abs(head - spec['head_seconds']) > 0.000051:
        raise Stop('This step requires movie frame %d (%.4f s); playhead is %.6f s' %
                   (spec['movie_frame'], spec['head_seconds'], head))
    media = numeric(shot.ToChildMediaTime(vs.DmeTime_t(head), False).GetSeconds())
    if abs(media - spec['media_seconds']) > 0.000051:
        raise Stop('Native shot-media time does not match the prepared fixture')
    if (abs(start - spec['start_ticks'] / 10000.0) > 0.000051 or
            abs(end - spec['end_ticks'] / 10000.0) > 0.000051):
        raise Stop('Live shot timing differs from the prepared fixture')
    return shot, {'pid': os.getpid(), 'document': ident(doc), 'file_id': int(doc.GetFileId()),
                  'document_path': normalized(path), 'shot': ident(shot), 'head_seconds': head,
                  'shot_media_seconds': media}


# ---------------------------------------------------------------------------
# Scene resolution (fresh identities every step)
# ---------------------------------------------------------------------------

def walk(root):
    nodes, parents = {}, {}
    pending = [(root, None, ())]
    edges = 0
    while pending:
        obj, parent, ancestors = pending.pop()
        h = handle(obj)
        if h in ancestors:
            raise Stop('Cycle in scene DAG at %s' % ident(obj))
        parents.setdefault(h, []).append(parent)
        if h in nodes:
            continue
        if len(nodes) >= MAX_NODES:
            raise Unresolved('Scene DAG exceeds bound')
        nodes[h] = obj
        for child in reversed(sequence(attr(obj, 'children'))):
            edges += 1
            if edges > 16384:
                raise Unresolved('Scene edge inventory exceeds bound')
            pending.append((child, h, ancestors + (h,)))
    return nodes, parents


def shot_inventory(shot, head_seconds, vs):
    """Every channel of the shot's channels clips, with its native clip-time chain."""
    pending, clips, inventory = [(shot, head_seconds, [])], {}, {}
    while pending:
        clip, parent_time, chain = pending.pop()
        h = handle(clip)
        if h in clips:
            raise Stop('Repeated or cyclic clip ownership')
        if len(clips) >= 512:
            raise Unresolved('Clip inventory bound exceeded')
        clips[h] = clip
        child_time = numeric(clip.ToChildMediaTime(vs.DmeTime_t(parent_time), False).GetSeconds())
        chain = chain + [{'clip': ident(clip), 'input_seconds': parent_time, 'output_seconds': child_time}]
        if has_attr(clip, 'channels'):
            for ch in sequence(attr(clip, 'channels')):
                if handle(ch) in inventory:
                    raise Stop('Channel has repeated clip membership')
                inventory[handle(ch)] = (ch, {'seconds': child_time, 'chain': chain})
        groups = sequence(attr(clip, 'trackGroups')) if has_attr(clip, 'trackGroups') else []
        if has_attr(clip, 'subClipTrackGroup'):
            sub = attr(clip, 'subClipTrackGroup')
            if sub is not None:
                groups.append(sub)
        for group in groups:
            for track in sequence(attr(group, 'tracks')):
                pending.extend((child, child_time, chain) for child in sequence(attr(track, 'children')))
                if len(pending) > 1024:
                    raise Unresolved('Pending clip inventory exceeds bound')
    return inventory


def unique(items, what):
    if len(items) != 1:
        raise Stop('%s missing or ambiguous (%d)' % (what, len(items)))
    return items[0]


BONE_NAME = re.compile(r'^bone (\d+) \((.+)\)$')


def resolve(sfmApp, vs, config, place):
    shot, token = context(sfmApp, vs, config, place)
    L = {'shot': shot, 'token': token, 'place': place}
    animset = unique([x for x in sequence(attr(shot, 'animationSets'))
                      if text(x.GetName()) == config['animation_set']], 'Animation set')
    gm = attr(animset, 'gameModel')
    if text(attr(gm, 'modelName')).replace('\\', '/').lower() != config['model']:
        raise Stop('Unexpected model')
    L['animset'], L['gm'] = animset, gm
    nodes, parents = walk(attr(shot, 'scene'))
    if handle(gm) not in nodes:
        raise Stop('Model is not in the current shot scene')
    L['nodes'], L['parents'] = nodes, parents
    regs = []
    for obj in nodes.values():
        if type_of(obj) == 'DmeRig':
            for reg in sequence(attr(obj, 'animSetList')):
                linked = attr(reg, 'animationSet')
                if linked is not None and handle(linked) == handle(animset):
                    regs.append(reg)
    L['reg'] = unique(regs, 'Rig registration for the animation set')
    L['owned'] = sequence(attr(L['reg'], 'elementList'))
    L['rig_handles'] = {}
    for obj in L['owned']:
        if type_of(obj) == 'DmeRigHandle':
            name = text(obj.GetName())
            if name in L['rig_handles']:
                raise Stop('Duplicate rig handle name ' + name)
            L['rig_handles'][name] = obj
    for name in HANDLE_NAMES:
        if name not in L['rig_handles']:
            raise Stop('Rig handle missing: ' + name)
    L['controls'] = {}
    L['all_controls'] = sequence(attr(animset, 'controls'))
    for name in CONTROL_NAMES:
        L['controls'][name] = unique([c for c in L['all_controls'] if type_of(c) == 'DmeTransformControl'
                                      and text(c.GetName()) == name], 'Control ' + name)
    L['inventory'] = shot_inventory(shot, token['head_seconds'], vs)
    L['channels'] = {}
    for spec in WRITE_CHANNELS + OBSERVED_CHANNELS:
        name, owner, channel_attr = spec[0], spec[1], spec[2]
        ch = attr(L['controls'][owner], channel_attr)
        if ch is None or text(ch.GetName()) != name:
            raise Stop('Control %s.%s is not the expected channel %s' % (owner, channel_attr, name))
        if handle(ch) not in L['inventory']:
            raise Stop('Channel %s has no owning clip in the shot inventory' % name)
        L['channels'][name] = ch
    bones = sequence(attr(gm, 'bones'))
    by_transform = {}
    for b in bones:
        by_transform[handle(b)] = b
    L['bones'] = {}
    for obj in nodes.values():
        if not has_attr(obj, 'transform'):
            continue
        t = attr(obj, 'transform')
        if t is None or handle(t) not in by_transform:
            continue
        m = BONE_NAME.match(text(t.GetName()))
        if m is None:
            raise Stop('Unrecognised bone transform name %s' % text(t.GetName()))
        index, name = int(m.group(1)), m.group(2)
        if name in L['bones']:
            raise Stop('Duplicate bone ' + name)
        L['bones'][name] = {'dag': obj, 'transform': t, 'index': index}
    if len(L['bones']) != len(bones):
        raise Stop('Not every model bone has exactly one scene DAG')
    for name in ARM_BONES + (COLLAR_BONE,):
        if name not in L['bones']:
            raise Stop('Bone missing: ' + name)
    operators = sequence(attr(animset, 'operators'))
    seen = set(handle(x) for x in operators)
    for op in sequence(attr(shot, 'operators')):
        if handle(op) not in seen:
            operators.append(op)
            seen.add(handle(op))
    L['operators'] = operators
    L['arm_ops'] = arm_constraints(L)
    return L


def slave_target(op, slave_attr):
    present, slave = opt_attr(op, slave_attr)
    if not present or slave is None:
        return None
    return attr(slave, 'target')


def arm_constraints(L):
    hand, collar = handle(L['bones']['bip_hand_l']['dag']), handle(L['bones'][COLLAR_BONE]['dag'])
    found = {'ik': [], 'hand_orient': [], 'collar_point': [], 'collar_orient': []}
    for op in L['operators']:
        kind = type_of(op)
        if kind == 'DmeRigIKConstraintOperator':
            end = slave_target(op, 'endJoint')
            if end is not None and handle(end) == hand:
                found['ik'].append(op)
        elif kind in ('DmeRigOrientConstraintOperator', 'DmeRigPointConstraintOperator'):
            target = slave_target(op, 'slave')
            if target is None:
                continue
            if kind == 'DmeRigOrientConstraintOperator' and handle(target) == hand:
                found['hand_orient'].append(op)
            if handle(target) == collar:
                found['collar_point' if kind == 'DmeRigPointConstraintOperator' else 'collar_orient'].append(op)
    return dict((k, unique(v, 'Arm constraint ' + k)) for k, v in found.items())


# ---------------------------------------------------------------------------
# Captures
# ---------------------------------------------------------------------------

def key_entries(layer, budget):
    serializer = KEY_SERIALIZERS.get(type_of(layer))
    if serializer is None:
        raise Unresolved('No lossless key serializer for layer type %s' % type_of(layer))
    count = int(layer.GetKeyCount())
    if count < 0 or count > MAX_LAYER_KEYS or budget[0] + count > MAX_TOTAL_KEYS:
        raise Unresolved('Key inventory exceeds bound; no truncation accepted')
    budget[0] += count
    return [[ticks_of(layer.GetKeyTime(k)), serializer(layer.GetKeyValue(k))] for k in range(count)]


def channel_authored(ch, budget):
    binding = {}
    for name in ('fromElement', 'fromAttribute', 'fromIndex', 'toElement', 'toAttribute', 'toIndex', 'mode'):
        binding[name] = field(ch, name)
    log = ch.GetLog()
    row = {'id': ident(ch), 'binding': binding, 'log': ident(log), 'layers': []}
    if log is not None:
        row['log_fields'] = dict((k, field(log, k)) for k in ('usedefaultvalue', 'defaultvalue', 'curveinfo'))
        n = int(log.GetNumLayers())
        if n < 0 or n > 16:
            raise Unresolved('Layer count exceeds bound')
        for i in range(n):
            layer = log.GetLayer(i)
            row['layers'].append({'id': ident(layer), 'type': type_of(layer), 'keys': key_entries(layer, budget)})
    return row


CONTROL_FIELDS = {'DmeTransformControl': ('valuePosition', 'valueOrientation', 'positionChannel',
                                          'orientationChannel')}
DEFAULT_CONTROL_FIELDS = ('value', 'leftValue', 'rightValue', 'channel', 'leftvaluechannel', 'rightvaluechannel')


def operator_relationships(op):
    row = {'id': ident(op), 'slaves': {}, 'targets': [], 'solver': {}}
    for slave_attr in SLAVE_ATTRS:
        present, slave = opt_attr(op, slave_attr)
        if present:
            row['slaves'][slave_attr] = {'slave': ident(slave),
                                         'target': ident(attr(slave, 'target')) if slave is not None else None}
    if has_attr(op, 'pvTarget'):
        row['pvTarget'] = ident(attr(op, 'pvTarget'))
    if has_attr(op, 'targets'):
        for t in sequence(attr(op, 'targets')):
            row['targets'].append({'id': ident(t), 'target': ident(attr(t, 'target')),
                                   'oOffset': field(t, 'oOffset'), 'vecOffset': field(t, 'vecOffset')})
    for name in SOLVER_FIELDS:
        if has_attr(op, name):
            row['solver'][name] = field(op, name)
    return row


def capture_authored(L):
    """Authored state of one shot: every channel's binding and complete logs,
    every animation-set control's stored values and channels, and the rig and
    constraint relationships. Exact comparison; any change is an authored
    mutation."""
    budget = [0]
    out = {'channels': [], 'controls': [], 'registration': [ident(x) for x in L['owned']],
           'rig_handle_parents': {}, 'operators': []}
    for h in sorted(L['inventory']):
        out['channels'].append(channel_authored(L['inventory'][h][0], budget))
    for c in sorted(L['all_controls'], key=handle):
        names = CONTROL_FIELDS.get(type_of(c), DEFAULT_CONTROL_FIELDS)
        out['controls'].append({'id': ident(c), 'fields': dict((n, field(c, n)) for n in names)})
    for name in sorted(L['rig_handles']):
        out['rig_handle_parents'][name] = sorted(x for x in L['parents'].get(handle(L['rig_handles'][name]), [])
                                                 if x is not None)
    for op in sorted(L['operators'], key=handle):
        if type_of(op) not in KNOWN_OPERATORS:
            raise Stop('Unsupported operator type in shot: %s' % type_of(op))
        out['operators'].append(operator_relationships(op))
    out['keys'] = budget[0]
    return require_readable(out, 'Authored')


def layer_types(authored):
    counts = {}
    for row in authored['channels']:
        for layer in row['layers']:
            counts[layer['type']] = counts.get(layer['type'], 0) + 1
    return counts


# Stages whose evidence verifies a restoration or reproduction made by native
# Undo/Redo: unreadable evidence there is STOP (recovery unverified).
RECOVERY_STAGES = ('undone', 'redone', 'final')


def recovery_read(fn, label):
    """A read required to verify an Abort/Undo/Redo restoration. Unreadable
    evidence means the restoration cannot be verified: STOP, never
    INCONCLUSIVE-and-go."""
    try:
        return fn()
    except Unresolved as exc:
        raise Stop('Recovery unverified (%s): %s' % (label, exc))


def recovery_capture(Lx):
    """The destination authored state read to verify a restoration."""
    return recovery_read(lambda: roundtrip(capture_authored(Lx)), 'destination authored state')


def channel_destinations(L):
    result = set()
    for ch, _ in L['inventory'].values():
        to = field(ch, 'toElement')
        name = field(ch, 'toAttribute')
        if to.get('status') == 'READ' and to['value'] is not None and name.get('status') == 'READ':
            result.add((to['value']['handle'], name['value']))
    return result


def capture_observed(L):
    """Every other operator/constraint attribute, excluding evaluated outputs.
    Changes are reported for review and prevent PASS, but are not classified as
    authored mutations (some may be evaluated caches)."""
    destinations = channel_destinations(L)
    out = {}
    elements = {}
    for op in L['operators']:
        elements[handle(op)] = op
        for slave_attr in SLAVE_ATTRS:
            present, slave = opt_attr(op, slave_attr)
            if present and slave is not None:
                elements[handle(slave)] = slave
        if has_attr(op, 'targets'):
            for t in sequence(attr(op, 'targets')):
                elements[handle(t)] = t
    for h in sorted(elements):
        obj = elements[h]
        skip = EVALUATED_OPERATOR_OUTPUTS.get(type_of(obj), ())
        row = {}
        for name in attribute_names(obj):
            if name in skip or (h, name) in destinations:
                continue
            row[name] = field(obj, name)
        out[str(h)] = {'id': ident(obj), 'attributes': row}
    return require_readable(out, 'Constraint/operator attribute')


def transform_state(dag):
    t = attr(dag, 'transform')
    return {'local_position': vec3(attr(t, 'position')), 'local_orientation': quat(attr(t, 'orientation')),
            'scale': field(t, 'scale'), 'world_position': vec3(dag.GetAbsPosition()),
            'world_orientation': quat(dag.GetAbsOrientation())}


def capture_skeleton(L, vs):
    """Evaluated state: every bone, every rig handle, the model, constraint
    weights and the four arm channels' native log values at both clocks."""
    dag_to_bone = dict((handle(v['dag']), k) for k, v in L['bones'].items())
    out = {'bones': {}, 'handles': {}, 'weights': {}, 'arm_channels': {}}
    for name, b in L['bones'].items():
        row = transform_state(b['dag'])
        row['index'] = b['index']
        row['handle'] = handle(b['dag'])
        row['transform_handle'] = handle(b['transform'])
        parents = [p for p in L['parents'].get(handle(b['dag']), []) if p is not None]
        row['parent'] = dag_to_bone.get(parents[0]) if len(parents) == 1 else None
        out['bones'][name] = row
    for name, dag in L['rig_handles'].items():
        row = transform_state(dag)
        row['handle'] = handle(dag)
        row['parents'] = sorted(p for p in L['parents'].get(handle(dag), []) if p is not None)
        out['handles'][name] = row
    gm = L['gm']
    out['model'] = transform_state(gm)
    out['rig_root_handle'] = handle(L['rig_handles']['rig_root'])
    for key, op in L['arm_ops'].items():
        rows = []
        for t in sequence(attr(op, 'targets')):
            rows.append({'target': ident(attr(t, 'target')), 'weight': numeric(attr(t, 'targetWeight'))})
        out['weights'][key] = rows
    for name in [s[0] for s in WRITE_CHANNELS + OBSERVED_CHANNELS]:
        ch = L['channels'][name]
        log = ch.GetLog()
        current = ch.GetCurrentTime()
        nominal = L['inventory'][handle(ch)][1]['seconds']
        out['arm_channels'][name] = {
            'current_ticks': ticks_of(current), 'current_seconds': numeric(current.GetSeconds()),
            'nominal_seconds': nominal,
            'value_current': plain(log.GetValue(current)),
            'value_nominal': plain(log.GetValue(vs.DmeTime_t(nominal)))}
    return require_readable(out, 'Evaluated')


def roundtrip(value):
    """JSON normal form, so live captures compare exactly with stored ones."""
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                                     separators=(',', ':')).encode('ascii')).hexdigest()


def differences(left, right, path='', limit=64, out=None):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(left, dict) and isinstance(right, dict):
        for k in sorted(set(left) | set(right)):
            if k not in left or k not in right:
                out.append(path + '/' + text_type(k))
            else:
                differences(left[k], right[k], path + '/' + text_type(k), limit, out)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append(path + '/length')
        else:
            for i in range(len(left)):
                differences(left[i], right[i], path + '/%d' % i, limit, out)
    elif isinstance(left, (text_type, bytes)) and isinstance(right, (text_type, bytes)):
        if text(left) != text(right):
            out.append(path)
    elif isinstance(left, bool) or isinstance(right, bool):
        if type(left) is not type(right) or left != right:
            out.append(path)
    elif isinstance(left, integer_types) and isinstance(right, integer_types):
        if left != right:
            out.append(path)
    elif type(left) is not type(right) or left != right:
        out.append(path)
    return out


# ---------------------------------------------------------------------------
# Preflight: write targets, keys, writers, compatibility
# ---------------------------------------------------------------------------

def find_bracket(layer, bracket_ticks):
    count = int(layer.GetKeyCount())
    if count < 2 or count > MAX_LAYER_KEYS:
        raise Stop('Unexpected key count %d' % count)
    times = [ticks_of(layer.GetKeyTime(k)) for k in range(count)]
    indices = []
    for wanted in bracket_ticks:
        hits = [k for k in range(count) if times[k] == wanted]
        if len(hits) != 1:
            raise Stop('Bracket key at %d ticks is missing or duplicated (%d matches)' % (wanted, len(hits)))
        indices.append(hits[0])
    if indices[1] != indices[0] + 1:
        raise Stop('Keys intervene between the bracket keys')
    return {'indices': indices, 'times': times, 'count': count}


def write_targets(L, config):
    """Each write channel verified by identity and binding; its own bracket
    indices resolved from native key times."""
    targets = {}
    for name, owner, channel_attr, source_attr, dest_attr, log_type, layer_type in WRITE_CHANNELS:
        ch = L['channels'][name]
        control = L['controls'][owner]
        handle_transform = attr(L['rig_handles'][owner], 'transform')
        b = dict((k, required(field(ch, k), name + '.' + k)) for k in
                 ('fromElement', 'fromAttribute', 'fromIndex', 'toElement', 'toAttribute', 'toIndex', 'mode'))
        if (b['fromElement'] is None or b['fromElement']['handle'] != handle(control) or
                b['fromAttribute'] != source_attr or b['toElement'] is None or
                b['toElement']['handle'] != handle(handle_transform) or b['toAttribute'] != dest_attr or
                b['fromIndex'] != 0 or b['toIndex'] != 0):
            raise Stop('Channel %s binding differs from the expected rig input binding' % name)
        if b['mode'] != 3:
            raise Stop('Channel %s is not in Play mode (3)' % name)
        log = ch.GetLog()
        if log is None or type_of(log) != log_type:
            raise Stop('Channel %s log type is not %s' % (name, log_type))
        if int(log.GetNumLayers()) != 1:
            raise Stop('Channel %s log is not single-layer' % name)
        layer = log.GetLayer(0)
        if type_of(layer) != layer_type:
            raise Stop('Channel %s layer type is not %s' % (name, layer_type))
        curve = field(log, 'curveinfo')
        if not (curve.get('status') == 'ABSENT' or (curve.get('status') == 'READ' and curve['value'] is None)):
            raise Stop('Channel %s log has unsupported curve info' % name)
        layer_curve = field(layer, 'curveinfo')
        if not (layer_curve.get('status') == 'ABSENT' or
                (layer_curve.get('status') == 'READ' and layer_curve['value'] is None)):
            raise Stop('Channel %s layer has unsupported curve info' % name)
        bracket = find_bracket(layer, config['bracket_ticks'])
        targets[name] = {'channel': ch, 'log': log, 'layer': layer, 'bracket': bracket,
                         'kind': 'quaternion' if 'Quaternion' in layer_type else 'vector'}
    return targets


def writer_index(sfmApp):
    """Document-wide channel and operator inventory, strict: any unreadable
    relationship is unresolved and stops the experiment before writing."""
    movie = sfmApp.GetMovie()
    if movie is None:
        raise Stop('Movie unavailable')
    seen, stack = set(), [movie]
    channels, operators = {}, {}
    nodes = 0
    while stack:
        el = stack.pop()
        h = handle(el)
        if h in seen:
            continue
        seen.add(h)
        nodes += 1
        if nodes > 200000:
            raise Unresolved('Writer discovery bound exceeded')
        kind = type_of(el)
        if kind == 'DmeChannel':
            channels[h] = el
            continue
        if kind == 'DmeFilmClip':
            if has_attr(el, 'subClipTrackGroup'):
                sub = attr(el, 'subClipTrackGroup')
                if sub is not None:
                    stack.append(sub)
            if has_attr(el, 'trackGroups'):
                stack.extend(sequence(attr(el, 'trackGroups')))
            if has_attr(el, 'operators'):
                for op in sequence(attr(el, 'operators')):
                    operators[handle(op)] = op
            if has_attr(el, 'animationSets'):
                for a in sequence(attr(el, 'animationSets')):
                    for op in sequence(attr(a, 'operators')):
                        operators[handle(op)] = op
            continue
        if kind == 'DmeTrackGroup':
            stack.extend(sequence(attr(el, 'tracks')))
            continue
        if kind == 'DmeTrack':
            stack.extend(sequence(attr(el, 'children')))
            continue
        if kind == 'DmeChannelsClip':
            stack.extend(sequence(attr(el, 'channels')))
            continue
    index = {'destinations': {}, 'logs': {}, 'layers': {}, 'slave_targets': {}, 'operator_types': {},
             'channels': len(channels), 'operators': len(operators)}
    for h, op in operators.items():
        kind = type_of(op)
        index['operator_types'][kind] = index['operator_types'].get(kind, 0) + 1
        if kind == 'DmeChannel':
            channels[h] = op
            continue
        if kind not in KNOWN_OPERATORS:
            raise Stop('Unsupported operator type in document: %s' % kind)
        for slave_attr in SLAVE_ATTRS:
            target = slave_target(op, slave_attr)
            if target is not None:
                index['slave_targets'].setdefault(handle(target), []).append(h)
    for h, ch in channels.items():
        to = attr(ch, 'toElement')
        if to is not None:
            key = '%d:%s' % (handle(to), text(attr(ch, 'toAttribute')))
            index['destinations'].setdefault(key, []).append(h)
        log = ch.GetLog()
        if log is None:
            continue
        index['logs'].setdefault(handle(log), []).append(h)
        if len(index['logs'][handle(log)]) > 1:
            continue
        for i in range(int(log.GetNumLayers())):
            index['layers'].setdefault(handle(log.GetLayer(i)), []).append(handle(log))
    return index


def check_writers(L, targets, index):
    for name, t in targets.items():
        ch = t['channel']
        to = attr(ch, 'toElement')
        key = '%d:%s' % (handle(to), text(attr(ch, 'toAttribute')))
        if index['destinations'].get(key) != [handle(ch)]:
            raise Stop('Channel %s is not the unique writer of its destination' % name)
        if index['logs'].get(handle(t['log'])) != [handle(ch)]:
            raise Stop('Channel %s log is shared' % name)
        if index['layers'].get(handle(t['layer'])) != [handle(t['log'])]:
            raise Stop('Channel %s layer is shared' % name)
    for owner in ('Hand_l', 'Elbow_l'):
        dag = L['rig_handles'][owner]
        if index['slave_targets'].get(handle(dag)):
            raise Stop('A constraint drives rig handle %s' % owner)
        control = L['controls'][owner]
        for source_attr in ('valuePosition', 'valueOrientation'):
            if index['destinations'].get('%d:%s' % (handle(control), source_attr)):
                raise Stop('A channel writes control %s.%s' % (owner, source_attr))


def arm_chain(skel):
    """Bones of the left arm below the collar, excluding the hand's descendants."""
    children = {}
    for name, row in skel['bones'].items():
        children.setdefault(row['parent'], []).append(name)
    chain, pending = [], [COLLAR_BONE]
    while pending:
        name = pending.pop()
        chain.append(name)
        if name != 'bip_hand_l':
            pending.extend(children.get(name, []))
    return sorted(chain)


def scale_ok(record):
    return record.get('status') == 'ABSENT' or (record.get('status') == 'READ' and record['value'] == 1.0)


def compatibility(src, dst, src_auth, dst_auth, tol):
    """Section 1 prerequisites comparing the two captured shots. Returns evidence."""
    ev = {}
    chain_s, chain_d = arm_chain(src), arm_chain(dst)
    if chain_s != chain_d or not set(ARM_BONES) <= set(chain_d):
        raise Stop('Arm hierarchy differs between shots')
    ev['arm_chain'] = chain_d
    worst = 0.0
    for name in chain_d:
        bs, bd = src['bones'][name], dst['bones'][name]
        if bs['parent'] != bd['parent'] or bs['index'] != bd['index']:
            raise Stop('Bone %s parent/index differs between shots' % name)
        worst = max(worst, distance(bs['local_position'], bd['local_position']))
        if not (scale_ok(bs['scale']) and scale_ok(bd['scale'])):
            raise Stop('Unsupported scale on arm bone %s' % name)
    if worst > tol['bone_offset']:
        raise Stop('Arm bone local positions differ (%.6g)' % worst)
    ev['bone_offset_max'] = worst
    for side, skel in (('source', src), ('destination', dst)):
        root = skel['rig_root_handle']
        for name in HANDLE_NAMES:
            if not scale_ok(skel['handles'][name]['scale']):
                raise Stop('Unsupported scale on %s %s' % (side, name))
        if not scale_ok(skel['model']['scale']):
            raise Stop('Unsupported model scale (%s)' % side)
        # The written inputs live in rig_root space. The CollarL anchor is used
        # as an evaluated world transform, whatever its parent (spine_4 here).
        for name in ('Hand_l', 'Elbow_l'):
            if skel['handles'][name]['parents'] != [root]:
                raise Stop('%s %s is not parented to rig_root' % (side, name))
            r = (skel['handles']['rig_root']['world_position'], skel['handles']['rig_root']['world_orientation'])
            h = skel['handles'][name]
            p, q = compose(r, (h['local_position'], h['local_orientation']))
            if (distance(p, h['world_position']) > tol['position'] or
                    angle_deg(q, h['world_orientation']) > tol['angle_degrees']):
                raise Stop('%s %s world transform is not rig_root x local' % (side, name))
        for key, rows in skel['weights'].items():
            if not rows or any(abs(r['weight'] - 1.0) > 1e-6 for r in rows):
                raise Stop('%s constraint %s weights are not 1.0' % (side, key))
    # Solver offsets, pole relationship and constraint targets.
    ops_s = dict((o['id']['handle'], o) for o in src_auth['operators'])
    ops_d = dict((o['id']['handle'], o) for o in dst_auth['operators'])
    ev['constraints'] = {}
    for key in ('ik', 'hand_orient', 'collar_point', 'collar_orient'):
        os_, od = ops_s[src['arm_op_handles'][key]], ops_d[dst['arm_op_handles'][key]]
        if os_['solver'] != od['solver']:
            raise Stop('Solver fields differ for %s' % key)
        if len(os_['targets']) != 1 or len(od['targets']) != 1:
            raise Stop('Constraint %s must have exactly one target' % key)
        ts, td = os_['targets'][0], od['targets'][0]
        if ts['oOffset'] != td['oOffset'] or ts['vecOffset'] != td['vecOffset']:
            raise Stop('Constraint target offsets differ for %s' % key)
        expected = 'CollarL' if key.startswith('collar') else 'Hand_l'
        for side, t, skel in (('source', ts, src), ('destination', td, dst)):
            if t['target'] is None or t['target']['handle'] != skel['handles'][expected]['handle']:
                raise Stop('%s constraint %s does not target rig handle %s' % (side, key, expected))
        ev['constraints'][key] = {'solver': od['solver'], 'offsets': [td['oOffset'], td['vecOffset']]}
    # Object identity, not names: IK pole target and joints, and the slaves.
    for side, ops, skel in (('source', ops_s, src), ('destination', ops_d, dst)):
        ik = ops[skel['arm_op_handles']['ik']]
        if ik.get('pvTarget') is None or ik['pvTarget']['handle'] != skel['handles']['Elbow_l']['handle']:
            raise Stop('%s IK pole target is not the Elbow_l rig handle' % side)
        joints = dict((k, (ik['slaves'].get(k) or {}).get('target')) for k in ('startJoint', 'midJoint', 'endJoint'))
        wanted = {'startJoint': 'bip_UpperArm_l', 'midJoint': 'bip_lowerArm_l', 'endJoint': 'bip_hand_l'}
        for k, bone in wanted.items():
            if joints[k] is None or joints[k]['handle'] != skel['bones'][bone]['handle']:
                raise Stop('%s IK %s is not %s' % (side, k, bone))
        for key, bone in (('hand_orient', 'bip_hand_l'), ('collar_point', COLLAR_BONE),
                          ('collar_orient', COLLAR_BONE)):
            slave = (ops[skel['arm_op_handles'][key]]['slaves'].get('slave') or {}).get('target')
            if slave is None or slave['handle'] != skel['bones'][bone]['handle']:
                raise Stop('%s constraint %s does not drive %s' % (side, key, bone))
    return ev


def hold_state(skel, config, side):
    """The arm channels are inside the hold interval at both clocks and the rig
    handle locals equal the native log values (effective inputs)."""
    lo, hi = config['bracket_ticks']
    ev = {}
    for name, row in skel['arm_channels'].items():
        nominal_ticks = row['nominal_seconds'] * 10000.0
        if not (lo < row['current_ticks'] < hi and lo < nominal_ticks < hi):
            raise Stop('%s %s clocks are not strictly inside the bracket' % (side, name))
        ev[name] = {'current_ticks': row['current_ticks'], 'nominal_seconds': row['nominal_seconds']}
    pairs = (('Hand_l_p', 'Hand_l', 'local_position'), ('Hand_l_o', 'Hand_l', 'local_orientation'),
             ('Elbow_l_p', 'Elbow_l', 'local_position'), ('Elbow_l_o', 'Elbow_l', 'local_orientation'))
    tol = config['tolerances']
    for ch, owner, key in pairs:
        local = skel['handles'][owner][key]
        for clock in ('value_current', 'value_nominal'):
            value = skel['arm_channels'][ch][clock]
            if key == 'local_position':
                bad = distance(local, value) > tol['effective_position']
            else:
                bad = angle_deg(local, value) > tol['effective_angle_degrees']
            if bad:
                raise Stop('%s %s handle value differs from its log at %s' % (side, ch, clock))
    return ev


# ---------------------------------------------------------------------------
# Goals and oracle
# ---------------------------------------------------------------------------

def world(skel, kind, name):
    row = skel[kind][name]
    return (row['world_position'], row['world_orientation'])


def compute_goals(src, dst, config, hand_reference=None):
    """Gworld = Cd x inverse(Cs) x Rs x Ls ; Ldestination = inverse(Rd) x Gworld.
    The hand quaternion's sign is chosen once, in the hemisphere of the key
    value it replaces (hand_reference), and written identically at both keys."""
    Cs, Cd = world(src, 'handles', 'CollarL'), world(dst, 'handles', 'CollarL')
    Rs, Rd = world(src, 'handles', 'rig_root'), world(dst, 'handles', 'rig_root')
    M = compose(Cd, invert(Cs))
    goals = {}
    for owner in ('Hand_l', 'Elbow_l'):
        h = src['handles'][owner]
        G = compose(compose(M, Rs), (h['local_position'], h['local_orientation']))
        Ld = compose(invert(Rd), G)
        goals[owner] = {'position': Ld[0], 'orientation': Ld[1], 'world_position': G[0]}
    upper_s = src['bones']['bip_UpperArm_l']['world_position']
    mapped = compose(M, (upper_s, [0.0, 0.0, 0.0, 1.0]))[0]
    collar_error = distance(mapped, dst['bones']['bip_UpperArm_l']['world_position'])
    if collar_error > config['tolerances']['collar_mapping']:
        raise Stop('Source upper-arm origin mapped through the CollarL anchors misses the destination '
                   'upper arm by %.6g' % collar_error)
    orientation = list(goals['Hand_l']['orientation'])
    sign = 1.0
    if hand_reference is not None and sum(orientation[i] * hand_reference[i] for i in range(4)) < 0.0:
        sign = -1.0
        orientation = [-c for c in orientation]
    write = {'Hand_l_p': [f32(c) for c in goals['Hand_l']['position']],
             'Hand_l_o': [f32(c) for c in orientation],
             'Elbow_l_p': [f32(c) for c in goals['Elbow_l']['position']]}
    cross = config['astra_cross_check']
    ctol = config['tolerances']
    checks = {
        'hand_position': distance(write['Hand_l_p'], cross['hand_position']),
        'hand_orientation_degrees': angle_deg(write['Hand_l_o'], cross['hand_orientation']),
        'elbow_position': distance(write['Elbow_l_p'], cross['elbow_position'])}
    if (checks['hand_position'] > ctol['cross_check_position'] or
            checks['elbow_position'] > ctol['cross_check_position'] or
            checks['hand_orientation_degrees'] > ctol['cross_check_angle_degrees']):
        raise Stop('Live goals disagree with the adjudicated cross-check values: %r' % checks)
    oracle = {'primary_local': dict((b, src['bones'][b]['local_orientation']) for b in ARM_BONES),
              'secondary_world': {}}
    for b in ARM_BONES:
        p, q = compose(M, world(src, 'bones', b))
        oracle['secondary_world'][b] = {'position': p, 'orientation': q}
    return {'goals_double': goals, 'write_float32': write, 'collar_mapping_error': collar_error,
            'hand_orientation_sign': {'reference': hand_reference, 'negated': sign < 0},
            'cross_check': checks, 'oracle': oracle, 'anchor': {'source': Cs, 'destination': Cd},
            'source_residual': hand_residual(src)}


def hand_residual(skel):
    return distance(skel['bones']['bip_hand_l']['world_position'], skel['handles']['Hand_l']['world_position'])


INPUT_CHANNELS = (('Hand_l_p', 'Hand_l', 'local_position'), ('Hand_l_o', 'Hand_l', 'local_orientation'),
                  ('Elbow_l_p', 'Elbow_l', 'local_position'))


def expected_inputs(baseline, plan, expect):
    """The rig inputs an accepted state requires: the float32 goals (committed,
    redone) or the destination baseline (aborted, undone, final)."""
    if expect == 'TRANSFERRED':
        return dict((ch, plan['write_float32'][ch]) for ch, _, _ in INPUT_CHANNELS)
    return dict((ch, baseline['handles'][owner][key]) for ch, owner, key in INPUT_CHANNELS)


def input_errors(skel, baseline, plan, expect, tol):
    """Rig-input acceptance: each written channel's handle value and its native
    log evaluation at both clocks equal the expected input; the unwritten elbow
    orientation channel equals its baseline at both clocks."""
    want = expected_inputs(baseline, plan, expect)
    errors = []

    def bad(name, got, value, kind):
        if len(value) == 4:
            return angle_deg(got, value) > tol[kind + '_angle_degrees']
        return distance(got, value) > tol[kind + '_position']
    for ch, owner, key in INPUT_CHANNELS:
        if bad(ch, skel['handles'][owner][key], want[ch], 'effective'):
            errors.append('input %s handle value' % ch)
        for clock in ('value_current', 'value_nominal'):
            if bad(ch, skel['arm_channels'][ch][clock], want[ch], 'log_evaluation'):
                errors.append('input %s log %s' % (ch, clock))
    for clock in ('value_current', 'value_nominal'):
        if angle_deg(skel['arm_channels']['Elbow_l_o'][clock], baseline['arm_channels']['Elbow_l_o'][clock]) > \
                tol['log_evaluation_angle_degrees']:
            errors.append('input Elbow_l_o log %s' % clock)
    return errors


def weight_and_scale_changes(skel, baseline):
    """Constraint weights and the scale state of the model and the four handles,
    exactly as captured at the baseline (both are already-captured evidence)."""
    changes = []
    if sorted(skel['weights']) != sorted(baseline['weights']):
        changes.append('weights constraint set')
    for key in sorted(baseline['weights']):
        now, was = skel['weights'].get(key), baseline['weights'][key]
        if now is None or len(now) != len(was) or any(
                n['target'] != w['target'] or abs(n['weight'] - w['weight']) > 1e-6 for n, w in zip(now, was)):
            changes.append('weights ' + key)
    if skel['model']['scale'] != baseline['model']['scale']:
        changes.append('scale model')
    for name in HANDLE_NAMES:
        if skel['handles'][name]['scale'] != baseline['handles'][name]['scale']:
            changes.append('scale handle ' + name)
    return changes


def classify(skel, baseline, plan, expect, tol):
    """Skeletal oracle and rig-input acceptance for one observation. expect is
    TRANSFERRED or BASELINE. The hand-target residual is diagnostic only."""
    o = plan['oracle']
    rows = {}
    primary = secondary = base = True
    for b in ARM_BONES:
        now = skel['bones'][b]
        p_err = angle_deg(now['local_orientation'], o['primary_local'][b])
        s_pos = distance(now['world_position'], o['secondary_world'][b]['position'])
        s_ang = angle_deg(now['world_orientation'], o['secondary_world'][b]['orientation'])
        b_ang = angle_deg(now['local_orientation'], baseline['bones'][b]['local_orientation'])
        b_pos = distance(now['world_position'], baseline['bones'][b]['world_position'])
        rows[b] = {'primary_angle': p_err, 'secondary_position': s_pos, 'secondary_angle': s_ang,
                   'baseline_angle': b_ang, 'baseline_world_position': b_pos}
        primary = primary and p_err <= tol['angle_degrees']
        secondary = secondary and s_pos <= tol['position'] and s_ang <= tol['angle_degrees']
        base = base and b_ang <= tol['angle_degrees'] and b_pos <= tol['position']
    preserved = []
    for name in ARM_BONES:
        now, row = skel['bones'][name], baseline['bones'][name]
        if (distance(now['local_position'], row['local_position']) > tol['position'] or
                now['scale'] != row['scale']):
            preserved.append('bone %s local position/scale' % name)
    for name, row in baseline['bones'].items():
        if name in ARM_BONES:
            continue
        now = skel['bones'][name]
        if (distance(now['local_position'], row['local_position']) > tol['position'] or
                angle_deg(now['local_orientation'], row['local_orientation']) > tol['angle_degrees'] or
                now['scale'] != row['scale']):
            preserved.append('bone ' + name)
    for key in ('local', 'world'):
        if (distance(skel['model'][key + '_position'], baseline['model'][key + '_position']) > tol['position'] or
                angle_deg(skel['model'][key + '_orientation'], baseline['model'][key + '_orientation']) >
                tol['angle_degrees']):
            preserved.append('model ' + key)
    for name in ('rig_root', 'CollarL'):
        if (distance(skel['handles'][name]['world_position'], baseline['handles'][name]['world_position']) >
                tol['position'] or angle_deg(skel['handles'][name]['world_orientation'],
                                             baseline['handles'][name]['world_orientation']) >
                tol['angle_degrees']):
            preserved.append('handle ' + name)
    if angle_deg(skel['handles']['Elbow_l']['local_orientation'],
                 baseline['handles']['Elbow_l']['local_orientation']) > tol['angle_degrees']:
        preserved.append('handle Elbow_l orientation')
    preserved.extend(weight_and_scale_changes(skel, baseline))
    if primary and secondary:
        state = 'TRANSFERRED'
    elif primary != secondary:
        state = 'ORACLE_DISAGREEMENT'
    elif base:
        state = 'BASELINE'
    else:
        state = 'PARTIAL'
    goal_errors = input_errors(skel, baseline, plan, 'TRANSFERRED', tol)
    base_errors = input_errors(skel, baseline, plan, 'BASELINE', tol)
    inputs = goal_errors if expect == 'TRANSFERRED' else base_errors
    correct = state == expect and not preserved and not inputs
    other = 'BASELINE' if expect == 'TRANSFERRED' else 'TRANSFERRED'
    return {'state': state, 'expected': expect, 'correct': correct, 'previous_state_remains': state == other,
            'unrelated_changes': preserved[:64], 'unrelated_change_count': len(preserved), 'bones': rows,
            'inputs_ok': not inputs, 'input_errors': inputs, 'inputs_at_goal': not goal_errors,
            'inputs_at_baseline': not base_errors, 'hand_target_residual': hand_residual(skel)}


def source_preserved(skel, baseline, tol):
    """shot15 evaluated state after a round trip (within tolerance), including
    constraint weights and model/handle/bone scale state."""
    changes = []
    for name, row in baseline['bones'].items():
        now = skel['bones'][name]
        if (distance(now['local_position'], row['local_position']) > tol['position'] or
                angle_deg(now['local_orientation'], row['local_orientation']) > tol['angle_degrees'] or
                now['scale'] != row['scale']):
            changes.append('bone ' + name)
    for b in ARM_BONES:
        if (distance(skel['bones'][b]['world_position'], baseline['bones'][b]['world_position']) > tol['position']
                or angle_deg(skel['bones'][b]['world_orientation'], baseline['bones'][b]['world_orientation']) >
                tol['angle_degrees']):
            changes.append('world ' + b)
    for name in HANDLE_NAMES:
        if (distance(skel['handles'][name]['world_position'], baseline['handles'][name]['world_position']) >
                tol['position'] or angle_deg(skel['handles'][name]['world_orientation'],
                                             baseline['handles'][name]['world_orientation']) >
                tol['angle_degrees']):
            changes.append('handle ' + name)
    for key in ('local', 'world'):
        if (distance(skel['model'][key + '_position'], baseline['model'][key + '_position']) > tol['position'] or
                angle_deg(skel['model'][key + '_orientation'], baseline['model'][key + '_orientation']) >
                tol['angle_degrees']):
            changes.append('model ' + key)
    changes.extend(weight_and_scale_changes(skel, baseline))
    return changes


# ---------------------------------------------------------------------------
# Undo state and native writes
# ---------------------------------------------------------------------------

def undo_state(dm):
    def call(name):
        try:
            value = getattr(dm, name)()
            return text(value) if isinstance(value, (bytes, text_type)) else value
        except Exception as exc:
            return {'unreadable': repr(exc)}
    return {'enabled': call('IsUndoEnabled'), 'can_undo': call('CanUndo'), 'can_redo': call('CanRedo'),
            'undo_desc': call('GetUndoDesc'), 'redo_desc': call('GetRedoDesc'),
            'item_count_recorded_only': call('GetUndoItemCount')}


def constructors(vs):
    vector = getattr(vs, 'Vector', None) or getattr(getattr(vs, 'mathlib', None), 'Vector', None)
    quaternion = getattr(vs, 'Quaternion', None) or getattr(getattr(vs, 'mathlib', None), 'Quaternion', None)
    if vector is None or quaternion is None:
        raise Unresolved('Native Vector/Quaternion constructors unavailable')
    return vector, quaternion


def native_value(vs, kind, values):
    vector, quaternion = constructors(vs)
    return quaternion(*values) if kind == 'quaternion' else vector(*values)


def readback(layer, index, kind):
    value = layer.GetKeyValue(index)
    return quat(value) if kind == 'quaternion' else vec3(value)


def write_key(vs, target, index, values):
    """One authorised key-value write followed by its exact float32 readback."""
    layer = target['layer']
    count = int(layer.GetKeyCount())
    before_ticks = ticks_of(layer.GetKeyTime(index))
    layer.SetKeyValue(int(index), native_value(vs, target['kind'], values))
    got = readback(layer, index, target['kind'])
    return {'index': index, 'ticks': before_ticks, 'requested_float32': list(values), 'readback': got,
            'exact': got == list(values), 'count_unchanged': int(layer.GetKeyCount()) == count,
            'time_unchanged': ticks_of(layer.GetKeyTime(index)) == before_ticks}


def expected_committed(authored, plan):
    """The destination's authored state with exactly the six values replaced
    (derived from the baseline and the plan; never stored separately)."""
    result = json.loads(json.dumps(authored))
    by_handle = dict((row['id']['handle'], row) for row in result['channels'])
    for name in sorted(plan['write_channels']):
        w = plan['write_channels'][name]
        keys = by_handle[w['channel_handle']]['layers'][0]['keys']
        for i in w['indices']:
            keys[i][1] = list(plan['write_float32'][name])
    return roundtrip(result)


def log_values_at_clocks(vs, targets, skel_rows):
    out = {}
    for name, t in targets.items():
        row = skel_rows[name]
        out[name] = {'current': plain(t['log'].GetValue(t['channel'].GetCurrentTime())),
                     'nominal': plain(t['log'].GetValue(vs.DmeTime_t(row['nominal_seconds'])))}
    return out


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def reports_dir(config):
    return config['reports_dir']


def read_ledger(config):
    d = reports_dir(config)
    entries = []
    for name in sorted(os.listdir(d)):
        m = REPORT_RE.match(name)
        if m is None:
            if name.startswith('F01W1-') and name.endswith('.json'):
                raise Stop('Unrecognised report name in ledger: ' + name)
            continue
        path = os.path.join(d, name)
        with open(path, 'rb') as f:
            raw = f.read()
        if not raw:
            raise Stop('Report %s is empty: a previous step did not finish. Do not continue.' % name)
        entries.append({'seq': int(m.group(1)), 'step': m.group(2), 'path': path, 'sha256':
                        hashlib.sha256(raw).hexdigest(), 'report': json.loads(raw.decode('utf-8'))})
    for i, e in enumerate(entries):
        if e['seq'] != i + 1:
            raise Stop('Ledger sequence is not contiguous')
        if i and e['report'].get('previous_report_sha256') != entries[i - 1]['sha256']:
            raise Stop('Ledger hash chain is broken at %s' % os.path.basename(e['path']))
    return entries


def due_step(entries):
    if not entries:
        return {'step': 'SOURCE_BASELINE', 'place': 'source', 'stage': None}
    last = entries[-1]['report']
    if last.get('status') != 'CONTINUE':
        return None
    return last['next']


def load_baselines(entries):
    found = {}
    for e in entries:
        r = e['report']
        for key in ('source_baseline', 'destination_baseline', 'plan'):
            if key in r:
                found[key] = r[key]
    return found


# ---------------------------------------------------------------------------
# Runtime (one asynchronous step at a time)
# ---------------------------------------------------------------------------

def runtime():
    module = sys.modules.get(RUNTIME_MODULE)
    if module is None:
        import types
        module = types.ModuleType(RUNTIME_MODULE)
        module.active = None
        module.timers = []
        sys.modules[RUNTIME_MODULE] = module
    return module


def schedule(fn):
    """One ordinary event-loop opportunity, then fn. The timer is retained
    until it has fired; there is no polling and no forced evaluation."""
    from PySide import QtCore
    rt = runtime()
    timer = QtCore.QTimer()
    timer.setSingleShot(True)

    def fire():
        try:
            rt.timers.remove(timer)
        except ValueError:
            pass
        fn()
    timer.timeout.connect(fire)
    rt.timers.append(timer)
    timer.start(0)


class Step(object):
    """One ledger step: an exclusively reserved report, written exactly once."""

    def __init__(self, config, entries, due):
        self.config = config
        self.entries = entries
        self.due = due
        self.seq = len(entries) + 1
        self.path = os.path.join(reports_dir(config), 'F01W1-%02d-%s.json' % (self.seq, due['step']))
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.report = {'format': FORMAT, 'seq': self.seq, 'step': due['step'], 'place': due['place'],
                       'stage': due.get('stage'), 'utc_start': utc(), 'python': sys.version,
                       'pid': os.getpid(), 'status': 'INCONCLUSIVE', 'events': [],
                       'previous_report_sha256': entries[-1]['sha256'] if entries else None}
        self.closed = False

    def event(self, name, **data):
        row = {'event': name, 'utc': utc()}
        row.update(data)
        self.report['events'].append(row)

    def finish(self, status, next_step=None, error=None, tb=None):
        if self.closed:
            return
        self.closed = True
        self.report['status'] = status
        if next_step is not None:
            self.report['next'] = next_step
        if error is not None:
            self.report['error'] = error
        if tb is not None:
            self.report['traceback'] = tb
        try:
            self.report['integrity_after'] = integrity(self.config)
            before = self.report.get('integrity_before')
            if before is not None and before != self.report['integrity_after']:
                raise Stop('Protected file, harness, config or CPM source changed during the step')
        except Exception as exc:
            self.report['status'] = 'STOP'
            self.report['integrity_error'] = repr(exc)
            self.report.pop('next', None)
        # Set only for steps that ended normally: every capture in them was
        # complete (incomplete evidence raises before a step can continue).
        self.report['evidence_complete'] = self.report['status'] in ('CONTINUE', 'COMPLETE_PENDING_CLOSE')
        self.report['utc_end'] = utc()
        with os.fdopen(self.fd, 'wb') as stream:
            stream.write(json.dumps(self.report, indent=1, sort_keys=True, ensure_ascii=True,
                                    allow_nan=False).encode('ascii'))
        rt = runtime()
        rt.active = None
        print('F01W1 step %02d %s: %s' % (self.seq, self.report['step'], self.report['status']))
        print('Report: ' + self.path)
        if self.report['status'] == 'CONTINUE':
            print('NEXT: ' + self.report['next']['instruction'])
        elif self.report['status'] == 'COMPLETE_PENDING_CLOSE':
            print('NEXT: All experiment steps are complete. Close the disposable session WITHOUT saving, quit '
                  'SFM, then run tools/finalize_f01w1.py as described in RUNBOOK.md.')
        else:
            print('NEXT: Do not submit further steps. Close the disposable session WITHOUT saving, quit SFM, '
                  'then run tools/finalize_f01w1.py as described in RUNBOOK.md.')
            if self.report.get('error'):
                print('Reason: ' + self.report['error'])


def utc():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def instruction(step, place, stage, config):
    spec = config['places'][place]
    where = 'movie frame %d (%s)' % (spec['movie_frame'], spec['shot'])
    texts = {
        'TRANSFER': 'Move the playhead to %s, let it settle, then submit NEXT_STEP.txt once. Do not interact '
                    'until the step reports.' % where,
        'RETIME': 'Move the playhead to movie frame %d, let it settle, then back to %s, let it settle, then '
                  'submit NEXT_STEP.txt once.' % (config['retime_frame'], where),
        'SOURCE_RETURN': 'Move the playhead to %s, let it settle, then submit NEXT_STEP.txt once.' % where,
        'DESTINATION_RETURN': 'Move the playhead to %s, let it settle, then submit NEXT_STEP.txt once.' % where,
        'UNDO': 'Stay at %s and submit NEXT_STEP.txt once. Do not interact until the step reports.' % where,
        'REDO': 'Stay at %s and submit NEXT_STEP.txt once. Do not interact until the step reports.' % where,
        'FINAL_UNDO': 'Stay at %s and submit NEXT_STEP.txt once. Do not interact until the step reports.' % where,
    }
    return texts[step]


def nxt(step, place, stage, config):
    return {'step': step, 'place': place, 'stage': stage,
            'instruction': instruction(step, place, stage, config)}


def after_stage_observed(stage, config):
    return nxt('SOURCE_RETURN', 'source', stage, config)


def after_destination_return(stage, config):
    following = {'committed': 'UNDO', 'undone': 'REDO', 'redone': 'FINAL_UNDO'}
    if stage == 'final':
        return None
    return nxt(following[stage], 'destination', {'committed': 'undone', 'undone': 'redone',
                                                  'redone': 'final'}[stage], config)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def capture_shot(sfmApp, vs, config, place):
    L = resolve(sfmApp, vs, config, place)
    skel = capture_skeleton(L, vs)
    skel['arm_op_handles'] = dict((k, handle(v)) for k, v in L['arm_ops'].items())
    return L, roundtrip(capture_authored(L)), roundtrip(capture_observed(L)), roundtrip(skel)


def verify_unchanged_context(step, L_token):
    if L_token['pid'] != step.report['pid']:
        raise Stop('Process changed')


def check_authored(label, now, expected):
    diffs = differences(now, expected)
    if diffs:
        raise Stop('Unexpected authored state (%s): %s' % (label, diffs[:16]))


def observed_changes(now, baseline):
    return differences(now, baseline)


def step_source_baseline(step, sfmApp, vs, config):
    L, auth, observed, skel = capture_shot(sfmApp, vs, config, 'source')
    step.report['context'] = L['token']
    hold = hold_state(skel, config, 'source')
    step.report['source_baseline'] = {'authored': auth, 'observed': observed, 'skeleton': skel,
                                      'context': L['token'], 'authored_sha256': canonical_sha(auth),
                                      'hold': hold}
    step.report['coverage'] = {'channels': len(auth['channels']), 'keys': auth['keys'],
                               'layer_types': layer_types(auth)}
    step.finish('CONTINUE', nxt('TRANSFER', 'destination', 'committed', config))


def step_transfer(step, sfmApp, vs, config, base):
    """Preflight, then (after the invocation returns) abort check, evaluated
    check, committed transfer and one idle observation."""
    src = base['source_baseline']
    tol = config['tolerances']
    L, auth, observed, skel = capture_shot(sfmApp, vs, config, 'destination')
    verify_unchanged_context(step, L['token'])
    if L['token']['pid'] != src['context']['pid'] or L['token']['document'] != src['context']['document']:
        raise Stop('Source baseline was captured in a different process or document')
    step.report['context'] = L['token']
    # Source authored state is readable at any playhead and must be unchanged.
    src_now = roundtrip(capture_authored(resolve_other(sfmApp, vs, config, L)))
    check_authored('source', src_now, src['authored'])
    hold = hold_state(skel, config, 'destination')
    targets = write_targets(L, config)
    index = writer_index(sfmApp)
    check_writers(L, targets, index)
    compat = compatibility(src['skeleton'], skel, src['authored'], auth, tol)
    hand_o = targets['Hand_l_o']
    reference = readback(hand_o['layer'], hand_o['bracket']['indices'][0], 'quaternion')
    plan = compute_goals(src['skeleton'], skel, config, reference)
    dm = vs.g_pDataModel
    undo0 = undo_state(dm)
    if undo0['enabled'] is not True:
        raise Stop('Native Undo is not enabled')
    for name, t in targets.items():
        native_value(vs, t['kind'], plan['write_float32'][name])
    nonce = binascii.hexlify(os.urandom(6)).decode('ascii')
    plan['nonce'] = nonce
    plan['descs'] = {'abort_undo': 'F01W1 abort check %s' % nonce, 'abort_redo': 'F01W1 abort check redo %s' % nonce,
                     'commit_undo': 'F01W1 arm transfer %s' % nonce, 'commit_redo': 'F01W1 arm transfer redo %s' % nonce}
    plan['brackets'] = dict((n, t['bracket']) for n, t in targets.items())
    plan['write_channels'] = dict((n, {'channel_handle': handle(t['channel']), 'layer_handle': handle(t['layer']),
                                       'indices': t['bracket']['indices']}) for n, t in targets.items())
    step.report['destination_baseline'] = {'authored': auth, 'observed': observed, 'skeleton': skel,
                                           'context': L['token'], 'authored_sha256': canonical_sha(auth),
                                           'hold': hold}
    step.report['plan'] = roundtrip(plan)
    committed = expected_committed(auth, step.report['plan'])
    arm_transforms = set(skel['bones'][b]['transform_handle'] for b in compat['arm_chain'])
    arm_writers = []
    for h in sorted(L['inventory']):
        ch = L['inventory'][h][0]
        to = field(ch, 'toElement')
        if to.get('status') == 'READ' and to['value'] is not None and to['value']['handle'] in arm_transforms:
            arm_writers.append({'channel': ident(ch), 'to': to['value'], 'attribute': field(ch, 'toAttribute')})
    step.report['preflight'] = {'compatibility': compat, 'arm_bone_writers_preserved': arm_writers, 'writers': {'channels': index['channels'],
                                'operators': index['operators'], 'operator_types': index['operator_types']},
                                'undo_state': undo0, 'coverage': {'channels': len(auth['channels']),
                                'keys': auth['keys'], 'layer_types': layer_types(auth)},
                                'element_undo_enabled': element_undo(dm, targets)}
    step.event('preflight-complete')
    plan = step.report['plan']
    state = {'targets': targets}

    def entry(label):
        Lx = resolve(sfmApp, vs, config, 'destination')
        if Lx['token'] != L['token']:
            raise Stop('Context changed before %s' % label)
        tx = write_targets(Lx, config)
        for n in tx:
            if handle(tx[n]['channel']) != handle(targets[n]['channel']) or \
                    handle(tx[n]['layer']) != handle(targets[n]['layer']) or \
                    tx[n]['bracket'] != targets[n]['bracket']:
                raise Stop('Write target %s changed before %s' % (n, label))
        return Lx, tx

    def abort_check():
        Lx, tx = entry('abort check')
        now = roundtrip(capture_authored(Lx))
        check_authored('destination before abort check', now, auth)
        before = undo_state(dm)
        name = 'Hand_l_p'
        index_ = tx[name]['bracket']['indices'][0]
        record, items, failure = None, None, None
        dm.StartUndo(native_name(plan['descs']['abort_undo']), native_name(plan['descs']['abort_redo']))
        try:
            record = write_key(vs, tx[name], index_, plan['write_float32'][name])
            if callable(getattr(dm, 'ItemsAddedToCurrentUndo', None)):
                items = bool(dm.ItemsAddedToCurrentUndo())
        except Exception as exc:
            failure = exc
        try:
            dm.AbortUndoableOperation()
        except Exception as exc:
            step.event('abort-check', write=record, failure=repr(failure), abort_error=repr(exc),
                       undo_before=before)
            raise Stop('AbortUndoableOperation raised; recovery unverified')
        after = undo_state(dm)
        restored = recovery_capture(Lx)
        diffs = differences(restored, auth)
        step.event('abort-check', write=record, write_failure=repr(failure) if failure else None,
                   items_added_recorded_only=items, undo_before=before, undo_after=after,
                   authored_restored=not diffs, differences=diffs[:32])
        if diffs:
            raise Stop('Abort did not restore the authored state exactly: %s' % diffs[:16])
        if failure is not None:
            raise Stop('The abort-check write raised %r (authored state restored)' % (failure,))
        if not (record['exact'] and record['count_unchanged'] and record['time_unchanged']):
            raise Stop('The abort-check write did not take effect as requested; the abort test is not meaningful')
        src_now_ = recovery_read(lambda: roundtrip(capture_authored(resolve_other(sfmApp, vs, config, Lx))),
                                 'source authored state after abort')
        check_authored('source after abort', src_now_, src['authored'])
        schedule(guarded(step, abort_evaluated, recovery=True))

    def abort_evaluated():
        Lx, tx = entry('abort evaluated check')
        sk = roundtrip(capture_skeleton(Lx, vs))
        result = classify(sk, skel, plan, 'BASELINE', tol)
        step.event('abort-evaluated', observation=result,
                   interpretation='Recorded only: unchanged evaluated outputs after the abort do not prove '
                                  'evaluated rollback; committed Undo provides that evidence.')
        if not result['correct']:
            raise Stop('After the aborted write and one idle opportunity the evaluated state is not the baseline')
        schedule(guarded(step, commit))

    def commit():
        Lx, tx = entry('commit')
        now = roundtrip(capture_authored(Lx))
        check_authored('destination before commit', now, auth)
        before = undo_state(dm)
        writes = []
        open_txn = [False]
        finished = False
        try:
            dm.StartUndo(native_name(plan['descs']['commit_undo']), native_name(plan['descs']['commit_redo']))
            open_txn[0] = True
            for name, _, _, _, _, _, _ in WRITE_CHANNELS:
                for i in tx[name]['bracket']['indices']:
                    r = write_key(vs, tx[name], i, plan['write_float32'][name])
                    r['channel'] = name
                    writes.append(r)
                    if not (r['exact'] and r['count_unchanged'] and r['time_unchanged']):
                        raise Stop('float32 readback mismatch on %s key %d' % (name, i))
            authored_now = roundtrip(capture_authored(Lx))
            diffs = differences(authored_now, committed)
            if diffs:
                raise Stop('Authored state after the six writes is not exactly the planned state: %s' % diffs[:16])
            src_now_ = roundtrip(capture_authored(resolve_other(sfmApp, vs, config, Lx)))
            check_authored('source during commit', src_now_, src['authored'])
            clocks = roundtrip(log_values_at_clocks(vs, tx, skel['arm_channels']))
            for name in clocks:
                for clock in ('current', 'nominal'):
                    got, want = clocks[name][clock], plan['write_float32'][name]
                    if len(want) == 4:
                        bad = angle_deg(got, want) > config['tolerances']['log_evaluation_angle_degrees']
                    else:
                        bad = distance(got, want) > config['tolerances']['log_evaluation_position']
                    if bad:
                        raise Stop('Native log evaluation of %s at the %s clock is not the written value' %
                                   (name, clock))
            dm.FinishUndo()
            open_txn[0] = False
            finished = True
        except Exception as commit_exc:
            if open_txn[0]:
                open_txn[0] = False
                # The original failure is carried into every recovery outcome.
                failure = repr(commit_exc)
                try:
                    dm.AbortUndoableOperation()
                except Exception as exc:
                    step.event('commit-abort-failed', error=repr(exc), commit_failure=failure)
                    raise Stop('Commit failed and AbortUndoableOperation raised; recovery unverified '
                               '(commit failure: %s)' % failure)
                # Recovery is verified only when the destination is restored AND
                # the source is preserved; either read unreadable is STOP.
                try:
                    restored = recovery_capture(Lx)
                    src_after = recovery_read(
                        lambda: roundtrip(capture_authored(resolve_other(sfmApp, vs, config, Lx))),
                        'source authored state after commit abort')
                except Stop as exc:
                    step.event('commit-aborted', writes=writes, commit_failure=failure, recovery_error=str(exc))
                    raise Stop('%s (commit failure: %s)' % (exc, failure))
                diffs = differences(restored, auth)
                src_diffs = differences(src_after, src['authored'])
                step.event('commit-aborted', writes=writes, commit_failure=failure, authored_restored=not diffs,
                           differences=diffs[:32], source_preserved=not src_diffs,
                           source_differences=src_diffs[:32])
                if diffs:
                    raise Stop('Commit failed and the abort did not restore the authored state; recovery '
                               'unverified (commit failure: %s)' % failure)
                if src_diffs:
                    raise Stop('Commit failed and the source authored state differs from its baseline after the '
                               'abort; recovery unverified (commit failure: %s)' % failure)
            raise
        after = undo_state(dm)
        step.event('commit', writes=writes, undo_before=before, undo_after=after, finished=finished)
        if after.get('undo_desc') != plan['descs']['commit_undo'] or after.get('can_undo') is not True:
            raise Stop('After FinishUndo the top Undo entry is not this transaction; ownership uncertain')
        check_authored('destination after commit', roundtrip(capture_authored(Lx)), committed)
        step.report['commit_undo_state'] = after
        schedule(guarded(step, observe_idle))

    def observe_idle():
        Lx, tx = entry('idle observation')
        check_authored('destination at idle observation', roundtrip(capture_authored(Lx)), committed)
        sk = roundtrip(capture_skeleton(Lx, vs))
        result = classify(sk, skel, plan, 'TRANSFERRED', tol)
        step.report['observation'] = result
        step.report['observed_changes'] = observed_changes(roundtrip(capture_observed(Lx)), observed)
        finish_observation(step, 'committed', result, config)

    schedule(guarded(step, abort_check))
    return 'ASYNC'


def element_undo(dm, targets):
    out = {}
    if not callable(getattr(dm, 'UndoEnabledForElement', None)):
        return 'unavailable'
    for name, t in targets.items():
        try:
            out[name] = bool(dm.UndoEnabledForElement(t['layer']))
        except Exception as exc:
            out[name] = repr(exc)
    return out


def resolve_other(sfmApp, vs, config, L):
    """The other shot's authored state, read without moving the playhead:
    resolve that shot by name from the movie, then its animation set,
    controls, channels and relationships."""
    other_place = 'source' if L['place'] == 'destination' else 'destination'
    spec = config['places'][other_place]
    movie = sfmApp.GetMovie()
    shots = []
    stack = [movie]
    seen = set()
    while stack:
        el = stack.pop()
        h = handle(el)
        if h in seen:
            continue
        seen.add(h)
        kind = type_of(el)
        if kind == 'DmeFilmClip':
            if text(el.GetName()) == spec['shot'] and h != handle(movie):
                shots.append(el)
            if has_attr(el, 'subClipTrackGroup'):
                sub = attr(el, 'subClipTrackGroup')
                if sub is not None:
                    stack.append(sub)
        elif kind == 'DmeTrackGroup':
            stack.extend(sequence(attr(el, 'tracks')))
        elif kind == 'DmeTrack':
            stack.extend(x for x in sequence(attr(el, 'children')) if type_of(x) == 'DmeFilmClip')
    shot = unique(shots, 'Shot ' + spec['shot'])
    O = {'shot': shot, 'place': other_place}
    animset = unique([x for x in sequence(attr(shot, 'animationSets'))
                      if text(x.GetName()) == config['animation_set']], 'Animation set (other shot)')
    O['animset'] = animset
    nodes, parents = walk(attr(shot, 'scene'))
    O['nodes'], O['parents'] = nodes, parents
    regs = []
    for obj in nodes.values():
        if type_of(obj) == 'DmeRig':
            for reg in sequence(attr(obj, 'animSetList')):
                linked = attr(reg, 'animationSet')
                if linked is not None and handle(linked) == handle(animset):
                    regs.append(reg)
    O['owned'] = sequence(attr(unique(regs, 'Rig registration (other shot)'), 'elementList'))
    O['rig_handles'] = dict((text(x.GetName()), x) for x in O['owned'] if type_of(x) == 'DmeRigHandle')
    O['all_controls'] = sequence(attr(animset, 'controls'))
    # The shot's time map is irrelevant to authored data; only membership is used.
    O['inventory'] = shot_inventory(shot, 0.0, vs)
    operators = sequence(attr(animset, 'operators'))
    seen_ops = set(handle(x) for x in operators)
    for op in sequence(attr(shot, 'operators')):
        if handle(op) not in seen_ops:
            operators.append(op)
            seen_ops.add(handle(op))
    O['operators'] = operators
    return O


def finish_observation(step, stage, result, config):
    if result['correct']:
        step.report['propagation'] = 'IDLE'
        step.finish('CONTINUE', after_stage_observed(stage, config))
        return
    step.report['propagation'] = 'NOT_AT_IDLE'
    step.report['idle_result'] = 'PREVIOUS_STATE_REMAINS' if result['previous_state_remains'] else 'INCORRECT_OR_PARTIAL'
    step.finish('CONTINUE', nxt('RETIME', 'destination', stage, config))


def guarded(step, fn, recovery=False):
    """Every callback ends in exactly one report; nothing escapes silently. A
    callback that verifies a restoration (recovery=True) turns unreadable
    evidence into STOP: recovery unverified."""
    def run():
        try:
            fn()
        except Stop as exc:
            step.finish('STOP', error=str(exc), tb=traceback.format_exc())
        except Fail as exc:
            step.finish('FAIL', error=str(exc), tb=traceback.format_exc())
        except Unresolved as exc:
            if recovery:
                step.finish('STOP', error='Recovery unverified: %s' % (exc,), tb=traceback.format_exc())
            else:
                step.finish('INCONCLUSIVE', error=str(exc), tb=traceback.format_exc())
        except Exception as exc:
            step.finish('STOP', error='Unexpected error: %r' % (exc,), tb=traceback.format_exc())
    return run


def expected_authored(stage, base):
    if STAGE_EXPECT[stage] == 'TRANSFERRED':
        return expected_committed(base['destination_baseline']['authored'], base['plan'])
    return base['destination_baseline']['authored']


def common_destination(step, sfmApp, vs, config, base, stage):
    L = resolve(sfmApp, vs, config, 'destination')
    if L['token']['pid'] != base['destination_baseline']['context']['pid'] or \
            L['token']['document'] != base['destination_baseline']['context']['document']:
        raise Stop('Process or document changed since the transfer step')
    step.report['context'] = L['token']
    check_authored('destination (%s)' % stage, roundtrip(capture_authored(L)), expected_authored(stage, base))
    check_authored('source (%s)' % stage, roundtrip(capture_authored(resolve_other(sfmApp, vs, config, L))),
                   base['source_baseline']['authored'])
    return L


def step_retime(step, sfmApp, vs, config, base):
    stage = step.due['stage']
    L = common_destination(step, sfmApp, vs, config, base, stage)
    sk = roundtrip(capture_skeleton(L, vs))
    result = classify(sk, base['destination_baseline']['skeleton'], base['plan'], STAGE_EXPECT[stage],
                      config['tolerances'])
    step.report['observation'] = result
    step.report['observed_changes'] = observed_changes(roundtrip(capture_observed(L)),
                                                       base['destination_baseline']['observed'])
    if not result['correct']:
        raise Fail('Still not the expected %s state after the prescribed retime (%s)' %
                   (STAGE_EXPECT[stage], result['state']))
    step.report['propagation'] = 'RETIMING_DEPENDENT'
    step.finish('CONTINUE', after_stage_observed(stage, config))


def step_source_return(step, sfmApp, vs, config, base):
    stage = step.due['stage']
    L = resolve(sfmApp, vs, config, 'source')
    src = base['source_baseline']
    if L['token']['pid'] != src['context']['pid'] or L['token']['document'] != src['context']['document']:
        raise Stop('Process or document changed')
    step.report['context'] = L['token']
    check_authored('source (%s)' % stage, roundtrip(capture_authored(L)), src['authored'])
    check_authored('destination (%s)' % stage, roundtrip(capture_authored(resolve_other(sfmApp, vs, config, L))),
                   expected_authored(stage, base))
    sk = roundtrip(capture_skeleton(L, vs))
    changes = source_preserved(sk, src['skeleton'], config['tolerances'])
    step.report['source_evaluated_changes'] = changes
    step.report['observed_changes'] = observed_changes(roundtrip(capture_observed(L)), src['observed'])
    if changes:
        raise Fail('Source shot evaluated state changed: %s' % changes[:16])
    step.finish('CONTINUE', nxt('DESTINATION_RETURN', 'destination', stage, config))


def step_destination_return(step, sfmApp, vs, config, base):
    stage = step.due['stage']
    L = common_destination(step, sfmApp, vs, config, base, stage)
    sk = roundtrip(capture_skeleton(L, vs))
    result = classify(sk, base['destination_baseline']['skeleton'], base['plan'], STAGE_EXPECT[stage],
                      config['tolerances'])
    step.report['observation'] = result
    step.report['observed_changes'] = observed_changes(roundtrip(capture_observed(L)),
                                                       base['destination_baseline']['observed'])
    if not result['correct']:
        raise Fail('After returning from shot15 the destination is not the expected %s state (%s)' %
                   (STAGE_EXPECT[stage], result['state']))
    following = after_destination_return(stage, config)
    if following is None:
        step.report['experiment_complete'] = True
        step.finish('COMPLETE_PENDING_CLOSE')
        return
    step.finish('CONTINUE', following)


def step_history(step, sfmApp, vs, config, base, action):
    """UNDO, REDO or FINAL_UNDO of the owned commit, then one idle observation."""
    stage = step.due['stage']
    plan = base['plan']
    dm = vs.g_pDataModel
    before_stage = {'undone': 'committed', 'redone': 'undone', 'final': 'redone'}[stage]
    L = common_destination(step, sfmApp, vs, config, base, before_stage)
    token = L['token']

    def entry(label):
        Lx = resolve(sfmApp, vs, config, 'destination')
        if Lx['token'] != token:
            raise Stop('Context changed before %s' % label)
        return Lx

    def perform():
        Lx = entry(action)
        check_authored('destination before %s' % action, roundtrip(capture_authored(Lx)),
                       expected_authored(before_stage, base))
        before = undo_state(dm)
        if action == 'redo':
            if before.get('can_redo') is not True or before.get('redo_desc') != plan['descs']['commit_redo']:
                raise Stop('The top Redo entry is not the owned transfer; ownership uncertain')
            dm.Redo()
        else:
            if before.get('can_undo') is not True or before.get('undo_desc') != plan['descs']['commit_undo']:
                raise Stop('The top Undo entry is not the owned transfer; ownership uncertain')
            dm.Undo()
        after = undo_state(dm)
        step.event(action, undo_before=before, undo_after=after)
        now = recovery_capture(Lx)
        diffs = differences(now, expected_authored(stage, base))
        if diffs:
            raise Stop('%s did not produce the exact expected authored state: %s' % (action, diffs[:16]))
        src_now_ = recovery_read(lambda: roundtrip(capture_authored(resolve_other(sfmApp, vs, config, Lx))),
                                 'source authored state after %s' % action)
        check_authored('source after %s' % action, src_now_, base['source_baseline']['authored'])
        schedule(guarded(step, observe, recovery=True))

    def observe():
        Lx = entry('idle observation')
        check_authored('destination at idle observation', roundtrip(capture_authored(Lx)),
                       expected_authored(stage, base))
        sk = roundtrip(capture_skeleton(Lx, vs))
        result = classify(sk, base['destination_baseline']['skeleton'], plan, STAGE_EXPECT[stage],
                          config['tolerances'])
        step.report['observation'] = result
        step.report['observed_changes'] = observed_changes(roundtrip(capture_observed(Lx)),
                                                           base['destination_baseline']['observed'])
        finish_observation(step, stage, result, config)

    schedule(guarded(step, perform))
    return 'ASYNC'


def run_step(step, sfmApp, vs, config, entries):
    base = load_baselines(entries)
    name = step.due['step']
    if name == 'SOURCE_BASELINE':
        return step_source_baseline(step, sfmApp, vs, config)
    if name == 'TRANSFER':
        return step_transfer(step, sfmApp, vs, config, base)
    if name == 'RETIME':
        return step_retime(step, sfmApp, vs, config, base)
    if name == 'SOURCE_RETURN':
        return step_source_return(step, sfmApp, vs, config, base)
    if name == 'DESTINATION_RETURN':
        return step_destination_return(step, sfmApp, vs, config, base)
    if name in ('UNDO', 'FINAL_UNDO'):
        return step_history(step, sfmApp, vs, config, base, 'undo')
    if name == 'REDO':
        return step_history(step, sfmApp, vs, config, base, 'redo')
    raise Stop('Unknown step ' + name)


def main():
    try:
        prepared = prepare()
    except Exception as exc:
        # Nothing was reserved or touched: refuse and explain.
        print('F01W1 REFUSED before any step was reserved: %s' % (exc,))
        return
    if prepared is None:
        return
    execute(*prepared)


def prepare():
    config = load_config()
    rt = runtime()
    if rt.active is not None:
        print('F01W1: a step is still running (%s). Wait for it to report; nothing was done.' % rt.active)
        return None
    entries = read_ledger(config)
    due = due_step(entries)
    if due is None:
        print('F01W1: the experiment has ended (last status %s). Nothing was done. Close the session WITHOUT '
              'saving and run tools/finalize_f01w1.py.' % entries[-1]['report'].get('status'))
        return None
    if entries:
        # Only the harness/config identity is checked here; a protected-file
        # change is recorded as a STOP report by the step itself.
        first = entries[0]['report']
        harness_now = digest(os.path.join(BASE, 'f01w1_harness.py'))
        config_now = digest(os.path.join(BASE, 'config.json'))
        if (harness_now != first['integrity_before']['harness'] or
                config_now != first['integrity_before']['config']):
            # The ledger must be completed by the same reviewed harness and config.
            due = {'step': 'LEDGER_STOP', 'place': due['place'], 'stage': due.get('stage')}
    return config, entries, due


def execute(config, entries, due):
    rt = runtime()
    step = Step(config, entries, due)
    rt.active = '%02d %s' % (step.seq, due['step'])
    try:
        step.report['integrity_before'] = integrity(config)
        if due['step'] == 'LEDGER_STOP':
            raise Stop('Harness or config changed since the first step')
        if entries and step.report['integrity_before']['cpm_source'] != entries[0]['report'][
                'integrity_before']['cpm_source']:
            raise Stop('CPM source changed since the first step')
        import sfmApp
        import vs
        print('F01W1 step %02d %s running. Do not interact until it reports.' % (step.seq, due['step']))
        if run_step(step, sfmApp, vs, config, entries) == 'ASYNC':
            return
    except Stop as exc:
        step.finish('STOP', error=str(exc), tb=traceback.format_exc())
    except Fail as exc:
        step.finish('FAIL', error=str(exc), tb=traceback.format_exc())
    except Unresolved as exc:
        if due['step'] in ('RETIME', 'SOURCE_RETURN', 'DESTINATION_RETURN') and due.get('stage') in RECOVERY_STAGES:
            step.finish('STOP', error='Recovery unverified: %s' % (exc,), tb=traceback.format_exc())
        else:
            step.finish('INCONCLUSIVE', error=str(exc), tb=traceback.format_exc())
    except Exception as exc:
        step.finish('STOP', error='Unexpected error: %r' % (exc,), tb=traceback.format_exc())
    finally:
        if step.closed:
            rt.active = None


if __name__ == '__f01w1_owner_step__':
    main()
