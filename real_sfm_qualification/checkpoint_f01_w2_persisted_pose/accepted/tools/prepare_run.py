# -*- coding: ascii -*-
"""F-01 W2 run preparation and process gate. Run with system Python while SFM is CLOSED.

    python -I prepare_run.py manifest <package root>
        Writes harness/CAPTURE_STEP.txt, harness/APPLY_STEP.txt and
        HARNESS_SHA256.json for a filled-in harness/config.json (exclusive
        creation; refuses if any exists). The resulting hashes are what the
        native-readiness reviewer approves.

    python -I prepare_run.py prepare <package root>
        Verifies the reviewed harness files against HARNESS_SHA256.json and the
        original session and R2 fixture hashes, then creates a NEW run
        directory (it must not exist) with two distinct, byte-identical
        disposable copies of the R2 fixture (capture copy, application copy),
        harness/, reports/ (empty) and poses/ (empty).

    python -I prepare_run.py gate <run dir>\\harness\\config.json
        After process A (capture) has exited WITHOUT saving and before process
        B is started: verifies the capture record, that process A (pid and
        creation time) is no longer running and that no sfm.exe is running,
        that both disposable copies are unsaved, and that the published pose
        still has the recorded hash. Then appends F01W2-02-PROCESS_GATE.json to
        the hash-chained ledger, recording the gate time.

Never opens, edits or writes the original session or the R2 fixture.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

HARNESS_FILES = ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py', 'config.json', 'CAPTURE_STEP.txt',
                 'APPLY_STEP.txt')
LAUNCHERS = {'CAPTURE_STEP.txt': 'f01w2_capture.py', 'APPLY_STEP.txt': 'f01w2_apply.py'}
REPORT_RE = re.compile(r'^F01W2-(\d{2})-([A-Z0-9_]+)\.json$')


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


def fail(message):
    raise SystemExit('PREPARATION REFUSED: ' + message)


def read_json(path):
    with open(path, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def launcher_line(path):
    escaped = path.replace('\\', '\\\\')
    return ("exec(compile(open('%s', 'rb').read(), '%s', 'exec', 0, True), "
            "{'__name__': '__f01w2_owner_step__', '__file__': '%s'})\n" % (escaped, escaped, escaped))


def load_config_checked(config):
    if config.get('format') != 'F01W2-config-v1':
        fail('unexpected config format')
    keys = ('original_session', 'r2_fixture', 'capture_session', 'apply_session')
    if len(set(normalized(config[k]) for k in keys)) != len(keys):
        fail('original, R2 fixture and the two disposable copies must be four distinct paths')
    run_dir = config['run_dir']
    for k in ('capture_session', 'apply_session'):
        if normalized(os.path.dirname(config[k])) != normalized(run_dir):
            fail('%s must be directly inside run_dir' % k)
        if config[k + '_sha256'] != config['r2_fixture_sha256']:
            fail('%s must be byte-identical to the R2 fixture' % k)
    if normalized(config['reports_dir']) != normalized(os.path.join(run_dir, 'reports')):
        fail('reports_dir must be <run dir>\\reports')
    if normalized(config['pose_path']) != normalized(os.path.join(run_dir, 'poses', 'left_arm_pose.f01w2.json')):
        fail('pose_path must be <run dir>\\poses\\left_arm_pose.f01w2.json')
    return config


def manifest(package_root):
    source_dir = os.path.join(package_root, 'harness')
    config = load_config_checked(read_json(os.path.join(source_dir, 'config.json')))
    target_dir = os.path.join(config['run_dir'], 'harness')
    for name, script in sorted(LAUNCHERS.items()):
        write_exclusive(os.path.join(source_dir, name), launcher_line(os.path.join(target_dir, script)).encode('ascii'))
    hashes = dict((name, digest(os.path.join(source_dir, name))) for name in HARNESS_FILES)
    write_exclusive(os.path.join(package_root, 'HARNESS_SHA256.json'),
                    json.dumps(hashes, indent=1, sort_keys=True).encode('ascii'))
    print('F01W2 manifest written: ' + os.path.join(package_root, 'HARNESS_SHA256.json'))
    return hashes


def prepare(package_root):
    expected = read_json(os.path.join(package_root, 'HARNESS_SHA256.json'))
    source_dir = os.path.join(package_root, 'harness')
    if sorted(expected) != sorted(HARNESS_FILES):
        fail('HARNESS_SHA256.json does not list exactly the harness files')
    for name in HARNESS_FILES:
        if digest(os.path.join(source_dir, name)) != expected[name]:
            fail('harness/%s does not match HARNESS_SHA256.json' % name)
    config = load_config_checked(read_json(os.path.join(source_dir, 'config.json')))
    for name, script in LAUNCHERS.items():
        with open(os.path.join(source_dir, name), 'rb') as f:
            line = f.read().decode('ascii')
        if line != launcher_line(os.path.join(config['run_dir'], 'harness', script)):
            fail('%s does not launch %s in the run directory' % (name, script))
    for key in ('original_session', 'r2_fixture'):
        if digest(config[key]) != config[key + '_sha256']:
            fail('%s hash differs from the configured value' % key)
    run_dir = config['run_dir']
    if os.path.exists(run_dir):
        fail('run directory already exists: %s (use a fresh directory; never reuse a run)' % run_dir)
    for sub in ('reports', 'harness', 'poses'):
        os.makedirs(os.path.join(run_dir, sub))
    for key in ('capture_session', 'apply_session'):
        fd = os.open(config[key], os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'wb') as out:
            with open(config['r2_fixture'], 'rb') as src:
                shutil.copyfileobj(src, out)
        if digest(config[key]) != config[key + '_sha256']:
            fail('%s copy hash mismatch' % key)
    for name in HARNESS_FILES:
        target = os.path.join(run_dir, 'harness', name)
        shutil.copyfile(os.path.join(source_dir, name), target)
        if digest(target) != expected[name]:
            fail('copied harness/%s hash mismatch' % name)
    if digest(config['original_session']) != config['original_session_sha256'] or \
            digest(config['r2_fixture']) != config['r2_fixture_sha256']:
        fail('a protected file changed during preparation')
    print('F01W2 run prepared: ' + run_dir)
    print('Process A opens: ' + config['capture_session'])
    print('Process B opens: ' + config['apply_session'])
    return run_dir


def ledger(directory):
    entries = []
    for name in sorted(os.listdir(directory)):
        m = REPORT_RE.match(name)
        if m is None:
            continue
        with open(os.path.join(directory, name), 'rb') as f:
            raw = f.read()
        if not raw:
            fail('report %s is empty (a step did not finish)' % name)
        entries.append({'seq': int(m.group(1)), 'name': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'report': json.loads(raw.decode('utf-8'))})
    for i, e in enumerate(entries):
        if e['seq'] != i + 1 or e['report'].get('seq') != e['seq']:
            fail('ledger sequence is not contiguous')
        if i and e['report'].get('previous_report_sha256') != entries[i - 1]['sha256']:
            fail('ledger hash chain is broken at ' + e['name'])
    return entries


def harness_integrity(config, harness_dir):
    values = {}
    for key in ('original_session', 'r2_fixture', 'capture_session', 'apply_session', 'cpm_source'):
        values[key] = digest(config[key])
    for name in ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py'):
        values[name] = digest(os.path.join(harness_dir, name))
    values['config'] = digest(os.path.join(harness_dir, 'config.json'))
    return values


def harness_core(harness_dir):
    """The harness's own core: its read-only kernel32 process queries and the strict classification of a
    recorded process (one implementation for the gate and process B)."""
    path = os.path.join(harness_dir, 'f01w2_core.py')
    ns = {'__name__': 'f01w2_core_gate', '__file__': path}
    with open(path, 'rb') as f:
        exec(compile(f.read(), path, 'exec', 0, True), ns)
    return ns


def utc():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def gate(config_path, provider=None):
    harness_dir = os.path.dirname(os.path.abspath(config_path))
    config = load_config_checked(read_json(config_path))
    entries = ledger(config['reports_dir'])
    if len(entries) != 1:
        fail('the gate runs exactly once, directly after the capture (ledger has %d reports)' % len(entries))
    cap = entries[0]['report']
    if cap.get('step') != 'CAPTURE' or cap.get('status') != 'CAPTURE_COMPLETE_PENDING_CLOSE' or \
            cap.get('evidence_complete') is not True:
        fail('the capture did not complete (status %s); do not start process B' % cap.get('status'))
    integrity = harness_integrity(config, harness_dir)
    first = cap.get('integrity_before') or {}
    for key in ('f01w2_core.py', 'f01w2_capture.py', 'f01w2_apply.py', 'config', 'cpm_source'):
        if first.get(key) != integrity[key]:
            fail('%s differs from the capture step' % key)
    for key in ('original_session', 'r2_fixture', 'capture_session', 'apply_session'):
        if integrity[key] != config[key + '_sha256']:
            fail('%s changed (a disposable copy must never be saved)' % key)
    publication = cap.get('publication') or {}
    if normalized(publication.get('pose_path') or '') != normalized(config['pose_path']):
        fail('the capture record names a different pose path')
    if not os.path.isfile(config['pose_path']) or digest(config['pose_path']) != publication.get('pose_sha256'):
        fail('the published pose is missing or differs from the capture record')
    core = harness_core(harness_dir)
    if provider is None:
        provider = core['WindowsProcesses']()
    a = cap.get('process') or {}
    if a.get('provider') != provider.name:
        fail('process evidence provider differs from the capture step')
    # Strict lookup of the recorded process A (F-05): only a verified absence, exit or PID reuse proves that it
    # has gone; an unresolved query (access denied or any other failure) blocks the gate.
    state = core['recorded_process_state'](provider, a)
    if state['state'] == 'RUNNING':
        fail('process A (pid %d) is still running; quit SFM without saving first' % a['pid'])
    if state['state'] not in core['EXITED_STATES']:
        fail('process A (pid %d) state could not be established (%s); the gate cannot prove that it exited'
             % (a['pid'], state['error']))
    try:
        running_images = provider.images()
    except Exception as exc:
        fail('process enumeration failed (%r); the gate cannot prove that SFM is closed' % (exc,))
    sfm = sorted(image for pid, image in running_images if os.path.basename(image).lower() == 'sfm.exe')
    if sfm:
        fail('an SFM process is running (%s); quit SFM without saving first' % sfm)
    me = provider.current()
    checked = int(provider.now())
    if not int(a['creation_filetime']) < checked:
        fail('process A creation time is not before the gate time')
    report = {'format': 'F01W2-v1', 'seq': 2, 'step': 'PROCESS_GATE', 'place': None, 'stage': None,
              'utc_start': utc(), 'python': sys.version, 'pid': os.getpid(),
              'process': {'provider': provider.name, 'pid': int(me['pid']),
                          'creation_filetime': int(me['creation_filetime']), 'image': me.get('image')},
              'previous_report_sha256': entries[0]['sha256'], 'status': 'CONTINUE', 'events': [],
              'gate': {'provider': provider.name, 'process_a': {'pid': a['pid'],
                                                                'creation_filetime': a['creation_filetime']},
                       'process_a_running': False, 'process_a_state': state['state'],
                       'process_a_lookup': state['lookup'], 'process_a_error': state['error'], 'sfm_processes': sfm,
                       'checked_filetime': checked, 'pose_sha256': publication['pose_sha256'],
                       'poses_dir_listing': sorted(os.listdir(os.path.dirname(config['pose_path'])))},
              'integrity_before': integrity,
              'next': {'step': 'APPLY', 'place': 'destination', 'stage': 'committed',
                       'instruction': 'Start SFM, open the APPLICATION copy, move the playhead to movie frame %d '
                                      '(%s), let it settle, then submit APPLY_STEP.txt once. Do not interact until '
                                      'the step reports.' % (config['places']['destination']['movie_frame'],
                                                             config['places']['destination']['shot'])}}
    report['integrity_after'] = harness_integrity(config, harness_dir)
    if report['integrity_after'] != integrity:
        fail('a protected or harness file changed during the gate')
    report['evidence_complete'] = True
    report['utc_end'] = utc()
    path = os.path.join(config['reports_dir'], 'F01W2-02-PROCESS_GATE.json')
    write_exclusive(path, json.dumps(report, indent=1, sort_keys=True, ensure_ascii=True,
                                     allow_nan=False).encode('ascii'))
    print('F01W2 process gate recorded: ' + path)
    print('NEXT: ' + report['next']['instruction'])
    return report


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('manifest', 'prepare', 'gate'):
        print('usage: python -I prepare_run.py manifest|prepare <package root>\n'
              '       python -I prepare_run.py gate <run dir>\\harness\\config.json')
        sys.exit(2)
    {'manifest': manifest, 'prepare': prepare, 'gate': gate}[sys.argv[1]](sys.argv[2])
