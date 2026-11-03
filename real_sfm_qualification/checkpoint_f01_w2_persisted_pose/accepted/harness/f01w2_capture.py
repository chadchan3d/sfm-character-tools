# -*- coding: ascii -*-
"""F-01 W2 process A: read-only capture of one left-arm pose and its exclusive
publication as <run dir>/poses/left_arm_pose.f01w2.json.

Submitted once from the Script Editor with CAPTURE_STEP.txt, in the capture
disposable copy, at shot15 movie frame 5. Read-only: no SetKeyValue, Undo
command, save, forced evaluation, playhead change, control setter or graph
mutation. The only files written are this step's report, one uniquely named
temporary file and the published pose. Python 2.7 (SFM) and 3 syntax.
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
Stop = C['Stop']


def snapshot(sfmApp, vs, config):
    """Resolve the source place and read everything the capture depends on."""
    L = C['resolve'](sfmApp, vs, config, 'source')
    auth = C['roundtrip'](C['capture_authored'](L))
    observed = C['roundtrip'](C['capture_observed'](L))
    skel = C['roundtrip'](C['capture_skeleton'](L, vs))
    bindings = {}
    for spec in C['WRITE_CHANNELS'] + C['OBSERVED_CHANNELS']:
        bindings[spec[0]] = C['channel_binding'](L, spec)
    return {'L': L, 'authored': auth, 'observed': observed, 'skeleton': skel, 'bindings': bindings,
            'identity': C['roundtrip'](C['binding_identity'](L)), 'undo': C['undo_state'](vs.g_pDataModel)}


def capture(step, sfmApp, vs, config, entries, provider):
    if entries:
        raise Stop('The ledger is not empty; a capture has already been attempted in this run')
    tol = config['tolerances']
    first = snapshot(sfmApp, vs, config)
    L = first['L']
    step.report['context'] = L['token']
    step.report['undo_at_start'] = first['undo']
    # F-03: readable required history before anything is built or published (else INCONCLUSIVE).
    C['require_history'](first['undo'], 'at capture start', False)
    hold = C['hold_state'](first['skeleton'], config, 'source')
    writes = dict((n, first['bindings'][n]) for n, _, _, _, _, _, _ in C['WRITE_CHANNELS'])
    index = C['writer_index'](sfmApp)
    C['check_writers'](L, writes, index)
    desc = C['descriptor'](L, first['skeleton'], first['authored'], first['bindings'], tol)
    payload = C['build_payload'](config, L, first['skeleton'], desc)
    data = C['serialize_pose'](payload)
    parsed = C['parse_pose'](data)
    if C['differences'](parsed, payload):
        raise Stop('Serialized pose does not parse back to the constructed payload')
    step.event('payload-built', bytes=len(data))
    # Completion gate: the same process, document, shot, playhead, bindings,
    # authored state, evaluated state and Undo history as at the start.
    second = snapshot(sfmApp, vs, config)
    step.report['undo_at_completion'] = second['undo']
    C['require_history'](second['undo'], 'at capture completion', False)
    checks = {'context': second['L']['token'] == L['token'],
              'process': C['same_process'](C['process_evidence'](provider), step.report['process']),
              'binding_identity': not C['differences'](second['identity'], first['identity']),
              'authored': not C['differences'](second['authored'], first['authored']),
              'observed': not C['differences'](second['observed'], first['observed']),
              'skeleton': not C['differences'](second['skeleton'], first['skeleton']),
              'undo_history': not C['differences'](C['roundtrip'](second['undo']), C['roundtrip'](first['undo']))}
    step.event('completion-gate', checks=checks)
    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise Stop('Capture-integrity gate failed: %s changed during the capture; nothing published' % failed)
    integrity_now = C['integrity'](config)
    if integrity_now != step.report['integrity_before']:
        raise Stop('A protected file, harness, config or CPM source changed during the capture; nothing published')
    nonce = binascii.hexlify(os.urandom(6)).decode('ascii')
    sha, temp = C['publish_pose'](config['pose_path'], data, nonce)
    if sha != C['hashlib'].sha256(data).hexdigest():
        raise Stop('Published pose hash differs from the validated payload')
    step.report['capture'] = {
        'source_baseline': {'authored_sha256': C['canonical_sha'](first['authored']),
                            'observed_sha256': C['canonical_sha'](first['observed']),
                            'skeleton': first['skeleton'], 'hold': hold, 'undo': first['undo'],
                            'undo_completion': second['undo'], 'binding_identity': first['identity']},
        'coverage': {'channels': len(first['authored']['channels']), 'keys': first['authored']['keys'],
                     'layer_types': C['layer_types'](first['authored'])},
        'writers': C['writer_summary'](index),
        'completion_gate': checks,
        'payload': payload}
    step.report['publication'] = {'pose_path': config['pose_path'], 'pose_sha256': sha, 'pose_bytes': len(data),
                                  'temporary_name': temp, 'method': 'no-replace-rename' if os.name == 'nt'
                                  else 'hard-link-no-replace'}
    step.finish('CAPTURE_COMPLETE_PENDING_CLOSE')


if __name__ == '__f01w2_owner_step__':
    C['run_entry'](C['PROCESS_A_STEPS'], capture, 'CAPTURE')
