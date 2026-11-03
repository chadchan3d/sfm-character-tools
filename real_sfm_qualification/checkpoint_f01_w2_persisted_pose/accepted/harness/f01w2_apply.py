# -*- coding: ascii -*-
"""F-01 W2 process B: independent reapplication of the saved left-arm pose
after a genuine SFM restart, in the application disposable copy, at shot10
movie frame 10.

Submitted from the Script Editor with APPLY_STEP.txt; each submission runs the
single due step (APPLY, RETIME, UNDO, REDO, FINAL_UNDO).

Source independence: every pose value, goal and expected skeletal result comes
only from one immutable snapshot of the pose file's bytes and from fresh
destination observations. Nothing here resolves, reads or evaluates the source
shot. The document-wide writer inventory reads binding and graph metadata only.
From the capture report only its status, completeness, process identity and
the published pose hash are used.

Native scene mutations, and nowhere else: CDmeVector3LogLayer.SetKeyValue /
CDmeQuaternionLogLayer.SetKeyValue on the three existing write channels;
IDataModel.StartUndo / FinishUndo / AbortUndoableOperation / Undo / Redo of
this experiment's own nonce-described transactions. Python 2.7 and 3 syntax.
"""
import os
import binascii

BASE = os.path.dirname(os.path.abspath(__file__))


def load_core():
    path = os.path.join(BASE, 'f01w2_core.py')
    ns = {'__name__': 'f01w2_core', '__file__': path}
    with open(path, 'rb') as f:
        exec(compile(f.read(), path, 'exec', 0, True), ns)
    return ns


C = load_core()
Stop, Fail, Unresolved = C['Stop'], C['Fail'], C['Unresolved']
roundtrip, differences = C['roundtrip'], C['differences']


def check_authored(label, now, expected):
    diffs = differences(now, expected)
    if diffs:
        raise Stop('Unexpected authored state (%s): %s' % (label, diffs[:16]))


def observed_now(Lx, label, mutated):
    """The operator/constraint attributes outside the write set. Unreadable after a mutation is STOP (F-04)."""
    try:
        return roundtrip(C['capture_observed'](Lx))
    except Unresolved as exc:
        if mutated:
            raise Stop('Preservation evidence unreadable %s: %s; STOP: no further native operation' % (label, exc))
        raise


def preservation_gate(step, Lx, baseline_observed, label, mutated):
    """F-04: record, then refuse, any unclassified operator/constraint change before the next native history
    operation (including after an Owner-controlled delay). No compensating Undo, Redo or write is attempted."""
    changes = differences(observed_now(Lx, label, mutated), baseline_observed)
    step.event('preservation-check', label=label, observed_changes=changes[:64])
    if changes:
        raise Stop('Unclassified operator/constraint attribute changes %s: %s; STOP: no further native operation' %
                   (label, changes[:8]))


def same_history(expected):
    return lambda u: ['history differs from the expected record: %s' % C['history_changes'](u, expected)] \
        if C['history_changes'](u, expected) else []


def owned_undo(descs):
    return lambda u: [] if u['can_undo'] is True and u['undo_desc'] == descs['commit_undo'] else \
        ['the owned apply is not the top Undo entry']


def owned_redo(descs):
    return lambda u: [] if u['can_redo'] is True and u['redo_desc'] == descs['commit_redo'] else \
        ['the owned apply is not the top Redo entry']


def history_boundary(step, dm, label, expect):
    """F-03: at a callback boundary after the first native history operation, the required history must be
    readable and as the experiment left it; otherwise STOP (recovery/ownership unverified)."""
    u = C['undo_state'](dm)
    step.event('history-boundary', label=label, undo=u)
    C['require_history'](u, label, True)
    problems = expect(u)
    if problems:
        raise Stop('Recovery/ownership unverified %s: %s' % (label, problems))
    return u


def capture_evidence(entries):
    """The only facts process B takes from process A's report: its status,
    completeness, process identity and the published pose hash. The captured
    pose values in that report are never read here."""
    if len(entries) < 2:
        raise Stop('The ledger does not hold a capture and a process gate')
    cap, gate = entries[0]['report'], entries[1]['report']
    if cap.get('step') != 'CAPTURE' or cap.get('status') != 'CAPTURE_COMPLETE_PENDING_CLOSE' or \
            cap.get('evidence_complete') is not True:
        raise Stop('No complete capture-success record precedes this application')
    publication = cap.get('publication') or {}
    sha = publication.get('pose_sha256')
    if not isinstance(sha, (C['text_type'], str)) or len(sha) != 64:
        raise Stop('The capture record does not bind a pose SHA-256')
    if gate.get('step') != 'PROCESS_GATE' or gate.get('status') != 'CONTINUE' or \
            gate.get('evidence_complete') is not True:
        raise Stop('No complete process gate precedes this application')
    return {'pose_sha256': sha, 'pose_path': publication.get('pose_path'), 'process_a': cap.get('process') or {},
            'gate': gate.get('gate') or {}}


def process_separation(evidence, process_b, provider, report):
    """Process A exited (verified by the gate with SFM closed and again here)
    before process B was created. The strict lookup of process A is recorded
    first; an unresolved lookup is INCONCLUSIVE, never an exit (F-05)."""
    a, gate = evidence['process_a'], evidence['gate']
    now = C['recorded_process_state'](provider, a)
    report['process_a_now'] = now
    if now['state'] == 'UNKNOWN':
        raise Unresolved('Process A state could not be established (%s); separation unproven' % now['error'])
    checks = {'b_is_not_a': not C['same_process'](a, process_b),
              'same_provider': a.get('provider') == process_b.get('provider') == gate.get('provider'),
              'gate_saw_a_exited': gate.get('process_a_running') is False and
              gate.get('process_a_state') in C['EXITED_STATES'],
              'gate_saw_no_sfm': gate.get('sfm_processes') == [],
              'a_created_before_gate': isinstance(a.get('creation_filetime'), C['integer_types']) and
              isinstance(gate.get('checked_filetime'), C['integer_types']) and
              a['creation_filetime'] < gate['checked_filetime'],
              'b_created_after_gate': isinstance(process_b.get('creation_filetime'), C['integer_types']) and
              isinstance(gate.get('checked_filetime'), C['integer_types']) and
              process_b['creation_filetime'] > gate['checked_filetime'],
              'a_not_running_now': now['state'] in C['EXITED_STATES']}
    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise Stop('Process separation not established: %s' % failed)
    return checks


def load_snapshot(config, evidence):
    """Read the complete pose file exactly once; everything after uses only
    these bytes."""
    if C['normalized'](evidence['pose_path'] or '') != C['normalized'](config['pose_path']):
        raise Stop('The capture record names a different pose path')
    raw = C['read_bytes'](config['pose_path'])
    sha = C['hashlib'].sha256(raw).hexdigest()
    if sha != evidence['pose_sha256']:
        raise Stop('Pose file bytes do not match the capture record (%s != %s)' % (sha, evidence['pose_sha256']))
    try:
        pose = C['parse_pose'](raw)
    except C['PoseFormatError'] as exc:
        raise Stop('Pose file rejected: %s' % exc)
    return raw, sha, pose


def destination(sfmApp, vs, config):
    L = C['resolve'](sfmApp, vs, config, 'destination')
    return L, roundtrip(C['capture_authored'](L)), roundtrip(C['capture_observed'](L)), \
        roundtrip(C['capture_skeleton'](L, vs))


def build_plan(config, pose, L, skel, targets, reference):
    tol = config['tolerances']
    a = C['plan_quaternion'](pose, skel, reference)
    b = C['plan_matrix'](pose, skel, reference)
    checks = C['cross_check'](a, b, tol)
    if not checks['agree']:
        raise Stop('The two independent plan implementations disagree: %r' % checks)
    guard = C['shoulder_guard'](pose, skel, tol)
    write = dict((n, a[n]) for n in ('Hand_l_p', 'Hand_l_o', 'Elbow_l_p'))
    return {'write_float32': write, 'independent_float32': dict((n, b[n]) for n in write),
            'goals_double': a['double'], 'cross_check': checks, 'collar_mapping_error': guard,
            'hand_orientation_sign': {'reference': reference, 'negated': a['negated']},
            'oracle': C['oracle_from_pose'](pose, skel),
            'brackets': dict((n, t['bracket']) for n, t in targets.items()),
            'write_channels': dict((n, {'channel_handle': C['handle'](t['channel']),
                                        'layer_handle': C['handle'](t['layer']),
                                        'indices': t['bracket']['indices']}) for n, t in targets.items()),
            'saved_hand_target_residual': pose['diagnostics']['hand_target_residual']}


def step_apply(step, sfmApp, vs, config, entries, provider):
    """Snapshot, fresh preflight, independent plan; then, after the invocation
    returns: abort check, evaluated check, committed six-key apply and one idle
    observation."""
    tol = config['tolerances']
    evidence = capture_evidence(entries)
    step.report['process_separation'] = process_separation(evidence, step.report['process'], provider, step.report)
    raw, sha, pose = load_snapshot(config, evidence)
    step.report['pose_snapshot'] = {'sha256': sha, 'bytes': len(raw), 'payload': pose}
    if pose['model'] != config['model'] or pose['animation_set'] != config['animation_set']:
        raise Stop('The pose was captured for a different model or animation set')
    L, auth, observed, skel = destination(sfmApp, vs, config)
    step.report['context'] = L['token']
    hold = C['hold_state'](skel, config, 'destination')
    targets = C['write_targets'](L, config)
    bindings = dict(targets)
    for spec in C['OBSERVED_CHANNELS']:
        bindings[spec[0]] = C['channel_binding'](L, spec)
    index = C['writer_index'](sfmApp)
    C['check_writers'](L, targets, index)
    live = C['descriptor'](L, skel, auth, bindings, tol)
    compat = C['compare_descriptor'](pose['compatibility'], live, tol)
    hand_o = targets['Hand_l_o']
    reference = C['readback'](hand_o['layer'], hand_o['bracket']['indices'][0], 'quaternion')
    plan = build_plan(config, pose, L, skel, targets, reference)
    dm = vs.g_pDataModel
    undo0 = C['undo_state'](dm)
    step.report['undo_preflight'] = undo0
    C['require_history'](undo0, 'at preflight', False)
    if undo0['enabled'] is not True:
        raise Stop('Native Undo is not enabled')
    for name, t in targets.items():
        C['native_value'](vs, t['kind'], plan['write_float32'][name])
    nonce = binascii.hexlify(os.urandom(6)).decode('ascii')
    plan['nonce'] = nonce
    plan['pose_sha256'] = sha
    plan['descs'] = {'abort_undo': 'F01W2 abort check %s' % nonce, 'abort_redo': 'F01W2 abort check redo %s' % nonce,
                     'commit_undo': 'F01W2 pose apply %s' % nonce, 'commit_redo': 'F01W2 pose apply redo %s' % nonce}
    step.report['destination_baseline'] = {'authored': auth, 'observed': observed, 'skeleton': skel,
                                           'context': L['token'], 'authored_sha256': C['canonical_sha'](auth),
                                           'hold': hold, 'binding_identity': roundtrip(C['binding_identity'](L))}
    step.report['plan'] = roundtrip(plan)
    plan = step.report['plan']
    committed = C['expected_committed'](auth, plan)
    step.report['preflight'] = {'compatibility': compat, 'live_descriptor': roundtrip(live),
                                'writers': C['writer_summary'](index), 'undo_state': undo0,
                                'coverage': {'channels': len(auth['channels']), 'keys': auth['keys'],
                                             'layer_types': C['layer_types'](auth)},
                                'element_undo_enabled': C['element_undo'](dm, targets)}
    step.event('preflight-complete')
    history = {}

    def entry(label):
        Lx = C['resolve'](sfmApp, vs, config, 'destination')
        if Lx['token'] != L['token']:
            raise Stop('Context changed before %s' % label)
        tx = C['write_targets'](Lx, config)
        for n in tx:
            if C['handle'](tx[n]['channel']) != C['handle'](targets[n]['channel']) or \
                    C['handle'](tx[n]['layer']) != C['handle'](targets[n]['layer']) or \
                    tx[n]['bracket'] != targets[n]['bracket']:
                raise Stop('Write target %s changed before %s' % (n, label))
        return Lx, tx

    def abort_check():
        Lx, tx = entry('abort check')
        check_authored('destination before abort check', roundtrip(C['capture_authored'](Lx)), auth)
        preservation_gate(step, Lx, observed, 'before the abort check', False)
        before = C['undo_state'](dm)
        step.report['undo_before_abort_check'] = before
        C['require_history'](before, 'before the abort check', False)
        if before['enabled'] is not True:
            raise Stop('Native Undo is not enabled')
        history['before'] = before
        name = 'Hand_l_p'
        index_ = tx[name]['bracket']['indices'][0]
        record, items, failure = None, None, None
        dm.StartUndo(C['native_name'](plan['descs']['abort_undo']), C['native_name'](plan['descs']['abort_redo']))
        try:
            record = C['write_key'](vs, tx[name], index_, plan['write_float32'][name])
            record['channel'] = name
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
        after = C['undo_state'](dm)
        restored = C['recovery_capture'](Lx)
        diffs = differences(restored, auth)
        readable = not C['history_problems'](after)
        changed = C['history_changes'](after, before) if readable else None
        step.event('abort-check', write=record, write_failure=repr(failure) if failure else None,
                   items_added_recorded_only=items, undo_before=before, undo_after=after,
                   authored_restored=not diffs, differences=diffs[:32],
                   history_restored=readable and not changed)
        C['require_history'](after, 'after AbortUndoableOperation', True)
        if diffs:
            raise Stop('Abort did not restore the authored state exactly: %s' % diffs[:16])
        if failure is not None:
            raise Stop('The abort-check write raised %r (authored state restored)' % (failure,))
        if not (record['exact'] and record['count_unchanged'] and record['time_unchanged']):
            raise Stop('The abort-check write did not take effect as requested; the abort test is not meaningful')
        if after.get('undo_desc') == plan['descs']['abort_undo'] or after.get('redo_desc') == \
                plan['descs']['abort_redo']:
            raise Stop('The aborted transaction appears in the Undo history; ownership uncertain')
        if changed:
            raise Stop('Recovery/ownership unverified: AbortUndoableOperation changed the required Undo/Redo '
                       'history %s; history is not cleared or repaired' % changed)
        C['schedule'](C['guarded'](step, abort_evaluated, recovery=True))

    def abort_evaluated():
        Lx, tx = entry('abort evaluated check')
        history_boundary(step, dm, 'at the abort evaluated check', same_history(history['before']))
        sk = roundtrip(C['capture_skeleton'](Lx, vs))
        result = C['classify'](sk, skel, plan, 'BASELINE', tol)
        step.event('abort-evaluated', observation=result,
                   interpretation='Recorded only: unchanged evaluated outputs after the abort do not prove '
                                  'evaluated rollback; committed Undo provides that evidence.')
        if not result['correct']:
            raise Stop('After the aborted write and one idle opportunity the evaluated state is not the baseline')
        C['schedule'](C['guarded'](step, commit, mutated=True))      # after the aborted test write

    def commit():
        Lx, tx = entry('commit')
        check_authored('destination before commit', roundtrip(C['capture_authored'](Lx)), auth)
        preservation_gate(step, Lx, observed, 'before the commit', True)
        before = history_boundary(step, dm, 'before the commit', same_history(history['before']))
        writes = []
        open_txn = [False]
        finished = False
        try:
            dm.StartUndo(C['native_name'](plan['descs']['commit_undo']),
                         C['native_name'](plan['descs']['commit_redo']))
            open_txn[0] = True
            for name, _, _, _, _, _, _ in C['WRITE_CHANNELS']:
                for i in tx[name]['bracket']['indices']:
                    r = C['write_key'](vs, tx[name], i, plan['write_float32'][name])
                    r['channel'] = name
                    writes.append(r)
                    if not (r['exact'] and r['count_unchanged'] and r['time_unchanged']):
                        raise Stop('float32 readback mismatch on %s key %d' % (name, i))
            diffs = differences(roundtrip(C['capture_authored'](Lx)), committed)
            if diffs:
                raise Stop('Authored state after the six writes is not exactly the planned state: %s' % diffs[:16])
            clocks = roundtrip(C['log_values_at_clocks'](vs, tx, skel['arm_channels']))
            for name in clocks:
                for clock in ('current', 'nominal'):
                    got, want = clocks[name][clock], plan['write_float32'][name]
                    if len(want) == 4:
                        bad = C['angle_deg'](got, want) > tol['log_evaluation_angle_degrees']
                    else:
                        bad = C['distance'](got, want) > tol['log_evaluation_position']
                    if bad:
                        raise Stop('Native log evaluation of %s at the %s clock is not the written value' %
                                   (name, clock))
            dm.FinishUndo()
            open_txn[0] = False
            finished = True
        except Exception as commit_exc:
            if open_txn[0]:
                open_txn[0] = False
                failure = repr(commit_exc)
                try:
                    dm.AbortUndoableOperation()
                except Exception as exc:
                    step.event('commit-abort-failed', writes=writes, error=repr(exc), commit_failure=failure,
                               undo_before=before)
                    raise Stop('Commit failed and AbortUndoableOperation raised; recovery unverified '
                               '(commit failure: %s)' % failure)
                after = C['undo_state'](dm)
                try:
                    restored = C['recovery_capture'](Lx)
                except Stop as exc:
                    step.event('commit-aborted', writes=writes, commit_failure=failure, recovery_error=str(exc),
                               undo_before=before, undo_after=after)
                    raise Stop('%s (commit failure: %s)' % (exc, failure))
                diffs = differences(restored, auth)
                readable = not C['history_problems'](after)
                changed = C['history_changes'](after, before) if readable else None
                step.event('commit-aborted', writes=writes, commit_failure=failure, authored_restored=not diffs,
                           differences=diffs[:32], undo_before=before, undo_after=after,
                           history_restored=readable and not changed)
                if diffs:
                    raise Stop('Commit failed and the abort did not restore the authored state; recovery '
                               'unverified (commit failure: %s)' % failure)
                C['require_history'](after, 'after the failed commit was aborted (commit failure: %s)' % failure,
                                     True)
                if changed or after.get('undo_desc') == plan['descs']['commit_undo'] or \
                        after.get('redo_desc') == plan['descs']['commit_redo']:
                    raise Stop('Commit failed; the abort restored the authored state but not the required '
                               'Undo/Redo history %s; recovery/ownership unverified (commit failure: %s)' %
                               (changed, failure))
            raise
        after = C['undo_state'](dm)
        step.event('commit', writes=writes, undo_before=before, undo_after=after, finished=finished)
        C['require_history'](after, 'after FinishUndo', True)
        if after.get('undo_desc') != plan['descs']['commit_undo'] or after.get('can_undo') is not True:
            raise Stop('After FinishUndo the top Undo entry is not this transaction; ownership uncertain')
        check_authored('destination after commit', roundtrip(C['capture_authored'](Lx)), committed)
        step.report['commit_undo_state'] = after
        C['schedule'](C['guarded'](step, observe_idle, mutated=True))

    def observe_idle():
        Lx, tx = entry('idle observation')
        history_boundary(step, dm, 'at the idle observation', owned_undo(plan['descs']))
        check_authored('destination at idle observation', roundtrip(C['capture_authored'](Lx)), committed)
        sk = roundtrip(C['capture_skeleton'](Lx, vs))
        result = C['classify'](sk, skel, plan, 'TRANSFERRED', tol)
        step.report['observation'] = result
        step.report['observed_changes'] = differences(observed_now(Lx, 'at the idle observation', True), observed)
        finish_observation(step, 'committed', result, config)

    C['schedule'](C['guarded'](step, abort_check))
    return 'ASYNC'


FOLLOWING = {'committed': ('UNDO', 'undone'), 'undone': ('REDO', 'redone'), 'redone': ('FINAL_UNDO', 'final')}


def continue_after(step, stage, config):
    if stage == 'final':
        step.report['experiment_complete'] = True
        step.finish('COMPLETE_PENDING_CLOSE')
        return
    name, next_stage = FOLLOWING[stage]
    step.finish('CONTINUE', C['nxt'](name, 'destination', next_stage, config))


def finish_observation(step, stage, result, config):
    """F-04 preservation gate before accepting an observation or offering a retime: unclassified
    operator/constraint changes are STOP; an idle observation that already shows a skeletal preservation failure
    is FAIL and is not sent to retime (F-01). Either way no next action is emitted."""
    if step.report.get('observed_changes') != []:
        raise Stop('Unclassified operator/constraint attribute changes at the %s observation: %s; STOP: no further '
                   'native operation' % (stage, (step.report.get('observed_changes') or [])[:8]))
    if result['correct']:
        step.report['propagation'] = 'IDLE'
        continue_after(step, stage, config)
        return
    if result['unrelated_change_count']:
        raise Fail('Preservation failed at the %s idle observation (%s); retiming is not offered' %
                   (stage, result['unrelated_changes'][:8]))
    step.report['propagation'] = 'NOT_AT_IDLE'
    step.report['idle_result'] = 'PREVIOUS_STATE_REMAINS' if result['previous_state_remains'] else \
        'INCORRECT_OR_PARTIAL'
    step.finish('CONTINUE', C['nxt']('RETIME', 'destination', stage, config))


def apply_record(entries):
    rows = [e['report'] for e in entries if e['report'].get('step') == 'APPLY']
    if len(rows) != 1:
        raise Stop('Exactly one APPLY report is required')
    return rows[0]


def expected_authored(stage, base):
    if C['STAGE_EXPECT'][stage] == 'TRANSFERRED':
        return C['expected_committed'](base['destination_baseline']['authored'], base['plan'])
    return base['destination_baseline']['authored']


def common_destination(step, sfmApp, vs, config, base, stage):
    if not C['same_process'](step.report['process'], base['process']):
        raise Stop('This step runs in a different process from the APPLY step')
    L = C['resolve'](sfmApp, vs, config, 'destination')
    if L['token']['pid'] != base['destination_baseline']['context']['pid'] or \
            L['token']['document'] != base['destination_baseline']['context']['document']:
        raise Stop('Process or document changed since the APPLY step')
    if differences(roundtrip(C['binding_identity'](L)), base['destination_baseline']['binding_identity']):
        raise Stop('Destination bindings changed since the APPLY step')
    step.report['context'] = L['token']
    check_authored('destination (%s)' % stage, roundtrip(C['capture_authored'](L)), expected_authored(stage, base))
    return L


def expected_history(stage, plan):
    """Where the owned apply must be once a stage's native operation is done."""
    return owned_undo(plan['descs']) if C['STAGE_EXPECT'][stage] == 'TRANSFERRED' else owned_redo(plan['descs'])


def step_retime(step, sfmApp, vs, config, entries, provider):
    stage = step.due['stage']
    base = apply_record(entries)
    L = common_destination(step, sfmApp, vs, config, base, stage)
    history_boundary(step, vs.g_pDataModel, 'at the %s retime observation' % stage,
                     expected_history(stage, base['plan']))
    sk = roundtrip(C['capture_skeleton'](L, vs))
    result = C['classify'](sk, base['destination_baseline']['skeleton'], base['plan'], C['STAGE_EXPECT'][stage],
                           config['tolerances'])
    step.report['observation'] = result
    step.report['observed_changes'] = differences(observed_now(L, 'at the %s retime observation' % stage, True),
                                                  base['destination_baseline']['observed'])
    if step.report['observed_changes']:
        raise Stop('Unclassified operator/constraint attribute changes at the %s retime observation: %s; STOP: no '
                   'further native operation' % (stage, step.report['observed_changes'][:8]))
    if not result['correct']:
        raise Fail('Still not the expected %s state after the prescribed retime (%s)' %
                   (C['STAGE_EXPECT'][stage], result['state']))
    step.report['propagation'] = 'RETIMING_DEPENDENT'
    continue_after(step, stage, config)


def step_history(step, sfmApp, vs, config, entries, provider, action):
    """UNDO, REDO or FINAL_UNDO of the owned commit, then one idle observation."""
    stage = step.due['stage']
    base = apply_record(entries)
    plan = base['plan']
    dm = vs.g_pDataModel
    before_stage = {'undone': 'committed', 'redone': 'undone', 'final': 'redone'}[stage]
    L = common_destination(step, sfmApp, vs, config, base, before_stage)
    token = L['token']

    def entry(label):
        Lx = C['resolve'](sfmApp, vs, config, 'destination')
        if Lx['token'] != token:
            raise Stop('Context changed before %s' % label)
        return Lx

    def perform():
        Lx = entry(action)
        check_authored('destination before %s' % action, roundtrip(C['capture_authored'](Lx)),
                       expected_authored(before_stage, base))
        # F-04: the preserved state is rechecked immediately before the native history operation, so a change
        # after the previous accepted observation (an Owner-controlled delay) cannot escape the boundary.
        preservation_gate(step, Lx, base['destination_baseline']['observed'], 'before %s' % action, True)
        sk = roundtrip(C['capture_skeleton'](Lx, vs))
        held = C['classify'](sk, base['destination_baseline']['skeleton'], plan, C['STAGE_EXPECT'][before_stage],
                             config['tolerances'])
        step.event('preservation-check', label='skeleton before %s' % action,
                   unrelated_changes=held['unrelated_changes'])
        if held['unrelated_change_count']:
            raise Stop('Skeletal preservation changed before %s: %s; STOP: no further native operation' %
                       (action, held['unrelated_changes'][:8]))
        before = C['undo_state'](dm)
        step.report['undo_before_%s' % action] = before
        C['require_history'](before, 'before %s' % action, True)
        if action == 'redo':
            if before.get('can_redo') is not True or before.get('redo_desc') != plan['descs']['commit_redo']:
                raise Stop('The top Redo entry is not the owned apply; ownership uncertain')
            dm.Redo()
        else:
            if before.get('can_undo') is not True or before.get('undo_desc') != plan['descs']['commit_undo']:
                raise Stop('The top Undo entry is not the owned apply; ownership uncertain')
            dm.Undo()
        after = C['undo_state'](dm)
        step.event(action, undo_before=before, undo_after=after)
        C['require_history'](after, 'after %s' % action, True)
        now = C['recovery_capture'](Lx)
        diffs = differences(now, expected_authored(stage, base))
        if diffs:
            raise Stop('%s did not produce the exact expected authored state: %s' % (action, diffs[:16]))
        if action == 'redo':
            owned = after.get('can_undo') is True and after.get('undo_desc') == plan['descs']['commit_undo']
        else:
            owned = after.get('can_redo') is True and after.get('redo_desc') == plan['descs']['commit_redo']
        if not owned:
            raise Stop('After %s the owned entry is not where it must be; ownership uncertain' % action)
        C['schedule'](C['guarded'](step, observe, recovery=True))

    def observe():
        Lx = entry('idle observation')
        history_boundary(step, dm, 'at the %s idle observation' % stage, expected_history(stage, plan))
        check_authored('destination at idle observation', roundtrip(C['capture_authored'](Lx)),
                       expected_authored(stage, base))
        sk = roundtrip(C['capture_skeleton'](Lx, vs))
        result = C['classify'](sk, base['destination_baseline']['skeleton'], plan, C['STAGE_EXPECT'][stage],
                               config['tolerances'])
        step.report['observation'] = result
        step.report['observed_changes'] = differences(observed_now(Lx, 'at the %s idle observation' % stage, True),
                                                      base['destination_baseline']['observed'])
        finish_observation(step, stage, result, config)

    C['schedule'](C['guarded'](step, perform, mutated=True))       # this step runs after the commit
    return 'ASYNC'


def run_step(step, sfmApp, vs, config, entries, provider):
    name = step.due['step']
    if name == 'APPLY':
        return step_apply(step, sfmApp, vs, config, entries, provider)
    if name == 'RETIME':
        return step_retime(step, sfmApp, vs, config, entries, provider)
    if name in ('UNDO', 'FINAL_UNDO'):
        return step_history(step, sfmApp, vs, config, entries, provider, 'undo')
    if name == 'REDO':
        return step_history(step, sfmApp, vs, config, entries, provider, 'redo')
    raise Stop('Unknown step ' + name)


if __name__ == '__f01w2_owner_step__':
    C['run_entry'](C['PROCESS_B_STEPS'], run_step, 'APPLY')
