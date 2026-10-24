# -*- coding: utf-8 -*-
"""Evidence-based recovery of interrupted transactions (R2 C12), ported from P1/C1
p1proto_c1.py. Recovery uses the same protected no-clobber move primitive and journal as
installation; it is gated by the same A3 process check and installation lock.

Terminal transactions are verified, never mutated. A transaction with an unknown schema
(including the U0A/P1 experimental schemas) is refused without mutation.
"""
import json
import os

from . import hooks, w32
from . import journal as jr
from .backend import (TERMINAL, acquire_lock, allowed_auth_names, auth_inventory, describe_divergence,
                      execute, expected_states, make_plan, match_state, observe_slots, verify_correspondence,
                      verify_final)
from .layout import LEGACY_LOCK
from .legacy_lock import LEGACY_HANDLE, hold_legacy_lock
from .messages import MESSAGES, Stop
from .process_gate import gate

SCHEMA = jr.SCHEMA


def barrier(name):
    hooks.barrier(name)


def original_intact(obs, states):
    """E_0 holds for every slot except the transaction's own candidate files. Before PROTECTED no active
    file can have moved, but the candidates may be absent or incomplete (interrupted while being written);
    they are never installed from an unprotected transaction, so only the original state is verified."""
    return match_state(obs, [{s: w for s, w in states[0].items() if s[0] != "candidate"}]) == [0]


def recover(layout, policy):
    if policy not in ("resume", "rollback"):
        raise Stop("REFUSED", "NOTHING", reason="unknown recovery policy", policy=policy)
    res = {"operation": "recover", "policy": policy, "transactions": []}
    res["process_status"] = gate("recovery")
    if not os.path.isdir(layout.txroot):
        res["outcome"] = "NOTHING_TO_RECOVER"
        res["message"] = "There is nothing to recover."
        return res
    lock = acquire_lock(layout)
    try:
        for txid in sorted(os.listdir(layout.txroot)):
            res["transactions"].append(recover_one(layout, txid, policy))
        outs = [t["outcome"] for t in res["transactions"]]
        res["outcome"] = "NOTHING_TO_RECOVER" if not outs else (
            "CONFLICT" if "CONFLICT" in outs else (
                "STOPPED" if "STOPPED" in outs else ("REFUSED" if "REFUSED" in outs else "OK")))
    finally:
        w32.close(lock)
    # C12: say whether working authority was restored or only the exact (possibly stale)
    # previous files. Checked after the lock and every handle were released.
    if res["outcome"] in ("OK", "NOTHING_TO_RECOVER") and os.path.isdir(layout.auth):
        corr = verify_correspondence(layout)
        res["correspondence"] = corr
        res["installed_state"] = "WORKING" if corr["ok"] else "NEEDS_REBUILD"
        changed = [t for t in res["transactions"] if t["outcome"] in ("COMPLETE", "ROLLED_BACK", "ABANDONED")]
        if changed:
            res["message"] = MESSAGES["RECOVERED" if corr["ok"] else "NEEDS_REBUILD"]
        else:
            res["message"] = "There is nothing to recover." + (
                "" if corr["ok"] else " The installed data needs rebuilding.")
    else:
        res["message"] = "Recovery did not finish; see the details. No files were overwritten."
    return res


def recover_one(layout, txid, policy):
    r = {"txid": txid}
    held = []
    journal = None
    try:
        td = layout.txdir(txid)
        try:
            intent = json.loads(open(os.path.join(td, "intent.json"), "rb").read().decode("utf-8"))
        except Exception as e:
            raise Stop("CONFLICT", "UNKNOWN_SCHEMA", reason="intent unreadable", error=str(e))
        if not isinstance(intent, dict) or intent.get("schema") != SCHEMA or intent.get("txid") != txid:
            raise Stop("CONFLICT", "UNKNOWN_SCHEMA", reason="unknown transaction schema")
        jpath = os.path.join(td, "journal")
        if w32.attrs(jpath) == w32.INVALID_FILE_ATTRIBUTES:
            # Interrupted between intent and journal creation: nothing can have moved.
            moves = make_plan(intent)
            states = expected_states(intent, moves)
            obs = observe_slots(layout, txid, sorted(states[0].keys()))
            if not original_intact(obs, states):
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="journal missing and state not original")
            journal = jr.Journal(jpath, create=True)
            journal.append({"t": "INTENT", "schema": SCHEMA, "txid": txid, "by": "recovery"})
            journal.append({"t": "ABANDONED", "reason": "journal missing; original state verified"})
            r.update(outcome="ABANDONED", message=MESSAGES["NOTHING"])
            return r
        journal = jr.Journal(jpath, create=False)
        recs = journal.records
        types = [x.get("t") for x in recs]
        moves = make_plan(intent)
        states = expected_states(intent, moves)
        slots = sorted(states[0].keys())
        obs = observe_slots(layout, txid, slots)
        hits = match_state(obs, states)
        r["observed_k"] = hits
        r["journal_tail"] = types[-4:]
        dirs = [x["dir"] for x in recs if x.get("t") == "DIR"]
        names = set(auth_inventory(layout))
        extra = sorted(names - allowed_auth_names(intent))
        last = types[-1] if types else None
        protected = "PROTECTED" in types
        if last in TERMINAL:
            # Terminal: verify only, never mutate (journal text is not trusted alone).
            want_k = {"COMPLETE": len(moves), "ROLLED_BACK": 0}.get(last)
            r["terminal"] = last
            if last == "ABANDONED" and not protected:
                r["verified"] = original_intact(obs, states) and not extra
            else:
                r["verified"] = (want_k is not None and want_k in hits and not extra)
            r.update(outcome="TERMINAL", message="Transaction already %s; verified=%s; no files changed."
                     % (last, r["verified"]))
            return r
        if extra:
            journal.append({"t": "CONFLICT", "reason": "unfamiliar authority content", "names": extra})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="unfamiliar authority content", names=extra)
        if not protected and not hits and original_intact(obs, states):
            journal.append({"t": "ABANDONED", "reason": "recovered before protection; candidate files incomplete"})
            r.update(outcome="ABANDONED", message=MESSAGES["NOTHING"])
            return r
        if len(hits) != 1:
            div = describe_divergence(obs, states)
            key = "FOLDER_CHANGED"
            master_slot = [d for d in div if d["slot"] == "master/"]
            if master_slot and master_slot[0]["observed"] is not None:
                key = "TXT_CHANGED"
            elif any(d["observed"] is None for d in div):
                key = "MISSING"
            journal.append({"t": "CONFLICT", "reason": "disk state matches no recorded transition",
                            "divergence": div})
            raise Stop("CONFLICT", key, reason="disk state matches no recorded transition",
                       divergence=div)
        k = hits[0]
        # Journal/disk consistency: the disk may be at most one move ahead of the last DONE.
        if not protected:
            if k != 0:
                journal.append({"t": "CONFLICT", "reason": "files moved without protection record"})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="files moved without protection record")
            journal.append({"t": "ABANDONED", "reason": "recovered before protection"})
            r.update(outcome="ABANDONED", message=MESSAGES["NOTHING"])
            return r
        direction = dirs[-1] if dirs else "forward"
        # Replay the journal: DONE records give the last certain k; an unmatched BEGIN
        # means the disk may legitimately be one move further (rename done, DONE not written).
        jk, pending = 0, None
        for x in recs:
            if x.get("t") == "BEGIN":
                pending = (x["dir"], x["i"])
            elif x.get("t") == "DONE":
                jk = x["i"] + 1 if x["dir"] == "forward" else x["i"]
                pending = None
            elif x.get("t") == "RECONCILED":
                # an earlier recovery verified this exact disk state before acting
                jk = x["k"]
                pending = None
        allowed = {jk}
        if pending is not None:
            allowed.add(pending[1] + 1 if pending[0] == "forward" else pending[1])
        consistent = k in allowed
        r["journal_allowed_k"] = sorted(allowed)
        r["journal_k"] = jk
        if not consistent:
            journal.append({"t": "CONFLICT", "reason": "journal and disk disagree", "disk_k": k})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="journal and disk disagree", disk_k=k,
                       journal_k=jk)
        if direction == "forward" and policy == "rollback":
            direction = "rollback"
        # Protect every file that will still move, plus the retained master (rebuild).
        master_handle = None
        if intent["kind"] == "rebuild":
            h, err = w32.create_file(layout.master, w32.GENERIC_READ, 0, w32.OPEN_EXISTING)
            if h is None:
                raise Stop("REFUSED", "NOTHING", reason="cannot protect master", error=w32.ename(err))
            held.append(h)
            master_handle = h
        handles = {}
        for m in moves:
            loc = m["dst"] if m["i"] < k else m["src"]
            p = layout.slot(txid, loc[0], loc[1])
            h, err = w32.create_file(p, w32.GENERIC_READ | w32.DELETE, 0, w32.OPEN_EXISTING)
            if h is None:
                raise Stop("REFUSED", "NOTHING", reason="cannot protect file", role=m["role"],
                           error=w32.ename(err))
            held.append(h)
            s, _ = w32.sha_handle(h)
            if s != m["sha256"] or w32.std_info(h)["links"] != 1:
                journal.append({"t": "CONFLICT", "reason": "file changed before protection", "role": m["role"]})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="file changed before protection",
                           role=m["role"])
            handles[m["i"]] = h
        if master_handle is not None:
            s, _ = w32.sha_handle(master_handle)
            if s != intent["old"]["master"]["sha256"]:
                journal.append({"t": "CONFLICT", "reason": "master changed"})
                raise Stop("CONFLICT", "TXT_CHANGED", reason="master changed")
        if sorted(set(auth_inventory(layout)) - allowed_auth_names(intent)):
            journal.append({"t": "CONFLICT", "reason": "unfamiliar authority content"})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="unfamiliar authority content")
        ll = intent["old"].get("legacy_lock")
        if ll:
            lpath = os.path.join(layout.auth, LEGACY_LOCK)
            if not os.path.lexists(lpath):
                journal.append({"t": "CONFLICT", "reason": "legacy publisher.lock missing"})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason="legacy publisher.lock missing")
            lh, why = hold_legacy_lock(lpath, ll)
            if lh is None:
                if "active" in why:
                    raise Stop("REFUSED", "NOTHING", reason=why)
                journal.append({"t": "CONFLICT", "reason": why})
                raise Stop("CONFLICT", "FOLDER_CHANGED", reason=why)
            held.append(lh)
        barrier("rec_protected")
        journal.append({"t": "RECONCILED", "k": k, "dir": direction})
        if not dirs or dirs[-1] != direction:
            journal.append({"t": "DIR", "dir": direction, "reason": "recovery policy=%s" % policy})
        kk, failure = execute(layout, txid, moves, handles, journal, direction, k, "rec")
        if failure:
            journal.append({"t": "CONFLICT", "reason": "recovery move failed", "failure": failure})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="recovery move failed", failure=failure)
        final_k = len(moves) if direction == "forward" else 0
        problems = verify_final(layout, txid, intent, moves, states, final_k, handles, master_handle)
        if problems:
            journal.append({"t": "CONFLICT", "reason": "recovery verification failed", "problems": problems})
            raise Stop("CONFLICT", "FOLDER_CHANGED", reason="recovery verification failed",
                       problems=problems)
        if direction == "forward":
            journal.append({"t": "VERIFIED"})
            journal.append({"t": "COMPLETE", "by": "recovery"})
            r.update(outcome="COMPLETE", message=MESSAGES["RECOVERED"], from_k=k)
        else:
            journal.append({"t": "ROLLED_BACK", "by": "recovery"})
            r.update(outcome="ROLLED_BACK", message=MESSAGES["RESTORED"], from_k=k)
        return r
    except Stop as e:
        r.update(outcome=e.outcome, message=MESSAGES[e.message_key], details=e.details)
        return r
    except hooks.BarrierAbort as e:
        r.update(outcome="STOPPED", message=MESSAGES["RECOVERY_STOPPED"], details={"barrier": str(e)})
        return r
    finally:
        for h in held:
            w32.close(h)
        LEGACY_HANDLE[0] = None
        if journal is not None:
            journal.close()
