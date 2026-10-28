# -*- coding: ascii -*-
"""F-01 W1 run preparation. Run with system Python while SFM is CLOSED:

    python -I prepare_run.py <candidate package root>

Verifies the reviewed harness files against HARNESS_SHA256.json, verifies the
original session and the R2 fixture hashes, then creates a NEW run directory
(it must not exist) containing:
  - a fresh disposable copy of the R2 fixture (exclusive creation, hash verified)
  - harness/ (the reviewed harness, config and NEXT_STEP.txt, hash verified)
  - reports/ (empty)
Never opens, edits or writes the original session or the R2 fixture.
"""
import hashlib
import json
import os
import shutil
import sys

HARNESS_FILES = ('f01w1_harness.py', 'config.json', 'NEXT_STEP.txt')


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


def main(package_root):
    with open(os.path.join(package_root, 'HARNESS_SHA256.json'), 'rb') as f:
        expected = json.loads(f.read().decode('utf-8'))
    source_dir = os.path.join(package_root, 'harness')
    for name in HARNESS_FILES:
        if digest(os.path.join(source_dir, name)) != expected[name]:
            fail('harness/%s does not match HARNESS_SHA256.json' % name)
    with open(os.path.join(source_dir, 'config.json'), 'rb') as f:
        config = json.loads(f.read().decode('utf-8'))
    for key in ('original_session', 'r2_fixture'):
        if digest(config[key]) != config[key + '_sha256']:
            fail('%s hash differs from the configured value' % key)
    if config['r2_fixture_sha256'] != config['disposable_session_sha256']:
        fail('the disposable copy must be byte-identical to the R2 fixture')
    run_dir = os.path.dirname(config['disposable_session'])
    if normalized(config['reports_dir']) != normalized(os.path.join(run_dir, 'reports')):
        fail('reports_dir must be <run dir>\\reports')
    with open(os.path.join(source_dir, 'NEXT_STEP.txt'), 'rb') as f:
        launcher = f.read().decode('ascii')
    harness_target = os.path.join(run_dir, 'harness', 'f01w1_harness.py')
    if launcher.count(harness_target.replace('\\', '\\\\')) != 3:
        fail('NEXT_STEP.txt does not point at %s' % harness_target)
    if os.path.exists(run_dir):
        fail('run directory already exists: %s (use a fresh directory; never reuse a run)' % run_dir)
    os.makedirs(os.path.join(run_dir, 'reports'))
    os.makedirs(os.path.join(run_dir, 'harness'))
    fd = os.open(config['disposable_session'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        with open(config['r2_fixture'], 'rb') as src:
            shutil.copyfileobj(src, out)
    if digest(config['disposable_session']) != config['disposable_session_sha256']:
        fail('disposable copy hash mismatch')
    for name in HARNESS_FILES:
        target = os.path.join(run_dir, 'harness', name)
        shutil.copyfile(os.path.join(source_dir, name), target)
        if digest(target) != expected[name]:
            fail('copied harness/%s hash mismatch' % name)
    if digest(config['original_session']) != config['original_session_sha256'] or \
            digest(config['r2_fixture']) != config['r2_fixture_sha256']:
        fail('a protected file changed during preparation')
    print('F01W1 run prepared: ' + run_dir)
    print('Disposable session: ' + config['disposable_session'])
    print('Script Editor line: ' + os.path.join(run_dir, 'harness', 'NEXT_STEP.txt'))
    return run_dir


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python -I prepare_run.py <candidate package root>')
        sys.exit(2)
    main(sys.argv[1])
