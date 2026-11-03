# -*- coding: utf-8 -*-
"""M-06 W2: evaluate two native probes for the prerequisites (offline; read-only).

usage: python -I compare_probes.py PROBE_BEFORE_RELOAD.json PROBE_AFTER_RELOAD.json

Reports, with explicit acceptance results:
  identity   str(GetId()) is a content rendering, stable across two reads and the registered wrapper, and distinct
             between elements; IsUniqueIdValid/IsUniqueIdEqual/GetElementId/GetElement are available, return bool
             where expected and agree.
  reload     whether the W1 selection token of the configured selected instance, captured before a same-session
             reopen of the same document, is invalidated. Both probes must be complete v2 probes with every token
             component readable (document key, the current shot's file id, shot key, the target animation set's key,
             its game model's key, model and checksum); an unreadable component is never proof of invalidation. The
             token is invalidated when the document file id or any (type, handle, id) key of the document, shot,
             selected animation set or its game model differs, while the model and checksum (the same document)
             agree. Peers are not part of the token: a peer-only change is not invalidation. Identical components
             mean the token survives the reload (acceptance fails: a finding for Astra).
  presence   HasAttribute()/GetAttribute() agreement for the optional channel attributes: every combination must be
             has=True/attribute or has=False/(AttributeError or None); anything else is a disagreement. Coverage
             must be complete and nonempty: every recorded attribute observed on every examined control (more than
             zero), with no animation set whose controls were unreadable.
Exit 0 only when every acceptance check passes.
"""
from __future__ import print_function

import io
import json
import sys


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def identity_checks(p):
    problems = []
    for name, ok in sorted(p["api"].items()):
        if not ok:
            problems.append("API %s unavailable" % name)
    texts = []
    for row in p["identities"]:
        a, b = row["str_twice"]
        if a is None or a != b or a.startswith("'<") or " at 0x" in a.lower():
            problems.append("%s: GetId rendering unstable or pointer-like (%r, %r)" % (row["role"], a, b))
        if row.get("registered_str") not in (None, a):
            problems.append("%s: registered wrapper renders differently (%r)" % (row["role"], row.get("registered_str")))
        for k in ("valid", "equal_to_registered"):
            r = row.get(k)
            if r is not None and not (r["ok"] and r["type"] == "bool" and r["repr"] == "True"):
                problems.append("%s: %s returned %r" % (row["role"], k, r))
        if row.get("get_element_same_handle") is False:
            problems.append("%s: GetElement(handle) does not return the element" % row["role"])
        texts.append(a)
    if len(set(texts)) != len(texts):
        problems.append("two elements render the same id text")
    d = p.get("distinct_elements_equal")
    if d is not None and not (d["ok"] and d["type"] == "bool" and d["repr"] == "False"):
        problems.append("IsUniqueIdEqual of two distinct elements returned %r" % (d,))
    return problems


PROBE_FORMAT = "M06W2-native-probe-v2"
TOKEN = ("document_key", "document_file_id", "shot_key", "animset_key", "gm_key", "model", "checksum")
KEYED = ("document_key", "shot_key", "animset_key", "gm_key")


def presence_checks(p):
    problems = []
    attrs, examined = p.get("channel_attrs"), p.get("controls_examined")
    if not isinstance(attrs, list) or not attrs or not isinstance(examined, int) or isinstance(examined, bool) or \
            examined <= 0:
        return ["presence coverage is empty or unrecorded (attributes %r, controls examined %r)" % (attrs, examined)]
    if p.get("controls_unreadable"):
        problems.append("controls of %d animation set(s) were unreadable" % len(p["controls_unreadable"]))
    totals = dict((a, 0) for a in attrs)
    for key, count in sorted(p["has_get_agreement"].items()):
        attr, has, get = key.split("|")
        ok = (has == "has=True(bool)" and get == "get=attribute") or \
            (has == "has=False(bool)" and get in ("get=AttributeError", "get=None"))
        if not ok:
            problems.append("%s: %s / %s on %d control(s)" % (attr, has, get, count))
        if attr not in totals:
            problems.append("%s: not a recorded attribute" % attr)
        else:
            totals[attr] += count
    for attr, n in sorted(totals.items()):
        if n != examined:
            problems.append("%s: observed on %d of %d examined controls (incomplete coverage)" % (attr, n, examined))
    return problems


def token_problems(p, label):
    """A probe's selected-instance token must be complete and readable; unreadable is insufficient, not changed."""
    if p.get("format") != PROBE_FORMAT:
        return ["%s: probe format %r" % (label, p.get("format"))]
    t = p.get("selected_token")
    if not isinstance(t, dict):
        return ["%s: no selected-instance token recorded" % label]
    problems = []
    for k in TOKEN:
        rec = t.get(k)
        if not isinstance(rec, dict) or rec.get("s") != "present" or "v" not in rec:
            problems.append("%s: token component %s unreadable or missing (%s)" % (
                label, k, (rec or {}).get("e") if isinstance(rec, dict) else rec))
        elif k in KEYED and not (isinstance(rec["v"], dict) and all(rec["v"].get(x) not in (None, "")
                                                                     for x in ("type", "handle", "id"))):
            problems.append("%s: token component %s is not a (type, handle, id) key" % (label, k))
    if t.get("complete") is not True:
        problems.append("%s: the probe marked its token incomplete" % label)
    return problems


def reload_result(before, after):
    """(changed components, problems). Problems make the reload undecidable (acceptance FAIL)."""
    problems = token_problems(before, "before") + token_problems(after, "after")
    if problems:
        return [], problems
    tb, ta = before["selected_token"], after["selected_token"]
    if tb.get("target_animset") != ta.get("target_animset") or \
            before.get("config_sha256") != after.get("config_sha256"):
        return [], ["the probes were taken for different selected instances or configurations"]
    for k in ("model", "checksum"):
        if tb[k]["v"] != ta[k]["v"]:
            problems.append("selected instance %s differs: not the same document reopened" % k)
    if tb["animset_key"]["v"].get("name") != ta["animset_key"]["v"].get("name"):
        problems.append("selected animation set name differs: not the same instance")
    if problems:
        return [], problems
    changed = []
    if tb["document_file_id"]["v"] != ta["document_file_id"]["v"]:
        changed.append("document_file_id")
    for k in KEYED:
        vb, va = tb[k]["v"], ta[k]["v"]
        if (vb["type"], vb["handle"], vb["id"]) != (va["type"], va["handle"], va["id"]):
            changed.append(k)
    return changed, []


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    before, after = load(argv[1]), load(argv[2])
    failures = []
    for label, p in (("before", before), ("after", after)):
        for x in identity_checks(p):
            failures.append("identity (%s): %s" % (label, x))
        for x in presence_checks(p):
            failures.append("presence (%s): %s" % (label, x))
    changed, problems = reload_result(before, after)
    for x in problems:
        failures.append("reload: %s" % x)
    if not problems:
        print("reload: %s" % ("selected-instance token INVALIDATED by " + ", ".join(changed) if changed
                              else "selected-instance token NOT invalidated (every component identical)"))
        if not changed:
            failures.append("reload: every selected-instance token component survived the same-session reopen")
    for f in failures:
        print("FAIL " + f)
    print("PROBE ACCEPTANCE: %s" % ("PASS" if not failures else "FAIL"))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
