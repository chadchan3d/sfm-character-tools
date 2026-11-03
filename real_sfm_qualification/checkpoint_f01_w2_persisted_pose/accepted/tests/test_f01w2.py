# -*- coding: ascii -*-
"""Offline qualification of the F-01 W2 harness, gate and finalizer.
Python 2.7 (SFM) and 3.

Fake native modules only (tests/fake_sfm_w2.py, built from the committed
synthetic fixture tests/fixtures/synthetic_scene.json). No SFM, no native
writes, no session files, no private captures: every protected file is a
temporary stand-in. Two fake worlds stand for the two SFM processes; process B's
world poisons every source-pose value.

usage: python test_f01w2.py [RESULTS_JSON]
"""
from __future__ import print_function

import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HARNESS_DIR = os.path.join(ROOT, 'harness')
HARNESS_FILES = ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py')
TEMPLATE = os.path.join(ROOT, 'config.template.json')
FINALIZE = os.path.join(ROOT, 'tools', 'finalize_f01w2.py')
PREPARE = os.path.join(ROOT, 'tools', 'prepare_run.py')
FIXTURES = os.path.join(HERE, 'fixtures')
GOLDEN = os.path.join(FIXTURES, 'golden_left_arm_pose.f01w2.json')
sys.path.insert(0, HERE)
import fake_sfm_w2 as fake  # noqa: E402

A_PID, GATE_PID, B_PID = 4000, 5000, 6000


def load(path, name='offline'):
    ns = {'__name__': name, '__file__': path}
    with open(path, 'rb') as f:
        exec(compile(f.read(), path, 'exec', 0, True), ns)
    return ns


def load_core():
    return load(os.path.join(HARNESS_DIR, 'f01w2_core.py'))


class Out(object):
    def __init__(self):
        self.lines = []

    def write(self, s):
        self.lines.append(s)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.lines)


def quiet(fn, *args, **kwargs):
    out = Out()
    old = sys.stdout
    sys.stdout = out
    try:
        return fn(*args, **kwargs)
    finally:
        sys.stdout = old


# ---------------------------------------------------------------------------
# Independent expectation (matrices from the fake, not the harness math)
# ---------------------------------------------------------------------------

def handle_world(S, name):
    dag = S.handles[name]
    return fake.xf(dag.world_xf[0], dag.world_xf[1])


def expected_application(world_a, world_b):
    """Destination-local inputs that reproduce the source's collar-relative
    hand/elbow, computed with the fake's matrices from both worlds."""
    src, dst = world_a.shots['shot15'], world_b.shots['shot10']
    Cs, Cd = handle_world(src, 'CollarL'), handle_world(dst, 'CollarL')
    Rd = handle_world(dst, 'rig_root')
    M = fake.xf_mul(Cd, fake.xf_inv(Cs))
    hand = fake.xf_mul(fake.xf_inv(Rd), fake.xf_mul(M, handle_world(src, 'Hand_l')))
    elbow = fake.xf_mul(fake.xf_inv(Rd), fake.xf_mul(M, handle_world(src, 'Elbow_l')))
    return {'Hand_l_p': [fake.f32(c) for c in hand[0]], 'Hand_l_o': fake.m_to_q(hand[1]),
            'Elbow_l_p': [fake.f32(c) for c in elbow[0]]}


# ---------------------------------------------------------------------------
# Environment: run directory, two processes, gate and finalizer
# ---------------------------------------------------------------------------

class Env(object):
    def __init__(self, policy='idle'):
        self.dir = tempfile.mkdtemp(prefix='f01w2_test_')
        self.run_dir = os.path.join(self.dir, 'run')
        self.hdir = os.path.join(self.run_dir, 'harness')
        for sub in ('harness', 'reports', 'poses'):
            os.makedirs(os.path.join(self.run_dir, sub))
        for name in HARNESS_FILES:
            shutil.copy2(os.path.join(HARNESS_DIR, name), os.path.join(self.hdir, name))
        with open(TEMPLATE, 'rb') as f:
            config = json.loads(f.read().decode('utf-8'))
        r2 = b'synthetic R2 fixture bytes'
        files = {'original_session': (os.path.join(self.dir, 'original.dmx'), b'original session bytes'),
                 'r2_fixture': (os.path.join(self.dir, 'r2.dmx'), r2),
                 'capture_session': (os.path.join(self.run_dir, 'F01_W2_CAPTURE_DISPOSABLE.dmx'), r2),
                 'apply_session': (os.path.join(self.run_dir, 'F01_W2_APPLY_DISPOSABLE.dmx'), r2),
                 'cpm_source': (os.path.join(self.dir, 'cpm.py'), b'cpm source bytes')}
        for k, (path, content) in files.items():
            with open(path, 'wb') as f:
                f.write(content)
            config[k] = path
            if k != 'cpm_source':
                config[k + '_sha256'] = hashlib.sha256(content).hexdigest()
        config['run_dir'] = self.run_dir
        config['reports_dir'] = os.path.join(self.run_dir, 'reports')
        config['pose_path'] = os.path.join(self.run_dir, 'poses', 'left_arm_pose.f01w2.json')
        self.config = config
        self.config_path = os.path.join(self.hdir, 'config.json')
        self.write_config()
        self.clock = [1000]
        self.table = {A_PID: {'creation_filetime': 1000, 'running': True, 'image': 'C:\\SFM\\sfm.exe'}}
        self.policy = policy
        self.world = None
        self.world_a = None
        self.world_b = None
        self.saved = {}
        for name in ('sfmApp', 'vs', 'PySide', 'PySide.QtCore', 'PySide.QtGui', 'f01w2_runtime'):
            self.saved[name] = sys.modules.get(name)
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

    # ---- processes ----------------------------------------------------------
    def new_process(self, world, pid):
        """A fresh SFM process: its own world, modules and harness runtime."""
        self.world = world
        world.policy = self.policy
        for name, module in world.modules().items():
            sys.modules[name] = module
        rt = types.ModuleType('f01w2_runtime')
        rt.active = None
        rt.timers = []
        rt.process_provider = fake.FakeProcesses(self.table, pid, self.clock)
        sys.modules['f01w2_runtime'] = rt

    def start_a(self, **kw):
        self.world_a = fake.World(self.config['capture_session'], handle_base=100000, **kw)
        self.new_process(self.world_a, A_PID)
        self.world_a.set_frame(5)
        return self.world_a

    def exit_a(self):
        self.table[A_PID]['running'] = False
        sys.modules.pop('f01w2_runtime', None)

    def gate(self, provider=None):
        if GATE_PID not in self.table:
            self.clock[0] += 10
            self.table[GATE_PID] = {'creation_filetime': self.clock[0], 'running': True,
                                    'image': 'C:\\Python310\\python.exe'}
        ns = load(PREPARE)
        provider = provider or fake.FakeProcesses(self.table, GATE_PID, self.clock)
        return quiet(ns['gate'], self.config_path, provider)

    def start_b(self, pid=B_PID, poison=True, **kw):
        self.clock[0] += 1000
        self.table[pid] = {'creation_filetime': self.clock[0], 'running': True, 'image': 'C:\\SFM\\sfm.exe'}
        self.world_b = fake.World(self.config['apply_session'], handle_base=500000, poison_source=poison, **kw)
        self.new_process(self.world_b, pid)
        self.world_b.set_frame(10)
        return self.world_b

    # ---- submissions --------------------------------------------------------
    def submit(self, entry, events=True):
        script = os.path.join(self.hdir, {'capture': 'f01w2_capture.py', 'apply': 'f01w2_apply.py'}[entry])
        out = Out()
        old = sys.stdout
        sys.stdout = out
        try:
            ns = {'__name__': '__f01w2_owner_step__', '__file__': script}
            with open(script, 'rb') as f:
                exec(compile(f.read(), script, 'exec', 0, True), ns)
            if events:
                self.world.run_events()
        finally:
            sys.stdout = old
        self.output.append(out.text())
        return self.last()

    def reports(self):
        d = self.config['reports_dir']
        names = sorted(n for n in os.listdir(d) if n.startswith('F01W2-') and n[6:8].isdigit())
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
        if nxt['step'] == 'RETIME':
            self.world.set_frame(11)
            self.world.set_frame(10)

    def capture(self, **kw):
        self.start_a(**kw)
        return self.submit('capture')

    def run_b(self, hooks=None, limit=20):
        hooks = hooks or {}
        due = {'step': 'APPLY', 'stage': 'committed'}
        for _ in range(limit):
            hook = hooks.get((due['step'], due.get('stage')))
            if hook is not None:
                hook(self)
            report = self.submit('apply')
            if report['status'] != 'CONTINUE':
                return report
            due = report['next']
            self.act(due)
        raise AssertionError('procedure did not end')

    def complete(self, b_hooks=None, **kw):
        cap = self.capture()
        assert cap['status'] == 'CAPTURE_COMPLETE_PENDING_CLOSE', (cap.get('error'), self.output)
        self.exit_a()
        self.gate()
        self.start_b(**kw)
        return self.run_b(b_hooks)

    def finalize(self, offline=True):
        ns = load(FINALIZE)
        return quiet(ns['main'], self.config_path, offline)

    def pose_bytes(self):
        with open(self.config['pose_path'], 'rb') as f:
            return f.read()

    def layer(self, world, shot, channel):
        return world.channel(shot, channel).log.layers[0]


def statuses(env):
    return [(n[9:-5], r['status'] if r else None, r.get('stage') if r else None,
             r.get('propagation') if r else None) for n, r in env.reports()]


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


# ---------------------------------------------------------------------------
# End-to-end procedure
# ---------------------------------------------------------------------------

class TestProcedure(Base):
    def test_full_procedure_pass(self):
        e = self.env()
        final = e.complete()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', (final.get('error'), e.output[-3:]))
        self.assertEqual(statuses(e), [('CAPTURE', 'CAPTURE_COMPLETE_PENDING_CLOSE', None, None),
                                       ('PROCESS_GATE', 'CONTINUE', None, None),
                                       ('APPLY', 'CONTINUE', 'committed', 'IDLE'),
                                       ('UNDO', 'CONTINUE', 'undone', 'IDLE'),
                                       ('REDO', 'CONTINUE', 'redone', 'IDLE'),
                                       ('FINAL_UNDO', 'COMPLETE_PENDING_CLOSE', 'final', 'IDLE')])
        self.assertEqual(e.world_b.poison_hits, [])
        self.assertGreater(len(e.world_b.poisoned), 60)
        result = e.finalize()
        self.assertEqual(result['verdict'], 'PASS', result.get('reasons'))
        self.assertEqual(result['write_accounting'], {'aborted_test_writes': 1, 'committed_writes': 6,
                                                      'native_history_operations': ['Undo', 'Redo', 'Undo']})


    def test_retime_dependent_procedure(self):
        e = self.env(policy='retime')
        final = e.complete()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        steps = [s[0] for s in statuses(e)]
        self.assertEqual(steps, ['CAPTURE', 'PROCESS_GATE', 'APPLY', 'RETIME', 'UNDO', 'RETIME', 'REDO', 'RETIME',
                                 'FINAL_UNDO', 'RETIME'])
        result = e.finalize()
        self.assertEqual(result['verdict'], 'PASS', result.get('reasons'))
        self.assertEqual(set(result['propagation'].values()), set(['RETIMING_DEPENDENT']))
        self.assertIn('RETIMING_DEPENDENT', result['interpretation'])

    def test_goals_match_independent_expectation(self):
        e = self.env()
        e.complete()
        plan = dict((n[9:-5], r) for n, r in e.reports())['APPLY']['plan']
        want = expected_application(e.world_a, e.world_b)
        core = load_core()
        self.assertLess(core['distance'](plan['write_float32']['Hand_l_p'], want['Hand_l_p']), 1e-6)
        self.assertLess(core['distance'](plan['write_float32']['Elbow_l_p'], want['Elbow_l_p']), 1e-6)
        self.assertLess(core['angle_deg'](plan['write_float32']['Hand_l_o'], want['Hand_l_o']), 1e-4)
        self.assertGreater(core['distance'](plan['write_float32']['Hand_l_p'],
                                            e.world_b.shots['shot10'].spec['handles']['Hand_l']['position']), 1.0)

    def test_per_channel_bracket_indices_and_write_accounting(self):
        e = self.env()
        e.complete()
        apply_r = dict((n[9:-5], r) for n, r in e.reports())['APPLY']
        writes = [x for x in apply_r['events'] if x['event'] == 'commit'][0]['writes']
        self.assertEqual([(w['channel'], w['index'], w['ticks']) for w in writes],
                         [('Hand_l_p', 0, 30000), ('Hand_l_p', 1, 70415), ('Hand_l_o', 1, 30000),
                          ('Hand_l_o', 2, 70415), ('Elbow_l_p', 0, 30000), ('Elbow_l_p', 1, 70415)])
        self.assertEqual(e.world_b.dm.calls[0][0], 'StartUndo')
        self.assertEqual([c[0] for c in e.world_b.dm.calls],
                         ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo', 'Undo', 'Redo', 'Undo'])
        # Keys outside the brackets are untouched and no key was created.
        layer = e.layer(e.world_b, 'shot10', 'Hand_l_o')
        self.assertEqual([k[0] for k in layer.keys], [5000, 30000, 70415, 90000])
        self.assertEqual(layer.keys[0][1], [0.0, 0.0, 0.0, 1.0])

    def test_capture_is_read_only(self):
        e = self.env()
        e.start_a()
        before = json.dumps([[l.keys for l in c.log.layers] for S in e.world_a.shots.values() for c in S.channels])
        report = e.submit('capture')
        self.assertEqual(report['status'], 'CAPTURE_COMPLETE_PENDING_CLOSE', report.get('error'))
        self.assertEqual(e.world_a.dm.calls, [])
        after = json.dumps([[l.keys for l in c.log.layers] for S in e.world_a.shots.values() for c in S.channels])
        self.assertEqual(before, after)
        self.assertEqual(sorted(os.listdir(os.path.join(e.run_dir, 'poses'))), ['left_arm_pose.f01w2.json'])
        self.assertTrue(all(report['capture']['completion_gate'].values()))

    def test_capture_bytes_are_deterministic_golden(self):
        e = self.env()
        e.capture()
        with open(GOLDEN, 'rb') as f:
            golden = f.read()
        self.assertEqual(e.pose_bytes(), golden)
        self.assertEqual(hashlib.sha256(golden).hexdigest(),
                         '2edf828c3a1bcc5078415338764277fc83e34df93beaedea10d4080a4f81579a')

    def test_pose_file_has_no_runtime_identities(self):
        e = self.env()
        e.capture()
        text_ = e.pose_bytes().decode('ascii')
        pose = json.loads(text_)
        handles = set(e.world_a.by_handle)
        found = []

        def walk(v, path):
            if isinstance(v, dict):
                for k, x in v.items():
                    if k in ('handle', 'pid', 'process', 'undo', 'nonce', 'path'):
                        found.append(path + '/' + k)
                    walk(x, path + '/' + k)
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    walk(x, '%s/%d' % (path, i))
            elif isinstance(v, int) and not isinstance(v, bool) and v in handles:
                found.append(path)
        walk(pose, '')
        self.assertEqual(found, [])
        for forbidden in (e.dir, 'F01W1', '.dmx', str(A_PID)):
            self.assertNotIn(forbidden, text_)

    def test_pid_reuse_is_not_mistaken_for_the_same_process(self):
        e = self.env()
        cap = e.capture()
        self.assertEqual(cap['status'], 'CAPTURE_COMPLETE_PENDING_CLOSE')
        e.exit_a()
        e.gate()
        e.clock[0] += 1000
        e.table[A_PID] = {'creation_filetime': e.clock[0], 'running': True, 'image': 'C:\\SFM\\sfm.exe'}
        e.world_b = fake.World(e.config['apply_session'], handle_base=500000, poison_source=True)
        e.new_process(e.world_b, A_PID)
        e.world_b.set_frame(10)
        final = e.run_b()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        self.assertEqual(e.finalize()['verdict'], 'PASS')


# ---------------------------------------------------------------------------
# Pose format: strict parsing
# ---------------------------------------------------------------------------

def golden_bytes():
    with open(GOLDEN, 'rb') as f:
        return f.read()


def golden_value():
    return json.loads(golden_bytes().decode('ascii'))


def encode(value):
    return json.dumps(value, sort_keys=True).encode('ascii')


class TestPoseFormat(unittest.TestCase):
    def setUp(self):
        self.core = load_core()
        self.parse = self.core['parse_pose']
        self.error = self.core['PoseFormatError']

    def rejects(self, raw, why=None):
        with self.assertRaises(self.error) as ctx:
            self.parse(raw)
        if why:
            self.assertIn(why, str(ctx.exception))

    def mutated(self, fn, why=None):
        v = golden_value()
        fn(v)
        self.rejects(encode(v), why)

    def test_golden_accepted_and_reserializes_identically(self):
        pose = self.parse(golden_bytes())
        self.assertEqual(self.core['serialize_pose'](pose), golden_bytes())

    def test_committed_adversarial_fixtures(self):
        cases = {'duplicate_key.f01w2.json': 'Duplicate key', 'nan_literal.f01w2.json': 'Non-finite',
                 'infinity_overflow.f01w2.json': 'non-finite', 'bom.f01w2.json': 'Byte-order mark',
                 'invalid_utf8.f01w2.bin': 'UTF-8', 'truncated.f01w2.json': 'not valid JSON'}
        for name, why in sorted(cases.items()):
            with open(os.path.join(FIXTURES, 'adversarial', name), 'rb') as f:
                self.rejects(f.read(), why)

    def test_unknown_missing_and_type_errors(self):
        self.mutated(lambda v: v.__setitem__('extra', 1), 'unknown fields')
        self.mutated(lambda v: v['pose'].__setitem__('elbow_orientation', [0, 0, 0, 1]), 'unknown fields')
        self.mutated(lambda v: v.pop('skeleton'), 'missing fields')
        self.mutated(lambda v: v['pose']['hand'].pop('orientation'), 'missing fields')
        self.mutated(lambda v: v.__setitem__('version', 2), 'expected 1')
        self.mutated(lambda v: v.__setitem__('version', True), 'expected 1')
        self.mutated(lambda v: v.__setitem__('version', 1.0), 'expected 1')
        self.mutated(lambda v: v.__setitem__('format', 'F01W2-left-arm-pose-x'))
        self.mutated(lambda v: v['conventions'].__setitem__('units', 'meters'))
        self.mutated(lambda v: v['conventions'].__setitem__('quaternion_order', 'w,x,y,z'))
        self.mutated(lambda v: v['pose']['hand'].__setitem__('position', [1.0, 2.0]), 'expected 3 numbers')
        self.mutated(lambda v: v['pose']['hand'].__setitem__('position', [1.0, 2.0, '3']), 'expected a number')
        self.mutated(lambda v: v['pose']['hand'].__setitem__('position', [1.0, 2.0, True]), 'expected a number')
        self.mutated(lambda v: v['pose']['elbow'].__setitem__('position', [1.0, 2.0, 2e6]), 'exceeds')
        self.mutated(lambda v: v['compatibility']['arm_chain'][0].__setitem__('index', 1.5), 'integer')
        self.mutated(lambda v: v['compatibility']['arm_chain'].pop(), 'list of')
        self.mutated(lambda v: v['compatibility']['constraints']['ik']['solver'].__setitem__(
            'mode', {'present': True}), 'exactly present and value')
        self.mutated(lambda v: v['compatibility']['constraints']['ik']['solver'].__setitem__(
            'mode', {'present': True, 'value': {'handle': 5}}), 'unsupported typed value')
        self.mutated(lambda v: v['compatibility']['constraints']['ik']['solver'].__setitem__(
            'other', {'present': False}), 'unknown fields')

    def test_duplicate_arm_bone_rejected(self):
        def dup(v):
            v['compatibility']['arm_chain'][1] = dict(v['compatibility']['arm_chain'][0])
        self.mutated(dup, 'each bone once')

    def test_quaternion_norm_tolerance(self):
        tol = self.core['QUATERNION_UNIT_TOLERANCE']
        self.assertEqual(tol, 1e-4)

        def scaled(factor):
            def fn(v):
                v['pose']['hand']['orientation'] = [c * factor for c in v['pose']['hand']['orientation']]
            return fn
        v = golden_value()
        scaled(1.0 + 0.5e-4)(v)
        self.parse(encode(v))                               # inside tolerance: accepted, not normalized
        self.assertNotEqual(self.parse(encode(v))['pose']['hand']['orientation'],
                            golden_value()['pose']['hand']['orientation'])
        self.mutated(scaled(1.0 + 2e-4), 'quaternion norm')
        self.mutated(scaled(0.5), 'quaternion norm')
        self.mutated(lambda v: v['skeleton']['bones']['bip_hand_l'].__setitem__('collar_orientation', [0, 0, 0, 0]),
                     'quaternion norm')

    def test_size_and_input_type(self):
        self.rejects(golden_bytes() + b' ' * 65536, 'exceeds')
        self.rejects(golden_bytes().decode('ascii') if sys.version_info[0] > 2 else
                     golden_bytes().decode('ascii'), None)

    def test_parser_never_executes_content(self):
        source = open(os.path.join(HARNESS_DIR, 'f01w2_core.py')).read()
        body = source[source.index('def parse_pose('):source.index('def serialize_pose(')]
        for forbidden in ('eval(', 'exec(', 'pickle', 'marshal', 'yaml', '__import__'):
            self.assertNotIn(forbidden, body)


# ---------------------------------------------------------------------------
# Publication: create-only, interruption, evidence binding
# ---------------------------------------------------------------------------

class TestPublication(Base):
    def test_platform_rename_refuses_existing_target(self):
        d = tempfile.mkdtemp(prefix='f01w2_rename_')
        try:
            a, b = os.path.join(d, 'a'), os.path.join(d, 'b')
            for p in (a, b):
                with open(p, 'wb') as f:
                    f.write(p.encode('ascii'))
            core = load_core()
            self.assertRaises(OSError, core['no_replace_rename'], a, b)
            with open(b, 'rb') as f:
                self.assertEqual(f.read(), b.encode('ascii'))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_preexisting_pose_refuses_and_is_not_overwritten(self):
        e = self.env()
        with open(e.config['pose_path'], 'wb') as f:
            f.write(b'someone else')
        report = e.capture()
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('already exists', report['error'])
        self.assertEqual(e.pose_bytes(), b'someone else')
        self.assertNotIn('publication', report)

    def test_interrupted_before_rename_leaves_no_pose(self):
        e = self.env()
        core_copy = os.path.join(e.hdir, 'f01w2_core.py')
        with open(core_copy, 'rb') as f:
            src = f.read().decode('ascii')
        src = src.replace("    try:\n        no_replace_rename(temp, final_path)",
                          "    raise Stop('simulated crash before publication')\n    try:\n"
                          "        no_replace_rename(temp, final_path)")
        with open(core_copy, 'wb') as f:
            f.write(src.encode('ascii'))
        report = e.capture()
        self.assertEqual(report['status'], 'STOP')
        listing = os.listdir(os.path.join(e.run_dir, 'poses'))
        self.assertEqual(len(listing), 1)
        self.assertTrue(listing[0].startswith('INCOMPLETE-') and listing[0].endswith('.f01w2-capture.tmp'))
        self.assertFalse(os.path.exists(e.config['pose_path']))
        e.exit_a()
        self.assertRaises(SystemExit, e.gate)

    def test_interrupted_after_rename_without_record_refuses(self):
        e = self.env()
        e.capture()
        report_path = os.path.join(e.config['reports_dir'], 'F01W2-01-CAPTURE.json')
        open(report_path, 'wb').close()                     # the success record never got written
        e.exit_a()
        self.assertRaises(SystemExit, e.gate)
        e.start_b()
        self.assertIsNone(quiet_submit(e))
        self.assertEqual(e.world_b.dm.calls, [])

    def test_pose_changed_before_gate_refuses(self):
        e = self.env()
        e.capture()
        e.exit_a()
        with open(e.config['pose_path'], 'ab') as f:
            f.write(b' ')
        self.assertRaises(SystemExit, e.gate)

    def test_pose_changed_after_gate_refuses_application(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        v = json.loads(e.pose_bytes().decode('ascii'))
        v['pose']['hand']['position'][0] += 0.5
        with open(e.config['pose_path'], 'wb') as f:
            f.write(e.world_a and load_core()['serialize_pose'](v))
        e.start_b()
        report = e.submit('apply')
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('do not match the capture record', report['error'])
        self.assertEqual(e.world_b.dm.calls, [])

    def test_capture_record_hash_binding_cannot_be_forged_without_breaking_the_chain(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        path = os.path.join(e.config['reports_dir'], 'F01W2-01-CAPTURE.json')
        with open(path, 'rb') as f:
            r = json.loads(f.read().decode('ascii'))
        r['publication']['pose_sha256'] = '0' * 64
        with open(path, 'wb') as f:
            f.write(json.dumps(r).encode('ascii'))
        e.start_b()
        self.assertIsNone(quiet_submit(e))
        self.assertEqual(e.world_b.dm.calls, [])

    def test_snapshot_read_exactly_once(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        target = os.path.normcase(os.path.abspath(e.config['pose_path']))
        opened = []
        builtins_mod = sys.modules['builtins' if sys.version_info[0] > 2 else '__builtin__']
        real_open = builtins_mod.open

        def spy(name, *a, **k):
            if isinstance(name, (str, type(u''))) and os.path.normcase(os.path.abspath(name)) == target:
                opened.append(name)
            return real_open(name, *a, **k)
        builtins_mod.open = spy
        try:
            final = e.run_b()
        finally:
            builtins_mod.open = real_open
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        self.assertEqual(len(opened), 1)


def quiet_submit(env):
    """Submit APPLY_STEP where a refusal before reservation is expected: returns
    the new report or None when nothing was reserved."""
    before = len(env.reports())
    env.submit('apply')
    reports = env.reports()
    return reports[-1][1] if len(reports) > before else None


# ---------------------------------------------------------------------------
# Capture integrity
# ---------------------------------------------------------------------------

class TestCaptureIntegrity(Base):
    def capture_with_hook(self, fn, after=200):
        e = self.env()
        e.start_a()
        calls = []

        def hook(n):
            if n >= after and not calls:
                calls.append(n)
                fn(e)
                return True
            return False
        e.world_a.read_hook = hook
        report = e.submit('capture')
        self.assertTrue(calls, 'hook did not fire')
        return e, report

    def assert_not_published(self, e, report, why):
        self.assertEqual(report['status'], 'STOP', report.get('error'))
        self.assertIn(why, report['error'])
        self.assertFalse(os.path.exists(e.config['pose_path']))
        self.assertNotIn('publication', report)

    def reads_in_capture(self):
        e = self.env()
        e.start_a()
        e.submit('capture')
        return e.world_a.read_count

    def test_authored_change_during_capture(self):
        n = self.reads_in_capture()

        def change(e):
            layer = e.layer(e.world_a, 'shot15', 'Elbow_l_o')
            layer.keys[0][1] = [0.0, 0.0, 0.0, 1.0]
        e, report = self.capture_with_hook(change, after=n - 3)       # inside the completion re-read
        self.assert_not_published(e, report, 'Capture-integrity gate failed')

    def test_undo_history_change_during_capture(self):
        n = self.reads_in_capture()
        e, report = self.capture_with_hook(lambda e: e.world_a.dm.push_foreign('user edit'), after=n - 3)
        self.assert_not_published(e, report, "['undo_history']")

    def test_evaluated_change_during_capture(self):
        n = self.reads_in_capture()

        def change(e):
            S = e.world_a.shots['shot15']
            dag = S.bone_dags['bip_head']
            dag.world_xf = (fake.add(dag.world_xf[0], [0.0, 0.0, 1e-3]), dag.world_xf[1])
        e, report = self.capture_with_hook(change, after=n // 2 + 1)
        self.assert_not_published(e, report, 'skeleton')

    def test_protected_file_change_during_capture(self):
        n = self.reads_in_capture()

        def change(e):
            with open(e.config['original_session'], 'ab') as f:
                f.write(b'!')
        e, report = self.capture_with_hook(change, after=n - 3)
        self.assertEqual(report['status'], 'STOP')
        self.assertFalse(os.path.exists(e.config['pose_path']))

    def test_effective_log_disagreement(self):
        e = self.env()
        e.start_a()
        e.world_a.input_offset = ('shot15', 0.01)
        e.world_a.evaluate(e.world_a.shots['shot15'])
        report = e.submit('capture')
        self.assert_not_published(e, report, 'differs from its log')

    def test_wrong_document_place_and_frame(self):
        e = self.env()
        e.start_a()
        e.world_a.set_frame(10)
        report = e.submit('capture')
        self.assert_not_published(e, report, 'requires shot15')
        e2 = self.env()
        e2.world_a = fake.World(e2.config['apply_session'], handle_base=100000)
        e2.new_process(e2.world_a, A_PID)
        e2.world_a.set_frame(5)
        report = e2.submit('capture')
        self.assert_not_published(e2, report, 'capture_session')

    def test_capture_entry_refuses_a_second_capture(self):
        e = self.env()
        e.capture()
        before = len(e.reports())
        e.submit('capture')
        self.assertEqual(len(e.reports()), before)
        self.assertIn('REFUSED', e.output[-1])


# ---------------------------------------------------------------------------
# Process separation and the gate
# ---------------------------------------------------------------------------

class TestProcessSeparation(Base):
    def test_gate_refuses_while_process_a_runs(self):
        e = self.env()
        e.capture()
        self.assertRaises(SystemExit, e.gate)               # A never exited

    def test_gate_refuses_while_renamed_process_a_runs(self):
        """Process A identified by pid and creation time, not by image name."""
        e = self.env()
        e.capture()
        e.table[A_PID]['image'] = 'C:\\SFM\\renamed_editor.exe'
        with self.assertRaises(SystemExit) as ctx:
            e.gate()
        self.assertIn('process A', str(ctx.exception))

    def test_gate_refuses_while_any_sfm_runs(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.table[7777] = {'creation_filetime': 5, 'running': True, 'image': 'D:\\other\\SFM.EXE'}
        self.assertRaises(SystemExit, e.gate)

    def test_gate_refuses_saved_capture_copy(self):
        e = self.env()
        e.capture()
        e.exit_a()
        with open(e.config['capture_session'], 'ab') as f:
            f.write(b'saved')
        self.assertRaises(SystemExit, e.gate)

    def test_gate_runs_once(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        self.assertRaises(SystemExit, e.gate)

    def test_apply_refuses_without_gate(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.start_b()
        self.assertIsNone(quiet_submit(e))
        self.assertIn('due step is PROCESS_GATE', e.output[-1])

    def test_apply_in_process_a_refuses(self):
        e = self.env()
        e.capture()
        e.gate_provider = None
        e.table[A_PID]['running'] = False
        e.gate()
        e.table[A_PID]['running'] = True                    # A is in fact still alive: same process continues
        e.world = e.world_a
        sys.modules['f01w2_runtime'].process_provider = fake.FakeProcesses(e.table, A_PID, e.clock) \
            if 'f01w2_runtime' in sys.modules else None
        e.new_process(e.world_a, A_PID)
        e.world_a.set_frame(10)
        report = e.submit('apply')
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('Process separation not established', report['error'])
        self.assertEqual(e.world_a.dm.calls, [])

    def test_b_created_before_gate_refuses(self):
        e = self.env()
        e.capture()
        e.exit_a()
        # A renamed SFM executable started before the gate: invisible to the
        # gate's image check, refused by its creation time.
        e.table[B_PID] = {'creation_filetime': e.clock[0] + 1, 'running': True, 'image': 'C:\\SFM\\sfm_copy.exe'}
        e.clock[0] += 5
        e.gate()
        e.world_b = fake.World(e.config['apply_session'], handle_base=500000, poison_source=True)
        e.new_process(e.world_b, B_PID)
        e.world_b.set_frame(10)
        report = e.submit('apply')
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('b_created_after_gate', report['error'])

    def test_later_steps_must_stay_in_process_b(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        report = e.submit('apply')
        self.assertEqual(report['status'], 'CONTINUE')
        e.table[B_PID]['running'] = False
        e.start_b(pid=8000)                                 # a third process tries to continue
        report = e.submit('apply')
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('different process', report['error'])


# ---------------------------------------------------------------------------
# Destination preflight: compatibility, writers, brackets, bindings
# ---------------------------------------------------------------------------

def modified_scene(fn):
    scene = fake.load_scene()
    fn(scene)
    return scene


class TestPreflight(Base):
    def apply_with(self, mutate_world=None, scene=None):
        e = self.env()
        cap = e.capture()
        self.assertEqual(cap['status'], 'CAPTURE_COMPLETE_PENDING_CLOSE')
        e.exit_a()
        e.gate()
        kw = {'scene': scene} if scene is not None else {}
        e.start_b(**kw)
        if mutate_world is not None:
            mutate_world(e.world_b)
            e.world_b.evaluate(e.world_b.shots['shot10'])
        report = e.submit('apply')
        return e, report

    def refused(self, why, mutate_world=None, scene=None):
        e, report = self.apply_with(mutate_world, scene)
        self.assertEqual(report['status'], 'STOP', report.get('error'))
        self.assertIn(why, report['error'])
        self.assertEqual(e.world_b.dm.calls, [], 'mutation attempted after a preflight refusal')
        self.assertEqual(e.world_b.poison_hits, [])
        return e, report

    def test_bone_index_differs(self):
        def fn(s):
            for b in s['bones']:
                if b['name'] == 'bip_lowerArm_l':
                    b['index'] = 15
        self.refused('not compatible', scene=modified_scene(fn))

    def test_arm_bone_offset_differs(self):
        def fn(s):
            for b in s['bones']:
                if b['name'] == 'bip_hand_l':
                    b['local_position'] = [10.001, 0.0, 0.0]
        self.refused('local offsets differ', scene=modified_scene(fn))

    def test_arm_bone_offset_within_bound_is_accepted(self):
        def fn(s):
            for b in s['bones']:
                if b['name'] == 'bip_hand_l':
                    b['local_position'] = [10.00005, 0.0, 0.0]
        e, report = self.apply_with(scene=modified_scene(fn))
        self.assertEqual(report['status'], 'CONTINUE', report.get('error'))

    def test_pole_target_identity(self):
        def fn(w):
            S = w.shots['shot10']
            S.ops[0].set('pvTarget', S.handles['spine_4'])
        self.refused('pole target', fn)

    def test_name_alone_is_not_identity(self):
        def fn(w):
            S = w.shots['shot10']
            impostor = fake.Dag(w, 'DmeRigHandle', 'Elbow_l', transform=fake.El(w, 'DmeTransform', 'Elbow_l',
                                                                                  position=fake.Vector(),
                                                                                  orientation=fake.Quaternion()))
            S.ops[0].set('pvTarget', impostor)
        self.refused('pole target', fn)

    def test_ik_joint_identity(self):
        def fn(w):
            S = w.shots['shot10']
            S.ops[0].get('midJoint').set('target', S.bone_dags['bip_finger_l'])
        self.refused('IK midJoint', fn)

    def test_constraint_weight(self):
        def fn(w):
            S = w.shots['shot10']
            S.ops[1].get('targets')[0].set('targetWeight', 0.5)
        self.refused('weight 1.0', fn)

    def test_constraint_extra_target(self):
        def fn(w):
            S = w.shots['shot10']
            t = fake.El(w, 'DmeConstraintTarget', 'extra', target=S.handles['spine_4'], targetWeight=1.0,
                        oOffset=fake.Quaternion(), vecOffset=fake.Vector())
            S.ops[2].set('targets', [S.ops[2].get('targets')[0], t])
        self.refused('one target', fn)

    def test_solver_field_differs(self):
        self.refused('not compatible', lambda w: w.shots['shot10'].ops[0].set('mode', 1))

    def test_solver_field_absent(self):
        def fn(w):
            op = w.shots['shot10'].ops[0]
            del op.attrs['poleVector']
            op.order.remove('poleVector')
        self.refused('not compatible', fn)

    def test_target_offset_differs(self):
        self.refused('not compatible',
                     lambda w: w.shots['shot10'].ops[3].get('targets')[0].set('oOffset', fake.Quaternion(0.0, 0.0,
                                                                                                         0.0871557,
                                                                                                         0.9961947)))

    def test_hand_handle_parentage(self):
        def fn(w):
            S = w.shots['shot10']
            S.handles['rig_root'].attrs['children'].value.items.remove(S.handles['Hand_l'])
            S.handles['spine_4'].add_child(S.handles['Hand_l'])
        self.refused('parented to rig_root', fn)

    def test_unsupported_scale(self):
        self.refused('Unsupported scale', lambda w: w.shots['shot10'].bone_transforms['bip_lowerArm_l'].set(
            'scale', 1.5))

    def test_model_mismatch(self):
        self.refused('Unexpected model', lambda w: w.shots['shot10'].gm.set('modelName', 'models/other.mdl'))

    def test_channel_mode(self):
        self.refused('Play mode', lambda w: w.channel('shot10', 'Elbow_l_p').set('mode', 0))

    def test_observed_channel_binding_change(self):
        def fn(w):
            S = w.shots['shot10']
            w.channel('shot10', 'Elbow_l_o').set('toElement', S.handles['spine_4'].get('transform'))
        self.refused('Elbow_l_o binding', fn)

    def test_layer_curve_info(self):
        self.refused('curve info', lambda w: w.channel('shot10', 'Hand_l_p').log.layers[0].set('curveinfo',
                                                                                                fake.El(w, 'DmeCurveInfo', 'c')))

    def test_bracket_key_missing(self):
        self.refused('Bracket key at 70415', lambda w: w.channel('shot10', 'Hand_l_o').log.layers[0].keys.pop(2))

    def test_bracket_key_duplicated(self):
        def fn(w):
            keys = w.channel('shot10', 'Elbow_l_p').log.layers[0].keys
            keys.insert(1, [30000, list(keys[0][1])])
        self.refused('duplicated', fn)

    def test_intervening_key(self):
        def fn(w):
            keys = w.channel('shot10', 'Hand_l_p').log.layers[0].keys
            keys.insert(1, [50000, list(keys[0][1])])
        self.refused('intervene', fn)

    def test_competing_writer_in_another_shot(self):
        def fn(w):
            target = w.shots['shot10'].handles['Hand_l'].get('transform')
            w.add_channel('shot15', 'rogue', target, 'position', mode=0)
        self.refused('unique writer', fn)

    def test_constraint_driving_rig_handle(self):
        def fn(w):
            S = w.shots['shot15']
            op = fake.El(w, 'DmeRigPointConstraintOperator', 'rogue',
                         slave=fake.El(w, 'DmeConstraintSlave', 'slave', target=w.shots['shot10'].handles['Elbow_l']))
            S.animset.attrs['operators'].value.items.append(op)
        self.refused('drives rig handle Elbow_l', fn)

    def test_channel_writing_control(self):
        def fn(w):
            w.add_channel('shot10', 'rogue', w.shots['shot10'].controls[0], 'valuePosition')
        self.refused('writes control', fn)

    def test_shared_log(self):
        def fn(w):
            S = w.shots['shot15']
            ch = w.channel('shot15', 'spine_4_p')
            ch.log = w.channel('shot10', 'Hand_l_p').log
        self.refused('log is shared', fn)

    def test_unknown_operator_type(self):
        def fn(w):
            S = w.shots['shot15']
            S.animset.attrs['operators'].value.items.append(fake.El(w, 'DmeMysteryOperator', 'x'))
        self.refused('Unsupported operator', fn)

    def test_shoulder_guard(self):
        """In the fake the collar bone coincides with CollarL, so an origin
        mismatch is caught first by the arm-offset comparison; the guard is
        exercised directly on a saved origin that misses the live upper arm."""
        e, report = self.apply_with()
        self.assertEqual(report['status'], 'CONTINUE')
        core = load_core()
        tol = e.config['tolerances']
        pose = report['pose_snapshot']['payload']
        dst = report['destination_baseline']['skeleton']
        self.assertLess(core['shoulder_guard'](pose, dst, tol), 1e-9)
        moved = json.loads(json.dumps(pose))
        moved['skeleton']['upper_arm_origin'][1] += 0.002
        with self.assertRaises(core['Stop']) as ctx:
            core['shoulder_guard'](moved, dst, tol)
        self.assertIn('upper arm', str(ctx.exception))

    def test_unreadable_required_relationship(self):
        def fn(w):
            w.unreadable.add((w.shots['shot10'].ops[0].h, 'pvTarget'))
        e, report = self.apply_with(fn)
        self.assertEqual(report['status'], 'INCONCLUSIVE')
        self.assertEqual(e.world_b.dm.calls, [])


# ---------------------------------------------------------------------------
# Source independence
# ---------------------------------------------------------------------------

class TestSourceIndependence(Base):
    def test_poison_detector_catches_indirect_source_access(self):
        """A sabotaged application copy that reads the source arm through a
        shared helper is caught before any write."""
        e = self.env()
        apply_copy = os.path.join(e.hdir, 'f01w2_apply.py')
        with open(apply_copy, 'rb') as f:
            src = f.read().decode('ascii')
        sabotage = ("    plan = build_plan(config, pose, L, skel, targets, reference)\n"
                    "    movie = sfmApp.GetMovie()\n"
                    "    for shot in C['sequence'](C['attr'](C['attr'](movie, 'subClipTrackGroup'), 'tracks')[0]"
                    ".GetAttribute('children').GetValue()):\n"
                    "        if C['text'](shot.GetName()) == 'shot15':\n"
                    "            for a in C['sequence'](C['attr'](shot, 'animationSets')):\n"
                    "                for c in C['sequence'](C['attr'](a, 'controls')):\n"
                    "                    C['field'](c, 'valuePosition') and C['attr'](c, 'valuePosition')\n")
        src = src.replace("    plan = build_plan(config, pose, L, skel, targets, reference)\n", sabotage)
        self.assertIn('shot15', src)
        with open(apply_copy, 'wb') as f:
            f.write(src.encode('ascii'))
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        report = e.submit('apply')
        self.assertIn(report['status'], ('STOP', 'INCONCLUSIVE'))      # the poisoned read is unreadable evidence
        self.assertIn('source-pose read in process B', report['error'])
        self.assertTrue(e.world_b.poison_hits)
        self.assertEqual(e.world_b.dm.calls, [])

    def test_writer_inventory_reads_only_metadata(self):
        e = self.env()
        e.start_b(poison=True)
        core = load_core()
        index = core['writer_index'](sys.modules['sfmApp'])
        self.assertEqual(index['channels'], 18)                          # both shots, every channel
        self.assertEqual(e.world_b.poison_hits, [])

    def test_application_never_reads_captured_payload_from_the_ledger(self):
        with open(os.path.join(HARNESS_DIR, 'f01w2_apply.py')) as f:
            src = f.read()
        self.assertNotIn("['capture']", src)
        self.assertNotIn(".get('capture')", src)
        self.assertNotIn('resolve_other', src)
        self.assertNotIn("'source'", src)
        with open(os.path.join(HARNESS_DIR, 'f01w2_core.py')) as f:
            self.assertNotIn('def resolve_other', f.read())

    def test_application_succeeds_with_source_values_destroyed(self):
        """Process B's copy has every source-pose value replaced: the plan
        and result are unchanged, so nothing in them came from the source shot."""
        e = self.env()
        e.complete()
        plan_a = dict((n[9:-5], r) for n, r in e.reports())['APPLY']['plan']['write_float32']
        e2 = self.env()
        e2.capture()
        e2.exit_a()
        e2.gate()
        world = e2.start_b()
        S = world.shots['shot15']
        for ch in S.channels:
            for layer in ch.log.layers:
                for k in layer.keys:
                    k[1] = [0.5, 0.5, 0.5, 0.5] if isinstance(k[1], list) and len(k[1]) == 4 else (
                        [99.0, 99.0, 99.0] if isinstance(k[1], list) else 9.0)
        final = e2.run_b()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        plan_b = dict((n[9:-5], r) for n, r in e2.reports())['APPLY']['plan']['write_float32']
        self.assertEqual(plan_a, plan_b)


# ---------------------------------------------------------------------------
# Independent plan implementations
# ---------------------------------------------------------------------------

class TestIndependentPlans(Base):
    def test_matrix_path_calls_no_quaternion_helper(self):
        import ast
        with open(os.path.join(HARNESS_DIR, 'f01w2_core.py')) as f:
            tree = ast.parse(f.read())
        funcs = dict((n.name, n) for n in tree.body if isinstance(n, ast.FunctionDef))
        forbidden = set(['unit', 'qmul', 'qconj', 'qrot', 'compose', 'invert', 'distance', 'angle_deg', 'f32',
                         'plan_quaternion', 'world'])
        for name in [n for n in funcs if n.startswith('mb_')] + ['plan_matrix']:
            called = set(c.func.id for c in ast.walk(funcs[name]) if isinstance(c, ast.Call)
                         and isinstance(c.func, ast.Name))
            self.assertEqual(called & forbidden, set(), name)

    def test_disagreement_refuses_before_mutation(self):
        e = self.env()
        core_copy = os.path.join(e.hdir, 'f01w2_core.py')
        with open(core_copy, 'rb') as f:
            src = f.read().decode('ascii')
        src = src.replace("    return {'Hand_l_p': [mb_f32(x) for x in H_local[0]],",
                          "    H_local = ([H_local[0][0] + 0.0002] + H_local[0][1:], H_local[1])\n"
                          "    return {'Hand_l_p': [mb_f32(x) for x in H_local[0]],")
        with open(core_copy, 'wb') as f:
            f.write(src.encode('ascii'))
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        report = e.submit('apply')
        self.assertEqual(report['status'], 'STOP')
        self.assertIn('disagree', report['error'])
        self.assertEqual(e.world_b.dm.calls, [])

    def test_cross_check_is_sign_invariant_but_requires_one_hemisphere(self):
        core = load_core()
        tol = json.loads(open(TEMPLATE).read())['tolerances']
        a = {'Hand_l_p': [1.0, 2.0, 3.0], 'Elbow_l_p': [0.0, 0.0, 0.0], 'Hand_l_o': [0.0, 0.0, 0.0, 1.0]}
        b = dict(a)
        b['Hand_l_o'] = [0.0, 0.0, 0.0, -1.0]
        checks = core['cross_check'](a, b, tol)
        self.assertLess(checks['hand_orientation_degrees'], 1e-9)
        self.assertFalse(checks['agree'])                      # two plans may not write opposite signs

    def test_hemisphere_follows_the_replaced_key(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        world = e.start_b()
        layer = e.layer(world, 'shot10', 'Hand_l_o')
        for k in layer.keys:
            if k[0] in (30000, 70415):
                k[1] = [-c for c in k[1]]                       # same rotation, other hemisphere
        world.evaluate(world.shots['shot10'])
        final = e.run_b()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        plan = dict((n[9:-5], r) for n, r in e.reports())['APPLY']['plan']
        ref = plan['hand_orientation_sign']['reference']
        self.assertGreater(sum(plan['write_float32']['Hand_l_o'][i] * ref[i] for i in range(4)), 0.0)
        writes = [w for w in [x for x in dict((n[9:-5], r) for n, r in e.reports())['APPLY']['events']
                              if x['event'] == 'commit'][0]['writes'] if w['channel'] == 'Hand_l_o']
        self.assertEqual(writes[0]['readback'], writes[1]['readback'])
        self.assertEqual(e.finalize()['verdict'], 'PASS')


# ---------------------------------------------------------------------------
# Transactions, ownership and recovery
# ---------------------------------------------------------------------------

class TestTransactions(Base):
    def run_with(self, hooks=None, prepare=None, policy='idle'):
        e = self.env(policy)
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        if prepare is not None:
            prepare(e)
        final = e.run_b(hooks)
        return e, final

    def test_abort_check_write_raises(self):
        def prep(e):
            e.world_b.raise_on_write = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('abort-check write raised', final['error'])
        ev = [x for x in final['events'] if x['event'] == 'abort-check'][0]
        self.assertTrue(ev['authored_restored'])

    def test_abort_raises_is_recovery_unverified(self):
        def prep(e):
            e.world_b.abort_raises = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('recovery unverified', final['error'])

    def test_abort_does_not_restore(self):
        def prep(e):
            e.world_b.abort_broken = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('did not restore', final['error'])
        self.assertNotIn('FinishUndo', [c[0] for c in e.world_b.dm.calls])

    def test_unreadable_after_abort_is_stop(self):
        def prep(e):
            layer = e.layer(e.world_b, 'shot10', 'Hand_l_p')
            e.world_b.unreadable_on_abort = set([(e.world_b.channel('shot10', 'Hand_l_p').h, 'mode')])
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Recovery unverified', final['error'])

    def test_commit_failure_midway_aborts_and_verifies(self):
        def prep(e):
            calls = [0]
            real = e.world_b.set_key

            def flaky(layer, index, value):
                calls[0] += 1
                if calls[0] == 4:                               # abort-check write + three commit writes
                    raise RuntimeError('native write failed (test)')
                return real(layer, index, value)
            e.world_b.set_key = flaky
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        aborted = [x for x in final['events'] if x['event'] == 'commit-aborted'][0]
        self.assertTrue(aborted['authored_restored'])
        self.assertEqual(len(aborted['writes']), 2)
        self.assertEqual([c[0] for c in e.world_b.dm.calls],
                         ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'AbortUndoableOperation'])

    def test_commit_readback_mismatch(self):
        def prep(e):
            e.world_b.perturb_layer = e.layer(e.world_b, 'shot10', 'Elbow_l_p').h
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('readback mismatch', final['error'])

    def test_commit_failure_with_unreadable_recovery(self):
        def prep(e):
            e.world_b.perturb_layer = e.layer(e.world_b, 'shot10', 'Elbow_l_p').h
            e.world_b.unreadable_on_abort = set([(e.world_b.channel('shot10', 'Hand_l_p').h, 'mode')])
            calls = [0]
            real = e.world_b.dm.AbortUndoableOperation

            def second_only():
                calls[0] += 1
                if calls[0] == 1:
                    saved = e.world_b.unreadable_on_abort
                    e.world_b.unreadable_on_abort = set()
                    try:
                        return real()
                    finally:
                        e.world_b.unreadable_on_abort = saved
                return real()
            e.world_b.dm.AbortUndoableOperation = second_only
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Recovery unverified', final['error'])

    def test_foreign_top_entry_before_undo(self):
        e, final = self.run_with(hooks={('UNDO', 'undone'): lambda e: e.world_b.dm.push_foreign('user edit')})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('ownership uncertain', final['error'])
        self.assertNotIn('Undo', [c[0] for c in e.world_b.dm.calls])

    def test_mangled_description_after_commit(self):
        def prep(e):
            e.world_b.mangle_undo_desc = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('ownership uncertain', final['error'])

    def test_redo_ownership(self):
        def foreign_redo(e):
            e.world_b.dm.redo.append({'undo': 'x', 'redo': 'user redo', 'items': []})
        e, final = self.run_with(hooks={('REDO', 'redone'): foreign_redo})
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('ownership uncertain', final['error'])
        self.assertNotIn('Redo', [c[0] for c in e.world_b.dm.calls])

    def test_undo_without_exact_restoration(self):
        def prep(e):
            e.world_b.undo_broken = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('exact expected authored state', final['error'])

    def test_unreadable_after_undo_is_stop(self):
        def prep(e):
            e.world_b.unreadable_on_undo = set([(e.world_b.channel('shot10', 'Hand_l_p').h, 'mode')])
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Recovery unverified', final['error'])

    def test_writes_ignored_is_detected(self):
        def prep(e):
            e.world_b.ignore_writes = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('did not take effect', final['error'])

    def test_oracle_disagreement_never_waived(self):
        def prep(e):
            e.world_b.oracle_disagreement = True
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'FAIL')
        obs = dict((n[9:-5], r) for n, r in e.reports())['APPLY']['observation']
        self.assertEqual(obs['state'], 'ORACLE_DISAGREEMENT')
        self.assertEqual(e.finalize()['verdict'], 'FAIL')

    def test_unrelated_bone_change_fails(self):
        def prep(e):
            e.world_b.shift_unrelated_bone = 'bip_head'
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'FAIL')

    def test_context_change_before_commit(self):
        def prep(e):
            calls = [0]
            real = e.world_b.dm.AbortUndoableOperation

            def then_move():
                real()
                e.world_b.head = fake.FRAME_TICKS[11]
            e.world_b.dm.AbortUndoableOperation = then_move
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertNotIn('FinishUndo', [c[0] for c in e.world_b.dm.calls])

    def test_undo_disabled(self):
        def prep(e):
            e.world_b.dm.enabled = False
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Undo is not enabled', final['error'])
        self.assertEqual(e.world_b.dm.calls, [])


# ---------------------------------------------------------------------------
# Finalizer: tampering, contradiction, incompleteness
# ---------------------------------------------------------------------------

class TestFinalizer(Base):
    def complete(self, policy='idle'):
        e = self.env(policy)
        final = e.complete()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        ns = load(FINALIZE)
        entries = ns['ledger'](e.config['reports_dir'])
        return e, ns, entries

    def verdict(self, e, ns, entries, offline=True, pose=None):
        return ns['verdict'](entries, True, True, e.config, e.pose_bytes() if pose is None else pose, offline)

    def by_step(self, entries, step, stage=None):
        return [x for x in entries if x['report']['step'] == step and x['report'].get('stage') == stage][0]['report']

    def mutated(self, e, ns, entries, fn, expect='INCONCLUSIVE'):
        copy = json.loads(json.dumps(entries))
        fn(copy)
        verdict, reasons, _ = self.verdict(e, ns, copy)
        self.assertEqual(verdict, expect, reasons)
        return reasons

    def test_complete_ledger_passes(self):
        e, ns, entries = self.complete()
        self.assertEqual(self.verdict(e, ns, entries)[0], 'PASS')

    def test_native_provider_required_without_offline_flag(self):
        e, ns, entries = self.complete()
        verdict, reasons, _ = self.verdict(e, ns, entries, offline=False)
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertIn('native kernel32 provider', ' '.join(reasons))

    def test_finalizer_chain_tamper(self):
        e, ns, entries = self.complete()
        path = os.path.join(e.config['reports_dir'], 'F01W2-03-APPLY.json')
        with open(path, 'rb') as f:
            raw = f.read()
        with open(path, 'wb') as f:
            f.write(raw.replace(b'"IDLE"', b'"IDLE" '))
        result = e.finalize()
        self.assertEqual(result['verdict'], 'STOP')

    def test_pose_file_changed_after_run(self):
        e, ns, entries = self.complete()
        verdict, reasons, _ = self.verdict(e, ns, entries, pose=e.pose_bytes() + b' ')
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertIn('not the recorded bytes', ' '.join(reasons))

    def test_write_accounting_tampering(self):
        e, ns, entries = self.complete()

        def commit(es):
            return [x for x in self.by_step(es, 'APPLY', 'committed')['events'] if x['event'] == 'commit'][0]

        def drop_one(es):
            commit(es)['writes'].pop()
        self.mutated(e, ns, entries, drop_one)

        def duplicate_abort(es):
            r = self.by_step(es, 'APPLY', 'committed')
            r['events'].append([x for x in r['events'] if x['event'] == 'abort-check'][0])
        self.mutated(e, ns, entries, duplicate_abort)

        def abort_on_wrong_channel(es):
            r = self.by_step(es, 'APPLY', 'committed')
            [x for x in r['events'] if x['event'] == 'abort-check'][0]['write']['channel'] = 'Elbow_l_p'
        self.mutated(e, ns, entries, abort_on_wrong_channel)

        def readback_differs(es):
            commit(es)['writes'][3]['readback'] = [0.0, 0.0, 0.0, 1.0]
        self.mutated(e, ns, entries, readback_differs)

        def swapped_indices(es):
            w = [x for x in commit(es)['writes'] if x['channel'] == 'Hand_l_o']
            w[0]['index'], w[1]['index'] = w[1]['index'], w[0]['index']
        self.mutated(e, ns, entries, swapped_indices)

        def summary_flags_only(es):
            for w in commit(es)['writes']:
                w['requested_float32'] = [0.0]
        self.mutated(e, ns, entries, summary_flags_only)

        def aborted_commit(es):
            self.by_step(es, 'APPLY', 'committed')['events'].append({'event': 'commit-aborted'})
        self.mutated(e, ns, entries, aborted_commit)

    def test_plan_tampering_detected_independently(self):
        e, ns, entries = self.complete()

        def shifted_goal(es):
            r = self.by_step(es, 'APPLY', 'committed')
            r['plan']['write_float32']['Hand_l_p'][0] += 0.01
            for x in r['events']:
                for w in (x.get('writes') or []) + ([x['write']] if x.get('write') else []):
                    if w.get('channel') == 'Hand_l_p':
                        w['requested_float32'] = w['readback'] = r['plan']['write_float32']['Hand_l_p']
        reasons = self.mutated(e, ns, entries, shifted_goal)
        self.assertIn("independent plan", ' '.join(reasons))

        def oracle_rewritten(es):
            r = self.by_step(es, 'APPLY', 'committed')
            r['plan']['oracle']['primary_local']['bip_hand_l'] = [0.0, 0.0, 0.0, 1.0]
        self.mutated(e, ns, entries, oracle_rewritten)

        def cross_check_flag(es):
            self.by_step(es, 'APPLY', 'committed')['plan']['cross_check']['agree'] = False
        self.mutated(e, ns, entries, cross_check_flag)

        def snapshot_payload(es):
            self.by_step(es, 'APPLY', 'committed')['pose_snapshot']['payload']['pose']['elbow']['position'][0] += 1
        self.mutated(e, ns, entries, snapshot_payload)

        def capture_payload(es):
            self.by_step(es, 'CAPTURE')['capture']['payload']['diagnostics']['hand_target_residual'] += 1
        self.mutated(e, ns, entries, capture_payload)

    def test_process_tampering(self):
        e, ns, entries = self.complete()

        def same_process(es):
            a = self.by_step(es, 'CAPTURE')['process']
            for x in es[2:]:
                x['report']['process'] = dict(a)
        self.mutated(e, ns, entries, same_process)

        def b_before_gate(es):
            g = self.by_step(es, 'PROCESS_GATE')['gate']
            for x in es[2:]:
                x['report']['process']['creation_filetime'] = g['checked_filetime'] - 1
        self.mutated(e, ns, entries, b_before_gate)

        def gate_saw_a(es):
            self.by_step(es, 'PROCESS_GATE')['gate']['process_a_running'] = True
        self.mutated(e, ns, entries, gate_saw_a)

        def second_b(es):
            es[-1]['report']['process']['pid'] = 9999
        self.mutated(e, ns, entries, second_b)

        def separation_checks(es):
            self.by_step(es, 'APPLY', 'committed')['process_separation'].pop('a_not_running_now')
        self.mutated(e, ns, entries, separation_checks)

    def test_grammar_and_status(self):
        e, ns, entries = self.complete()
        self.mutated(e, ns, entries, lambda es: es.pop(4))
        self.mutated(e, ns, entries, lambda es: es.append(json.loads(json.dumps(es[-1]))))
        self.mutated(e, ns, entries, lambda es: es[3]['report'].__setitem__('status', 'COMPLETE_PENDING_CLOSE'))
        self.mutated(e, ns, entries, lambda es: es[1]['report'].__setitem__('evidence_complete', False))
        self.mutated(e, ns, entries, lambda es: es[2]['report'].__setitem__('observed_changes', ['/x']))

        def history_ownership(es):
            r = self.by_step(es, 'REDO', 'redone')
            [x for x in r['events'] if x['event'] == 'redo'][0]['undo_before']['redo_desc'] = 'user'
        self.mutated(e, ns, entries, history_ownership)

        def observation_flag_only(es):
            r = self.by_step(es, 'UNDO', 'undone')
            r['observation']['unrelated_changes'] = ['bone x']
        self.mutated(e, ns, entries, observation_flag_only)

    def test_status_alone_is_not_evidence(self):
        e, ns, entries = self.complete()
        stripped = json.loads(json.dumps(entries))
        for x in stripped:
            for key in ('observation', 'events', 'evidence_complete', 'plan', 'process', 'gate', 'publication',
                        'capture', 'pose_snapshot', 'process_separation'):
                x['report'].pop(key, None)
        verdict, reasons, _ = self.verdict(e, ns, stripped)
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertGreater(len(reasons), 10)

    def test_stop_and_protected_precedence(self):
        e, ns, entries = self.complete()
        self.assertEqual(ns['verdict'](entries, False, True, e.config, e.pose_bytes(), True)[0], 'STOP')
        self.assertEqual(ns['verdict'](entries, True, False, e.config, e.pose_bytes(), True)[0], 'STOP')
        copy = json.loads(json.dumps(entries))
        copy[3]['report']['status'] = 'FAIL'
        self.assertEqual(self.verdict(e, ns, copy)[0], 'FAIL')

    def test_saved_disposable_copy_is_stop(self):
        e, ns, entries = self.complete()
        with open(e.config['apply_session'], 'ab') as f:
            f.write(b'saved')
        self.assertEqual(e.finalize()['verdict'], 'STOP')

    def test_finalizer_is_independent_of_harness_code(self):
        with open(FINALIZE) as f:
            src = f.read()
        for forbidden in ('exec(', 'compile(open', 'import f01w2', '__import__', 'import fake', 'imp.load'):
            self.assertNotIn(forbidden, src)


# ---------------------------------------------------------------------------
# Run preparation
# ---------------------------------------------------------------------------

class TestPrepare(Base):
    def package(self):
        d = tempfile.mkdtemp(prefix='f01w2_pkg_')
        self.addCleanup(shutil.rmtree, d, True)
        pkg = os.path.join(d, 'package')
        os.makedirs(os.path.join(pkg, 'harness'))
        for name in HARNESS_FILES:
            shutil.copy2(os.path.join(HARNESS_DIR, name), os.path.join(pkg, 'harness', name))
        config = json.loads(open(TEMPLATE).read())
        r2 = os.path.join(d, 'r2.dmx')
        orig = os.path.join(d, 'orig.dmx')
        with open(r2, 'wb') as f:
            f.write(b'fixture')
        with open(orig, 'wb') as f:
            f.write(b'original')
        run = os.path.join(d, 'run')
        config.update({'original_session': orig, 'original_session_sha256': hashlib.sha256(b'original').hexdigest(),
                       'r2_fixture': r2, 'r2_fixture_sha256': hashlib.sha256(b'fixture').hexdigest(),
                       'run_dir': run, 'capture_session': os.path.join(run, 'F01_W2_CAPTURE_DISPOSABLE.dmx'),
                       'apply_session': os.path.join(run, 'F01_W2_APPLY_DISPOSABLE.dmx'),
                       'reports_dir': os.path.join(run, 'reports'),
                       'pose_path': os.path.join(run, 'poses', 'left_arm_pose.f01w2.json'),
                       'cpm_source': orig})
        config['capture_session_sha256'] = config['apply_session_sha256'] = config['r2_fixture_sha256']
        with open(os.path.join(pkg, 'harness', 'config.json'), 'wb') as f:
            f.write(json.dumps(config, indent=1, sort_keys=True).encode('ascii'))
        return pkg, config

    def test_manifest_and_prepare(self):
        pkg, config = self.package()
        ns = load(PREPARE)
        quiet(ns['manifest'], pkg)
        self.assertRaises(OSError, quiet, ns['manifest'], pkg)            # exclusive
        run = quiet(ns['prepare'], pkg)
        self.assertEqual(sorted(os.listdir(run)), ['F01_W2_APPLY_DISPOSABLE.dmx', 'F01_W2_CAPTURE_DISPOSABLE.dmx',
                                                   'harness', 'poses', 'reports'])
        for k in ('capture_session', 'apply_session'):
            with open(config[k], 'rb') as f:
                self.assertEqual(f.read(), b'fixture')
        self.assertNotEqual(os.path.normcase(config['capture_session']), os.path.normcase(config['apply_session']))
        self.assertEqual(os.listdir(os.path.join(run, 'poses')), [])
        self.assertRaises(SystemExit, quiet, ns['prepare'], pkg)           # never reuse a run directory
        with open(os.path.join(run, 'harness', 'CAPTURE_STEP.txt')) as f:
            line = f.read()
        self.assertIn('__f01w2_owner_step__', line)
        self.assertIn(os.path.join(run, 'harness', 'f01w2_capture.py').replace('\\', '\\\\'), line)

    def test_prepare_refuses_tampered_harness(self):
        pkg, config = self.package()
        ns = load(PREPARE)
        quiet(ns['manifest'], pkg)
        with open(os.path.join(pkg, 'harness', 'f01w2_apply.py'), 'ab') as f:
            f.write(b'\n')
        self.assertRaises(SystemExit, quiet, ns['prepare'], pkg)

    def test_config_must_name_four_distinct_files_and_fixed_pose_path(self):
        pkg, config = self.package()
        ns = load(PREPARE)
        bad = dict(config)
        bad['apply_session'] = bad['capture_session']
        self.assertRaises(SystemExit, ns['load_config_checked'], bad)
        bad = dict(config)
        bad['pose_path'] = os.path.join(config['run_dir'], 'poses', 'other.json')
        self.assertRaises(SystemExit, ns['load_config_checked'], bad)


# ---------------------------------------------------------------------------
# Astra-adjudicated corrections F-01..F-05 (October 29): each negative case runs through the affected path
# ---------------------------------------------------------------------------

NATIVE = 'windows-kernel32'


def native_ledger(entries):
    """The offline ledger re-expressed as native evidence: the fake injects process ids that differ from the test
    process, so for native-mode finalization every report's process id is set to the report's own pid (process A
    and process B then share a pid with different creation times, as after PID reuse) and every provider is the
    native one. The PASS of this copy shows that the native-only checks accept consistent evidence."""
    copy = json.loads(json.dumps(entries))
    for x in copy:
        r = x['report']
        r['process']['provider'] = NATIVE
        r['process']['pid'] = r['pid']
        if r['step'] == 'PROCESS_GATE':
            r['gate']['provider'] = NATIVE
    a = copy[0]['report']['process']
    copy[1]['report']['gate']['process_a']['pid'] = a['pid']
    for row in (copy[1]['report']['gate'].get('process_a_lookup'),
                (copy[2]['report'].get('process_a_now') or {}).get('lookup')):
        if isinstance(row, dict):
            row['pid'] = a['pid']                  # the raw lookup of process A names process A's pid
    return copy


class FinalizerTools(Base):
    """TestFinalizer's helpers without re-running its tests."""
    complete = TestFinalizer.__dict__['complete']
    verdict = TestFinalizer.__dict__['verdict']
    by_step = TestFinalizer.__dict__['by_step']
    mutated = TestFinalizer.__dict__['mutated']


class TransactionTools(FinalizerTools):
    """TestTransactions' helper without re-running its tests."""
    run_with = TestTransactions.__dict__['run_with']


class TestF01SkeletalEvidence(FinalizerTools):
    """F-01: the finalizer validates the per-bone errors, not only the summary flags."""

    def bones(self, es, step, stage=None, event=None):
        r = self.by_step(es, step, stage)
        o = [x for x in r['events'] if x['event'] == event][0]['observation'] if event else r['observation']
        return o, o['bones']

    def test_missing_and_malformed_bone_records(self):
        e, ns, entries = self.complete()
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'APPLY', 'committed')[0].pop('bones'))
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'UNDO', 'undone')[1].pop('bip_hand_l'))
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'REDO', 'redone')[1].__setitem__('bip_extra',
                                                                                              {}))
        for bad in (True, None, -0.001, float('nan'), float('inf'), '0.0', [0.0]):
            def malformed(es, bad=bad):
                self.bones(es, 'FINAL_UNDO', 'final')[1]['bip_lowerArm_l']['baseline_angle'] = bad
            self.mutated(e, ns, entries, malformed)
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'APPLY', 'committed', 'abort-evaluated')[1]
                     ['bip_UpperArm_l'].pop('baseline_world_position'))

    def test_out_of_tolerance_with_summary_flags_unchanged(self):
        e, ns, entries = self.complete()
        tol = e.config['tolerances']
        cases = [('APPLY', 'committed', 'primary_angle', tol['angle_degrees']),
                 ('APPLY', 'committed', 'secondary_position', tol['position']),
                 ('REDO', 'redone', 'secondary_angle', tol['angle_degrees']),
                 ('UNDO', 'undone', 'baseline_angle', tol['angle_degrees']),
                 ('FINAL_UNDO', 'final', 'baseline_world_position', tol['position'])]
        for step, stage, key, limit in cases:
            def over(es, step=step, stage=stage, key=key, limit=limit):
                o, bones = self.bones(es, step, stage)
                self.assertTrue(o['correct'])
                bones['bip_hand_l'][key] = limit * 1.5
            self.mutated(e, ns, entries, over)

        def abort_baseline_over(es):
            self.bones(es, 'APPLY', 'committed', 'abort-evaluated')[1]['bip_hand_l']['baseline_angle'] = 1.0
        self.mutated(e, ns, entries, abort_baseline_over)

    def test_rig_inputs_must_match_the_expectation(self):
        e, ns, entries = self.complete()
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'APPLY', 'committed')[0].__setitem__(
            'inputs_at_goal', False))
        self.mutated(e, ns, entries, lambda es: self.bones(es, 'UNDO', 'undone')[0].__setitem__(
            'inputs_at_baseline', False))

    def test_unsuccessful_idle_observation_must_be_complete_before_retime(self):
        e, ns, entries = self.complete(policy='retime')
        self.assertEqual(self.verdict(e, ns, entries)[0], 'PASS')
        reasons = self.mutated(e, ns, entries, lambda es: self.by_step(es, 'APPLY', 'committed')['observation']
                               .pop('bones'))
        self.assertIn('retiming was not allowed', ' '.join(reasons))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'UNDO', 'undone')['observation'].__setitem__(
            'unrelated_changes', ['bone bip_head']))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'REDO', 'redone').pop('observed_changes'))

    def test_idle_preservation_failure_is_not_sent_to_retime(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        e.world_b.shift_unrelated_bone = 'bip_head'
        final = e.run_b()
        self.assertEqual((final['step'], final['status']), ('APPLY', 'FAIL'), final.get('error'))
        self.assertIn('retiming is not offered', final['error'])
        self.assertNotIn('next', final)
        self.assertNotIn('Undo', [c[0] for c in e.world_b.dm.calls])


class TestF02EvidenceFinalization(FinalizerTools):
    """F-02: context, process identity, protected-file evidence, compatibility and both planning
    implementations are audited explicitly."""

    def test_wrong_context_on_every_scene_step(self):
        e, ns, entries = self.complete()
        for step, stage in (('CAPTURE', None), ('APPLY', 'committed'), ('UNDO', 'undone'), ('REDO', 'redone'),
                            ('FINAL_UNDO', 'final')):
            for key, value in (('document_path', 'C:\\wrong_session.dmx'), ('head_seconds', 0.5),
                               ('shot_media_seconds', 0.1), ('pid', 99999), ('file_id', None)):
                def wrong(es, step=step, stage=stage, key=key, value=value):
                    self.by_step(es, step, stage)['context'][key] = value
                self.mutated(e, ns, entries, wrong)

            def shot(es, step=step, stage=stage):
                self.by_step(es, step, stage)['context']['shot']['name'] = 'shot99'
            self.mutated(e, ns, entries, shot)
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'CAPTURE').pop('context'))

        def baseline_context(es):
            self.by_step(es, 'APPLY', 'committed')['destination_baseline']['context']['document']['handle'] += 1
        self.mutated(e, ns, entries, baseline_context)

        def shot_handle_moves(es):
            self.by_step(es, 'REDO', 'redone')['context']['shot']['handle'] += 1
        self.mutated(e, ns, entries, shot_handle_moves)

    def test_retime_context_is_audited(self):
        e, ns, entries = self.complete(policy='retime')

        def retime_document(es):
            [x for x in es if x['report']['step'] == 'RETIME'][1]['report']['context']['document_path'] = 'C:\\x'
        self.mutated(e, ns, entries, retime_document)

    def test_gate_needs_no_scene_context(self):
        e, ns, entries = self.complete()
        self.assertNotIn('context', self.by_step(entries, 'PROCESS_GATE'))
        self.assertEqual(self.verdict(e, ns, entries)[0], 'PASS')

    def test_native_process_identity_and_provider(self):
        e, ns, entries = self.complete()
        native = native_ledger(entries)
        verdict, reasons, _ = ns['verdict'](native, True, True, e.config, e.pose_bytes(), False)
        self.assertEqual(verdict, 'PASS', reasons)

        def check(fn, why):
            copy = json.loads(json.dumps(native))
            fn(copy)
            v, r, _ = ns['verdict'](copy, True, True, e.config, e.pose_bytes(), False)
            self.assertEqual(v, 'INCONCLUSIVE', r)
            self.assertIn(why, ' '.join(r))
        check(lambda es: self.by_step(es, 'PROCESS_GATE')['gate'].__setitem__('provider', 'offline-fake'),
              'native kernel32 provider')
        check(lambda es: self.by_step(es, 'UNDO', 'undone')['process'].__setitem__('pid', 4242),
              'report pid is not the queried process')
        check(lambda es: self.by_step(es, 'CAPTURE')['context'].__setitem__('pid', 4242), 'process id')
        check(lambda es: self.by_step(es, 'REDO', 'redone')['process'].__setitem__('creation_filetime', 1),
              'not the same process B')
        check(lambda es: self.by_step(es, 'APPLY', 'committed')['process'].__setitem__('provider', 'other'),
              'not consistent')

    def test_complete_protected_file_evidence_on_every_report(self):
        e, ns, entries = self.complete()
        for i in range(len(entries)):
            def tamper(es, i=i):
                es[i]['report']['integrity_before'] = es[i]['report']['integrity_after'] = {'tampered': 'hash'}
            self.mutated(e, ns, entries, tamper)

            def drop(es, i=i):
                for k in ('integrity_before', 'integrity_after'):
                    es[i]['report'][k].pop('cpm_source')
            self.mutated(e, ns, entries, drop)

            def other_hash(es, i=i):
                for k in ('integrity_before', 'integrity_after'):
                    es[i]['report'][k]['f01w2_apply.py'] = 'a' * 64
            self.mutated(e, ns, entries, other_hash)

        def all_consistent_but_not_configured(es):
            for x in es:
                for k in ('integrity_before', 'integrity_after'):
                    x['report'][k]['apply_session'] = 'b' * 64
        reasons = self.mutated(e, ns, entries, all_consistent_but_not_configured)
        self.assertIn('configured hashes', ' '.join(reasons))

    def test_compatibility_descriptor_and_preflight(self):
        e, ns, entries = self.complete()

        def pf(es):
            return self.by_step(es, 'APPLY', 'committed')['preflight']
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'APPLY', 'committed').pop('preflight'))
        self.mutated(e, ns, entries, lambda es: pf(es).pop('live_descriptor'))
        self.mutated(e, ns, entries, lambda es: pf(es).__setitem__('compatibility', {}))
        self.mutated(e, ns, entries, lambda es: pf(es)['compatibility'].__setitem__('arm_bone_offset_max', 0.5))
        self.mutated(e, ns, entries, lambda es: pf(es)['live_descriptor']['arm_chain'][1].__setitem__('index', 77))
        self.mutated(e, ns, entries, lambda es: pf(es)['live_descriptor']['arm_chain'][0]['local_position']
                     .__setitem__(0, 1.0e-6))
        self.mutated(e, ns, entries, lambda es: pf(es)['live_descriptor']['constraints']['ik'].__setitem__(
            'target_weight', 0.5))
        self.mutated(e, ns, entries, lambda es: pf(es)['live_descriptor']['handles'].pop('Elbow_l'))
        self.mutated(e, ns, entries, lambda es: pf(es)['undo_state'].__setitem__('can_redo', {'unreadable': 'x'}))

    def test_shoulder_guard_recomputed(self):
        e, ns, entries = self.complete()

        def moved(es):
            r = self.by_step(es, 'APPLY', 'committed')
            r['destination_baseline']['skeleton']['bones']['bip_UpperArm_l']['world_position'][0] += 5.0
            r['plan']['collar_mapping_error'] = 0.0
        reasons = self.mutated(e, ns, entries, moved)
        self.assertIn('shoulder-origin guard not reproduced', ' '.join(reasons))

        def forged_error(es):
            self.by_step(es, 'APPLY', 'committed')['plan']['collar_mapping_error'] += 1e-4
        self.mutated(e, ns, entries, forged_error)

    def test_both_planning_implementations_against_independent_goals(self):
        e, ns, entries = self.complete()

        def second(es, name, value):
            self.by_step(es, 'APPLY', 'committed')['plan']['independent_float32'][name] = value
        self.mutated(e, ns, entries, lambda es: second(es, 'Hand_l_p', [0.0, 0.0, 0.0]))
        self.mutated(e, ns, entries, lambda es: second(es, 'Elbow_l_p', [9.0, 9.0, 9.0]))
        self.mutated(e, ns, entries, lambda es: second(es, 'Hand_l_o', [0.0, 0.0, 0.0, 1.0]))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'APPLY', 'committed')['plan'].pop(
            'independent_float32'))

        def opposite_sign_is_the_same_orientation(es):
            p = self.by_step(es, 'APPLY', 'committed')['plan']
            p['independent_float32']['Hand_l_o'] = [-c for c in p['independent_float32']['Hand_l_o']]
        self.mutated(e, ns, entries, opposite_sign_is_the_same_orientation, expect='PASS')

    def test_observed_changes_must_be_explicitly_empty(self):
        e, ns, entries = self.complete()
        for step, stage in (('APPLY', 'committed'), ('UNDO', 'undone'), ('REDO', 'redone'), ('FINAL_UNDO', 'final')):
            self.mutated(e, ns, entries, lambda es, s=step, g=stage: self.by_step(es, s, g).pop('observed_changes'))
            self.mutated(e, ns, entries, lambda es, s=step, g=stage: self.by_step(es, s, g).__setitem__(
                'observed_changes', None))

    def test_gate_and_apply_process_states(self):
        e, ns, entries = self.complete()
        self.assertIn(self.by_step(entries, 'PROCESS_GATE')['gate']['process_a_state'], ('EXITED', 'ABSENT'))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'PROCESS_GATE')['gate'].__setitem__(
            'process_a_state', 'UNKNOWN'))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'APPLY', 'committed').pop('process_a_now'))
        self.mutated(e, ns, entries, lambda es: self.by_step(es, 'APPLY', 'committed')['process_a_now']
                     .__setitem__('state', 'UNKNOWN'))


def raiser(message):
    def fn(*a, **k):
        raise RuntimeError(message)
    return fn


class TestF03UndoEvidence(TransactionTools):
    """F-03: required history fields readable; operation-specific invariants."""

    def native_calls(self, e):
        return [c[0] for c in e.world_b.dm.calls]

    def test_identically_unreadable_capture_history_is_inconclusive(self):
        for name in ('IsUndoEnabled', 'CanUndo', 'CanRedo', 'GetUndoDesc', 'GetRedoDesc'):
            e = self.env()
            w = e.start_a()
            setattr(w.dm, name, raiser('%s failed (test)' % name))
            report = e.submit('capture')
            self.assertEqual(report['status'], 'INCONCLUSIVE', (name, report.get('error')))
            self.assertIn('Undo history unreadable', report['error'])
            self.assertFalse(os.path.exists(e.config['pose_path']))
            self.assertNotIn('publication', report)
            self.assertEqual(w.dm.calls, [])

    def test_transiently_unreadable_capture_history_is_inconclusive_at_either_snapshot(self):
        """Unreadable at only one of the two capture snapshots: still INCONCLUSIVE before any publication
        (not reclassified as a capture-integrity STOP)."""
        for failing_call, where in ((1, 'at capture start'), (2, 'at capture completion')):
            e = self.env()
            w = e.start_a()
            calls = [0]
            real = w.dm.CanRedo

            def can_redo(real=real, calls=calls, failing_call=failing_call):
                calls[0] += 1
                if calls[0] == failing_call:
                    raise RuntimeError('CanRedo failed once (test)')
                return real()
            w.dm.CanRedo = can_redo
            report = e.submit('capture')
            self.assertEqual(report['status'], 'INCONCLUSIVE', (where, report.get('error')))
            self.assertIn(where, report['error'])
            self.assertFalse(os.path.exists(e.config['pose_path']))

    def test_non_boolean_history_flag_is_unreadable(self):
        e = self.env()
        w = e.start_a()
        w.dm.CanRedo = lambda: 'no'
        report = e.submit('capture')
        self.assertEqual(report['status'], 'INCONCLUSIVE')
        self.assertFalse(os.path.exists(e.config['pose_path']))

    def test_unreadable_item_count_alone_does_not_block_capture(self):
        """GetUndoItemCount is diagnostic: unreadable, it is recorded as unreadable, never as a count."""
        e = self.env()
        w = e.start_a()
        w.dm.GetUndoItemCount = raiser('count failed (test)')
        report = e.submit('capture')
        self.assertEqual(report['status'], 'CAPTURE_COMPLETE_PENDING_CLOSE', report.get('error'))
        self.assertIn('unreadable', report['capture']['source_baseline']['undo']['item_count_recorded_only'])

    def test_unreadable_history_before_any_write_is_inconclusive(self):
        def prep(e):
            e.world_b.dm.GetRedoDesc = raiser('GetRedoDesc failed (test)')
        e, final = self.run_with(prepare=prep)
        self.assertEqual((final['step'], final['status']), ('APPLY', 'INCONCLUSIVE'), final.get('error'))
        self.assertEqual(e.world_b.dm.calls, [])

    def test_unreadable_history_after_abort_stops_before_commit(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.AbortUndoableOperation

            def abort():
                real()
                dm.GetUndoDesc = raiser('GetUndoDesc failed after Abort (test)')
            dm.AbortUndoableOperation = abort
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Recovery/ownership unverified', final['error'])
        self.assertEqual(self.native_calls(e), ['StartUndo', 'AbortUndoableOperation'])
        ev = [x for x in final['events'] if x['event'] == 'abort-check'][0]
        self.assertIn('unreadable', ev['undo_after']['undo_desc'])

    def test_history_changed_by_abort_stops_without_repair(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.AbortUndoableOperation

            def abort():
                real()
                dm.redo.append({'undo': 'x', 'redo': 'stray redo', 'items': []})
            dm.AbortUndoableOperation = abort
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('changed the required Undo/Redo history', final['error'])
        self.assertEqual(self.native_calls(e), ['StartUndo', 'AbortUndoableOperation'])
        self.assertEqual(len(e.world_b.dm.redo), 1)                  # evidence preserved, not cleared

    def test_history_changed_between_abort_and_commit(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.AbortUndoableOperation

            def abort():
                real()
                e.world_b.queue.insert(0, _Callback(lambda: dm.push_foreign('user edit')))
            dm.AbortUndoableOperation = abort
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('Recovery/ownership unverified', final['error'])
        self.assertNotIn('FinishUndo', self.native_calls(e))

    def test_failed_commit_abort_must_restore_history(self):
        def prep(e):
            e.world_b.perturb_layer = e.layer(e.world_b, 'shot10', 'Elbow_l_p').h
            dm = e.world_b.dm
            real = dm.AbortUndoableOperation
            n = [0]

            def abort():
                n[0] += 1
                real()
                if n[0] == 2:
                    dm.redo.append({'undo': 'x', 'redo': 'stray redo', 'items': []})
            dm.AbortUndoableOperation = abort
        e, final = self.run_with(prepare=prep)
        self.assertEqual(final['status'], 'STOP')
        self.assertIn('not the required Undo/Redo history', final['error'])
        ev = [x for x in final['events'] if x['event'] == 'commit-aborted'][0]
        self.assertTrue(ev['authored_restored'])
        self.assertFalse(ev['history_restored'])
        self.assertIn('undo_before', ev)

    def test_unreadable_history_before_and_after_undo_is_stop(self):
        e, final = self.run_with(hooks={('UNDO', 'undone'): lambda e: setattr(
            e.world_b.dm, 'CanUndo', raiser('CanUndo failed (test)'))})
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'), final.get('error'))
        self.assertIn('Recovery/ownership unverified', final['error'])
        self.assertNotIn('Undo', self.native_calls(e))

        def prep(e):
            dm = e.world_b.dm
            real = dm.Undo

            def undo():
                real()
                dm.GetRedoDesc = raiser('GetRedoDesc failed after Undo (test)')
            dm.Undo = undo
        e, final = self.run_with(prepare=prep)
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'), final.get('error'))
        self.assertNotIn('Redo', self.native_calls(e))

    def test_false_redo_availability_after_undo(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.CanRedo
            dm.CanRedo = lambda: False if ('Undo',) in dm.calls else real()
        e, final = self.run_with(prepare=prep)
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'), final.get('error'))
        self.assertNotIn('Redo', self.native_calls(e))

    def test_false_undo_availability_after_redo(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.CanUndo
            dm.CanUndo = lambda: False if ('Redo',) in dm.calls else real()
        e, final = self.run_with(prepare=prep)
        self.assertEqual((final['step'], final['status']), ('REDO', 'STOP'), final.get('error'))
        self.assertEqual(self.native_calls(e).count('Undo'), 1)

    def test_finalizer_requires_readable_restored_owned_history(self):
        t = self
        e, ns, entries = self.complete()

        def ev(es, step, stage, name):
            return [x for x in t.by_step(es, step, stage)['events'] if x['event'] == name][0]
        cases = [
            lambda es: ev(es, 'APPLY', 'committed', 'abort-check')['undo_after'].__setitem__(
                'redo_desc', {'unreadable': 'x'}),
            lambda es: ev(es, 'APPLY', 'committed', 'abort-check')['undo_before'].__setitem__('can_undo', None),
            lambda es: ev(es, 'APPLY', 'committed', 'abort-check')['undo_after'].update(
                {'can_redo': True, 'redo_desc': 'user redo'}),
            lambda es: ev(es, 'APPLY', 'committed', 'commit')['undo_before'].__setitem__('can_undo', True),
            lambda es: ev(es, 'APPLY', 'committed', 'commit')['undo_after'].__setitem__('redo_desc', 7),
            lambda es: ev(es, 'UNDO', 'undone', 'undo')['undo_after'].__setitem__('can_redo', False),
            lambda es: ev(es, 'REDO', 'redone', 'redo')['undo_after'].__setitem__('can_undo', False),
            lambda es: ev(es, 'FINAL_UNDO', 'final', 'undo')['undo_before'].__setitem__('can_undo', 'yes'),
            lambda es: t.by_step(es, 'CAPTURE')['capture']['source_baseline']['undo_completion'].__setitem__(
                'can_redo', True),
            lambda es: t.by_step(es, 'CAPTURE')['capture']['source_baseline'].pop('undo_completion'),
            lambda es: t.by_step(es, 'CAPTURE')['capture']['source_baseline']['undo_completion'].__setitem__(
                'item_count_recorded_only', 99),
        ]
        for fn in cases:
            copy = json.loads(json.dumps(entries))
            fn(copy)
            verdict, reasons, _ = ns['verdict'](copy, True, True, e.config, e.pose_bytes(), True)
            self.assertEqual(verdict, 'INCONCLUSIVE', reasons)


class _Callback(object):
    """A queued event-loop callback (stands for any other activity between two harness callbacks)."""

    def __init__(self, fn):
        sig = fake.Signal()
        sig.connect(fn)
        self.timeout = sig


def observed_change(e):
    e.world_b.shots['shot10'].ops[4].set('extra_observed_attr', 1.0)


class TestF04Preservation(TransactionTools):
    """F-04: unclassified operator/constraint changes stop at every boundary; nothing native follows."""

    def native_calls(self, e):
        return [c[0] for c in e.world_b.dm.calls]

    def assert_stopped(self, e, final, step, calls):
        self.assertEqual((final['step'], final['status']), (step, 'STOP'), final.get('error'))
        self.assertIn('Unclassified operator/constraint attribute changes', final['error'])
        self.assertNotIn('next', final)
        self.assertEqual(self.native_calls(e), calls)
        before = len(e.reports())
        e.submit('apply')                                   # subsequent submissions are refused
        self.assertEqual(len(e.reports()), before)
        self.assertEqual(self.native_calls(e), calls)
        self.assertIn('experiment has ended', e.output[-1])

    def test_change_before_the_abort_check(self):
        def prep(e):
            e.world_b.queue.insert(0, _Callback(lambda: observed_change(e)))
        e, final = self.run_with(prepare=prep)
        self.assert_stopped(e, final, 'APPLY', [])

    def test_change_at_apply_idle_observation(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.FinishUndo

            def finish():
                real()
                observed_change(e)
            dm.FinishUndo = finish
        e, final = self.run_with(prepare=prep)
        self.assert_stopped(e, final, 'APPLY', ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo'])
        self.assertTrue(final['observed_changes'][0].endswith('/attributes/extra_observed_attr'),
                        final['observed_changes'])

    def test_change_at_unsuccessful_idle_is_not_sent_to_retime(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.FinishUndo

            def finish():
                real()
                observed_change(e)
            dm.FinishUndo = finish
        e, final = self.run_with(prepare=prep, policy='retime')
        self.assert_stopped(e, final, 'APPLY', ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo'])

    def test_change_after_owner_delay_before_undo(self):
        e, final = self.run_with(hooks={('UNDO', 'undone'): observed_change})
        self.assert_stopped(e, final, 'UNDO', ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo'])

    def test_change_before_redo_and_final_undo(self):
        e, final = self.run_with(hooks={('REDO', 'redone'): observed_change})
        self.assert_stopped(e, final, 'REDO',
                            ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo', 'Undo'])
        e, final = self.run_with(hooks={('FINAL_UNDO', 'final'): observed_change})
        self.assert_stopped(e, final, 'FINAL_UNDO',
                            ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo', 'Undo', 'Redo'])

    def test_change_at_history_observation(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.Undo

            def undo():
                real()
                observed_change(e)
            dm.Undo = undo
        e, final = self.run_with(prepare=prep)
        self.assert_stopped(e, final, 'UNDO',
                            ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo', 'Undo'])

    def test_change_at_retime(self):
        e, final = self.run_with(hooks={('RETIME', 'committed'): observed_change}, policy='retime')
        self.assertEqual([s[0] for s in statuses(e)], ['CAPTURE', 'PROCESS_GATE', 'APPLY', 'RETIME'])
        self.assert_stopped(e, final, 'RETIME', ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo'])

    def test_skeletal_change_before_a_history_operation(self):
        def shift(e):
            e.world_b.shift_unrelated_bone = 'bip_head'     # takes effect at the next evaluation
        e, final = self.run_with(hooks={('UNDO', 'undone'): shift})
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'), final.get('error'))
        self.assertIn('Skeletal preservation changed before undo', final['error'])
        self.assertNotIn('Undo', self.native_calls(e))

    def test_unreadable_preservation_evidence_after_mutation_is_stop(self):
        def hook(e):
            op = e.world_b.shots['shot10'].ops[4]
            op.set('extra_observed_attr', 1.0)
            e.world_b.unreadable |= set([(op.h, 'extra_observed_attr')])
        e, final = self.run_with(hooks={('UNDO', 'undone'): hook})
        self.assertEqual((final['step'], final['status']), ('UNDO', 'STOP'), final.get('error'))
        self.assertIn('Preservation evidence unreadable', final['error'])
        self.assertNotIn('Undo', self.native_calls(e))


class Kernel(object):
    """Scripted kernel32 for WindowsProcesses: pid -> (state, creation); state is absent, denied, running or
    exited. Counts opened and closed handles."""

    def __init__(self, table):
        self.table = table
        self.last_error = 0
        self.opened = []
        self.closed = []
        self.by_handle = {}
        for name in ('OpenProcess', 'CloseHandle', 'GetProcessTimes', 'GetExitCodeProcess',
                     'QueryFullProcessImageNameW', 'K32EnumProcesses'):
            setattr(self, name, _Fn(getattr(self, '_' + name)))

    def _OpenProcess(self, access, inherit, pid):
        state = self.table.get(int(pid), ('absent', 0))[0]
        if state in ('absent', 'denied'):
            self.last_error = 87 if state == 'absent' else 5
            return 0
        h = 1000 + len(self.opened)
        self.opened.append(h)
        self.by_handle[h] = int(pid)
        return h

    def _CloseHandle(self, h):
        self.closed.append(h)
        return True

    def _GetProcessTimes(self, h, created, exited, kernel, user):
        c = self.table[self.by_handle[h]][1]
        created.dwHighDateTime, created.dwLowDateTime = c >> 32, c & 0xffffffff
        return True

    def _GetExitCodeProcess(self, h, code):
        code.value = 259 if self.table[self.by_handle[h]][0] == 'running' else 0
        return True

    def _QueryFullProcessImageNameW(self, h, flags, buf, size):
        buf.value = u'C:\\SFM\\sfm.exe'
        return True

    def _K32EnumProcesses(self, ids, size, used):
        for i, p in enumerate(sorted(self.table)):
            ids[i] = p
        used.value = len(self.table) * 4
        return True


class _Fn(object):
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *a):
        return self.fn(*a)


class TestF05ProcessQueries(Base):
    """F-05: strict lookup of the recorded process versus best-effort enumeration."""

    def windows(self, table):
        import ctypes
        import ctypes.wintypes
        core = load_core()
        k = Kernel(table)

        class CT(object):
            byref = staticmethod(lambda x: x)
            sizeof = staticmethod(ctypes.sizeof)
            POINTER = staticmethod(ctypes.POINTER)
            create_unicode_buffer = staticmethod(ctypes.create_unicode_buffer)

            @staticmethod
            def get_last_error():
                return k.last_error
        wp = core['WindowsProcesses'].__new__(core['WindowsProcesses'])
        wp.ctypes, wp.wintypes, wp.k = CT, ctypes.wintypes, k
        return core, wp, k

    def test_targeted_lookup_distinguishes_absent_denied_exited_reused(self):
        core, wp, k = self.windows({10: ('denied', 1000), 11: ('exited', 1000), 12: ('running', 2000),
                                    13: ('running', 1000)})
        state = core['recorded_process_state']
        self.assertRaises(core['Unresolved'], wp.lookup, 10)
        self.assertIsNone(wp.lookup(99))
        self.assertEqual(state(wp, {'pid': 99, 'creation_filetime': 1000})['state'], 'ABSENT')
        denied = state(wp, {'pid': 10, 'creation_filetime': 1000})
        self.assertEqual(denied['state'], 'UNKNOWN')
        self.assertIn('(5)', denied['error'])
        self.assertEqual(state(wp, {'pid': 11, 'creation_filetime': 1000})['state'], 'EXITED')
        self.assertEqual(state(wp, {'pid': 12, 'creation_filetime': 1000})['state'], 'PID_REUSED')
        self.assertEqual(state(wp, {'pid': 13, 'creation_filetime': 1000})['state'], 'RUNNING')
        self.assertEqual(sorted(k.opened), sorted(k.closed))      # every opened handle is closed

    def test_images_is_best_effort_and_filters_exited(self):
        core, wp, k = self.windows({10: ('denied', 1000), 11: ('exited', 1000), 12: ('running', 2000)})
        self.assertEqual(wp.images(), [(12, u'C:\\SFM\\sfm.exe')])
        self.assertEqual(sorted(k.opened), sorted(k.closed))

    def test_gate_diagnoses_a_running_process_a_as_running(self):
        """A live process A is reported as running, not as an unresolved query."""
        e = self.env()
        e.capture()
        with self.assertRaises(SystemExit) as ctx:
            e.gate()
        self.assertIn('is still running', str(ctx.exception))
        self.assertNotIn('could not be established', str(ctx.exception))

    def test_gate_refuses_when_process_a_cannot_be_queried(self):
        e = self.env()
        e.capture()
        e.table[A_PID]['denied'] = True                     # access denied: not proof that A exited
        with self.assertRaises(SystemExit) as ctx:
            e.gate()
        self.assertIn('could not be established', str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(e.config['reports_dir'], 'F01W2-02-PROCESS_GATE.json')))
        e.table[A_PID]['running'] = False                   # still denied after A really exits
        self.assertRaises(SystemExit, e.gate)

    def test_gate_records_verified_exit_absence_and_reuse(self):
        for prepare, expected in ((lambda e: e.table[A_PID].__setitem__('running', False), 'EXITED'),
                                  (lambda e: e.table.pop(A_PID), 'ABSENT'),
                                  (lambda e: e.table.__setitem__(A_PID, {'creation_filetime': 999999, 'running': True,
                                                                         'image': 'C:\\Windows\\notepad.exe'}),
                                   'PID_REUSED')):
            e = self.env()
            e.capture()
            prepare(e)
            sys.modules.pop('f01w2_runtime', None)
            report = e.gate()
            self.assertEqual(report['gate']['process_a_state'], expected)
            self.assertIs(report['gate']['process_a_running'], False)

    def test_apply_refuses_when_process_a_becomes_unqueryable(self):
        e = self.env()
        e.capture()
        e.exit_a()
        e.gate()
        e.start_b()
        e.table[A_PID]['denied'] = True
        report = e.submit('apply')
        self.assertEqual(report['status'], 'INCONCLUSIVE', report.get('error'))
        self.assertIn('Process A state could not be established', report['error'])
        self.assertEqual(report['process_a_now']['state'], 'UNKNOWN')
        self.assertEqual(e.world_b.dm.calls, [])
        verdict = e.finalize()['verdict']
        self.assertEqual(verdict, 'INCONCLUSIVE')


class _FrontQueue(list):
    """Puts one fault callback in front of the n-th callback a step schedules: the fault happens after the
    step's synchronous entry (or an earlier callback) and before that deferred callback."""

    def __init__(self, items, fault, nth=1):
        list.__init__(self, items)
        self.fault, self.nth = fault, nth

    def append(self, timer):
        self.nth -= 1
        if self.fault is not None and self.nth == 0:
            fault, self.fault = self.fault, None
            list.append(self, _Callback(fault))
        list.append(self, timer)


class TestCorrectionAPostMutationStop(TransactionTools):
    """Correction A: after a native mutation, unreadable required authored, preservation or recovery evidence is
    STOP (unverified) at synchronous entry, in deferred callbacks and at retime; before any write it stays
    INCONCLUSIVE. STOP schedules nothing more, emits no next action and makes no compensating call."""

    def mode_unreadable(self, e):
        e.world_b.unreadable |= set([(e.world_b.channel('shot10', 'Hand_l_p').h, 'mode')])

    def native_calls(self, e):
        return [c[0] for c in e.world_b.dm.calls]

    def assert_stop(self, e, final, step, calls):
        self.assertEqual((final['step'], final['status']), (step, 'STOP'), final.get('error'))
        self.assertIn('unverified', final['error'].lower())
        self.assertNotIn('next', final)
        self.assertEqual(self.native_calls(e), calls)
        before = len(e.reports())
        e.submit('apply')
        self.assertEqual(len(e.reports()), before)
        self.assertEqual(self.native_calls(e), calls)

    COMMITTED = ['StartUndo', 'AbortUndoableOperation', 'StartUndo', 'FinishUndo']

    def test_unreadable_at_history_step_entry(self):
        for step, stage, calls in (('UNDO', 'undone', self.COMMITTED),
                                   ('REDO', 'redone', self.COMMITTED + ['Undo']),
                                   ('FINAL_UNDO', 'final', self.COMMITTED + ['Undo', 'Redo'])):
            e, final = self.run_with(hooks={(step, stage): self.mode_unreadable})
            self.assert_stop(e, final, step, calls)
            self.assertIn('Unverified after mutation (%s, %s stage)' % (step, stage), final['error'])

    def test_unreadable_between_entry_and_the_deferred_callback(self):
        for step, stage, calls in (('UNDO', 'undone', self.COMMITTED),
                                   ('REDO', 'redone', self.COMMITTED + ['Undo']),
                                   ('FINAL_UNDO', 'final', self.COMMITTED + ['Undo', 'Redo'])):
            def hook(e):
                e.world_b.queue = _FrontQueue(e.world_b.queue, lambda: self.mode_unreadable(e))
            e, final = self.run_with(hooks={(step, stage): hook})
            self.assert_stop(e, final, step, calls)
            self.assertIn('Unverified after mutation', final['error'])

    def test_unreadable_after_the_history_operation_before_its_observation(self):
        def prep(e):
            dm = e.world_b.dm
            real = dm.Undo

            def undo():
                real()
                e.world_b.queue = _FrontQueue(e.world_b.queue, lambda: self.mode_unreadable(e))
            dm.Undo = undo
        e, final = self.run_with(prepare=prep)
        self.assert_stop(e, final, 'UNDO', self.COMMITTED + ['Undo'])

    def test_unreadable_at_retime_of_every_stage(self):
        for stage, calls in (('committed', self.COMMITTED), ('undone', self.COMMITTED + ['Undo']),
                             ('redone', self.COMMITTED + ['Undo', 'Redo'])):
            e, final = self.run_with(hooks={('RETIME', stage): self.mode_unreadable}, policy='retime')
            self.assert_stop(e, final, 'RETIME', calls)

    def test_unreadable_after_the_aborted_test_write_before_commit(self):
        """The aborted test write is a native mutation: the commit callback's entry reads are post-mutation."""
        def prep(e):
            e.world_b.queue = _FrontQueue(e.world_b.queue, lambda: self.mode_unreadable(e), nth=3)
        e, final = self.run_with(prepare=prep)
        self.assert_stop(e, final, 'APPLY', ['StartUndo', 'AbortUndoableOperation'])
        self.assertIn('Unverified after mutation', final['error'])

    def test_unreadable_after_commit_before_the_idle_observation(self):
        def prep(e):
            e.world_b.queue = _FrontQueue(e.world_b.queue, lambda: self.mode_unreadable(e), nth=4)
        e, final = self.run_with(prepare=prep)
        self.assert_stop(e, final, 'APPLY', self.COMMITTED)

    def test_restoration_evidence_unreadable_after_an_aborted_mutation(self):
        def prep(e):
            e.world_b.unreadable_on_abort = set([(e.world_b.channel('shot10', 'Hand_l_p').h, 'mode')])
        e, final = self.run_with(prepare=prep)
        self.assert_stop(e, final, 'APPLY', ['StartUndo', 'AbortUndoableOperation'])

    def test_unreadable_before_any_write_remains_inconclusive(self):
        def prep(e):
            self.mode_unreadable(e)
        e, final = self.run_with(prepare=prep)
        self.assertEqual((final['step'], final['status']), ('APPLY', 'INCONCLUSIVE'), final.get('error'))
        self.assertEqual(e.world_b.dm.calls, [])

        def prep2(e):
            e.world_b.queue = _FrontQueue(e.world_b.queue, lambda: self.mode_unreadable(e), nth=1)
        e, final = self.run_with(prepare=prep2)                      # before the abort check's write
        self.assertEqual((final['step'], final['status']), ('APPLY', 'INCONCLUSIVE'), final.get('error'))
        self.assertEqual(e.world_b.dm.calls, [])


def rewrite_chain(directory, reports):
    """Writes reports back to the ledger with a valid regenerated hash chain (the forgery is internally
    consistent: only the independent evidence audit can refuse it)."""
    ns = load(FINALIZE)
    names = sorted(n for n in os.listdir(directory) if ns['REPORT_RE'].match(n))
    previous = None
    for name, report in zip(names, reports):
        report['previous_report_sha256'] = previous
        raw = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=True).encode('ascii')
        with open(os.path.join(directory, name), 'wb') as f:
            f.write(raw)
        previous = hashlib.sha256(raw).hexdigest()


DENIED = "Unresolved('OpenProcess(4000) failed (5); the process state is unknown',)"


class TestCorrectionBLookupEvidence(FinalizerTools):
    """Correction B: the independent finalizer validates the raw process-A lookup behind the gate and APPLY
    exit classifications. Full-finalizer runs (main(), offline=False) on native-form ledgers with valid
    regenerated hash chains."""

    def native_run(self, forge, expect):
        e = self.env()
        final = e.complete()
        self.assertEqual(final['status'], 'COMPLETE_PENDING_CLOSE', final.get('error'))
        ns = load(FINALIZE)
        entries = native_ledger(ns['ledger'](e.config['reports_dir']))
        reports = [x['report'] for x in entries]
        forge(reports)
        rewrite_chain(e.config['reports_dir'], reports)
        result = quiet(ns['main'], e.config_path, False)
        self.assertEqual(result['verdict'], expect, result.get('reasons'))
        self.assertFalse(result['offline_process_evidence_accepted'])
        return result

    def test_consistent_native_ledger_passes(self):
        self.native_run(lambda reports: None, 'PASS')

    def test_gate_claims_exit_but_lookup_was_denied(self):
        def forge(reports):
            g = reports[1]['gate']
            g['process_a_state'], g['process_a_lookup'], g['process_a_error'] = 'EXITED', None, DENIED
        result = self.native_run(forge, 'INCONCLUSIVE')
        self.assertIn('gate: process A lookup recorded an error', ' '.join(result['reasons']))

    def test_apply_claims_exit_but_lookup_was_denied(self):
        def forge(reports):
            reports[2]['process_a_now'] = {'state': 'EXITED', 'lookup': None, 'error': DENIED}
        result = self.native_run(forge, 'INCONCLUSIVE')
        self.assertIn('apply: process A lookup recorded an error', ' '.join(result['reasons']))

    def test_gate_lookup_records_omitted(self):
        def forge(reports):
            reports[1]['gate'].pop('process_a_lookup')
            reports[1]['gate'].pop('process_a_error')
        result = self.native_run(forge, 'INCONCLUSIVE')
        self.assertIn('gate: process A lookup evidence missing', ' '.join(result['reasons']))

    def test_each_state_requires_its_own_lookup_evidence(self):
        e, ns, entries = self.complete()
        native = native_ledger(entries)
        a = native[0]['report']['process']

        def verdict(fn):
            copy = json.loads(json.dumps(native))
            fn(copy[1]['report']['gate'], copy[2]['report'])
            return ns['verdict'](copy, True, True, e.config, e.pose_bytes(), False)
        self.assertEqual(verdict(lambda g, r: None)[0], 'PASS')
        row = lambda **k: dict({'pid': a['pid'], 'creation_filetime': a['creation_filetime'], 'running': False,
                                'image': 'C:\\SFM\\sfm.exe'}, **k)
        accepted = [
            lambda g, r: g.update({'process_a_state': 'ABSENT', 'process_a_lookup': None, 'process_a_error': None}),
            lambda g, r: r.__setitem__('process_a_now', {'state': 'PID_REUSED', 'error': None,
                                                         'lookup': row(creation_filetime=a['creation_filetime'] + 9,
                                                                       running=True)}),
            lambda g, r: g.__setitem__('process_a_lookup', row(exit_code=0)),
        ]
        for fn in accepted:
            self.assertEqual(verdict(fn)[0], 'PASS', verdict(fn)[1])
        refused = [
            lambda g, r: g.update({'process_a_state': 'ABSENT', 'process_a_lookup': row()}),
            lambda g, r: g.__setitem__('process_a_lookup', row(running=True)),
            lambda g, r: g.__setitem__('process_a_lookup', row(creation_filetime=a['creation_filetime'] + 1)),
            lambda g, r: g.__setitem__('process_a_lookup', row(pid=a['pid'] + 1)),
            lambda g, r: g.__setitem__('process_a_lookup', row(running=0)),
            lambda g, r: g.__setitem__('process_a_lookup', row(creation_filetime=True)),
            lambda g, r: g.__setitem__('process_a_lookup', row(exit_code=259)),
            lambda g, r: g.__setitem__('process_a_lookup', None),
            lambda g, r: g.__setitem__('process_a_error', 'access denied'),
            lambda g, r: g.update({'process_a_state': 'PID_REUSED', 'process_a_lookup': row()}),
            lambda g, r: g.update({'process_a_state': 'UNKNOWN'}),
            lambda g, r: r.__setitem__('process_a_now', {'state': 'ABSENT', 'lookup': None}),
            lambda g, r: r.__setitem__('process_a_now', {'state': 'EXITED', 'lookup': row(running=True),
                                                         'error': None}),
            lambda g, r: r['process_a_now'].__setitem__('extra', 1),
            lambda g, r: r.pop('process_a_now'),
        ]
        for i, fn in enumerate(refused):
            v, reasons, _ = verdict(fn)
            self.assertEqual(v, 'INCONCLUSIVE', (i, reasons))


def main(results_path=None):
    if results_path is not None and not results_path.endswith('.json'):
        raise SystemExit('usage: python test_f01w2.py [RESULTS_JSON]  (the results path must end in .json)')
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for case in CASES:
        suite.addTests(loader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {'python': sys.version, 'tests': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'native_execution': False,
               'cases': dict((c.__name__, loader.loadTestsFromTestCase(c).countTestCases()) for c in CASES)}
    if results_path:
        with open(results_path, 'wb') as f:
            f.write(json.dumps(summary, indent=1, sort_keys=True).encode('ascii'))
    return result.wasSuccessful()


CASES = (TestProcedure, TestPoseFormat, TestPublication, TestCaptureIntegrity, TestProcessSeparation, TestPreflight,
         TestSourceIndependence, TestIndependentPlans, TestTransactions, TestFinalizer, TestPrepare,
         TestF01SkeletalEvidence, TestF02EvidenceFinalization, TestF03UndoEvidence, TestF04Preservation,
         TestF05ProcessQueries, TestCorrectionAPostMutationStop, TestCorrectionBLookupEvidence)

if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
