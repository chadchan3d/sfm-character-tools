# -*- coding: ascii -*-
"""F-01 W1 finalization. Run with system Python AFTER the disposable session has
been closed without saving and SFM has exited:

    python -I finalize_f01w1.py <run dir>\\harness\\config.json

Read-only except for one new report, F01W1-FINAL.json (exclusive creation).
Verifies the protected files, the ledger hash chain and the harness/config
identity, then derives the overall verdict: PASS, FAIL, STOP or INCONCLUSIVE.
"""
import datetime
import hashlib
import json
import os
import re
import sys

REPORT_RE = re.compile(r'^F01W1-(\d{2})-([A-Z0-9_]+)\.json$')


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
        path = os.path.join(directory, name)
        with open(path, 'rb') as f:
            raw = f.read()
        if not raw:
            raise ValueError('Report %s is empty (a step did not finish)' % name)
        entries.append({'seq': int(m.group(1)), 'step': m.group(2), 'name': name,
                        'sha256': hashlib.sha256(raw).hexdigest(), 'report': json.loads(raw.decode('utf-8'))})
    for i, e in enumerate(entries):
        if e['seq'] != i + 1:
            raise ValueError('Ledger sequence is not contiguous')
        if i and e['report'].get('previous_report_sha256') != entries[i - 1]['sha256']:
            raise ValueError('Ledger hash chain is broken at ' + e['name'])
    return entries


STAGES = ('committed', 'undone', 'redone', 'final')
EXPECT = {'committed': 'TRANSFERRED', 'undone': 'BASELINE', 'redone': 'TRANSFERRED', 'final': 'BASELINE'}
OBSERVING_STEP = {'committed': 'TRANSFER', 'undone': 'UNDO', 'redone': 'REDO', 'final': 'FINAL_UNDO'}
WRITTEN = ['Hand_l_p', 'Hand_l_p', 'Hand_l_o', 'Hand_l_o', 'Elbow_l_p', 'Elbow_l_p']


def accepted(observation, expect):
    """An observation is accepted only from its own complete evidence."""
    o = observation or {}
    return bool(o.get('correct') is True and o.get('expected') == expect and o.get('state') == expect
                and o.get('inputs_ok') is True and o.get('input_errors') == []
                and o.get('unrelated_change_count') == 0 and o.get('unrelated_changes') == [])


BRACKET_TICKS = [30000, 70415]


def writes_consistent(plan, writes):
    """Each write's raw evidence, per channel, independently of its summary
    flags: requested value = the plan's float32 goal; readback = requested;
    exactly the channel's two planned bracket indices, at the bracket ticks,
    in order. A global tick set is never taken as per-channel coverage."""
    goals = plan.get('write_float32') or {}
    brackets = plan.get('brackets') or {}
    channels = plan.get('write_channels') or {}
    if sorted(goals) != sorted(set(WRITTEN)) or sorted(brackets) != sorted(goals):
        return False
    for name in sorted(goals):
        rows = [x for x in writes if x.get('channel') == name]
        bracket = brackets[name] or {}
        indices = bracket.get('indices')
        times = bracket.get('times') or []
        if (not isinstance(indices, list) or len(indices) != 2 or indices[1] != indices[0] + 1
                or any(i >= len(times) for i in indices) or [times[i] for i in indices] != BRACKET_TICKS
                or (channels.get(name) or {}).get('indices') != indices):
            return False
        if len(rows) != 2 or [x.get('index') for x in rows] != indices or [x.get('ticks') for x in rows] != BRACKET_TICKS:
            return False
        for x in rows:
            if not (x.get('exact') is True and x.get('count_unchanged') is True and x.get('time_unchanged') is True
                    and x.get('requested_float32') == goals[name] and x.get('readback') == goals[name]
                    and x.get('readback') == x.get('requested_float32')):
                return False
    return True


def events(report, name):
    return [x for x in report.get('events') or [] if x.get('event') == name]


def audit(entries):
    """Independent check of the complete ledger: step grammar, transaction and
    ownership evidence, every accepted observation (oracle, rig inputs,
    preservation) and evidence completeness. Returns (problems, propagation)."""
    problems, propagation = [], {}
    reports = [e['report'] for e in entries]
    names = [e['name'] for e in entries]
    if len(set(r.get('pid') for r in reports)) != 1:
        problems.append('steps ran in more than one process')
    for name, r in zip(names, reports):
        if r.get('evidence_complete') is not True:
            problems.append('%s: evidence not marked complete' % name)
        if r.get('observed_changes'):
            problems.append('%s: unclassified operator/constraint attribute changes %s' %
                            (name, r['observed_changes'][:8]))
        if not r.get('integrity_before') or r.get('integrity_before') != r.get('integrity_after'):
            problems.append('%s: integrity before/after missing or different' % name)
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

    first = take('SOURCE_BASELINE', None)
    if first is not None and not first.get('source_baseline'):
        problems.append('source baseline missing')
    plan = {}
    for stage in STAGES:
        r = take(OBSERVING_STEP[stage], stage)
        if r is None:
            break
        if stage == 'committed':
            plan = r.get('plan') or {}
            descs = plan.get('descs') or {}
            if not r.get('destination_baseline') or not descs:
                problems.append('transfer: destination baseline or plan missing')
            abort = events(r, 'abort-check')
            w = (abort[0].get('write') or {}) if len(abort) == 1 else {}
            goal = (plan.get('write_float32') or {}).get('Hand_l_p')
            if not (len(abort) == 1 and abort[0].get('authored_restored') is True
                    and abort[0].get('differences') == []
                    and not abort[0].get('write_failure') and w.get('exact') is True
                    and w.get('count_unchanged') is True and w.get('time_unchanged') is True
                    and goal is not None and w.get('requested_float32') == goal and w.get('readback') == goal):
                problems.append('transfer: abort check did not prove authored restoration')
            evaluated = events(r, 'abort-evaluated')
            if len(evaluated) != 1 or not accepted(evaluated[0].get('observation'), 'BASELINE'):
                problems.append('transfer: evaluated state after the abort not accepted as baseline')
            commit = events(r, 'commit')
            writes = (commit[0].get('writes') or []) if len(commit) == 1 else []
            if not (len(commit) == 1 and [x.get('channel') for x in writes] == WRITTEN
                    and writes_consistent(plan, writes)
                    and commit[0].get('finished') is True
                    and (commit[0].get('undo_after') or {}).get('undo_desc') == descs.get('commit_undo')):
                problems.append('transfer: committed writes or transaction ownership not proven')
        else:
            action = 'redo' if stage == 'redone' else 'undo'
            ev = events(r, action)
            before = (ev[0].get('undo_before') or {}) if len(ev) == 1 else {}
            descs = plan.get('descs') or {}
            if action == 'redo':
                owned = before.get('can_redo') is True and before.get('redo_desc') == descs.get('commit_redo')
            else:
                owned = before.get('can_undo') is True and before.get('undo_desc') == descs.get('commit_undo')
            if len(ev) != 1 or not owned or not descs:
                problems.append('%s: %s ownership precondition not proven' % (stage, action))
        if r.get('propagation') == 'IDLE':
            if not accepted(r.get('observation'), EXPECT[stage]):
                problems.append('%s: idle observation reported IDLE but is not accepted' % stage)
            propagation[stage] = 'IDLE'
        elif r.get('propagation') == 'NOT_AT_IDLE':
            if accepted(r.get('observation'), EXPECT[stage]):
                problems.append('%s: accepted idle observation was sent to retime' % stage)
            rt = take('RETIME', stage)
            if rt is not None:
                if rt.get('propagation') != 'RETIMING_DEPENDENT' or not accepted(rt.get('observation'),
                                                                                  EXPECT[stage]):
                    problems.append('%s: retime observation not accepted' % stage)
                propagation[stage] = 'RETIMING_DEPENDENT'
        else:
            problems.append('%s: no propagation classification' % stage)
        sr = take('SOURCE_RETURN', stage)
        if sr is not None and sr.get('source_evaluated_changes') != []:
            problems.append('%s: source return not proven unchanged' % stage)
        dr = take('DESTINATION_RETURN', stage)
        if dr is not None and not accepted(dr.get('observation'), EXPECT[stage]):
            problems.append('%s: destination return not accepted' % stage)
    if position[0] != len(reports):
        problems.append('unexpected additional steps after the final stage')
    for name, r in zip(names[:-1], reports[:-1]):
        if r.get('status') != 'CONTINUE':
            problems.append('%s: status %s before the end' % (name, r.get('status')))
    if reports and reports[-1].get('status') != 'COMPLETE_PENDING_CLOSE':
        problems.append('final step status is %s' % reports[-1].get('status'))
    return problems, propagation


def verdict(entries, protected_ok, identity_ok):
    if not protected_ok:
        return 'STOP', ['A protected file hash changed']
    if not identity_ok:
        return 'STOP', ['Harness, config or CPM source differs from the first step']
    if not entries:
        return 'INCONCLUSIVE', ['No step was run']
    statuses = [e['report'].get('status') for e in entries]
    for wanted in ('STOP', 'INCONCLUSIVE', 'FAIL'):
        if wanted in statuses:
            first = [e for e in entries if e['report'].get('status') == wanted][0]
            return wanted, ['%s at %s: %s' % (wanted, first['name'], first['report'].get('error'))]
    if statuses[-1] != 'COMPLETE_PENDING_CLOSE':
        return 'INCONCLUSIVE', ['The experiment did not reach its final step (last status %s)' % statuses[-1]]
    problems, _ = audit(entries)
    if problems:
        # A terminal status is not evidence: incomplete or contradictory evidence cannot PASS.
        return 'INCONCLUSIVE', problems
    return 'PASS', []


def propagation(entries):
    return audit(entries)[1]


def main(config_path):
    with open(config_path, 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
    directory = config['reports_dir']
    out_path = os.path.join(directory, 'F01W1-FINAL.json')
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    result = {'format': 'F01W1-final-v1', 'utc': datetime.datetime.utcnow().isoformat() + 'Z',
              'python': sys.version, 'verdict': 'INCONCLUSIVE'}
    try:
        protected = {}
        ok = True
        for key in ('original_session', 'r2_fixture', 'disposable_session'):
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
            current = {'harness': digest(os.path.join(harness_dir, 'f01w1_harness.py')),
                       'config': digest(config_path), 'cpm_source': digest(config['cpm_source'])}
            result['identity'] = current
            identity_ok = all(first.get(k) == v for k, v in current.items())
        result['verdict'], result['reasons'] = verdict(entries, ok, identity_ok)
        result['propagation'] = propagation(entries)
        if result['verdict'] == 'PASS':
            classes = set(result['propagation'].values())
            result['interpretation'] = (
                'Rig transfer demonstrated with idle propagation at every stage.' if classes == set(['IDLE']) else
                'Rig transfer demonstrated; at least one stage required retiming (not an immediately evaluated '
                'Apply mechanism).')
    except Exception as exc:
        result['verdict'] = 'STOP'
        result['reasons'] = ['Finalization error: %r' % (exc,)]
    with os.fdopen(fd, 'wb') as stream:
        stream.write(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=True).encode('ascii'))
    print('F01W1 FINAL: ' + result['verdict'])
    for reason in result.get('reasons') or []:
        print('  ' + reason)
    if result.get('propagation'):
        print('Propagation: %r' % (result['propagation'],))
    print('Report: ' + out_path)
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python -I finalize_f01w1.py <run dir>\\harness\\config.json')
        sys.exit(2)
    main(sys.argv[1])
