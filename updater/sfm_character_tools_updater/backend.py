# -*- coding: utf-8 -*-
"""The one protected installed-publication backend (R2 C3-C9, Amendment §2.1).

prepare_rebuild() / prepare_import() / prepare_official(): build and validate the candidate in
updater-private staging (Rebuild My Data, Use Another TXT, Get Official Data). Writes nothing to the Master
path or the authority directory, so it may run while SFM runs.

install(): process gate -> (transaction, candidates, snapshots) -> installation lock ->
transaction records -> process gate -> protection -> revalidation through held handles ->
journaled no-clobber moves -> final verification through held handles -> release ->
TXT/SIDECAR correspondence verification -> post-install process-status recheck.

The activation body is ported from the qualified P1/C1 prototype (p1proto_c1.py
8871f137...). The C6-C8 move order, own-handle no-clobber rename, protection through final
verification and the verified-no-op branch are unchanged; differences are recorded in the
L-1 equivalence table.
"""
import json
import os
import uuid

from . import PREP_SCHEMA, hooks, official, w32
from . import candidate as cand
from . import journal as jr
from .layout import LEGACY_LOCK, SIDECAR_RE, TXID_RE
from .legacy_lock import LEGACY_HANDLE, classify_legacy_lock, hold_legacy_lock
from .messages import MESSAGES, Stop
from .process_gate import gate, process_status
from .compat import inventory as software

sha = cand.sha
SCHEMA = jr.SCHEMA
TERMINAL = jr.TERMINAL
KINDS = ("rebuild", "replace")


def barrier(name):
    hooks.barrier(name)


# ---------------------------------------------------------------- observation
def observe_path(path):
    """Path-based reader with full sharing (conflicts with nothing but an exclusive owner)."""
    a = w32.attrs(path)
    if a == w32.INVALID_FILE_ATTRIBUTES:
        return None
    if a & w32.FILE_ATTRIBUTE_REPARSE_POINT:
        return {"reparse": True}
    ident = w32.path_identity(path)
    if ident is None:
        return {"unreadable": True}
    return {"sha256": ident["sha256"], "file_id": ident["file_id"], "links": ident["info"]["links"]}


def auth_inventory(layout):
    return sorted(os.listdir(layout.auth))


def acquire_lock(layout):
    """C4: CreateFileW(GENERIC_READ|GENERIC_WRITE, share 0, OPEN_ALWAYS), non-inheritable."""
    h, err = w32.create_file(layout.lock, w32.GENERIC_READ | w32.GENERIC_WRITE, 0,
                             w32.OPEN_ALWAYS, inherit=False)
    if h is None:
        raise Stop("REFUSED", "NOTHING", reason="installation lock not acquired",
                   error=w32.ename(err))
    return h


def noop_transaction_gate(layout):
    """R2 C4 on the verified-no-op path, with the lock held: every transaction entry is
    checked. Unfamiliar entries and unknown schemas refuse; any transaction that is not
    terminal refuses with "run recovery" -- the no-op neither reconciles it in place nor
    reports NOOP over it. Nothing here opens an authority file or mutates anything."""
    seen = []
    for other in sorted(os.listdir(layout.txroot)):
        if not TXID_RE.match(other):
            w32.trace_event("transaction_record", entry=other, decision="REFUSE", why="unfamiliar entry")
            raise Stop("REFUSED", "FOLDER_CHANGED", reason="unfamiliar transaction entry", entry=other)
        schema = jr.intent_schema(layout, other)
        st = jr.transaction_status(layout, other)
        rec = {"txid": other, "intent_schema": schema, "status": st}
        if schema != SCHEMA or st == "MALFORMED":
            w32.trace_event("transaction_record", decision="REFUSE", why="unknown or malformed schema", **rec)
            raise Stop("REFUSED", "UNKNOWN_SCHEMA", reason="unknown transaction schema", **rec)
        if st not in TERMINAL:
            w32.trace_event("transaction_record", decision="REFUSE", why="unresolved transaction", **rec)
            raise Stop("REFUSED", "NOTHING", reason="another transaction must be reconciled first; run recovery",
                       **rec)
        w32.trace_event("transaction_record", decision="TERMINAL_OK", **rec)
        seen.append(rec)
    return seen


# ---------------------------------------------------------------- plan
def make_plan(intent):
    """Deterministic move list derived from the intent's hashes and validated names."""
    old, new, kind = intent["old"], intent["new"], intent["kind"]
    moves = []
    for s in old["sidecars"]:
        moves.append({"role": "S0", "src": ("auth", s["name"]), "dst": ("retired", s["name"]),
                      "sha256": s["sha256"]})
    if old["manifest"] is not None:
        moves.append({"role": "P0", "src": ("auth", "manifest.json"),
                      "dst": ("retired", "manifest.json"), "sha256": old["manifest"]["sha256"]})
    if kind == "replace":
        moves.append({"role": "M0", "src": ("master", ""), "dst": ("retired", "master.txt"),
                      "sha256": old["master"]["sha256"]})
        moves.append({"role": "M1", "src": ("candidate", "master.txt"), "dst": ("master", ""),
                      "sha256": new["master_sha256"]})
    moves.append({"role": "S1", "src": ("candidate", new["sidecar"]),
                  "dst": ("auth", new["sidecar"]), "sha256": new["sidecar_sha256"]})
    moves.append({"role": "P1", "src": ("candidate", "manifest.json"),
                  "dst": ("auth", "manifest.json"), "sha256": new["manifest_sha256"]})
    for i, m in enumerate(moves):
        m["i"] = i
    return moves


def expected_states(intent, moves):
    """E_k for k = 0..n: slot -> sha (None = vacant) after the first k moves."""
    state = {}
    for m in moves:
        state.setdefault(tuple(m["src"]), None)
        state.setdefault(tuple(m["dst"]), None)
    # Build E_0: a slot's initial content is the sha of the first move that reads from it,
    # unless an earlier move writes it first.
    e0 = dict(state)
    touched = set()
    for m in moves:
        s, d = tuple(m["src"]), tuple(m["dst"])
        if s not in touched:
            e0[s] = m["sha256"]
        touched.add(s)
        touched.add(d)
    if intent["kind"] == "rebuild":
        e0[("master", "")] = intent["old"]["master"]["sha256"]
    states = [dict(e0)]
    cur = dict(e0)
    for m in moves:
        cur = dict(cur)
        cur[tuple(m["src"])] = None
        cur[tuple(m["dst"])] = m["sha256"]
        states.append(cur)
    return states


def observe_slots(layout, txid, slots):
    obs = {}
    for s in slots:
        o = observe_path(layout.slot(txid, s[0], s[1]))
        obs[s] = o
    return obs


def match_state(obs, states):
    """Returns list of k whose expected state matches observation exactly (by sha256)."""
    hits = []
    for k, st in enumerate(states):
        good = True
        for slot, want in st.items():
            o = obs.get(slot)
            have = None if o is None else o.get("sha256", "!unusable")
            if have != want:
                good = False
                break
        if good:
            hits.append(k)
    return hits


def describe_divergence(obs, states):
    """Mismatching slots against the nearest expected state (fewest mismatches)."""
    best = None
    for k, st in enumerate(states):
        mm = []
        for slot, want in st.items():
            o = obs.get(slot)
            have = None if o is None else o.get("sha256", "!unusable")
            if have != want:
                mm.append({"slot": "/".join(slot), "observed": have, "expected": want, "nearest_k": k})
        if best is None or len(mm) < len(best):
            best = mm
    return best


def allowed_auth_names(intent):
    names = {s["name"] for s in intent["old"]["sidecars"]}
    names.add(intent["new"]["sidecar"])
    names.add("manifest.json")
    if intent["old"].get("legacy_lock"):
        names.add(LEGACY_LOCK)
    return names


# ---------------------------------------------------------------- move executor
def norm_final(p):
    if p is None:
        return None
    if p.startswith("\\\\?\\"):
        p = p[4:]
    return os.path.normcase(os.path.abspath(p))


def execute(layout, txid, moves, handles, journal, direction, start_k, prefix):
    """Forward: performs moves start_k..n-1. Rollback: undoes moves start_k-1..0.
    Every move: journal BEGIN -> no-clobber handle rename -> journal DONE.
    Returns (k_reached, failure or None)."""
    order = range(start_k, len(moves)) if direction == "forward" else range(start_k - 1, -1, -1)
    k = start_k
    for i in order:
        m = moves[i]
        src, dst = (m["src"], m["dst"]) if direction == "forward" else (m["dst"], m["src"])
        dest = layout.slot(txid, dst[0], dst[1])
        journal.append({"t": "BEGIN", "dir": direction, "i": i, "role": m["role"]})
        barrier("%s_begin_%s_%d" % (prefix, direction, i))
        ok, err = w32.rename_by_handle(handles[i], dest, replace_if_exists=False)
        barrier("%s_moved_%s_%d" % (prefix, direction, i))
        if not ok:
            journal.append({"t": "FAILED", "dir": direction, "i": i, "error": w32.ename(err)})
            return k, {"i": i, "role": m["role"], "dest": dest, "error": w32.ename(err)}
        if norm_final(w32.final_path(handles[i])) != norm_final(dest):
            journal.append({"t": "FAILED", "dir": direction, "i": i, "error": "final path mismatch"})
            return k, {"i": i, "role": m["role"], "error": "final path mismatch"}
        journal.append({"t": "DONE", "dir": direction, "i": i, "role": m["role"]})
        barrier("%s_done_%s_%d" % (prefix, direction, i))
        k = i + 1 if direction == "forward" else i
    return k, None


def verify_final(layout, txid, intent, moves, states, k, handles, master_handle):
    """Through held handles (bytes + location) and an independent directory listing."""
    problems = []
    for m in moves:
        h = handles.get(m["i"])
        s, _ = w32.sha_handle(h)
        if s != m["sha256"]:
            problems.append({"role": m["role"], "problem": "hash via handle", "sha": s})
        loc = m["dst"] if k == len(moves) else m["src"]
        want = layout.slot(txid, loc[0], loc[1])
        if norm_final(w32.final_path(h)) != norm_final(want):
            problems.append({"role": m["role"], "problem": "location", "have": w32.final_path(h)})
    if master_handle is not None:
        s, _ = w32.sha_handle(master_handle)
        if s != intent["old"]["master"]["sha256"]:
            problems.append({"role": "M(retained)", "problem": "hash via handle", "sha": s})
    names = auth_inventory(layout)
    st = states[k]
    want_names = [n for (kind, n), v in st.items() if kind == "auth" and v is not None]
    if intent["old"].get("legacy_lock"):
        want_names.append(LEGACY_LOCK)
        lh = LEGACY_HANDLE[0]
        if lh is None or w32.file_id(lh) != intent["old"]["legacy_lock"]["file_id"] \
                or w32.sha_handle(lh)[0] != intent["old"]["legacy_lock"]["sha256"]:
            problems.append({"problem": "legacy publisher.lock identity changed"})
    want_names = sorted(want_names)
    if names != want_names:
        problems.append({"problem": "authority inventory", "have": names, "want": want_names})
    return problems


# ---------------------------------------------------------------- preparation
MAX_SOURCE_BYTES = official.MAX_SOURCE_BYTES
WORKFLOWS = ("rebuild", "import", "official")


def read_source(path, key_unreadable="SOURCE_UNREADABLE"):
    """Exact bytes of a TXT, bounded before reading. Never writes to the file."""
    try:
        st = os.stat(path)
    except (OSError, TypeError, ValueError) as e:
        raise Stop("REFUSED", key_unreadable, reason="source unreadable", error=type(e).__name__)
    a = w32.attrs(path)
    if a == w32.INVALID_FILE_ATTRIBUTES or a & (w32.FILE_ATTRIBUTE_DIRECTORY | w32.FILE_ATTRIBUTE_REPARSE_POINT):
        raise Stop("REFUSED", key_unreadable, reason="source is not a regular file")
    if st.st_size > MAX_SOURCE_BYTES:
        raise Stop("REFUSED", "SOURCE_TOO_LARGE", reason="source larger than allowed", size=st.st_size,
                   limit=MAX_SOURCE_BYTES)
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_SOURCE_BYTES + 1)
    except OSError as e:
        raise Stop("REFUSED", key_unreadable, reason="source unreadable",
                   error="%s winerror=%s" % (type(e).__name__, getattr(e, "winerror", None)))
    if len(data) > MAX_SOURCE_BYTES:
        raise Stop("REFUSED", "SOURCE_TOO_LARGE", reason="source larger than allowed", limit=MAX_SOURCE_BYTES)
    return data


def _compile(txt, label, invalid_key):
    try:
        return cand.compile_real(txt, label)
    except Stop as e:
        if e.message_key == "NOTHING":
            raise Stop("REFUSED", invalid_key, **e.details)
        raise


def _preview_master(layout):
    m0 = observe_path(layout.master)
    if m0 is None or "sha256" not in m0:
        raise Stop("REFUSED", "MISSING", reason="active master missing or unusable", observed=m0)
    return m0


def _stage(layout, files, check):
    """Write the staged files (CREATE_NEW, checked, flushed) into a new staging directory, then
    run `check(sdir)`, which returns None or the failure text."""
    layout.ensure_updater_dirs()
    prepid = uuid.uuid4().hex
    sdir = layout.prepdir(prepid)
    os.mkdir(sdir)
    for n, data in files:
        ok, err = w32.write_new_file(os.path.join(sdir, n), data)
        if not ok:
            raise Stop("REFUSED", "NOTHING", reason="staging write failed", error=w32.ename(err))
    bad = check(sdir)
    if bad:
        raise Stop("REFUSED", "NOTHING", reason="staged candidate failed validation from disk", error=bad)
    return prepid, sdir


def _finish(sdir, record, res, message):
    ok, err = w32.write_new_file(os.path.join(sdir, "prepared.json"),
                                 json.dumps(record, sort_keys=True, indent=1).encode("utf-8"))
    if not ok:
        raise Stop("REFUSED", "NOTHING", reason="staging write failed", error=w32.ename(err))
    st = res["process_status"][0]
    if st != "CLEAR":
        message = "%s %s" % (message, MESSAGES["SFM_OPEN_NOTE"])
    res.update(prepid=record["prepid"], confirm_sha=record["destination"]["master_sha256"],
               workflow=record["workflow"], kind=record["kind"], candidate=record["candidate"],
               source=record["source"], destination=record["destination"],
               consent_required=record["consent_required"], outcome="PREPARED", message=message)
    if "official" in record:
        res["official"] = record["official"]
    return res


def _start(workflow):
    res = {"operation": "prepare", "workflow": workflow}
    st, why = process_status()  # advisory only: preparation may run while SFM runs
    res["process_status"] = [st, why]
    return res


def prepare_rebuild(layout):
    """Rebuild My Data: the installed Master's exact bytes (never rewritten) compiled into staging."""
    res = _start("rebuild")
    txt = read_source(layout.master, "MISSING")
    name, body, manifest, outcome = _compile(txt, "active", "REBUILD_INVALID")
    layout.require_path_budget(name)
    m0 = _preview_master(layout)
    if m0["sha256"] != sha(txt):
        raise Stop("REFUSED", "PREPARE_AGAIN", reason="active master changed while preparing")
    prepid, sdir = _stage(layout, [(name, body), ("manifest.json", manifest)],
                          lambda d: cand.validate_candidate_files(outcome, name, os.path.join(d, name),
                                                                  os.path.join(d, "manifest.json")))
    record = {"schema": PREP_SCHEMA, "prepid": prepid, "workflow": "rebuild", "kind": "rebuild",
              "source": {"sha256": sha(txt), "bytes": len(txt), "label": "current TXT"},
              "candidate": {"sidecar": name, "sidecar_sha256": sha(body), "manifest_sha256": sha(manifest)},
              "destination": {"master_sha256": m0["sha256"]}, "consent_required": False}
    return _finish(sdir, record, res, MESSAGES["PREPARED"])


def prepare_import(layout, source):
    """Use Another TXT: an immutable captured copy of the chosen file (the file is only read),
    compiled and validated into staging, previewed against the observed destination."""
    res = _start("import")
    src_path = os.path.abspath(source)
    txt = read_source(src_path)
    name, body, manifest, outcome = _compile(txt, "import", "SOURCE_INVALID")
    layout.require_path_budget(name)
    m0 = _preview_master(layout)
    prepid, sdir = _stage(layout, [(name, body), ("manifest.json", manifest), ("master.txt", txt)],
                          lambda d: cand.validate_candidate_files(outcome, name, os.path.join(d, name),
                                                                  os.path.join(d, "manifest.json")))
    record = {"schema": PREP_SCHEMA, "prepid": prepid, "workflow": "import", "kind": "replace",
              "source": {"sha256": sha(txt), "bytes": len(txt), "label": "chosen TXT", "path": src_path},
              "candidate": {"sidecar": name, "sidecar_sha256": sha(body), "manifest_sha256": sha(manifest)},
              "destination": {"master_sha256": m0["sha256"]},
              "consent_required": sha(txt) != m0["sha256"]}
    return _finish(sdir, record, res, MESSAGES["PREPARED_IMPORT"] if record["consent_required"] else MESSAGES["PREPARED"])


def prepare_official(layout, package_dir, allow_older=False):
    """Get Official Data from a local package: authenticate, check compatibility and payload
    identities, verify the official sidecar against the official TXT, and remember the
    authenticated release sequence. The official sidecar is never combined with another TXT."""
    res = _start("official")
    d, desc_bytes, sig, payload = official.read_package(os.path.abspath(package_dir))
    # L-5 (R2 E2-E3): official data only for a verified, supported Character Tools installation.
    sw = software.verify_installation(layout, accepted_profiles=set(d["compatible_authority_profiles"]))
    desc_sha = sha(desc_bytes)
    txt, body, manifest = payload["master"], payload["sidecar"], payload["manifest"]
    name = d["files"]["sidecar"]["name"]
    outcome = _compile(txt, "official", "PACKAGE_DAMAGED")[3]
    bad = cand.validate_official_bytes(outcome, name, body, manifest)
    if bad:
        raise Stop("REFUSED", "PACKAGE_DAMAGED", reason="official sidecar does not correspond to the official TXT",
                   error=bad)
    layout.require_path_budget(name)
    m0 = _preview_master(layout)
    layout.ensure_updater_dirs()
    log = official.ReleaseLog(layout)
    try:
        seq = official.check_sequence(log, d, desc_sha, allow_older)
        recognized = m0["sha256"] in log.recognized_masters()
        kind = "rebuild" if m0["sha256"] == sha(txt) else "replace"
        prepid, sdir = _stage(layout, [(name, body), ("manifest.json", manifest), ("master.txt", txt),
                                       (official.DESCRIPTOR, desc_bytes), (official.SIGNATURE, sig)],
                              lambda dd: cand.validate_official_files(outcome, name, os.path.join(dd, name),
                                                                      os.path.join(dd, "manifest.json"), sha(body)))
        if not seq["already_seen"]:
            log.append({"sequence": d["sequence"], "descriptor_sha256": desc_sha, "master_sha256": sha(txt),
                        "data_version": d["data_version"], "signing_key_id": d["signing_key_id"],
                        "published_at": d["published_at"]})
    except Stop as e:
        if e.message_key == "NOTHING" and "validation" in str(e.details.get("reason", "")):
            raise Stop("REFUSED", "PACKAGE_DAMAGED", **e.details)
        raise
    finally:
        log.close()
    record = {"schema": PREP_SCHEMA, "prepid": prepid, "workflow": "official", "kind": kind,
              "source": {"sha256": sha(txt), "bytes": len(txt), "label": "official data %s" % d["data_version"]},
              "candidate": {"sidecar": name, "sidecar_sha256": sha(body), "manifest_sha256": sha(manifest)},
              "destination": {"master_sha256": m0["sha256"], "recognized_official": recognized},
              "consent_required": kind == "replace" and not recognized,
              "official": {"sequence": d["sequence"], "data_version": d["data_version"],
                           "release_tag": d["release_tag"], "descriptor_sha256": desc_sha,
                           "signing_key_id": d["signing_key_id"], "older_than_seen": seq["older"],
                           "high_water_before": seq["high_water_before"], "software": sw}}
    v = d["data_version"]
    msg = (MESSAGES["PREPARED_OFFICIAL_OLDER"] % v if seq["older"] else
           MESSAGES["PREPARED_OFFICIAL_REPLACES"] % v if record["consent_required"] else
           MESSAGES["PREPARED_OFFICIAL"] % v)
    return _finish(sdir, record, res, msg)


def load_prepared(layout, prepid):
    """The staged record and the exact bytes it names; any mismatch: prepare again. An official
    preparation is re-authenticated from its staged descriptor and signature."""
    sdir = layout.prepdir(prepid)
    try:
        rec = json.loads(open(os.path.join(sdir, "prepared.json"), "rb").read().decode("utf-8"))
        assert isinstance(rec, dict) and rec.get("schema") == PREP_SCHEMA and rec.get("prepid") == prepid
        assert rec.get("workflow") in WORKFLOWS and rec.get("kind") in KINDS
        assert (rec["workflow"], rec["kind"]) in (("rebuild", "rebuild"), ("import", "replace"),
                                                  ("official", "rebuild"), ("official", "replace"))
        assert isinstance(rec.get("consent_required"), bool)
        c = rec["candidate"]
        assert SIDECAR_RE.match(c["sidecar"])
        body = open(os.path.join(sdir, c["sidecar"]), "rb").read()
        manifest = open(os.path.join(sdir, "manifest.json"), "rb").read()
        assert sha(body) == c["sidecar_sha256"] and sha(manifest) == c["manifest_sha256"]
        txt = None
        if rec["workflow"] in ("import", "official"):
            txt = open(os.path.join(sdir, "master.txt"), "rb").read()
            assert sha(txt) == rec["source"]["sha256"] and len(txt) == rec["source"]["bytes"]
        if rec["workflow"] == "official":
            desc_bytes = open(os.path.join(sdir, official.DESCRIPTOR), "rb").read()
            sig = open(os.path.join(sdir, official.SIGNATURE), "rb").read()
    except Exception as e:
        raise Stop("REFUSED", "PREPARE_AGAIN", reason="prepared data missing or changed",
                   error="%s: %s" % (type(e).__name__, str(e)[:200]))
    if rec["workflow"] == "official":
        d = official.reverify_staged(desc_bytes, sig, {"master": txt, "manifest": manifest, "sidecar": body})
        rec["_accepted_profiles"] = list(d["compatible_authority_profiles"])
        if sha(desc_bytes) != rec["official"]["descriptor_sha256"] or d["files"]["sidecar"]["name"] != c["sidecar"]:
            raise Stop("REFUSED", "PREPARE_AGAIN", reason="prepared official record does not match its descriptor")
    return rec, body, manifest, txt


# ---------------------------------------------------------------- installation
def install(layout, prepid, confirm_sha, accept_replacement=False):
    """Amendment §2.1 steps 5-7. Returns the result dictionary."""
    res = {"operation": "install"}
    try:
        res["process_status"] = gate("pre-lock")
        rec, body, manifest, staged_txt = load_prepared(layout, prepid)
        kind = rec["kind"]
        res.update(kind=kind, workflow=rec["workflow"], prepid=prepid)
        if rec["workflow"] == "import":
            # C3: before confirmation takes effect, a changed selection requires a new preview.
            try:
                now = read_source(rec["source"]["path"], "SOURCE_CHANGED")
            except Stop as e:
                raise Stop("REFUSED", "SOURCE_CHANGED", **e.details)
            if sha(now) != rec["source"]["sha256"]:
                raise Stop("REFUSED", "SOURCE_CHANGED", reason="chosen TXT changed since preparation")
        # L-5 (owner-approved correction, 2026-10-18): installing data of any workflow requires a verified,
        # supported Character Tools installation, re-verified here even if preparation checked earlier.
        # A valid TXT establishes valid data, not that the installed software can consume it.
        res["software"] = software.verify_installation(
            layout, set(rec["_accepted_profiles"]) if rec["workflow"] == "official" else None)
        if rec["consent_required"] and not accept_replacement:
            raise Stop("REFUSED", "NEEDS_CONSENT", reason="replacement not confirmed")
        if kind == "rebuild":
            try:
                txt = open(layout.master, "rb").read()
            except OSError as e:
                raise Stop("REFUSED", "MISSING", reason="source unreadable",
                           error="%s winerror=%s" % (type(e).__name__, getattr(e, "winerror", None)))
            if sha(txt) != rec["source"]["sha256"]:
                raise Stop("REFUSED", "PREPARE_AGAIN", reason="active TXT changed since preparation")
        else:
            txt = staged_txt
        layout.require_path_budget(rec["candidate"]["sidecar"])
        layout.ensure_updater_dirs()
    except Stop as e:
        res.update(outcome=e.outcome, message=MESSAGES[e.message_key], details=e.details)
        return res
    res.update(_activate(layout, kind, txt, rec["candidate"]["sidecar"], body, manifest, confirm_sha,
                         hooks.candidate_write_error))
    # Step 7: everything below runs after every handle was released.
    if res.get("outcome") in ("COMPLETE", "NOOP"):
        corr = verify_correspondence(layout)
        res["correspondence"] = corr
        if not corr["ok"]:
            res.update(outcome="UNVERIFIED", message=MESSAGES["UNVERIFIED"])
        elif res["outcome"] == "COMPLETE":
            v = (rec.get("official") or {}).get("data_version")
            res["message"] = {"rebuild": MESSAGES["INSTALLED_REBUILD"], "import": MESSAGES["INSTALLED_IMPORT"],
                              "official": (MESSAGES["INSTALLED_OFFICIAL_REPLACED"] if kind == "replace"
                                           else MESSAGES["INSTALLED_OFFICIAL"]) % v if v else ""}[rec["workflow"]]
        st, why = process_status()
        res["post_install_process_status"] = [st, why]
        if res["outcome"] != "UNVERIFIED":
            if st == "CLEAR":
                res["message"] = "%s %s" % (res["message"], MESSAGES["REOPEN"])
            else:
                res["restart_required"] = True
                res["message"] = "%s %s" % (res["message"],
                                            MESSAGES["RESTART_RUNNING" if st == "RUNNING" else "RESTART_UNKNOWN"])
    return res


def _activate(layout, kind, txt, name, body, manifest, confirm_sha, inject_write_error):
    res = {"kind": kind}
    lock = None
    held = []
    journal = None
    txid = None
    try:
        res["candidate"] = {"master_sha256": sha(txt), "sidecar": name,
                            "sidecar_sha256": sha(body), "manifest_sha256": sha(manifest)}
        # Preview of the active state (path readers)
        m0 = observe_path(layout.master)
        if m0 is None or "sha256" not in m0:
            raise Stop("REFUSED", "MISSING", reason="active master missing or unusable", observed=m0)
        if m0["links"] != 1:
            raise Stop("REFUSED", "FOLDER_CHANGED", reason="master has hard links", links=m0["links"])
        inv = auth_inventory(layout)
        sidecars, manifest_old, unknown = [], None, []
        legacy_lock = None
        for n in inv:
            p = os.path.join(layout.auth, n)
            if n == LEGACY_LOCK:
                legacy_lock, why = classify_legacy_lock(p)
                if why:
                    raise Stop("REFUSED", "FOLDER_CHANGED" if "active" not in why else "NOTHING",
                               reason=why)
                continue
            o = observe_path(p)
            if SIDECAR_RE.match(n) and o and "sha256" in o and o["links"] == 1:
                sidecars.append({"name": n, "sha256": o["sha256"], "file_id": o["file_id"]})
            elif n == "manifest.json" and o and "sha256" in o and o["links"] == 1:
                manifest_old = {"sha256": o["sha256"], "file_id": o["file_id"]}
            else:
                unknown.append(n)
        if unknown:
            raise Stop("REFUSED", "FOLDER_CHANGED", reason="unfamiliar authority content",
                       unfamiliar=unknown)
        res["legacy_lock"] = legacy_lock
        dir_ids = {"cfg": w32.path_identity(layout.cfg, True)["file_id"],
                   "auth": w32.path_identity(layout.auth, True)["file_id"]}
        res["preview"] = {"master": m0, "sidecars": sidecars, "manifest": manifest_old,
                          "inventory": inv, "dirs": dir_ids}
        if kind == "rebuild" and confirm_sha != sha(txt):
            raise Stop("REFUSED", "PREPARE_AGAIN", reason="rebuild source changed since confirmation")
        if confirm_sha != m0["sha256"]:
            raise Stop("REFUSED", "DESTINATION_CHANGED", reason="destination generation changed; re-present decision",
                       observed=m0["sha256"], confirmed=confirm_sha)
        noop = (sha(txt) == m0["sha256"] and len(sidecars) == 1 and sidecars[0]["name"] == name
                and manifest_old is not None and manifest_old["sha256"] == sha(manifest))
        barrier("previewed")
        if noop:
            # C4 lock -> C4 transaction records -> C7.6/A3 process gate -> C7.7/C8
            # exclusive identity-bound verification. No authority handle before the gate.
            w32.trace_event("noop_branch_entered")
            lock = acquire_lock(layout)
            w32.trace_event("installation_lock_acquired")
            res["transactions_checked"] = noop_transaction_gate(layout)
            res["process_status"] = gate("post-lock")
            verification = []
            for role, p, want, fid in (
                    ("master", layout.master, m0["sha256"], m0["file_id"]),
                    ("sidecar", os.path.join(layout.auth, name), sha(body), sidecars[0]["file_id"]),
                    ("manifest", os.path.join(layout.auth, "manifest.json"), sha(manifest),
                     manifest_old["file_id"])):
                h, err = w32.create_file(p, w32.GENERIC_READ, 0, w32.OPEN_EXISTING)
                if h is None:
                    w32.trace_event("noop_verify", role=role, decision="REFUSE", error=w32.ename(err))
                    raise Stop("REFUSED", "NOTHING", reason="no-op verification open failed",
                               role=role, path=p, error=w32.ename(err))
                held.append(h)
                s, _ = w32.sha_handle(h)
                got = {"role": role, "sha256": s, "file_id": w32.file_id(h),
                       "links": w32.std_info(h)["links"]}
                verification.append(got)
                if s != want or got["file_id"] != fid or got["links"] != 1:
                    w32.trace_event("noop_verify", role=role, decision="REFUSE")
                    raise Stop("REFUSED", "NOTHING", reason="no-op verification identity mismatch",
                               role=role, observed=got, expected={"sha256": want, "file_id": fid})
                w32.trace_event("noop_verify", role=role, decision="MATCH")
            want_inv = [name, "manifest.json"] + ([LEGACY_LOCK] if legacy_lock else [])
            if auth_inventory(layout) != sorted(want_inv):
                w32.trace_event("noop_inventory", decision="REFUSE")
                raise Stop("REFUSED", "NOTHING", reason="no-op inventory changed")
            w32.trace_event("noop_inventory", decision="MATCH")
            res["noop_verification"] = verification
            res.update(outcome="NOOP", message=MESSAGES["NOOP"])
            w32.trace_event("result", outcome="NOOP")
            return res

        # C7.3: transaction directory, intent, journal, candidates (outside the active directory)
        txid = uuid.uuid4().hex
        res["txid"] = txid
        td = layout.txdir(txid)
        for d in (td, os.path.join(td, "candidate"), os.path.join(td, "snapshot"),
                  os.path.join(td, "retired")):
            os.mkdir(d)
        intent = {"schema": SCHEMA, "txid": txid, "kind": kind,
                  "old": {"master": {"sha256": m0["sha256"], "file_id": m0["file_id"]},
                          "sidecars": sidecars, "manifest": manifest_old,
                          "legacy_lock": legacy_lock},
                  "new": {"master_sha256": sha(txt), "sidecar": name, "sidecar_sha256": sha(body),
                          "manifest_sha256": sha(manifest)},
                  "dirs": dir_ids}
        ok, err = w32.write_new_file(os.path.join(td, "intent.json"),
                                     json.dumps(intent, sort_keys=True, indent=1).encode("utf-8"))
        if not ok:
            raise Stop("ABANDONED", "NOTHING", reason="intent write failed", error=w32.ename(err))
        journal = jr.Journal(os.path.join(td, "journal"), create=True)
        journal.append({"t": "INTENT", "schema": SCHEMA, "txid": txid})
        cands = [("master.txt", txt)] if kind == "replace" else []
        cands += [(name, body), ("manifest.json", manifest)]
        for n, data in cands:
            ok, err = w32.write_new_file(layout.slot(txid, "candidate", n), data,
                                         inject_error=inject_write_error)
            if not ok:
                journal.append({"t": "ABANDONED", "reason": "candidate write failed",
                                "error": w32.ename(err)})
                raise Stop("ABANDONED", "NOTHING", reason="candidate write failed",
                           error=w32.ename(err))
        bad = cand.validate_staged_copy(name, layout.slot(txid, "candidate", name),
                                        layout.slot(txid, "candidate", "manifest.json"),
                                        sha(body), sha(txt), len(txt))
        if bad:
            journal.append({"t": "ABANDONED", "reason": "candidate failed validation from disk"})
            raise Stop("ABANDONED", "NOTHING", reason="candidate failed validation from disk", error=bad)
        if kind == "replace" and sha(open(layout.slot(txid, "candidate", "master.txt"), "rb").read()) != sha(txt):
            journal.append({"t": "ABANDONED", "reason": "candidate master bytes differ"})
            raise Stop("ABANDONED", "NOTHING", reason="candidate master bytes differ")
        barrier("candidates_written")
        # C7.4: verified snapshot copies of the pre-operation files
        snaps = [("master.txt", layout.master, m0["sha256"])]
        snaps += [(s["name"], os.path.join(layout.auth, s["name"]), s["sha256"]) for s in sidecars]
        if manifest_old:
            snaps.append(("manifest.json", os.path.join(layout.auth, "manifest.json"),
                          manifest_old["sha256"]))
        for n, p, want in snaps:
            try:
                data = open(p, "rb").read()
            except OSError as e:
                journal.append({"t": "ABANDONED", "reason": "source unreadable during snapshot"})
                raise Stop("ABANDONED", "NOTHING", reason="source unreadable during snapshot",
                           error="%s winerror=%s" % (type(e).__name__, getattr(e, "winerror", None)))
            if sha(data) != want:
                journal.append({"t": "ABANDONED", "reason": "source changed during snapshot"})
                raise Stop("ABANDONED", "NOTHING", reason="source changed during snapshot", path=p)
            ok, err = w32.write_new_file(layout.slot(txid, "snapshot", n), data)
            if not ok:
                journal.append({"t": "ABANDONED", "reason": "snapshot write failed",
                                "error": w32.ename(err)})
                raise Stop("ABANDONED", "NOTHING", reason="snapshot write failed", error=w32.ename(err))
        barrier("snapshots_written")
        # C7.5 confirmation was supplied (confirm_sha) and bound to M0 above.
        # C7.6: installation lock; other transactions; process gate
        try:
            lock = acquire_lock(layout)
        except Stop as e:
            journal.append({"t": "ABANDONED", "reason": e.details.get("reason"),
                            "error": e.details.get("error")})
            raise Stop("ABANDONED", "NOTHING", **e.details)
        barrier("locked")
        for other in sorted(os.listdir(layout.txroot)):
            if other == txid:
                continue
            if not TXID_RE.match(other):
                journal.append({"t": "ABANDONED", "reason": "unfamiliar transaction entry"})
                raise Stop("ABANDONED", "FOLDER_CHANGED", reason="unfamiliar transaction entry",
                           entry=other)
            st = jr.transaction_status(layout, other)
            if st not in TERMINAL:
                journal.append({"t": "ABANDONED", "reason": "other transaction needs reconciliation",
                                "other": other, "other_status": st})
                raise Stop("ABANDONED", "NOTHING", reason="another transaction must be reconciled first",
                           other=other, other_status=st)
        jdata, _ = w32.read_all_handle(journal.h)
        if jr.parse_journal(jdata)[0][-1].get("t") != "INTENT":
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="own journal changed by another process")
        res["process_status"] = gate("post-lock", journal)
        # C7.7: protected handles
        moves = make_plan(intent)
        states = expected_states(intent, moves)
        handles = {}
        master_handle = None

        def protect(path, access):
            h, err = w32.create_file(path, access, 0, w32.OPEN_EXISTING)
            if h is None:
                journal.append({"t": "ABANDONED", "reason": "protection failed",
                                "path_role": os.path.relpath(path, layout.cfg), "error": w32.ename(err)})
                raise Stop("ABANDONED", "NOTHING", reason="protection failed", path=path,
                           error=w32.ename(err))
            held.append(h)
            return h

        if kind == "rebuild":
            master_handle = protect(layout.master, w32.GENERIC_READ)
        if legacy_lock:
            lh, why = hold_legacy_lock(os.path.join(layout.auth, LEGACY_LOCK), legacy_lock)
            if lh is None:
                journal.append({"t": "ABANDONED", "reason": why})
                raise Stop("ABANDONED", "NOTHING", reason=why)
            held.append(lh)
        elif os.path.lexists(os.path.join(layout.auth, LEGACY_LOCK)):
            journal.append({"t": "ABANDONED", "reason": "publisher.lock appeared"})
            raise Stop("ABANDONED", "FOLDER_CHANGED", reason="publisher.lock appeared after preview")
        for m in moves:
            p = layout.slot(txid, m["src"][0], m["src"][1])
            handles[m["i"]] = protect(p, w32.GENERIC_READ | w32.DELETE)
        dir_pins = {}
        for key, p in (("cfg", layout.cfg), ("auth", layout.auth),
                       ("candidate", os.path.join(td, "candidate")),
                       ("retired", os.path.join(td, "retired"))):
            h, err = w32.open_dir(p)
            if h is None:
                journal.append({"t": "ABANDONED", "reason": "directory pin failed", "error": w32.ename(err)})
                raise Stop("ABANDONED", "NOTHING", reason="directory pin failed", dir=key,
                           error=w32.ename(err))
            held.append(h)
            dir_pins[key] = w32.file_id(h)
        barrier("protected")
        # C7.8: revalidate bytes and physical identities through the held handles
        mism = []
        if master_handle is not None:
            s, _ = w32.sha_handle(master_handle)
            if s != m0["sha256"] or w32.file_id(master_handle) != m0["file_id"]:
                mism.append("master")
        for m in moves:
            h = handles[m["i"]]
            s, _ = w32.sha_handle(h)
            info = w32.std_info(h)
            if s != m["sha256"] or info["links"] != 1:
                mism.append(m["role"])
            if m["role"] == "M0" and w32.file_id(h) != m0["file_id"]:
                mism.append("M0 identity")
            if m["role"] == "S0":
                want = [x for x in sidecars if x["name"] == m["src"][1]][0]["file_id"]
                if w32.file_id(h) != want:
                    mism.append("S0 identity")
            if m["role"] == "P0" and w32.file_id(h) != manifest_old["file_id"]:
                mism.append("P0 identity")
        if dir_pins["cfg"] != dir_ids["cfg"] or dir_pins["auth"] != dir_ids["auth"]:
            mism.append("directory identity")
        # C7.9: recheck the active-directory inventory
        if auth_inventory(layout) != inv:
            mism.append("authority inventory")
        if mism:
            journal.append({"t": "ABANDONED", "reason": "revalidation failed", "mismatch": mism})
            raise Stop("ABANDONED", "NOTHING", reason="revalidation through handles failed",
                       mismatch=mism)
        journal.append({"t": "PROTECTED"})
        journal.append({"t": "DIR", "dir": "forward"})
        res["plan"] = [{"i": m["i"], "role": m["role"], "src": "/".join(m["src"]),
                        "dst": "/".join(m["dst"])} for m in moves]
        k, failure = execute(layout, txid, moves, handles, journal, "forward", 0, "act")
        if failure:
            res["forward_failure"] = failure
            journal.append({"t": "DIR", "dir": "rollback", "reason": "forward move failed"})
            k, rfail = execute(layout, txid, moves, handles, journal, "rollback", k, "actrb")
            if rfail or k != 0:
                journal.append({"t": "CONFLICT", "reason": "rollback incomplete"})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="rollback incomplete",
                           rollback_failure=rfail, k=k)
            problems = verify_final(layout, txid, intent, moves, states, 0, handles, master_handle)
            if problems:
                journal.append({"t": "CONFLICT", "reason": "post-rollback verification failed"})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="post-rollback verification failed",
                           problems=problems)
            journal.append({"t": "ROLLED_BACK"})
            res.update(outcome="ROLLED_BACK", message=MESSAGES["NOTHING"])
            return res
        barrier("moves_done")
        problems = verify_final(layout, txid, intent, moves, states, len(moves), handles, master_handle)
        if problems:
            journal.append({"t": "CONFLICT", "reason": "final verification failed", "problems": problems})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="final verification failed",
                       problems=problems)
        journal.append({"t": "VERIFIED"})
        journal.append({"t": "COMPLETE"})
        barrier("complete")
        res.update(outcome="COMPLETE", message=MESSAGES["INSTALLED"])
        return res
    except Stop as e:
        res.update(outcome=e.outcome, message=MESSAGES[e.message_key], details=e.details)
        return res
    except hooks.BarrierAbort as e:
        res.update(outcome="STOPPED", message=MESSAGES["STOPPED"], details={"barrier": str(e)})
        return res
    finally:
        for h in held:
            w32.close(h)
        LEGACY_HANDLE[0] = None
        if journal is not None:
            journal.close()
        if lock is not None:
            w32.close(lock)


# ---------------------------------------------------------------- step 7 / status
def verify_correspondence(layout):
    """Amendment §2.1 step 7, by path after release: the effective Master, exactly one active
    sidecar bound to it (authority-bound reader open, FINAL R3-A2B admission), a manifest
    binding both, nothing unfamiliar in the authority directory, and the consumer path budget."""
    out = {"ok": False, "problems": []}
    P = out["problems"]
    try:
        txt = open(layout.master, "rb").read()
    except OSError as e:
        P.append("master unreadable: %s" % type(e).__name__)
        return out
    msha = sha(txt)
    out["master_sha256"] = msha
    try:
        names = auth_inventory(layout)
    except OSError as e:
        P.append("authority directory unreadable: %s" % type(e).__name__)
        return out
    sidecars = [n for n in names if SIDECAR_RE.match(n)]
    other = [n for n in names if n not in sidecars and n not in ("manifest.json", LEGACY_LOCK)]
    if other:
        P.append("unfamiliar authority content: %s" % other)
    if LEGACY_LOCK in names:
        ident, why = classify_legacy_lock(os.path.join(layout.auth, LEGACY_LOCK))
        if why:
            P.append(why)
    if len(sidecars) != 1:
        P.append("expected exactly one active sidecar, found %d" % len(sidecars))
        return out
    name = sidecars[0]
    out["sidecar"] = name
    sp = os.path.join(layout.auth, name)
    try:
        body = open(sp, "rb").read()
        if "sfm_master_0_%s.sfmsidecar" % sha(body) != name:
            P.append("sidecar name does not match its bytes")
        r = cand.deps()["reader"].SidecarReader.open_generation_path(sp, msha)
        r.close()
        cand.admit(sp, msha)
    except Stop:
        raise
    except Exception as e:
        P.append("sidecar does not bind the Master: %s: %s" % (type(e).__name__, str(e)[:200]))
    try:
        md = cand.deps()["manifest"].parse_manifest_bytes(open(os.path.join(layout.auth, "manifest.json"), "rb").read())
        if (md.generation_basename, md.sidecar_sha256, md.source_sha256, md.source_byte_length) != \
                (name, sha(body), msha, len(txt)):
            P.append("manifest does not bind the Master and sidecar")
    except Exception as e:
        P.append("manifest unusable: %s: %s" % (type(e).__name__, str(e)[:200]))
    over = layout.path_budget(name)
    if over:
        P.append("consumer path budget exceeded: %s" % over)
    out["ok"] = not P
    return out


def status(layout):
    """Read-only: nothing is created, locked exclusively or written."""
    res = {"operation": "status"}
    st, why = process_status()
    res["process_status"] = [st, why]
    m = observe_path(layout.master)
    res["master"] = m
    res["authority_inventory"] = auth_inventory(layout) if os.path.isdir(layout.auth) else None
    txs = []
    if os.path.isdir(layout.txroot):
        for t in sorted(os.listdir(layout.txroot)):
            if not TXID_RE.match(t):
                txs.append({"entry": t, "status": "UNFAMILIAR"})
                continue
            txs.append({"txid": t, "intent_schema": jr.intent_schema(layout, t),
                        "status": jr.transaction_status(layout, t, readonly=True)})
    res["transactions"] = txs
    res["recovery_needed"] = any(x.get("status") not in TERMINAL or x.get("intent_schema") != SCHEMA for x in txs)
    res["correspondence"] = verify_correspondence(layout) if m and "sha256" in m and res["authority_inventory"] is not None \
        else {"ok": False, "problems": ["master or authority directory missing"]}
    res["outcome"] = "STATUS"
    res["message"] = ("An interrupted update needs recovery. Close SFM, then recover the installation."
                      if res["recovery_needed"] else
                      ("Installed data is consistent." if res["correspondence"]["ok"]
                       else "Installed data needs rebuilding."))
    return res
