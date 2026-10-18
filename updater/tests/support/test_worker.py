# -*- coding: utf-8 -*-
"""TEST-ONLY entry point for the L-1 qualification suite. Never shipped.

Wraps the product worker (sfm_character_tools_updater.worker) and, for this one process:
  * installs exact-token, fail-closed barriers (P1/C1 semantics): at a named barrier it
    prints `BARRIER <name>` and continues only on exactly `GO <name> <token>`; EOF, a wrong
    token or a timeout stop the operation without success;
  * substitutes the A3 process query's output (--inject process=FORM, or process_seq with
    forms separated by `||`, one per query, the last repeating);
  * injects a candidate-write fault (--inject candidate_write_error=CODE);
  * enables the Win32 call trace and adds it, with the barrier log, to the result;
  * trusts a TEST signing key (--trust-key HEX, Ed25519 raw public key) through the test-only
    seam hooks.extra_trusted_keys; the product's own trust table is never changed;
  * refuses any installation that does not resolve under --scratch-root or that resolves
    under --forbid (the real game directory), before the product code runs;
  * (L-3) maps the product's https URLs onto a local test server (--net-base http://127.0.0.1:PORT)
    through the test-only seam hooks.network_rewrite, and shortens the network timeout
    (--net-timeout SECONDS) through hooks.network_timeout;
  * records every name lookup and socket connection attempt of the operation (Python audit
    hook) in the result as `network`;
  * (L-4) holds at a named barrier indefinitely (--hold-at NAME), after creating the marker file
    --hold-marker PATH, so that the GUI qualification can kill or close a worker mid-operation.

Process forms: clear | real | raise | rc:N | output:TEXT (\\n allowed).
"""
import json
import os
import sys
import threading
import time
from urllib.parse import urlsplit

UPDATER = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, UPDATER)

from sfm_character_tools_updater import hooks, official, w32, worker  # noqa: E402
from sfm_character_tools_updater.layout import resolve_installation  # noqa: E402
from sfm_character_tools_updater.messages import Stop  # noqa: E402

STOPS = set()
HOLD = {}
PASSED = []
TOKEN = [None]
BARRIER_TIMEOUT = [120.0]
CLEAR_OUTPUT = "INFO: No tasks are running which match the specified criteria."
NETWORK = []


def audit(event, args):
    if event == "socket.getaddrinfo":
        NETWORK.append([event, "%s:%s" % (args[0], args[1])])
    elif event == "socket.connect":
        NETWORK.append([event, repr(args[1])])


def make_rewrite(base):
    def rewrite(url):
        u = urlsplit(url)
        tail = u.path + ("?" + u.query if u.query else "")
        if u.hostname == "api.github.com":
            return base + "/api" + tail
        return base + "/cdn/" + u.hostname + tail
    return rewrite


def barrier(name):
    """Exact-token, fail-closed: only `GO <name> <token>` continues."""
    PASSED.append(name)
    if name in HOLD.get("names", ()):
        with open(HOLD["marker"], "x", encoding="ascii") as f:
            f.write("%s %d\n" % (name, os.getpid()))
        while True:
            time.sleep(1)
    if name in STOPS:
        sys.stdout.write("BARRIER %s\n" % name)
        sys.stdout.flush()
        box = []
        t = threading.Thread(target=lambda: box.append(sys.stdin.readline()), daemon=True)
        t.start()
        t.join(BARRIER_TIMEOUT[0])
        if not box:
            PASSED.append("barrier_fail:%s:timeout" % name)
            raise hooks.BarrierAbort("timeout at %s" % name)
        line = box[0]
        if line == "":
            PASSED.append("barrier_fail:%s:eof" % name)
            raise hooks.BarrierAbort("EOF at %s" % name)
        if TOKEN[0] is None or line.rstrip("\r\n") != "GO %s %s" % (name, TOKEN[0]):
            PASSED.append("barrier_fail:%s:bad_token" % name)
            raise hooks.BarrierAbort("bad token at %s" % name)
        PASSED.append("resumed:%s" % name)


def make_query(forms):
    seq = list(forms)
    used = []

    def query():
        form = seq.pop(0) if len(seq) > 1 else seq[0]
        used.append(form)
        if form == "real":
            import subprocess
            cp = subprocess.run(["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq sfm.exe"],
                                capture_output=True, text=True, timeout=30)
            return cp.returncode, cp.stdout
        if form == "clear":
            return 0, CLEAR_OUTPUT
        if form == "raise":
            raise OSError("injected query failure")
        if form.startswith("rc:"):
            return int(form[3:]), ""
        if form.startswith("output:"):
            return 0, form[len("output:"):].replace("\\n", "\n")
        raise ValueError("unknown process form %r" % form)
    query.used = used
    return query


def norm(p):
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        p = p[4:]
    return os.path.normcase(p).rstrip("\\")


def under(path, root):
    p, r = norm(path), norm(root)
    return p == r or p.startswith(r + "\\")


def main(argv):
    test_opts = {"--stop-at": [], "--token": [], "--barrier-timeout": [], "--inject": [],
                 "--scratch-root": [], "--forbid": [], "--trust-key": [], "--net-base": [], "--net-timeout": [],
                 "--hold-at": [], "--hold-marker": []}
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] in test_opts:
            test_opts[argv[i]].append(argv[i + 1])
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    STOPS.update(x for v in test_opts["--stop-at"] for x in v.split(",") if x)
    TOKEN[0] = (test_opts["--token"] or [None])[0]
    if test_opts["--barrier-timeout"]:
        BARRIER_TIMEOUT[0] = float(test_opts["--barrier-timeout"][0])
    scratch = test_opts["--scratch-root"][0]
    forbid = test_opts["--forbid"]
    hooks.barrier = barrier
    query = None
    for kv in test_opts["--inject"]:
        k, v = kv.split("=", 1)
        if k == "process":
            query = make_query([v])
        elif k == "process_seq":
            query = make_query(v.split("||"))
        elif k == "candidate_write_error":
            hooks.candidate_write_error = int(v)
        else:
            raise SystemExit("unknown injection %r" % k)
    if query is not None:
        hooks.process_query = query
    if test_opts["--trust-key"]:
        hooks.extra_trusted_keys = {official.key_id_for(bytes.fromhex(k)): k for k in test_opts["--trust-key"]}
    if test_opts["--hold-at"]:
        HOLD.update(names=set(test_opts["--hold-at"]), marker=test_opts["--hold-marker"][0])
    if test_opts["--net-base"]:
        hooks.network_rewrite = make_rewrite(test_opts["--net-base"][0])
    if test_opts["--net-timeout"]:
        hooks.network_timeout = float(test_opts["--net-timeout"][0])
    w32.TRACE_ENABLED[0] = True
    sys.addaudithook(audit)

    args = worker.build_parser().parse_args(rest)
    if not under(args.result, scratch):
        raise SystemExit("STOP: result path outside the scratch root")
    try:
        real = resolve_installation(args.installation)
        guard_ok = under(real, scratch) and not any(under(real, f) for f in forbid)
    except Stop as e:
        real, guard_ok = None, True  # unresolvable: the product reports it
    if not guard_ok:
        res = {"operation": args.command, "outcome": "REFUSED",
               "message": "Refused by the test boundary.",
               "details": {"reason": "installation outside the L-1 scratch root", "resolved": real}}
    else:
        res = worker.run(args)
    res["barriers"] = PASSED
    res["trace"] = w32.TRACE
    res["network"] = NETWORK
    if query is not None:
        res["process_forms_used"] = query.used
    worker.write_result(args.result, res)


if __name__ == "__main__":
    main(sys.argv[1:])
