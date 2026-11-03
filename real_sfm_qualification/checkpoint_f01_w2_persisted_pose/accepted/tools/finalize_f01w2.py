# -*- coding: ascii -*-
"""F-01 W2 independent finalization. Run with system Python AFTER process B has
closed the application copy without saving and SFM has exited:

    python -I finalize_f01w2.py <run dir>\\harness\\config.json

Read-only except for one new report, F01W2-FINAL.json (exclusive creation).
Independent of the harness: it does not load or call harness code. It audits
the complete hash-chained ledger, the exact pose bytes, process separation,
write accounting (one aborted test write, six committed writes, native history
operations), every accepted observation and the protected files, and it
recomputes the application plan from the pose bytes and the recorded
destination baseline with its own arithmetic. Verdict: PASS, FAIL, STOP or
INCONCLUSIVE. A status flag alone never yields PASS.
"""
import datetime
import hashlib
import json
import math
import os
import re
import struct
import sys

REPORT_RE = re.compile(r'^F01W2-(\d{2})-([A-Z0-9_]+)\.json$')
STAGES = ('committed', 'undone', 'redone', 'final')
EXPECT = {'committed': 'TRANSFERRED', 'undone': 'BASELINE', 'redone': 'TRANSFERRED', 'final': 'BASELINE'}
OBSERVING_STEP = {'committed': 'APPLY', 'undone': 'UNDO', 'redone': 'REDO', 'final': 'FINAL_UNDO'}
WRITTEN = ['Hand_l_p', 'Hand_l_p', 'Hand_l_o', 'Hand_l_o', 'Elbow_l_p', 'Elbow_l_p']
ARM_BONES = ('bip_UpperArm_l', 'bip_lowerArm_l', 'bip_hand_l')
HARNESS = ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py')
NATIVE_PROVIDER = 'windows-kernel32'
EXITED_STATES = ('ABSENT', 'EXITED', 'PID_REUSED')
UNDO_REQUIRED = ('enabled', 'can_undo', 'can_redo', 'undo_desc', 'redo_desc')
BONE_ERRORS = ('primary_angle', 'secondary_position', 'secondary_angle', 'baseline_angle', 'baseline_world_position')
OBSERVATION_STATES = ('TRANSFERRED', 'BASELINE', 'ORACLE_DISAGREEMENT', 'PARTIAL')
OBSERVING_STEPS = ('APPLY', 'RETIME', 'UNDO', 'REDO', 'FINAL_UNDO')
PROTECTED = ('original_session', 'r2_fixture', 'capture_session', 'apply_session')
INTEGRITY_KEYS = PROTECTED + ('cpm_source', 'config') + HARNESS
CONTEXT_SECONDS = 0.000051
HEX = re.compile(r'^[0-9a-f]{64}$')
try:
    INTEGER_TYPES = (int, long)
    TEXT_TYPES = (str, unicode)
except NameError:
    INTEGER_TYPES = (int,)
    TEXT_TYPES = (str,)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def ledger(directory):
    entries = []
    for name in sorted(os.listdir(directory)):
        m = REPORT_RE.match(name)
        if m is None:
            continue
        with open(os.path.join(directory, name), 'rb') as f:
            raw = f.read()
        if not raw:
            raise ValueError('Report %s is empty (a step did not finish)' % name)
        entries.append({'seq': int(m.group(1)), 'step': m.group(2), 'name': name,
                        'sha256': hashlib.sha256(raw).hexdigest(), 'report': json.loads(raw.decode('utf-8'))})
    for i, e in enumerate(entries):
        if e['seq'] != i + 1 or e['report'].get('seq') != e['seq'] or e['report'].get('step') != e['step']:
            raise ValueError('Ledger sequence or report naming is not consistent at ' + e['name'])
        expected_previous = entries[i - 1]['sha256'] if i else None
        if e['report'].get('previous_report_sha256') != expected_previous:
            raise ValueError('Ledger hash chain is broken at ' + e['name'])
    return entries


# ---------------------------------------------------------------------------
# Independent arithmetic (written for the finalizer; Euler-Rodrigues rotation)
# ---------------------------------------------------------------------------

def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def normalize(q):
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def rotate(q, v):
    x, y, z, w = normalize(q)
    # v' = v + 2w(u x v) + 2u x (u x v), u = (x, y, z)
    ux = [y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]]
    uux = [y * ux[2] - z * ux[1], z * ux[0] - x * ux[2], x * ux[1] - y * ux[0]]
    return [v[i] + 2.0 * w * ux[i] + 2.0 * uux[i] for i in range(3)]


def hamilton(a, b):
    a1, b1, c1, d1 = a[3], a[0], a[1], a[2]
    a2, b2, c2, d2 = b[3], b[0], b[1], b[2]
    return [a1 * b2 + b1 * a2 + c1 * d2 - d1 * c2, a1 * c2 - b1 * d2 + c1 * a2 + d1 * b2,
            a1 * d2 + b1 * c2 - c1 * b2 + d1 * a2, a1 * a2 - b1 * b2 - c1 * c2 - d1 * d2]


def conjugate(q):
    return [-q[0], -q[1], -q[2], q[3]]


def angle(a, b):
    a, b = normalize(a), normalize(b)
    d = min(1.0, abs(sum(a[i] * b[i] for i in range(4))))
    return math.degrees(2.0 * math.acos(d))


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def independent_plan(pose, dst, reference):
    c, r = dst['handles']['CollarL'], dst['handles']['rig_root']
    cq, rq_inv = normalize(c['world_orientation']), conjugate(normalize(r['world_orientation']))
    hand = pose['pose']['hand']
    hw = [c['world_position'][i] + rotate(cq, hand['position'])[i] for i in range(3)]
    hq = normalize(hamilton(cq, normalize(hand['orientation'])))
    hl = rotate(rq_inv, [hw[i] - r['world_position'][i] for i in range(3)])
    hlq = normalize(hamilton(rq_inv, hq))
    if sum(hlq[i] * reference[i] for i in range(4)) < 0.0:
        hlq = [-x for x in hlq]
    ew = [c['world_position'][i] + rotate(cq, pose['pose']['elbow']['position'])[i] for i in range(3)]
    el = rotate(rq_inv, [ew[i] - r['world_position'][i] for i in range(3)])
    secondary = {}
    for b in ARM_BONES:
        row = pose['skeleton']['bones'][b]
        secondary[b] = {'position': [c['world_position'][i] + rotate(cq, row['collar_position'])[i]
                                     for i in range(3)],
                        'orientation': normalize(hamilton(cq, normalize(row['collar_orientation'])))}
    return {'Hand_l_p': [f32(x) for x in hl], 'Hand_l_o': [f32(x) for x in hlq], 'Elbow_l_p': [f32(x) for x in el],
            'secondary': secondary}


def duplicate_free(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError('duplicate key %r' % (k,))
        seen[k] = v
    return seen


def reject(name):
    raise ValueError('non-finite literal %s' % name)


def parse_pose_independently(raw):
    if len(raw) > 65536 or raw[:3] == b'\xef\xbb\xbf':
        raise ValueError('pose size or encoding')
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=duplicate_free, parse_constant=reject)
    if value.get('format') != 'F01W2-left-arm-pose' or value.get('version') != 1 or \
            isinstance(value.get('version'), bool):
        raise ValueError('pose format or version')
    numbers = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, float):
            numbers.append(v)
    walk(value)
    if any(math.isnan(x) or math.isinf(x) for x in numbers):
        raise ValueError('non-finite number')
    quats = [value['pose']['hand']['orientation']] + [value['skeleton']['bones'][b][k] for b in ARM_BONES
                                                      for k in ('local_orientation', 'collar_orientation')]
    for q in quats:
        if len(q) != 4 or abs(math.sqrt(sum(c * c for c in q)) - 1.0) > 1e-4:
            raise ValueError('quaternion norm')
    return value


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def number(x):
    return isinstance(x, (float,) + INTEGER_TYPES) and not isinstance(x, bool) and not math.isnan(x) and \
        not math.isinf(x)


def error_value(x):
    """A finite, nonnegative measured error; booleans and malformed values are not evidence."""
    return number(x) and x >= 0


def observation_complete(observation):
    """Complete skeletal evidence and satisfied preservation, whatever the oracle outcome (F-01): exactly the
    three arm-bone records, every required error a finite nonnegative number, typed summary fields and no
    unrelated skeletal change. Required before an observation is accepted or sent to retime."""
    o = observation if isinstance(observation, dict) else {}
    bones = o.get('bones')
    if not isinstance(bones, dict) or sorted(bones) != sorted(ARM_BONES):
        return False
    for b in ARM_BONES:
        if not isinstance(bones[b], dict) or not all(error_value(bones[b].get(k)) for k in BONE_ERRORS):
            return False
    return (o.get('state') in OBSERVATION_STATES and o.get('expected') in ('TRANSFERRED', 'BASELINE')
            and all(isinstance(o.get(k), bool) for k in ('correct', 'inputs_ok', 'inputs_at_goal',
                                                           'inputs_at_baseline'))
            and isinstance(o.get('input_errors'), list)
            and o.get('unrelated_change_count') == 0 and o.get('unrelated_changes') == [])


def accepted(observation, expect, tol):
    """An accepted observation, checked against the per-bone errors themselves (never only the summary flags):
    TRANSFERRED within every primary and secondary tolerance with the rig inputs at the goal; BASELINE within the
    baseline tolerances with the rig inputs at the baseline."""
    o = observation if isinstance(observation, dict) else {}
    if not (observation_complete(o) and o.get('correct') is True and o.get('expected') == expect
            and o.get('state') == expect and o.get('inputs_ok') is True and o.get('input_errors') == []):
        return False
    bones, a, p = o['bones'], tol['angle_degrees'], tol['position']
    if expect == 'TRANSFERRED':
        return o.get('inputs_at_goal') is True and all(
            bones[b]['primary_angle'] <= a and bones[b]['secondary_position'] <= p and
            bones[b]['secondary_angle'] <= a for b in ARM_BONES)
    if expect == 'BASELINE':
        return o.get('inputs_at_baseline') is True and all(
            bones[b]['baseline_angle'] <= a and bones[b]['baseline_world_position'] <= p for b in ARM_BONES)
    return False


def history_readable(u):
    """The required Undo/Redo fields are present and readable (F-03)."""
    return isinstance(u, dict) and all(
        isinstance(u.get(k), bool) if k in ('enabled', 'can_undo', 'can_redo') else isinstance(u.get(k), TEXT_TYPES)
        for k in UNDO_REQUIRED)


def same_history(a, b):
    return history_readable(a) and history_readable(b) and all(a[k] == b[k] for k in UNDO_REQUIRED)


def owned_undo(u, descs):
    return history_readable(u) and u['can_undo'] is True and u['undo_desc'] == descs.get('commit_undo')


def owned_redo(u, descs):
    return history_readable(u) and u['can_redo'] is True and u['redo_desc'] == descs.get('commit_redo')


def norm_path(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path))) if isinstance(path, TEXT_TYPES) else None


def context_problems(r, config, place, session_key, offline):
    """A native scene step's own context: configured document, shot, playhead and shot-media clock, and its
    process. Offline fakes inject process identities, so only a native run requires the report's pid to equal
    the provider's pid."""
    c = r.get('context')
    spec = config['places'][place]
    if not isinstance(c, dict):
        return ['context missing']
    problems = []
    if c.get('document_path') != norm_path(config[session_key]):
        problems.append('document is not the configured %s' % session_key)
    shot = c.get('shot') if isinstance(c.get('shot'), dict) else {}
    if shot.get('name') != spec['shot'] or not isinstance(shot.get('handle'), INTEGER_TYPES):
        problems.append('shot is not %s' % spec['shot'])
    if not isinstance(c.get('document'), dict) or not isinstance(c.get('file_id'), INTEGER_TYPES):
        problems.append('document identity missing')
    if not (number(c.get('head_seconds')) and abs(c['head_seconds'] - spec['head_seconds']) <= CONTEXT_SECONDS
            and number(c.get('shot_media_seconds'))
            and abs(c['shot_media_seconds'] - spec['media_seconds']) <= CONTEXT_SECONDS):
        problems.append('observation clock is not movie frame %d' % spec['movie_frame'])
    pid = c.get('pid')
    if not isinstance(pid, INTEGER_TYPES) or isinstance(pid, bool) or pid != r.get('pid') or \
            (not offline and pid != (r.get('process') or {}).get('pid')):
        problems.append('process id does not match the step report and its process evidence')
    return problems


def identity_of(context):
    c = context if isinstance(context, dict) else {}
    return [c.get('pid'), c.get('document'), c.get('file_id'), c.get('document_path'), c.get('shot')]


def events(report, name):
    return [x for x in report.get('events') or [] if x.get('event') == name]


def bracket_ok(plan, name, bracket_ticks):
    bracket = (plan.get('brackets') or {}).get(name) or {}
    indices, times = bracket.get('indices'), bracket.get('times') or []
    return (isinstance(indices, list) and len(indices) == 2 and indices[1] == indices[0] + 1
            and all(isinstance(i, INTEGER_TYPES) and 0 <= i < len(times) for i in indices)
            and [times[i] for i in indices] == bracket_ticks
            and times.count(bracket_ticks[0]) == 1 and times.count(bracket_ticks[1]) == 1
            and ((plan.get('write_channels') or {}).get(name) or {}).get('indices') == indices)


def write_ok(x, name, index, ticks, goal):
    return (x.get('channel') == name and x.get('index') == index and x.get('ticks') == ticks
            and x.get('exact') is True and x.get('count_unchanged') is True and x.get('time_unchanged') is True
            and x.get('requested_float32') == goal and x.get('readback') == goal)


def committed_writes_ok(plan, writes, bracket_ticks):
    goals = plan.get('write_float32') or {}
    if sorted(goals) != sorted(set(WRITTEN)) or [x.get('channel') for x in writes] != WRITTEN:
        return False
    for name in sorted(goals):
        if not bracket_ok(plan, name, bracket_ticks):
            return False
        rows = [x for x in writes if x.get('channel') == name]
        indices = plan['brackets'][name]['indices']
        if len(rows) != 2 or not all(write_ok(rows[k], name, indices[k], bracket_ticks[k], goals[name])
                                     for k in range(2)):
            return False
    return True


def plan_independently_ok(pose, plan, baseline, tol, problems):
    dst = baseline.get('skeleton') or {}
    hand_o = [row for row in (baseline.get('authored') or {}).get('channels') or []
              if (row.get('id') or {}).get('handle') == ((plan.get('write_channels') or {}).get('Hand_l_o') or {})
              .get('channel_handle')]
    reference = (plan.get('hand_orientation_sign') or {}).get('reference')
    try:
        indices = plan['brackets']['Hand_l_o']['indices']
        if len(hand_o) != 1 or hand_o[0]['layers'][0]['keys'][indices[0]][1] != reference:
            problems.append('apply: hemisphere reference is not the replaced destination key value')
            return
        mine = independent_plan(pose, dst, reference)
    except Exception as exc:
        problems.append('apply: independent plan could not be computed (%r)' % (exc,))
        return
    goals = plan.get('write_float32') or {}
    if (dist(mine['Hand_l_p'], goals.get('Hand_l_p') or [1e9] * 3) > tol['cross_check_position']
            or dist(mine['Elbow_l_p'], goals.get('Elbow_l_p') or [1e9] * 3) > tol['cross_check_position']
            or angle(mine['Hand_l_o'], goals.get('Hand_l_o') or [0, 0, 0, 1]) > tol['cross_check_angle_degrees']
            or sum(mine['Hand_l_o'][i] * goals['Hand_l_o'][i] for i in range(4)) <= 0.0):
        problems.append('apply: planned float32 goals disagree with the finalizer\'s independent plan')
    # The second recorded implementation, against the same independent goals. Orientation is compared
    # sign-invariantly: two independent calculations need not produce the same quaternion sign (only the two
    # authored keys must share the replaced key's hemisphere, checked above).
    other = plan.get('independent_float32') or {}
    try:
        if (dist(mine['Hand_l_p'], other['Hand_l_p']) > tol['cross_check_position']
                or dist(mine['Elbow_l_p'], other['Elbow_l_p']) > tol['cross_check_position']
                or len(other['Hand_l_o']) != 4
                or angle(mine['Hand_l_o'], other['Hand_l_o']) > tol['cross_check_angle_degrees']):
            problems.append('apply: the second planning implementation disagrees with the finalizer\'s '
                            'independent plan')
    except Exception as exc:
        problems.append('apply: the second planning implementation result is missing or malformed (%r)' % (exc,))
    # Shoulder-origin guard, recomputed: the saved upper-arm origin mapped through the destination CollarL.
    try:
        c = dst['handles']['CollarL']
        cq = normalize(c['world_orientation'])
        moved = rotate(cq, pose['skeleton']['upper_arm_origin'])
        mapped = [c['world_position'][i] + moved[i] for i in range(3)]
        error = dist(mapped, dst['bones']['bip_UpperArm_l']['world_position'])
        recorded = plan.get('collar_mapping_error')
        if error > tol['collar_mapping'] or not number(recorded) or abs(error - recorded) > 1e-6:
            problems.append('apply: shoulder-origin guard not reproduced (independent %.6g, recorded %r)' %
                            (error, recorded))
    except Exception as exc:
        problems.append('apply: shoulder-origin guard could not be recomputed (%r)' % (exc,))
    oracle = plan.get('oracle') or {}
    for b in ARM_BONES:
        saved = pose['skeleton']['bones'][b]['local_orientation']
        if angle(saved, (oracle.get('primary_local') or {}).get(b) or [0, 0, 0, 1]) > 1e-6:
            problems.append('apply: primary oracle for %s is not the saved local orientation' % b)
        sec = (oracle.get('secondary_world') or {}).get(b) or {}
        if dist(mine['secondary'][b]['position'], sec.get('position') or [1e9] * 3) > 1e-6 or \
                angle(mine['secondary'][b]['orientation'], sec.get('orientation') or [0, 0, 0, 1]) > 1e-6:
            problems.append('apply: secondary oracle for %s is not the saved pose mapped through CollarL' % b)


def compatibility_problems(saved, live, recorded, dst, tol):
    """The compatibility check recomputed from the saved descriptor (pose bytes) and the recorded live
    descriptor, and the live descriptor tied to the recorded destination baseline: exact equality except the
    arm-bone local offsets (bone_offset) and constraint target weights (weight)."""
    if not isinstance(saved, dict) or not isinstance(live, dict) or not isinstance(dst, dict):
        return ['compatibility descriptor missing']
    problems = []
    a, b = saved.get('arm_chain'), live.get('arm_chain')
    worst = None
    if not isinstance(a, list) or not isinstance(b, list) or not a or len(a) != len(b):
        problems.append('arm chain')
    else:
        worst = 0.0
        for x, y in zip(a, b):
            if not isinstance(x, dict) or not isinstance(y, dict) or \
                    (x.get('name'), x.get('index'), x.get('parent')) != (y.get('name'), y.get('index'), y.get('parent')):
                problems.append('arm chain bone %r' % ((x or {}).get('name'),))
                continue
            worst = max(worst, dist(x['local_position'], y['local_position']))
            row = (dst.get('bones') or {}).get(y.get('name')) or {}
            if (row.get('index'), row.get('parent'), row.get('local_position')) != \
                    (y.get('index'), y.get('parent'), y.get('local_position')):
                problems.append('live descriptor bone %r is not the recorded destination bone' % (y.get('name'),))
        if worst > tol['bone_offset']:
            problems.append('arm bone local offsets differ (%.6g)' % worst)
    for key in ('scale_state', 'handles', 'channels'):
        if saved.get(key) is None or saved.get(key) != live.get(key):
            problems.append(key)
    sc, lc = saved.get('constraints'), live.get('constraints')
    if not isinstance(sc, dict) or not isinstance(lc, dict) or not sc or sorted(sc) != sorted(lc):
        problems.append('constraint set')
    else:
        for key in sorted(sc):
            x, y = dict(sc[key]), dict(lc[key])
            ws, wl = x.pop('target_weight', None), y.pop('target_weight', None)
            if not number(ws) or not number(wl) or abs(ws - wl) > tol['weight'] or x != y:
                problems.append('constraint %s' % key)
            weights = (dst.get('weights') or {}).get(key) or [{}]
            if weights[0].get('weight') != wl:
                problems.append('live constraint %s weight is not the recorded destination weight' % key)
    if worst is None or not isinstance(recorded, dict) or sorted(recorded) != ['arm_bone_offset_max'] or \
            not number(recorded['arm_bone_offset_max']) or abs(recorded['arm_bone_offset_max'] - worst) > 1e-9:
        problems.append('recorded compatibility result is not the recomputed result')
    return problems


def integrity_problems(name, r, first, config):
    """Complete protected-file and identity evidence on every report, identical across the run, with the four
    protected files at their configured hashes."""
    problems = []
    for key in ('integrity_before', 'integrity_after'):
        v = r.get(key)
        if not isinstance(v, dict) or sorted(v) != sorted(INTEGRITY_KEYS) or \
                not all(isinstance(v[k], TEXT_TYPES) and HEX.match(v[k]) for k in INTEGRITY_KEYS):
            problems.append('%s: %s incomplete or malformed' % (name, key))
        elif v != first:
            problems.append('%s: %s differs from the first report' % (name, key))
    return problems


def identity_number(x):
    return isinstance(x, INTEGER_TYPES) and not isinstance(x, bool)


def lookup_problems(label, record, a):
    """The raw strict lookup of process A behind a recorded exit classification (Correction B). record holds
    'state', 'lookup' and 'error', each explicitly present; a missing field is never read as absence.
    ABSENT: an explicitly recorded null lookup. EXITED: a lookup of the same pid and creation time with
    running False. PID_REUSED: a lookup of the same pid with a different valid creation time. Any recorded
    error, UNKNOWN, malformed, missing or contradictory evidence is refused."""
    if not isinstance(record, dict) or sorted(record) != ['error', 'lookup', 'state']:
        return ['%s: process A lookup evidence missing or incomplete' % label]
    state, row, error = record['state'], record['lookup'], record['error']
    if error is not None:
        return ['%s: process A lookup recorded an error (%r)' % (label, error)]
    if not (identity_number(a.get('pid')) and identity_number(a.get('creation_filetime'))):
        return ['%s: process A identity missing' % label]
    if state == 'ABSENT':
        return [] if row is None else ['%s: ABSENT but a lookup row was recorded' % label]
    if state not in ('EXITED', 'PID_REUSED'):
        return ['%s: process A state %r does not establish that it exited' % (label, state)]
    if not isinstance(row, dict) or not identity_number(row.get('pid')) or \
            not identity_number(row.get('creation_filetime')) or row['creation_filetime'] <= 0 or \
            not isinstance(row.get('running'), bool):
        return ['%s: %s without a complete lookup row' % (label, state)]
    if row['pid'] != a['pid']:
        return ['%s: the lookup row is not for process A\'s pid' % label]
    if state == 'EXITED':
        if row['creation_filetime'] != a['creation_filetime'] or row['running'] is not False:
            return ['%s: EXITED but the lookup row is not process A with running False' % label]
        if 'exit_code' in row and (not identity_number(row['exit_code']) or row['exit_code'] == 259):
            return ['%s: EXITED but the recorded exit code is STILL_ACTIVE or malformed' % label]
    elif row['creation_filetime'] == a['creation_filetime']:
        return ['%s: PID_REUSED but the lookup row has process A\'s creation time' % label]
    return []


def process_audit(reports, names, offline, problems):
    cap, gate = reports[0], reports[1]
    a = cap.get('process') or {}
    g = gate.get('gate') or {}
    b_reports = reports[2:]
    providers = [(r.get('process') or {}).get('provider') for r in reports] + [g.get('provider')]
    if not offline and any(p != NATIVE_PROVIDER for p in providers):
        problems.append('process evidence (steps or gate) is not from the native kernel32 provider')
    if len(set(providers)) != 1:
        problems.append('process evidence providers are not consistent across the run')
    for name, r in zip(names, reports):
        p = r.get('process') or {}
        if not all(isinstance(p.get(k), INTEGER_TYPES) and not isinstance(p.get(k), bool)
                   for k in ('pid', 'creation_filetime')):
            problems.append('%s: process identity (pid and creation time) missing' % name)
        if not offline and p.get('pid') != r.get('pid'):
            problems.append('%s: report pid is not the queried process' % name)
    b = (b_reports[0].get('process') or {}) if b_reports else {}
    for name, r in zip(names[2:], b_reports):
        p = r.get('process') or {}
        if (p.get('pid'), p.get('creation_filetime'), p.get('provider')) != \
                (b.get('pid'), b.get('creation_filetime'), b.get('provider')):
            problems.append('%s: not the same process B as the APPLY step' % name)
    if (a.get('pid'), a.get('creation_filetime')) == (b.get('pid'), b.get('creation_filetime')):
        problems.append('process B is process A')
    numbers = [a.get('creation_filetime'), g.get('checked_filetime'), b.get('creation_filetime')]
    if not all(isinstance(x, INTEGER_TYPES) and not isinstance(x, bool) for x in numbers) or \
            not numbers[0] < numbers[1] < numbers[2]:
        problems.append('process order not proven: A created < gate (A exited) < B created')
    if g.get('process_a_running') is not False or g.get('process_a_state') not in EXITED_STATES or \
            g.get('sfm_processes') != [] or \
            g.get('process_a') != {'pid': a.get('pid'), 'creation_filetime': a.get('creation_filetime')}:
        problems.append('gate did not prove that process A had exited and SFM was closed')
    gate_record = dict((k[len('process_a_'):], g[k]) for k in ('process_a_state', 'process_a_lookup',
                                                                'process_a_error') if k in g)
    problems.extend(lookup_problems('gate', gate_record, a))
    if b_reports:
        problems.extend(lookup_problems('apply', b_reports[0].get('process_a_now'), a))
    sep = (b_reports[0].get('process_separation') or {}) if b_reports else {}
    wanted = ('a_created_before_gate', 'a_not_running_now', 'b_created_after_gate', 'b_is_not_a',
              'gate_saw_a_exited', 'gate_saw_no_sfm', 'same_provider')
    if sorted(sep) != sorted(wanted) or not all(sep[k] is True for k in wanted):
        problems.append('apply: process separation checks incomplete')
    if ((b_reports[0].get('process_a_now') or {}) if b_reports else {}).get('state') not in EXITED_STATES:
        problems.append('apply: process A was not verified absent, exited or replaced at the APPLY step')


def audit(entries, config, pose_raw, offline):
    problems, propagation = [], {}
    reports = [e['report'] for e in entries]
    names = [e['name'] for e in entries]
    tol = config['tolerances']
    bracket_ticks = config['bracket_ticks']
    first = reports[0].get('integrity_before') if reports else None
    if not isinstance(first, dict) or any(first.get(k) != config[k + '_sha256'] for k in PROTECTED):
        problems.append('first report: protected files are not at their configured hashes')
    for name, r in zip(names, reports):
        if r.get('evidence_complete') is not True:
            problems.append('%s: evidence not marked complete' % name)
        if r.get('step') in OBSERVING_STEPS:
            if r.get('observed_changes') != []:
                problems.append('%s: observed_changes not recorded as an explicitly empty list (%r)' %
                                (name, r.get('observed_changes')))
        elif r.get('observed_changes'):
            problems.append('%s: unclassified operator/constraint attribute changes %s' %
                            (name, r['observed_changes'][:8]))
        problems.extend(integrity_problems(name, r, first, config))
    if len(reports) < 3:
        return problems + ['ledger has fewer than capture, gate and apply'], propagation
    position = [0]

    def take(step, stage):
        if position[0] >= len(reports):
            problems.append('missing step %s (%s)' % (step, stage))
            return None
        r = reports[position[0]]
        if r.get('step') != step or r.get('stage') != stage:
            problems.append('%s: expected %s (%s), found %s (%s)' % (names[position[0]], step, stage,
                                                                     r.get('step'), r.get('stage')))
        position[0] += 1
        return r

    cap = take('CAPTURE', None)
    gate = take('PROCESS_GATE', None)
    pose = None
    pose_sha = hashlib.sha256(pose_raw).hexdigest() if pose_raw is not None else None
    if cap is not None:
        pub = cap.get('publication') or {}
        gate_checks = (cap.get('capture') or {}).get('completion_gate') or {}
        baseline = (cap.get('capture') or {}).get('source_baseline') or {}
        if cap.get('status') != 'CAPTURE_COMPLETE_PENDING_CLOSE':
            problems.append('capture: status %s' % cap.get('status'))
        if sorted(gate_checks) != ['authored', 'binding_identity', 'context', 'observed', 'process', 'skeleton',
                                   'undo_history'] or not all(v is True for v in gate_checks.values()):
            problems.append('capture: completion gate incomplete')
        for p in context_problems(cap, config, 'source', 'capture_session', offline):
            problems.append('capture: ' + p)
        start, done = baseline.get('undo'), baseline.get('undo_completion')
        count_start = (start or {}).get('item_count_recorded_only') if isinstance(start, dict) else None
        count_done = (done or {}).get('item_count_recorded_only') if isinstance(done, dict) else None
        if not same_history(start, done) or (isinstance(count_start, INTEGER_TYPES) and
                                             isinstance(count_done, INTEGER_TYPES) and count_start != count_done):
            problems.append('capture: required Undo/Redo history unreadable or changed during the read-only capture')
        if pose_raw is None or pub.get('pose_sha256') != pose_sha or pub.get('pose_bytes') != len(pose_raw):
            problems.append('capture: published pose missing or not the recorded bytes')
        else:
            try:
                pose = parse_pose_independently(pose_raw)
            except Exception as exc:
                problems.append('pose file rejected by the finalizer: %r' % (exc,))
            if pose is not None and (cap.get('capture') or {}).get('payload') != pose:
                problems.append('capture: recorded payload differs from the published pose bytes')
            if pose is not None and (pose.get('model') != config['model'] or
                                     pose.get('animation_set') != config['animation_set']):
                problems.append('capture: pose model or animation set is not the configured one')
    if gate is not None and ((gate.get('gate') or {}).get('pose_sha256') != pose_sha or gate.get('status') != 'CONTINUE'):
        problems.append('gate: pose hash or status not proven')
    process_audit(reports, names, offline, problems)
    plan = {}
    apply_identity = None
    for stage in STAGES:
        r = take(OBSERVING_STEP[stage], stage)
        if r is None:
            break
        if stage == 'committed':
            plan = r.get('plan') or {}
            descs = plan.get('descs') or {}
            snapshot = r.get('pose_snapshot') or {}
            dst = r.get('destination_baseline') or {}
            apply_identity = identity_of(r.get('context'))
            if identity_of(dst.get('context')) != apply_identity:
                problems.append('apply: destination baseline context is not the APPLY context')
            if snapshot.get('sha256') != pose_sha or plan.get('pose_sha256') != pose_sha or \
                    (pose is not None and snapshot.get('payload') != pose):
                problems.append('apply: pose snapshot is not the published pose')
            if not dst or not descs:
                problems.append('apply: destination baseline or plan missing')
            if (plan.get('cross_check') or {}).get('agree') is not True or \
                    plan.get('independent_float32') is None or \
                    not isinstance(plan.get('collar_mapping_error'), float) or \
                    plan['collar_mapping_error'] > tol['collar_mapping']:
                problems.append('apply: live two-implementation cross-check or shoulder guard not proven')
            preflight = r.get('preflight') if isinstance(r.get('preflight'), dict) else {}
            if not preflight:
                problems.append('apply: preflight record missing')
            elif pose is not None:
                for p in compatibility_problems(pose.get('compatibility'), preflight.get('live_descriptor'),
                                                preflight.get('compatibility'), dst.get('skeleton'), tol):
                    problems.append('apply: compatibility ' + p)
            if not history_readable(preflight.get('undo_state')) or preflight['undo_state']['enabled'] is not True:
                problems.append('apply: preflight Undo state unreadable or Undo not enabled')
            if pose is not None:
                plan_independently_ok(pose, plan, dst, tol, problems)
            abort = events(r, 'abort-check')
            w = (abort[0].get('write') or {}) if len(abort) == 1 else {}
            goal = (plan.get('write_float32') or {}).get('Hand_l_p')
            first_index = (((plan.get('brackets') or {}).get('Hand_l_p') or {}).get('indices') or [None])[0]
            if not (len(abort) == 1 and abort[0].get('authored_restored') is True and abort[0].get('differences') == []
                    and not abort[0].get('write_failure') and bracket_ok(plan, 'Hand_l_p', bracket_ticks)
                    and write_ok(w, 'Hand_l_p', first_index, bracket_ticks[0], goal)):
                problems.append('apply: the single aborted test write and its restoration are not proven')
            history0 = abort[0].get('undo_before') if len(abort) == 1 else None
            after_abort = abort[0].get('undo_after') if len(abort) == 1 else None
            if not same_history(history0, after_abort) or history0.get('enabled') is not True or \
                    after_abort.get('undo_desc') in (descs.get('abort_undo'), descs.get('abort_redo')) or \
                    after_abort.get('redo_desc') in (descs.get('abort_undo'), descs.get('abort_redo')):
                problems.append('apply: required Undo/Redo history not readable and restored after the Abort test')
            evaluated = events(r, 'abort-evaluated')
            if len(evaluated) != 1 or not accepted(evaluated[0].get('observation'), 'BASELINE', tol):
                problems.append('apply: evaluated state after the abort not accepted as baseline')
            commit = events(r, 'commit')
            writes = (commit[0].get('writes') or []) if len(commit) == 1 else []
            if events(r, 'commit-aborted') or events(r, 'commit-abort-failed'):
                problems.append('apply: a commit was aborted')
            if not (len(commit) == 1 and committed_writes_ok(plan, writes, bracket_ticks)
                    and commit[0].get('finished') is True
                    and same_history(commit[0].get('undo_before'), history0)
                    and owned_undo(commit[0].get('undo_after'), descs)):
                problems.append('apply: six committed writes or transaction ownership not proven')
        else:
            action = 'redo' if stage == 'redone' else 'undo'
            ev = events(r, action)
            before = (ev[0].get('undo_before') or {}) if len(ev) == 1 else {}
            after = (ev[0].get('undo_after') or {}) if len(ev) == 1 else {}
            descs = plan.get('descs') or {}
            if action == 'redo':
                owned = owned_redo(before, descs) and owned_undo(after, descs)
            else:
                owned = owned_undo(before, descs) and owned_redo(after, descs)
            if len(ev) != 1 or not owned or not descs or len(events(r, 'undo') + events(r, 'redo')) != 1:
                problems.append('%s: %s ownership not proven' % (stage, action))
        for p in context_problems(r, config, 'destination', 'apply_session', offline):
            problems.append('%s: %s' % (stage, p))
        if identity_of(r.get('context')) != apply_identity:
            problems.append('%s: document, shot or process differs from the APPLY step' % stage)
        if r.get('propagation') == 'IDLE':
            if not accepted(r.get('observation'), EXPECT[stage], tol):
                problems.append('%s: idle observation reported IDLE but is not accepted' % stage)
            propagation[stage] = 'IDLE'
        elif r.get('propagation') == 'NOT_AT_IDLE':
            if accepted(r.get('observation'), EXPECT[stage], tol):
                problems.append('%s: accepted idle observation was sent to retime' % stage)
            if not observation_complete(r.get('observation')) or r.get('observed_changes') != []:
                problems.append('%s: unsuccessful idle observation lacks complete evidence or preservation; '
                                'retiming was not allowed' % stage)
            rt = take('RETIME', stage)
            if rt is not None:
                if rt.get('propagation') != 'RETIMING_DEPENDENT' or not accepted(rt.get('observation'),
                                                                                  EXPECT[stage], tol):
                    problems.append('%s: retime observation not accepted' % stage)
                if events(rt, 'undo') or events(rt, 'redo') or events(rt, 'commit'):
                    problems.append('%s: retime step performed a native operation' % stage)
                for p in context_problems(rt, config, 'destination', 'apply_session', offline):
                    problems.append('%s retime: %s' % (stage, p))
                if identity_of(rt.get('context')) != apply_identity:
                    problems.append('%s retime: document, shot or process differs from the APPLY step' % stage)
                propagation[stage] = 'RETIMING_DEPENDENT'
        else:
            problems.append('%s: no propagation classification' % stage)
    if position[0] != len(reports):
        problems.append('unexpected additional steps after the final stage')
    for name, r in zip(names[:-1], reports[:-1]):
        if r.get('status') not in ('CONTINUE', 'CAPTURE_COMPLETE_PENDING_CLOSE') or \
                (r.get('status') == 'CAPTURE_COMPLETE_PENDING_CLOSE' and r.get('step') != 'CAPTURE'):
            problems.append('%s: status %s before the end' % (name, r.get('status')))
    if reports[-1].get('status') != 'COMPLETE_PENDING_CLOSE':
        problems.append('final step status is %s' % reports[-1].get('status'))
    return problems, propagation


def verdict(entries, protected_ok, identity_ok, config, pose_raw, offline):
    if not protected_ok:
        return 'STOP', ['A protected file hash changed'], {}
    if not identity_ok:
        return 'STOP', ['Harness, config or CPM source differs from the first step'], {}
    if not entries:
        return 'INCONCLUSIVE', ['No step was run'], {}
    statuses = [e['report'].get('status') for e in entries]
    for wanted in ('STOP', 'INCONCLUSIVE', 'FAIL'):
        if wanted in statuses:
            first = [e for e in entries if e['report'].get('status') == wanted][0]
            return wanted, ['%s at %s: %s' % (wanted, first['name'], first['report'].get('error'))], {}
    if statuses[-1] != 'COMPLETE_PENDING_CLOSE':
        return 'INCONCLUSIVE', ['The experiment did not reach its final step (last status %s)' % statuses[-1]], {}
    problems, propagation = audit(entries, config, pose_raw, offline)
    if problems:
        return 'INCONCLUSIVE', problems, propagation
    return 'PASS', [], propagation


def main(config_path, offline=False):
    """offline=True accepts injected process evidence; only offline tests pass it."""
    with open(config_path, 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
    directory = config['reports_dir']
    out_path = os.path.join(directory, 'F01W2-FINAL.json')
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    result = {'format': 'F01W2-final-v1', 'utc': datetime.datetime.utcnow().isoformat() + 'Z',
              'python': sys.version, 'verdict': 'INCONCLUSIVE', 'offline_process_evidence_accepted': bool(offline)}
    try:
        protected, ok = {}, True
        for key in ('original_session', 'r2_fixture', 'capture_session', 'apply_session'):
            value = digest(config[key])
            protected[key] = {'sha256': value, 'expected': config[key + '_sha256'],
                              'unchanged': value == config[key + '_sha256']}
            ok = ok and protected[key]['unchanged']
        result['protected_files'] = protected
        entries = ledger(directory)
        result['ledger'] = [{'name': e['name'], 'sha256': e['sha256'], 'status': e['report'].get('status'),
                             'propagation': e['report'].get('propagation'), 'error': e['report'].get('error')}
                            for e in entries]
        identity_ok = True
        if entries:
            first = entries[0]['report'].get('integrity_before') or {}
            harness_dir = os.path.dirname(os.path.abspath(config_path))
            current = dict((n, digest(os.path.join(harness_dir, n))) for n in HARNESS)
            current['config'] = digest(config_path)
            current['cpm_source'] = digest(config['cpm_source'])
            result['identity'] = current
            identity_ok = all(first.get(k) == v for k, v in current.items())
        pose_raw = None
        if os.path.isfile(config['pose_path']):
            with open(config['pose_path'], 'rb') as f:
                pose_raw = f.read()
            result['pose'] = {'sha256': hashlib.sha256(pose_raw).hexdigest(), 'bytes': len(pose_raw)}
        result['verdict'], result['reasons'], result['propagation'] = verdict(
            entries, ok, identity_ok, config, pose_raw, offline)
        if result['verdict'] == 'PASS':
            classes = set(result['propagation'].values())
            result['write_accounting'] = {'aborted_test_writes': 1, 'committed_writes': 6,
                                          'native_history_operations': ['Undo', 'Redo', 'Undo']}
            result['interpretation'] = (
                'Persisted pose applied after a process restart with idle propagation at every stage.'
                if classes == set(['IDLE']) else
                'Persisted pose applied after a process restart; at least one stage required retiming '
                '(RETIMING_DEPENDENT).')
            result['not_claimed'] = ('The source shot was not re-observed in process B; W1 source-preservation '
                                     'evidence is unchanged and not extended.')
    except Exception as exc:
        result['verdict'] = 'STOP'
        result['reasons'] = ['Finalization error: %r' % (exc,)]
    with os.fdopen(fd, 'wb') as stream:
        stream.write(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=True).encode('ascii'))
    print('F01W2 FINAL: ' + result['verdict'])
    for reason in result.get('reasons') or []:
        print('  ' + reason)
    print('Report: ' + out_path)
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python -I finalize_f01w2.py <run dir>\\harness\\config.json')
        sys.exit(2)
    main(sys.argv[1])
