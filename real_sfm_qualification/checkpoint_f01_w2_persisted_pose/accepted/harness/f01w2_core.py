# -*- coding: ascii -*-
"""F-01 W2 shared core: persisted left-arm pose capture (process A) and
independent reapplication after an SFM restart (process B).

Governing design: F01_W2_Astra_Corrected_Design_Contract_2026-10-28 (Astra:
ACCEPT WITH BOUNDED CORRECTIONS). Mechanisms are copied and adapted from the
accepted W1 harness (real_sfm_qualification/checkpoint_f01_w1_arm_transfer/
accepted/harness/f01w1_harness.py); the W1 files are not imported or altered.

This module is loaded by f01w2_capture.py and f01w2_apply.py. It performs no
scene mutation itself; the only native writes are made by f01w2_apply.py
through write_key() inside owned transactions. Python 2.7 (SFM) and 3 syntax.

W1 source-pose resolution (resolve_other) is deliberately NOT present here.
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

FORMAT = 'F01W2-v1'
CONFIG_FORMAT = 'F01W2-config-v1'
POSE_FORMAT = 'F01W2-left-arm-pose'
POSE_VERSION = 1
POSE_MAX_BYTES = 65536
POSE_MAX_MAGNITUDE = 1.0e6
QUATERNION_UNIT_TOLERANCE = 1e-4
BASE = os.path.dirname(os.path.abspath(__file__))
HARNESS_FILES = ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py')
RUNTIME_MODULE = 'f01w2_runtime'
REPORT_RE = re.compile(r'^F01W2-(\d{2})-([A-Z0-9_]+)\.json$')

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
OBSERVED_CHANNELS = (('Elbow_l_o', 'Elbow_l', 'orientationChannel', 'valueOrientation', 'orientation',
                      'DmeQuaternionLog', 'DmeQuaternionLogLayer'),)
KNOWN_OPERATORS = ('DmeExpressionOperator', 'DmePackColorOperator', 'DmeRigPointConstraintOperator',
                   'DmeRigOrientConstraintOperator', 'DmeRigIKConstraintOperator')
CONSTRAINT_OPERATORS = ('DmeRigPointConstraintOperator', 'DmeRigOrientConstraintOperator',
                        'DmeRigIKConstraintOperator')
SLAVE_ATTRS = ('slave', 'startJoint', 'midJoint', 'endJoint')
SOLVER_FIELDS = ('startOffset', 'midOffset', 'poleVector', 'mode')
ARM_CONSTRAINTS = ('ik', 'hand_orient', 'collar_point', 'collar_orient')
CONSTRAINT_TYPES = {'ik': 'DmeRigIKConstraintOperator', 'hand_orient': 'DmeRigOrientConstraintOperator',
                    'collar_point': 'DmeRigPointConstraintOperator',
                    'collar_orient': 'DmeRigOrientConstraintOperator'}
CONSTRAINT_TARGET_HANDLE = {'ik': 'Hand_l', 'hand_orient': 'Hand_l', 'collar_point': 'CollarL',
                            'collar_orient': 'CollarL'}
CONSTRAINT_SLAVE_BONE = {'hand_orient': 'bip_hand_l', 'collar_point': COLLAR_BONE, 'collar_orient': COLLAR_BONE}
IK_JOINTS = {'startJoint': 'bip_UpperArm_l', 'midJoint': 'bip_lowerArm_l', 'endJoint': 'bip_hand_l'}
# Attributes that are evaluated outputs rather than authored data.
EVALUATED_OPERATOR_OUTPUTS = {'DmeExpressionOperator': ('result',)}
STAGES = ('committed', 'undone', 'redone', 'final')
STAGE_EXPECT = {'committed': 'TRANSFERRED', 'undone': 'BASELINE', 'redone': 'TRANSFERRED', 'final': 'BASELINE'}
PROCESS_A_STEPS = ('CAPTURE',)
PROCESS_B_STEPS = ('APPLY', 'RETIME', 'UNDO', 'REDO', 'FINAL_UNDO')
# Every process B step after APPLY runs after APPLY's committed transaction: within these steps unreadable
# required evidence is unverified post-mutation evidence (STOP), never a pre-write refusal (Correction A).
POST_MUTATION_STEPS = ('RETIME', 'UNDO', 'REDO', 'FINAL_UNDO')


class Stop(Exception):
    """Invalid context, binding, ownership, integrity or authored-state failure."""


class Fail(Exception):
    """The experiment ran and its required result was not obtained."""


class Unresolved(Exception):
    """Required evidence could not be read: INCONCLUSIVE, never inferred."""


class PoseFormatError(Exception):
    """A pose file is not a valid F01W2-left-arm-pose version 1 document."""


# ---------------------------------------------------------------------------
# Strict native reads (W1 idioms, unchanged)
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


KEY_SERIALIZERS = {'DmeFloatLogLayer': key_float, 'DmeVector3LogLayer': vec3,
                   'DmeQuaternionLogLayer': quat, 'DmeColorLogLayer': key_color}


def require_readable(value, label):
    """Every required evidence record must have been read (or verifiably be
    absent). An UNREADABLE record is never accepted as preserved evidence."""
    problems = []

    def walk_(v, path):
        if len(problems) >= 8:
            return
        if isinstance(v, dict):
            if v.get('status') == 'UNREADABLE':
                problems.append(path)
            for k in sorted(v):
                walk_(v[k], path + '/' + text_type(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk_(x, path + '/%d' % i)
    walk_(value, '')
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
# Rigid-transform math, implementation A (W1: column vectors; quaternions
# x, y, z, w; compose(a, b) = a x b = parent x child)
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


IDENTITY_Q = [0.0, 0.0, 0.0, 1.0]


# ---------------------------------------------------------------------------
# Rigid-transform math, implementation B: 3x3 rotation matrices. Written
# independently of implementation A; it calls none of A's helpers.
# ---------------------------------------------------------------------------

def mb_from_quaternion(q):
    n = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    if n < 1e-9:
        raise Unresolved('Degenerate quaternion (matrix path)')
    x, y, z, w = q[0] / n, q[1] / n, q[2] / n, q[3] / n
    return [[1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)]]


def mb_to_quaternion(m):
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        q = [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        q = [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        q = [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def mb_mul(a, b):
    return [[a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j] for j in range(3)] for i in range(3)]


def mb_apply(m, v):
    return [m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3)]


def mb_transpose(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def mb_xf(position, q):
    return (list(position), mb_from_quaternion(q))


def mb_xf_mul(a, b):
    moved = mb_apply(a[1], b[0])
    return ([a[0][i] + moved[i] for i in range(3)], mb_mul(a[1], b[1]))


def mb_xf_inv(a):
    rt = mb_transpose(a[1])
    p = mb_apply(rt, a[0])
    return ([-p[0], -p[1], -p[2]], rt)


def mb_angle_deg(a, b):
    """Sign-invariant angle between two quaternions via their matrices."""
    r = mb_mul(mb_transpose(mb_from_quaternion(a)), mb_from_quaternion(b))
    c = max(-1.0, min(1.0, (r[0][0] + r[1][1] + r[2][2] - 1.0) / 2.0))
    return math.degrees(math.acos(c))


def mb_distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def mb_f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


# ---------------------------------------------------------------------------
# Process identity (Windows kernel32, read-only queries)
# ---------------------------------------------------------------------------

FILETIME_TICKS_PER_SECOND = 10000000
STILL_ACTIVE = 259
ERROR_INVALID_PARAMETER = 87
# States of one recorded process (F-05). Only the first three establish that it is no longer running.
EXITED_STATES = ('ABSENT', 'EXITED', 'PID_REUSED')


class WindowsProcesses(object):
    """Read-only process queries: OpenProcess(QUERY_LIMITED_INFORMATION),
    GetProcessTimes, GetExitCodeProcess, QueryFullProcessImageNameW,
    GetSystemTimeAsFileTime. No process is modified."""
    name = 'windows-kernel32'

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.wintypes = ctypes, wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k = k
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        k.GetCurrentProcess.argtypes = []
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k.GetProcessTimes.restype = wintypes.BOOL
        k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k.GetExitCodeProcess.restype = wintypes.BOOL
        k.GetSystemTimeAsFileTime.argtypes = [ctypes.POINTER(wintypes.FILETIME)]
        k.GetSystemTimeAsFileTime.restype = None
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
        k.QueryFullProcessImageNameW.restype = wintypes.BOOL

    def _ft(self, ft):
        return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)

    def now(self):
        ft = self.wintypes.FILETIME()
        self.k.GetSystemTimeAsFileTime(self.ctypes.byref(ft))
        return self._ft(ft)

    def _query(self, h):
        w, c = self.wintypes, self.ctypes
        created, exited, kernel, user = w.FILETIME(), w.FILETIME(), w.FILETIME(), w.FILETIME()
        if not self.k.GetProcessTimes(h, c.byref(created), c.byref(exited), c.byref(kernel), c.byref(user)):
            raise Unresolved('GetProcessTimes failed (%d)' % c.get_last_error())
        code = w.DWORD()
        if not self.k.GetExitCodeProcess(h, c.byref(code)):
            raise Unresolved('GetExitCodeProcess failed (%d)' % c.get_last_error())
        size = w.DWORD(1024)
        buf = c.create_unicode_buffer(1024)
        image = buf.value if self.k.QueryFullProcessImageNameW(h, 0, buf, c.byref(size)) else None
        return {'creation_filetime': self._ft(created), 'exit_code': int(code.value),
                'running': int(code.value) == STILL_ACTIVE, 'image': image}

    def current(self):
        row = self._query(self.k.GetCurrentProcess())
        row['pid'] = os.getpid()
        return row

    def _open(self, pid):
        h = self.k.OpenProcess(0x1000, False, int(pid))
        return h, (0 if h else int(self.ctypes.get_last_error()))

    def images(self):
        """(pid, image path) of every running process whose image can be queried. Best effort over the whole
        system: a process that cannot be opened (inaccessible, or gone since the enumeration) is skipped. Never a
        substitute for the strict lookup() of a recorded process."""
        c, w = self.ctypes, self.wintypes
        enum = getattr(self.k, 'K32EnumProcesses', None)
        if enum is None:
            raise Unresolved('K32EnumProcesses unavailable')
        enum.argtypes = [c.POINTER(w.DWORD), w.DWORD, c.POINTER(w.DWORD)]
        enum.restype = w.BOOL
        size = 4096
        while True:
            ids = (w.DWORD * size)()
            used = w.DWORD()
            if not enum(ids, c.sizeof(ids), c.byref(used)):
                raise Unresolved('EnumProcesses failed (%d)' % c.get_last_error())
            if used.value < c.sizeof(ids):
                break
            size *= 2
        out = []
        for i in range(used.value // c.sizeof(w.DWORD)):
            pid = int(ids[i])
            h, _ = self._open(pid)
            if not h:
                continue
            try:
                row = self._query(h)
            finally:
                self.k.CloseHandle(h)
            if row.get('running') and row.get('image'):
                out.append((pid, row['image']))
        return out

    def lookup(self, pid):
        """Strict lookup of one recorded process: None only when Windows reports that no process has this id
        (ERROR_INVALID_PARAMETER); otherwise its times and exit state. Access denied or any other failure raises
        Unresolved: it never reads as an exit."""
        h, error = self._open(pid)
        if not h:
            if error == ERROR_INVALID_PARAMETER:
                return None
            raise Unresolved('OpenProcess(%d) failed (%d); the process state is unknown' % (int(pid), error))
        try:
            row = self._query(h)
            row['pid'] = int(pid)
            return row
        finally:
            self.k.CloseHandle(h)


def process_provider():
    """The process-identity provider. Offline tests inject a fake through the
    harness runtime module; the provider's name is recorded in every report and
    the finalizer accepts only 'windows-kernel32' for a native PASS."""
    injected = getattr(runtime(), 'process_provider', None)
    if injected is not None:
        return injected
    return WindowsProcesses()


def process_evidence(provider):
    row = provider.current()
    if row.get('pid') != os.getpid() and getattr(provider, 'name', '') == 'windows-kernel32':
        raise Stop('Process identity query returned a different process')
    if not row.get('running'):
        raise Unresolved('Current process is not reported as running')
    return {'provider': provider.name, 'pid': int(row['pid']), 'creation_filetime': int(row['creation_filetime']),
            'image': row.get('image'), 'queried_filetime': int(provider.now())}


def same_process(a, b):
    return (a.get('pid') == b.get('pid') and a.get('creation_filetime') == b.get('creation_filetime')
            and a.get('provider') == b.get('provider'))


def recorded_process_state(provider, evidence):
    """Strict lookup of one recorded process (pid AND creation time).
    ABSENT: no process has this id; EXITED: that very process, no longer STILL_ACTIVE; PID_REUSED: the id belongs
    to a process with another creation time; RUNNING: that process is alive; UNKNOWN: the query could not be
    resolved (access denied or any other failure), which never establishes an exit."""
    try:
        row = provider.lookup(evidence['pid'])
    except Exception as exc:
        return {'state': 'UNKNOWN', 'error': repr(exc), 'lookup': None}
    if row is None:
        return {'state': 'ABSENT', 'error': None, 'lookup': None}
    try:
        created, running = int(row['creation_filetime']), row['running']
        if not isinstance(running, bool):
            raise ValueError('running flag %r' % (running,))
    except Exception as exc:
        return {'state': 'UNKNOWN', 'error': repr(exc), 'lookup': row}
    if created != int(evidence['creation_filetime']):
        state = 'PID_REUSED'
    else:
        state = 'RUNNING' if running else 'EXITED'
    return {'state': state, 'error': None, 'lookup': row}


# ---------------------------------------------------------------------------
# Configuration, integrity and context
# ---------------------------------------------------------------------------

def load_config():
    path = os.path.join(BASE, 'config.json')
    with open(path, 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
    check_config(config)
    return config


def check_config(config):
    if config.get('format') != CONFIG_FORMAT:
        raise Stop('Unexpected config format')
    keys = ('original_session', 'r2_fixture', 'capture_session', 'apply_session')
    paths = [normalized(config[k]) for k in keys]
    if len(set(paths)) != len(keys):
        raise Stop('Original session, R2 fixture and the two disposable copies must be four distinct files')
    for k in ('capture_session', 'apply_session'):
        if config[k + '_sha256'] != config['r2_fixture_sha256']:
            raise Stop('Each disposable copy must be byte-identical to the R2 fixture')
    run_dir = normalized(config['run_dir'])
    if normalized(os.path.dirname(config['pose_path'])) != normalized(os.path.join(run_dir, 'poses')) or \
            os.path.basename(config['pose_path']) != 'left_arm_pose.f01w2.json':
        raise Stop('pose_path must be <run dir>/poses/left_arm_pose.f01w2.json')
    if normalized(config['reports_dir']) != normalized(os.path.join(run_dir, 'reports')):
        raise Stop('reports_dir must be <run dir>/reports')
    for k in ('capture_session', 'apply_session'):
        if normalized(os.path.dirname(config[k])) != run_dir:
            raise Stop('%s must be inside the run directory' % k)
    return config


def integrity(config):
    """Protected files (must equal their configured hashes), the CPM source and
    the harness/config identity. The pose file is checked separately."""
    values = {}
    for key in ('original_session', 'r2_fixture', 'capture_session', 'apply_session', 'cpm_source'):
        values[key] = digest(config[key])
    for key in ('original_session', 'r2_fixture', 'capture_session', 'apply_session'):
        if values[key] != config[key + '_sha256']:
            raise Stop('Protected file hash changed: %s; preserve evidence and stop' % key)
    for name in HARNESS_FILES:
        values[name] = digest(os.path.join(BASE, name))
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


PLACE_SESSION = {'source': 'capture_session', 'destination': 'apply_session'}


def context(sfmApp, vs, config, place):
    """Process A works only in the capture copy at the source place; process B
    only in the application copy at the destination place."""
    check_ui()
    spec = config['places'][place]
    if not sfmApp.HasDocument():
        raise Stop('No document open')
    doc = sfmApp.GetDocumentRoot()
    path = text(vs.g_pDataModel.GetFileName(doc.GetFileId()))
    if normalized(path) != normalized(config[PLACE_SESSION[place]]):
        raise Stop('The open document is not the configured %s' % PLACE_SESSION[place])
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
# Scene resolution (fresh identities every step; W1, unchanged)
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


def binding_identity(L):
    """Every native identity a capture or application depends on. Compared
    exactly between the start and the completion of a step."""
    out = {'shot': handle(L['shot']), 'animset': handle(L['animset']), 'gm': handle(L['gm']),
           'registration': handle(L['reg']),
           'rig_handles': dict((k, handle(v)) for k, v in L['rig_handles'].items()),
           'controls': dict((k, handle(v)) for k, v in L['controls'].items()),
           'channels': {}, 'bones': {}, 'arm_ops': dict((k, handle(v)) for k, v in L['arm_ops'].items())}
    for name, ch in L['channels'].items():
        log = ch.GetLog()
        out['channels'][name] = {'channel': handle(ch), 'log': handle(log) if log is not None else None,
                                 'layers': [handle(log.GetLayer(i)) for i in range(int(log.GetNumLayers()))]
                                 if log is not None else []}
    for name, b in L['bones'].items():
        out['bones'][name] = [handle(b['dag']), handle(b['transform']), b['index']]
    return out


# ---------------------------------------------------------------------------
# Captures (W1, unchanged)
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


RECOVERY_STAGES = ('undone', 'redone', 'final')


def recovery_read(fn, label):
    """A read required to verify an Abort/Undo/Redo restoration. Unreadable
    evidence means the restoration cannot be verified: STOP."""
    try:
        return fn()
    except Unresolved as exc:
        raise Stop('Recovery unverified (%s): %s' % (label, exc))


def recovery_capture(Lx):
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
    """Every other operator/constraint attribute, excluding evaluated outputs."""
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
    out['arm_op_handles'] = dict((k, handle(v)) for k, v in L['arm_ops'].items())
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
# Bindings, write targets, writers (W1; binding split from bracket resolution)
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


def channel_binding(L, spec):
    """One rig-input channel verified by identity: control -> channel ->
    rig-handle transform attribute, Play mode, log/layer types, single layer,
    no curve info. Returns its native objects and portable role record."""
    name, owner, channel_attr, source_attr, dest_attr, log_type, layer_type = spec
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
    if isinstance(b['mode'], bool) or b['mode'] != 3:
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
    role = {'control': owner, 'control_attribute': channel_attr, 'from_attribute': source_attr,
            'from_index': 0, 'to_rig_handle': owner, 'to_attribute': dest_attr, 'to_index': 0, 'mode': 3,
            'log_type': log_type, 'layer_type': layer_type, 'layer_count': 1, 'curve_info': 'none'}
    return {'channel': ch, 'log': log, 'layer': layer,
            'kind': 'quaternion' if 'Quaternion' in layer_type else 'vector', 'role': role}


def write_targets(L, config):
    """Each write channel verified by identity and binding; its own bracket
    indices resolved from native key times."""
    targets = {}
    for spec in WRITE_CHANNELS:
        t = channel_binding(L, spec)
        t['bracket'] = find_bracket(t['layer'], config['bracket_ticks'])
        targets[spec[0]] = t
    return targets


def writer_index(sfmApp):
    """Document-wide channel and operator inventory, strict: any unreadable
    relationship is unresolved and stops before writing. Reads binding and
    graph metadata only (element identities, attribute names, logs, layers),
    never key values, stored control values or evaluated transforms."""
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


def writer_summary(index):
    return {'channels': index['channels'], 'operators': index['operators'],
            'operator_types': index['operator_types']}


# ---------------------------------------------------------------------------
# Structural checks of one side (W1 compatibility, per side, by identity)
# ---------------------------------------------------------------------------

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


def structural_checks(skel, auth, tol, side):
    """Every relationship W1 tested, on one side, by native identity: arm
    hierarchy, supported scales, rig_root parentage of the written handles,
    unit weights, single targets and their rig-handle identity, IK joints and
    pole target, constraint slaves."""
    chain = arm_chain(skel)
    if not set(ARM_BONES) <= set(chain):
        raise Stop('%s arm hierarchy does not contain the upper arm, lower arm and hand' % side)
    for name in chain:
        if not scale_ok(skel['bones'][name]['scale']):
            raise Stop('Unsupported scale on %s arm bone %s' % (side, name))
    root = skel['rig_root_handle']
    for name in HANDLE_NAMES:
        if not scale_ok(skel['handles'][name]['scale']):
            raise Stop('Unsupported scale on %s %s' % (side, name))
    if not scale_ok(skel['model']['scale']):
        raise Stop('Unsupported model scale (%s)' % side)
    for name in ('Hand_l', 'Elbow_l'):
        if skel['handles'][name]['parents'] != [root]:
            raise Stop('%s %s is not parented to rig_root' % (side, name))
        r = (skel['handles']['rig_root']['world_position'], skel['handles']['rig_root']['world_orientation'])
        h = skel['handles'][name]
        p, q = compose(r, (h['local_position'], h['local_orientation']))
        if (distance(p, h['world_position']) > tol['position'] or
                angle_deg(q, h['world_orientation']) > tol['angle_degrees']):
            raise Stop('%s %s world transform is not rig_root x local' % (side, name))
    for key in ARM_CONSTRAINTS:
        rows = skel['weights'].get(key) or []
        if len(rows) != 1 or abs(rows[0]['weight'] - 1.0) > tol['weight']:
            raise Stop('%s constraint %s must have one target of weight 1.0' % (side, key))
    ops = dict((o['id']['handle'], o) for o in auth['operators'])
    for key in ARM_CONSTRAINTS:
        op = ops[skel['arm_op_handles'][key]]
        if op['id']['type'] != CONSTRAINT_TYPES[key]:
            raise Stop('%s constraint %s has type %s' % (side, key, op['id']['type']))
        if len(op['targets']) != 1:
            raise Stop('%s constraint %s must have exactly one target' % (side, key))
        target = op['targets'][0]['target']
        expected = CONSTRAINT_TARGET_HANDLE[key]
        if target is None or target['handle'] != skel['handles'][expected]['handle']:
            raise Stop('%s constraint %s does not target rig handle %s' % (side, key, expected))
        weight_target = skel['weights'][key][0]['target']
        if weight_target is None or weight_target['handle'] != skel['handles'][expected]['handle']:
            raise Stop('%s constraint %s weight target is not rig handle %s' % (side, key, expected))
    ik = ops[skel['arm_op_handles']['ik']]
    if ik.get('pvTarget') is None or ik['pvTarget']['handle'] != skel['handles']['Elbow_l']['handle']:
        raise Stop('%s IK pole target is not the Elbow_l rig handle' % side)
    for k, bone in IK_JOINTS.items():
        joint = (ik['slaves'].get(k) or {}).get('target')
        if joint is None or joint['handle'] != skel['bones'][bone]['handle']:
            raise Stop('%s IK %s is not %s' % (side, k, bone))
    for key, bone in CONSTRAINT_SLAVE_BONE.items():
        slave = (ops[skel['arm_op_handles'][key]]['slaves'].get('slave') or {}).get('target')
        if slave is None or slave['handle'] != skel['bones'][bone]['handle']:
            raise Stop('%s constraint %s does not drive %s' % (side, key, bone))
    return {'arm_chain': chain}


def portable_value(record, path):
    """A typed, portable constraint field: required/absent distinguished; any
    element reference is not portable and refuses."""
    if record.get('status') == 'ABSENT':
        return {'present': False}
    value = required(record, path)

    def check(v):
        if isinstance(v, dict):
            raise Stop('Constraint field %s holds an element reference; unsupported representation' % path)
        if isinstance(v, list):
            if len(v) > 16:
                raise Stop('Constraint field %s is too long' % path)
            for x in v:
                if isinstance(x, (list, dict)):
                    raise Stop('Constraint field %s is nested; unsupported representation' % path)
                check(x)
        elif not (v is None or isinstance(v, (bool, float, text_type)) or isinstance(v, integer_types)):
            raise Stop('Constraint field %s has unsupported type' % path)
    check(value)
    return {'present': True, 'value': value}


def parent_role(L, element_handle):
    parents = [p for p in L['parents'].get(element_handle, []) if p is not None]
    if len(parents) != 1:
        raise Stop('Rig handle does not have exactly one parent')
    parent = L['nodes'][parents[0]]
    return {'type': type_of(parent), 'name': text(parent.GetName())}


def descriptor(L, skel, auth, bindings, tol):
    """The portable compatibility descriptor of one side, built only after the
    identity checks: names and typed values, never runtime handles."""
    structural = structural_checks(skel, auth, tol, L['place'])
    chain = []
    for name in structural['arm_chain']:
        row = skel['bones'][name]
        chain.append({'name': name, 'index': row['index'], 'parent': row['parent'],
                      'local_position': list(row['local_position'])})
    handles = {}
    for name in HANDLE_NAMES:
        handles[name] = {'parent': parent_role(L, skel['handles'][name]['handle'])}
    ops = dict((o['id']['handle'], o) for o in auth['operators'])
    constraints = {}
    for key in ARM_CONSTRAINTS:
        op = ops[skel['arm_op_handles'][key]]
        t = op['targets'][0]
        row = {'type': op['id']['type'], 'target_rig_handle': CONSTRAINT_TARGET_HANDLE[key],
               'target_weight': skel['weights'][key][0]['weight'],
               'offsets': {'oOffset': portable_value(t['oOffset'], key + '.oOffset'),
                           'vecOffset': portable_value(t['vecOffset'], key + '.vecOffset')},
               'solver': dict((n, portable_value(v, key + '.' + n)) for n, v in sorted(op['solver'].items()))}
        if key == 'ik':
            row['joints'] = dict(IK_JOINTS)
            row['pole_target_rig_handle'] = 'Elbow_l'
        else:
            row['slave_bone'] = CONSTRAINT_SLAVE_BONE[key]
        constraints[key] = row
    channels = dict((name, bindings[name]['role']) for name in sorted(bindings))
    return {'arm_chain': chain, 'scale_state': 'unit', 'handles': handles, 'constraints': constraints,
            'channels': channels}


def compare_descriptor(saved, live, tol):
    """Exact equality except arm-bone local offsets (W1 bone offset bound) and
    constraint target weights (W1 weight bound). Returns evidence; refuses on
    any other difference."""
    problems = []
    a, b = saved.get('arm_chain'), live.get('arm_chain')
    worst = 0.0
    if not isinstance(a, list) or len(a) != len(b):
        problems.append('arm chain length')
    else:
        for x, y in zip(a, b):
            if (x['name'], x['index'], x['parent']) != (y['name'], y['index'], y['parent']):
                problems.append('arm chain bone %s' % x['name'])
            else:
                worst = max(worst, distance(x['local_position'], y['local_position']))
        if worst > tol['bone_offset']:
            problems.append('arm bone local offsets differ (%.6g)' % worst)
    for key in ('scale_state', 'handles', 'channels'):
        problems.extend(differences(saved.get(key), live.get(key), key))
    sc, lc = saved.get('constraints') or {}, live.get('constraints') or {}
    if sorted(sc) != sorted(lc):
        problems.append('constraint set')
    else:
        for key in sorted(sc):
            s, l = dict(sc[key]), dict(lc[key])
            ws, wl = s.pop('target_weight', None), l.pop('target_weight', None)
            if not isinstance(ws, float) or not isinstance(wl, float) or abs(ws - wl) > tol['weight']:
                problems.append('constraints/%s/target_weight' % key)
            problems.extend(differences(s, l, 'constraints/' + key))
    if problems:
        raise Stop('Destination is not compatible with the saved pose: %s' % problems[:16])
    return {'arm_bone_offset_max': worst}


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
# Pose file format F01W2-left-arm-pose version 1 (POSE_FORMAT_v1.md)
# ---------------------------------------------------------------------------

CONVENTIONS = {'units': 'sfm-native-units', 'quaternion_order': 'x,y,z,w',
               'transform_representation': 'rigid-position-unit-quaternion',
               'transform_composition': 'parent-times-child',
               'pose_frame': 'source-CollarL-world-at-capture',
               'quaternion_unit_tolerance': QUATERNION_UNIT_TOLERANCE}

# Schema nodes: ('obj', {key: node}) | ('list', node, min, max) | ('vec', n)
# | ('quat',) | ('num',) | ('int',) | ('str',) | ('const', value)
# | ('enum', values) | ('nullable', node) | ('map', key_names, node)
# | ('typed',)  (a portable constraint field)
NUM = ('num',)
INT = ('int',)
STR = ('str',)
VEC3 = ('vec', 3)
QUAT = ('quat',)
TYPED = ('typed',)
PARENT = ('obj', {'type': STR, 'name': STR})
TARGET_HANDLES = ('enum', ('Hand_l', 'CollarL'))
CONSTRAINT_COMMON = {'type': ('enum', ('DmeRigIKConstraintOperator', 'DmeRigOrientConstraintOperator',
                                       'DmeRigPointConstraintOperator')),
                     'target_rig_handle': TARGET_HANDLES, 'target_weight': NUM,
                     'offsets': ('obj', {'oOffset': TYPED, 'vecOffset': TYPED}),
                     'solver': ('map', SOLVER_FIELDS, TYPED)}


def constraint_schema(ik):
    fields = dict(CONSTRAINT_COMMON)
    if ik:
        fields['joints'] = ('obj', {'startJoint': STR, 'midJoint': STR, 'endJoint': STR})
        fields['pole_target_rig_handle'] = ('const', 'Elbow_l')
    else:
        fields['slave_bone'] = STR
    return ('obj', fields)


CHANNEL_ROLE = ('obj', {'control': STR, 'control_attribute': STR, 'from_attribute': STR, 'from_index': INT,
                        'to_rig_handle': STR, 'to_attribute': STR, 'to_index': INT, 'mode': INT,
                        'log_type': STR, 'layer_type': STR, 'layer_count': INT,
                        'curve_info': ('const', 'none')})
BONE_REFERENCE = ('obj', {'local_orientation': QUAT, 'collar_position': VEC3, 'collar_orientation': QUAT})
POSE_SCHEMA = ('obj', {
    'format': ('const', POSE_FORMAT),
    'version': ('const', POSE_VERSION),
    'conventions': ('obj', dict((k, ('const', v)) for k, v in CONVENTIONS.items())),
    'model': STR,
    'animation_set': STR,
    'compatibility': ('obj', {
        'arm_chain': ('list', ('obj', {'name': STR, 'index': INT, 'parent': ('nullable', STR),
                                       'local_position': VEC3}), 4, 64),
        'scale_state': ('const', 'unit'),
        'handles': ('obj', dict((n, ('obj', {'parent': PARENT})) for n in HANDLE_NAMES)),
        'constraints': ('obj', {'ik': constraint_schema(True), 'hand_orient': constraint_schema(False),
                                'collar_point': constraint_schema(False),
                                'collar_orient': constraint_schema(False)}),
        'channels': ('obj', dict((s[0], CHANNEL_ROLE) for s in WRITE_CHANNELS + OBSERVED_CHANNELS)),
    }),
    'pose': ('obj', {'hand': ('obj', {'position': VEC3, 'orientation': QUAT}),
                     'elbow': ('obj', {'position': VEC3})}),
    'skeleton': ('obj', {'bones': ('obj', dict((b, BONE_REFERENCE) for b in ARM_BONES)),
                         'upper_arm_origin': VEC3}),
    'diagnostics': ('obj', {'hand_target_residual': NUM, 'capture_shot': STR, 'capture_movie_frame': INT}),
})


def is_number(v):
    return (isinstance(v, float) or isinstance(v, integer_types)) and not isinstance(v, bool)


def validate_node(node, value, path):
    kind = node[0]
    if kind == 'obj':
        if not isinstance(value, dict):
            raise PoseFormatError('%s: expected an object' % path)
        missing = sorted(set(node[1]) - set(value))
        unknown = sorted(set(value) - set(node[1]))
        if missing:
            raise PoseFormatError('%s: missing fields %s' % (path, missing))
        if unknown:
            raise PoseFormatError('%s: unknown fields %s' % (path, unknown))
        for k in sorted(node[1]):
            validate_node(node[1][k], value[k], path + '/' + k)
    elif kind == 'map':
        if not isinstance(value, dict):
            raise PoseFormatError('%s: expected an object' % path)
        unknown = sorted(set(value) - set(node[1]))
        if unknown:
            raise PoseFormatError('%s: unknown fields %s' % (path, unknown))
        for k in sorted(value):
            validate_node(node[2], value[k], path + '/' + k)
    elif kind == 'list':
        if not isinstance(value, list) or not node[2] <= len(value) <= node[3]:
            raise PoseFormatError('%s: expected a list of %d..%d items' % (path, node[2], node[3]))
        for i, x in enumerate(value):
            validate_node(node[1], x, '%s/%d' % (path, i))
    elif kind in ('vec', 'quat'):
        n = 4 if kind == 'quat' else node[1]
        if not isinstance(value, list) or len(value) != n:
            raise PoseFormatError('%s: expected %d numbers' % (path, n))
        for i, x in enumerate(value):
            validate_node(NUM, x, '%s/%d' % (path, i))
        if kind == 'quat':
            norm = math.sqrt(sum(float(c) * float(c) for c in value))
            if abs(norm - 1.0) > QUATERNION_UNIT_TOLERANCE:
                raise PoseFormatError('%s: quaternion norm %.9g is outside 1 +/- %g' %
                                      (path, norm, QUATERNION_UNIT_TOLERANCE))
    elif kind == 'num':
        if not is_number(value):
            raise PoseFormatError('%s: expected a number' % path)
        f = float(value)
        if math.isnan(f) or math.isinf(f) or abs(f) > POSE_MAX_MAGNITUDE:
            raise PoseFormatError('%s: number is non-finite or exceeds %g' % (path, POSE_MAX_MAGNITUDE))
    elif kind == 'int':
        if isinstance(value, bool) or not isinstance(value, integer_types) or abs(value) > 1000000:
            raise PoseFormatError('%s: expected a bounded integer' % path)
    elif kind == 'str':
        if not isinstance(value, text_type) or not 0 < len(value) <= 256:
            raise PoseFormatError('%s: expected a non-empty string' % path)
    elif kind == 'const':
        if type(value) is not type(node[1]) and not (isinstance(value, text_type) and
                                                     isinstance(node[1], (str, text_type))):
            raise PoseFormatError('%s: expected %r' % (path, node[1]))
        if value != node[1] or isinstance(value, bool) != isinstance(node[1], bool):
            raise PoseFormatError('%s: expected %r' % (path, node[1]))
    elif kind == 'enum':
        if not isinstance(value, text_type) or value not in node[1]:
            raise PoseFormatError('%s: expected one of %r' % (path, node[1]))
    elif kind == 'nullable':
        if value is not None:
            validate_node(node[1], value, path)
    elif kind == 'typed':
        if not isinstance(value, dict) or 'present' not in value or not isinstance(value['present'], bool):
            raise PoseFormatError('%s: expected a typed field' % path)
        if value['present']:
            if sorted(value) != ['present', 'value']:
                raise PoseFormatError('%s: present typed field needs exactly present and value' % path)
            validate_typed_value(value['value'], path + '/value')
        elif sorted(value) != ['present']:
            raise PoseFormatError('%s: absent typed field must have no value' % path)
    else:
        raise PoseFormatError('%s: schema error %r' % (path, kind))


def validate_typed_value(v, path):
    if v is None or isinstance(v, bool):
        return
    if isinstance(v, text_type):
        if len(v) > 256:
            raise PoseFormatError('%s: string too long' % path)
        return
    if is_number(v):
        validate_node(NUM, v, path)
        return
    if isinstance(v, list) and len(v) <= 16:
        for i, x in enumerate(v):
            if isinstance(x, (list, dict)):
                raise PoseFormatError('%s: nested value' % path)
            validate_typed_value(x, '%s/%d' % (path, i))
        return
    raise PoseFormatError('%s: unsupported typed value' % path)


def reject_constant(name):
    raise PoseFormatError('Non-finite number literal %s' % name)


def unique_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise PoseFormatError('Duplicate key %r' % (k,))
        out[k] = v
    return out


def parse_pose(raw):
    """Strictly parse and validate the exact bytes of one pose file. Nothing in
    the file is executed or deserialized as code."""
    if not isinstance(raw, bytes):
        raise PoseFormatError('Pose input must be bytes')
    if len(raw) > POSE_MAX_BYTES:
        raise PoseFormatError('Pose file exceeds %d bytes' % POSE_MAX_BYTES)
    if raw[:3] == b'\xef\xbb\xbf':
        raise PoseFormatError('Byte-order mark is not allowed')
    try:
        decoded = raw.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        raise PoseFormatError('Pose file is not valid UTF-8')
    try:
        value = json.loads(decoded, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except PoseFormatError:
        raise
    except ValueError as exc:
        raise PoseFormatError('Pose file is not valid JSON: %s' % exc)
    validate_node(POSE_SCHEMA, value, '')
    names = [row['name'] for row in value['compatibility']['arm_chain']]
    if len(set(names)) != len(names) or not set(ARM_BONES) | set([COLLAR_BONE]) <= set(names):
        raise PoseFormatError('arm_chain must name each bone once and include the collar and arm bones')
    return value


def serialize_pose(payload):
    """Canonical bytes: sorted keys, ASCII, no non-finite numbers, repr floats."""
    return (json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=1,
                       separators=(',', ': ')) + '\n').encode('ascii')


def build_payload(config, L, skel, desc):
    """Process A: collar-relative pose inputs and the independently evaluated
    skeletal reference, from the source capture only."""
    Cs = world(skel, 'handles', 'CollarL')
    Rs = world(skel, 'handles', 'rig_root')
    inv_c = invert(Cs)
    hand = skel['handles']['Hand_l']
    elbow = skel['handles']['Elbow_l']
    Hs = compose(Rs, (hand['local_position'], hand['local_orientation']))
    Es = compose(Rs, (elbow['local_position'], IDENTITY_Q))
    Hc = compose(inv_c, Hs)
    Ec = compose(inv_c, (Es[0], IDENTITY_Q))[0]
    bones = {}
    for b in ARM_BONES:
        row = skel['bones'][b]
        p, q = compose(inv_c, (row['world_position'], row['world_orientation']))
        bones[b] = {'local_orientation': list(row['local_orientation']), 'collar_position': p,
                    'collar_orientation': q}
    origin = compose(inv_c, (skel['bones']['bip_UpperArm_l']['world_position'], IDENTITY_Q))[0]
    spec = config['places']['source']
    return roundtrip({'format': POSE_FORMAT, 'version': POSE_VERSION, 'conventions': dict(CONVENTIONS),
                      'model': config['model'], 'animation_set': config['animation_set'],
                      'compatibility': desc,
                      'pose': {'hand': {'position': Hc[0], 'orientation': Hc[1]}, 'elbow': {'position': Ec}},
                      'skeleton': {'bones': bones, 'upper_arm_origin': origin},
                      'diagnostics': {'hand_target_residual': hand_residual(skel), 'capture_shot': spec['shot'],
                                      'capture_movie_frame': spec['movie_frame']}})


# ---------------------------------------------------------------------------
# Exclusive publication
# ---------------------------------------------------------------------------

def no_replace_rename(src, dst):
    """Publish src at dst, failing if dst exists. Windows os.rename refuses an
    existing destination; elsewhere a hard link (which also refuses) is used."""
    if os.name == 'nt':
        os.rename(src, dst)
    else:
        os.link(src, dst)
        os.unlink(src)


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def publish_pose(final_path, data, nonce):
    """Write a uniquely named non-pose temporary in the same directory, verify
    its exact bytes, then publish with a no-replace rename. A pre-existing final
    path refuses. Returns (sha256, temp name)."""
    directory = os.path.dirname(final_path)
    if not os.path.isdir(directory):
        raise Stop('Pose directory does not exist: %s' % directory)
    if os.path.exists(final_path):
        raise Stop('A pose file already exists at the final path; never overwrite')
    temp = os.path.join(directory, 'INCOMPLETE-%s.f01w2-capture.tmp' % nonce)
    write_exclusive(temp, data)
    if read_bytes(temp) != data:
        raise Stop('Temporary pose bytes differ from the validated payload; not published')
    parse_pose(read_bytes(temp))
    try:
        no_replace_rename(temp, final_path)
    except OSError as exc:
        raise Stop('No-replace publication failed (%r); nothing was overwritten' % (exc,))
    published = read_bytes(final_path)
    if published != data:
        raise Stop('Published pose bytes differ from the validated payload')
    return hashlib.sha256(published).hexdigest(), os.path.basename(temp)


# ---------------------------------------------------------------------------
# Goals: two independent implementations of the application plan
# ---------------------------------------------------------------------------

def world(skel, kind, name):
    row = skel[kind][name]
    return (row['world_position'], row['world_orientation'])


def hand_residual(skel):
    return distance(skel['bones']['bip_hand_l']['world_position'], skel['handles']['Hand_l']['world_position'])


def plan_quaternion(pose, dst, reference):
    """Implementation A: Hd_world = Cd x Hc, Hd_local = inverse(Rd) x Hd_world;
    Ed likewise for the position. The hand quaternion's sign is chosen once, in
    the hemisphere of the destination key value it replaces."""
    Cd, Rd = world(dst, 'handles', 'CollarL'), world(dst, 'handles', 'rig_root')
    inv_r = invert(Rd)
    hand = pose['pose']['hand']
    Hw = compose(Cd, (hand['position'], hand['orientation']))
    Hl = compose(inv_r, Hw)
    Ew = compose(Cd, (pose['pose']['elbow']['position'], IDENTITY_Q))[0]
    El = compose(inv_r, (Ew, IDENTITY_Q))[0]
    orientation = list(Hl[1])
    negated = sum(orientation[i] * reference[i] for i in range(4)) < 0.0
    if negated:
        orientation = [-c for c in orientation]
    return {'Hand_l_p': [f32(c) for c in Hl[0]], 'Hand_l_o': [f32(c) for c in orientation],
            'Elbow_l_p': [f32(c) for c in El], 'negated': negated,
            'double': {'Hand_l_p': Hl[0], 'Hand_l_o': orientation, 'Elbow_l_p': El,
                       'hand_world_position': Hw[0], 'elbow_world_position': Ew}}


def plan_matrix(pose, dst, reference):
    """Implementation B: the same plan with 3x3 rotation matrices and its own
    quaternion conversions (mb_* only)."""
    c = dst['handles']['CollarL']
    r = dst['handles']['rig_root']
    C = mb_xf(c['world_position'], c['world_orientation'])
    R_inv = mb_xf_inv(mb_xf(r['world_position'], r['world_orientation']))
    hand = pose['pose']['hand']
    H_local = mb_xf_mul(R_inv, mb_xf_mul(C, mb_xf(hand['position'], hand['orientation'])))
    elbow = pose['pose']['elbow']['position']
    e_world = [C[0][i] + mb_apply(C[1], elbow)[i] for i in range(3)]
    e_local = [R_inv[0][i] + mb_apply(R_inv[1], e_world)[i] for i in range(3)]
    q = mb_to_quaternion(H_local[1])
    if q[0] * reference[0] + q[1] * reference[1] + q[2] * reference[2] + q[3] * reference[3] < 0.0:
        q = [-x for x in q]
    return {'Hand_l_p': [mb_f32(x) for x in H_local[0]], 'Hand_l_o': [mb_f32(x) for x in q],
            'Elbow_l_p': [mb_f32(x) for x in e_local]}


def cross_check(a, b, tol):
    """Compare the two float32 plans: positions within cross_check_position,
    orientation sign-invariantly within cross_check_angle_degrees."""
    checks = {'hand_position': distance(a['Hand_l_p'], b['Hand_l_p']),
              'elbow_position': distance(a['Elbow_l_p'], b['Elbow_l_p']),
              'hand_orientation_degrees': angle_deg(a['Hand_l_o'], b['Hand_l_o']),
              'hand_orientation_degrees_matrix_path': mb_angle_deg(a['Hand_l_o'], b['Hand_l_o']),
              'hand_orientation_same_hemisphere': sum(a['Hand_l_o'][i] * b['Hand_l_o'][i] for i in range(4)) > 0.0}
    ok = (checks['hand_position'] <= tol['cross_check_position'] and
          checks['elbow_position'] <= tol['cross_check_position'] and
          checks['hand_orientation_degrees'] <= tol['cross_check_angle_degrees'] and
          checks['hand_orientation_degrees_matrix_path'] <= tol['cross_check_angle_degrees'] and
          checks['hand_orientation_same_hemisphere'])
    checks['agree'] = ok
    return checks


def oracle_from_pose(pose, dst):
    """Primary: saved local orientations. Secondary: saved collar-relative world
    transforms mapped through the live destination CollarL."""
    Cd = world(dst, 'handles', 'CollarL')
    oracle = {'primary_local': {}, 'secondary_world': {}}
    for b in ARM_BONES:
        row = pose['skeleton']['bones'][b]
        oracle['primary_local'][b] = list(row['local_orientation'])
        p, q = compose(Cd, (row['collar_position'], row['collar_orientation']))
        oracle['secondary_world'][b] = {'position': p, 'orientation': q}
    return oracle


def shoulder_guard(pose, dst, tol):
    Cd = world(dst, 'handles', 'CollarL')
    mapped = compose(Cd, (pose['skeleton']['upper_arm_origin'], IDENTITY_Q))[0]
    error = distance(mapped, dst['bones']['bip_UpperArm_l']['world_position'])
    if error > tol['collar_mapping']:
        raise Stop('Saved upper-arm origin mapped through the destination CollarL misses the live upper arm '
                   'by %.6g' % error)
    return error


# ---------------------------------------------------------------------------
# Oracle and rig-input acceptance (W1, unchanged)
# ---------------------------------------------------------------------------

INPUT_CHANNELS = (('Hand_l_p', 'Hand_l', 'local_position'), ('Hand_l_o', 'Hand_l', 'local_orientation'),
                  ('Elbow_l_p', 'Elbow_l', 'local_position'))


def expected_inputs(baseline, plan, expect):
    if expect == 'TRANSFERRED':
        return dict((ch, plan['write_float32'][ch]) for ch, _, _ in INPUT_CHANNELS)
    return dict((ch, baseline['handles'][owner][key]) for ch, owner, key in INPUT_CHANNELS)


def input_errors(skel, baseline, plan, expect, tol):
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


# ---------------------------------------------------------------------------
# Undo state and native writes (W1, unchanged)
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


# Required Undo/Redo history fields (F-03). GetUndoItemCount stays diagnostic: never a transaction count.
UNDO_REQUIRED = ('enabled', 'can_undo', 'can_redo', 'undo_desc', 'redo_desc')


def history_problems(u):
    """Why the required history fields are not readable evidence: absent, an unreadable sentinel, a non-boolean
    flag or a non-string description."""
    if not isinstance(u, dict):
        return ['history record missing']
    problems = []
    for k in UNDO_REQUIRED:
        if k not in u:
            problems.append('%s absent' % k)
        elif k in ('enabled', 'can_undo', 'can_redo'):
            if not isinstance(u[k], bool):
                problems.append('%s unreadable (%r)' % (k, u[k]))
        elif not isinstance(u[k], (text_type, str)):
            problems.append('%s unreadable (%r)' % (k, u[k]))
    return problems


def require_history(u, label, mutated):
    """Before any write, unreadable required history is INCONCLUSIVE (Unresolved, no publication or mutation);
    after a mutation it is STOP: recovery/ownership unverified."""
    problems = history_problems(u)
    if problems:
        if mutated:
            raise Stop('Recovery/ownership unverified: Undo history unreadable %s: %s' % (label, problems))
        raise Unresolved('Undo history unreadable %s: %s' % (label, problems))
    return u


def history_changes(now, then):
    """Required fields that differ between two readable history records."""
    return [k for k in UNDO_REQUIRED if now.get(k) != then.get(k)]


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
    """The destination's authored state with exactly the six values replaced."""
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


# ---------------------------------------------------------------------------
# Ledger (hash-chained reports shared by process A, the gate and process B)
# ---------------------------------------------------------------------------

def read_ledger(config):
    d = config['reports_dir']
    entries = []
    for name in sorted(os.listdir(d)):
        m = REPORT_RE.match(name)
        if m is None:
            if name.startswith('F01W2-') and name.endswith('.json'):
                raise Stop('Unrecognised report name in ledger: ' + name)
            continue
        path = os.path.join(d, name)
        raw = read_bytes(path)
        if not raw:
            raise Stop('Report %s is empty: a previous step did not finish. Do not continue.' % name)
        entries.append({'seq': int(m.group(1)), 'step': m.group(2), 'path': path, 'sha256':
                        hashlib.sha256(raw).hexdigest(), 'report': json.loads(raw.decode('utf-8'))})
    for i, e in enumerate(entries):
        if e['seq'] != i + 1:
            raise Stop('Ledger sequence is not contiguous')
        if e['report'].get('step') != e['step'] or e['report'].get('seq') != e['seq']:
            raise Stop('Report name and content disagree at %s' % os.path.basename(e['path']))
        if i and e['report'].get('previous_report_sha256') != entries[i - 1]['sha256']:
            raise Stop('Ledger hash chain is broken at %s' % os.path.basename(e['path']))
        if not i and e['report'].get('previous_report_sha256') is not None:
            raise Stop('First report claims a predecessor')
    return entries


def due_step(entries):
    if not entries:
        return {'step': 'CAPTURE', 'place': 'source', 'stage': None}
    last = entries[-1]['report']
    if last.get('status') == 'CAPTURE_COMPLETE_PENDING_CLOSE' and last.get('step') == 'CAPTURE':
        return {'step': 'PROCESS_GATE', 'place': None, 'stage': None}
    if last.get('status') != 'CONTINUE':
        return None
    return last['next']


def runtime():
    module = sys.modules.get(RUNTIME_MODULE)
    if module is None:
        import types
        module = types.ModuleType(RUNTIME_MODULE)
        module.active = None
        module.timers = []
        module.process_provider = None
        sys.modules[RUNTIME_MODULE] = module
    return module


def schedule(fn):
    """One ordinary event-loop opportunity, then fn. No polling, no forced
    evaluation."""
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


def utc():
    return datetime.datetime.utcnow().isoformat() + 'Z'


class Step(object):
    """One ledger step: an exclusively reserved report, written exactly once."""

    def __init__(self, config, entries, due, process):
        self.config = config
        self.entries = entries
        self.due = due
        self.seq = len(entries) + 1
        self.path = os.path.join(config['reports_dir'], 'F01W2-%02d-%s.json' % (self.seq, due['step']))
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        self.report = {'format': FORMAT, 'seq': self.seq, 'step': due['step'], 'place': due['place'],
                       'stage': due.get('stage'), 'utc_start': utc(), 'python': sys.version,
                       'pid': os.getpid(), 'process': process, 'status': 'INCONCLUSIVE', 'events': [],
                       'previous_report_sha256': entries[-1]['sha256'] if entries else None}
        self.closed = False
        self.on_finish = None

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
        self.report['evidence_complete'] = self.report['status'] in ('CONTINUE', 'COMPLETE_PENDING_CLOSE',
                                                                     'CAPTURE_COMPLETE_PENDING_CLOSE')
        self.report['utc_end'] = utc()
        with os.fdopen(self.fd, 'wb') as stream:
            stream.write(json.dumps(self.report, indent=1, sort_keys=True, ensure_ascii=True,
                                    allow_nan=False).encode('ascii'))
            stream.flush()
            os.fsync(stream.fileno())
        rt = runtime()
        rt.active = None
        print('F01W2 step %02d %s: %s' % (self.seq, self.report['step'], self.report['status']))
        print('Report: ' + self.path)
        status = self.report['status']
        if status == 'CONTINUE':
            print('NEXT: ' + self.report['next']['instruction'])
        elif status == 'CAPTURE_COMPLETE_PENDING_CLOSE':
            print('NEXT: Capture complete. Close the capture copy WITHOUT saving and quit SFM. Then run '
                  'tools/prepare_run.py gate as described in INSTRUCTIONS.md.')
        elif status == 'COMPLETE_PENDING_CLOSE':
            print('NEXT: All application steps are complete. Close the application copy WITHOUT saving, quit '
                  'SFM, then run tools/finalize_f01w2.py as described in INSTRUCTIONS.md.')
        else:
            print('NEXT: Do not submit further steps. Close the session WITHOUT saving, quit SFM, then run '
                  'tools/finalize_f01w2.py as described in INSTRUCTIONS.md.')
            if self.report.get('error'):
                print('Reason: ' + self.report['error'])
        if self.on_finish is not None:
            self.on_finish(self)


def guarded(step, fn, recovery=False, mutated=False):
    """Every callback ends in exactly one report; nothing escapes silently.
    recovery: the callback verifies an Abort/Undo/Redo restoration. mutated: the callback runs after a native
    mutation (the aborted test write or the commit). Either way unreadable required evidence is STOP; only a
    callback that runs before any native mutation reports it as INCONCLUSIVE."""
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
            elif mutated:
                step.finish('STOP', error='Unverified after mutation: %s' % (exc,), tb=traceback.format_exc())
            else:
                step.finish('INCONCLUSIVE', error=str(exc), tb=traceback.format_exc())
        except Exception as exc:
            step.finish('STOP', error='Unexpected error: %r' % (exc,), tb=traceback.format_exc())
    return run


def run_entry(allowed_steps, runner, label):
    """Shared Script Editor entry: refuse before reserving anything unless the
    due step belongs to this entrypoint; otherwise reserve one report and run."""
    try:
        config = load_config()
        rt = runtime()
        if rt.active is not None:
            print('F01W2: a step is still running (%s). Wait for it to report; nothing was done.' % rt.active)
            return None
        entries = read_ledger(config)
        due = due_step(entries)
        if due is None:
            print('F01W2: the experiment has ended (last status %s). Nothing was done.' %
                  entries[-1]['report'].get('status'))
            return None
        if due['step'] not in allowed_steps:
            print('F01W2 %s REFUSED: the due step is %s, which this entrypoint does not run. Nothing was done.'
                  % (label, due['step']))
            return None
        provider = process_provider()
        process = process_evidence(provider)
    except Exception as exc:
        print('F01W2 %s REFUSED before any step was reserved: %s' % (label, exc))
        return None
    if entries:
        first = entries[0]['report'].get('integrity_before') or {}
        now = dict((n, digest(os.path.join(BASE, n))) for n in HARNESS_FILES)
        now['config'] = digest(os.path.join(BASE, 'config.json'))
        if any(first.get(k) != v for k, v in now.items()):
            due = {'step': 'LEDGER_STOP', 'place': due['place'], 'stage': due.get('stage')}
    step = Step(config, entries, due, process)
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
        print('F01W2 step %02d %s running. Do not interact until it reports.' % (step.seq, due['step']))
        if runner(step, sfmApp, vs, config, entries, provider) == 'ASYNC':
            return step
    except Stop as exc:
        step.finish('STOP', error=str(exc), tb=traceback.format_exc())
    except Fail as exc:
        step.finish('FAIL', error=str(exc), tb=traceback.format_exc())
    except Unresolved as exc:
        if due['step'] == 'RETIME' and due.get('stage') in RECOVERY_STAGES:
            step.finish('STOP', error='Recovery unverified: %s' % (exc,), tb=traceback.format_exc())
        elif due['step'] in POST_MUTATION_STEPS:
            step.finish('STOP', error='Unverified after mutation (%s, %s stage): %s' % (due['step'], due.get('stage'),
                                                                                         exc),
                        tb=traceback.format_exc())
        else:
            step.finish('INCONCLUSIVE', error=str(exc), tb=traceback.format_exc())
    except Exception as exc:
        step.finish('STOP', error='Unexpected error: %r' % (exc,), tb=traceback.format_exc())
    finally:
        if step.closed:
            rt.active = None
    return step


def instruction(step, place, stage, config):
    spec = config['places'][place]
    where = 'movie frame %d (%s)' % (spec['movie_frame'], spec['shot'])
    texts = {
        'RETIME': 'Move the playhead to movie frame %d, let it settle, then back to %s, let it settle, then '
                  'submit APPLY_STEP.txt once.' % (config['retime_frame'], where),
        'UNDO': 'Stay at %s and submit APPLY_STEP.txt once. Do not interact until the step reports.' % where,
        'REDO': 'Stay at %s and submit APPLY_STEP.txt once. Do not interact until the step reports.' % where,
        'FINAL_UNDO': 'Stay at %s and submit APPLY_STEP.txt once. Do not interact until the step reports.' % where,
    }
    return texts[step]


def nxt(step, place, stage, config):
    return {'step': step, 'place': place, 'stage': stage,
            'instruction': instruction(step, place, stage, config)}
