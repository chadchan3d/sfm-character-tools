# -*- coding: ascii -*-
"""Offline tests of the F-01 W1 harness. Python 2.7 and 3.

Fake native modules only (tests/fake_sfm.py, built from the R3 captures).
No SFM, no native writes, no session files: every protected file is a
temporary stand-in.

usage: python test_f01w1_harness.py [RESULTS_JSON]
"""
from __future__ import print_function

import ast
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HARNESS = os.path.join(ROOT, 'harness', 'f01w1_harness.py')
CONFIG = os.path.join(ROOT, 'harness', 'config.json')
FINALIZE = os.path.join(ROOT, 'tools', 'finalize_f01w1.py')
INPUTS = os.path.join(ROOT, 'test_inputs')
sys.path.insert(0, HERE)
import fake_sfm  # noqa: E402

R3_HASHES = {'R3-shot15-A.json': '838c21d231f497edd640524f1ae728ab4ff08013ee660f7c7014b06daa64dde0',
             'R3-shot10-A.json': 'b14bcd930f3e4eb2d1d1f4f5637ba833dc7a0fb678835ec0dc2bc911cc3105de'}
R3 = {}


def r3(name):
    if name not in R3:
        path = os.path.join(INPUTS, name)
        with open(path, 'rb') as f:
            raw = f.read()
        assert hashlib.sha256(raw).hexdigest() == R3_HASHES[name], 'test input changed: ' + name
        R3[name] = json.loads(raw.decode('utf-8'))
    return R3[name]


def load_harness(name='offline'):
    ns = {'__name__': name, '__file__': HARNESS}
    with open(HARNESS, 'rb') as f:
        exec(compile(f.read(), HARNESS, 'exec', 0, True), ns)
    return ns


def load_finalize():
    ns = {'__name__': 'offline', '__file__': FINALIZE}
    with open(FINALIZE, 'rb') as f:
        exec(compile(f.read(), FINALIZE, 'exec', 0, True), ns)
    return ns


class Out(object):
    def __init__(self):
        self.lines = []

    def write(self, s):
        self.lines.append(s)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.lines)


# ---------------------------------------------------------------------------
# Independent expectation (matrices, not the harness's quaternion code)
# ---------------------------------------------------------------------------

def handle_xf(S, name, local=False):
    dag = S.handles[name]
    if local:
        t = dag.get('transform')
        return fake_sfm.xf(fake_sfm.as_list(t.get('position')), fake_sfm.as_list(t.get('orientation')))
    return fake_sfm.xf(dag.world_xf[0], dag.world_xf[1])


def expected_transfer(world):
    src, dst = world.shots['shot15'], world.shots['shot10']
    Cs, Cd = handle_xf(src, 'CollarL'), handle_xf(dst, 'CollarL')
    Rs, Rd = handle_xf(src, 'rig_root'), handle_xf(dst, 'rig_root')
    M = fake_sfm.xf_mul(Cd, fake_sfm.xf_inv(Cs))
    goal = {}
    for owner in ('Hand_l', 'Elbow_l'):
        G = fake_sfm.xf_mul(fake_sfm.xf_mul(M, Rs), handle_xf(src, owner, local=True))
        L = fake_sfm.xf_mul(fake_sfm.xf_inv(Rd), G)
        goal[owner] = (L[0], fake_sfm.m_to_q(L[1]))
    inputs = ([fake_sfm.f32(c) for c in goal['Hand_l'][0]], [fake_sfm.f32(c) for c in goal['Hand_l'][1]],
              [fake_sfm.f32(c) for c in goal['Elbow_l'][0]])
    arm = {}
    for bone, h in src.arm.items():
        dag = world.by_handle[h]
        W = fake_sfm.xf_mul(M, fake_sfm.xf(dag.world_xf[0], dag.world_xf[1]))
        arm[bone] = (src.baseline_arm[bone][0], W[0], fake_sfm.m_to_q(W[1]))
    return inputs, arm, M


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Env(object):
    def __init__(self, policy='idle'):
        self.dir = tempfile.mkdtemp(prefix='f01w1_test_')
        hdir = os.path.join(self.dir, 'harness')
        os.makedirs(hdir)
        shutil.copy2(HARNESS, os.path.join(hdir, 'f01w1_harness.py'))
        self.harness = os.path.join(hdir, 'f01w1_harness.py')
        with open(CONFIG, 'rb') as f:
            config = json.loads(f.read().decode('utf-8'))
        files = {'original_session': b'original session bytes', 'r2_fixture': b'fixture bytes',
                 'disposable_session': b'fixture bytes', 'cpm_source': b'cpm source bytes'}
        for k, content in files.items():
            path = os.path.join(self.dir, k + '.dmx')
            with open(path, 'wb') as f:
                f.write(content)
            config[k] = path
            if k != 'cpm_source':
                config[k + '_sha256'] = hashlib.sha256(content).hexdigest()
        config['reports_dir'] = os.path.join(self.dir, 'reports')
        os.makedirs(config['reports_dir'])
        self.config = config
        self.config_path = os.path.join(hdir, 'config.json')
        self.write_config()
        self.world = fake_sfm.World(r3('R3-shot15-A.json'), r3('R3-shot10-A.json'), config['disposable_session'],
                                    config['model'])
        self.world.policy = policy
        inputs, arm, self.M = expected_transfer(self.world)
        self.world.shots['shot10'].transfer_inputs = inputs
        self.world.shots['shot10'].transfer_arm = arm
        self.saved = {}
        for name, module in self.world.modules().items():
            self.saved[name] = sys.modules.get(name)
            sys.modules[name] = module
        self.saved['f01w1_runtime'] = sys.modules.pop('f01w1_runtime', None)
        self.output = []

    def write_config(self):
        with open(self.config_path, 'wb') as f:
            f.write(json.dumps(self.config, indent=1, sort_keys=True).encode('ascii'))

    def close(self):
        for name, module in self.saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        shutil.rmtree(self.dir, ignore_errors=True)

    def submit(self, events=True):
        out = Out()
        old = sys.stdout
        sys.stdout = out
        try:
            ns = {'__name__': '__f01w1_owner_step__', '__file__': self.harness}
            with open(self.harness, 'rb') as f:
                exec(compile(f.read(), self.harness, 'exec', 0, True), ns)
            if events:
                self.world.run_events()
        finally:
            sys.stdout = old
        self.output.append(out.text())
        return self.last()

    def reports(self):
        d = self.config['reports_dir']
        names = sorted(n for n in os.listdir(d) if n.startswith('F01W1-') and n[6:8].isdigit())
        result = []
        for n in names:
            with open(os.path.join(d, n), 'rb') as f:
                raw = f.read()
            result.append((n, json.loads(raw.decode('utf-8')) if raw else None))
        return result

    def last(self):
        r = self.reports()
        return r[-1][1] if r else None

    def act(self, nxt):
        step = nxt['step']
        if step == 'RETIME':
            self.world.set_frame(11)
            self.world.set_frame(10)
        elif step == 'SOURCE_RETURN':
            self.world.set_frame(5)
        elif step in ('TRANSFER', 'DESTINATION_RETURN'):
            self.world.set_frame(10)

    def run(self, until=None, limit=30, hooks=None):
        """Drive the Owner procedure. hooks: {(step, stage): fn(env)} run before that submission."""
        hooks = hooks or {}
        due = {'step': 'SOURCE_BASELINE', 'stage': None}
        for _ in range(limit):
            hook = hooks.get((due['step'], due.get('stage')))
            if hook is not None:
                hook(self)
            report = self.submit()
            if until is not None and report['step'] == until[0] and report.get('stage') == until[1]:
                return report
            if report['status'] != 'CONTINUE':
                return report
            due = report['next']
            self.act(due)
        raise AssertionError('procedure did not end')

    def finalize(self):
        ns = load_finalize()
        out = Out()
        old = sys.stdout
        sys.stdout = out
        try:
            return ns['main'](self.config_path)
        finally:
            sys.stdout = old

    def layer(self, shot, channel):
        S = self.world.shots[shot]
        ch = [c for c, _, _ in S.channels if c.name == channel][0]
        return ch.log.layers[0]


def statuses(env):
    return [(n[9:-5], r['status'], r.get('stage'), r.get('propagation')) for n, r in env.reports()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class Base(unittest.TestCase):
    def setUp(self):
        self.envs = []

    def tearDown(self):
        for e in self.envs:
            e.close()

    def env(self, policy='idle'):
        e = Env(policy)
        self.envs.append(e)
        return e


def r3_skeleton(st):
    """The harness skeleton form built directly from an R3 capture (no fake rig)."""
    st = json.loads(json.dumps(st))  # never share lists with the cached capture

    def v(rec):
        return rec.get('value')
    dags = dict((d['identity']['handle'], d) for d in st['skeletal_dags'])
    names = {}
    for h, d in dags.items():
        names[h] = d['identity']['name'].split('(', 1)[1][:-1]
    out = {'bones': {}, 'handles': {}}
    for h, d in dags.items():
        p = d['parents'][0] if d['parents'] else None
        out['bones'][names[h]] = {'local_position': v(d['local']['position']),
                                  'local_orientation': v(d['local']['orientation']), 'scale': d['local']['scale'],
                                  'world_position': v(d['absolute_position']),
                                  'world_orientation': v(d['absolute_orientation']), 'parent': names.get(p),
                                  'handle': h}
    for r in st['rig_handles']:
        out['handles'][r['identity']['name']] = {
            'local_position': v(r['local']['position']), 'local_orientation': v(r['local']['orientation']),
            'world_position': v(r['absolute_position']), 'world_orientation': v(r['absolute_orientation']),
            'scale': r['local']['scale'], 'parents': r['parents'], 'handle': r['identity']['handle']}
    return out


def package_config():
    with open(CONFIG, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


class TestMath(Base):
    """Coordinate transformation and oracle against the adjudicated values."""

    def skeletons(self):
        e = self.env()
        h = load_harness()
        src = h['roundtrip'](self.capture(e, h, 'source'))
        dst = h['roundtrip'](self.capture(e, h, 'destination'))
        return e, h, src, dst

    def capture(self, e, h, place):
        import sfmApp
        import vs
        e.world.set_frame(5 if place == 'source' else 10)
        L = h['resolve'](sfmApp, vs, e.config, place)
        sk = h['capture_skeleton'](L, vs)
        sk['arm_op_handles'] = dict((k, h['handle'](v)) for k, v in L['arm_ops'].items())
        return sk

    def test_goals_reproduce_adjudication_from_r3_captures(self):
        """Directly from the R3 native captures: Astra's goals, anchor error and residual."""
        h = load_harness()
        config = package_config()
        src = r3_skeleton(r3('R3-shot15-A.json')['state'])
        dst = r3_skeleton(r3('R3-shot10-A.json')['state'])
        plan = h['compute_goals'](src, dst, config)
        w = plan['write_float32']
        cross = config['astra_cross_check']
        # Astra's values are rounded to 6 decimals; float32 spacing near 39 is 3.8e-6.
        self.assertLess(h['distance'](w['Hand_l_p'], cross['hand_position']), 2e-5)
        self.assertLess(h['distance'](w['Elbow_l_p'], cross['elbow_position']), 2e-5)
        # Same rotation as the adjudicated value (quaternion sign is a separate, explicit rule).
        self.assertLess(h['angle_deg'](w['Hand_l_o'], cross['hand_orientation']), 2e-4)
        self.assertLess(min(max(abs(w['Hand_l_o'][i] - sg * cross['hand_orientation'][i]) for i in range(4))
                            for sg in (1, -1)), 2e-6)
        self.assertAlmostEqual(plan['collar_mapping_error'], 0.0000647, delta=0.000001)
        self.assertAlmostEqual(plan['source_residual'], 0.051391, delta=0.000001)
        for k, value in w.items():
            self.assertEqual(value, [h['f32'](c) for c in value], 'goal not float32: ' + k)

    def test_hand_quaternion_sign_follows_replaced_key(self):
        h = load_harness()
        config = package_config()
        src = r3_skeleton(r3('R3-shot15-A.json')['state'])
        dst = r3_skeleton(r3('R3-shot10-A.json')['state'])
        key = [c for c in r3('R3-shot10-A.json')['state']['channels'] if c['identity']['name'] == 'Hand_l_o'][0]
        replaced = [k['value']['value'] for k in key['layers'][0]['keys']
                    if int(round(k['time']['value']['seconds'] * 10000)) == 30000][0]
        plan = h['compute_goals'](src, dst, config, replaced)
        q = plan['write_float32']['Hand_l_o']
        self.assertGreaterEqual(sum(q[i] * replaced[i] for i in range(4)), 0.0)
        flipped = h['compute_goals'](src, dst, config, [-c for c in replaced])['write_float32']['Hand_l_o']
        self.assertEqual(flipped, [-c for c in q])

    def test_goals_in_fake_scene_match_independent_matrix_math(self):
        e, h, src, dst = self.skeletons()
        plan = h['compute_goals'](src, dst, e.config)
        inputs = e.world.shots['shot10'].transfer_inputs
        self.assertLess(h['distance'](plan['write_float32']['Hand_l_p'], inputs[0]), 1e-5)
        self.assertLess(h['angle_deg'](plan['write_float32']['Hand_l_o'], inputs[1]), 1e-4)
        self.assertLess(h['distance'](plan['write_float32']['Elbow_l_p'], inputs[2]), 1e-5)

    def test_cross_check_mismatch_stops(self):
        h = load_harness()
        config = package_config()
        config['astra_cross_check']['hand_position'][0] += 0.01
        src = r3_skeleton(r3('R3-shot15-A.json')['state'])
        dst = r3_skeleton(r3('R3-shot10-A.json')['state'])
        self.assertRaises(h['Stop'], h['compute_goals'], src, dst, config)

    def test_collar_anchor_mismatch_stops(self):
        h = load_harness()
        config = package_config()
        src = r3_skeleton(r3('R3-shot15-A.json')['state'])
        dst = r3_skeleton(r3('R3-shot10-A.json')['state'])
        dst['bones']['bip_UpperArm_l']['world_position'][0] += 0.01
        self.assertRaises(h['Stop'], h['compute_goals'], src, dst, config)

    def test_oracle_classifies_baseline_and_transfer(self):
        e, h, src, dst = self.skeletons()
        plan = h['roundtrip'](h['compute_goals'](src, dst, e.config))
        tol = e.config['tolerances']
        base = h['classify'](dst, dst, plan, 'BASELINE', tol)
        self.assertTrue(base['correct'])
        self.assertEqual(base['state'], 'BASELINE')
        # P1-2 correction: a matching skeleton with the BASELINE rig inputs is not accepted.
        skeleton_only = transferred_skeleton(dst, plan, e.world.shots['shot10'].transfer_arm, inputs=False)
        r = h['classify'](skeleton_only, dst, plan, 'TRANSFERRED', tol)
        self.assertEqual(r['state'], 'TRANSFERRED')
        self.assertFalse(r['correct'])
        self.assertFalse(r['inputs_ok'])
        self.assertIn('input Hand_l_p handle value', r['input_errors'])
        transferred = transferred_skeleton(dst, plan, e.world.shots['shot10'].transfer_arm)
        r = h['classify'](transferred, dst, plan, 'TRANSFERRED', tol)
        self.assertEqual(r['state'], 'TRANSFERRED')
        self.assertTrue(r['correct'])
        self.assertTrue(r['inputs_ok'] and r['inputs_at_goal'] and not r['inputs_at_baseline'])
        self.assertFalse(r['previous_state_remains'])
        r = h['classify'](dst, dst, plan, 'TRANSFERRED', tol)
        self.assertTrue(r['previous_state_remains'])
        self.assertFalse(r['correct'])
        shifted = json.loads(json.dumps(transferred))
        shifted['bones']['bip_hand_l']['world_position'][0] += 0.01
        self.assertEqual(h['classify'](shifted, dst, plan, 'TRANSFERRED', tol)['state'], 'ORACLE_DISAGREEMENT')
        moved = json.loads(json.dumps(transferred))
        moved['bones']['bip_spine_0']['local_position'][2] += 0.01
        r = h['classify'](moved, dst, plan, 'TRANSFERRED', tol)
        self.assertEqual(r['state'], 'TRANSFERRED')
        self.assertFalse(r['correct'])
        self.assertIn('bone bip_spine_0', r['unrelated_changes'])
        stretched = json.loads(json.dumps(transferred))
        stretched['bones']['bip_lowerArm_l']['local_position'][1] += 0.01
        r = h['classify'](stretched, dst, plan, 'TRANSFERRED', tol)
        self.assertFalse(r['correct'])
        self.assertIn('bone bip_lowerArm_l local position/scale', r['unrelated_changes'])

    def test_quaternion_sign_equivalence_and_float32(self):
        h = load_harness()
        q = [0.371737, -0.504114, 0.601212, -0.496211]
        self.assertLess(h['angle_deg'](q, [-c for c in q]), 1e-9)
        self.assertEqual(h['f32'](0.1), 0.10000000149011612)


AUTHORISED_MUTATORS = set(['SetKeyValue', 'StartUndo', 'FinishUndo', 'AbortUndoableOperation', 'Undo', 'Redo'])
FORBIDDEN = set(['SetValue', 'Operate', 'SetHeadTimeInSeconds', 'SetHeadTimeInFrames', 'SetCurrentTime',
                 'InsertKey', 'SetKey', 'FindOrAddKey', 'SetAllKeys', 'ReplaceKeys', 'ClearKeys', 'RemoveKey',
                 'InsertKeyAtTime', 'ClearUndo', 'ClearRedo', 'SetUndoEnabled', 'SetUndoDepth', 'SaveSession',
                 'Save', 'SaveFile', 'SetMode', 'AddAttribute', 'RemoveAttribute', 'SetAbsPosition',
                 'SetAbsOrientation', 'ProcessEvents', 'processEvents', 'AddUndoElement', 'TraceUndo'])


class TestStaticSafety(Base):
    def calls(self):
        with open(HARNESS, 'rb') as f:
            tree = ast.parse(f.read())
        out = []
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        out.append((fn.name, node.func.attr))
        return out

    def test_only_authorised_native_mutators(self):
        calls = self.calls()
        names = set(c[1] for c in calls)
        self.assertEqual(names & FORBIDDEN, set())
        where = dict((m, sorted(set(f for f, a in calls if a == m))) for m in AUTHORISED_MUTATORS)
        self.assertEqual(where['SetKeyValue'], ['write_key'])
        self.assertEqual(where['FinishUndo'], ['commit', 'step_transfer'])
        self.assertEqual(where['StartUndo'], ['abort_check', 'commit', 'step_transfer'])
        self.assertEqual(where['AbortUndoableOperation'], ['abort_check', 'commit', 'step_transfer'])
        self.assertEqual(where['Undo'], ['perform', 'step_history'])
        self.assertEqual(where['Redo'], ['perform', 'step_history'])

    def test_no_production_imports_and_python27_syntax(self):
        with open(HARNESS, 'rb') as f:
            raw = f.read()
        source = raw.decode('ascii')
        tree = ast.parse(raw)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertEqual(imported - set(['os', 'sys', 'json', 'math', 're', 'struct', 'hashlib', 'datetime',
                                         'traceback', 'binascii', 'types', 'PySide', 'sfmApp', 'vs']), set())
        self.assertNotIn('nonlocal', source)


class TestProcedure(Base):
    def assert_no_scene_writes(self, e):
        self.assertEqual([c for c in e.world.dm.calls], [])

    def test_idle_propagation_pass(self):
        e = self.env('idle')
        final = e.run()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', statuses(e))
        names = [s[0] for s in statuses(e)]
        self.assertEqual(names, ['SOURCE_BASELINE', 'TRANSFER', 'SOURCE_RETURN', 'DESTINATION_RETURN', 'UNDO',
                                 'SOURCE_RETURN', 'DESTINATION_RETURN', 'REDO', 'SOURCE_RETURN',
                                 'DESTINATION_RETURN', 'FINAL_UNDO', 'SOURCE_RETURN', 'DESTINATION_RETURN'])
        self.assertTrue(all(not r.get('observed_changes') for n, r in e.reports()))
        result = e.finalize()
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['propagation'], {'committed': 'IDLE', 'undone': 'IDLE', 'redone': 'IDLE',
                                                 'final': 'IDLE'})
        calls = [c[0] for c in e.world.dm.calls]
        self.assertEqual(calls, ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo', 'Undo', 'Redo',
                                 'Undo'])
        descs = [c[1:] for c in e.world.dm.calls if c[0] == 'StartUndo']
        self.assertNotEqual(descs[0], descs[1])
        self.assertTrue(all(d[0] != d[1] for d in descs))
        transfer = [r for n, r in e.reports() if r['step'] == 'TRANSFER'][0]
        abort = [x for x in transfer['events'] if x['event'] == 'abort-check'][0]
        self.assertTrue(abort['authored_restored'] and abort['write']['exact'])
        commit = [x for x in transfer['events'] if x['event'] == 'commit'][0]
        self.assertEqual(len(commit['writes']), 6)
        self.assertTrue(all(w['exact'] and w['count_unchanged'] and w['time_unchanged'] for w in commit['writes']))
        self.assertEqual([w['channel'] for w in commit['writes']],
                         ['Hand_l_p', 'Hand_l_p', 'Hand_l_o', 'Hand_l_o', 'Elbow_l_p', 'Elbow_l_p'])
        self.assertEqual(sorted(set(w['ticks'] for w in commit['writes'])), [30000, 70415])
        o = [w['requested_float32'] for w in commit['writes'] if w['channel'] == 'Hand_l_o']
        self.assertEqual(o[0], o[1])
        # Per-channel indices resolved separately (Elbow_l_p has an extra key at time 0 in shot10).
        brackets = transfer['plan']['brackets']
        self.assertNotEqual(brackets['Elbow_l_p']['indices'], brackets['Hand_l_p']['indices'])
        self.assertEqual(e.layer('shot10', 'Hand_l_p').keys, original_keys('Hand_l_p'))
        hand = [c for c in e.world.shots['shot10'].controls if c.name == 'Hand_l'][0]
        self.assertEqual(fake_sfm.as_list(hand.get('valuePosition')), ctl_value('Hand_l', 'valuePosition'))
        self.assertIn('hand_target_residual', transfer['observation'])
        self.assertTrue(transfer['observation']['inputs_at_goal'])

    def test_retiming_dependent_pass(self):
        e = self.env('retime')
        final = e.run()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', statuses(e))
        self.assertEqual([s[0] for s in statuses(e)].count('RETIME'), 4)
        transfer = [r for n, r in e.reports() if r['step'] == 'TRANSFER'][0]
        self.assertEqual(transfer['idle_result'], 'PREVIOUS_STATE_REMAINS')
        self.assertFalse(transfer['observation']['inputs_at_goal'])
        result = e.finalize()
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(set(result['propagation'].values()), set(['RETIMING_DEPENDENT']))
        self.assertIn('required retiming', result['interpretation'])

    def test_no_propagation_after_retime_fails(self):
        e = self.env('never')
        final = e.run()
        self.assertEqual(final['status'], 'FAIL')
        self.assertEqual([s[0] for s in statuses(e)], ['SOURCE_BASELINE', 'TRANSFER', 'RETIME'])
        self.assertIn('prescribed retime', final['error'])
        self.assertEqual(e.finalize()['verdict'], 'FAIL')

    def test_oracle_disagreement_is_not_waived(self):
        e = self.env('idle')
        arm = e.world.shots['shot10'].transfer_arm
        for b in list(arm):
            q, p, wq = arm[b]
            arm[b] = (q, [p[0] + 0.01, p[1], p[2]], wq)
        final = e.run()
        self.assertEqual(final['status'], 'FAIL')
        self.assertEqual(final['observation']['state'], 'ORACLE_DISAGREEMENT')

    def test_unrelated_bone_change_fails(self):
        e = self.env('idle')
        spine = [h for h, (d, rec) in e.world.shots['shot10'].bone_dags.items() if d.name.endswith('(bip_spine_0)')]
        e.world.shift_unrelated_bone = spine[0]
        final = e.run()
        self.assertEqual(final['status'], 'FAIL')
        self.assertIn('bone bip_spine_0', final['observation']['unrelated_changes'])

    def test_abort_not_restoring_stops(self):
        e = self.env('idle')
        e.world.abort_broken = True
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('Abort did not restore', final['error'])
        self.assertEqual([c[0] for c in e.world.dm.calls], ['StartUndo', 'AbortUndoableOperation'])
        self.assertEqual(e.finalize()['verdict'], 'STOP')

    def test_synchronous_evaluation_not_rolled_back_stops(self):
        e = self.env('retime')
        e.world.eval_on_write = True
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('evaluated state is not the baseline', final['error'])
        self.assertEqual([c[0] for c in e.world.dm.calls], ['StartUndo', 'AbortUndoableOperation'])

    def test_write_without_effect_stops(self):
        e = self.env('idle')
        e.world.ignore_writes = True
        final = e.run()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('did not take effect', final['error'])

    def test_write_exception_restores_then_stops(self):
        e = self.env('idle')
        e.world.raise_on_write = True
        final = e.run()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('authored state restored', final['error'])
        self.assertEqual([c[0] for c in e.world.dm.calls], ['StartUndo', 'AbortUndoableOperation'])

    def test_float32_readback_mismatch_aborts_commit(self):
        e = self.env('idle')
        e.world.perturb_layer = e.layer('shot10', 'Elbow_l_p').h
        final = e.run()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('float32 readback mismatch on Elbow_l_p', final['error'])
        self.assertEqual([c[0] for c in e.world.dm.calls],
                         ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'AbortUndoableOperation'])
        aborted = [x for x in final['events'] if x['event'] == 'commit-aborted'][0]
        self.assertTrue(aborted['authored_restored'])
        self.assertEqual(e.layer('shot10', 'Elbow_l_p').keys, original_keys('Elbow_l_p'))

    def test_uncertain_commit_ownership_stops_without_undo(self):
        e = self.env('idle')
        e.world.mangle_undo_desc = True
        final = e.run()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('ownership uncertain', final['error'])
        self.assertNotIn('Undo', [c[0] for c in e.world.dm.calls])

    def test_foreign_undo_entry_stops_undo(self):
        e = self.env('idle')
        final = e.run(hooks={('UNDO', 'undone'): lambda env: env.world.dm.push_foreign('user edit')})
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'))
        self.assertIn('ownership uncertain', final['error'])
        self.assertNotIn('Undo', [c[0] for c in e.world.dm.calls])

    def test_foreign_entry_before_redo_stops(self):
        e = self.env('idle')
        final = e.run(hooks={('REDO', 'redone'): lambda env: env.world.dm.push_foreign('user edit')})
        self.assertEqual((final['step'], final['status']), ('REDO', 'STOP'))
        self.assertNotIn('Redo', [c[0] for c in e.world.dm.calls])

    def test_undo_not_restoring_stops(self):
        e = self.env('idle')
        e.world.undo_broken = True
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'))
        self.assertIn('did not produce the exact expected authored state', final['error'])

    def test_competing_writer_stops_before_any_write(self):
        e = self.env('idle')

        def rogue(env):
            hand = env.world.shots['shot10'].handles['Hand_l'].get('transform')
            env.world.add_channel('shot10', 'rogue', hand, 'position')
        final = e.run(hooks={('TRANSFER', 'committed'): rogue})
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('not the unique writer', final['error'])
        self.assert_no_scene_writes(e)

    def test_shared_log_stops(self):
        e = self.env('idle')

        def share(env):
            ch = env.world.add_channel('shot10', 'twin', env.world.document, 'value')
            ch.log = env.world.channel('shot10', 'Elbow_l_p').log
        final = e.run(hooks={('TRANSFER', 'committed'): share})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('log is shared', final['error'])
        self.assert_no_scene_writes(e)

    def test_bracket_key_missing_stops(self):
        e = self.env('idle')

        def move(env):
            layer = env.layer('shot10', 'Hand_l_o')
            for k in layer.keys:
                if k[0] == 70415:
                    k[0] = 70414
        final = e.run(hooks={('TRANSFER', 'committed'): move})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('70415 ticks is missing', final['error'])
        self.assert_no_scene_writes(e)

    def test_intervening_key_stops(self):
        e = self.env('idle')

        def insert(env):
            layer = env.layer('shot10', 'Elbow_l_p')
            i = [k[0] for k in layer.keys].index(30000)
            layer.keys.insert(i + 1, [50000, list(layer.keys[i][1])])
        final = e.run(hooks={('TRANSFER', 'committed'): insert})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('intervene', final['error'])
        self.assert_no_scene_writes(e)

    def test_modal_dialog_at_callback_entry_stops_before_writing(self):
        e = self.env('idle')
        r = e.submit()
        e.act(r['next'])
        e.submit(events=False)
        e.world.modal = object()
        e.world.run_events()
        final = e.last()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('modal', final['error'])
        self.assert_no_scene_writes(e)

    def test_concurrent_submission_refused(self):
        e = self.env('idle')
        r = e.submit()
        e.act(r['next'])
        e.submit(events=False)
        count = len(e.reports())
        e.submit(events=False)
        self.assertIn('still running', e.output[-1])
        self.assertEqual(len(e.reports()), count)
        e.world.run_events()
        self.assertEqual(e.last()['status'], 'CONTINUE')

    def test_authored_mutation_between_steps_stops(self):
        e = self.env('idle')

        def edit(env):
            layer = env.layer('shot10', 'Hip_p')
            layer.keys[0][1] = [c + 1.0 for c in layer.keys[0][1]]
        final = e.run(hooks={('DESTINATION_RETURN', 'committed'): edit})
        self.assertEqual((final['step'], final['status']), ('DESTINATION_RETURN', 'STOP'))
        self.assertIn('Unexpected authored state (destination', final['error'])

    def test_source_authored_mutation_stops(self):
        e = self.env('idle')

        def edit(env):
            layer = env.layer('shot15', 'Hip_p')
            layer.keys[0][1] = [c + 1.0 for c in layer.keys[0][1]]
        final = e.run(hooks={('TRANSFER', 'committed'): edit})
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('Unexpected authored state (source', final['error'])
        self.assert_no_scene_writes(e)

    def test_source_evaluated_change_fails(self):
        e = self.env('idle')

        def move(env):
            S = env.world.shots['shot15']
            dag = [d for h, (d, rec) in S.bone_dags.items() if d.name.endswith('(bip_spine_0)')][0]
            p = fake_sfm.as_list(dag.get('transform').get('position'))
            dag.get('transform').set('position', fake_sfm.Vector(p[0] + 0.5, p[1], p[2]))
        final = e.run(hooks={('SOURCE_RETURN', 'committed'): move})
        self.assertEqual((final['step'], final['status']), ('SOURCE_RETURN', 'FAIL'))
        self.assertIn('bone bip_spine_0', final['source_evaluated_changes'])

    def test_wrong_playhead_stops(self):
        e = self.env('idle')
        e.submit()
        final = e.submit()   # still at movie frame 5 (shot15)
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('requires shot10', final['error'])
        self.assert_no_scene_writes(e)

    def test_protected_file_change_stops(self):
        e = self.env('idle')

        def touch(env):
            with open(env.config['original_session'], 'wb') as f:
                f.write(b'changed')
        final = e.run(hooks={('TRANSFER', 'committed'): touch})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Protected file hash changed', final['error'])
        self.assert_no_scene_writes(e)

    def test_unreadable_required_evidence_is_inconclusive(self):
        e = self.env('idle')
        t = e.world.shots['shot15'].handles['Hand_l'].get('transform')
        e.world.unreadable.add((t.h, 'position'))
        final = e.submit()
        self.assertEqual((final['step'], final['status']), ('SOURCE_BASELINE', 'INCONCLUSIVE'))
        self.assertEqual(e.finalize()['verdict'], 'INCONCLUSIVE')

    def test_undo_disabled_stops(self):
        e = self.env('idle')
        e.world.dm.enabled = False
        final = e.run()
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Undo is not enabled', final['error'])
        self.assert_no_scene_writes(e)

    def test_harness_change_mid_ledger_stops(self):
        e = self.env('idle')
        r = e.submit()
        e.act(r['next'])
        with open(e.harness, 'ab') as f:
            f.write(b'\n# edited\n')
        final = e.submit()
        self.assertEqual((final['step'], final['status']), ('LEDGER_STOP', 'STOP'))
        self.assert_no_scene_writes(e)

    def test_ledger_tamper_and_empty_report_refused(self):
        e = self.env('idle')
        r = e.submit()
        e.act(r['next'])
        e.submit()
        path = os.path.join(e.config['reports_dir'], sorted(os.listdir(e.config['reports_dir']))[0])
        with open(path, 'ab') as f:
            f.write(b' ')
        count = len(e.reports())
        e.submit()
        self.assertIn('REFUSED', e.output[-1])
        self.assertIn('hash chain', e.output[-1])
        self.assertEqual(len(e.reports()), count)
        e2 = self.env('idle')
        open(os.path.join(e2.config['reports_dir'], 'F01W1-01-SOURCE_BASELINE.json'), 'wb').close()
        e2.submit()
        self.assertIn('REFUSED', e2.output[-1])
        self.assertIn('empty', e2.output[-1])

    def test_no_further_steps_after_end(self):
        e = self.env('idle')
        e.world.abort_broken = True
        e.run()
        count = len(e.reports())
        e.submit()
        self.assertIn('has ended', e.output[-1])
        self.assertEqual(len(e.reports()), count)


class TestFinalize(Base):
    def test_disposable_saved_after_experiment_stops(self):
        e = self.env('idle')
        e.run()
        with open(e.config['disposable_session'], 'wb') as f:
            f.write(b'saved by mistake')
        result = e.finalize()
        self.assertEqual(result['verdict'], 'STOP')
        self.assertFalse(result['protected_files']['disposable_session']['unchanged'])

    def test_incomplete_ledger_is_inconclusive(self):
        e = self.env('idle')
        e.submit()
        self.assertEqual(e.finalize()['verdict'], 'INCONCLUSIVE')

    def test_final_report_is_exclusive(self):
        e = self.env('idle')
        e.submit()
        e.finalize()
        self.assertRaises(OSError, e.finalize)

    def test_observed_attribute_change_prevents_pass(self):
        e = self.env('idle')
        e.run()
        ns = load_finalize()
        entries = ns['ledger'](e.config['reports_dir'])
        self.assertEqual(ns['verdict'](entries, True, True)[0], 'PASS')
        entries[3]['report']['observed_changes'] = ['/123/attributes/x']
        self.assertEqual(ns['verdict'](entries, True, True)[0], 'INCONCLUSIVE')


PREPARE = os.path.join(ROOT, 'tools', 'prepare_run.py')


class TestPrepare(Base):
    def package(self):
        root = tempfile.mkdtemp(prefix='f01w1_pkg_')
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, 'harness'))
        config = package_config()
        for k, content in (('original_session', b'original'), ('r2_fixture', b'fixture')):
            path = os.path.join(root, k + '.dmx')
            with open(path, 'wb') as f:
                f.write(content)
            config[k] = path
            config[k + '_sha256'] = hashlib.sha256(content).hexdigest()
        config['disposable_session_sha256'] = config['r2_fixture_sha256']
        run = os.path.join(root, 'run')
        config['disposable_session'] = os.path.join(run, 'disposable.dmx')
        config['reports_dir'] = os.path.join(run, 'reports')
        target = os.path.join(run, 'harness', 'f01w1_harness.py').replace('\\', '\\\\')
        files = {'f01w1_harness.py': open(HARNESS, 'rb').read(),
                 'config.json': json.dumps(config).encode('ascii'),
                 'NEXT_STEP.txt': ("exec(compile(open('%s', 'rb').read(), '%s', 'exec', 0, True), "
                                   "{'__name__': '__f01w1_owner_step__', '__file__': '%s'})\n"
                                   % (target, target, target)).encode('ascii')}
        hashes = {}
        for name, data in files.items():
            with open(os.path.join(root, 'harness', name), 'wb') as f:
                f.write(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        with open(os.path.join(root, 'HARNESS_SHA256.json'), 'wb') as f:
            f.write(json.dumps(hashes).encode('ascii'))
        return root, config

    def prepare(self, root):
        ns = {'__name__': 'offline', '__file__': PREPARE}
        with open(PREPARE, 'rb') as f:
            exec(compile(f.read(), PREPARE, 'exec', 0, True), ns)
        out = Out()
        old = sys.stdout
        sys.stdout = out
        try:
            return ns['main'](root)
        finally:
            sys.stdout = old

    def test_prepares_fresh_run_and_refuses_reuse(self):
        root, config = self.package()
        run = self.prepare(root)
        with open(config['disposable_session'], 'rb') as f:
            self.assertEqual(f.read(), b'fixture')
        self.assertEqual(sorted(os.listdir(os.path.join(run, 'harness'))),
                         ['NEXT_STEP.txt', 'config.json', 'f01w1_harness.py'])
        self.assertEqual(os.listdir(os.path.join(run, 'reports')), [])
        self.assertRaises(SystemExit, self.prepare, root)
        with open(config['original_session'], 'rb') as f:
            self.assertEqual(f.read(), b'original')

    def test_refuses_modified_harness(self):
        root, config = self.package()
        with open(os.path.join(root, 'harness', 'f01w1_harness.py'), 'ab') as f:
            f.write(b'# edit')
        self.assertRaises(SystemExit, self.prepare, root)
        self.assertFalse(os.path.exists(os.path.dirname(config['disposable_session'])))

    def test_refuses_changed_fixture(self):
        root, config = self.package()
        with open(config['r2_fixture'], 'wb') as f:
            f.write(b'other')
        self.assertRaises(SystemExit, self.prepare, root)
        self.assertFalse(os.path.exists(os.path.dirname(config['disposable_session'])))


def transferred_skeleton(dst, plan, arm, inputs=True):
    """The destination skeleton with the transferred arm; with inputs=True the
    rig inputs and their log evaluations also carry the float32 goals."""
    t = json.loads(json.dumps(dst))
    for b, (q, p, wq) in arm.items():
        t['bones'][b]['local_orientation'] = q
        t['bones'][b]['world_position'] = p
        t['bones'][b]['world_orientation'] = wq
    if inputs:
        w = plan['write_float32']
        t['handles']['Hand_l']['local_position'] = list(w['Hand_l_p'])
        t['handles']['Hand_l']['local_orientation'] = list(w['Hand_l_o'])
        t['handles']['Elbow_l']['local_position'] = list(w['Elbow_l_p'])
        for ch in ('Hand_l_p', 'Hand_l_o', 'Elbow_l_p'):
            t['arm_channels'][ch]['value_current'] = list(w[ch])
            t['arm_channels'][ch]['value_nominal'] = list(w[ch])
    return t


class FakeColor(object):
    def __init__(self, *rgba):
        self.rgba = rgba

    def r(self):
        return self.rgba[0]

    def g(self):
        return self.rgba[1]

    def b(self):
        return self.rgba[2]

    def a(self):
        return self.rgba[3]


class TestP1Evidence(Base):
    """P1-1: preservation evidence must be readable and losslessly comparable."""

    def test_no_type_markers_exist(self):
        with open(HARNESS, 'rb') as f:
            source = f.read().decode('ascii')
        self.assertNotIn('unsupported_type', source)
        self.assertNotIn('def key_value', source)

    def test_identical_unsupported_layers_cannot_be_compared(self):
        e = self.env()
        h = load_harness()
        layer = fake_sfm.Layer(e.world, 'DmeVector2LogLayer', 'v2', None, [[0, [0.0, 0.0]]])
        self.assertRaises(h['Unresolved'], h['key_entries'], layer, [0])
        layer2 = fake_sfm.Layer(e.world, 'DmeVector2LogLayer', 'v2b', None, [[0, [0.0, 0.0]]])
        self.assertRaises(h['Unresolved'], h['key_entries'], layer2, [0])

    def test_identical_unreadable_records_cannot_satisfy_preservation(self):
        h = load_harness()
        a = {'channels': [{'binding': {'mode': {'status': 'UNREADABLE', 'error': 'x'}}}]}
        b = json.loads(json.dumps(a))
        self.assertEqual(h['differences'](a, b), [])          # equal as data ...
        self.assertRaises(h['Unresolved'], h['require_readable'], a, 'test')   # ... but never accepted
        self.assertEqual(h['require_readable']({'f': {'status': 'ABSENT'}}, 'test'), {'f': {'status': 'ABSENT'}})

    def test_key_serializers_are_lossless_and_strict(self):
        h = load_harness()
        self.assertEqual(h['key_color'](FakeColor(1, 2, 3, 255)), [1, 2, 3, 255])
        self.assertRaises(h['Unresolved'], h['key_color'], FakeColor(1, 2, 3, 256))
        self.assertRaises(h['Unresolved'], h['key_color'], FakeColor(1, 2, 3, 0.5))
        self.assertRaises(h['Unresolved'], h['key_float'], True)
        self.assertRaises(h['Unresolved'], h['key_float'], 'text')
        self.assertEqual(sorted(h['KEY_SERIALIZERS']), ['DmeColorLogLayer', 'DmeFloatLogLayer',
                                                         'DmeQuaternionLogLayer', 'DmeVector3LogLayer'])

    def test_unsupported_layer_type_in_preflight_is_inconclusive_without_writes(self):
        e = self.env()

        def add(env):
            ch = env.world.add_channel('shot10', 'vec2', env.world.document, 'value')
            ch.log.layers[0].kind = 'DmeVector2LogLayer'
        final = e.run(hooks={('TRANSFER', 'committed'): add})
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'INCONCLUSIVE'))
        self.assertIn('No lossless key serializer', final['error'])
        self.assertEqual(e.world.dm.calls, [])
        self.assertEqual(e.finalize()['verdict'], 'INCONCLUSIVE')

    def test_unreadable_field_in_preflight_is_inconclusive_without_writes(self):
        e = self.env()

        def hide(env):
            env.world.unreadable.add((env.world.channel('shot10', 'Hip_p').h, 'mode'))
        final = e.run(hooks={('TRANSFER', 'committed'): hide})
        self.assertEqual(final['status'], 'INCONCLUSIVE')
        self.assertIn('evidence is unreadable', final['error'])
        self.assertEqual(e.world.dm.calls, [])

    def test_later_unreadability_prevents_pass(self):
        e = self.env()

        def hide(env):
            env.world.unreadable.add((env.world.channel('shot10', 'Hip_p').h, 'mode'))
        final = e.run(hooks={('SOURCE_RETURN', 'committed'): hide})
        self.assertEqual((final['step'], final['stage'], final['status']),
                         ('SOURCE_RETURN', 'committed', 'INCONCLUSIVE'))
        self.assertFalse(final['evidence_complete'])
        self.assertEqual(e.finalize()['verdict'], 'INCONCLUSIVE')

    def test_unreadable_evidence_during_abort_recovery_stops(self):
        e = self.env()
        e.world.unreadable_on_abort = set([(e.world.channel('shot10', 'Hip_p').h, 'mode')])
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('Recovery unverified', final['error'])

    def test_unreadable_weight_is_inconclusive(self):
        e = self.env()
        target = [x for x in e.world.by_handle.values() if getattr(x, 'kind', None) == 'DmeConstraintTarget'
                  and x.name == 'Hand_l' and x.h in e.world.shots['shot10'].op_targets['ikConstraint_Hand_l']][0]
        e.world.unreadable.add((target.h, 'targetWeight'))
        final = e.run()
        self.assertEqual(final['status'], 'INCONCLUSIVE')
        self.assertEqual(e.world.dm.calls, [])


class TestRecoveryClassification(Base):
    """Unreadable evidence while verifying an Abort/Undo/Redo restoration is STOP (recovery unverified)."""

    def bone_position(self, env, shot, bone):
        S = env.world.shots[shot]
        dag = [d for h, (d, rec) in S.bone_dags.items() if d.name.endswith('(%s)' % bone)][0]
        return (dag.get('transform').h, 'position')

    def assert_recovery_stop(self, e, final, step, stage):
        self.assertEqual((final['step'], final.get('stage'), final['status']), (step, stage, 'STOP'), statuses(e))
        self.assertIn('Recovery unverified', final['error'])
        self.assertFalse(final['evidence_complete'])
        self.assertEqual(e.finalize()['verdict'], 'STOP')

    def test_unreadable_source_after_commit_abort_stops(self):
        # Six authorized writes, then the source-authored capture inside the commit
        # becomes unreadable; the abort restores the destination but the source stays
        # unreadable: STOP (recovery unverified), never INCONCLUSIVE.
        e = self.env()
        e.world.unreadable_after_writes = (6, set([(e.world.channel('shot15', 'Hip_p').h, 'mode')]))
        final = e.run()
        self.assert_recovery_stop(e, final, 'TRANSFER', 'committed')
        self.assertIn('source authored state after commit abort', final['error'])
        self.assertIn('Unresolved', final['error'])    # the original commit failure is kept
        self.assertEqual([c[0] for c in e.world.dm.calls],
                         ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'AbortUndoableOperation'])
        commit = [c for c in e.world.dm.calls if c[0] == 'StartUndo'][1]
        self.assertTrue(commit[1].startswith('F01W1 arm transfer'))
        aborted = [x for x in final['events'] if x['event'] == 'commit-aborted'][0]
        self.assertEqual(len(aborted['writes']), 6)
        self.assertIn('Unresolved', aborted['commit_failure'])
        self.assertIn('source authored state after commit abort', aborted['recovery_error'])
        for name in ('Hand_l_p', 'Hand_l_o', 'Elbow_l_p'):
            self.assertEqual(e.layer('shot10', name).keys, original_keys(name))   # destination restored

    def test_source_changed_after_commit_abort_stops(self):
        e = self.env()
        hip = e.layer('shot15', 'Hip_p')

        def corrupt(world):
            hip.keys[0][1] = [c + 1.0 for c in hip.keys[0][1]]
        real = e.world.dm.AbortUndoableOperation

        def abort():
            real()
            if len(e.world.dm.calls) == 4:      # the commit's abort
                corrupt(e.world)
        e.world.dm.AbortUndoableOperation = abort
        e.world.perturb_layer = e.layer('shot10', 'Elbow_l_p').h
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('source authored state differs from its baseline after the abort', final['error'])
        self.assertIn('float32 readback mismatch', final['error'])
        aborted = [x for x in final['events'] if x['event'] == 'commit-aborted'][0]
        self.assertTrue(aborted['authored_restored'])
        self.assertFalse(aborted['source_preserved'])
        self.assertEqual(e.finalize()['verdict'], 'STOP')

    def test_unreadable_source_after_abort_stops(self):
        e = self.env()
        e.world.unreadable_on_abort = set([(e.world.channel('shot15', 'Hip_p').h, 'mode')])
        final = e.run()
        self.assert_recovery_stop(e, final, 'TRANSFER', 'committed')
        self.assertIn('source authored state after abort', final['error'])
        self.assertEqual([c[0] for c in e.world.dm.calls], ['StartUndo', 'AbortUndoableOperation'])

    def test_unreadable_evaluated_evidence_after_abort_stops(self):
        e = self.env()
        e.world.unreadable_on_abort = set([self.bone_position(e, 'shot10', 'bip_spine_0')])
        final = e.run()
        self.assert_recovery_stop(e, final, 'TRANSFER', 'committed')
        self.assertEqual([c[0] for c in e.world.dm.calls], ['StartUndo', 'AbortUndoableOperation'])

    def test_unreadable_source_after_undo_stops(self):
        e = self.env()
        e.world.unreadable_on_undo = set([(e.world.channel('shot15', 'Hip_p').h, 'mode')])
        final = e.run()
        self.assert_recovery_stop(e, final, 'UNDO', 'undone')
        self.assertIn('source authored state after undo', final['error'])

    def test_unreadable_evaluated_evidence_after_undo_stops(self):
        e = self.env()
        e.world.unreadable_on_undo = set([self.bone_position(e, 'shot10', 'bip_spine_0')])
        final = e.run()
        self.assert_recovery_stop(e, final, 'UNDO', 'undone')

    def test_unreadable_source_after_redo_stops(self):
        e = self.env()
        e.world.unreadable_on_redo = set([(e.world.channel('shot15', 'Hip_p').h, 'mode')])
        final = e.run()
        self.assert_recovery_stop(e, final, 'REDO', 'redone')

    def test_unreadable_evidence_at_final_restoration_stops(self):
        e = self.env()

        def hide(env):
            env.world.unreadable.add(self.bone_position(env, 'shot10', 'bip_spine_0'))
        final = e.run(hooks={('DESTINATION_RETURN', 'final'): hide})
        self.assert_recovery_stop(e, final, 'DESTINATION_RETURN', 'final')

    def test_unreadable_evidence_in_undone_source_return_stops(self):
        e = self.env()

        def hide(env):
            env.world.unreadable.add((env.world.channel('shot10', 'Hip_p').h, 'mode'))
        final = e.run(hooks={('SOURCE_RETURN', 'undone'): hide})
        self.assert_recovery_stop(e, final, 'SOURCE_RETURN', 'undone')

    def test_preflight_unreadability_stays_inconclusive(self):
        e = self.env()

        def hide(env):
            env.world.unreadable.add((env.world.channel('shot10', 'Hip_p').h, 'mode'))
        final = e.run(hooks={('TRANSFER', 'committed'): hide})
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'INCONCLUSIVE'))
        self.assertEqual(e.world.dm.calls, [])


class TestP1Inputs(Base):
    """P1-2: rig inputs and their log evaluations are acceptance conditions."""

    def plan(self):
        e = self.env()
        m = TestMath('test_quaternion_sign_equivalence_and_float32')
        h = load_harness()
        src = h['roundtrip'](m.capture(e, h, 'source'))
        dst = h['roundtrip'](m.capture(e, h, 'destination'))
        plan = h['roundtrip'](h['compute_goals'](src, dst, e.config))
        return e, h, dst, plan, e.config['tolerances']

    def test_baseline_states_require_baseline_inputs(self):
        """Aborted, undone and final states all expect BASELINE."""
        e, h, dst, plan, tol = self.plan()
        goal_inputs = transferred_skeleton(dst, plan, {}, inputs=True)   # baseline skeleton, goal inputs
        r = h['classify'](goal_inputs, dst, plan, 'BASELINE', tol)
        self.assertEqual(r['state'], 'BASELINE')
        self.assertFalse(r['correct'])
        self.assertIn('input Hand_l_p handle value', r['input_errors'])
        stale_log = json.loads(json.dumps(dst))
        stale_log['arm_channels']['Elbow_l_p']['value_nominal'] = list(plan['write_float32']['Elbow_l_p'])
        r = h['classify'](stale_log, dst, plan, 'BASELINE', tol)
        self.assertFalse(r['correct'])
        self.assertEqual(r['input_errors'], ['input Elbow_l_p log value_nominal'])
        elbow_o = json.loads(json.dumps(dst))
        elbow_o['arm_channels']['Elbow_l_o']['value_current'] = [0.0, 0.0, 0.0, 1.0]
        self.assertFalse(h['classify'](elbow_o, dst, plan, 'BASELINE', tol)['correct'])

    def test_transferred_states_require_goal_log_evaluation(self):
        e, h, dst, plan, tol = self.plan()
        t = transferred_skeleton(dst, plan, e.world.shots['shot10'].transfer_arm)
        t['arm_channels']['Hand_l_o']['value_current'] = dst['arm_channels']['Hand_l_o']['value_current']
        r = h['classify'](t, dst, plan, 'TRANSFERRED', tol)
        self.assertFalse(r['correct'])
        self.assertEqual(r['input_errors'], ['input Hand_l_o log value_current'])

    def test_residual_is_diagnostic_only(self):
        e, h, dst, plan, tol = self.plan()
        t = transferred_skeleton(dst, plan, e.world.shots['shot10'].transfer_arm)
        t['handles']['Hand_l']['world_position'][0] += 5.0
        r = h['classify'](t, dst, plan, 'TRANSFERRED', tol)
        self.assertTrue(r['correct'])
        self.assertGreater(r['hand_target_residual'], 4.0)

    def test_aborted_state_with_wrong_inputs_stops(self):
        e = self.env('idle')
        e.world.offset_after_abort = 0.5
        final = e.run()
        self.assertEqual((final['step'], final['status']), ('TRANSFER', 'STOP'))
        self.assertIn('evaluated state is not the baseline', final['error'])
        ev = [x for x in final['events'] if x['event'] == 'abort-evaluated'][0]
        self.assertEqual(ev['observation']['state'], 'BASELINE')
        self.assertIn('input Hand_l_p handle value', ev['observation']['input_errors'])

    def stage_case(self, step, stage):
        e = self.env('idle')

        def corrupt(env):
            env.world.input_offset = 0.5
        final = e.run(hooks={(step, stage): corrupt})
        self.assertEqual(final['status'], 'FAIL', statuses(e))
        self.assertEqual((final['step'], final['stage']), ('RETIME', stage))
        self.assertIn('input Hand_l_p handle value', final['observation']['input_errors'])
        self.assertEqual(e.finalize()['verdict'], 'FAIL')

    def test_committed_state_with_wrong_inputs_fails(self):
        e = self.env('idle')
        e.world.offset_after_finish = 0.5     # corrupt the rig input only after the commit
        final = e.run()
        self.assertEqual((final['step'], final['stage'], final['status']), ('RETIME', 'committed', 'FAIL'))
        self.assertEqual(final['observation']['state'], 'TRANSFERRED')
        self.assertIn('input Hand_l_p handle value', final['observation']['input_errors'])
        self.assertEqual(e.finalize()['verdict'], 'FAIL')

    def test_undone_state_with_wrong_inputs_fails(self):
        self.stage_case('UNDO', 'undone')

    def test_redone_state_with_wrong_inputs_fails(self):
        self.stage_case('REDO', 'redone')

    def test_final_state_with_wrong_inputs_fails(self):
        self.stage_case('FINAL_UNDO', 'final')


class TestP1WeightsScale(Base):
    """P1-3: constraint weights and model/root/collar scale are judged."""

    def ik_target(self, e, shot):
        S = e.world.shots[shot]
        return [e.world.by_handle[h] for h in S.op_targets['ikConstraint_Hand_l']][0]

    def test_changed_weight_fails(self):
        e = self.env('idle')

        def weaken(env):
            self.ik_target(env, 'shot10').set('targetWeight', 0.5)
        final = e.run(hooks={('DESTINATION_RETURN', 'committed'): weaken})
        self.assertEqual((final['step'], final['status']), ('DESTINATION_RETURN', 'FAIL'))
        self.assertIn('weights ik', final['observation']['unrelated_changes'])

    def test_changed_model_scale_fails(self):
        e = self.env('idle')

        def scale(env):
            env.world.shots['shot10'].gm.get('transform').set('scale', 1.25)
        final = e.run(hooks={('DESTINATION_RETURN', 'committed'): scale})
        self.assertEqual(final['status'], 'FAIL')
        self.assertIn('scale model', final['observation']['unrelated_changes'])

    def test_changed_collar_scale_fails_at_destination(self):
        e = self.env('idle')

        def scale(env):
            env.world.shots['shot10'].handles['CollarL'].get('transform').set('scale', 1.1)
        final = e.run(hooks={('DESTINATION_RETURN', 'undone'): scale})
        self.assertEqual(final['status'], 'FAIL')
        self.assertIn('scale handle CollarL', final['observation']['unrelated_changes'])

    def test_source_return_judges_weights_and_scale(self):
        for change, label in ((lambda env: self.ik_target(env, 'shot15').set('targetWeight', 0.5), 'weights ik'),
                              (lambda env: env.world.shots['shot15'].handles['rig_root'].get('transform')
                               .set('scale', 2.0), 'scale handle rig_root')):
            e = self.env('idle')
            final = e.run(hooks={('SOURCE_RETURN', 'redone'): change})
            self.assertEqual((final['step'], final['status']), ('SOURCE_RETURN', 'FAIL'))
            self.assertIn(label, final['source_evaluated_changes'])


class TestFinalizerAudit(Base):
    """PASS depends on independently verified evidence, not on the terminal status."""

    def complete(self):
        e = self.env('idle')
        e.run()
        ns = load_finalize()
        entries = ns['ledger'](e.config['reports_dir'])
        self.assertEqual(ns['verdict'](entries, True, True), ('PASS', []))
        return ns, entries

    def mutated(self, ns, entries, fn):
        copy_ = json.loads(json.dumps(entries))
        fn(copy_)
        verdict, reasons = ns['verdict'](copy_, True, True)
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertTrue(reasons)
        return reasons

    def by_step(self, entries, step, stage):
        return [e['report'] for e in entries if e['report']['step'] == step and e['report'].get('stage') == stage][0]

    def test_contradictory_or_incomplete_evidence_cannot_pass(self):
        ns, entries = self.complete()

        def obs(step, stage, key, value):
            def f(es):
                self.by_step(es, step, stage)['observation'][key] = value
            return f

        def commit_write(es):
            ev = [x for x in self.by_step(es, 'TRANSFER', 'committed')['events'] if x['event'] == 'commit'][0]
            ev['writes'][3]['exact'] = False

        def abort_restore(es):
            ev = [x for x in self.by_step(es, 'TRANSFER', 'committed')['events'] if x['event'] == 'abort-check'][0]
            ev['authored_restored'] = False

        def ownership(es):
            ev = [x for x in self.by_step(es, 'REDO', 'redone')['events'] if x['event'] == 'redo'][0]
            ev['undo_before']['redo_desc'] = 'someone else'

        def evidence(es):
            es[5]['report']['evidence_complete'] = False

        def missing_step(es):
            del es[6]

        def extra_step(es):
            es.append(json.loads(json.dumps(es[-1])))

        def pid(es):
            es[4]['report']['pid'] = 1

        def source(es):
            self.by_step(es, 'SOURCE_RETURN', 'final')['source_evaluated_changes'] = ['bone x']

        def integrity(es):
            es[2]['report']['integrity_after'] = {'changed': True}

        def propagation(es):
            self.by_step(es, 'UNDO', 'undone')['propagation'] = None

        for fn in (obs('TRANSFER', 'committed', 'inputs_ok', False),
                   obs('UNDO', 'undone', 'input_errors', ['input Hand_l_p handle value']),
                   obs('DESTINATION_RETURN', 'final', 'unrelated_change_count', 1),
                   obs('DESTINATION_RETURN', 'redone', 'state', 'BASELINE'),
                   obs('REDO', 'redone', 'correct', False),
                   commit_write, abort_restore, ownership, evidence, missing_step, extra_step, pid, source,
                   integrity, propagation):
            self.mutated(ns, entries, fn)

    def commit_event(self, entries):
        return [x for x in self.by_step(entries, 'TRANSFER', 'committed')['events'] if x['event'] == 'commit'][0]

    def test_write_readback_contradiction_rejected(self):
        """A: exact=True cannot override a readback that differs from the requested float32 value."""
        ns, entries = self.complete()

        def readback(es):
            w = self.commit_event(es)['writes'][2]
            w['readback'] = [c + 0.5 for c in w['readback']]
            self.assertTrue(w['exact'])
        self.mutated(ns, entries, readback)

        def requested(es):
            w = self.commit_event(es)['writes'][4]
            w['requested_float32'] = [c + 0.5 for c in w['requested_float32']]
            w['readback'] = list(w['requested_float32'])          # self-consistent, but not the plan
        self.mutated(ns, entries, requested)

        def abort_readback(es):
            ev = [x for x in self.by_step(es, 'TRANSFER', 'committed')['events'] if x['event'] == 'abort-check'][0]
            ev['write']['readback'] = [c + 0.5 for c in ev['write']['readback']]
        self.mutated(ns, entries, abort_readback)

    def test_abort_restoration_contradiction_rejected(self):
        """B: authored_restored=True with a nonempty (or missing) differences list is not proof."""
        ns, entries = self.complete()

        def nonempty(es):
            ev = [x for x in self.by_step(es, 'TRANSFER', 'committed')['events'] if x['event'] == 'abort-check'][0]
            ev['differences'] = ['/channels/3/layers/0/keys/1/1']
            self.assertTrue(ev['authored_restored'])
        self.mutated(ns, entries, nonempty)

        def missing(es):
            ev = [x for x in self.by_step(es, 'TRANSFER', 'committed')['events'] if x['event'] == 'abort-check'][0]
            del ev['differences']
        self.mutated(ns, entries, missing)

    def test_per_channel_bracket_coverage_required(self):
        """C: the global tick set {30000, 70415} must not stand in for per-channel coverage."""
        ns, entries = self.complete()

        def both_at_30000(es):
            writes = self.commit_event(es)['writes']
            first = [w for w in writes if w['channel'] == 'Hand_l_p'][0]
            second = [w for w in writes if w['channel'] == 'Hand_l_p'][1]
            second['ticks'] = first['ticks']
            second['index'] = first['index']
            self.assertEqual(sorted(set(w['ticks'] for w in writes)), [30000, 70415])   # globally still "complete"
        self.mutated(ns, entries, both_at_30000)

        def swapped_indices(es):
            writes = [w for w in self.commit_event(es)['writes'] if w['channel'] == 'Elbow_l_p']
            writes[0]['index'], writes[1]['index'] = writes[1]['index'], writes[0]['index']
        self.mutated(ns, entries, swapped_indices)

        def wrong_index(es):
            w = [w for w in self.commit_event(es)['writes'] if w['channel'] == 'Hand_l_o'][1]
            w['index'] = w['index'] + 1
        self.mutated(ns, entries, wrong_index)

        def bracket_times(es):
            plan = self.by_step(es, 'TRANSFER', 'committed')['plan']
            b = plan['brackets']['Elbow_l_p']
            b['times'][b['indices'][1]] = 70414
        self.mutated(ns, entries, bracket_times)

    def test_status_alone_is_not_evidence(self):
        ns, entries = self.complete()
        stripped = json.loads(json.dumps(entries))
        for e in stripped:
            for key in ('observation', 'events', 'evidence_complete', 'plan'):
                e['report'].pop(key, None)
        verdict, reasons = ns['verdict'](stripped, True, True)
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertGreater(len(reasons), 10)


def original_keys(channel):
    st = r3('R3-shot10-A.json')['state']
    c = [x for x in st['channels'] if x['identity']['name'] == channel][0]
    return [[int(round(k['time']['value']['seconds'] * 10000)), k['value']['value']] for k in c['layers'][0]['keys']]


def ctl_value(name, field):
    st = r3('R3-shot10-A.json')['state']
    c = [x for x in st['control_inventory'] if x['identity']['name'] == name][0]
    return c['fields'][field]['value']


def main(results_path=None):
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for case in (TestMath, TestStaticSafety, TestProcedure, TestFinalize, TestPrepare, TestP1Evidence,
                 TestRecoveryClassification, TestP1Inputs, TestP1WeightsScale, TestFinalizerAudit):
        suite.addTests(loader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if results_path:
        with open(results_path, 'wb') as f:
            f.write(json.dumps({'python': sys.version, 'tests': result.testsRun, 'failures': len(result.failures),
                                'errors': len(result.errors), 'native_execution': False}, indent=1).encode('ascii'))
    return result.wasSuccessful()


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
