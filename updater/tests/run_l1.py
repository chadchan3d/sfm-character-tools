# -*- coding: utf-8 -*-
"""L-1 qualification controller (TEST-ONLY). Ported from the U0B-P1 controller (p1run.py
4affc60b...) and the C1 no-op cases (p1c1run.py 6eaa0c8a...), now driving the PRODUCT backend
through tests/support/test_worker.py (product worker + test seams).

Builds disposable installations under the scratch run directory, drives prepare/install/
recover processes through barriers, and checks every final state independently. Every write
of this controller goes through a guard that raises unless the target is under the run
directory. Nothing here reads the live installation except through the read-only
fingerprint tool, and nothing writes to it.

  run_l1.py setup  --run RUN --game GAME --p1-preservation DIR --g3-source FILE --py27 EXE
  run_l1.py groups --run RUN --game GAME --py27 EXE --label LABEL --groups A,B,...

Groups: A B C D E F G H I J K N X W (L-1, rerun as L-2/L-3 regression), M O W3 (L-2: Use Another
TXT and Get Official Data from a local signed package; rerun as L-3 regression) and Q W4 (L-3: Get
Official Data online -- explicit check and bounded download against a loopback GitHub stand-in, and
the shipping worker's network boundary including one explicit query of the real, empty official
release list) and U (L-4 with its usability refinement: the GUI's three actions end-to-end, the
replacement confirmation, user backups, recovery, worker containment and staging cleanup, driving the
real Tkinter App with its bounded worker). Run with a Python that provides the `cryptography` package (the isolated
qualification environment).
Results: RUN\\LABEL\\results\\cases\\<case>.json and RUN\\LABEL\\results\\matrix_<group>.json
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
UPDATER = os.path.dirname(HERE)
REPO = os.path.dirname(UPDATER)
SUPPORT = os.path.join(HERE, "support")
TEST_WORKER = os.path.join(SUPPORT, "test_worker.py")
PY3 = sys.executable
SUBDIR = r"SteamLibrary\steamapps\common\SourceFilmmaker\game\usermod\cfg"
LOCK_REL = "sfm_character_tools_updater\\installation.lock"
EMPTY_SHA = hashlib.sha256(b"").hexdigest()

# Fixture identities established by U0B-P1 (report bb91b373...).
FIXTURE_TXT = {"G1": "ac45e5c1cd45d55b3af95747c97d2f8e93eda4f4fe4fec63e97d62828c904d93",
               "G2": "54413b6ca618f73733b6624e1d2411a6cfb00a24489330ccbfc153760f3486e7",
               "G3": "5635ecf352e71a25c345ac838b8410f03af13efdece082e1cc559727e066d993"}
FIXTURE_SIDECAR = {"g1": "bcd9764105f92ce87fb84053d591ec40c51bc8f482584be1c373c1726305750b",
                   "g2": "cd370f67bfd4db6a17fdc3d425ffae6934ad223c2f5519eda99e3f5b2264ffe3",
                   "g3": "3a16e9459db61110a323162c6e90797e8929c5325f906e68905b0299aec7d267"}
FIXTURE_MANIFEST_PREFIX = {"g1": "d810d648", "g2": "9da5057f", "g3": "d8136a90"}
G2_REPO = os.path.join(REPO, "real_sfm_qualification", "checkpoint_i_generation_replacement", "i_pass_evidence",
                       "sfm_checkpoint_i_generated_g2_source.txt")
AUTH_PKG_REL = os.path.join("tests", "sidecar", "qualification", "candidate_b2c_correction6",
                            "sfm_master_authority_productionized")

A = None          # parsed arguments
RUN = ART = WORK = NOPYC = None
ENV = None
GEN = {}
SHA = {}
G1_TXT = G2_TXT = G3_TXT = None
TOKEN = uuid.uuid4().hex[:12]
PSTAT = None      # the product's real process-status query, bound in main()


# ------------------------------------------------------------------ guarded writes
def norm(p):
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        p = p[4:]
    return os.path.normcase(p).rstrip("\\")


def under(path, root):
    p, r = norm(path), norm(root)
    return p == r or p.startswith(r + "\\")


def guard(path):
    if not under(path, RUN):
        raise RuntimeError("STOP: write outside the run directory: %r" % path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def wcopy(src, dst):
    guard(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "rb") as f, open(dst, "xb") as g:
        g.write(f.read())


def wbytes(dst, data):
    guard(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "xb") as g:
        g.write(data)


def wappend(dst, data):
    guard(dst)
    with open(dst, "ab") as g:
        g.write(data)


def wremove(p):
    guard(p)
    os.remove(p)


def wmkdirs(p):
    guard(p)
    os.makedirs(p)


# ------------------------------------------------------------------ setup
def setup():
    """Fixtures: G1 (preserved P1 copy), G2 (repository), G3 (P1 scratch artifact), each
    verified against the P1 identity, then compiled by the unchanged pinned compiler through
    the product's candidate module. A .py-only, hash-verified copy of the consumer libraries
    for the Python 2.7 checks (no pre-existing bytecode is ever loaded)."""
    sys.path.insert(0, UPDATER)
    from sfm_character_tools_updater import candidate
    os.makedirs(RUN)
    rep = {"fixtures": {}, "artifacts": {}, "py27lib": []}
    for tag, src in (("G1", os.path.join(A.p1_preservation, "sfm_defaultanimationgroups.txt")),
                     ("G2", G2_REPO), ("G3", A.g3_source)):
        dst = os.path.join(ART, tag.lower() + "_source.txt")
        wcopy(src, dst)
        got = sha_file(dst)
        rep["fixtures"][tag] = {"sha256": got, "expected": FIXTURE_TXT[tag], "ok": got == FIXTURE_TXT[tag]}
    for g in ("g1", "g2", "g3"):
        txt = open(os.path.join(ART, g + "_source.txt"), "rb").read()
        name, body, manifest, outcome = candidate.compile_real(txt, g)
        d = os.path.join(ART, g)
        wbytes(os.path.join(d, name), body)
        wbytes(os.path.join(d, "manifest.json"), manifest)
        bad = candidate.validate_candidate_files(outcome, name, os.path.join(d, name), os.path.join(d, "manifest.json"))
        rep["artifacts"][g] = {"sidecar": name, "sidecar_sha256": sha(body), "manifest_sha256": sha(manifest),
                               "validation": bad or "PASS",
                               "ok": (sha(body) == FIXTURE_SIDECAR[g] and name.endswith(FIXTURE_SIDECAR[g] + ".sfmsidecar")
                                      and sha(manifest).startswith(FIXTURE_MANIFEST_PREFIX[g]) and bad is None)}
    lib = os.path.join(RUN, "py27lib")
    srcs = [(os.path.join(REPO, AUTH_PKG_REL), os.path.join(lib, "sfm_master_authority_productionized")),
            (os.path.join(REPO, "tools", "sfm_master_sidecar"), os.path.join(lib, "sfm_master_sidecar"))]
    for s, d in srcs:
        for n in sorted(os.listdir(s)):
            if n.endswith(".py"):
                wcopy(os.path.join(s, n), os.path.join(d, n))
                rep["py27lib"].append({"file": os.path.relpath(os.path.join(d, n), lib),
                                       "sha256": sha_file(os.path.join(d, n)),
                                       "ok": sha_file(os.path.join(d, n)) == sha_file(os.path.join(s, n))})
    wcopy(os.path.join(REPO, "tools", "sfm_master_core.py"), os.path.join(lib, "sfm_master_core.py"))
    rep["ok"] = all(x["ok"] for x in rep["fixtures"].values()) and all(x["ok"] for x in rep["artifacts"].values()) \
        and all(x["ok"] for x in rep["py27lib"])
    out = os.path.join(RUN, "setup.json")
    guard(out)
    with open(out, "x", encoding="utf-8") as f:
        json.dump(rep, f, indent=1, sort_keys=True)
    print("SETUP ok=%s" % rep["ok"])


def load_generations():
    for g in ("g1", "g2", "g3"):
        d = os.path.join(ART, g)
        sc = [n for n in os.listdir(d) if n.endswith(".sfmsidecar")][0]
        GEN[g] = {"sidecar": sc, "sidecar_path": os.path.join(d, sc), "sidecar_sha": sha_file(os.path.join(d, sc)),
                  "manifest_path": os.path.join(d, "manifest.json"),
                  "manifest_sha": sha_file(os.path.join(d, "manifest.json"))}
    for t in ("G1", "G2", "G3"):
        SHA[t] = sha_file(os.path.join(ART, t.lower() + "_source.txt"))


# ------------------------------------------------------------------ installations and observation
def inst_id(case):
    """Short installation directory name: keeps every ordinary scratch installation's consumer
    paths inside the 260-character budget regardless of the case name's length."""
    return hashlib.sha256(case.encode("utf-8")).hexdigest()[:10]


def make_install(case, master="G1", gens=("g1",), legacy_lock=True, manifest="g1", depth_pad=0, base=None,
                 software=None):
    """A scratch installation. Unless software=False, it also carries the qualified Character Tools
    software files and their test-signed inventory under usermod\\scripts (L-5: data of every workflow
    is installed only into a verified software installation)."""
    base = base or os.path.join(WORK, "i", inst_id(case))
    if depth_pad:
        base = os.path.join(base, *(["p" * 40] * depth_pad))
    cfg = os.path.join(base, SUBDIR)
    wmkdirs(os.path.join(cfg, "sfm_shared_authority"))
    wcopy({"G1": G1_TXT, "G3": G3_TXT, "G2": G2_TXT}[master], os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
    for g in gens:
        wcopy(GEN[g]["sidecar_path"], os.path.join(cfg, "sfm_shared_authority", GEN[g]["sidecar"]))
    if manifest:
        wcopy(GEN[manifest]["manifest_path"], os.path.join(cfg, "sfm_shared_authority", "manifest.json"))
    if legacy_lock:
        wbytes(os.path.join(cfg, "sfm_shared_authority", "publisher.lock"), b"")
    wmkdirs(os.path.join(cfg, "sfm_character_tools_updater", "transactions"))
    if software is None:
        software = True
    if software:
        install_software(os.path.dirname(cfg), software if isinstance(software, str) else "signed_a")
    return cfg


SOFTWARE_SPEC = os.path.join(UPDATER, "release_tools", "character_tools_software_v1.json")
SOFTWARE_PRODUCER = os.path.join(UPDATER, "release_tools", "make_software_inventory.py")
INVENTORY_REL = os.path.join("scripts", "sfm", "mainmenu", "SFM Character Tools", "sfm_character_tools_inventory")


def software_dir(*p):
    return os.path.join(RUN, "software", *p)


def ensure_software():
    """Stage the qualified software from the repository (refusing non-qualified bytes) and sign its
    inventory with the per-run TEST key test_a (and, for refusal cases, test_b)."""
    if os.path.exists(software_dir("signed_a", "sfm_character_tools_inventory.json")):
        return
    ensure_keys()
    guard(software_dir("usermod"))

    def run(*args):
        cp = subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, SOFTWARE_PRODUCER] + list(args),
                            capture_output=True, text=True, env=ENV, cwd=os.path.join(RUN, "tmp"), timeout=600)
        if cp.returncode != 0:
            raise RuntimeError("software producer failed: %s" % cp.stderr[-800:])
        return json.loads(cp.stdout.strip().splitlines()[-1])
    run("stage", "--spec", SOFTWARE_SPEC, "--out", software_dir("usermod"))
    for k in ("a", "b"):
        run("sign", "--spec", SOFTWARE_SPEC, "--root", software_dir("usermod"), "--software-version", "1.0.0-test",
            "--private", keyfile("test_" + k, "pem"), "--out", software_dir("signed_" + k))


def install_software(usermod, signed="signed_a"):
    ensure_software()
    src = software_dir("usermod")
    for dp, dn, fn in os.walk(src):
        for n in fn:
            rel = os.path.relpath(os.path.join(dp, n), src)
            wcopy(os.path.join(dp, n), os.path.join(usermod, rel))
    if signed:
        for ext in (".json", ".sig"):
            wcopy(software_dir(signed, "sfm_character_tools_inventory" + ext), os.path.join(usermod, INVENTORY_REL + ext))


STAGING_PREFIX = "sfm_character_tools_updater\\staging\\"


def tree(cfg, include_staging=False):
    """Independent observer: every file under cfg -> sha256 (plain shared reads). Updater-
    private staging is reported separately unless include_staging."""
    out = {}
    for dp, dn, fn in os.walk(cfg):
        for n in fn:
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, cfg)
            if rel.startswith(STAGING_PREFIX) and not include_staging:
                continue
            try:
                out[rel] = sha_file(p)
            except OSError as e:
                out[rel] = "UNREADABLE:%s" % getattr(e, "winerror", e)
    return out


def active_set(t):
    """Active slots only: Master and the authority directory."""
    return {k: v for k, v in t.items() if k == "sfm_defaultanimationgroups.txt"
            or k.startswith("sfm_shared_authority\\")}


def noop_unchanged(before, after):
    """Active slots byte-identical; the only permitted new file (outside updater-private
    staging) is the permanent, empty C4 installation lock."""
    added = sorted(set(after) - set(before))
    return (active_set(before) == active_set(after)
            and all(before[k] == after.get(k) for k in before)
            and added in ([], [LOCK_REL])
            and (LOCK_REL not in after or after[LOCK_REL] == EMPTY_SHA))


def expected_active(master, g, legacy_lock=True):
    e = {"sfm_defaultanimationgroups.txt": SHA[master],
         "sfm_shared_authority\\" + GEN[g]["sidecar"]: GEN[g]["sidecar_sha"],
         "sfm_shared_authority\\manifest.json": GEN[g]["manifest_sha"]}
    if legacy_lock:
        e["sfm_shared_authority\\publisher.lock"] = EMPTY_SHA
    return e


def final_is(cfg, which, legacy_lock=True):
    t = tree(cfg)
    act = active_set(t)
    exp = expected_active(which[0], which[1], legacy_lock)
    return act == exp, {"active": act, "expected": exp}


def preserved(t, shas):
    have = set(t.values())
    return {s[:12]: (s in have) for s in shas}


def originals_present(t, master="G1"):
    return preserved(t, [SHA[master], GEN["g1"]["sidecar_sha"], GEN["g1"]["manifest_sha"]])


def txdirs(cfg):
    root = os.path.join(cfg, "sfm_character_tools_updater", "transactions")
    return [os.path.join(root, n) for n in sorted(os.listdir(root))]


def tx_files(cfg):
    return {k: v for k, v in tree(cfg).items() if k.startswith("sfm_character_tools_updater\\transactions\\")}


def max_path(cfg):
    m = 0
    for dp, dn, fn in os.walk(cfg):
        for n in dn + fn:
            m = max(m, len(os.path.join(dp, n)))
    return m


# ------------------------------------------------------------------ trace classification (C1)
def classify_trace(cfg, trace):
    """Ordinal classification of every traced CreateFileW and EVENT."""
    master = norm(os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
    auth = norm(os.path.join(cfg, "sfm_shared_authority"))
    lockp = norm(os.path.join(cfg, LOCK_REL))
    legacy = norm(os.path.join(cfg, "sfm_shared_authority", "publisher.lock"))
    summary = {"exclusive_authority_opens": [], "preview_authority_opens": 0,
               "installation_lock_opens": [], "legacy_lock_probe_opens": [], "events": []}
    for i, r in enumerate(trace or []):
        if r.get("op") == "EVENT":
            summary["events"].append(dict(r, ordinal=i))
            continue
        if r.get("op") != "CreateFileW":
            continue
        a = r["args"]
        p = norm(a["path"])
        role = "other"
        if p == master:
            role = "authority:master"
        elif os.path.dirname(p) == auth and (p.endswith(".sfmsidecar") or p.endswith("manifest.json")):
            role = "authority:" + ("sidecar" if p.endswith(".sfmsidecar") else "manifest")
        elif p == lockp:
            role = "installation.lock"
        elif p == legacy:
            role = "legacy publisher.lock"
        rec = {"ordinal": i, "role": role, "access": a["access"], "share": a["share"],
               "disposition": a["disposition"], "ok": r["ok"], "error": r.get("error"),
               "file": os.path.basename(a["path"])}
        if role.startswith("authority:"):
            if a["share"] == "READ|WRITE|DELETE":
                summary["preview_authority_opens"] += 1
            else:
                summary["exclusive_authority_opens"].append(rec)
        elif role == "installation.lock":
            summary["installation_lock_opens"].append(rec)
        elif role == "legacy publisher.lock":
            summary["legacy_lock_probe_opens"].append(rec)
    gates = [e["ordinal"] for e in summary["events"] if e["event"] == "process_gate"]
    excl = [x["ordinal"] for x in summary["exclusive_authority_opens"]]
    summary["gate_before_first_exclusive_open"] = (bool(gates) and (not excl or gates[0] < min(excl)))
    summary["n_exclusive_authority_opens"] = len(excl)
    return summary


def zero_excl(step):
    return step.get("trace_summary", {}).get("n_exclusive_authority_opens") == 0


def noop_ok(step):
    """C1 success shape: CLEAR gates before exactly three identity-matched share-0 authority opens."""
    s = step.get("trace_summary", {})
    ex = s.get("exclusive_authority_opens", [])
    roles = sorted(x["role"] for x in ex)
    return (step.get("outcome") == "NOOP" and s.get("gate_before_first_exclusive_open")
            and roles == ["authority:manifest", "authority:master", "authority:sidecar"]
            and all(x["access"] == "GENERIC_READ" and x["share"] == "0" and x["ok"] for x in ex)
            and (step.get("process_status") or [None])[0] == "CLEAR"
            and len(step.get("noop_verification") or []) == 3
            and (step.get("correspondence") or {}).get("ok") is True)


# ------------------------------------------------------------------ process drivers
KEEP = ("process_status", "noop_verification", "transactions_checked", "correspondence", "restart_required",
        "post_install_process_status", "installed_state", "prepid", "confirm_sha", "candidate", "kind",
        "recovery_needed", "process_forms_used", "forward_failure", "txid", "workflow", "consent_required",
        "official", "source", "destination",
        # L-3
        "network", "offer", "releases", "installed_release", "older_release", "download", "high_water",
        "newer_needs_newer_updater", "conflicting_sequences", "releases_listed", "data_releases", "repository",
        # L-4R / L-5
        "user_backup", "software")


def run_op(case, step, args, cfg, stop_at=None, action="go", timeout=900, barrier_timeout=None,
           before_go=None, inject=None, trust=True, net=False, net_timeout=None, net_base=None):
    """action: go | kill | eof | badtoken | timeout | callable(name)->'go'|'kill'."""
    out = os.path.join(WORK, "results", "ops", "%s__%s.json" % (case, step))
    guard(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, TEST_WORKER, args[0],
           "--installation", cfg, "--result", out] + list(args[1:])
    cmd += ["--token", TOKEN, "--scratch-root", RUN, "--forbid", A.game]
    if trust:
        cmd += ["--trust-key", open(os.path.join(RUN, "keys", "test_a.pub"), encoding="ascii").read().strip()]
    if net:
        cmd += ["--net-base", net_base or FAKE.base]
    if net_timeout:
        cmd += ["--net-timeout", str(net_timeout)]
    inject = dict(inject or {})
    if A.process_default and not any(k.startswith("process") for k in inject):
        # Scratch installations are independent of any SFM the owner has open for other work:
        # unless a case asks for a specific (or the real) process status, report CLEAR.
        inject["process"] = A.process_default
    for k, v in inject.items():
        cmd += ["--inject", "%s=%s" % (k, v)]
    if stop_at:
        cmd += ["--stop-at", stop_at]
    if barrier_timeout:
        cmd += ["--barrier-timeout", str(barrier_timeout)]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env=ENV, cwd=os.path.join(RUN, "tmp"))
    events = []
    killed = False
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.strip()
        events.append(line)
        if line.startswith("BARRIER "):
            name = line.split(" ", 1)[1]
            act = action(name) if callable(action) else action
            if before_go:
                events.append("before_go:%s" % before_go(name))
            if act == "go":
                p.stdin.write("GO %s %s\n" % (name, TOKEN))
                p.stdin.flush()
            elif act == "kill":
                p.kill()
                killed = True
                break
            elif act == "eof":
                p.stdin.close()
            elif act == "badtoken":
                p.stdin.write("GO %s %s\n" % (name, "wrong" + TOKEN))
                p.stdin.flush()
            elif act == "timeout":
                pass  # say nothing; the worker's own barrier timeout must fire
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        events.append("CONTROLLER_TIMEOUT")
    err = p.stderr.read()
    res = None
    if not killed and os.path.exists(out):
        res = jload(out)
    r = {"step": step, "args": [a for a in args], "stop_at": stop_at,
         "action": action if not callable(action) else "custom", "inject": inject,
         "killed": killed, "events": events, "rc": p.returncode, "stderr_tail": err[-600:],
         "outcome": (res or {}).get("outcome"), "message": (res or {}).get("message"),
         "details": (res or {}).get("details"), "transactions": [
             {k: t.get(k) for k in ("txid", "outcome", "message", "observed_k", "from_k", "terminal",
                                     "verified", "details")} for t in (res or {}).get("transactions", [])],
         "seconds": round(time.time() - t0, 2), "result_file": os.path.relpath(out, WORK)}
    for k in KEEP:
        if res and k in res:
            r[k] = res[k]
    if res:
        r["trace_summary"] = classify_trace(cfg, res.get("trace"))
    return r


def prepare(case, step, cfg, kind, source=None, inject=None):
    """kind: rebuild (Rebuild My Data) | replace (Use Another TXT, product `prepare-import`)."""
    a = ["prepare-rebuild"] if kind == "rebuild" else ["prepare-import", "--source", source]
    return run_op(case, step + "__prep", a, cfg, inject=inject)


def install(case, step, cfg, prepid, confirm, accept=False, **kw):
    a = ["install", "--prepared", prepid, "--confirm-sha", confirm] + (["--accept-replacement"] if accept else [])
    return run_op(case, step, a, cfg, **kw)


def activate(case, step, cfg, kind, confirm, source=None, prep_inject=None, accept=None, **kw):
    """P1 `activate` = product prepare (staging) + install. Barriers, kills and injections
    apply to the install process. A failed preparation is returned as the step. An import
    gives explicit replacement consent unless accept=False (the user confirmed the preview)."""
    pr = prepare(case, step, cfg, kind, source, inject=prep_inject)
    if pr["outcome"] != "PREPARED":
        pr["stage"] = "prepare"
        return pr
    st = install(case, step, cfg, pr["prepid"], confirm, accept=(kind == "replace") if accept is None else accept, **kw)
    st["prepare"] = {k: pr.get(k) for k in ("outcome", "message", "prepid", "confirm_sha", "process_status",
                                            "candidate", "seconds", "consent_required", "workflow")}
    return st


def recover(case, step, cfg, policy="resume", **kw):
    return run_op(case, step, ["recover", "--policy", policy], cfg, **kw)


def status(case, step, cfg, **kw):
    return run_op(case, step, ["status"], cfg, **kw)


def py27_select(cfg):
    """Unchanged selector (hash-verified .py-only copy) under SFM's bundled Python 2.7, outside SFM."""
    out = os.path.join(WORK, "results", "py27", "%s.json" % uuid.uuid4().hex[:10])
    guard(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    script = os.path.join(RUN, "py27lib", "py27_select.py")
    cp = subprocess.run([A.py27, "-E", "-s", "-B", script, "select", cfg, out],
                        capture_output=True, text=True, env=ENV, cwd=os.path.join(RUN, "tmp"), timeout=300)
    if not os.path.exists(out):
        return {"error": cp.stderr[-600:], "rc": cp.returncode}
    return jload(out)


def select_ok(cfg, g):
    s = py27_select(cfg)
    ok = s.get("selected_basename") == GEN[g]["sidecar"] and s.get("python", "").startswith("2.7")
    return ok, s


def py3(script, *args, **kw):
    return subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, os.path.join(SUPPORT, script)]
                          + list(args), capture_output=True, text=True, env=ENV, cwd=os.path.join(RUN, "tmp"),
                          timeout=kw.get("timeout", 120))


def start_holder(script, *args):
    p = subprocess.Popen([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, os.path.join(SUPPORT, script)]
                         + list(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env=ENV, cwd=os.path.join(RUN, "tmp"))
    first = p.stdout.readline().strip()
    return p, first


def release(p):
    try:
        p.stdin.write("release\n")
        p.stdin.flush()
    except OSError:
        pass
    try:
        out = p.communicate(timeout=60)[0]
    except subprocess.TimeoutExpired:
        p.kill()
        out = "KILLED"
    return out.strip()


def racer(*args):
    cp = py3("racer.py", *args)
    try:
        return json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception:
        return {"raw": cp.stdout[-300:], "err": cp.stderr[-300:]}


def junction(link, target):
    guard(link)
    cp = subprocess.run(["cmd", "/c", "mklink", "/J", os.path.abspath(link), os.path.abspath(target)],
                        capture_output=True, text=True)
    return cp.returncode == 0


def rec_terminal_ok(step):
    return step["outcome"] in ("OK", "NOTHING_TO_RECOVER") and all(
        x["outcome"] == "TERMINAL" for x in step["transactions"])


def finalize_case(case, cfg, steps, verdict, why, extra=None):
    rec = {"case": case, "verdict": verdict, "why": why, "steps": steps, "inst_id": inst_id(case), "cfg": cfg,
           "final_tree": tree(cfg) if cfg and os.path.isdir(cfg) else None,
           "final_staging": ({k: v for k, v in tree(cfg, True).items() if k.startswith(STAGING_PREFIX)}
                             if cfg and os.path.isdir(cfg) else None)}
    if extra:
        rec.update(extra)
    out = os.path.join(WORK, "results", "cases", case + ".json")
    guard(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "x", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True, default=str)
    print("%-6s %-58s %s" % (verdict, case, why[:110]))
    sys.stdout.flush()
    return {"case": case, "verdict": verdict, "why": why}


def outcomes(steps):
    return [x.get("outcome") for x in steps]


RUNNING = 'output:"sfm.exe","4242","Console","1","1,000 K"'


# ------------------------------------------------------------------ groups
def group_A():
    """Canonical real-artifact operations (P1 categories 1, 2, 8, 11)."""
    R = []
    cfg = make_install("A1_import_G3")
    s = [activate("A1_import_G3", "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    ok, d = final_is(cfg, ("G3", "g3"))
    sel_ok, sel = select_ok(cfg, "g3")
    src_untouched = sha_file(G3_TXT) == SHA["G3"]
    corr = (s[0].get("correspondence") or {}).get("ok") is True
    v = s[0]["outcome"] == "COMPLETE" and ok and sel_ok and src_untouched and corr
    R.append(finalize_case("A1_import_G3", cfg, s, "PASS" if v else "FAIL",
                           "COMPLETE; exact G3 set; correspondence verified; selector picks G3; import source unchanged"
                           if v else "unexpected: %s" % [s[0]["outcome"], ok, sel_ok, src_untouched, corr],
                           {"final_check": d, "selector": sel}))
    cfg = make_install("A2_rebuild_stale", master="G3", gens=("g1",), manifest="g1")
    s = [activate("A2_rebuild_stale", "act", cfg, "rebuild", SHA["G3"])]
    ok, d = final_is(cfg, ("G3", "g3"))
    sel_ok, sel = select_ok(cfg, "g3")
    master_bytes_same = sha_file(os.path.join(cfg, "sfm_defaultanimationgroups.txt")) == SHA["G3"]
    corr = (s[0].get("correspondence") or {}).get("ok") is True
    v = s[0]["outcome"] == "COMPLETE" and ok and sel_ok and master_bytes_same and corr
    R.append(finalize_case("A2_rebuild_stale", cfg, s, "PASS" if v else "FAIL",
                           "rebuild COMPLETE; TXT not rewritten; G1 artifact retired; correspondence verified; "
                           "selector picks G3" if v else "unexpected", {"final_check": d, "selector": sel}))
    cfg = make_install("A3_noop")
    before = tree(cfg)
    s = [activate("A3_noop", "act", cfg, "rebuild", SHA["G1"])]
    after = tree(cfg)
    sel_ok, sel = select_ok(cfg, "g1")
    v = noop_ok(s[0]) and noop_unchanged(before, after) and sel_ok
    R.append(finalize_case("A3_noop", cfg, s, "PASS" if v else "FAIL",
                           "NOOP (C1 shape); active slots byte-identical; selector picks G1" if v else "unexpected",
                           {"selector": sel}))
    cfg = make_install("A4_import_same")
    before = tree(cfg)
    s = [activate("A4_import_same", "act", cfg, "replace", SHA["G1"], source=G1_TXT)]
    v = noop_ok(s[0]) and noop_unchanged(before, tree(cfg))
    R.append(finalize_case("A4_import_same", cfg, s, "PASS" if v else "FAIL",
                           "importing identical bytes is a verified NOOP" if v else "unexpected: %s" % s[0]["outcome"]))
    cfg = make_install("A5_round_trip")
    s = [activate("A5_round_trip", "to_g3", cfg, "replace", SHA["G1"], source=G3_TXT)]
    s.append(activate("A5_round_trip", "to_g1", cfg, "replace", SHA["G3"], source=G1_TXT))
    ok, d = final_is(cfg, ("G1", "g1"))
    t = tree(cfg)
    hist = preserved(t, [GEN["g3"]["sidecar_sha"], SHA["G3"], GEN["g1"]["sidecar_sha"]])
    v = outcomes(s) == ["COMPLETE", "COMPLETE"] and ok and all(hist.values())
    R.append(finalize_case("A5_round_trip", cfg, s, "PASS" if v else "FAIL",
                           "two COMPLETE imports; exact G1 set restored; G3 generation kept in transaction history"
                           if v else "unexpected", {"history": hist}))
    cfg = make_install("A6_two_old_sidecars", gens=("g1", "g2"))
    s = [activate("A6_two_old_sidecars", "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    ok, d = final_is(cfg, ("G3", "g3"))
    t = tree(cfg)
    hist = preserved(t, [GEN["g1"]["sidecar_sha"], GEN["g2"]["sidecar_sha"]])
    v = s[0]["outcome"] == "COMPLETE" and ok and all(hist.values())
    R.append(finalize_case("A6_two_old_sidecars", cfg, s, "PASS" if v else "FAIL",
                           "both prior sidecars retired (preserved); exactly one active artifact"
                           if v else "unexpected", {"history": hist, "final_check": d}))
    crlf = os.path.join(WORK, "inputs", "g3_crlf.txt")
    wbytes(crlf, open(G3_TXT, "rb").read().replace(b"\n", b"\r\n"))
    crlf_sha = sha_file(crlf)
    cfg = make_install("A7_custom_crlf")
    s = [activate("A7_custom_crlf", "act", cfg, "replace", SHA["G1"], source=crlf)]
    m = sha_file(os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
    sc = (s[0].get("candidate") or {}).get("sidecar")
    t = active_set(tree(cfg))
    v = (s[0]["outcome"] == "COMPLETE" and m == crlf_sha and sha_file(crlf) == crlf_sha
         and sc and ("sfm_shared_authority\\" + sc) in t)
    sel = py27_select(cfg)
    v = v and sel.get("selected_basename") == sc
    R.append(finalize_case("A7_custom_crlf", cfg, s, "PASS" if v else "FAIL",
                           "custom CRLF source active byte-exact (no normalization); own sidecar selected; "
                           "external original unchanged" if v else "unexpected",
                           {"crlf_sha256": crlf_sha, "selector": sel}))
    return R


REPLACE_MOVES = 6   # S0 P0 M0 M1 S1 P1
REBUILD_MOVES = 4   # S0 P0 S1 P1
PRE = ["previewed", "candidates_written", "snapshots_written", "locked", "protected"]


def barriers_for(n):
    return PRE + ["act_%s_forward_%d" % (p, i) for i in range(n) for p in ("begin", "moved", "done")] + \
        ["moves_done", "complete"]


def kill_and_recover(case, kind, barrier, policy="resume", rec_kill=None):
    if kind == "replace":
        cfg = make_install(case)
        old, confirm, src = ("G1", "g1"), SHA["G1"], G3_TXT
    else:
        cfg = make_install(case, master="G3", gens=("g1",))
        old, confirm, src = ("G3", "g1"), SHA["G3"], None
    new = ("G3", "g3")
    steps = [activate(case, "act", cfg, kind, confirm, source=src, stop_at=barrier, action="kill")]
    t_crash = tree(cfg)
    if rec_kill:
        steps.append(recover(case, "rec_killed", cfg, policy, stop_at=rec_kill, action="kill"))
    steps.append(recover(case, "rec1", cfg, policy))
    t1 = tree(cfg)
    steps.append(recover(case, "rec2", cfg, policy))
    t2 = tree(cfg)
    fwd = barrier.startswith("act_") or barrier in ("moves_done", "complete")
    if policy == "rollback" and barrier != "complete":
        fwd = False
    exp = new if fwd else old
    final_ok = active_set(t1) == expected_active(exp[0], exp[1])
    idem = t1 == t2 and rec_terminal_ok(steps[-1])
    loss = originals_present(t1, old[0])
    stale = kind == "rebuild" and exp == old
    if stale:
        # The restored OLD rebuild state is the stale pre-existing installation (G3 TXT, G1
        # artifact): the truthful selector result is SidecarMissing via SourceGenerationMismatch.
        sel = py27_select(cfg)
        sel_ok = sel.get("classification") == "SidecarMissing" and \
            [d.get("reason") for d in sel.get("diagnostics", [])] == ["SourceGenerationMismatch"]
    else:
        sel_ok, sel = select_ok(cfg, exp[1])
    # C12 truthful state report (L-1 addition): restored stale data is reported as needing rebuild.
    state_ok = steps[-2].get("installed_state") == ("NEEDS_REBUILD" if stale else "WORKING")
    killed = steps[0]["killed"]
    v = killed and final_ok and idem and all(loss.values()) and sel_ok and state_ok
    return finalize_case(case, cfg, steps, "PASS" if v else "FAIL",
                         "kill@%s -> recover(%s) -> exact %s set; 2nd recovery no-op; originals preserved; "
                         "selector ok; state %s" % (barrier, policy, "NEW" if fwd else "OLD",
                                                    steps[-2].get("installed_state")) if v else
                         "killed=%s final_ok=%s idem=%s loss=%s sel=%s state=%s" % (
                             killed, final_ok, idem, loss, sel_ok, steps[-2].get("installed_state")),
                         {"crash_tree": t_crash, "selector": sel, "expected": "NEW" if fwd else "OLD"})


def group_B():
    """Interrupted forward transactions and reverse/forward recovery (P1 category 4)."""
    R = []
    for b in barriers_for(REPLACE_MOVES):
        R.append(kill_and_recover("B_rep_%s" % b, "replace", b))
    for b in barriers_for(REBUILD_MOVES):
        R.append(kill_and_recover("B_reb_%s" % b, "rebuild", b))
    for i in range(REPLACE_MOVES):
        R.append(kill_and_recover("B_rollback_moved_%d" % i, "replace", "act_moved_forward_%d" % i,
                                  policy="rollback"))
    rec_barriers = ["rec_protected"] + ["rec_%s_forward_%d" % (p, i) for i in range(3, 6)
                                        for p in ("begin", "moved", "done")]
    for rb in rec_barriers:
        R.append(kill_and_recover("B_reckill_%s" % rb, "replace", "act_done_forward_2", rec_kill=rb))
    for rb in ["rec_%s_rollback_%d" % (p, i) for i in (3, 1) for p in ("begin", "moved", "done")]:
        R.append(kill_and_recover("B_rbkill_%s" % rb, "replace", "act_done_forward_3", policy="rollback",
                                  rec_kill=rb))
    return R


def group_C():
    """Newer-data preservation after interruption (P1 category 4) -- no destructive restore."""
    R = []
    user = b"USER NEWER TXT WRITTEN AFTER THE INTERRUPTION\n"

    def case(name, barrier, mutate, policy="resume", expect_key="TXT_CHANGED"):
        cfg = make_install(name)
        s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at=barrier, action="kill")]
        info = mutate(cfg)
        t0 = tree(cfg)
        s.append(recover(name, "rec1", cfg, policy))
        t1 = tree(cfg)
        s.append(recover(name, "rec2", cfg, policy))
        t2 = tree(cfg)
        msg = (s[1]["transactions"] or [{}])[0].get("message") or ""
        want_msg = {"TXT_CHANGED": "Your TXT changed", "MISSING": "Automatic recovery is unavailable"}[expect_key]
        conflict = s[1]["outcome"] == "CONFLICT" and want_msg in msg
        nj = lambda t: {k: v for k, v in t.items() if not k.endswith("\\journal")}  # noqa: E731
        untouched = nj(t0) == nj(t1) == nj(t2)  # recovery may only append its CONFLICT record
        kept = originals_present(t1)
        v = conflict and untouched and all(kept.values())
        return finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                             "%s; recovery CONFLICT '%s'; no file moved or overwritten (twice); originals kept"
                             % (info, want_msg) if v else "conflict=%s untouched=%s kept=%s msg=%r"
                             % (conflict, untouched, kept, msg))

    def new_master_in_vacant_slot(cfg):
        wbytes(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), user)
        return "user created a new TXT in the vacated Master slot (k=3)"

    def edit_active_g3(cfg):
        wappend(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), b"\n// user edit after interruption\n")
        return "user edited the newly active TXT in place (k=4)"

    def lose_candidate(cfg):
        td = txdirs(cfg)[0]
        cand = [n for n in os.listdir(os.path.join(td, "candidate")) if n.endswith(".sfmsidecar")][0]
        wremove(os.path.join(td, "candidate", cand))
        return "candidate sidecar lost before recovery (k=2)"

    R.append(case("C1_new_txt_in_vacant_slot", "act_done_forward_2", new_master_in_vacant_slot))
    R.append(case("C2_edit_after_cutover", "act_done_forward_3", edit_active_g3))
    R.append(case("C3_edit_after_cutover_rollback", "act_done_forward_3", edit_active_g3, policy="rollback"))
    R.append(case("C4_candidate_lost", "act_done_forward_1", lose_candidate, expect_key="MISSING"))
    name = "C5_edit_before_protection"
    cfg = make_install(name)

    def edit_now(b):
        if b == "snapshots_written":
            wappend(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), b"\n// edit before protection\n")
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="snapshots_written",
                  before_go=edit_now)]
    t = tree(cfg)
    edited = t["sfm_defaultanimationgroups.txt"] not in (SHA["G1"], SHA["G3"])
    v = s[0]["outcome"] == "ABANDONED" and edited and \
        active_set(t)["sfm_shared_authority\\" + GEN["g1"]["sidecar"]] == GEN["g1"]["sidecar_sha"]
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "edit after snapshot detected through held handles -> ABANDONED; edited TXT active and "
                           "kept; nothing moved" if v else "unexpected %s" % s[0]["outcome"]))
    return R


def group_D():
    """Occupied destinations, source substitution, competing actors (P1 category 3)."""
    R = []
    dests = {0: ("retired", GEN["g1"]["sidecar"]), 1: ("retired", "manifest.json"), 2: ("retired", "master.txt"),
             3: ("master", None), 4: ("auth", GEN["g3"]["sidecar"])}
    for i, (kind, nm) in dests.items():
        name = "D_occupied_dest_%d" % i
        cfg = make_install(name)
        occ = ("OCCUPANT FOR MOVE %d\n" % i).encode()

        def place(b, i=i, kind=kind, nm=nm, cfg=cfg, occ=occ):
            if b == "act_begin_forward_%d" % i:
                if kind == "retired":
                    p = os.path.join(txdirs(cfg)[0], "retired", nm)
                elif kind == "master":
                    p = os.path.join(cfg, "sfm_defaultanimationgroups.txt")
                else:
                    p = os.path.join(cfg, "sfm_shared_authority", nm)
                if not os.path.exists(p):
                    wbytes(p, occ)
            return b
        s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_begin_forward_%d" % i,
                      before_go=place)]
        s.append(recover(name, "rec1", cfg))
        t1 = tree(cfg)
        occ_kept = sha(occ) in t1.values()
        kept = originals_present(t1)
        no_success = s[0]["outcome"] in ("ROLLED_BACK", "CONFLICT")
        v = occ_kept and all(kept.values()) and no_success and s[1]["outcome"] in ("OK", "CONFLICT",
                                                                                   "NOTHING_TO_RECOVER")
        R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                               "occupant at move %d destination: %s; occupant bytes kept; originals kept; "
                               "recovery %s" % (i, s[0]["outcome"], s[1]["outcome"]) if v else
                               "occ_kept=%s kept=%s outcome=%s" % (occ_kept, kept, s[0]["outcome"]),
                               {"forward_failure": s[0].get("forward_failure")}))
    name = "D_occupied_dest_5_after_vacate"
    cfg = make_install(name)
    occ = b"OCCUPANT FOR MOVE 5 (manifest)\n"

    def place5(b):
        if b == "act_begin_forward_5":
            wbytes(os.path.join(cfg, "sfm_shared_authority", "manifest.json"), occ)
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_begin_forward_5",
                  before_go=place5)]
    t1 = tree(cfg)
    v = s[0]["outcome"] in ("ROLLED_BACK", "CONFLICT") and sha(occ) in t1.values() and \
        all(originals_present(t1).values())
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "manifest-slot occupant after vacate: %s; occupant and originals kept" % s[0]["outcome"]
                           if v else "unexpected %s" % s[0]["outcome"]))
    name = "D_substitute_before_protection"
    cfg = make_install(name)
    rr = {}

    def sub(b):
        if b == "locked":
            rr["r"] = racer("movereplace", os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="locked", before_go=sub)]
    t = tree(cfg)
    sub_kept = rr["r"].get("result_sha256") in t.values()
    v = s[0]["outcome"] == "ABANDONED" and sub_kept and rr["r"].get("ok") is True
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "substituted TXT detected (identity/bytes) -> ABANDONED; substitute kept active"
                           if v else "unexpected %s %s" % (s[0]["outcome"], rr), {"racer": rr}))
    name = "D_import_source_changed"
    src = os.path.join(WORK, "inputs", "import_copy_D9.txt")
    wcopy(G3_TXT, src)
    cfg = make_install(name)

    def change_src(b):
        if b == "candidates_written":
            guard(src)
            with open(src, "wb") as f:
                f.write(open(G2_TXT, "rb").read())
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=src, stop_at="candidates_written",
                  before_go=change_src)]
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok and sha_file(src) == SHA["G2"]
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "captured G3 snapshot installed; later change to the external file ignored and "
                           "untouched" if v else "unexpected"))
    name = "D_racers_during_protection"
    cfg = make_install(name)
    rr = []

    def races(b):
        if b == "protected":
            m = os.path.join(cfg, "sfm_defaultanimationgroups.txt")
            a = os.path.join(cfg, "sfm_shared_authority")
            for act in ("inplace", "inplace_py", "replacefile", "movereplace", "delete"):
                rr.append({"target": "master", **racer(act, m)})
            rr.append({"target": "master", **racer("rename", m, os.path.join(cfg, "renamed_master.txt"))})
            for nm in (GEN["g1"]["sidecar"], "manifest.json", "publisher.lock"):
                rr.append({"target": nm, **racer("delete", os.path.join(a, nm))})
                rr.append({"target": nm, **racer("rename", os.path.join(a, nm), os.path.join(cfg, nm + ".moved"))})
                rr.append({"target": nm, **racer("inplace", os.path.join(a, nm))})
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="protected", before_go=races)]
    ok, d = final_is(cfg, ("G3", "g3"))
    refused = all(r.get("ok") is False for r in rr)
    v = s[0]["outcome"] == "COMPLETE" and ok and refused and len(rr) == 15
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "15 competing writes/replaces/deletes/renames (Master, sidecar, manifest, "
                           "publisher.lock) all refused; activation COMPLETE with exact G3 set"
                           if v else "unexpected %s refused=%s" % (s[0]["outcome"], refused), {"racers": rr}))
    name = "D_new_child_during_protection"
    cfg = make_install(name)

    def child(b):
        if b == "act_done_forward_4":
            wbytes(os.path.join(cfg, "sfm_shared_authority", "unexpected_new_child.tmp"), b"X")
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_done_forward_4",
                  before_go=child)]
    t = tree(cfg)
    v = s[0]["outcome"] == "CONFLICT" and "sfm_shared_authority\\unexpected_new_child.tmp" in t and \
        all(originals_present(t).values())
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "unexpected new authority child detected by final exact-inventory check -> CONFLICT, "
                           "no success claimed, nothing deleted" if v else "unexpected %s" % s[0]["outcome"]))
    return R


def group_E():
    """Malformed, incomplete, inconsistent and conflicting states (P1 category 5)."""
    R = []

    def refused(name, cfg, s, want=("REFUSED",), extra_ok=True, why=""):
        before = s.pop()
        t = tree(cfg)
        v = s[0]["outcome"] in want and noop_unchanged(before, t) and extra_ok
        return finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                             "%s -> %s; active slots unchanged" % (why, s[0]["outcome"]) if v else
                             "unexpected %s %s" % (s[0]["outcome"], s[0].get("details")))
    cfg = make_install("E1_unknown_auth_file")
    wbytes(os.path.join(cfg, "sfm_shared_authority", "sfm_master_0_tmp.partial"), b"partial")
    b = tree(cfg)
    R.append(refused("E1_unknown_auth_file", cfg,
                     [activate("E1_unknown_auth_file", "act", cfg, "replace", SHA["G1"], source=G3_TXT), b],
                     why="unrecognized authority file"))
    cfg = make_install("E2_wrong_format_sidecar_name")
    wcopy(GEN["g1"]["sidecar_path"], os.path.join(cfg, "sfm_shared_authority",
                                                  GEN["g1"]["sidecar"].replace("_0_", "_1_")))
    b = tree(cfg)
    R.append(refused("E2_wrong_format_sidecar_name", cfg,
                     [activate("E2_wrong_format_sidecar_name", "act", cfg, "replace", SHA["G1"], source=G3_TXT), b],
                     why="sidecar-like file of an unknown format version"))
    bad_src = os.path.join(WORK, "inputs", "malformed.txt")
    wbytes(bad_src, open(G3_TXT, "rb").read()[:200000])
    cfg = make_install("E3_malformed_import")
    b = tree(cfg)
    R.append(refused("E3_malformed_import", cfg,
                     [activate("E3_malformed_import", "act", cfg, "replace", SHA["G1"], source=bad_src), b],
                     extra_ok=not os.listdir(os.path.join(cfg, "sfm_character_tools_updater", "transactions")),
                     why="truncated (grammatically invalid) import; no transaction created"))
    cfg = make_install("E4_master_missing")
    wremove(os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
    b = tree(cfg)
    R.append(refused("E4_master_missing", cfg,
                     [activate("E4_master_missing", "act", cfg, "rebuild", SHA["G1"]), b], why="active TXT absent"))
    cfg = make_install("E5_master_hardlinked")
    guard(os.path.join(cfg, "hardlink_to_master.txt"))
    os.link(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), os.path.join(cfg, "hardlink_to_master.txt"))
    b = tree(cfg)
    R.append(refused("E5_master_hardlinked", cfg,
                     [activate("E5_master_hardlinked", "act", cfg, "replace", SHA["G1"], source=G3_TXT), b],
                     why="active TXT has a second hard link"))
    cfg = make_install("E6_stale_confirmation")
    b = tree(cfg)
    R.append(refused("E6_stale_confirmation", cfg,
                     [activate("E6_stale_confirmation", "act", cfg, "replace", SHA["G2"], source=G3_TXT), b],
                     why="confirmation bound to a different destination generation"))
    name = "E7_manifest_absent"
    cfg = make_install(name, manifest=None)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "no prior manifest: plan omits P0; exact G3 set" if v else "unexpected"))
    name = "E8_corrupt_prior_sidecar"
    cfg = make_install(name, gens=())
    junk = b"CORRUPT SIDECAR BYTES " * 1000
    wbytes(os.path.join(cfg, "sfm_shared_authority", GEN["g1"]["sidecar"]), junk)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    t = tree(cfg)
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok and sha(junk) in t.values()
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "corrupt prior artifact retired (bytes preserved), never selected" if v else "unexpected"))
    name = "E9_unknown_journal_schema"
    cfg = make_install(name)
    txid = uuid.uuid4().hex
    td = os.path.join(cfg, "sfm_character_tools_updater", "transactions", txid)
    wmkdirs(os.path.join(td, "candidate"))
    wbytes(os.path.join(td, "intent.json"), json.dumps({"schema": "future-tx-9", "txid": txid}).encode())
    body = json.dumps({"seq": 0, "rec": {"t": "INTENT", "schema": "future-tx-9", "txid": txid}},
                      sort_keys=True, separators=(",", ":"))
    wbytes(os.path.join(td, "journal"), ("%s\t%s\n" % (body, sha(body.encode()))).encode())
    before = tree(cfg)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    s.append(recover(name, "rec1", cfg))
    t = tree(cfg)
    future_untouched = all(before[k] == t.get(k) for k in before if txid in k)
    v = s[0]["outcome"] == "ABANDONED" and s[1]["outcome"] == "CONFLICT" and future_untouched and \
        active_set(t) == active_set(before) and \
        any("compatible updater" in (x.get("message") or "") for x in s[1]["transactions"])
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "unknown-schema transaction blocks activation; recovery refuses without mutation "
                           "('Use a compatible updater')" if v else "unexpected %s" % outcomes(s)))
    name = "E10_torn_journal_tail"
    cfg = make_install(name)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_moved_forward_2",
                  action="kill")]
    wappend(os.path.join(txdirs(cfg)[0], "journal"), b'{"rec":{"t":"DONE","dir":"forw')
    s.append(recover(name, "rec1", cfg))
    s.append(recover(name, "rec2", cfg))
    ok, d = final_is(cfg, ("G3", "g3"))
    j = open(os.path.join(txdirs(cfg)[0], "journal"), "rb").read()
    v = ok and b"TORN_TAIL" in j and b'{"rec":{"t":"DONE","dir":"forw' in j and rec_terminal_ok(s[2])
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "torn bytes preserved + acknowledged; forward recovery to exact G3 set" if v else
                           "unexpected"))
    name = "E11_journal_missing"
    cfg = make_install(name)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="candidates_written",
                  action="kill")]
    wremove(os.path.join(txdirs(cfg)[0], "journal"))
    s.append(recover(name, "rec1", cfg))
    ok, d = final_is(cfg, ("G1", "g1"))
    v = ok and s[1]["transactions"] and s[1]["transactions"][0]["outcome"] == "ABANDONED"
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "missing journal: original state verified before declaring ABANDONED" if v else
                           "unexpected"))
    name = "E12_reparse_auth_dir"
    cfg = make_install(name)
    real_auth = os.path.join(WORK, "i", inst_id(name), "auth_real")
    guard(real_auth)
    os.rename(os.path.join(cfg, "sfm_shared_authority"), real_auth)
    jok = junction(os.path.join(cfg, "sfm_shared_authority"), real_auth)
    before = tree(cfg)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    v = jok and s[0]["outcome"] == "REFUSED" and "reparse" in json.dumps(s[0]["details"]) and tree(cfg) == before
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "junction authority directory refused before any write" if v else "unexpected"))
    return R


def group_F():
    """Alias ownership and single publication owner (P1 category 6, same-account scope)."""
    R = []
    name = "F1_lock_held_by_other"
    cfg = make_install(name)
    lockp = os.path.join(cfg, LOCK_REL)
    p, first = start_holder("racer.py", "lock", lockp)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    release(p)
    s.append(recover(name, "rec1", cfg))
    s.append(activate(name, "act2", cfg, "replace", SHA["G1"], source=G3_TXT))
    ok, d = final_is(cfg, ("G3", "g3"))
    v = "ACQUIRED" in first and s[0]["outcome"] == "ABANDONED" and ok and s[2]["outcome"] == "COMPLETE"
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "lock held elsewhere -> ABANDONED before protection; after release the retry COMPLETEs"
                           if v else "unexpected %s %s" % (first, outcomes(s))))
    name = "F2_lock_aliases"
    cfg = make_install(name)
    lockp = os.path.join(cfg, LOCK_REL)
    jroot = os.path.join(WORK, "i", inst_id(name), "alias_junction")
    junction(jroot, os.path.join(cfg, "sfm_character_tools_updater"))
    import ctypes
    buf = ctypes.create_unicode_buffer(2048)
    wbytes(lockp, b"")
    ctypes.windll.kernel32.GetShortPathNameW("\\\\?\\" + lockp, buf, 2048)
    short = buf.value[4:] if buf.value.startswith("\\\\?\\") else buf.value
    aliases = {"junction": os.path.join(jroot, "installation.lock"), "upper_case": lockp.upper(),
               "extended_prefix": "\\\\?\\" + lockp, "dotdot": os.path.join(cfg, "sfm_shared_authority", "..",
                                                                          "sfm_character_tools_updater",
                                                                          "installation.lock")}
    if short and short.lower() != lockp.lower():
        aliases["short_8dot3"] = short
    p, first = start_holder("racer.py", "lock", lockp)
    res = {}
    for k, v in aliases.items():
        q, f2 = start_holder("racer.py", "lock", v)
        res[k] = f2
        release(q)
    release(p)
    q, f3 = start_holder("racer.py", "lock", aliases["junction"])
    q2, f4 = start_holder("racer.py", "lock", lockp)
    release(q2)
    release(q)
    allref = all('"REFUSED"' in x for x in res.values()) and '"REFUSED"' in f4
    R.append(finalize_case(name, cfg, [], "PASS" if allref else "FAIL",
                           "canonical holder refuses %d aliases (%s) with 32; junction holder refuses canonical"
                           % (len(aliases), ", ".join(sorted(aliases))) if allref else "unexpected",
                           {"alias_results": res, "reverse": f4, "8dot3_available": "short_8dot3" in aliases}))
    name = "F3_activate_via_junction"
    cfg = make_install(name)
    jl = os.path.join(WORK, "i", inst_id(name), "cfg_alias")
    junction(jl, cfg)
    s = [activate(name, "act", jl, "replace", SHA["G1"], source=G3_TXT)]
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "alias resolved to the physical installation; exact G3 set" if v else "unexpected"))
    name = "F4_alias_outside_scratch_refused"
    target = A.outside_target  # an existing directory outside the scratch root; only listed, never written
    jl = os.path.join(WORK, "inst", name)
    os.makedirs(os.path.dirname(jl), exist_ok=True)
    jok = junction(jl, target)
    before = sorted(os.listdir(target))
    s = [run_op(name, "act", ["prepare-rebuild"], cfg=jl)]
    v = jok and s[0]["outcome"] == "REFUSED" and "outside the L-1 scratch root" in json.dumps(s[0]["details"]) and \
        sorted(os.listdir(target)) == before
    R.append(finalize_case(name, None, s, "PASS" if v else "FAIL",
                           "installation resolving outside the scratch root refused; target unchanged"
                           if v else "unexpected"))
    name = "F5_concurrent_activations"
    cfg = make_install(name)
    other = {}

    def second(b):
        if b == "locked":
            other["s"] = activate(name, "act_second", cfg, "replace", SHA["G1"], source=G3_TXT)
            other["r"] = recover(name, "rec_while_held", cfg)
        return b
    s = [activate(name, "act_first", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="locked", before_go=second)]
    s += [other["s"], other["r"]]
    s.append(recover(name, "rec_after", cfg))
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and other["s"]["outcome"] == "ABANDONED" and \
        other["r"]["outcome"] in ("REFUSED", "ERROR") and ok and rec_terminal_ok(s[-1])
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "second activation ABANDONED (lock 32) and recovery refused while the owner held the "
                           "lock; owner COMPLETE; exact G3 set" if v else "unexpected %s" % outcomes(s)))
    return R


def group_G():
    """Legacy publisher.lock recognition and in-place preservation (P1 category 7)."""
    R = []
    sys.path.insert(0, UPDATER)
    from sfm_character_tools_updater import w32
    name = "G1_lock_identity_preserved"
    cfg = make_install(name)
    lp = os.path.join(cfg, "sfm_shared_authority", "publisher.lock")

    def ident(p):
        h, e = w32.create_file(p, w32.FILE_READ_ATTRIBUTES, 7, w32.OPEN_EXISTING)
        i = (w32.file_id(h), os.path.getmtime(p), os.path.getsize(p))
        w32.close(h)
        return i
    i0 = ident(lp)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    i1 = ident(lp)
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok and i0 == i1
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "publisher.lock recognized; same FileId, mtime and size 0 after activation" if v else
                           "unexpected %s %s %s" % (s[0]["outcome"], i0, i1)))
    name = "G2_legacy_publisher_active"
    cfg = make_install(name)
    p, first = start_holder("legacy_pub.py", "hold", os.path.join(cfg, "sfm_shared_authority", "publisher.lock"))
    before = tree(cfg)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    after = tree(cfg)
    rel = release(p)
    v = first == "HELD" and s[0]["outcome"] == "REFUSED" and "legacy publisher may be active" in \
        json.dumps(s[0]["details"]) and noop_unchanged(before, after) and \
        not os.listdir(os.path.join(cfg, "sfm_character_tools_updater", "transactions"))
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "real legacy _ExclusiveFileLock held -> REFUSED 'a legacy publisher may be active'; "
                           "nothing written" if v else "unexpected %s %s" % (first, s[0]["outcome"]),
                           {"legacy_release": rel}))
    name = "G3_legacy_publisher_blocked_during_activation"
    cfg = make_install(name)
    tried = {}

    def attempt(b):
        if b == "act_done_forward_3":
            cp = py3("legacy_pub.py", "try", os.path.join(cfg, "sfm_shared_authority", "publisher.lock"))
            tried["r"] = cp.stdout.strip()
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_done_forward_3",
                  before_go=attempt)]
    after_try = py3("legacy_pub.py", "try", os.path.join(cfg, "sfm_shared_authority", "publisher.lock")).stdout.strip()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["outcome"] == "COMPLETE" and ok and '"acquired": false' in tried.get("r", "") and \
        '"acquired": true' in after_try
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "legacy lock acquisition fails while activation holds publisher.lock; succeeds after; "
                           "exact G3 set" if v else "unexpected %s %s" % (tried, after_try),
                           {"during": tried.get("r"), "after": after_try}))

    def nonempty(lp):
        wappend(lp, b"x")

    def hardlink(lp):
        q = os.path.join(os.path.dirname(os.path.dirname(lp)), "lock_link")
        guard(q)
        os.link(lp, q)

    def directory(lp):
        wremove(lp)
        wmkdirs(lp)
    for nm, mut, why in (("G4_lock_not_empty", nonempty, "non-empty publisher.lock"),
                         ("G5_lock_hardlinked", hardlink, "hard-linked publisher.lock"),
                         ("G6_lock_is_directory", directory, "publisher.lock is a directory")):
        cfg = make_install(nm)
        mut(os.path.join(cfg, "sfm_shared_authority", "publisher.lock"))
        b = tree(cfg)
        s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
        v = s[0]["outcome"] == "REFUSED" and noop_unchanged(b, tree(cfg))
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "%s -> REFUSED, unchanged" % why if v else "unexpected %s %s" % (
                                   s[0]["outcome"], s[0]["details"])))
    name = "G7_lock_absent"
    cfg = make_install(name, legacy_lock=False)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    ok, d = final_is(cfg, ("G3", "g3"), legacy_lock=False)
    v = s[0]["outcome"] == "COMPLETE" and ok
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "no publisher.lock: completes; none created" if v else "unexpected"))
    name = "G8_legacy_starts_before_protection"
    cfg = make_install(name)
    hp = {}

    def grab(b):
        if b == "locked":
            hp["p"], hp["first"] = start_holder("legacy_pub.py", "hold",
                                                os.path.join(cfg, "sfm_shared_authority", "publisher.lock"))
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="locked", before_go=grab)]
    release(hp["p"])
    s.append(recover(name, "rec1", cfg))
    ok, d = final_is(cfg, ("G1", "g1"))
    v = hp["first"] == "HELD" and s[0]["outcome"] == "ABANDONED" and ok and rec_terminal_ok(s[1])
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "legacy publisher started after preview -> ABANDONED at protection; exact G1 set"
                           if v else "unexpected %s" % outcomes(s)))
    name = "G9_lock_replaced_before_protection"
    cfg = make_install(name)

    def swap(b):
        if b == "locked":
            lp = os.path.join(cfg, "sfm_shared_authority", "publisher.lock")
            wremove(lp)
            wbytes(lp, b"")
        return b
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="locked", before_go=swap)]
    ok, d = final_is(cfg, ("G1", "g1"))
    v = s[0]["outcome"] == "ABANDONED" and "identity changed" in json.dumps(s[0]["details"]) and ok
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "publisher.lock replaced by a different empty file -> identity mismatch -> ABANDONED"
                           if v else "unexpected %s %s" % (s[0]["outcome"], s[0]["details"])))
    return R


def group_H():
    """Selector behaviour on prepared states (P1 category 8; Py2.7, outside SFM)."""
    R = []
    cfg = make_install("H1_two_art", gens=("g1", "g3"))
    sel = py27_select(cfg)
    v = sel.get("selected_basename") == GEN["g1"]["sidecar"] and GEN["g1"]["sidecar"] > GEN["g3"]["sidecar"]
    R.append(finalize_case("H1_two_art", cfg, [], "PASS" if v else "FAIL",
                           "G1 Master with G3 (sorts first) + G1 artifacts: selector skips the mismatch and selects "
                           "G1 by source hash" if v else "unexpected", {"selector": sel}))
    cfg = make_install("H2_no_matching_artifact", master="G3", gens=("g1",))
    sel = py27_select(cfg)
    v = sel.get("classification") == "SidecarMissing"
    R.append(finalize_case("H2_no_matching_artifact", cfg, [], "PASS" if v else "FAIL",
                           "stale authority (G3 Master, G1 artifact only) -> SidecarMissing, no fallback" if v else
                           "unexpected", {"selector": sel}))
    return R


def group_I():
    """Broker-level sharing-violation classification (P1 category 9). Library level only."""
    R = []
    cfg = make_install("I_sharing")
    m = os.path.join(cfg, "sfm_defaultanimationgroups.txt")
    sc = os.path.join(cfg, "sfm_shared_authority", GEN["g1"]["sidecar"])
    mf = os.path.join(cfg, "sfm_shared_authority", "manifest.json")
    rows = []
    for label, path, acc, share, want in (
            ("updater protection on Master (READ|DELETE, share 0)", m, "rd", 0, "MasterUnreadable"),
            ("updater protection on sidecar (READ|DELETE, share 0)", sc, "rd", 0, "SidecarMissing"),
            ("Normalizer-style read handle on Master (share READ)", m, "r", 1, "SELECTED"),
            ("updater protection on manifest (share 0)", mf, "rd", 0, "SELECTED")):
        p, first = start_holder("hold.py", path, acc, str(share))
        sel = py27_select(cfg)
        release(p)
        rows.append({"label": label, "holder": first, "classification": sel.get("classification"),
                     "diagnostics": sel.get("diagnostics"), "detail": sel.get("detail"), "want": want})
    v = all(r["classification"] == r["want"] and '"held": true' in r["holder"] for r in rows)
    R.append(finalize_case("I1_broker_classification", cfg, [], "PASS" if v else "FAIL",
                           "Py2.7 library: protected Master -> MasterUnreadable; protected sidecar -> skipped, "
                           "SidecarMissing; share-read Master -> SELECTED; manifest not consulted" if v else
                           "unexpected %s" % [(r["label"][:20], r["classification"]) for r in rows], {"rows": rows}))
    name = "I2_normalizer_handle_blocks_updater"
    cfg = make_install(name)
    p, first = start_holder("hold.py", os.path.join(cfg, "sfm_defaultanimationgroups.txt"), "r", "1")
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    release(p)
    s.append(recover(name, "rec1", cfg))
    ok, d = final_is(cfg, ("G1", "g1"))
    v = s[0]["outcome"] == "ABANDONED" and "ERROR_SHARING_VIOLATION" in json.dumps(s[0]["details"]) and ok
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "Normalizer-style share-read handle -> updater protection fails 32 -> ABANDONED; "
                           "exact G1 set" if v else "unexpected %s %s" % (s[0]["outcome"], s[0]["details"])))
    return R


def group_J():
    """A3 process status and fail-closed barriers (P1 category 10). In the product the pre-lock
    gate refuses first: REFUSED with nothing created (P1: ABANDONED at the post-lock gate; that
    path is covered by X5)."""
    R = []
    for nm, inj, want in (("J1_process_running", RUNNING, "RUNNING"),
                          ("J2_query_exception", "raise", "UNKNOWN"),
                          ("J3_query_nonzero_exit", "rc:5", "UNKNOWN"),
                          ("J4_query_empty_output", "output:", "UNKNOWN"),
                          ("J5_query_unparseable", "output:ERROR: something odd", "UNKNOWN"),
                          ("J6_query_other_image", 'output:"notsfm.exe","1","Console","1","1 K"', "UNKNOWN")):
        cfg = make_install(nm)
        before = tree(cfg)
        s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT, inject={"process": inj})]
        mid = tree(cfg)
        s.append(recover(nm, "rec_with_same_status", cfg, inject={"process": inj}))
        s.append(recover(nm, "rec_clear", cfg))
        ok, d = final_is(cfg, ("G1", "g1"))
        v = s[0]["outcome"] == "REFUSED" and want in json.dumps(s[0]["details"]) and zero_excl(s[0]) and \
            before == mid and not txdirs(cfg) and s[1]["outcome"] == "REFUSED" and ok and rec_terminal_ok(s[2]) \
            and "Close SFM" in (s[0]["message"] or "")
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "process status %s -> install REFUSED at the pre-lock gate (no transaction, no lock, "
                               "0 exclusive opens), recovery REFUSED; exact G1 set" % want if v else
                               "unexpected %s %s" % (outcomes(s), s[0]["details"])))
    for nm, act, at in (("J7_barrier_eof", "eof", "act_moved_forward_2"),
                        ("J8_barrier_bad_token", "badtoken", "act_moved_forward_2"),
                        ("J9_barrier_timeout", "timeout", "act_moved_forward_2"),
                        ("J10_barrier_eof_before_protection", "eof", "protected")):
        cfg = make_install(nm)
        s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at=at, action=act,
                      barrier_timeout=5 if act == "timeout" else None)]
        s.append(recover(nm, "rec1", cfg))
        s.append(recover(nm, "rec2", cfg))
        exp = ("G1", "g1") if at == "protected" else ("G3", "g3")
        ok, d = final_is(cfg, exp)
        v = s[0]["outcome"] == "STOPPED" and ok and rec_terminal_ok(s[2])
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "barrier %s at %s -> STOPPED (no success claimed); recovery -> exact %s set"
                               % (act, at, exp[0]) if v else "unexpected %s" % outcomes(s)))
    return R


def group_K():
    """Path lengths on E: (P1 category 11) under the Amendment §2.3 consumer path budget."""
    R = []
    name = "K1_deep_installation_refused"
    cfg = make_install(name, depth_pad=5)
    before = tree(cfg, include_staging=True)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
    s.append(activate(name, "act_rebuild", cfg, "rebuild", SHA["G1"]))
    after = tree(cfg, include_staging=True)
    v = all(x["outcome"] == "REFUSED" and "budget" in json.dumps(x["details"]) for x in s) and before == after
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "cfg path %d chars: consumer sidecar path over budget -> prepare REFUSED (import and "
                           "rebuild); nothing written" % len(cfg) if v else "unexpected %s" % outcomes(s),
                           {"cfg_len": len(cfg)}))
    name = "K3_long_transaction_paths_in_budget"
    cfg = make_install(name)
    s = [activate(name, "act", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_done_forward_3",
                  action="kill")]
    s.append(recover(name, "rec1", cfg))
    s.append(recover(name, "rec2", cfg))
    ok, d = final_is(cfg, ("G3", "g3"))
    mp = max_path(cfg)
    v = ok and rec_terminal_ok(s[2]) and mp > 260
    R.append(finalize_case(name, cfg, s, "PASS" if v else "FAIL",
                           "consumer paths in budget; transaction paths up to %d chars; kill + recovery to exact G3 "
                           "set" % mp if v else "unexpected", {"cfg_len": len(cfg), "max_path": mp}))
    rows = []
    for target in (259, 260):
        fixed = len(os.path.join(WORK, "inst", "")) + len("\\" + SUBDIR + "\\sfm_shared_authority\\") + \
            len(GEN["g1"]["sidecar"])
        nm = "K2_%d_" % target
        nm += "x" * (target - fixed - len(nm))
        cfg = make_install(nm, base=os.path.join(WORK, "inst", nm))
        sp = os.path.join(cfg, "sfm_shared_authority", GEN["g1"]["sidecar"])
        sel = py27_select(cfg)
        rows.append({"sidecar_path_len": len(sp), "classification": sel.get("classification"),
                     "reasons": [d.get("reason") for d in sel.get("diagnostics", []) if isinstance(d, dict)]})
    v = rows[0]["sidecar_path_len"] == 259 and rows[0]["classification"] == "SELECTED" and \
        rows[1]["sidecar_path_len"] == 260 and rows[1]["classification"] == "SidecarMissing" and \
        rows[1]["reasons"] == ["io_error"]
    R.append(finalize_case("K2_py27_consumer_maxpath", None, [], "PASS" if v else "FAIL",
                           "Py2.7 selector: 259-char sidecar path SELECTED; 260-char path skipped as io_error -> "
                           "SidecarMissing (the boundary the product budget enforces)" if v else "unexpected %s" % rows,
                           {"rows": rows}))
    return R


def group_N():
    """C1 corrected verified-no-op path (p1c1run.py N1-N10), on the product backend."""
    R = []
    for nm, kind, src in (("N1_noop_rebuild_clear", "rebuild", None), ("N2_noop_import_same_clear", "replace", G1_TXT)):
        cfg = make_install(nm)
        before = tree(cfg)
        s = [activate(nm, "noop", cfg, kind, SHA["G1"], source=src)]
        after = tree(cfg)
        sel = py27_select(cfg)
        v = noop_ok(s[0]) and noop_unchanged(before, after) and sel.get("selected_basename") == GEN["g1"]["sidecar"]
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "NOOP after gate -> lock -> tx check -> CLEAR gate -> 3 share-0 identity matches; "
                               "unchanged; correspondence verified; selector G1" if v else
                               "unexpected %s" % s[0].get("outcome"), {"selector": sel}))
    for nm, inj, want in (("N3_noop_running", RUNNING, "RUNNING"), ("N4_noop_unknown_exception", "raise", "UNKNOWN")):
        cfg = make_install(nm)
        before = tree(cfg)
        s = [activate(nm, "noop", cfg, "rebuild", SHA["G1"], inject={"process": inj})]
        ev = [e for e in s[0]["trace_summary"]["events"] if e["event"] == "process_gate"]
        v = (s[0]["outcome"] == "REFUSED" and want in json.dumps(s[0]["details"]) and zero_excl(s[0])
             and ev and ev[0]["decision"] == "REFUSE" and noop_unchanged(before, tree(cfg))
             and not s[0]["trace_summary"]["installation_lock_opens"])
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "%s -> REFUSED; no lock; 0 exclusive authority opens; unchanged" % want if v else
                               "unexpected %s %s" % (s[0]["outcome"], s[0].get("details"))))
    nm = "N5_noop_pending_before_protection"
    cfg = make_install(nm)
    s = [activate(nm, "act_killed", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="locked", action="kill")]
    before = tree(cfg)
    txb = tx_files(cfg)
    s.append(activate(nm, "noop1", cfg, "rebuild", SHA["G1"]))
    mid = tree(cfg)
    s.append(recover(nm, "rec", cfg))
    s.append(activate(nm, "noop2", cfg, "rebuild", SHA["G1"]))
    ok, d = final_is(cfg, ("G1", "g1"))
    txa = tx_files(cfg)
    v = (s[0]["killed"] and s[1]["outcome"] == "REFUSED" and "run recovery" in json.dumps(s[1]["details"])
         and s[1]["details"].get("status") == "INTENT" and zero_excl(s[1]) and noop_unchanged(before, mid)
         and s[2]["outcome"] == "OK" and s[2]["transactions"][0]["outcome"] == "ABANDONED"
         and noop_ok(s[3]) and [t["status"] for t in s[3]["transactions_checked"]] == ["ABANDONED"]
         and ok and all(k in txa for k in txb))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "pending INTENT tx -> no-op REFUSED (run recovery), 0 excl opens; recovery ABANDONED; "
                           "then NOOP; exact G1; tx evidence retained" if v else
                           "unexpected %s" % outcomes(s), {"final_check": d}))
    nm = "N6_noop_pending_after_protection"
    cfg = make_install(nm)
    s = [activate(nm, "act_killed", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_begin_forward_0",
                  action="kill")]
    before = tree(cfg)
    s.append(activate(nm, "noop1", cfg, "rebuild", SHA["G1"]))
    s.append(recover(nm, "rec_running", cfg, inject={"process": RUNNING}))
    mid = tree(cfg)
    s.append(recover(nm, "rec_rollback", cfg, policy="rollback"))
    s.append(activate(nm, "noop2", cfg, "rebuild", SHA["G1"]))
    ok, d = final_is(cfg, ("G1", "g1"))
    rr = s[2].get("trace_summary", {})
    v = (s[0]["killed"] and s[1]["outcome"] == "REFUSED" and s[1]["details"].get("status") == "BEGIN"
         and zero_excl(s[1]) and s[2]["outcome"] == "REFUSED" and zero_excl(s[2])
         and not rr.get("installation_lock_opens") and noop_unchanged(before, mid)
         and s[3]["outcome"] == "OK" and s[3]["transactions"][0]["outcome"] == "ROLLED_BACK"
         and noop_ok(s[4]) and ok)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "protected/BEGIN tx -> no-op REFUSED; RUNNING recovery REFUSED with 0 excl opens and no "
                           "lock; rollback recovery ROLLED_BACK; NOOP; exact G1" if v else
                           "unexpected %s" % outcomes(s), {"final_check": d}))
    nm = "N7_noop_unknown_schema"
    cfg = make_install(nm)
    txid = uuid.uuid4().hex
    td = os.path.join(cfg, "sfm_character_tools_updater", "transactions", txid)
    wbytes(os.path.join(td, "intent.json"), json.dumps({"schema": "future-tx-9", "txid": txid}).encode())
    body = json.dumps({"seq": 0, "rec": {"t": "INTENT", "schema": "future-tx-9", "txid": txid}},
                      sort_keys=True, separators=(",", ":"))
    wbytes(os.path.join(td, "journal"), ("%s\t%s\n" % (body, sha(body.encode()))).encode())
    before = tree(cfg)
    s = [activate(nm, "noop", cfg, "rebuild", SHA["G1"])]
    v = (s[0]["outcome"] == "REFUSED" and "compatible updater" in (s[0]["message"] or "") and zero_excl(s[0])
         and noop_unchanged(before, tree(cfg)))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "unknown-schema tx -> REFUSED 'Use a compatible updater'; 0 excl opens; bytes unchanged"
                           if v else "unexpected %s %s" % (s[0]["outcome"], s[0].get("details"))))
    nm = "N8_noop_terminal_records"
    cfg = make_install(nm)
    s = [activate(nm, "to_g3", cfg, "replace", SHA["G1"], source=G3_TXT),
         activate(nm, "back_to_g1", cfg, "replace", SHA["G3"], source=G1_TXT)]
    before = tree(cfg)
    s.append(activate(nm, "noop", cfg, "rebuild", SHA["G1"]))
    st = [t["status"] for t in (s[2].get("transactions_checked") or [])]
    v = (s[0]["outcome"] == "COMPLETE" and s[1]["outcome"] == "COMPLETE" and noop_ok(s[2])
         and st == ["COMPLETE", "COMPLETE"] and noop_unchanged(before, tree(cfg)))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "two COMPLETE records -> NOOP lists both as terminal" if v else
                           "unexpected %s %s" % (outcomes(s), st)))
    nm = "N9_noop_unfamiliar_entry"
    cfg = make_install(nm)
    wmkdirs(os.path.join(cfg, "sfm_character_tools_updater", "transactions", "not-a-transaction"))
    before = tree(cfg)
    s = [activate(nm, "noop", cfg, "rebuild", SHA["G1"])]
    v = (s[0]["outcome"] == "REFUSED" and "unfamiliar transaction entry" in json.dumps(s[0]["details"])
         and zero_excl(s[0]) and noop_unchanged(before, tree(cfg)))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "unfamiliar entry -> REFUSED; 0 excl opens" if v else "unexpected %s" % s[0]["outcome"]))
    nm = "N10_noop_protection_conflict"
    cfg = make_install(nm)
    before = tree(cfg)
    p, first = start_holder("hold.py", os.path.join(cfg, "sfm_shared_authority", GEN["g1"]["sidecar"]), "r", "1")
    s = [activate(nm, "noop_held", cfg, "rebuild", SHA["G1"])]
    rel = release(p)
    mid = tree(cfg)
    s.append(activate(nm, "noop_released", cfg, "rebuild", SHA["G1"]))
    v = ('"held": true' in first and s[0]["outcome"] == "REFUSED"
         and "ERROR_SHARING_VIOLATION" in json.dumps(s[0]["details"]) and noop_unchanged(before, mid)
         and noop_ok(s[1]))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "sidecar held (share READ) -> REFUSED sharing violation, unchanged; released -> NOOP"
                           if v else "unexpected %s %s" % (outcomes(s), s[0].get("details")),
                           {"holder": first, "holder_release": rel}))
    return R


def group_X():
    """L-1 additional cases (card §8)."""
    R = []
    # X1 preparation with SFM RUNNING: staging only; install refuses while RUNNING; installs once CLEAR.
    nm = "X1_prepare_while_running"
    cfg = make_install(nm, master="G3", gens=("g1",))
    before = tree(cfg)
    pr = prepare(nm, "prep", cfg, "rebuild", inject={"process": RUNNING})
    mid = tree(cfg)
    staged = {k: v for k, v in tree(cfg, True).items() if k.startswith(STAGING_PREFIX)}
    s = [pr, install(nm, "install_running", cfg, pr.get("prepid") or "", SHA["G3"], inject={"process": RUNNING})]
    mid2 = tree(cfg)
    s.append(install(nm, "install_clear", cfg, pr.get("prepid") or "", SHA["G3"]))
    ok, d = final_is(cfg, ("G3", "g3"))
    excl_prep = pr.get("trace_summary", {}).get("n_exclusive_authority_opens")
    v = (pr["outcome"] == "PREPARED" and (pr.get("process_status") or [None])[0] == "RUNNING"
         and "Close SFM before installing" in (pr["message"] or "") and before == mid and excl_prep == 0
         and not pr["trace_summary"]["installation_lock_opens"]
         and sorted(os.path.basename(k) for k in staged) == sorted([GEN["g3"]["sidecar"], "manifest.json",
                                                                    "prepared.json"])
         and s[1]["outcome"] == "REFUSED" and before == mid2 and s[2]["outcome"] == "COMPLETE" and ok
         and (s[2].get("correspondence") or {}).get("ok") is True)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "prepare with RUNNING -> PREPARED (warning), only staging written, no lock, 0 exclusive "
                           "authority opens; install RUNNING -> REFUSED unchanged; install CLEAR -> COMPLETE exact G3"
                           if v else "unexpected %s excl=%s" % (outcomes(s), excl_prep), {"staged": staged}))
    # X2 consumer path budget boundary: sidecar consumer path 259 installs, 260 refuses.
    rows = []
    for target in (259, 260):
        fixed = len(os.path.join(WORK, "inst", "")) + len("\\" + SUBDIR + "\\sfm_shared_authority\\") + \
            len(GEN["g3"]["sidecar"])
        nm = "X2_%d_" % target
        nm += "y" * (target - fixed - len(nm))
        cfg = make_install(nm, master="G3", gens=("g1",), base=os.path.join(WORK, "inst", nm))
        sp = os.path.join(cfg, "sfm_shared_authority", GEN["g3"]["sidecar"])
        before = tree(cfg, include_staging=True)
        st = activate(nm, "act", cfg, "rebuild", SHA["G3"])
        rows.append({"sidecar_path_len": len(sp), "outcome": st["outcome"], "details": st.get("details"),
                     "unchanged": tree(cfg, include_staging=True) == before,
                     "exact_g3": final_is(cfg, ("G3", "g3"))[0]})
    v = (rows[0]["sidecar_path_len"] == 259 and rows[0]["outcome"] == "COMPLETE" and rows[0]["exact_g3"]
         and rows[1]["sidecar_path_len"] == 260 and rows[1]["outcome"] == "REFUSED"
         and "budget" in json.dumps(rows[1]["details"]) and rows[1]["unchanged"])
    R.append(finalize_case("X2_path_budget_boundary", None, [], "PASS" if v else "FAIL",
                           "sidecar consumer path 259 -> COMPLETE; 260 -> REFUSED 'path too long', nothing written"
                           if v else "unexpected %s" % rows, {"rows": rows}))
    # X3 post-install process-status recheck (gate CLEAR, gate CLEAR, then RUNNING / UNKNOWN).
    for nm, third, key in (("X3a_post_install_running", RUNNING, "RESTART_RUNNING"),
                           ("X3b_post_install_unknown", "raise", "RESTART_UNKNOWN")):
        cfg = make_install(nm, master="G3", gens=("g1",))
        s = [activate(nm, "act", cfg, "rebuild", SHA["G3"], inject={"process_seq": "clear||clear||" + third})]
        ok, d = final_is(cfg, ("G3", "g3"))
        want = "SFM was started during installation" if key == "RESTART_RUNNING" else "could not be confirmed"
        v = (s[0]["outcome"] == "COMPLETE" and ok and s[0].get("restart_required") is True
             and want in (s[0]["message"] or "") and (s[0].get("correspondence") or {}).get("ok") is True
             and len(s[0].get("process_forms_used") or []) == 3)
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "installation verified and kept; post-install status %s -> restart required, "
                               "message says so" % key if v else "unexpected %s %s" % (outcomes(s), s[0]["message"])))
    cfg = make_install("X3c_real_process_query", master="G3", gens=("g1",))
    real0 = PSTAT()
    before = tree(cfg)
    s = [activate("X3c_real_process_query", "act", cfg, "rebuild", SHA["G3"], inject={"process": "real"})]
    real1 = PSTAT()
    if real0[0] == real1[0] == "CLEAR":
        v = s[0]["outcome"] == "COMPLETE" and not s[0].get("restart_required") and \
            "You can now reopen SFM" in (s[0]["message"] or "") and \
            (s[0].get("post_install_process_status") or [None])[0] == "CLEAR"
        why = "real query CLEAR -> COMPLETE, 'You can now reopen SFM'"
    elif real0[0] == real1[0] == "RUNNING":
        v = s[0]["outcome"] == "REFUSED" and "Close SFM" in (s[0]["message"] or "") and before == tree(cfg) and \
            not txdirs(cfg)
        why = "real query RUNNING (SFM open for other work) -> install REFUSED 'Close SFM', nothing changed"
    else:
        v, why = False, "real process status changed during the case (inconclusive)"
    R.append(finalize_case("X3c_real_process_query", cfg, s, "PASS" if v else "FAIL",
                           why if v else "unexpected %s %s (%s)" % (outcomes(s), s[0]["message"], why),
                           {"real_status_before": real0, "real_status_after": real1}))
    # X4 experimental and future transaction schemas: refused without mutation.
    for nm, schema in (("X4a_schema_p1", "u0b-p1-tx-1"), ("X4b_schema_u0a", "u0a-tx-1")):
        cfg = make_install(nm)
        txid = uuid.uuid4().hex
        td = os.path.join(cfg, "sfm_character_tools_updater", "transactions", txid)
        wmkdirs(os.path.join(td, "candidate"))
        wbytes(os.path.join(td, "intent.json"), json.dumps({"schema": schema, "txid": txid, "kind": "replace"}).encode())
        body = json.dumps({"seq": 0, "rec": {"t": "INTENT", "schema": schema, "txid": txid}},
                          sort_keys=True, separators=(",", ":"))
        wbytes(os.path.join(td, "journal"), ("%s\t%s\n" % (body, sha(body.encode()))).encode())
        before = tree(cfg)
        s = [status(nm, "status", cfg), recover(nm, "rec1", cfg), recover(nm, "rec2", cfg, policy="rollback"),
             activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT)]
        after = tree(cfg)
        txs_untouched = {k: v for k, v in before.items() if txid in k} == {k: v for k, v in after.items() if txid in k}
        v = (s[0].get("recovery_needed") is True
             and all(x["outcome"] == "CONFLICT" and any("compatible updater" in (t.get("message") or "")
                                                        for t in x["transactions"]) for x in s[1:3])
             and s[3]["outcome"] == "ABANDONED" and txs_untouched and active_set(before) == active_set(after))
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "%s transaction: status reports recovery needed; recovery (resume and rollback) "
                               "CONFLICT 'Use a compatible updater' without mutation; install ABANDONED" % schema
                               if v else "unexpected %s" % outcomes(s)))
    # X5 post-lock gate: CLEAR before the lock, then RUNNING / UNKNOWN -> ABANDONED before protection.
    for nm, second in (("X5a_post_lock_gate_running", RUNNING), ("X5b_post_lock_gate_unknown", "rc:1")):
        cfg = make_install(nm)
        s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT, inject={"process_seq": "clear||" + second})]
        s.append(recover(nm, "rec_clear", cfg))
        ok, d = final_is(cfg, ("G1", "g1"))
        lockp = s[0]["trace_summary"]["installation_lock_opens"]
        v = (s[0]["outcome"] == "ABANDONED" and zero_excl(s[0]) and lockp and lockp[0]["ok"]
             and s[0]["details"].get("gate") == "post-lock" and ok and rec_terminal_ok(s[1]))
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "pre-lock CLEAR, post-lock %s -> ABANDONED after the lock and before any exclusive "
                               "authority open; exact G1" % second.split(":")[0] if v else
                               "unexpected %s %s" % (outcomes(s), s[0].get("details"))))
    # X6 prepared data no longer matching: TXT edited after preparation / staged bytes altered.
    nm = "X6a_txt_changed_after_prepare"
    cfg = make_install(nm, master="G3", gens=("g1",))
    pr = prepare(nm, "prep", cfg, "rebuild")
    if pr["outcome"] != "PREPARED":
        return R + [finalize_case(nm, cfg, [pr], "FAIL", "preparation failed: %s" % pr.get("details"))]
    wappend(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), b"\n// edit after preparation\n")
    before = tree(cfg)
    s = [pr, install(nm, "install", cfg, pr["prepid"], SHA["G3"])]
    v = s[1]["outcome"] == "REFUSED" and "Prepare it again" in (s[1]["message"] or "") and before == tree(cfg) \
        and not txdirs(cfg)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "TXT edited after preparation -> REFUSED 'prepare again'; nothing created; edit kept"
                           if v else "unexpected %s" % outcomes(s)))
    nm = "X6b_staged_bytes_altered"
    cfg = make_install(nm, master="G3", gens=("g1",))
    pr = prepare(nm, "prep", cfg, "rebuild")
    if pr["outcome"] != "PREPARED":
        return R + [finalize_case(nm, cfg, [pr], "FAIL", "preparation failed: %s" % pr.get("details"))]
    sp = os.path.join(cfg, "sfm_character_tools_updater", "staging", pr["prepid"], GEN["g3"]["sidecar"])
    wappend(sp, b"X")
    before = tree(cfg)
    s = [pr, install(nm, "install", cfg, pr["prepid"], SHA["G3"]),
         install(nm, "install_unknown_id", cfg, uuid.uuid4().hex, SHA["G3"])]
    v = all(x["outcome"] == "REFUSED" and "Prepare it again" in (x["message"] or "") for x in s[1:]) and \
        before == tree(cfg) and not txdirs(cfg)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "altered staged sidecar / unknown preparation id -> REFUSED 'prepare again'; nothing "
                           "created" if v else "unexpected %s" % outcomes(s)))
    # X7 status is read-only (no lock file, no staging, no journal change) and reports a pending transaction.
    nm = "X7_status_read_only"
    cfg = make_install(nm)
    s = [activate(nm, "act_killed", cfg, "replace", SHA["G1"], source=G3_TXT, stop_at="act_done_forward_2",
                  action="kill")]
    before = tree(cfg, include_staging=True)
    lock_existed = os.path.exists(os.path.join(cfg, LOCK_REL))
    s.append(status(nm, "status", cfg))
    after = tree(cfg, include_staging=True)
    s.append(recover(nm, "rec", cfg))
    s.append(status(nm, "status_after", cfg))
    ok, d = final_is(cfg, ("G3", "g3"))
    ts = s[1].get("trace_summary", {})
    v = (s[1]["outcome"] == "STATUS" and before == after and ts.get("n_exclusive_authority_opens") == 0
         and not ts.get("installation_lock_opens") and lock_existed
         and s[3].get("recovery_needed") is False and (s[3].get("correspondence") or {}).get("ok") is True and ok)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "status changed nothing (no lock/exclusive opens), reported recovery needed; after "
                           "recovery: consistent, exact G3" if v else "unexpected %s" % outcomes(s)))
    # X8 truthful report: authority changed after final verification -> UNVERIFIED (not 'complete').
    nm = "X8_correspondence_failure_unverified"
    cfg = make_install(nm, master="G3", gens=("g1",))

    def add_child(b):
        if b == "complete":
            wbytes(os.path.join(cfg, "sfm_shared_authority", "late_child.tmp"), b"late")
        return b
    s = [activate(nm, "act", cfg, "rebuild", SHA["G3"], stop_at="complete", before_go=add_child)]
    s.append(recover(nm, "rec", cfg))
    v = (s[0]["outcome"] == "UNVERIFIED" and "could not be verified" in (s[0]["message"] or "")
         and not (s[0].get("correspondence") or {}).get("ok")
         and any("unfamiliar" in p for p in (s[0].get("correspondence") or {}).get("problems", []))
         and rec_terminal_ok(s[1]) and s[1].get("installed_state") == "NEEDS_REBUILD")
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "unexpected authority file after final verification -> UNVERIFIED (not success); "
                           "recovery reports the installation needs attention" if v else
                           "unexpected %s %s" % (outcomes(s), s[0].get("correspondence"))))
    # X9 candidate write fault -> ABANDONED, nothing moved; recovery confirms.
    nm = "X9_candidate_write_fault"
    cfg = make_install(nm)
    s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G3_TXT, inject={"candidate_write_error": 112})]
    s.append(recover(nm, "rec", cfg))
    ok, d = final_is(cfg, ("G1", "g1"))
    v = s[0]["outcome"] == "ABANDONED" and "ERROR_DISK_FULL" in json.dumps(s[0]["details"]) and ok and \
        rec_terminal_ok(s[1])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "injected ERROR_DISK_FULL on candidate write -> ABANDONED; exact G1" if v else
                           "unexpected %s" % outcomes(s)))
    return R


def product_worker(args, cwd):
    return subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, "-m",
                           "sfm_character_tools_updater.worker"] + args, capture_output=True, text=True, env=ENV,
                          cwd=cwd, timeout=900)


def group_W():
    """The product worker entry point itself (no test seams, no trace, real process query)."""
    R = []
    nm = "W1_product_surface"
    cfg = make_install(nm)
    out = os.path.join(WORK, "results", "ops", nm + "__replace.json")
    guard(out)
    before = tree(cfg, include_staging=True)
    cps = [product_worker(a + ["--installation", cfg, "--result", out], UPDATER) for a in (
        ["prepare-replace", "--source", G3_TXT], ["prepare-rebuild", "--trust-key", "00" * 32],
        ["prepare-rebuild", "--inject", "process=raise"], ["install", "--stop-at", "locked"],
        ["prepare-rebuild", "--scratch-root", RUN])]
    v = all(cp.returncode == 2 for cp in cps) and not os.path.exists(out) and \
        tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, [{"rc": cp.returncode, "stderr": cp.stderr[-300:]} for cp in cps],
                           "PASS" if v else "FAIL",
                           "product worker rejects 'prepare-replace', '--trust-key', '--inject', '--stop-at' and "
                           "'--scratch-root' (usage error, no result, nothing written)" if v else "unexpected"))
    nm = "W2_product_rebuild_flow"
    cfg = make_install(nm, master="G3", gens=("g1",))
    outs = {k: os.path.join(WORK, "results", "ops", "%s__%s.json" % (nm, k)) for k in
            ("status0", "prep", "install", "status1", "recover")}
    for p in outs.values():
        guard(p)
    steps = []
    real0 = PSTAT()
    for k, a in (("status0", ["status"]), ("prep", ["prepare-rebuild"])):
        cp = product_worker(a + ["--installation", cfg, "--result", outs[k]], UPDATER)
        steps.append({"step": k, "rc": cp.returncode, "stdout": cp.stdout.strip()[-200:], **jload(outs[k])})
    prep = steps[-1]
    cp = product_worker(["install", "--installation", cfg, "--result", outs["install"], "--prepared", prep["prepid"],
                         "--confirm-sha", prep["confirm_sha"]], UPDATER)
    steps.append({"step": "install", "rc": cp.returncode, "stdout": cp.stdout.strip()[-200:], **jload(outs["install"])})
    for k, a in (("status1", ["status"]), ("recover", ["recover"])):
        cp = product_worker(a + ["--installation", cfg, "--result", outs[k]], UPDATER)
        steps.append({"step": k, "rc": cp.returncode, "stdout": cp.stdout.strip()[-200:], **jload(outs[k])})
    real1 = PSTAT()
    if real0[0] == real1[0] == "CLEAR":
        ok, d = final_is(cfg, ("G3", "g1"))
        sel = None
        from sfm_character_tools_updater.messages import MESSAGES as M_
        v = (steps[0]["outcome"] == "STATUS" and steps[0]["correspondence"]["ok"] is False
             and steps[1]["outcome"] == "PREPARED" and steps[2]["outcome"] == "REFUSED"
             and steps[2].get("message") == M_["SOFTWARE_UNVERIFIED"] and "trace" not in steps[2]
             and steps[2]["stdout"] == "RESULT REFUSED" and steps[3]["recovery_needed"] is False
             and steps[4]["outcome"] in ("OK", "NOTHING_TO_RECOVER") and ok and not txdirs(cfg))
        why = ("product worker, real query CLEAR: status (needs rebuild) -> prepare-rebuild PREPARED -> install REFUSED "
               "'couldn't verify the installed Character Tools' (the shipping worker trusts no test key, so the test-signed "
               "inventory cannot verify; L-5 correction) -> nothing changed -> recover nothing to do")
    elif real0[0] == real1[0] == "RUNNING":
        ok, d = final_is(cfg, ("G3", "g1"))
        sel = None
        v = (steps[0]["outcome"] == "STATUS" and steps[1]["outcome"] == "PREPARED"
             and "Close SFM before installing" in (steps[1]["message"] or "")
             and steps[2]["outcome"] == "REFUSED" and "Close SFM" in (steps[2]["message"] or "")
             and steps[2]["stdout"] == "RESULT REFUSED" and "trace" not in steps[2]
             and steps[3]["recovery_needed"] is False and steps[4]["outcome"] == "REFUSED" and ok
             and not txdirs(cfg))
        why = ("product worker, real query RUNNING (SFM open for other work): prepare-rebuild PREPARED with the "
               "'close SFM' note; install and recover REFUSED 'Close SFM'; installation unchanged")
    else:
        v, why, sel = False, "real process status changed during the case (inconclusive)", None
    for x in steps:
        x.pop("trace", None)
    R.append(finalize_case(nm, cfg, steps, "PASS" if v else "FAIL",
                           why if v else "unexpected %s (%s)" % ([x.get("outcome") for x in steps], why),
                           {"selector": sel, "real_status_before": real0, "real_status_after": real1}))
    return R


# ------------------------------------------------------------------ L-2: packages and keys (test-only)
PRODUCER = os.path.join(UPDATER, "release_tools", "make_official_package.py")


def producer(*args):
    cp = subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, PRODUCER] + list(args),
                        capture_output=True, text=True, env=ENV, cwd=os.path.join(RUN, "tmp"), timeout=900)
    if cp.returncode != 0:
        raise RuntimeError("producer failed: %s %s" % (args[:1], cp.stderr[-800:]))
    return cp.stdout


def keyfile(name, ext):
    return os.path.join(RUN, "keys", "%s.%s" % (name, ext))


def ensure_keys():
    """Per-run TEST keys in the scratch run (never in the repository, never shipping trust)."""
    for k in ("test_a", "test_b"):
        if not os.path.exists(keyfile(k, "pem")):
            guard(keyfile(k, "pem"))
            os.makedirs(os.path.dirname(keyfile(k, "pem")), exist_ok=True)
            producer("keygen", "--private", keyfile(k, "pem"), "--public", keyfile(k, "pub"))


def pkgdir(n):
    return os.path.join(RUN, "pkgs", n)


def build_pkg(n, master, seq, ver, key="test_a", **extra):
    d = pkgdir(n)
    if os.path.exists(d):
        return d
    guard(d)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    args = ["build", "--master", master, "--private", keyfile(key, "pem"), "--out", d, "--sequence", str(seq),
            "--data-version", ver, "--release-tag", extra.get("tag", "data-" + ver), "--source-commit", "a1" * 20,
            "--published-at", "2026-10-17T00:00:00Z"]
    for p in extra.get("profiles", []):
        args += ["--profile", p]
    if "muc" in extra:
        args += ["--minimum-updater-contract", str(extra["muc"])]
    producer(*args)
    return d


def desc_bytes(d):
    return (json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def craft(n, base, mutate=None, raw=None, files=None, sign_key="test_a", sig=None, drop=(), add=()):
    """Copy package `base` to `n` with a modified descriptor (re-signed with `sign_key` unless
    `sig` is given) and/or replaced, dropped or added files."""
    d = pkgdir(n)
    if os.path.exists(d):
        return d
    src = pkgdir(base)
    desc = json.load(open(os.path.join(src, "release.json"), encoding="utf-8"))
    for nm in os.listdir(src):
        if nm in ("release.json", "release.sig") or nm in drop or (files and nm == desc["files"]["sidecar"]["name"]
                                                                  and "sidecar" in files):
            continue
        if files and nm == "manifest.json" and "manifest" in files:
            continue
        wcopy(os.path.join(src, nm), os.path.join(d, nm))
    for role, path in (files or {}).items():
        data = open(path, "rb").read()
        nm = os.path.basename(path) if role == "sidecar" else ("manifest.json" if role == "manifest" else nm)
        wbytes(os.path.join(d, nm), data)
        desc["files"][role] = {"name": nm, "byte_length": len(data), "sha256": sha(data)}
    if mutate:
        mutate(desc)
    db = raw(desc) if raw else desc_bytes(desc)
    wbytes(os.path.join(d, "release.json"), db)
    if sig is not None:
        wbytes(os.path.join(d, "release.sig"), sig)
    else:
        producer("sign", "--descriptor", os.path.join(d, "release.json"), "--private", keyfile(sign_key, "pem"),
                 "--out", os.path.join(d, "release.sig"))
    for nm, data in add:
        wbytes(os.path.join(d, nm), data)
    return d


def tampered(n, base, filename, fn):
    """Copy package `base` with one file's bytes transformed by fn (no re-signing)."""
    d = pkgdir(n)
    if os.path.exists(d):
        return d
    for nm in os.listdir(pkgdir(base)):
        data = open(os.path.join(pkgdir(base), nm), "rb").read()
        wbytes(os.path.join(d, nm), fn(data) if nm == filename else data)
    return d


def pkg_tree(d):
    return {n: sha_file(os.path.join(d, n)) for n in sorted(os.listdir(d))}


def ensure_packages():
    ensure_keys()
    build_pkg("G3_s5", G3_TXT, 5, "2026.10.5")
    build_pkg("G1_s6", G1_TXT, 6, "2026.10.6")
    build_pkg("G3_s3", G3_TXT, 3, "2026.10.3")
    build_pkg("G3_s5_alt", G3_TXT, 5, "2026.10.5-alt")
    build_pkg("G1_s7_keyB", G1_TXT, 7, "2026.10.7", key="test_b")
    build_pkg("G3_s8_muc2", G3_TXT, 8, "2026.10.8", muc=2)
    build_pkg("G3_s9_profile", G3_TXT, 9, "2026.10.9", profiles=["other-profile-9"])


def official_prep(case, step, cfg, pkg, allow_older=False, trust=True):
    a = ["prepare-official", "--package", pkg] + (["--allow-older"] if allow_older else [])
    return run_op(case, step + "__prep", a, cfg, trust=trust)


def release_log(cfg):
    p = os.path.join(cfg, "sfm_character_tools_updater", "official_releases.log")
    if not os.path.exists(p):
        return None
    return [json.loads(l.split(b"\t")[0]) for l in open(p, "rb").read().split(b"\n") if l]


def retired_masters(cfg):
    out = []
    for td in txdirs(cfg):
        p = os.path.join(td, "retired", "master.txt")
        if os.path.exists(p):
            out.append(p)
    return out


def group_M():
    """L-2 Use Another TXT (headless import through prepare-import + install)."""
    R = []
    nm = "M1_import_consent_and_backup"
    cfg = make_install(nm)
    src = os.path.join(WORK, "inputs", "m1_custom.txt")
    wcopy(G3_TXT, src)
    pr = prepare(nm, "prep", cfg, "replace", src)
    before = tree(cfg)
    s = [pr, install(nm, "install_no_consent", cfg, pr.get("prepid", ""), SHA["G1"], accept=False)]
    mid = tree(cfg)
    s.append(install(nm, "install_consent", cfg, pr.get("prepid", ""), SHA["G1"], accept=True))
    ok3, d3 = final_is(cfg, ("G3", "g3"))
    ret = retired_masters(cfg)
    ret_ok = len(ret) == 1 and sha_file(ret[0]) == SHA["G1"]
    s.append(activate(nm, "restore_previous", cfg, "replace", SHA["G3"], source=ret[0] if ret else src))
    ok1, d1 = final_is(cfg, ("G1", "g1"))
    v = (pr["outcome"] == "PREPARED" and pr.get("consent_required") is True and "replaces" in (pr["message"] or "")
         and s[1]["outcome"] == "REFUSED" and "Confirm the replacement" in (s[1]["message"] or "")
         and before == mid
         and s[2]["outcome"] == "COMPLETE" and ok3 and "previous TXT was kept as a backup" in (s[2]["message"] or "")
         and (s[2].get("correspondence") or {}).get("ok") is True and ret_ok
         and s[3]["outcome"] == "COMPLETE" and ok1 and sha_file(src) == SHA["G3"]
         and ret and sha_file(ret[0]) == SHA["G1"])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "preview says it replaces (consent required); install without consent REFUSED, nothing "
                           "changed; with consent COMPLETE exact G3; previous G1 TXT kept byte-exact in the backup "
                           "and restored from it to exact G1; chosen file unchanged" if v else
                           "unexpected %s" % outcomes(s)))
    nm = "M2_import_identical_no_consent"
    cfg = make_install(nm)
    before = tree(cfg)
    s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=G1_TXT, accept=False)]
    v = noop_ok(s[0]) and s[0]["prepare"]["consent_required"] is False and noop_unchanged(before, tree(cfg))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "importing the identical TXT needs no consent and is a verified NOOP" if v else
                           "unexpected %s" % outcomes(s)))
    # M3 unusable sources: too large, missing, locked, a directory, malformed
    big = os.path.join(WORK, "inputs", "too_large.txt")
    guard(big)
    with open(big, "xb") as f:
        f.seek(64 * 1024 * 1024)
        f.write(b"\n")
    held = os.path.join(WORK, "inputs", "held.txt")
    wcopy(G3_TXT, held)
    bad = os.path.join(WORK, "inputs", "malformed_m3.txt")
    wbytes(bad, open(G3_TXT, "rb").read()[:150000])
    for nm, path, key, word in (("M3a_too_large", big, "SOURCE_TOO_LARGE", "too large"),
                                ("M3b_missing", os.path.join(WORK, "inputs", "does_not_exist.txt"),
                                 "SOURCE_UNREADABLE", "couldn't be read"),
                                ("M3c_locked", held, "SOURCE_UNREADABLE", "couldn't be read"),
                                ("M3d_directory", os.path.join(WORK, "inputs"), "SOURCE_UNREADABLE", "couldn't be read"),
                                ("M3e_malformed", bad, "SOURCE_INVALID", "isn't a valid animation-group TXT")):
        cfg = make_install(nm)
        before = tree(cfg, include_staging=True)
        hp = None
        src_before = sha_file(path) if os.path.isfile(path) else None
        if nm == "M3c_locked":
            hp, first = start_holder("hold.py", held, "rd", "0")
        s = [prepare(nm, "prep", cfg, "replace", path)]
        if hp:
            release(hp)
        v = (s[0]["outcome"] == "REFUSED" and word in (s[0]["message"] or "") and "Nothing was changed" in s[0]["message"]
             and tree(cfg, include_staging=True) == before
             and (src_before is None or sha_file(path) == src_before))
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "%s -> REFUSED '%s'; nothing written; source unchanged" % (nm[4:], word) if v else
                               "unexpected %s %s" % (s[0]["outcome"], s[0]["message"])))
    # M4 selection changed before confirmation -> fresh preview required
    for nm, change in (("M4a_source_edited_before_install", "edit"), ("M4b_source_removed_before_install", "remove")):
        cfg = make_install(nm)
        src = os.path.join(WORK, "inputs", nm + ".txt")
        wcopy(G3_TXT, src)
        pr = prepare(nm, "prep", cfg, "replace", src)
        if change == "edit":
            wappend(src, b"\n// edited after preview\n")
        else:
            wremove(src)
        before = tree(cfg)
        s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), SHA["G1"], accept=True)]
        v = (pr["outcome"] == "PREPARED" and s[1]["outcome"] == "REFUSED" and "changed after it was checked"
             in (s[1]["message"] or "") and before == tree(cfg) and not txdirs(cfg))
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "chosen file %s after the preview -> REFUSED 'choose the file again'; nothing changed"
                               % ("edited" if change == "edit" else "removed") if v else "unexpected %s" % outcomes(s)))
    nm = "M5_destination_changed_before_install"
    cfg = make_install(nm)
    pr = prepare(nm, "prep", cfg, "replace", G3_TXT)
    wappend(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), b"\n// user edit after preview\n")
    before = tree(cfg)
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), accept=True)]
    v = (s[1]["outcome"] == "REFUSED" and "changed after it was checked" in (s[1]["message"] or "")
         and before == tree(cfg) and not txdirs(cfg))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "installed TXT edited after the preview -> REFUSED 'check again'; edit kept; nothing changed"
                           if v else "unexpected %s %s" % (outcomes(s), s[1].get("message"))))
    nm = "M6_import_interrupted_then_recovered"
    cfg = make_install(nm)
    src = os.path.join(WORK, "inputs", "m6.txt")
    wcopy(G3_TXT, src)
    s = [activate(nm, "act", cfg, "replace", SHA["G1"], source=src, stop_at="act_moved_forward_3", action="kill")]
    s.append(recover(nm, "rec1", cfg))
    s.append(recover(nm, "rec2", cfg))
    ok, d = final_is(cfg, ("G3", "g3"))
    v = s[0]["killed"] and ok and rec_terminal_ok(s[2]) and sha_file(src) == SHA["G3"] and \
        len(retired_masters(cfg)) == 1 and sha_file(retired_masters(cfg)[0]) == SHA["G1"]
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "killed after the new TXT moved in -> recovery completes exact G3; previous TXT in the "
                           "backup; chosen file unchanged" if v else "unexpected %s" % outcomes(s)))
    return R


def group_O():
    """L-2 Get Official Data from a local signed package."""
    R = []
    ensure_packages()
    P = {n: pkgdir(n) for n in os.listdir(os.path.join(RUN, "pkgs"))}
    pk0 = {n: pkg_tree(d) for n, d in P.items()}
    # O1-O5: one installation through a sequence of official packages
    cfg = make_install("O_sequence")
    nm = "O1_valid_package_customized_needs_consent"
    pr = official_prep(nm, "prep", cfg, P["G3_s5"])
    before = tree(cfg)
    s = [pr, install(nm, "install_no_consent", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True)]
    mid = tree(cfg)
    s.append(install(nm, "install_consent", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), accept=True,
                     trust=True))
    ok, d = final_is(cfg, ("G3", "g3"))
    log = release_log(cfg) or []
    v = (pr["outcome"] == "PREPARED" and pr.get("consent_required") is True and "2026.10.5" in pr["message"]
         and "doesn't match official data" in pr["message"]
         and s[1]["outcome"] == "REFUSED" and before == mid
         and s[2]["outcome"] == "COMPLETE" and ok and "Official data 2026.10.5 is installed" in (s[2]["message"] or "")
         and "kept as a backup" in s[2]["message"] and (s[2].get("correspondence") or {}).get("ok") is True
         and [r["sequence"] for r in log] == [5] and len(retired_masters(cfg)) == 1
         and sha_file(retired_masters(cfg)[0]) == SHA["G1"])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "signed package authenticated; current TXT not official -> consent required; without "
                           "consent nothing changed; with consent official G3 installed exactly, verified; previous "
                           "TXT backed up; sequence 5 remembered" if v else "unexpected %s %s" % (outcomes(s), log)))
    nm = "O2_recognized_official_no_consent"
    pr = official_prep(nm, "prep", cfg, P["G1_s6"])
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True)]
    ok, d = final_is(cfg, ("G1", "g1"))
    log = release_log(cfg) or []
    v = (pr.get("consent_required") is False and (pr.get("destination") or {}).get("recognized_official") is True
         and s[1]["outcome"] == "COMPLETE" and ok and [r["sequence"] for r in log] == [5, 6])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "current TXT is recognized official data -> no replacement consent needed; official G1 "
                           "(sequence 6) installed exactly; high-water 6" if v else "unexpected %s" % outcomes(s)))
    nm = "O3_older_release_explicit_only"
    s = [official_prep(nm, "prep_older", cfg, P["G3_s3"])]
    s.append(official_prep(nm, "prep_older_allowed", cfg, P["G3_s3"], allow_older=True))
    pr = s[1]
    s.append(install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True))
    ok, d = final_is(cfg, ("G3", "g3"))
    log = release_log(cfg) or []
    v = (s[0]["outcome"] == "REFUSED" and "older than official data already seen" in (s[0]["message"] or "")
         and pr["outcome"] == "PREPARED" and (pr.get("official") or {}).get("older_than_seen") is True
         and "older" in pr["message"] and s[2]["outcome"] == "COMPLETE" and ok
         and max(r["sequence"] for r in log) == 6 and [r["sequence"] for r in log] == [5, 6, 3])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "older release (3 < 6) refused unless explicitly allowed; allowed -> installed exactly; "
                           "remembered high-water stays 6" if v else "unexpected %s %s" % (outcomes(s), log)))
    nm = "O4_replay_same_release"
    s = [official_prep(nm, "prep_newest_again", cfg, P["G1_s6"]), official_prep(nm, "prep_older_again", cfg, P["G3_s5"])]
    log = release_log(cfg) or []
    v = (s[0]["outcome"] == "PREPARED" and s[1]["outcome"] == "REFUSED"
         and "older than official data already seen" in (s[1]["message"] or "")
         and [r["sequence"] for r in log] == [5, 6, 3])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "newest release offered again -> accepted as already seen, nothing new remembered; an "
                           "already-seen older release offered again -> still refused as older without explicit "
                           "choice" if v else "unexpected %s %s" % (outcomes(s), log)))
    nm = "O5_same_sequence_different_bytes"
    before = tree(cfg, include_staging=True)
    s = [official_prep(nm, "prep", cfg, P["G3_s5_alt"])]
    v = (s[0]["outcome"] == "REFUSED" and "can't be trusted" in (s[0]["message"] or "")
         and tree(cfg, include_staging=True) == before)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "sequence 5 with different descriptor bytes -> REFUSED (conflict); nothing changed"
                           if v else "unexpected %s %s" % (outcomes(s), s[0]["message"])))
    # O6 same official TXT already installed, stale sidecar -> data-only install, TXT not moved
    nm = "O6_official_same_txt_data_only"
    cfg = make_install(nm, master="G3", gens=("g1",))
    pr = official_prep(nm, "prep", cfg, P["G3_s5"])
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True)]
    ok, d = final_is(cfg, ("G3", "g3"))
    v = (pr.get("kind") == "rebuild" and pr.get("consent_required") is False and s[1]["outcome"] == "COMPLETE" and ok
         and not retired_masters(cfg) and "Official data 2026.10.5 is installed" in (s[1]["message"] or ""))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "official TXT already active -> only the official data files installed; TXT not moved; "
                           "exact G3" if v else "unexpected %s" % outcomes(s)))
    nm = "O7_official_already_installed_noop"
    cfg = make_install(nm, master="G3", gens=("g3",), manifest="g3")
    before = tree(cfg)
    pr = official_prep(nm, "prep", cfg, P["G3_s5"])
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True)]
    v = noop_ok(s[1]) and active_set(before) == active_set(tree(cfg))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "official data already installed -> verified NOOP" if v else "unexpected %s" % outcomes(s)))
    # O8 tampering with each package file
    g3sc = GEN["g3"]["sidecar"]
    flips = (("O8a_tamper_descriptor", "release.json", lambda b: b.replace(b"2026.10.5", b"2026.10.4"), "isn't signed"),
             ("O8b_tamper_signature", "release.sig", lambda b: bytes([b[0] ^ 1]) + b[1:], "isn't signed"),
             ("O8c_tamper_txt", "sfm_defaultanimationgroups.txt", lambda b: b + b"\n", "damaged or was altered"),
             ("O8d_tamper_manifest", "manifest.json", lambda b: b.replace(b'"', b"'", 1), "damaged or was altered"),
             ("O8e_tamper_sidecar", g3sc, lambda b: b[:-1] + bytes([b[-1] ^ 1]), "damaged or was altered"))
    cases = [(n, tampered(n, "G3_s5", f, fn), w) for n, f, fn, w in flips]
    cases += [("O9a_extra_file", craft("O9a_extra_file", "G3_s5", add=[("readme.txt", b"extra")]),
               "isn't a complete official data package"),
              ("O9b_missing_file", craft("O9b_missing_file", "G3_s5", drop=("manifest.json",)),
               "isn't a complete official data package"),
              ("O10_signed_by_other_key_claiming_trusted", craft("O10_signed_by_other_key", "G3_s5", sign_key="test_b"),
               "isn't signed"),
              ("O11_unknown_signing_key", P["G1_s7_keyB"], "isn't signed"),
              ("O13a_wrong_association", craft("O13a_wrong_association", "G1_s6",
                                               files={"sidecar": GEN["g3"]["sidecar_path"],
                                                      "manifest": GEN["g3"]["manifest_path"]}),
               "damaged or was altered"),
              ("O14a_duplicate_key", craft("O14a_duplicate_key", "G3_s5",
                                           raw=lambda d: desc_bytes(d).replace(b'"channel":"stable"',
                                                                               b'"channel":"stable","channel":"stable"')),
               "isn't a complete official data package"),
              ("O14b_unknown_field", craft("O14b_unknown_field", "G3_s5", mutate=lambda d: d.update(extra=1)),
               "isn't a complete official data package"),
              ("O14c_wrong_type", craft("O14c_wrong_type", "G3_s5", mutate=lambda d: d.update(sequence="5")),
               "isn't a complete official data package"),
              ("O14d_unsafe_name", craft("O14d_unsafe_name", "G3_s5",
                                         mutate=lambda d: d["files"]["sidecar"].update(name="..\\" + g3sc)),
               "isn't a complete official data package"),
              ("O14e_byte_order_mark", craft("O14e_byte_order_mark", "G3_s5", raw=lambda d: b"\xef\xbb\xbf" + desc_bytes(d)),
               "isn't a complete official data package"),
              ("O14f_oversized_descriptor", craft("O14f_oversized_descriptor", "G3_s5",
                                                  raw=lambda d: desc_bytes(d)[:-1] + b" " * 17000 + b"\n"),
               "isn't a complete official data package"),
              ("O15a_needs_newer_updater", P["G3_s8_muc2"], "needs a newer version"),
              ("O15b_unsupported_profile", P["G3_s9_profile"], "isn't compatible"),
              ("O15c_unsupported_sidecar_contract", craft("O15c_unsupported_sidecar_contract", "G3_s5",
                                                          mutate=lambda d: d["sidecar_contract"].update(format=1)),
               "isn't compatible")]
    for nm, pkg, word in cases:
        cfg = make_install(nm)
        before = tree(cfg, include_staging=True)
        pk_before = pkg_tree(pkg)
        s = [official_prep(nm, "prep", cfg, pkg)]
        v = (s[0]["outcome"] == "REFUSED" and word in (s[0]["message"] or "") and "Nothing was changed" in s[0]["message"]
             and tree(cfg, include_staging=True) == before and pkg_tree(pkg) == pk_before)
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "REFUSED '%s'; installation and package unchanged; nothing staged or remembered" % word
                               if v else "unexpected %s %s %s" % (s[0]["outcome"], s[0]["message"], s[0].get("details")),
                               {"package": os.path.basename(pkg)}))
    nm = "O12_shipping_trust_refuses_test_key"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    s = [official_prep(nm, "prep", cfg, P["G3_s5"], trust=False)]
    v = s[0]["outcome"] == "REFUSED" and "isn't signed" in (s[0]["message"] or "") and tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "without the test-only trust seam the product trusts no test key: a test-signed package is "
                           "REFUSED as unsigned" if v else "unexpected %s" % outcomes(s)))
    nm = "O13b_official_txt_edited_before_install"
    cfg = make_install(nm, master="G3", gens=("g1",))
    pr = official_prep(nm, "prep", cfg, P["G3_s5"])
    wappend(os.path.join(cfg, "sfm_defaultanimationgroups.txt"), b"\n// local edit after preview\n")
    before = tree(cfg)
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), trust=True)]
    v = pr.get("kind") == "rebuild" and s[1]["outcome"] == "REFUSED" and before == tree(cfg) and not txdirs(cfg)
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "official data never combined with a different local TXT: TXT edited after the preview -> "
                           "REFUSED, nothing changed" if v else "unexpected %s" % outcomes(s)))
    # O16 interrupted official installation
    for nm, at, exp in (("O16a_official_killed_after_cutover", "act_done_forward_3", ("G3", "g3")),
                        ("O16b_official_killed_before_moves", "protected", ("G1", "g1"))):
        cfg = make_install(nm)
        pr = official_prep(nm, "prep", cfg, P["G3_s5"])
        s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), accept=True, trust=True,
                         stop_at=at, action="kill")]
        s.append(recover(nm, "rec1", cfg))
        s.append(recover(nm, "rec2", cfg))
        ok, d = final_is(cfg, exp)
        v = s[1]["killed"] and ok and rec_terminal_ok(s[3]) and s[2].get("installed_state") == "WORKING"
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "official install killed at %s -> recovery to exact %s; second recovery no-op"
                               % (at, exp[0]) if v else "unexpected %s" % outcomes(s)))
    nm = "O17_official_write_fault"
    cfg = make_install(nm)
    pr = official_prep(nm, "prep", cfg, P["G3_s5"])
    s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), accept=True, trust=True,
                     inject={"candidate_write_error": 112})]
    ok, d = final_is(cfg, ("G1", "g1"))
    v = s[1]["outcome"] == "ABANDONED" and ok
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "write fault during official install -> ABANDONED; exact G1" if v else
                           "unexpected %s" % outcomes(s)))
    # O18 the remembered-release record: damaged, busy
    nm = "O18a_release_record_damaged"
    cfg = make_install(nm)
    wbytes(os.path.join(cfg, "sfm_character_tools_updater", "official_releases.log"), b"not a record\n")
    before = tree(cfg, include_staging=True)
    s = [official_prep(nm, "prep", cfg, P["G3_s5"])]
    v = s[0]["outcome"] == "REFUSED" and "record of official releases is damaged" in (s[0]["message"] or "") and \
        tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "damaged release record -> REFUSED; record and installation unchanged" if v else
                           "unexpected %s" % outcomes(s)))
    nm = "O18b_release_record_busy"
    cfg = make_install(nm)
    logp = os.path.join(cfg, "sfm_character_tools_updater", "official_releases.log")
    wbytes(logp, b"")
    before = tree(cfg, include_staging=True)
    hp, first = start_holder("hold.py", logp, "r", "0")
    s = [official_prep(nm, "prep", cfg, P["G3_s5"])]
    release(hp)
    v = s[0]["outcome"] == "REFUSED" and "Another updater window" in (s[0]["message"] or "") and \
        tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "release record held by another process -> REFUSED 'another updater window'; unchanged"
                           if v else "unexpected %s %s" % (outcomes(s), s[0]["message"])))
    # O19 staged official files altered after preparation
    for nm, mut in (("O19a_staged_signature_altered", "sig"), ("O19b_staged_descriptor_swapped", "swap")):
        cfg = make_install(nm)
        pr = official_prep(nm, "prep", cfg, P["G3_s5"])
        sd = os.path.join(cfg, "sfm_character_tools_updater", "staging", pr.get("prepid", "x"))
        if mut == "sig":
            data = open(os.path.join(sd, "release.sig"), "rb").read()
            wremove(os.path.join(sd, "release.sig"))
            wbytes(os.path.join(sd, "release.sig"), bytes([data[0] ^ 1]) + data[1:])
        else:
            for f in ("release.json", "release.sig"):
                wremove(os.path.join(sd, f))
                wcopy(os.path.join(P["G3_s5_alt"], f), os.path.join(sd, f))
        before = tree(cfg)
        s = [pr, install(nm, "install", cfg, pr.get("prepid", ""), pr.get("confirm_sha", ""), accept=True, trust=True)]
        v = s[1]["outcome"] == "REFUSED" and before == tree(cfg) and not txdirs(cfg)
        R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                               "staged official %s altered after preparation -> install REFUSED (%s); nothing changed"
                               % ("signature" if mut == "sig" else "descriptor", s[1]["message"]) if v else
                               "unexpected %s %s" % (outcomes(s), s[1].get("details"))))
    unchanged = all(pkg_tree(d) == pk0[n] for n, d in P.items())
    R.append(finalize_case("O20_packages_never_modified", None, [], "PASS" if unchanged else "FAIL",
                           "every source package byte-identical after all official cases" if unchanged else
                           "a package changed"))
    return R


def group_W3():
    """The shipping worker (no test seams) refuses a test-signed official package."""
    ensure_packages()
    nm = "W3_shipping_worker_official_untrusted"
    cfg = make_install(nm)
    out = os.path.join(WORK, "results", "ops", nm + "__prep.json")
    guard(out)
    before = tree(cfg, include_staging=True)
    cp = product_worker(["prepare-official", "--installation", cfg, "--result", out, "--package", pkgdir("G3_s5")],
                        UPDATER)
    r = jload(out) if os.path.exists(out) else {}
    v = (cp.returncode == 0 and r.get("outcome") == "REFUSED" and "isn't signed" in (r.get("message") or "")
         and tree(cfg, include_staging=True) == before and "trace" not in r)
    return [finalize_case(nm, cfg, [r], "PASS" if v else "FAIL",
                          "shipping worker: test-signed package REFUSED as unsigned (no trusted key in the product); "
                          "nothing written" if v else "unexpected %s" % r.get("outcome"))]


# ------------------------------------------------------------------ L-3: online Get Official Data (test-only)
CONFIRMED_REPOSITORY = "chadchan3d/sfm-character-tools"   # owner-confirmed permanent identity (2026-10-17)
FAKE = None


def start_fake():
    global FAKE
    if FAKE is None:
        sys.path.insert(0, SUPPORT)
        import fake_github
        FAKE = fake_github.Fake().start()
    return FAKE


def ensure_l3_packages():
    ensure_packages()
    build_pkg("L3_s1", G3_TXT, 1, "1.0.0", tag="data-v1.0.0")
    build_pkg("L3_s2", G1_TXT, 2, "1.0.1", tag="data-v1.0.1")
    build_pkg("L3_s3_muc2", G3_TXT, 3, "1.0.2", tag="data-v1.0.2", muc=2)
    build_pkg("L3_s4_profile", G3_TXT, 4, "1.0.3", tag="data-v1.0.3", profiles=["other-profile-4"])
    build_pkg("L3_s1_alt", G1_TXT, 1, "1.0.9", tag="data-v1.0.9")
    build_pkg("L3_s1_keyB", G3_TXT, 1, "1.0.0", tag="data-v1.0.0", key="test_b")
    build_pkg("L3_s5_conflict", G1_TXT, 5, "5.0.0", tag="data-v5.0.0")
    craft("L3_s1_oldrepo", "L3_s1", mutate=lambda d: d.update(repository="chadchan3d/sfm-animation-groups-master"))
    craft("L3_s1_republished", "L3_s1", mutate=lambda d: d.update(published_at="2026-10-18T00:00:00Z"))


def pkg_files(n):
    d = pkgdir(n)
    return {x: open(os.path.join(d, x), "rb").read() for x in sorted(os.listdir(d))}


def serve(rels, pages=None):
    """rels: [(rid, tag, files, kwargs)] on page 1, or explicit pages {n: spec}. Returns {rid: {name: aid}}."""
    import fake_github
    FAKE.reset()
    assets, ids, objs = {}, {}, []
    for rid, tag, files, kw in rels:
        obj, data = fake_github.release_json(rid, tag, files, **kw)
        objs.append(obj)
        ids[rid] = {a["name"]: a["id"] for a in obj["assets"]}
        assets.update({aid: {"data": b} for aid, b in data.items()})
    FAKE.assets = assets
    FAKE.pages = pages if pages is not None else {1: {"json": objs}}
    return ids


def asset_mode(ids, rid, name, **mode):
    FAKE.assets[ids[rid][name]].update(mode)


def fake_requests(kind=None):
    """Logged request paths; kind 'assets' = asset API requests, 'cdn' = asset-host requests."""
    paths = [r["path"] for r in FAKE.log]
    if kind == "assets":
        return [p for p in paths if p.startswith("/api/") and "/assets/" in p]
    if kind == "cdn":
        return [p for p in paths if p.startswith("/cdn/")]
    return paths


def asset_paths(ids, rid, names):
    return {"/api/repos/%s/releases/assets/%d" % (CONFIRMED_REPOSITORY, ids[rid][n]) for n in names}


def PRODUCT_VERSION():
    from sfm_character_tools_updater import VERSION
    return VERSION


def headers_ok():
    return all("authorization" not in r["headers"]
               and r["headers"].get("user-agent", "") == "SFM-Character-Tools-Updater/%s" % PRODUCT_VERSION()
               for r in FAKE.log)


def local_only(step, expect_any=True):
    ev = step.get("network") or []
    ok = all(e[1].startswith("127.0.0.1:") if e[0] == "socket.getaddrinfo" else e[1].startswith("('127.0.0.1',")
             for e in ev)
    return ok and (bool(ev) if expect_any else True)


def no_latest(step):
    return "latest" not in (step.get("message") or "").lower() and "newest" not in (step.get("message") or "").lower()


def check_op(nm, step, cfg, trust=True, **kw):
    return run_op(nm, step, ["check-official"], cfg, trust=trust, net=True, **kw)


def download_op(nm, step, cfg, tag, dsha, allow_older=False, trust=True, **kw):
    a = ["download-official", "--release-tag", tag, "--descriptor-sha", dsha] + (["--allow-older"] if allow_older else [])
    return run_op(nm, step, a, cfg, trust=trust, net=True, **kw)


def closed_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d" % port


def group_Q():
    """L-3 Get Official Data online (headless): explicit check-official and download-official
    against a loopback GitHub stand-in serving test-signed packages, then the L-2 path."""
    R = []
    start_fake()
    ensure_l3_packages()
    from sfm_character_tools_updater import discovery, official as off
    S1, S2 = pkg_files("L3_s1"), pkg_files("L3_s2")
    S1_SHA = sha(S1["release.json"])
    S1_SC = [n for n in S1 if n.endswith(".sfmsidecar")][0]
    PAYLOAD = [S1_SC, "manifest.json", "sfm_defaultanimationgroups.txt"]

    def single(nm, rels, want, phrase, trust=True, check=None, pages=None, why="", cfg=None, **kw):
        cfg = cfg or make_install(nm)
        ids = serve(rels, pages)
        before = tree(cfg, include_staging=True)
        st = check_op(nm, "check", cfg, trust=trust, **kw)
        v = (st["outcome"] == want and phrase in (st["message"] or "") and tree(cfg, include_staging=True) == before
             and local_only(st) and headers_ok() and no_latest(st) and (check(st, ids) if check else True))
        R.append(finalize_case(nm, cfg, [st], "PASS" if v else "FAIL",
                               why if v else "unexpected %s: %s / %s" % (st["outcome"], st["message"], st.get("details")),
                               {"server_log": fake_requests()}))
        return st

    # ---- identity
    nm = "Q0_repository_identity"
    v = (off.REPOSITORY == CONFIRMED_REPOSITORY
         and discovery.RELEASES_URL == "https://api.github.com/repos/%s/releases" % CONFIRMED_REPOSITORY
         and json.loads(S1["release.json"])["repository"] == CONFIRMED_REPOSITORY)
    R.append(finalize_case(nm, None, [], "PASS" if v else "FAIL",
                           "product identity is the confirmed repository for descriptor validation and discovery; "
                           "the producer signs it" if v else "identity mismatch %s" % off.REPOSITORY))
    nm = "Q0b_old_repository_descriptor_refused_locally"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    st = official_prep(nm, "prep", cfg, pkgdir("L3_s1_oldrepo"))
    v = (st["outcome"] == "REFUSED" and "isn't a complete official data package" in (st["message"] or "")
         and (st.get("details") or {}).get("fields") == ["repository"] and tree(cfg, include_staging=True) == before
         and st.get("network") == [])
    R.append(finalize_case(nm, cfg, [st], "PASS" if v else "FAIL",
                           "validly signed (trusted test key) descriptor naming the previous repository name: refused "
                           "(field 'repository'); nothing written; no network" if v else "unexpected %s %s" % (
                               st["outcome"], st.get("details"))))

    # ---- discovery outcomes (check writes nothing)
    single("Q1_empty_release_list", [], "NONE_PUBLISHED", "No official data has been published yet",
           check=lambda st, ids: "offer" not in st and st.get("releases_listed") == 0,
           why="empty list -> NONE_PUBLISHED, not an error and no offer; nothing written")
    single("Q2_only_non_data_releases",
           [(1, "v0.3.0", {"updater.zip": b"zip"}, {}), (2, "data-v1.0.0", S1, {"prerelease": True}),
            (3, "data-v1.0.1", S2, {"draft": True}), (4, "data-v1.0", S1, {})],
           "NONE_PUBLISHED", "No official data has been published yet",
           check=lambda st, ids: st.get("releases_listed") == 4 and st.get("data_releases") == 0
           and not fake_requests("assets"),
           why="software release, prerelease, draft and malformed data tag ignored -> NONE_PUBLISHED; no asset fetched")
    single("Q3_one_valid_release_available", [(10, "data-v1.0.0", S1, {})], "AVAILABLE", "Official data 1.0.0 is available.",
           check=lambda st, ids: st.get("offer") == {"release_tag": "data-v1.0.0", "sequence": 1, "data_version": "1.0.0",
                                                     "descriptor_sha256": S1_SHA}
           and set(fake_requests("assets")) == asset_paths(ids, 10, ["release.json", "release.sig"]),
           why="one authenticated compatible release -> AVAILABLE 1.0.0 (offer bound to the descriptor digest); only "
               "release.json/release.sig fetched by the check; nothing written")
    single("Q4_untrusted_release_not_offered", [(10, "data-v1.0.0", S1, {})], "OFFICIAL_UNVERIFIED",
           "couldn't be verified", trust=False,
           check=lambda st, ids: "offer" not in st and st["releases"][0]["message_key"] == "PACKAGE_UNTRUSTED",
           why="test-signed release without a trusted key -> not offered (OFFICIAL_UNVERIFIED)")
    single("Q5_highest_compatible_selected", [(10, "data-v1.0.0", S1, {}), (11, "data-v1.0.1", S2, {})], "AVAILABLE",
           "Official data 1.0.1 is available.", check=lambda st, ids: st["offer"]["sequence"] == 2,
           cfg=make_install("Q5_highest_compatible_selected", master="G2"),
           why="two compatible releases -> the highest sequence found (1.0.1) is offered, without a 'latest' claim")
    single("Q6_newer_incompatible_noted", [(10, "data-v1.0.0", S1, {}),
                                           (12, "data-v1.0.2", pkg_files("L3_s3_muc2"), {})], "AVAILABLE",
           "Official data 1.0.0 is available. A newer release needs newer SFM Character Tools.",
           check=lambda st, ids: st["offer"]["sequence"] == 1 and st.get("newer_needs_newer_updater") is True,
           why="compatible 1.0.0 offered and the newer release needing a newer updater is reported")
    single("Q7_only_newer_needs_updater", [(12, "data-v1.0.2", pkg_files("L3_s3_muc2"), {})], "NEEDS_NEWER_UPDATER",
           "A newer release needs newer SFM Character Tools.", check=lambda st, ids: "offer" not in st,
           why="only a release needing a newer updater -> NEEDS_NEWER_UPDATER, not 'up to date'")
    single("Q8_only_incompatible_profile", [(13, "data-v1.0.3", pkg_files("L3_s4_profile"), {})],
           "OFFICIAL_INCOMPATIBLE", "isn't compatible", check=lambda st, ids: "offer" not in st,
           why="only an unsupported-profile release -> OFFICIAL_INCOMPATIBLE")
    single("Q9_installed_release_current", [(10, "data-v1.0.0", S1, {})], "INSTALLED_CURRENT",
           "Official data 1.0.0 is already installed.", cfg=make_install("Q9_installed_release_current", master="G3",
                                                                         gens=("g3",), manifest="g3"),
           check=lambda st, ids: "offer" not in st and st["installed_release"]["sequence"] == 1,
           why="installed TXT equals the best release -> INSTALLED_CURRENT; no offer")
    single("Q10_same_sequence_conflict", [(10, "data-v1.0.0", S1, {}),
                                          (14, "data-v1.0.9", pkg_files("L3_s1_alt"), {})], "RELEASE_CONFLICT",
           "can't be trusted", check=lambda st, ids: st.get("conflicting_sequences") == [1] and "offer" not in st,
           why="two releases with sequence 1 and different descriptors -> RELEASE_CONFLICT, nothing offered")
    # remembered releases: older-only and conflict with the release record
    nm = "Q11_older_and_record_conflict"
    cfg = make_install(nm)
    s = [official_prep(nm, "seed_s5", cfg, pkgdir("G3_s5"))]
    before = tree(cfg, include_staging=True)
    serve([(10, "data-v1.0.0", S1, {})])
    s.append(check_op(nm, "check_older", cfg))
    log1 = list(FAKE.log)
    serve([(15, "data-v5.0.0", pkg_files("L3_s5_conflict"), {})])
    s.append(check_op(nm, "check_conflict", cfg))
    v = (s[0]["outcome"] == "PREPARED" and s[1]["outcome"] == "OLDER_ONLY"
         and "(1.0.0) is older than official data already seen" in (s[1]["message"] or "")
         and s[1]["older_release"]["sequence"] == 1 and s[1].get("high_water") == 5 and "offer" not in s[1]
         and s[2]["outcome"] == "RELEASE_CONFLICT" and s[2].get("conflicting_sequences") == [5]
         and tree(cfg, include_staging=True) == before and local_only(s[1]) and local_only(s[2]) and no_latest(s[1]))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "record high-water 5: release 1 -> OLDER_ONLY (not offered); a different sequence-5 "
                           "descriptor -> RELEASE_CONFLICT; checks wrote nothing" if v else "unexpected %s" % outcomes(s),
                           {"server_log": [r["path"] for r in log1] + fake_requests()}))

    # ---- per-release refusals: authenticated metadata only, never offered
    nm = "Q12_release_not_offered_variants"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    no_sc = {k: b for k, b in S1.items() if k != S1_SC}
    variants = [("tag_mismatch", [(20, "data-v1.0.5", S1, {})], "PACKAGE_INVALID", "signed release tag differs"),
                ("missing_asset", [(21, "data-v1.0.0", no_sc, {})], "PACKAGE_INVALID", "differ from the signed file list"),
                ("extra_asset", [(22, "data-v1.0.0", dict(S1, **{"notes.txt": b"x"}), {})], "PACKAGE_INVALID",
                 "differ from the signed file list"),
                ("size_mismatch", [(23, "data-v1.0.0", S1, {"sizes": {S1_SC: len(S1[S1_SC]) + 1}})], "PACKAGE_DAMAGED",
                 "asset size differs"),
                ("old_repository", [(24, "data-v1.0.0", pkg_files("L3_s1_oldrepo"), {})], "PACKAGE_INVALID",
                 "descriptor fields invalid"),
                ("not_uploaded", [(25, "data-v1.0.0", S1, {"state": "starter"})], "PACKAGE_INVALID", "not fully uploaded"),
                ("descriptor_too_large", [(26, "data-v1.0.0", S1, {"sizes": {"release.json": 16 * 1024 + 1}})],
                 "PACKAGE_INVALID", "size invalid"),
                ("untrusted_key", [(27, "data-v1.0.0", pkg_files("L3_s1_keyB"), {})], "PACKAGE_UNTRUSTED",
                 "not trusted")]
    s, ok = [], True
    for tag, rels, key, reason in variants:
        serve(rels)
        st = check_op(nm, tag, cfg)
        r0 = (st.get("releases") or [{}])[0]
        good = (st["outcome"] == "OFFICIAL_UNVERIFIED" and r0.get("message_key") == key and reason in r0.get("reason", "")
                and "offer" not in st and local_only(st) and headers_ok())
        if tag == "old_repository":
            good = good and r0.get("fields") == ["repository"]
        st["variant_ok"] = good
        ok = ok and good
        s.append(st)
    v = ok and tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "tag mismatch, missing/extra asset, size mismatch, previous repository name, incomplete "
                           "upload, oversized descriptor, untrusted key: each not offered with its reason; nothing "
                           "written" if v else "unexpected %s" % [(x["step"], x["outcome"], x.get("variant_ok"))
                                                                  for x in s]))

    # ---- incomplete queries: "Couldn't check for updates", never a partial answer
    nm = "Q13_incomplete_query_variants"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    rel_ok = [(10, "data-v1.0.0", S1, {})]
    filler = [{"url": "https://api.github.com/repos/%s/releases/%d" % (CONFIRMED_REPOSITORY, 1000 + i), "id": 1000 + i,
               "tag_name": "v0.%d" % i, "draft": False, "prerelease": False, "assets": []} for i in range(100)]
    old_rel = {"url": "https://api.github.com/repos/chadchan3d/sfm-animation-groups-master/releases/9", "id": 9,
               "tag_name": "data-v1.0.0", "draft": False, "prerelease": False, "assets": []}
    import fake_github
    other_asset = fake_github.release_json(31, "data-v1.0.0", S1, repo="someone-else/sfm-character-tools")[0]
    other_asset["url"] = "https://api.github.com/repos/%s/releases/31" % CONFIRMED_REPOSITORY

    def pages_with(spec1, extra=None):
        return dict({1: spec1}, **(extra or {}))
    variants = [
        ("http_500", None, pages_with({"status": 500, "json": {"message": "err"}})),
        ("rate_limited_403", None, pages_with({"status": 403, "json": {"message": "API rate limit exceeded"},
                                               "headers": {"X-RateLimit-Remaining": "0"}})),
        ("redirect_301_not_followed", None, pages_with({"status": 301, "raw": b"", "headers": {
            "Location": "https://api.github.com/repositories/1/releases?per_page=100&page=1"}})),
        ("invalid_json", None, pages_with({"raw": b"[{"})),
        ("duplicate_keys", None, pages_with({"raw": b'[{"id":1,"id":2}]'})),
        ("truncated_body", None, pages_with({"json": [], "raw": json.dumps(filler[:3]).encode(), "mode": "truncate"})),
        ("oversized_page", None, pages_with({"raw": b" " * (8 * 1024 * 1024 + 1)})),
        ("not_a_list", None, pages_with({"json": {"message": "Not Found"}})),
        ("partial_listing_page2_fails", rel_ok, None),
        ("too_many_pages", None, {i: {"json": filler} for i in range(1, 11)}),
        ("release_from_old_identity", None, pages_with({"json": [old_rel]})),
        ("asset_from_other_repository", None, pages_with({"json": [other_asset]})),
        ("malformed_release_fields", None, pages_with({"json": [dict(filler[0], tag_name=5)]})),
        ("descriptor_fetch_500", rel_ok, None),
        ("descriptor_redirect_offsite", rel_ok, None),
        ("timeout", None, pages_with({"json": [], "mode": "sleep", "seconds": 3})),
        ("server_unreachable", None, pages_with({"json": []})),
        ("too_many_data_releases", None, pages_with({"json": [dict(filler[i], tag_name="data-v9.0.%d" % i)
                                                               for i in range(51)]})),
    ]
    s, ok = [], True
    for tag, rels, pages in variants:
        ids = serve(rels or [], pages)
        kw = {}
        if tag == "partial_listing_page2_fails":
            objs = FAKE.pages[1]["json"]
            FAKE.pages = {1: {"json": objs + filler[:99]}, 2: {"status": 502, "json": {"message": "bad gateway"}}}
        if tag == "descriptor_fetch_500":
            asset_mode(ids, 10, "release.json", api="status:500")
        if tag == "descriptor_redirect_offsite":
            asset_mode(ids, 10, "release.sig", api="offsite")
        if tag == "timeout":
            kw["net_timeout"] = 1
        if tag == "server_unreachable":
            kw["net_base"] = closed_port()
        st = check_op(nm, tag, cfg, **kw)
        good = (st["outcome"] == "CHECK_FAILED" and (st["message"] or "").startswith("Couldn't check for updates.")
                and "offer" not in st and local_only(st) and headers_ok())
        if tag == "redirect_301_not_followed":
            good = good and fake_requests() == ["/api/repos/%s/releases?per_page=100&page=1" % CONFIRMED_REPOSITORY]
        if tag == "descriptor_redirect_offsite":
            good = good and "/cdn/objects.githubusercontent.com/assets/%d" % ids[10]["release.sig"] not in fake_requests()
        st["variant_ok"] = good
        st["server_log"] = fake_requests()
        ok = ok and good
        s.append(st)
    v = ok and tree(cfg, include_staging=True) == before
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "%d incomplete or untrustworthy queries (HTTP errors, rate limit, unfollowed 301, bad/"
                           "duplicate/truncated/oversized JSON, partial pagination, page bound, foreign identity, "
                           "metadata fetch failure, off-site redirect, timeout, unreachable, release bound) -> "
                           "'Couldn't check for updates'; nothing written" % len(variants) if v else
                           "unexpected %s" % [(x["step"], x["outcome"], x.get("variant_ok")) for x in s]))
    nm = "Q14_pagination_complete"
    cfg = make_install(nm)
    ids = serve([(10, "data-v1.0.0", S1, {})])
    FAKE.pages = {1: {"json": filler}, 2: FAKE.pages[1]}
    st = check_op(nm, "check", cfg)
    v = (st["outcome"] == "AVAILABLE" and st.get("releases_listed") == 101 and st["offer"]["sequence"] == 1
         and [p for p in fake_requests() if "/releases?" in p] == [
             "/api/repos/%s/releases?per_page=100&page=%d" % (CONFIRMED_REPOSITORY, i) for i in (1, 2)])
    R.append(finalize_case(nm, cfg, [st], "PASS" if v else "FAIL",
                           "full first page (100) then a second page: both read; release on page 2 offered"
                           if v else "unexpected %s %s" % (st["outcome"], st.get("details"))))

    # ---- download-official: bounded, verified, then the L-2 path
    nm = "Q20_download_prepare_install"
    cfg = make_install(nm)
    ids = serve([(10, "data-v1.0.0", S1, {})])
    s = [check_op(nm, "check", cfg)]
    log_check = fake_requests()
    t0 = tree(cfg)
    FAKE.log.clear()
    s.append(download_op(nm, "download", cfg, "data-v1.0.0", s[0].get("offer", {}).get("descriptor_sha256", "")))
    log_dl = fake_requests()
    t1 = tree(cfg)
    dl = s[1]
    s.append(install(nm, "install", cfg, dl.get("prepid", ""), dl.get("confirm_sha", ""), accept=True, trust=True))
    ok, d = final_is(cfg, ("G3", "g3"))
    log = release_log(cfg) or []
    s.append(check_op(nm, "check_after", cfg))
    staged = sorted(k for k in tree(cfg, True) if k.startswith(STAGING_PREFIX + discovery.DOWNLOAD_PREFIX))
    conds = {"check_available": s[0]["outcome"] == "AVAILABLE",
             "prepared_official": dl["outcome"] == "PREPARED" and dl.get("workflow") == "official",
             "message": "Official data 1.0.0 is checked and ready" in (dl["message"] or ""),
             "consent_required": dl.get("consent_required") is True,
             "bound_descriptor": (dl.get("download") or {}).get("descriptor_sha256") == S1_SHA,
             "active_unchanged": active_set(t0) == active_set(t1),
             "only_record_added": sorted(set(t1) - set(t0)) == [os.path.join("sfm_character_tools_updater",
                                                                             "official_releases.log")],
             "all_assets_requested": set(log_dl) >= asset_paths(ids, 10, list(S1)),
             "one_redirect_each": len([p for p in log_dl if p.startswith("/cdn/")]) == 5,
             "download_folder_removed": staged == [] and (dl.get("download") or {}).get("folder_removed") is True,
             "install_complete": s[2]["outcome"] == "COMPLETE" and ok,
             "install_message": "Official data 1.0.0 is installed" in (s[2]["message"] or ""),
             "correspondence": (s[2].get("correspondence") or {}).get("ok") is True,
             "record": [r["sequence"] for r in log] == [1],
             "check_after_current": s[3]["outcome"] == "INSTALLED_CURRENT",
             "loopback_only": all(local_only(x) for x in (s[0], s[1], s[3])),
             "install_no_network": s[2].get("network") == [],
             "headers": headers_ok()}
    v = all(conds.values())
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "check AVAILABLE -> download (5 assets via one redirect each, verified, written only to "
                           "staging and removed once prepared (L-4); active files unchanged; release record appended) -> PREPARED through the L-2 path (consent required) -> "
                           "install COMPLETE exact G3, verified; record [1]; next check INSTALLED_CURRENT; install "
                           "used no network" if v else "unexpected %s %s" % (
                               outcomes(s), sorted(k for k, c in conds.items() if not c)),
                           {"server_log_check": log_check, "server_log_download": log_dl, "conditions": conds}))

    def dl_refused(nm, rels, key, phrase, prepare=None, dsha=S1_SHA, trust=True, payload_requests=None, why="", **kw):
        cfg = make_install(nm)
        ids = serve(rels)
        if prepare:
            prepare(ids)
        before = tree(cfg, include_staging=True)
        st = download_op(nm, "download", cfg, "data-v1.0.0", dsha, trust=trust, **kw)
        v = (st["outcome"] == "REFUSED" and phrase in (st["message"] or "") and tree(cfg, include_staging=True) == before
             and local_only(st) and headers_ok())
        if payload_requests is not None and rels:
            got = set(fake_requests("assets")) & asset_paths(ids, rels[0][0], PAYLOAD)
            v = v and len(got) == payload_requests
        R.append(finalize_case(nm, cfg, [st], "PASS" if v else "FAIL",
                               why if v else "unexpected %s: %s / %s" % (st["outcome"], st["message"], st.get("details")),
                               {"server_log": fake_requests(), "expected_key": key}))

    dl_refused("Q21_descriptor_changed_since_check", [(10, "data-v1.0.0", pkg_files("L3_s1_republished"), {})],
               "RELEASE_CHANGED", "changed or was removed since it was checked", payload_requests=0,
               why="same tag now carries a different signed descriptor -> RELEASE_CHANGED before any payload request; "
                   "nothing written")
    dl_refused("Q22_release_removed", [], "RELEASE_CHANGED", "changed or was removed since it was checked",
               why="release no longer listed -> RELEASE_CHANGED; nothing written")
    flip = bytearray(S1[S1_SC])
    flip[len(flip) // 2] ^= 1
    dl_refused("Q23_payload_altered_on_asset_host", [(10, "data-v1.0.0", S1, {})], "PACKAGE_DAMAGED",
               "damaged or was altered", prepare=lambda ids: asset_mode(ids, 10, S1_SC, cdn="replace",
                                                                        cdn_data=bytes(flip)),
               why="sidecar bytes altered (same length) -> PACKAGE_DAMAGED before anything is written")
    dl_refused("Q24_payload_truncated", [(10, "data-v1.0.0", S1, {})], "DOWNLOAD_FAILED", "Couldn't download",
               prepare=lambda ids: asset_mode(ids, 10, S1_SC, cdn="truncate"),
               why="connection closed early -> DOWNLOAD_FAILED; nothing written")
    dl_refused("Q25_payload_longer_than_signed", [(10, "data-v1.0.0", S1, {})], "PACKAGE_DAMAGED",
               "damaged or was altered", prepare=lambda ids: asset_mode(ids, 10, "manifest.json", cdn="extra"),
               why="more bytes than the signed length -> bounded read stops, PACKAGE_DAMAGED; nothing written")
    dl_refused("Q26_offsite_redirect_refused", [(10, "data-v1.0.0", S1, {})], "DOWNLOAD_FAILED", "Couldn't download",
               prepare=lambda ids: asset_mode(ids, 10, S1_SC, api="offsite"),
               why="asset redirect to a non-GitHub host refused without connecting (loopback only); nothing written")
    dl_refused("Q27_plain_http_redirect_refused", [(10, "data-v1.0.0", S1, {})], "DOWNLOAD_FAILED", "Couldn't download",
               prepare=lambda ids: asset_mode(ids, 10, S1_SC, api="http_redirect"),
               why="asset redirect to plain http refused; nothing written")
    dl_refused("Q28_second_redirect_refused", [(10, "data-v1.0.0", S1, {})], "DOWNLOAD_FAILED", "Couldn't download",
               prepare=lambda ids: asset_mode(ids, 10, S1_SC, cdn="redirect_again"),
               why="a second redirect from the asset host is not followed; nothing written")
    dl_refused("Q29_asset_redirect_to_old_identity_refused", [(10, "data-v1.0.0", S1, {})], "DOWNLOAD_FAILED",
               "Couldn't download", prepare=lambda ids: asset_mode(ids, 10, S1_SC, api="api_redirect"),
               why="asset redirect to the previous repository name on api.github.com is not followed; nothing written")
    dl_refused("Q30_untrusted_download_refused", [(10, "data-v1.0.0", S1, {})], "PACKAGE_UNTRUSTED",
               "isn't signed as official", trust=False, payload_requests=0,
               why="untrusted signature -> PACKAGE_UNTRUSTED before any payload request; nothing written")
    dl_refused("Q31a_signed_tag_binding_at_download", [(12, "data-v1.0.0", dict(pkg_files("L3_s3_muc2")), {})],
               "PACKAGE_INVALID", "isn't a complete official data package",
               why="signed tag data-v1.0.2 served as data-v1.0.0 -> refused (tag binding); nothing written")
    nm = "Q31b_needs_newer_updater_download"
    cfg = make_install(nm)
    M2 = pkg_files("L3_s3_muc2")
    ids = serve([(12, "data-v1.0.2", M2, {})])
    before = tree(cfg, include_staging=True)
    st = download_op(nm, "download", cfg, "data-v1.0.2", sha(M2["release.json"]))
    payload_req = set(fake_requests("assets")) - asset_paths(ids, 12, ["release.json", "release.sig"])
    v = (st["outcome"] == "REFUSED" and "needs a newer version of SFM Character Tools" in (st["message"] or "")
         and not payload_req and tree(cfg, include_staging=True) == before)
    R.append(finalize_case(nm, cfg, [st], "PASS" if v else "FAIL",
                           "release needing a newer updater -> PACKAGE_NEEDS_NEWER before payload; nothing written"
                           if v else "unexpected %s" % st["outcome"]))
    dl_refused("Q34_listing_fails_at_download", [], "DOWNLOAD_FAILED", "Couldn't download",
               prepare=lambda ids: FAKE.pages.update({1: {"status": 500, "json": {}}}),
               why="listing failure during download -> DOWNLOAD_FAILED; nothing written")

    nm = "Q32_download_while_sfm_running"
    cfg = make_install(nm)
    serve([(10, "data-v1.0.0", S1, {})])
    act0 = active_set(tree(cfg))
    s = [download_op(nm, "download", cfg, "data-v1.0.0", S1_SHA, inject={"process": RUNNING})]
    s.append(install(nm, "install", cfg, s[0].get("prepid", ""), s[0].get("confirm_sha", ""), accept=True, trust=True,
                     inject={"process": RUNNING}))
    v = (s[0]["outcome"] == "PREPARED" and "Close SFM before installing" in (s[0]["message"] or "")
         and s[1]["outcome"] == "REFUSED" and "Close SFM" in (s[1]["message"] or "")
         and active_set(tree(cfg)) == act0 and not txdirs(cfg))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "SFM running (injected): download prepares into staging with the 'close SFM' note; install "
                           "REFUSED; active files unchanged" if v else "unexpected %s" % outcomes(s)))

    nm = "Q33_older_download_explicit_only"
    cfg = make_install(nm)
    s = [official_prep(nm, "seed_s5", cfg, pkgdir("G3_s5"))]
    ids = serve([(10, "data-v1.0.0", S1, {})])
    before = tree(cfg, include_staging=True)
    s.append(download_op(nm, "download", cfg, "data-v1.0.0", S1_SHA))
    pay0 = set(fake_requests("assets")) & asset_paths(ids, 10, PAYLOAD)
    mid = tree(cfg, include_staging=True)
    s.append(download_op(nm, "download_allowed", cfg, "data-v1.0.0", S1_SHA, allow_older=True))
    s.append(install(nm, "install", cfg, s[2].get("prepid", ""), s[2].get("confirm_sha", ""), accept=True, trust=True))
    ok, d = final_is(cfg, ("G3", "g3"))
    log = release_log(cfg) or []
    v = (s[1]["outcome"] == "REFUSED" and "older than official data already seen" in (s[1]["message"] or "")
         and not pay0 and before == mid and s[2]["outcome"] == "PREPARED"
         and (s[2].get("official") or {}).get("older_than_seen") is True and s[3]["outcome"] == "COMPLETE" and ok
         and [r["sequence"] for r in log] == [5, 1])
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "older release refused before any payload request unless explicitly allowed; allowed -> "
                           "prepared and installed; high-water stays 5" if v else "unexpected %s" % outcomes(s)))

    nm = "Q40_no_network_outside_check_and_download"
    cfg = make_install(nm)
    s = [run_op(nm, "status", ["status"], cfg, net=True),
         run_op(nm, "rebuild__prep", ["prepare-rebuild"], cfg, net=True),
         run_op(nm, "import__prep", ["prepare-import", "--source", G3_TXT], cfg, net=True),
         run_op(nm, "official__prep", ["prepare-official", "--package", pkgdir("L3_s1")], cfg, trust=True, net=True)]
    s.append(install(nm, "install", cfg, s[2].get("prepid", ""), s[2].get("confirm_sha", ""), accept=True, net=True))
    s.append(recover(nm, "recover", cfg, net=True))
    v = (all(x.get("network") == [] for x in s) and outcomes(s)[:4] == ["STATUS", "PREPARED", "PREPARED", "PREPARED"]
         and s[4]["outcome"] == "COMPLETE" and s[5]["outcome"] in ("OK", "NOTHING_TO_RECOVER"))
    R.append(finalize_case(nm, cfg, s, "PASS" if v else "FAIL",
                           "status, prepare-rebuild, prepare-import, prepare-official, install and recover (with the "
                           "test network endpoint configured) made no name lookup or connection" if v else
                           "unexpected %s %s" % (outcomes(s), [x.get("network") for x in s])))
    return R


def audited_worker(nm, step, args):
    netlog = os.path.join(WORK, "results", "ops", "%s__%s.net.json" % (nm, step))
    guard(netlog)
    cp = subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, os.path.join(SUPPORT, "net_audit.py"),
                         netlog] + args, capture_output=True, text=True, env=ENV, cwd=os.path.join(RUN, "tmp"), timeout=900)
    return cp, (jload(netlog) if os.path.exists(netlog) else None)


def group_W4():
    """The SHIPPING worker's network boundary (no seams): only check-official/download-official use
    the network, only to api.github.com; one explicit query of the real official release list."""
    R = []
    ensure_l3_packages()
    from sfm_character_tools_updater import discovery
    nm = "W4a_shipping_no_network_other_commands"
    cfg = make_install(nm, master="G3")
    outs = {}
    steps = []

    def call(step, args):
        out = os.path.join(WORK, "results", "ops", "%s__%s.json" % (nm, step))
        guard(out)
        cp, net = audited_worker(nm, step, args + ["--installation", cfg, "--result", out])
        r = jload(out) if os.path.exists(out) else {}
        r.pop("trace", None)
        steps.append({"step": step, "rc": cp.returncode, "net": net, "outcome": r.get("outcome"),
                      "message": r.get("message")})
        outs[step] = r
        return r
    real0 = PSTAT()
    call("status", ["status"])
    pr = call("prepare_rebuild", ["prepare-rebuild"])
    call("prepare_import", ["prepare-import", "--source", G1_TXT])
    call("prepare_official", ["prepare-official", "--package", pkgdir("L3_s1")])
    call("install", ["install", "--prepared", pr.get("prepid", ""), "--confirm-sha", pr.get("confirm_sha", "")])
    call("recover", ["recover"])
    real1 = PSTAT()
    v = (all(x["net"] == [] for x in steps) and steps[3]["outcome"] == "REFUSED"
         and "isn't signed" in (steps[3]["message"] or "")
         and steps[4]["outcome"] == "REFUSED"
         and real0[0] == real1[0] and real0[0] in ("CLEAR", "RUNNING"))
    R.append(finalize_case(nm, cfg, steps, "PASS" if v else "FAIL",
                           "shipping worker: status, prepare-rebuild, prepare-import, prepare-official (test-signed -> "
                           "refused as unsigned), install (real process query %s) and recover made no name lookup or "
                           "connection" % real0[0] if v else "unexpected %s" % [(x["outcome"], x["net"]) for x in steps],
                           {"real_status_before": real0, "real_status_after": real1}))

    nm = "W4b_shipping_real_check_empty"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    out = os.path.join(WORK, "results", "ops", nm + "__check.json")
    guard(out)
    cp, net = audited_worker(nm, "check", ["check-official", "--installation", cfg, "--result", out])
    r = jload(out) if os.path.exists(out) else {}
    hosts = {e[1] for e in (net or []) if e[0] == "socket.getaddrinfo"}
    if r.get("outcome") == "NONE_PUBLISHED":
        v = (r.get("releases_listed") == 0 and r.get("repository") == CONFIRMED_REPOSITORY and "offer" not in r
             and "No official data has been published yet" in (r.get("message") or "")
             and hosts == {"api.github.com:443"} and tree(cfg, include_staging=True) == before and "trace" not in r)
        why = ("explicit real query of %s: empty release list -> NONE_PUBLISHED (not an update, not an error); "
               "lookups only api.github.com:443; nothing written" % discovery.RELEASES_URL)
    else:
        v, why = False, "real query did not return the empty list (%s): inconclusive" % r.get("outcome")
    R.append(finalize_case(nm, cfg, [{"rc": cp.returncode, "net": net, **r}], "PASS" if v else "FAIL",
                           why if v else "%s / %s" % (why, r.get("details"))))

    nm = "W4c_shipping_real_download_absent_release"
    cfg = make_install(nm)
    before = tree(cfg, include_staging=True)
    out = os.path.join(WORK, "results", "ops", nm + "__download.json")
    guard(out)
    cp, net = audited_worker(nm, "download", ["download-official", "--installation", cfg, "--result", out,
                                              "--release-tag", "data-v1.0.0", "--descriptor-sha", "0" * 64])
    r = jload(out) if os.path.exists(out) else {}
    hosts = {e[1] for e in (net or []) if e[0] == "socket.getaddrinfo"}
    v = (r.get("outcome") == "REFUSED" and "changed or was removed" in (r.get("message") or "")
         and hosts == {"api.github.com:443"} and tree(cfg, include_staging=True) == before)
    R.append(finalize_case(nm, cfg, [{"rc": cp.returncode, "net": net, **r}], "PASS" if v else "FAIL",
                           "real download of data-v1.0.0 before any release exists -> RELEASE_CHANGED (not found); "
                           "nothing written" if v else "unexpected %s / %s" % (r.get("outcome"), r.get("details"))))

    nm = "W4d_shipping_rejects_network_test_options"
    cfg = make_install(nm)
    out = os.path.join(WORK, "results", "ops", nm + "__x.json")
    guard(out)
    cps = [product_worker(["check-official", "--installation", cfg, "--result", out] + a, UPDATER)
           for a in (["--net-base", "http://127.0.0.1:1"], ["--net-timeout", "1"])]
    v = all(cp.returncode == 2 for cp in cps) and not os.path.exists(out)
    R.append(finalize_case(nm, cfg, [{"rc": cp.returncode, "stderr": cp.stderr[-200:]} for cp in cps],
                           "PASS" if v else "FAIL",
                           "shipping worker rejects --net-base and --net-timeout (usage error, no result)" if v else
                           "unexpected"))

    nm = "W4e_previous_name_redirect_not_followed"
    old = "https://api.github.com/repos/chadchan3d/sfm-animation-groups-master/releases?per_page=100&page=1"
    try:
        st, h, body = discovery._request(old, "application/vnd.github+json", discovery.MAX_PAGE_BYTES,
                                         time.monotonic() + 60)
        got = {"status": st, "location": h.get("location"), "body_bytes": len(body)}
    except discovery.NetFail as e:
        got = {"error": e.details}
    v = got.get("status") in (301, 302, 307, 308) and got.get("body_bytes") == 0
    R.append(finalize_case(nm, None, [got], "PASS" if v else "FAIL",
                           "real GitHub answers the previous repository name with a redirect (%s); the product "
                           "transport returns it unfollowed, and the listing treats any non-200 as \"Couldn't check\""
                           % got.get("status") if v else "inconclusive/unexpected %s" % got))

    nm = "W4f_network_code_confined"
    import ast
    pkg = os.path.join(UPDATER, "sfm_character_tools_updater")
    netmods = {"socket", "ssl", "http", "urllib", "requests", "urllib3", "asyncio"}
    users = {}
    for n in sorted(os.listdir(pkg)):
        if n.endswith(".py"):
            tree_ = ast.parse(open(os.path.join(pkg, n), encoding="utf-8").read())
            mods = set()
            for node in ast.walk(tree_):
                if isinstance(node, ast.Import):
                    mods |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods.add(node.module.split(".")[0])
            if mods & netmods:
                users[n] = sorted(mods & netmods)
    cp = subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, "-c",
                         "import sys; import sfm_character_tools_updater.worker as w; "
                         "print(sorted(m for m in sys.modules if m.split('.')[0] in %r))" % sorted(netmods)],
                        capture_output=True, text=True, env=ENV, cwd=UPDATER, timeout=120)
    wsrc = open(os.path.join(pkg, "worker.py"), encoding="utf-8").read()
    v = (users == {"discovery.py": ["http", "ssl", "urllib"], "runtime_check.py": ["ssl"]} and cp.stdout.strip() == "[]"
         and "from . import discovery" in wsrc and "\nfrom . import discovery" not in wsrc)
    R.append(finalize_case(nm, None, [{"importers": users, "worker_import_net_modules": cp.stdout.strip()}],
                           "PASS" if v else "FAIL",
                           "only discovery.py imports network modules (runtime_check uses ssl only to read the trust store); importing the worker loads none; discovery is "
                           "imported only inside the check/download dispatch" if v else "unexpected %s %s" % (
                               users, cp.stdout)))
    return R


# ------------------------------------------------------------------ L-4: GUI and bounded worker (test-only)
def alive(pid):
    cp = subprocess.run(["tasklist", "/FO", "CSV", "/NH", "/FI", "PID eq %d" % pid], capture_output=True, text=True)
    return ('"%d"' % pid) in cp.stdout


def test_worker_argv(inject=None, trust=True, net=False, hold=None, marker=None):
    argv = [PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, TEST_WORKER, "--token", TOKEN,
            "--scratch-root", RUN, "--forbid", A.game]
    inject = dict(inject or {})
    if A.process_default and not any(k.startswith("process") for k in inject):
        inject["process"] = A.process_default
    for k, v in inject.items():
        argv += ["--inject", "%s=%s" % (k, v)]
    if trust:
        argv += ["--trust-key", open(os.path.join(RUN, "keys", "test_a.pub"), encoding="ascii").read().strip()]
    if net:
        argv += ["--net-base", FAKE.base]
    if hold:
        argv += ["--hold-at", hold, "--hold-marker", marker]
    return argv


class Gui(object):
    """The real App (withdrawn window) driven in this process: buttons are invoked exactly as a
    click would; the file picker, the close confirmation and Open Backup Folder are answered or
    recorded by the case."""

    def __init__(self, cfg, worker_argv="test", memory_limit=None, pick=None, confirm_close=True, settle=True, **kw):
        import tkinter as tk
        import tempfile
        from sfm_character_tools_updater.gui import app as gapp
        global TK_ROOT
        tempfile.tempdir = os.path.join(RUN, "tmp")
        if TK_ROOT is None:
            # One interpreter for the whole group: each case's window is a Toplevel of it, so no Tk
            # interpreter is ever deleted, and closed windows are collected on this (main) thread.
            TK_ROOT = tk.Tk()
            TK_ROOT.withdraw()
        self.tk = TK_ROOT
        self.root = tk.Toplevel(TK_ROOT)
        self.root.withdraw()
        self.pick = pick
        self.close_texts = []
        self.opened = []
        self.busy_trace = []
        self.confirm = confirm_close
        argv = test_worker_argv(**kw) if worker_argv == "test" else worker_argv
        self.app = gapp.App(self.root, installations=[cfg], worker_argv=argv, memory_limit=memory_limit, env=ENV,
                            pick_file=lambda: self.pick or "", pick_folder=lambda: "",
                            confirm_close=lambda t: (self.close_texts.append(t), self.confirm)[1],
                            open_folder=self.opened.append)
        if settle:
            self.settle()

    def pump(self, cond, timeout=900):
        t0 = time.time()
        while not cond():
            if self.app.closed or time.time() - t0 > timeout:
                return False
            self.tk.update()
            if self.app.screen == "busy":
                self.busy_trace.append((self.app.panel_heading, str(getattr(self.app, "busy_bar", ""))))
            time.sleep(0.03)
        self.tk.update()
        return True

    def settle(self, timeout=900):
        return self.pump(lambda: self.app.run is None and self.app.screen not in ("busy", "checking"), timeout)

    def click(self, key):
        self.app.buttons[key].invoke()
        return self.settle()

    def panel(self, key):
        self.app.panel_buttons[key].invoke()
        return self.settle()

    def view(self):
        a = self.app
        return {"screen": a.screen, "kind": getattr(a, "panel_kind", None), "heading": getattr(a, "panel_heading", ""),
                "text": getattr(a, "panel_text", ""),
                "panel_buttons": sorted(k for k in a.panel_buttons if k != "row"),
                "panel_labels": {k: str(b.cget("text")) for k, b in a.panel_buttons.items() if k != "row"},
                "actions": {k: str(b.cget("state")) for k, b in a.buttons.items()},
                "state_label": str(a.state_label.cget("text")), "alert": str(a.alert_label.cget("text"))}

    def commands(self):
        return [h["step"] for h in self.app.history]

    def results(self):
        return [{"step": h["step"], "outcome": h["result"].get("outcome"), "message": h["result"].get("message"),
                 "worker": {k: v for k, v in (h["result"].get("worker") or {}).items() if k != "worker_result"},
                 "details": h["result"].get("details"), "staging_cleanup": h["result"].get("staging_cleanup"),
                 "user_backup": h["result"].get("user_backup")} for h in self.app.history]

    def close(self):
        import gc
        if self.app is not None and not self.app.closed:
            self.app.on_close()
        try:
            self.root.destroy()
        except Exception:
            pass
        self.app = None
        gc.collect()


def actions_on(v):
    return all(s == "normal" for s in v["actions"].values())


def actions_off(v):
    return all(s == "disabled" for s in v["actions"].values())


def staging_entries(cfg):
    p = os.path.join(cfg, "sfm_character_tools_updater", "staging")
    return sorted(os.listdir(p)) if os.path.isdir(p) else []


def backups(cfg):
    p = os.path.join(cfg, "sfm_character_tools_backups")
    return {n: sha_file(os.path.join(p, n)) for n in sorted(os.listdir(p))} if os.path.isdir(p) else None


PEAKS = []
TK_ROOT = None
ACTIONS_DESC = ("Download the flex and bone organization maintained by ChadChan3D.",)
EXACT = {
    "match": "Character Tools data already matches the animation-group TXT in SFM. Nothing was changed.",
    "replace_lead": "This will replace SFM's animation-group TXT with your chosen file and build matching Character "
                    "Tools data.",
    "replace_backup": "Your current animation-group TXT will be saved in the Backups folder.",
    "updated": "Your chosen animation-group TXT and matching Character Tools data are installed.",
    "saved": "Your previous animation-group TXT was saved in the Backups folder.",
    "status": "Installed animation-group TXT and Character Tools data match.",
    "rebuilt": "Character Tools data now matches the animation-group TXT in SFM.",
}


def gui_case(nm, cfg, g, v, why, views, extra=None):
    for r in g.results():
        if r["worker"].get("peak_job_memory"):
            PEAKS.append({"case": nm, "command": r["step"], "peak": r["worker"]["peak_job_memory"],
                          "limit": r["worker"]["memory_limit"], "outcome": r["outcome"]})
    rec = {"views": views, "commands": g.commands(), "results": g.results(), "opened": list(g.opened)}
    rec.update(extra or {})
    g.close()
    return finalize_case(nm, cfg, [], "PASS" if v else "FAIL", why if v else "unexpected: %s" % json.dumps(
        {"views": views, "commands": rec["commands"]}, default=str)[:700], rec)


def group_U():
    """L-4 GUI (usability refinement): the three actions end-to-end with the approved wording, one
    explicit replacement confirmation bound to the observed TXT, user backups, published-version
    outcomes, SFM gates, recovery, worker containment and staging cleanup."""
    R = []
    from sfm_character_tools_updater import supervisor, user_backup, layout as lay
    from sfm_character_tools_updater.gui import app as gapp
    start_fake()
    ensure_l3_packages()
    S1 = pkg_files("L3_s1")
    bdir_of = lambda cfg: os.path.join(cfg, "sfm_character_tools_backups")

    # U1 Update Using SFM's TXT: one click installs while SFM is closed
    nm = "U1_update_from_my_txt_one_click"
    cfg = make_install(nm, master="G3", gens=("g1",))
    g = Gui(cfg)
    v0 = g.view()
    g.click("rebuild")
    v1 = g.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = (v0["screen"] == "home" and "doesn't match" in v0["alert"] and v0["state_label"] == "" and actions_on(v0)
         and v1["kind"] == "success" and v1["heading"] == "Character Tools data updated" and v1["text"] == EXACT["rebuilt"]
         and v1["state_label"] == EXACT["status"] and v1["alert"] == ""
         and {t for t, b in g.busy_trace} == {"Updating Character Tools data\u2026"}
         and len({b for t, b in g.busy_trace}) == 1 and ok
         and sha_file(os.path.join(cfg, "sfm_defaultanimationgroups.txt")) == SHA["G3"]
         and g.commands() == ["status", "prepare-rebuild", "install"] and staging_entries(cfg) == []
         and backups(cfg) is None)
    R.append(gui_case(nm, cfg, g, v, "one click: prepare-rebuild then install under one stable 'Updating Character "
                                     "Tools data…' message and one progress bar; 'Character Tools data updated'; exact "
                                     "G3 set; TXT unchanged; no backup; status refreshed", [v0, v1],
                      {"busy_trace": sorted(set(g.busy_trace))}))

    # U2 matching data -> the approved NOOP wording
    nm = "U2_update_from_my_txt_already_matches"
    cfg = make_install(nm)
    before = active_set(tree(cfg))
    g = Gui(cfg)
    v0 = g.view()
    g.click("rebuild")
    v1 = g.view()
    v = (v0["state_label"] == EXACT["status"] and v0["alert"] == ""
         and v1["heading"] == "Your data already matches" and v1["text"] == EXACT["match"]
         and active_set(tree(cfg)) == before and g.commands() == ["status", "prepare-rebuild", "install"])
    R.append(gui_case(nm, cfg, g, v, "'Your data already matches' / exact sync text from the backend's verified "
                                     "NOOP; nothing changed", [v0, v1]))

    # U3 Choose Another TXT File: confirmation, replacement, user backup, Open Backup Folder
    nm = "U3_choose_another_file_replace"
    cfg = make_install(nm)
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    g = Gui(cfg, pick=src)
    g.click("import")
    v1 = g.view()
    act_mid = active_set(tree(cfg))
    g.panel("replace")
    v2 = g.view()
    bk = backups(cfg) or {}
    ok, d = final_is(cfg, ("G3", "g3"))
    name = list(bk)[0] if len(bk) == 1 else ""
    if "open_backup" in g.app.panel_buttons:
        g.app.panel_buttons["open_backup"].invoke()
    v = (v1["screen"] == "confirm" and v1["heading"] == "Replace your animation groups?"
         and v1["text"] == "%s\n\n%s\n%s" % (EXACT["replace_lead"], EXACT["replace_backup"], bdir_of(cfg))
         and v1["panel_labels"] == {"replace": "Replace Groups", "cancel": "Cancel"}
         and act_mid == expected_active("G1", "g1")
         and v2["heading"] == "Animation groups updated"
         and v2["text"] == "%s\n\n%s\n%s" % (EXACT["updated"], EXACT["saved"], os.path.join(bdir_of(cfg), name))
         and v2["panel_labels"] == {"open_backup": "Open Backup Folder"} and ok
         and list(bk.values()) == [SHA["G1"]] and user_backup.NAME_RE.match(name)
         and g.opened == [os.path.join(bdir_of(cfg), name)]
         and [sha_file(p) for p in retired_masters(cfg)] == [SHA["G1"]] and sha_file(src) == SHA["G3"]
         and g.commands() == ["status", "prepare-import", "install"])
    R.append(gui_case(nm, cfg, g, v, "exact confirmation text with the backup folder; nothing installed until "
                                     "Replace Groups; exact G3 set; verified backup of the previous TXT (G1) shown by "
                                     "name and opened by Open Backup Folder; internal retired copy unchanged; "
                                     "chosen file unchanged", [v1, v2]))

    # U4 Cancel at the confirmation
    nm = "U4_choose_another_file_cancel"
    cfg = make_install(nm)
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    before = tree(cfg)
    g = Gui(cfg, pick=src)
    g.click("import")
    g.panel("cancel")
    v1 = g.view()
    v = (v1["heading"] == "Nothing was changed" and tree(cfg) == before and staging_entries(cfg) == []
         and backups(cfg) is None and g.commands() == ["status", "prepare-import", "discard-prepared"])
    R.append(gui_case(nm, cfg, g, v, "Cancel: preparation discarded; nothing installed; no backup", [v1]))

    # U5 consent invalidated: installed TXT edited after the confirmation was shown
    nm = "U5_destination_changed_after_confirmation"
    cfg = make_install(nm)
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    g = Gui(cfg, pick=src)
    g.click("import")
    master = os.path.join(cfg, "sfm_defaultanimationgroups.txt")
    wbytes(master + ".edit", open(G2_TXT, "rb").read())
    os.replace(master + ".edit", master)
    act0 = active_set(tree(cfg))
    g.panel("replace")
    v1 = g.view()
    v = (v1["heading"] == "Your animation groups changed" and active_set(tree(cfg)) == act0
         and sha_file(master) == SHA["G2"] and backups(cfg) is None and not txdirs(cfg))
    R.append(gui_case(nm, cfg, g, v, "TXT changed after the confirmation: refused before any backup or install "
                                     "('Your animation groups changed'); nothing replaced", [v1]))

    # U6 consent invalidated: chosen file changed after the confirmation was shown
    nm = "U6_source_changed_after_confirmation"
    cfg = make_install(nm)
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    g = Gui(cfg, pick=src)
    g.click("import")
    wbytes(src + ".edit", open(G2_TXT, "rb").read())
    os.replace(src + ".edit", src)
    act0 = active_set(tree(cfg))
    g.panel("replace")
    v1 = g.view()
    bk = backups(cfg) or {}
    v = (v1["heading"] == "The file you chose changed" and active_set(tree(cfg)) == act0
         and "Backups" not in v1["text"] and all(h == SHA["G1"] for h in bk.values())
         and (g.results()[-1]["user_backup"] or {}).get("previous_txt_replaced") is False)
    R.append(gui_case(nm, cfg, g, v, "chosen file changed after the confirmation: 'The file you chose changed', "
                                     "nothing replaced, no backup claimed (a verified copy of the still-installed "
                                     "TXT may remain)", [v1], {"backups": bk}))

    # U7 unusable file and cancelled picker
    nm = "U7_unusable_file_and_cancelled_picker"
    cfg = make_install(nm)
    bad = os.path.join(WORK, "ext", nm, "notes.txt")
    wbytes(bad, b"this is not an animation group file\n")
    before = tree(cfg)
    g = Gui(cfg, pick="")
    g.click("import")
    v0 = g.view()
    g.pick = bad
    g.click("import")
    v1 = g.view()
    v = (v0["screen"] == "home" and g.commands()[:1] == ["status"] and v1["heading"] == "This file can't be used"
         and "flex and bone group definitions" in v1["text"] and tree(cfg) == before
         and g.commands() == ["status", "prepare-import"])
    R.append(gui_case(nm, cfg, g, v, "no file chosen: nothing runs; an unusable file: 'This file can't be used' "
                                     "with the flex/bone explanation; nothing changed", [v0, v1]))

    # U8 Get Published Version outcomes
    nm = "U8_published_version_outcomes"
    cfg = make_install(nm)
    steps = []
    serve([])
    g = Gui(cfg, net=True, trust=True)
    g.click("official")
    steps.append(g.view())
    g.close()
    serve([(10, "data-v1.0.0", S1, {})])
    g = Gui(cfg, net=True, trust=False)
    g.click("official")
    steps.append(g.view())
    g.close()
    serve([])
    FAKE.pages = {1: {"status": 500, "json": {}}}
    g = Gui(cfg, net=True, trust=True)
    g.click("official")
    steps.append(g.view())
    v = (steps[0]["heading"] == "Nothing published yet" and "download" not in steps[0]["panel_buttons"]
         and steps[1]["heading"] == "Published version rejected" and "download" not in steps[1]["panel_buttons"]
         and steps[2]["heading"] == "Couldn't check for a published version"
         and active_set(tree(cfg)) == expected_active("G1", "g1"))
    R.append(gui_case(nm, cfg, g, v, "none published -> 'Nothing published yet'; unverified -> 'Published version "
                                     "rejected'; failed check -> 'Couldn't check for a published version'; nothing "
                                     "offered or changed", steps))

    # U9 published version installed over a customized TXT (test key), then reported as installed
    nm = "U9_published_version_install"
    cfg = make_install(nm)
    serve([(10, "data-v1.0.0", S1, {})])
    g = Gui(cfg, net=True, trust=True)
    g.click("official")
    v1 = g.view()
    g.panel("download")
    v2 = g.view()
    g.panel("replace")
    v3 = g.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    bk = backups(cfg) or {}
    g.click("official")
    v4 = g.view()
    v = (v1["heading"] == "Published version available"
         and v1["text"] == "A published animation-group TXT and matching Character Tools data are available to install."
         and v1["panel_labels"]["download"] == "Download and Install" and v2["heading"] == "Replace your animation groups?"
         and EXACT["replace_backup"] in v2["text"] and v3["heading"] == "Published version 1.0.0 installed"
         and EXACT["saved"] in v3["text"] and ok and list(bk.values()) == [SHA["G1"]]
         and v4["heading"] == "Published version already installed"
         and v4["text"] == "Published animation-group version 1.0.0 is already installed. Nothing was changed."
         and staging_entries(cfg) == [])
    R.append(gui_case(nm, cfg, g, v, "available -> Download and Install -> replacement confirmation (customized TXT) "
                                     "-> installed with the previous TXT backed up -> next check 'Published version "
                                     "already installed' (version 1.0.0)", [v1, v2, v3, v4]))

    # U10 / U11 SFM RUNNING or UNKNOWN: Update Using SFM's TXT prepares, asks to close SFM, then finishes
    for nm, form in (("U10_update_waits_for_sfm_running", RUNNING), ("U11_update_waits_for_state_unknown", "raise")):
        cfg = make_install(nm, master="G3", gens=("g1",))
        g = Gui(cfg)
        g.app.worker_argv = test_worker_argv(inject={"process": form})
        act0 = active_set(tree(cfg))
        g.click("rebuild")
        v1 = g.view()
        unchanged = active_set(tree(cfg)) == act0
        g.app.panel_buttons["finish"].invoke()
        g.settle()
        v2 = g.view()
        still = active_set(tree(cfg)) == act0
        g.app.worker_argv = test_worker_argv()
        g.panel("finish")
        v3 = g.view()
        ok, d = final_is(cfg, ("G3", "g3"))
        v = (v1["screen"] == "wait" and v1["heading"] == "Close SFM to finish"
             and v1["panel_labels"] == {"finish": "Finish Update", "cancel": "Cancel"} and unchanged
             and v2["screen"] == "wait" and still and v3["heading"] == "Character Tools data updated" and ok
             and g.commands() == ["status", "prepare-rebuild", "install", "install"])
        R.append(gui_case(nm, cfg, g, v, "SFM %s: prepared privately, no install, 'Close SFM to finish'; Finish Update "
                                         "refused while open; Finish Update after SFM closed -> installed" % (
                                             "RUNNING" if form == RUNNING else "state UNKNOWN"), [v1, v2, v3]))

    # U12 replacement refused while SFM runs: no backup, then completes after SFM closes
    nm = "U12_replace_waits_for_sfm"
    cfg = make_install(nm)
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    g = Gui(cfg, pick=src)
    g.click("import")
    g.app.worker_argv = test_worker_argv(inject={"process": RUNNING})
    g.panel("replace")
    v1 = g.view()
    no_backup = backups(cfg) is None and active_set(tree(cfg)) == expected_active("G1", "g1")
    g.app.worker_argv = test_worker_argv()
    g.panel("finish")
    v2 = g.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = (v1["screen"] == "wait" and v1["panel_labels"].get("finish") == "Replace Groups" and no_backup
         and v2["heading"] == "Animation groups updated" and ok and list((backups(cfg) or {}).values()) == [SHA["G1"]])
    R.append(gui_case(nm, cfg, g, v, "Replace Groups with SFM open: refused, no backup made; Replace Groups after "
                                     "SFM closed -> replaced with one verified backup", [v1, v2]))

    # U13 recovery presented and executed; U14 recovery refused while SFM runs
    for nm, form in (("U13_recovery_presented_and_executed", None), ("U14_recovery_refused_sfm_running", RUNNING)):
        cfg = make_install(nm, master="G3", gens=("g1",))
        st = activate(nm, "interrupt", cfg, "rebuild", SHA["G3"], stop_at="act_moved_forward_0", action="kill")
        g = Gui(cfg, **({"inject": {"process": form}} if form else {}))
        v1 = g.view()
        g.panel("recover")
        v2 = g.view()
        if form is None:
            ok, d = final_is(cfg, ("G3", "g3"))
            v = (st["killed"] and v1["screen"] == "recovery" and actions_off(v1) and "choose Recover" in v1["text"]
                 and v2["heading"] == "Recovered" and actions_on(v2) and ok
                 and g.commands() == ["status", "recover", "status"])
            why = "interrupted update -> recovery screen (actions unavailable) -> Recover -> 'Recovered'; exact set"
        else:
            v = (st["killed"] and v1["screen"] == "recovery" and v2["screen"] == "recovery"
                 and "Close SFM, then choose Recover." in v2["text"] and txdirs(cfg))
            why = "Recover with SFM open -> stays in recovery with 'Close SFM, then choose Recover.'"
        R.append(gui_case(nm, cfg, g, v, why, [v1, v2]))

    # U15 worker killed during the update -> recovery, never success
    nm = "U15_worker_killed_during_update"
    cfg = make_install(nm, master="G3", gens=("g1",))
    marker = os.path.join(WORK, "markers", nm)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    g = Gui(cfg, hold="act_moved_forward_0", marker=marker)
    g.app.buttons["rebuild"].invoke()
    g.pump(lambda: os.path.exists(marker), 300)
    pid = g.app.run.pid
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    g.settle()
    v1 = g.view()
    g.app.worker_argv = test_worker_argv()
    g.panel("recover")
    v2 = g.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = (v1["screen"] == "recovery" and "The update stopped unexpectedly" in v1["text"]
         and "Close SFM, then choose Recover." in v1["text"] and not alive(pid) and v2["heading"] == "Recovered" and ok)
    R.append(gui_case(nm, cfg, g, v, "worker killed mid-update -> 'The update stopped unexpectedly ... choose "
                                     "Recover' (no success) -> Recover -> exact set", [v1, v2]))

    # U16 memory ceiling
    nm = "U16_worker_memory_ceiling"
    cfg = make_install(nm, master="G3", gens=("g1",))
    before = tree(cfg, include_staging=True)
    g = Gui(cfg)
    g.app.memory_limit = 64 * 1024 * 1024
    g.click("rebuild")
    v1 = g.view()
    v = (g.results()[-1]["outcome"] == "WORKER_MEMORY_LIMIT" and v1["heading"] == "The update was stopped"
         and "more memory" in v1["text"] and tree(cfg) == before)
    R.append(gui_case(nm, cfg, g, v, "64 MiB ceiling (test) -> 'The update was stopped ... more memory'; nothing "
                                     "installed", [v1]))

    # U17 window closed during the update (confirmed) -> worker stopped -> recoverable
    nm = "U17_window_closed_during_update"
    cfg = make_install(nm, master="G3", gens=("g1",))
    marker = os.path.join(WORK, "markers", nm)
    g = Gui(cfg, hold="act_moved_forward_0", marker=marker)
    g.app.buttons["rebuild"].invoke()
    g.pump(lambda: os.path.exists(marker), 300)
    pid = g.app.run.pid
    g.app.on_close()
    closed, texts = g.app.closed, list(g.close_texts)
    time.sleep(1)
    gone = not alive(pid)
    g2 = Gui(cfg)
    v1 = g2.view()
    g2.panel("recover")
    v2 = g2.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = closed and texts and "choose Recover" in texts[0] and gone and v1["screen"] == "recovery" and ok
    R.append(gui_case(nm, cfg, g2, v, "close during the update: warned, confirmed; worker stopped; next start shows "
                                      "recovery; Recover -> exact set", [v1, v2], {"close_texts": texts}))

    # U18 GUI process killed during the update -> the job ends the worker -> recoverable
    nm = "U18_gui_process_killed_during_update"
    cfg = make_install(nm, master="G3", gens=("g1",))
    marker = os.path.join(WORK, "markers", nm)
    pidfile = os.path.join(WORK, "markers", nm + ".pids")
    argv = test_worker_argv(hold="act_moved_forward_0", marker=marker)
    p = subprocess.Popen([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, os.path.join(SUPPORT, "gui_driver.py"),
                          cfg, pidfile, json.dumps(argv)], env=ENV, cwd=os.path.join(RUN, "tmp"))
    t0 = time.time()
    while not os.path.exists(pidfile) and time.time() - t0 < 300 and p.poll() is None:
        time.sleep(0.2)
    gui_pid, worker_pid = (int(x) for x in open(pidfile).read().split()) if os.path.exists(pidfile) else (0, 0)
    alive_before = worker_pid and alive(worker_pid)
    subprocess.run(["taskkill", "/F", "/PID", str(p.pid)], capture_output=True)
    p.wait(60)
    t0 = time.time()
    while worker_pid and alive(worker_pid) and time.time() - t0 < 20:
        time.sleep(0.5)
    gone = worker_pid and not alive(worker_pid)
    steps = [status(nm, "status_after", cfg), recover(nm, "recover", cfg)]
    ok, d = final_is(cfg, ("G3", "g3"))
    v = alive_before and gone and steps[0].get("recovery_needed") is True and steps[1]["outcome"] == "OK" and ok
    R.append(finalize_case(nm, cfg, steps, "PASS" if v else "FAIL",
                           "GUI process killed mid-update: its worker ended with it; recovery needed; recovered" if v
                           else "alive_before=%s gone=%s %s" % (alive_before, gone, outcomes(steps)),
                           {"gui_pid": gui_pid, "worker_pid": worker_pid}))

    # U19 user backups: never overwritten, identical copy reused, collision-safe, failure refuses
    nm = "U19_user_backup_rules"
    cfg = make_install(nm)
    L = lay.Layout(cfg)
    bdir = bdir_of(cfg)
    fixed = time.mktime((2026, 10, 18, 12, 0, 0, 0, 0, -1))
    other = os.path.join(bdir, "sfm_defaultanimationgroups_backup_20261018-120000.txt")
    wbytes(other, b"an earlier, different backup\n")
    other_sha = sha_file(other)
    unrelated = os.path.join(bdir, "my_notes.txt")
    wbytes(unrelated, b"user file\n")
    b1 = user_backup.save_previous_txt(L, SHA["G1"], now=fixed)
    b2 = user_backup.save_previous_txt(L, SHA["G1"], now=fixed + 60)
    try:
        user_backup.save_previous_txt(L, SHA["G3"], now=fixed)
        mism = None
    except Exception as e:
        mism = getattr(e, "message_key", str(e))
    rules_ok = (b1["name"] == "sfm_defaultanimationgroups_backup_20261018-120000_2.txt" and not b1["reused"]
                and sha_file(os.path.join(bdir, b1["name"])) == SHA["G1"] and sha_file(other) == other_sha
                and b2["reused"] and b2["name"] == b1["name"] and sha_file(unrelated) == sha(b"user file\n")
                and mism == "DESTINATION_CHANGED" and len(os.listdir(bdir)) == 3)
    # failure: the Backups location is a file -> the replacement is refused and nothing changes
    nm2 = cfg
    cfg = make_install(nm + "_fail")
    wbytes(bdir_of(cfg), b"not a folder")
    src = os.path.join(WORK, "ext", nm, "chosen.txt")
    wcopy(G3_TXT, src)
    before = active_set(tree(cfg))
    g = Gui(cfg, pick=src)
    g.click("import")
    g.panel("replace")
    v1 = g.view()
    v = (rules_ok and v1["heading"] == "Nothing was replaced" and active_set(tree(cfg)) == before and not txdirs(cfg)
         and "saved in the Backups folder." not in v1["text"])
    R.append(gui_case(nm, cfg, g, v, "existing backup with the same name kept (new name _2); identical backup reused; "
                                     "unrelated files untouched; wrong TXT identity refused; Backups location "
                                     "unusable -> 'Nothing was replaced', nothing changed", [v1],
                      {"b1": b1, "b2": b2, "rules_cfg": nm2}))

    # U20 staging cleanup scope (consumed, stale, unexpected, unfamiliar, recent)
    nm = "U20_staging_cleanup_scope"
    cfg = make_install(nm, master="G3", gens=("g1",))
    st0 = run_op(nm, "seed_prep", ["prepare-rebuild"], cfg)
    stg = os.path.join(cfg, "sfm_character_tools_updater", "staging")
    old = time.time() - 3 * 24 * 3600
    stale_prep = st0["prepid"]
    for p_ in [os.path.join(stg, stale_prep)] + [os.path.join(stg, stale_prep, n) for n in
                                                 os.listdir(os.path.join(stg, stale_prep))]:
        os.utime(p_, (old, old))
    seeds = {"download-" + "a" * 32: [("release.json", b"{}"), ("release.sig", b"x" * 64)],
             "b" * 32: [("prepared.json", b"{}"), ("unexpected.bin", b"x")],
             "notes": [("readme.txt", b"x")], "c" * 32: [("prepared.json", b"{}")]}
    for d_, files in seeds.items():
        for n, data in files:
            wbytes(os.path.join(stg, d_, n), data)
            os.utime(os.path.join(stg, d_, n), (old, old))
        os.utime(os.path.join(stg, d_), (old, old))
    recent = "d" * 32
    wbytes(os.path.join(stg, recent, "prepared.json"), b"{}")
    g = Gui(cfg)
    g.click("rebuild")
    v1 = g.view()
    cl = g.results()[-1]["staging_cleanup"] or {}
    left = staging_entries(cfg)
    v = (v1["kind"] == "success" and set(cl.get("removed", [])) >= {stale_prep, "download-" + "a" * 32, "c" * 32}
         and {"b" * 32, "notes", recent} <= set(left))
    R.append(gui_case(nm, cfg, g, v, "after an update: consumed and stale updater folders removed; unexpected, "
                                     "unfamiliar and recent folders kept", [v1], {"cleanup": cl, "left": left}))

    # U21 startup line, final layout, About window, Close buttons, diagnostics kept out of the interface
    nm = "U21_startup_layout_about_close"
    cfg = make_install(nm)
    g = Gui(cfg, settle=False)
    import tkinter.ttk as ttk_
    first = {"screen": g.app.screen, "label": str(g.app.state_label.cget("text")),
             "bars": sum(isinstance(w, ttk_.Progressbar) for w in g.app.panel.winfo_children())}
    g.settle()
    after = g.view()

    def widgets(w, out):
        for c in w.winfo_children():
            out.append(c)
            widgets(c, out)
        return out

    def text_of(c):
        try:
            return str(c.cget("text"))
        except Exception:
            return None

    def font_of(c):
        try:
            f = str(c.cget("font"))
        except Exception:
            return ""
        if not f:
            try:
                f = str(ttk_.Style(c).lookup(c.cget("style") or c.winfo_class(), "font"))
            except Exception:
                f = ""
        return f
    main_w = widgets(g.app.root, [])
    main_texts = [t for t in (text_of(c) for c in main_w) if t]
    by_text = {text_of(c): c for c in main_w if text_of(c)}
    g.root.deiconify()
    g.root.geometry("800x560+100+100")
    g.tk.update()
    g.app.show_about()
    g.tk.update()
    about = g.app.about
    about_w = widgets(about, [])
    about_texts = [t for t in (text_of(c) for c in about_w) if t]
    title = about.title()
    cx = about.winfo_rootx() + about.winfo_width() // 2
    cy = about.winfo_rooty() + about.winfo_height() // 2
    mx = g.root.winfo_rootx() + g.root.winfo_width() // 2
    my = g.root.winfo_rooty() + g.root.winfo_height() // 2
    centered = abs(cx - mx) <= 40 and abs(cy - my) <= 40
    close_btn = [c for c in about_w if text_of(c) == "Close"]
    close_right = bool(close_btn) and close_btn[0].winfo_rootx() + close_btn[0].winfo_width() > \
        about.winfo_rootx() + about.winfo_width() * 0.6
    order = [t for t in about_texts if t in ("Version:", "Author:")]
    close_btn[0].invoke() if close_btn else None
    g.tk.update()
    about_closed = g.app.about is None
    g.root.withdraw()
    diag = json.loads(g.app.diagnostics())
    bold = {t: "bold" in font_of(by_text[t]) for t in (gapp.REMINDER, "SFM folder:", ACTIONS_DESC[0])
            if t in by_text}
    main_close = by_text.get("Close")
    v = (first["screen"] == "checking" and first["label"] == "Checking animation-group data\u2026" and first["bars"] == 0
         and after["state_label"] == EXACT["status"] and after["alert"] == ""
         and g.app.root.title() == "SFM Control Group Updater" and "SFM Control Group Updater" in main_texts
         and "Choose an action." not in main_texts and "Show Details" not in main_texts
         and "About" in main_texts and main_close is not None and gapp.REMINDER in main_texts
         and not any(bold.values()) and len(bold) == 3
         and title == "About SFM Control Group Updater" and "About SFM Control Group Updater" in about_texts
         and gapp.ABOUT in about_texts and order == ["Version:", "Author:"]
         and PRODUCT_VERSION() in about_texts and "ChadChan3D" in about_texts
         and "Copy Diagnostic Information" not in about_texts and centered and close_right and about_closed
         and diag.get("version") == PRODUCT_VERSION() and diag.get("results")
         and not any(t.lstrip().startswith("{") for t in main_texts + about_texts))
    idle_close_ok = None
    if v:
        main_close.invoke()
        idle_close_ok = g.app.closed is True and g.close_texts == []
        v = idle_close_ok
    R.append(gui_case(nm, cfg, g, v, "startup 'Checking animation-group data…' with no bar, then the subtle match "
                                     "status; final title; no 'Choose an action.'; regular-weight reminder, folder "
                                     "label and descriptions; About titled 'About SFM Control Group Updater' with the "
                                     "approved text, Version then Author, centered, Close at bottom right, no Copy "
                                     "Diagnostic Information; diagnostics kept internally; main Close exits when idle",
                      [first, after], {"about_texts": about_texts, "bold": bold, "centered": centered,
                                       "close_right": close_right, "idle_close_ok": idle_close_ok}))

    # U21b main-window Close during an update keeps the safe-close behavior
    nm = "U21b_close_button_during_update"
    cfg = make_install(nm, master="G3", gens=("g1",))
    marker = os.path.join(WORK, "markers", nm)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    g = Gui(cfg, hold="act_moved_forward_0", marker=marker, confirm_close=False)
    g.app.buttons["rebuild"].invoke()
    g.pump(lambda: os.path.exists(marker), 300)
    pid = g.app.run.pid
    close_btn = [c for c in widgets(g.app.root, []) if text_of(c) == "Close"][0]
    close_btn.invoke()
    declined = (not g.app.closed) and g.close_texts and "choose Recover" in g.close_texts[0] and alive(pid)
    g.confirm = True
    close_btn.invoke()
    time.sleep(1)
    stopped = g.app.closed and not alive(pid)
    g2 = Gui(cfg)
    v1 = g2.view()
    g2.panel("recover")
    v2 = g2.view()
    ok, d = final_is(cfg, ("G3", "g3"))
    v = declined and stopped and v1["screen"] == "recovery" and v2["heading"] == "Recovered" and ok
    R.append(gui_case(nm, cfg, g2, v, "Close during an update asks first: declined -> the update keeps running; "
                                      "confirmed -> worker stopped; next start shows recovery; Recover -> exact set",
                      [v1, v2], {"close_texts": list(g.close_texts)}))

    # U22 shipping worker command and production ceiling
    nm = "U22_shipping_worker_update"
    cfg = make_install(nm, master="G3", gens=("g1",))
    real0 = PSTAT()
    g = Gui(cfg, worker_argv=None)
    g.click("rebuild")
    v1 = g.view()
    res = g.results()
    real1 = PSTAT()
    argv0 = supervisor.default_worker_argv()
    if real0[0] == real1[0] == "CLEAR":
        from sfm_character_tools_updater.messages import MESSAGES as M_
        ok, d = final_is(cfg, ("G3", "g1"))
        v = (v1["kind"] == "warning" and v1["text"] == M_["SOFTWARE_UNVERIFIED"] and ok and not txdirs(cfg)
             and "success" not in v1["kind"])
    else:
        v = v1["screen"] == "wait"
    v = v and (argv0[-2:] == ["-m", "sfm_character_tools_updater.worker"] and "test_worker" not in " ".join(argv0)
               and all(r["worker"].get("memory_limit") == supervisor.MEMORY_LIMIT for r in res))
    R.append(gui_case(nm, cfg, g, v, "shipping worker and 2 GiB ceiling, real process query %s" % real0[0], [v1],
                      {"default_worker_argv": argv0}))

    # U23 workloads within the ceiling
    nm = "U23_workloads_within_ceiling"
    peaks = [p_ for p_ in PEAKS if p_["outcome"] != "WORKER_MEMORY_LIMIT" and p_["limit"] == supervisor.MEMORY_LIMIT]
    top = max(p_["peak"] for p_ in peaks) if peaks else 0
    v = bool(peaks) and top < supervisor.MEMORY_LIMIT / 4
    R.append(finalize_case(nm, None, [], "PASS" if v else "FAIL",
                           "%d bounded worker runs at the production ceiling; highest peak %.0f MiB of %d MiB" % (
                               len(peaks), top / 2 ** 20, supervisor.MEMORY_LIMIT // 2 ** 20), {"peaks": PEAKS}))

    # U24 product surface: labels, entry point, imports, worker options
    nm = "U24_product_surface"
    import ast
    pkg = os.path.join(UPDATER, "sfm_character_tools_updater")
    src_ = open(os.path.join(pkg, "gui", "app.py"), encoding="utf-8").read()
    main_src = src_[src_.index("def main():"):]
    imports = set()
    for node in ast.walk(ast.parse(src_)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(("." * node.level) + node.module)
        elif isinstance(node, ast.Import):
            imports |= {a.name for a in node.names}
    cp = subprocess.run([PY3, "-E", "-s", "-B", "-X", "pycache_prefix=" + NOPYC, "-c",
                         "import sys; import sfm_character_tools_updater.gui.app; "
                         "print(sorted(m for m in sys.modules if m.split('.')[0] in ('http','ssl','socket','urllib') "
                         "or m.endswith('discovery') or m.endswith('hooks')))"],
                        capture_output=True, text=True, env=ENV, cwd=UPDATER, timeout=120)
    out = os.path.join(WORK, "results", "ops", nm + "__x.json")
    guard(out)
    cfg24 = make_install(nm)
    cps = [product_worker(["status", "--installation", cfg24, "--result", out] + a, UPDATER)
           for a in (["--hold-at", "x"], ["--hold-marker", "x"])]
    labels = [(k, l, d_) for k, l, d_ in gapp.ACTIONS]
    v = (labels == [("official", "Get Published Version",
                     "Download the flex and bone organization maintained by ChadChan3D."),
                    ("rebuild", "Update Using SFM's TXT",
                     "Build Character Tools data from the animation-group TXT already in your SFM folder."),
                    ("import", "Choose Another TXT File", "Select a different animation-group TXT to use in SFM.")]
         and gapp.TITLE == "SFM Control Group Updater"
         and gapp.REMINDER == "Close SFM before updating its animation-group TXT or Character Tools data."
         and gapp.FOLDER_PICKER_TITLE == "Select your SourceFilmmaker folder"
         and "initialdir=sfm_folder(self.cfg)" in src_ and "including any changes" not in src_
         and "App(root, installations=startup_installations(sys.argv[1:]))" in main_src and "worker_argv" not in main_src
         and gapp.startup_installations(["--trust-key", "x"]) == gapp.detect_installations()
         and gapp.startup_installations(["--sfm-folder", os.path.dirname(os.path.dirname(os.path.dirname(cfg24)))])[0]
         == os.path.normpath(cfg24)
         and imports <= {"json", "os", "re", "subprocess", "sys", "tkinter", "..", "..messages", "ctypes", "winreg"}
         and cp.stdout.strip() == "[]" and all(c.returncode == 2 for c in cps))
    R.append(finalize_case(nm, None, [{"imports": sorted(imports), "gui_import_modules": cp.stdout.strip(),
                                       "worker_rc": [c.returncode for c in cps]}], "PASS" if v else "FAIL",
                           "approved title, labels, descriptions and reminder; the shipping entry passes no test "
                           "arguments; no network, discovery or seam module at GUI import; the worker rejects test "
                           "options" if v else "unexpected imports=%s mods=%s rc=%s labels=%s" % (
                               sorted(imports), cp.stdout, [c.returncode for c in cps], labels)))
    return R


# ------------------------------------------------------------------ L-5: compatibility profile, signed inventory, package
def software_variant(name, mutate=None, sign_key="test_a", raw=None, drop_sig=False):
    """A signed-inventory variant under software_dir(name): the test_a inventory with `mutate`
    applied, re-signed with `sign_key` (or the original signature kept when sign_key is None)."""
    d = software_dir(name)
    if os.path.exists(d):
        return name
    base = software_dir("signed_a", "sfm_character_tools_inventory.json")
    inv = json.load(open(base, encoding="utf-8"))
    if mutate:
        mutate(inv)
    data = raw(inv) if raw else (json.dumps(inv, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    wbytes(os.path.join(d, "sfm_character_tools_inventory.json"), data)
    if sign_key is None:
        wcopy(software_dir("signed_a", "sfm_character_tools_inventory.sig"), os.path.join(d, "sfm_character_tools_inventory.sig"))
    elif not drop_sig:
        producer("sign", "--descriptor", os.path.join(d, "sfm_character_tools_inventory.json"), "--private",
                 keyfile(sign_key, "pem"), "--out", os.path.join(d, "sfm_character_tools_inventory.sig"))
    return name


def frozen_bundle():
    # Per run label: every run copies the bundle it is given into its own clean folder.
    return os.path.join(WORK, "clean", "SFM Control Group Updater")


CLEAN_ENV = None


def frozen_env():
    windir = os.environ.get("SystemRoot", r"C:\\Windows")
    return {"SystemRoot": windir, "WINDIR": windir, "TEMP": os.path.join(RUN, "tmp"), "TMP": os.path.join(RUN, "tmp"),
            "PATH": os.pathsep.join([os.path.join(windir, "System32"), windir]),
            "USERPROFILE": os.environ.get("USERPROFILE", ""), "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "APPDATA": os.environ.get("APPDATA", ""), "SystemDrive": os.environ.get("SystemDrive", "C:"),
            "COMPUTERNAME": os.environ.get("COMPUTERNAME", ""), "USERNAME": os.environ.get("USERNAME", "")}


def frozen_worker(nm, step, args, cfg, extra_env=None):
    out = os.path.join(WORK, "results", "ops", "%s__%s.json" % (nm, step))
    guard(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cwd = os.path.join(WORK, "clean_cwd")
    os.makedirs(cwd, exist_ok=True)
    env = frozen_env()
    env.update(extra_env or {})
    cp = subprocess.run([os.path.join(frozen_bundle(), "sct-updater-worker.exe"), args[0], "--installation", cfg,
                         "--result", out] + list(args[1:]), capture_output=True, text=True, env=env, cwd=cwd,
                        timeout=900, creationflags=0x08000000)
    r = jload(out) if os.path.exists(out) else {}
    r.pop("trace", None)
    r["_rc"] = cp.returncode
    r["_stderr"] = cp.stderr[-600:]
    return r


def under_dir(path, root):
    return norm(path) == norm(root) or norm(path).startswith(norm(root) + "\\")


def group_P():
    """L-5: authority profile, signed installed-software inventory (accept and refuse) and the packaged
    one-folder application run from a clean directory."""
    R = []
    from sfm_character_tools_updater import candidate, official as off
    from sfm_character_tools_updater.compat import inventory as inv_mod, profile as prof
    ensure_packages()
    ensure_software()

    # P1 profile, pins and qualified software identities
    nm = "P1_profile_pins_and_qualified_software"
    spec = json.load(open(SOFTWARE_SPEC, encoding="utf-8"))
    pins_ok = set(candidate.PINS.values()) == (set(prof.PROFILE_1["compiler"].values()) | {
        v for k, v in prof.PROFILE_1["validator_provider"].items() if k.endswith(".py")})
    staged = {f["path"]: sha_file(software_dir("usermod", *f["path"].split("/"))) for f in spec["files"]}
    signed = json.load(open(software_dir("signed_a", "sfm_character_tools_inventory.json"), encoding="utf-8"))
    v = (pins_ok and prof.contract_sha256(prof.PROFILE_1) == prof.PROFILE_SHA256["sct-authority-profile-1"]
         and len(spec["files"]) == 31 and all(staged[f["path"]] == f["sha256"] for f in spec["files"])
         and {f["role"] for f in spec["files"]} >= set(prof.REQUIRED_ROLES)
         and signed["profile_contract_sha256"] == prof.PROFILE_SHA256["sct-authority-profile-1"]
         and signed["runtime_api_version"] == "1.0.0-b2a"
         and signed["runtime_build_id"] == "package-boundary-corrected-2026-09-22"
         and not any(f["path"].endswith((".pyc", ".txt", ".json", ".sfmsidecar")) for f in signed["files"]))
    R.append(finalize_case(nm, None, [{"profile_sha256": prof.PROFILE_SHA256, "files": len(spec["files"])}],
                           "PASS" if v else "FAIL",
                           "profile pins equal the updater's pins; 31 qualified software files staged byte-exact; all "
                           "required roles; the signed inventory names profile, contract hash, runtime API/build; no "
                           "mutable or bytecode files listed" if v else "unexpected"))

    def official_case(nm, why, expect_key=None, variant="signed_a", alter=None, install=False):
        cfg = make_install(nm, software=variant or False)
        if variant == "":
            install_software(os.path.dirname(cfg), signed=None)
        if alter:
            alter(os.path.dirname(cfg))
        before = tree(cfg, include_staging=True)
        st = official_prep(nm, "prep", cfg, pkgdir("G3_s5"))
        steps = [st]
        if expect_key is None:
            ok_ = st["outcome"] == "PREPARED" and (st.get("official") or {}).get("software", {}).get("files") == 31
            if install and ok_:
                steps.append(install_fn(nm, "install", cfg, st["prepid"], st["confirm_sha"], accept=True, trust=True))
                fin, d = final_is(cfg, ("G3", "g3"))
                ok_ = steps[-1]["outcome"] == "COMPLETE" and fin and (steps[-1].get("software") or {}).get(
                    "authority_profile") == "sct-authority-profile-1"
        else:
            ok_ = (st["outcome"] == "REFUSED" and st.get("message") == MESSAGES_[expect_key]
                   and tree(cfg, include_staging=True) == before)
        R.append(finalize_case(nm, cfg, steps, "PASS" if ok_ else "FAIL", why if ok_ else "unexpected %s %s %s" % (
            outcomes(steps), st.get("message"), st.get("details"))))
        return cfg

    from sfm_character_tools_updater.messages import MESSAGES as MESSAGES_
    install_fn = install
    official_case("P2_qualified_installation_accepted", "qualified test installation (31 files, test-signed inventory): "
                  "official prepared with the verified software summary, installed exact G3, re-verified at install",
                  install=True)

    def change_cpm(u):
        p = os.path.join(u, "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py")
        data = open(p, "rb").read()
        os.remove(p)
        wbytes(p, data + b"\n# local change\n")

    def drop_normalizer(u):
        os.remove(os.path.join(u, "scripts", "sfm", "mainmenu", "SFM Character Tools", "Rebuild_Control_Groups_Normalizer.py"))

    def flip_sig(u):
        p = os.path.join(u, INVENTORY_REL + ".sig")
        data = bytearray(open(p, "rb").read())
        os.remove(p)
        data[0] ^= 1
        wbytes(p, bytes(data))
    official_case("P3a_changed_consumer_refused", "changed installed CPM app -> SOFTWARE_MODIFIED; nothing written",
                  "SOFTWARE_MODIFIED", alter=change_cpm)
    official_case("P3b_missing_required_file_refused", "Normalizer removed -> SOFTWARE_MODIFIED; nothing written",
                  "SOFTWARE_MODIFIED", alter=drop_normalizer)
    official_case("P3c_invalid_signature_refused", "inventory signature altered -> SOFTWARE_UNVERIFIED; nothing written",
                  "SOFTWARE_UNVERIFIED", alter=flip_sig)
    official_case("P3d_altered_inventory_refused", "inventory bytes changed under the original signature -> "
                  "SOFTWARE_UNVERIFIED", "SOFTWARE_UNVERIFIED",
                  variant=software_variant("v_altered", lambda d: d.update(software_version="9.9.9"), sign_key=None))
    official_case("P3e_unsupported_profile_refused", "validly signed inventory naming an unimplemented profile -> "
                  "SOFTWARE_UNSUPPORTED", "SOFTWARE_UNSUPPORTED",
                  variant=software_variant("v_profile9", lambda d: d.update(authority_profile="sct-authority-profile-9")))
    official_case("P3f_profile_contract_mismatch_refused", "signed inventory with the profile ID but a different contract "
                  "hash -> SOFTWARE_UNSUPPORTED", "SOFTWARE_UNSUPPORTED",
                  variant=software_variant("v_contract", lambda d: d.update(profile_contract_sha256="0" * 64)))
    official_case("P3g_missing_inventory_refused", "software present but no inventory -> SOFTWARE_UNVERIFIED",
                  "SOFTWARE_UNVERIFIED", variant="")
    official_case("P3h_untrusted_signer_refused", "inventory signed by an untrusted key (test_b) -> SOFTWARE_UNVERIFIED",
                  "SOFTWARE_UNVERIFIED", variant="signed_b")
    official_case("P3i_missing_role_refused", "signed inventory without the Normalizer role -> SOFTWARE_UNSUPPORTED",
                  "SOFTWARE_UNSUPPORTED", variant=software_variant(
                      "v_norole", lambda d: d.update(files=[f for f in d["files"] if f["role"] != "normalizer"])))
    official_case("P3j_path_traversal_refused", "signed inventory with a '..' path -> SOFTWARE_UNVERIFIED",
                  "SOFTWARE_UNVERIFIED", variant=software_variant(
                      "v_traversal", lambda d: d["files"][0].update(path="scripts/../../cfg/x.py")))
    official_case("P3k_runtime_mismatch_refused", "signed inventory with a different runtime build -> "
                  "SOFTWARE_UNSUPPORTED", "SOFTWARE_UNSUPPORTED",
                  variant=software_variant("v_runtime", lambda d: d.update(runtime_build_id="other-build")))

    def mutable_noise(u):
        md = os.path.join(u, "scripts", "sfm", "mainmenu", "SFM Character Tools")
        wbytes(os.path.join(md, "cpm_authority_adapter.pyc"), b"\x03\xf3\r\nstale bytecode")
        wbytes(os.path.join(u, "scripts", "ChadChan3D_CPM", "presets", "library.json"), b"{}")
        wbytes(os.path.join(u, "cfg", "SFM_Character_Preset_Manager.log"), b"log")
    official_case("P4_mutable_data_not_checked", "bytecode, presets and logs added: not inventoried, official prepared",
                  alter=mutable_noise)

    # P5 install-time re-check: the software changes after preparation
    nm = "P5_install_time_recheck"
    cfg = make_install(nm)
    st = official_prep(nm, "prep", cfg, pkgdir("G3_s5"))
    change_cpm(os.path.dirname(cfg))
    act0 = active_set(tree(cfg))
    s2 = install(nm, "install", cfg, st.get("prepid", ""), st.get("confirm_sha", ""), accept=True, trust=True)
    v = (st["outcome"] == "PREPARED" and s2["outcome"] == "REFUSED" and s2.get("message") == MESSAGES_["SOFTWARE_MODIFIED"]
         and active_set(tree(cfg)) == act0 and not txdirs(cfg))
    R.append(finalize_case(nm, cfg, [st, s2], "PASS" if v else "FAIL",
                           "software changed after preparation -> install refused SOFTWARE_MODIFIED before any "
                           "transaction; installed files unchanged" if v else "unexpected %s" % outcomes([st, s2])))

    # P6 (owner-approved correction): the local workflows require the same verified software before installing
    def local_case(nm, why, kind, variant="signed_a", alter=None, after_prepare=None, expect=None, noise=False):
        """kind: rebuild (Update Using SFM's TXT, G3 TXT with G1 data) | import (Choose Another TXT File, custom G3 TXT
        over G1). expect None -> installed; else the refusal key, with nothing installed and the TXT unchanged."""
        if kind == "rebuild":
            cfg = make_install(nm, master="G3", gens=("g1",), software=variant or False)
            prep_args, confirm, want = ["prepare-rebuild"], SHA["G3"], ("G3", "g3")
        else:
            cfg = make_install(nm, software=variant or False)
            prep_args, confirm, want = ["prepare-import", "--source", G3_TXT], SHA["G1"], ("G3", "g3")
        u = os.path.dirname(cfg)
        if variant == "":
            install_software(u, signed=None)
        if alter:
            alter(u)
        if noise:
            mutable_noise(u)
        pr = run_op(nm, "prep", prep_args, cfg)
        if after_prepare:
            after_prepare(u)
        act0 = active_set(tree(cfg))
        master_sha = sha_file(os.path.join(cfg, "sfm_defaultanimationgroups.txt"))
        args_ = ["install", "--prepared", pr.get("prepid", ""), "--confirm-sha", pr.get("confirm_sha", "")]
        if kind == "import":
            args_ += ["--accept-replacement", "--backup-txt"]  # exactly as the GUI's Replace Groups
        st = run_op(nm, "install", args_, cfg)
        steps = [pr, st]
        if expect is None:
            fin, d = final_is(cfg, want)
            ok_ = (pr["outcome"] == "PREPARED" and st["outcome"] == "COMPLETE" and fin
                   and (st.get("software") or {}).get("files") == 31
                   and (kind != "import" or list((backups(cfg) or {}).values()) == [SHA["G1"]]))
        else:
            ok_ = (pr["outcome"] == "PREPARED" and st["outcome"] == "REFUSED" and st.get("message") == MESSAGES_[expect]
                   and active_set(tree(cfg)) == act0 and not txdirs(cfg) and backups(cfg) is None
                   and sha_file(os.path.join(cfg, "sfm_defaultanimationgroups.txt")) == master_sha)
        R.append(finalize_case(nm, cfg, steps, "PASS" if ok_ else "FAIL", why if ok_ else "unexpected %s %s %s" % (
            outcomes(steps), st.get("message"), st.get("details"))))

    for kind, label in (("rebuild", "Update Using SFM's TXT"), ("import", "Choose Another TXT File (custom TXT)")):
        k = kind[0]
        local_case("P6%s1_%s_verified_installs" % (k, kind), "%s on verified software: prepared and installed, software "
                   "re-verified at install" % label, kind)
        local_case("P6%s2_%s_unverified_refused" % (k, kind), "%s with no software inventory: compiled and validated "
                   "(preparation allowed), installation refused SOFTWARE_UNVERIFIED; nothing installed; TXT unchanged"
                   % label, kind, variant="", expect="SOFTWARE_UNVERIFIED")
        local_case("P6%s3_%s_modified_refused" % (k, kind), "%s with a modified CPM program file: installation refused "
                   "SOFTWARE_MODIFIED; nothing installed; TXT unchanged" % label, kind, alter=change_cpm,
                   expect="SOFTWARE_MODIFIED")
        local_case("P6%s4_%s_changed_after_prepare" % (k, kind), "%s: software modified between preparation and "
                   "installation -> refused SOFTWARE_MODIFIED at install" % label, kind, after_prepare=change_cpm,
                   expect="SOFTWARE_MODIFIED")
        local_case("P6%s5_%s_unsupported_profile_refused" % (k, kind), "%s with a validly signed inventory naming an "
                   "unimplemented profile -> refused SOFTWARE_UNSUPPORTED" % label, kind, variant="v_profile9",
                   expect="SOFTWARE_UNSUPPORTED")
        local_case("P6%s6_%s_mutable_data_ignored" % (k, kind), "%s: presets, logs and bytecode added (and a custom TXT) "
                   "do not invalidate the inventory; installed" % label, kind, noise=True)

    # P6r recovery of an already-started transaction is not gated by the software check
    nm = "P6r_recovery_not_gated"
    cfg = make_install(nm, master="G3", gens=("g1",))
    st = activate(nm, "interrupt", cfg, "rebuild", SHA["G3"], stop_at="act_moved_forward_0", action="kill")
    change_cpm(os.path.dirname(cfg))
    rec = recover(nm, "recover", cfg)
    fin, d = final_is(cfg, ("G3", "g3"))
    st2 = status(nm, "status", cfg)
    v = (st["killed"] and rec["outcome"] == "OK" and fin and st2.get("recovery_needed") is False)
    R.append(finalize_case(nm, cfg, [st, rec, st2], "PASS" if v else "FAIL",
                           "install interrupted mid-transaction, then a program file changed: recovery still runs and "
                           "completes the exact set (not gated by the software check)" if v else "unexpected %s" % (
                               outcomes([st, rec, st2]))))

    # ---------------- packaged application (clean directory) ----------------
    src_bundle = A.bundle
    if not src_bundle or not os.path.isdir(src_bundle):
        R.append(finalize_case("P7_packaged_bundle_present", None, [], "FAIL", "no --bundle given"))
        return R
    if not os.path.exists(frozen_bundle()):
        guard(frozen_bundle())
        shutil.copytree(src_bundle, frozen_bundle())
    clean = frozen_bundle()

    # P7 runtime closure from a clean directory (no development Python on PATH; PYTHONPATH/PYTHONHOME ignored)
    nm = "P7_runtime_closure_clean_directory"
    cfg = make_install(nm)
    rc = frozen_worker(nm, "runtime", ["runtime-check"], cfg)
    rc2 = frozen_worker(nm, "runtime_hostile_env", ["runtime-check"], cfg, extra_env={
        "PYTHONPATH": os.path.join(REPO, "tools") + os.pathsep + UPDATER, "PYTHONHOME": os.path.dirname(PY3),
        "PATH": os.pathsep.join([os.path.dirname(PY3), frozen_env()["PATH"]])})
    def closure_ok(r):
        ch = r.get("checks") or {}
        return (r.get("outcome") == "RUNTIME_OK" and r.get("frozen") is True and r.get("version") == PRODUCT_VERSION()
                and under_dir(r.get("executable", ""), clean)
                and all(under_dir(p, clean) for p in r.get("sys_path", []) if p)
                and all(p == "<frozen>" or under_dir(p, clean) for p in r.get("module_origins", []))
                and under_dir(ch["pinned_dependencies"]["deps_root"], clean)
                and ch["ed25519"]["rfc8032_test1_verifies"] and ch["ed25519"]["rejects_altered_message"]
                and under_dir(ch["ed25519"]["location"], clean)
                and ch["tls"]["ca_certificates"] > 0 and ch["tls"]["ok"] and ch["profile_matches_pins"]["ok"])
    v = closure_ok(rc) and closure_ok(rc2)
    R.append(finalize_case(nm, cfg, [rc, rc2], "PASS" if v else "FAIL",
                           "packaged worker from a clean copy: frozen 0.1.0; every sys.path entry and loaded module from "
                           "the bundle (also with PYTHONPATH/PYTHONHOME/PATH pointing at the development Python); pinned "
                           "sources verified in the bundle; Ed25519 RFC 8032 vector; TLS trust store loaded" if v else
                           "unexpected %s / %s" % (rc.get("outcome"), rc.get("checks"))))

    # P8 canonical compiler parity and determinism with the packaged dependencies
    nm = "P8_packaged_compiler_parity"
    cfg = make_install(nm, master="G3", gens=("g1",))
    a1 = frozen_worker(nm, "prep_rebuild_1", ["prepare-rebuild"], cfg)
    a2 = frozen_worker(nm, "prep_rebuild_2", ["prepare-rebuild"], cfg)
    cfg2 = make_install(nm + "_g1", master="G3", gens=("g3",), manifest="g3")
    a3 = frozen_worker(nm, "prep_import_g1", ["prepare-import", "--source", G1_TXT], cfg2)

    def staged(cfg_, r):
        d_ = os.path.join(cfg_, "sfm_character_tools_updater", "staging", r.get("prepid", "x"))
        c = r.get("candidate") or {}
        return (sha_file(os.path.join(d_, c.get("sidecar", "x"))) if os.path.exists(os.path.join(d_, c.get("sidecar", "x")))
                else None, sha_file(os.path.join(d_, "manifest.json")) if os.path.exists(os.path.join(d_, "manifest.json"))
                else None)
    s1_, s2_, s3_ = staged(cfg, a1), staged(cfg, a2), staged(cfg2, a3)
    v = (a1.get("outcome") == a2.get("outcome") == a3.get("outcome") == "PREPARED"
         and s1_ == s2_ == (GEN["g3"]["sidecar_sha"], GEN["g3"]["manifest_sha"])
         and s3_ == (GEN["g1"]["sidecar_sha"], GEN["g1"]["manifest_sha"]))
    R.append(finalize_case(nm, cfg, [a1, a2, a3], "PASS" if v else "FAIL",
                           "packaged compile of G3 (twice) and G1 reproduces the reference sidecars and manifests "
                           "byte-for-byte (G1 = live bcd97641/d810d648)" if v else "unexpected %s %s %s" % (s1_, s2_, s3_)))

    # P9 the three workflows through the packaged (shipping) worker, real process query
    nm = "P9_packaged_workflows"
    real0 = PSTAT()
    cfg = make_install(nm, master="G3", gens=("g1",))
    w = [frozen_worker(nm, "prep_rebuild", ["prepare-rebuild"], cfg)]
    w.append(frozen_worker(nm, "install_rebuild", ["install", "--prepared", w[0].get("prepid", ""), "--confirm-sha",
                                                   w[0].get("confirm_sha", "")], cfg))
    ok_r, d = final_is(cfg, ("G3", "g3"))
    cfg2 = make_install(nm + "_import")
    w.append(frozen_worker(nm, "prep_import", ["prepare-import", "--source", G3_TXT], cfg2))
    w.append(frozen_worker(nm, "install_import", ["install", "--prepared", w[2].get("prepid", ""), "--confirm-sha",
                                                  w[2].get("confirm_sha", ""), "--accept-replacement", "--backup-txt"],
                           cfg2))
    ok_i, d = final_is(cfg2, ("G3", "g3"))
    bk = (w[3].get("user_backup") or {})
    cfg3 = make_install(nm + "_official")
    before3 = tree(cfg3, include_staging=True)
    w.append(frozen_worker(nm, "prep_official", ["prepare-official", "--package", pkgdir("G3_s5")], cfg3))
    w.append(frozen_worker(nm, "check_official", ["check-official"], cfg3))
    real1 = PSTAT()
    if real0[0] == real1[0] == "CLEAR":
        ok_r0, d = final_is(cfg, ("G3", "g1"))
        ok_i0, d = final_is(cfg2, ("G1", "g1"))
        v = (w[0].get("outcome") == "PREPARED" and w[1].get("outcome") == "REFUSED"
             and w[1].get("message") == MESSAGES_["SOFTWARE_UNVERIFIED"] and ok_r0 and not txdirs(cfg)
             and w[2].get("outcome") == "PREPARED" and w[3].get("outcome") == "REFUSED"
             and w[3].get("message") == MESSAGES_["SOFTWARE_UNVERIFIED"] and ok_i0 and not txdirs(cfg2)
             and not bk and backups(cfg2) is None
             and w[4].get("outcome") == "REFUSED" and w[4].get("message") == MESSAGES_["PACKAGE_UNTRUSTED"]
             and tree(cfg3, include_staging=True) == before3 and w[5].get("outcome") in ("NONE_PUBLISHED",))
        why = ("packaged shipping worker (real query CLEAR; the product trusts no test key): Update Using SFM's TXT and "
               "Choose Another TXT File compile and prepare, then refuse installation because the test-signed software "
               "inventory cannot be verified (nothing changed, no backup made); Get Published Version refuses a "
               "test-signed package as unsigned and reads the real release list over TLS -> NONE_PUBLISHED")
    else:
        v, why = False, "real process status not CLEAR (%s/%s): inconclusive" % (real0[0], real1[0])
    R.append(finalize_case(nm, cfg, w, "PASS" if v else "FAIL", why if v else "%s %s" % (
        why, [(x.get("outcome"), x.get("message")) for x in w])))

    # P10 the packaged worker exposes no test option
    nm = "P10_packaged_worker_rejects_test_options"
    cfg = make_install(nm)
    rcs = []
    for opt in (["--trust-key", "00" * 32], ["--inject", "process=clear"], ["--hold-at", "x"], ["--net-base", "http://x"],
                ["--stop-at", "locked"], ["--scratch-root", RUN]):
        out = os.path.join(WORK, "results", "ops", "%s__%s.json" % (nm, opt[0].strip("-")))
        guard(out)
        cp = subprocess.run([os.path.join(clean, "sct-updater-worker.exe"), "status", "--installation", cfg, "--result",
                             out] + opt, capture_output=True, text=True, env=frozen_env(), timeout=120,
                            creationflags=0x08000000)
        rcs.append((opt[0], cp.returncode, os.path.exists(out)))
    v = all(rc_ == 2 and not ex for o, rc_, ex in rcs)
    R.append(finalize_case(nm, cfg, [{"rcs": rcs}], "PASS" if v else "FAIL",
                           "packaged worker rejects --trust-key, --inject, --hold-at, --net-base, --stop-at and "
                           "--scratch-root (usage error, no result)" if v else "unexpected %s" % rcs))

    # P11 packaged GUI from the clean directory: window, worker in a Job Object, idle close, no orphan
    nm = "P11_packaged_gui_clean_launch"
    cfg = make_install(nm)
    sfm = os.path.dirname(os.path.dirname(os.path.dirname(cfg)))
    before = tree(cfg, include_staging=True)
    import ctypes
    import ctypes.wintypes as wt
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    k32.OpenProcess.restype = wt.HANDLE
    p = subprocess.Popen([os.path.join(clean, "SFM Control Group Updater.exe"), "--sfm-folder", sfm], env=frozen_env(),
                         cwd=os.path.join(WORK, "clean_cwd"))
    seen_workers, in_job, titles = set(), [], set()
    t0 = time.time()
    while time.time() - t0 < 60:
        out = subprocess.run(["wmic", "process", "where", "ParentProcessId=%d" % p.pid, "get", "ProcessId,Name",
                              "/format:csv"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.strip().split(",")
            if len(parts) == 3 and parts[1].lower() == "sct-updater-worker.exe" and parts[2].isdigit():
                wpid = int(parts[2])
                if wpid not in seen_workers:
                    seen_workers.add(wpid)
                    h = k32.OpenProcess(0x1000, False, wpid)
                    flag = wt.BOOL()
                    if h and k32.IsProcessInJob(h, None, ctypes.byref(flag)):
                        in_job.append(bool(flag.value))
                    if h:
                        k32.CloseHandle(h)

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(hwnd, lp):
            pid_ = wt.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_))
            if pid_.value == p.pid and u32.IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(256)
                u32.GetWindowTextW(hwnd, buf, 256)
                titles.add(buf.value)
            return True
        u32.EnumWindows(cb, 0)
        if "SFM Control Group Updater" in titles and seen_workers and time.time() - t0 > 8:
            break
        time.sleep(0.05)
    subprocess.run(["taskkill", "/PID", str(p.pid)], capture_output=True)
    try:
        p.wait(20)
        exited = True
    except subprocess.TimeoutExpired:
        p.kill()
        exited = False
    orphans = [w_ for w_ in seen_workers if alive(w_)]
    v = ("SFM Control Group Updater" in titles and seen_workers and in_job and all(in_job) and exited and not orphans
         and tree(cfg, include_staging=True) == before)
    R.append(finalize_case(nm, cfg, [{"titles": sorted(titles), "workers": sorted(seen_workers), "in_job": in_job,
                                      "exited": exited, "exit_code": p.returncode, "orphans": orphans}],
                           "PASS" if v else "FAIL",
                           "packaged GUI from the clean copy (--sfm-folder scratch): window 'SFM Control Group Updater'; "
                           "its packaged worker ran inside a Job Object; WM_CLOSE when idle exits; no orphan worker; "
                           "installation unchanged (read-only status)" if v else
                           "unexpected titles=%s workers=%s in_job=%s exited=%s orphans=%s" % (
                               titles, seen_workers, in_job, exited, orphans)))

    # P12 bundle contents and identity
    nm = "P12_bundle_contents"
    man = json.load(open(A.bundle_manifest, encoding="utf-8")) if A.bundle_manifest else {}
    files = {f["path"]: f["sha256"] for f in man.get("files", [])}
    actual = {}
    for dp, dn, fn in os.walk(clean):
        for n in fn:
            actual[os.path.relpath(os.path.join(dp, n), clean).replace("\\", "/")] = sha_file(os.path.join(dp, n))
    forbidden = [f_ for f_ in actual if any(x in "/" + f_.lower() for x in (
        "test_worker", "fake_github", "net_audit", "gui_driver", "run_l1", "make_official_package",
        "make_software_inventory", ".pem", "/tests/"))]
    deps = {f_: h for f_, h in actual.items() if f_.startswith("_internal/sct_deps/")}
    v = (files == actual and not forbidden and len(deps) == 9 and set(deps.values()) == set(candidate.PINS.values())
         and man.get("version") == PRODUCT_VERSION() and not man.get("workstation_path_markers_found_in"))
    R.append(finalize_case(nm, None, [{"files": len(actual), "identity": man.get("bundle_identity_sha256"),
                                       "forbidden": forbidden}], "PASS" if v else "FAIL",
                           "clean copy equals the build manifest (%d files, identity %s); 9 pinned sources exactly; no "
                           "test or development material; no workstation path markers" % (
                               len(actual), (man.get("bundle_identity_sha256") or "")[:12]) if v else
                           "unexpected forbidden=%s deps=%d same=%s" % (forbidden, len(deps), files == actual)))
    return R


GROUPS = {"A": group_A, "B": group_B, "C": group_C, "D": group_D, "E": group_E, "F": group_F, "G": group_G,
          "H": group_H, "I": group_I, "J": group_J, "K": group_K, "N": group_N, "X": group_X, "W": group_W,
          "M": group_M, "O": group_O, "W3": group_W3, "Q": group_Q, "W4": group_W4, "U": group_U, "P": group_P}


def main():
    global A, RUN, ART, WORK, NOPYC, ENV, G1_TXT, G2_TXT, G3_TXT
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("setup", "groups"))
    ap.add_argument("--run", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--py27", required=True)
    ap.add_argument("--p1-preservation")
    ap.add_argument("--g3-source")
    ap.add_argument("--label")
    ap.add_argument("--groups")
    ap.add_argument("--outside-target")
    ap.add_argument("--bundle", help="L-5: the built one-folder application to copy into a clean directory")
    ap.add_argument("--bundle-manifest", help="L-5: the build's bundle_manifest.json")
    ap.add_argument("--process-default", default="clear",
                    help="process form injected into every test operation that does not set one ('' = real query)")
    A = ap.parse_args()
    RUN = os.path.abspath(A.run)
    ART = os.path.join(RUN, "artifacts")
    NOPYC = os.path.join(RUN, "nopyc")
    G1_TXT, G2_TXT, G3_TXT = (os.path.join(ART, t + "_source.txt") for t in ("g1", "g2", "g3"))
    if under(RUN, A.game) or under(RUN, REPO):
        raise SystemExit("STOP: run directory inside the game or repository tree")
    ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TEMP=os.path.join(RUN, "tmp"), TMP=os.path.join(RUN, "tmp"))
    if A.mode == "setup":
        setup()
        for d in ("tmp", "nopyc"):
            wmkdirs(os.path.join(RUN, d))
        wcopy(os.path.join(SUPPORT, "py27_select.py"), os.path.join(RUN, "py27lib", "py27_select.py"))
        return
    WORK = os.path.join(RUN, A.label)
    sys.path.insert(0, UPDATER)
    from sfm_character_tools_updater.process_gate import process_status
    global PSTAT
    PSTAT = process_status
    st0 = process_status()
    if st0[0] != "CLEAR" and not A.process_default:
        raise SystemExit("STOP: real process status %s (%s) before the run" % st0)
    print("PROCESS real status at start: %s (%s); default injected: %r" % (st0[0], st0[1], A.process_default))
    wmkdirs(WORK)
    load_generations()
    statuses = []
    for g in A.groups.split(","):
        before = process_status()
        R = GROUPS[g]()
        statuses.append({"group": g, "before": before, "after": process_status()})
        print("PROCESS %s before=%s after=%s" % (g, before[0], statuses[-1]["after"][0]))
        sys.stdout.flush()
        out = os.path.join(WORK, "results", "matrix_%s.json" % g)
        guard(out)
        with open(out, "x", encoding="utf-8") as f:
            json.dump(R, f, indent=1)
    out = os.path.join(WORK, "results", "process_status_by_group.json")
    guard(out)
    with open(out, "x", encoding="utf-8") as f:
        json.dump(statuses, f, indent=1)


if __name__ == "__main__":
    main()
