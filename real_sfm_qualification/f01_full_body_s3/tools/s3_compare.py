# -*- coding: utf-8 -*-
"""F-01 full-body S3: the offline comparator. Python 3, run with -I after restore (SFM closed). Read-only except for
its two verdict files. It is independent of CPM's code: it reads the native observations (the pinned S0 observer and
the S3 sidecars), the saved pose records, the CPM logs and the run's evidence files, and checks each Expected result
of PROCEDURE.md with the body registry's own tolerances.

usage: python -I s3_compare.py S3.json      (or: s3_tool.py S3.json compare)
Writes Q/evidence/S3_VERDICT.json and S3_VERDICT.md (exclusive create). Exit 0 only on "verdict": "PASS".
"""
from __future__ import print_function

import datetime
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_full_body_s0", "tools"))
import s0_analyze  # noqa: E402

LABELS = dict(("A%d" % i, "S0-%02d" % i) for i in range(1, 8))
LABELS.update(("B%d" % i, "S0-%02d" % (i + 7)) for i in range(1, 18))
POSE_A, POSE_B, LEGACY = u"S3 Pose A", u"S3 Pose B", u"NQ1 Pose A"
LEGACY_WRITTEN = ("Hand_l_p", "Hand_l_o", "Elbow_l_p")
VISIBLE_DEGREES = 5.0
REQUIRED_GROUPS = ("spine and hips", "neck and head", "arms", "legs", "tail", "ears", "fingers")
EPOCH = datetime.datetime(2000, 1, 1)
PERF = {"responsive_ms": 5000, "limit_ms": 30000}
LOG_RE = re.compile(r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.(\d{3})Z #(\d+) s=(\S+) w=(\S+) op=(\S+) \| (.*)$")


# --- math (the convention of the records: quaternions x, y, z, w) -------------------------------------------------

def unit(q):
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qrot(q, v):
    return qmul(qmul(q, list(v) + [0.0]), [-q[0], -q[1], -q[2], q[3]])[:3]


def compose(a, b):
    qa = unit(a[1])
    moved = qrot(qa, b[0])
    return [a[0][i] + moved[i] for i in range(3)], unit(qmul(qa, unit(b[1])))


def invert(a):
    q = unit(a[1])
    qi = [-q[0], -q[1], -q[2], q[3]]
    return [-c for c in qrot(qi, a[0])], qi


def angle(a, b):
    a, b = unit(a), unit(b)
    return math.degrees(2.0 * math.acos(min(1.0, abs(sum(a[i] * b[i] for i in range(4))))))


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


# --- loading ------------------------------------------------------------------------------------------------------

def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def groups_of(name):
    n = name.lower()
    if "twist" in n:
        return "twist"
    if n.startswith("bip_pelvis") or n.startswith("bip_spine"):
        return "spine and hips"
    if n in ("bip_neck", "bip_head"):
        return "neck and head"
    if any(n.startswith(s) for s in ("bip_collar", "bip_upperarm", "bip_lowerarm", "bip_hand", "lcarpal", "rcarpal")):
        return "arms"
    if any(n.startswith(s) for s in ("bip_hip_", "bip_knee", "bip_foot", "bip_toe")) or "toe_" in n:
        return "legs"
    if n.startswith("bip_tail"):
        return "tail"
    if n.startswith("ear_"):
        return "ears"
    if any(n.startswith("bip_" + s) for s in ("index", "middle", "ring", "pinky", "thumb")):
        return "fingers"
    if "hair" in n:
        return "hair"
    if "breast" in n or "butt" in n:
        return "body"
    return "other"


class Run(object):
    def __init__(self, c):
        self.c = c
        self.q = c["paths"]["Q"]
        self.checks = []
        self.ids = read_json(os.path.join(self.q, "staged", "IDENTITIES.json"))
        reg = read_json(os.path.join(self.q, "staged", "cpm_body_profiles_v1.json"))
        self.profile = list(reg["profiles"].values())[0] if isinstance(reg["profiles"], dict) else reg["profiles"][0]
        self.tol = self.profile["tolerances"]
        self.unposed = set(self.profile["preserved_fk_bones"]) | set(self.profile["passive_channel_bones"])
        self.obs, self.side = {}, {}
        for step, label in sorted(LABELS.items()):
            path = os.path.join(self.q, "observations", label + ".json")
            if os.path.isfile(path):
                self.obs[step] = read_json(path)
            side = os.path.join(self.q, "observations", label + ".s3.json")
            if os.path.isfile(side):
                self.side[step] = read_json(side)
        self.records = self.load_records()

    def check(self, cid, ok, detail=None):
        self.checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        return ok

    def load_records(self):
        out = {}
        for path in glob.glob(os.path.join(self.q, "evidence", "library_poses", self.c["character_dir"], "*.json")):
            r = read_json(path)
            out.setdefault(r.get("name"), []).append((path, r))
        return out

    def record(self, name):
        rows = self.records.get(name) or []
        return rows[0][1] if len(rows) == 1 else None

    # --- views of one observation ---------------------------------------------------------------------------------

    @staticmethod
    def channels(o):
        return dict((ch["id"]["name"], ch) for ch in o.get("channels") or [] if ch.get("id"))

    @staticmethod
    def sig(ch):
        return ([(l.get("key_count"), l.get("keys_sha256")) for l in ch.get("layers") or []],
                ch.get("value_at_mapped"))

    def placement(self, o):
        h = o["rig"]["handles"][self.profile["placement_handle"]]
        return h["world_position"], h["world_orientation"]

    def relative(self, o, bone):
        b = o["bones"][bone]
        return compose(invert(self.placement(o)), (b["world_position"], b["world_orientation"]))

    @staticmethod
    def doc_unchanged(o1, o2):
        """No write between two observations of one SFM process: the whole-document digest after the first equals the
        digest before the second, and the Undo/Redo state is the same."""
        return (o1["readonly"]["digest_after"]["sha256"] == o2["readonly"]["digest_before"]["sha256"] and
                o1["session_after"]["undo"] == o2["session_before"]["undo"])

    # --- comparisons ----------------------------------------------------------------------------------------------

    def oracle_problems(self, o, region):
        out = []
        oracle = region["oracle"]["bones"]
        for name in sorted(o["bones"]):
            if name not in oracle:
                out.append("%s missing from the oracle" % name)
                continue
            p, qq = self.relative(o, name)
            e = oracle[name]
            if dist(p, e["position"]) > self.tol["position"] or angle(qq, e["orientation"]) > self.tol["angle_degrees"]:
                out.append("%s %.4f/%.4f deg" % (name, dist(p, e["position"]), angle(qq, e["orientation"])))
        return out

    def applied_problems(self, o, base, region):
        """The posed bones at the record's placement-relative posture in this placement; preserved and passive bones
        keep their local transform; scales, the model and the placement handle unchanged."""
        out = []
        oracle = region["oracle"]["bones"]
        for name, b in sorted(o["bones"].items()):
            was = base["bones"][name]
            if b.get("scale") != was.get("scale"):
                out.append("bone %s scale" % name)
            if name in self.unposed:
                if dist(b["local_position"], was["local_position"]) > self.tol["position"] or \
                        angle(b["local_orientation"], was["local_orientation"]) > self.tol["angle_degrees"]:
                    out.append("preserved %s local" % name)
                continue
            p, qq = self.relative(o, name)
            e = oracle[name]
            if dist(p, e["position"]) > self.tol["position"] or angle(qq, e["orientation"]) > self.tol["angle_degrees"]:
                out.append("posed %s %.4f/%.4f deg" % (name, dist(p, e["position"]), angle(qq, e["orientation"])))
        for key in ("world_position", "world_orientation", "local_position", "local_orientation"):
            a, b = o["model"]["state"].get(key), base["model"]["state"].get(key)
            if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b) or                     (len(a) == 3 and dist(a, b) > self.tol["position"]) or                     (len(a) == 4 and angle(a, b) > self.tol["angle_degrees"]):
                out.append("model %s" % key)
        if o["model"]["state"].get("scale") != base["model"]["state"].get("scale"):
            out.append("model scale")
        pa, pb = self.placement(o), self.placement(base)
        if dist(pa[0], pb[0]) > self.tol["position"] or angle(pa[1], pb[1]) > self.tol["angle_degrees"]:
            out.append("placement handle moved")
        return out

    def skeleton_problems(self, o1, o2):
        out = []
        for name, b in sorted(o1["bones"].items()):
            c = o2["bones"][name]
            for kind in ("world", "local"):
                if dist(b[kind + "_position"], c[kind + "_position"]) > self.tol["position"] or \
                        angle(b[kind + "_orientation"], c[kind + "_orientation"]) > self.tol["angle_degrees"]:
                    out.append("%s %s" % (name, kind))
        return out

    def channel_problems(self, o1, o2, names=None, exclude=()):
        a, b = self.channels(o1), self.channels(o2)
        out = []
        for name in sorted(names if names is not None else set(a) | set(b)):
            if name in exclude:
                continue
            if name not in a or name not in b or self.sig(a[name]) != self.sig(b[name]):
                out.append(name)
        return out

    def control_problems(self, o1, o2, written):
        def rows(o):
            return dict((c["id"]["name"], c.get("attributes")) for c in o.get("controls") or [])
        a, b = rows(o1), rows(o2)
        return sorted(n for n in set(a) | set(b) if (n + "_p") not in written and (n + "_o") not in written and
                      a.get(n) != b.get(n))

    def written_problems(self, o, base, region, update):
        """Every written channel holds the record's value at the mapped tick: one key there (inserted, or updated in
        place), and no other key changed where the observer lists the keys."""
        out = []
        now, was = self.channels(o), self.channels(base)
        for name in sorted(set(region["positions"]) | set(region["orientations"])):
            if name not in now or name not in was:
                out.append("%s missing" % name)
                continue
            want = region["positions"].get(name) or region["orientations"][name]
            got = now[name].get("value_at_mapped")
            if not isinstance(got, list) or len(got) != len(want):
                out.append("%s value unreadable" % name)
                continue
            if (len(want) == 3 and max(abs(got[i] - want[i]) for i in range(3)) > 1e-6) or \
                    (len(want) == 4 and angle(got, want) > self.tol["effective_angle_degrees"]):
                out.append("%s value" % name)
            la, lb = now[name]["layers"], was[name]["layers"]
            if len(la) != len(lb) or not la:
                out.append("%s layers" % name)
                continue
            a, b = la[0], lb[0]
            if a.get("key_at_mapped") is None:
                out.append("%s no key at the mapped tick" % name)
            inserted = a["key_count"] == b["key_count"] + 1 and b.get("key_at_mapped") is None
            updated = a["key_count"] == b["key_count"] and b.get("key_at_mapped") is not None and \
                a.get("key_at_mapped") == b.get("key_at_mapped")
            if not (updated if update else (inserted or updated)):
                out.append("%s key structure (%s -> %s)" % (name, b["key_count"], a["key_count"]))
            if a.get("keys") is not None and b.get("keys") is not None:
                t = o["time"]["t_chan"]
                if [k for k in a["keys"] if k[0] != t] != [k for k in b["keys"] if k[0] != t]:
                    out.append("%s other keys changed" % name)
            if [(l["key_count"], l["keys_sha256"]) for l in la[1:]] != [(l["key_count"], l["keys_sha256"])
                                                                       for l in lb[1:]]:
                out.append("%s other layers changed" % name)
        return out

    def distinct_groups(self, region, o):
        """Per anatomical group, the largest local-orientation difference (degrees) between a record and a posture."""
        out = {}
        for name, e in region["oracle"]["bones"].items():
            if name in self.unposed or name not in o["bones"]:
                continue
            g = groups_of(name)
            d = angle(e["local_orientation"], o["bones"][name]["local_orientation"])
            out[g] = max(out.get(g, 0.0), d)
        return out

    def outside_equal(self, s1, s2):
        return s1 in self.side and s2 in self.side and \
            self.side[s1]["outside"]["sha256"] == self.side[s2]["outside"]["sha256"]


# --- the CPM log ----------------------------------------------------------------------------------------------------

def parse_logs(folder):
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "*.log"))):
        m = re.search(r"pid(\d+)", os.path.basename(path))
        pid = int(m.group(1)) if m else None
        with open(path, "rb") as f:
            for raw in f.read().decode("utf-8", "replace").splitlines():
                g = LOG_RE.match(raw)
                if not g:
                    continue
                y, mo, d, hh, mi, ss, ms = [int(x) for x in g.groups()[:7]]
                when = datetime.datetime(y, mo, d, hh, mi, ss, ms * 1000) - EPOCH
                stamp = int(round(when.total_seconds() * 1000))
                rows.append({"pid": pid, "ms": stamp, "seq": int(g.group(8)), "op": g.group(11), "text": g.group(12)})
    rows.sort(key=lambda r: (r["pid"], r["seq"]))
    return rows


def apply_operations(rows, pid):
    """The Apply Pose operations of one SFM process, in order: their log lines and the timing marks."""
    ops, current = [], None
    for r in rows:
        if r["pid"] != pid:
            continue
        m = re.match(r"PROD_OPERATION_BEGIN id=(\d+) kind=u?'([^']*)'", r["text"])
        if m:
            current = {"id": m.group(1), "kind": m.group(2), "lines": [], "begin": r["ms"]} \
                if m.group(2) == "Apply Pose" else None
            if current is not None:
                ops.append(current)
            continue
        if current is not None:
            current["lines"].append(r)
    for op in ops:
        for key, marks in (("p1", ("PROD_POSE_BODY-P1 ", "PROD_POSE_P1 ")), ("p6", ("PROD_POSE_BODY-P6 ", "PROD_POSE_P6 ")),
                           ("p7", ("PROD_POSE_BODY-P7-verified", "PROD_POSE_P7-verified")),
                           ("end", ("PROD_OPERATION_END ",))):
            hits = [r["ms"] for r in op["lines"] if any(r["text"].startswith(m) for m in marks)]
            op[key] = hits[0] if hits else None
        op["text"] = [r["text"] for r in op["lines"]]
    return ops


def has(op, prefix):
    return any(t.startswith(prefix) for t in op["text"])


def p1_detail(op):
    for t in op["text"]:
        if t.startswith("PROD_POSE_BODY-P1 ") or t.startswith("PROD_POSE_P1 "):
            try:
                return json.loads(t.split(" ", 1)[1])
            except ValueError:
                return None
    return None


def timing(op):
    def gap(a, b):
        return None if op.get(a) is None or op.get(b) is None else op[b] - op[a]
    return {"preflight_ms": gap("begin", "p1"), "transaction_ms": gap("p1", "p6"), "blocking_ms": gap("begin", "p6"),
            "deferred_verify_ms": gap("p6", "p7"), "whole_ms": gap("begin", "p7") if op.get("p7") else gap("begin", "end")}


# --- the verdict ----------------------------------------------------------------------------------------------------

def evaluate(R):
    o, chk = R.obs, R.check
    tol = R.tol
    for step in sorted(LABELS, key=lambda s: (s[0], int(s[1:]))):
        if not chk("observed.%s" % step, step in o and step in R.side, LABELS[step]):
            continue
        problems = s0_analyze.validate(o[step]) + list(o[step].get("problems") or []) + list(R.side[step]["mismatch"])
        chk("valid.%s" % step, not problems and o[step]["readonly"]["unchanged"], problems[:5])
        want = R.ids["qualification_cpm_sha256"]
        if step.startswith("A") and R.c.get("continuation"):      # Process A ran in the source run, on its build
            want = R.c["continuation"]["process_a_qualification_cpm_sha256"]
        chk("cpm.%s" % step, (o[step].get("cpm_loaded") or {}).get("build_sha256") == want, o[step].get("cpm_loaded"))
    if len(o) != len(LABELS):
        chk("complete", False, "missing observations: %s" % sorted(set(LABELS) - set(o)))
        return
    A = ["A%d" % i for i in range(1, 8)]
    B = ["B%d" % i for i in range(1, 18)]
    pa, pb = set(o[s]["pid"] for s in A), set(o[s]["pid"] for s in B)
    chk("process.restart_between_save_and_apply", len(pa) == 1 and len(pb) == 1 and pa != pb, (sorted(pa), sorted(pb)))
    chk("process.sessions", all(o[s]["document"].lower().endswith("s3_source.dmx") for s in A) and
        all(o[s]["document"].lower().endswith("s3_destination.dmx") for s in B),
        (o["A1"]["document"], o["B1"]["document"]))

    # Save, Update and the library
    rec_a, rec_b, legacy = R.record(POSE_A), R.record(POSE_B), R.record(LEGACY)
    chk("library.one_record_each", rec_a is not None and rec_b is not None and legacy is not None,
        dict((k, len(v)) for k, v in R.records.items()))
    if rec_a is None or rec_b is None:
        return
    reg_a, reg_b = rec_a["pose"]["regions"].get("full_body"), rec_b["pose"]["regions"].get("full_body")
    chk("save.version_2_full_body", rec_a["pose"].get("version") == 2 and reg_a is not None and
        rec_b["pose"].get("version") == 2 and reg_b is not None)
    if reg_a is None or reg_b is None:
        return
    written = set(reg_a["positions"]) | set(reg_a["orientations"])
    chk("save.written_set", len(written) == 278 and written == set(reg_b["positions"]) | set(reg_b["orientations"]),
        len(written))
    chk("save.A_captures_the_visible_posture", not R.oracle_problems(o["A2"], reg_a), R.oracle_problems(o["A2"], reg_a)[:8])
    chk("save.A_writes_nothing_to_the_scene", R.doc_unchanged(o["A2"], o["A3"]))
    chk("save.B_writes_nothing_to_the_scene", R.doc_unchanged(o["A4"], o["A5"]))
    chk("update.B_holds_the_updated_posture", not R.oracle_problems(o["A6"], reg_b),
        R.oracle_problems(o["A6"], reg_b)[:8])
    chk("update.B_no_longer_holds_the_saved_posture", len(R.oracle_problems(o["A4"], reg_b)) > 0)
    chk("update.in_place", rec_b.get("updated_at") != rec_b.get("created_at") and
        len(R.records.get(POSE_B) or []) == 1, (rec_b.get("created_at"), rec_b.get("updated_at")))
    chk("update.writes_nothing_to_the_scene", R.doc_unchanged(o["A6"], o["A7"]))
    lib = dict((t, read_json(os.path.join(R.q, "evidence", "library_%s.json" % t))) for t in ("A", "B")
               if os.path.isfile(os.path.join(R.q, "evidence", "library_%s.json" % t)))
    final = {}                        # every file, including the .bak Update Pose keeps of the replaced record
    folder = os.path.join(R.q, "evidence", "library_poses", R.c["character_dir"])
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        final[name] = s0_hash(os.path.join(folder, name))
    baks = [n for n in final if n.endswith(".bak")]
    chk("library.update_backups_are_the_replaced_records", all(
        n.startswith("S3 Pose B--") and R.oracle_problems(o["A4"], read_json(os.path.join(folder, n))["pose"][
            "regions"]["full_body"]) == [] for n in baks) and len(baks) <= 1, baks)
    chk("library.records_unchanged_by_the_apply_process", len(lib) == 2 and lib["A"]["files"] == lib["B"]["files"] ==
        final, sorted(final))

    if R.c.get("continuation"):
        pre = os.path.join(R.q, "evidence", "A1_PRECHECK.json")
        pc = read_json(pre) if os.path.isfile(pre) else {}
        smoke_path = os.path.join(R.q, "observations", "UI-SMOKE.json")
        smoke = read_json(smoke_path) if os.path.isfile(smoke_path) else {}
        chk("ui.full_body_apply_enabled_before_apply", smoke.get("apply_button_enabled") is True and
            (smoke.get("selected") or {}).get("name") == POSE_A and
            (smoke.get("selected") or {}).get("regions") == ["full_body"] and
            (smoke.get("state") or {}).get("apply_mode") == "direct" and not smoke.get("recovery_paused") and
            smoke.get("cpm_build_sha256") == R.ids["qualification_cpm_sha256"] and
            smoke.get("pid") == o["B1"]["pid"], dict((k, smoke.get(k)) for k in ("apply_button_enabled", "selected")))
        chk("precheck.revised_A1_compatible_before_apply", pc.get("compatible") is True and
            pc.get("qualification_cpm_sha256") == R.ids["qualification_cpm_sha256"] and
            (pc.get("observation") or {}).get("label") == "S0-08", {k: pc.get(k) for k in ("revised_A1", "compatible")})

    # Distinct postures (an Apply that changes nothing proves nothing: PS-1b5)
    d_dest = R.distinct_groups(reg_a, o["B1"])
    chk("distinct.destination_differs_from_A_in_every_group",
        all(d_dest.get(g, 0.0) >= VISIBLE_DEGREES for g in REQUIRED_GROUPS),
        dict((g, round(d_dest.get(g, 0.0), 2)) for g in REQUIRED_GROUPS))
    d_ab = R.distinct_groups(reg_b, o["A2"])
    chk("distinct.B_differs_from_A_visibly", sum(1 for g in REQUIRED_GROUPS if d_ab.get(g, 0.0) >= VISIBLE_DEGREES) >= 2,
        dict((g, round(d_ab.get(g, 0.0), 2)) for g in REQUIRED_GROUPS))

    # Apply A (B2), Undo/Redo (B3, B4), repeat (B5)
    b1 = o["B1"]
    chk("apply_A.written_channels_hold_the_record", not R.written_problems(o["B2"], b1, reg_a, False),
        R.written_problems(o["B2"], b1, reg_a, False)[:8])
    chk("apply_A.full_body_posture_reproduced", not R.applied_problems(o["B2"], b1, reg_a),
        R.applied_problems(o["B2"], b1, reg_a)[:8])
    chk("apply_A.other_instance_channels_unchanged", not R.channel_problems(b1, o["B2"], exclude=written),
        R.channel_problems(b1, o["B2"], exclude=written)[:8])
    chk("apply_A.facial_gaze_and_other_controls_unchanged", not R.control_problems(b1, o["B2"], written),
        R.control_problems(b1, o["B2"], written)[:8])
    chk("apply_A.unrelated_animation_unchanged", R.outside_equal("B1", "B2"))
    chk("apply_A.one_owned_undo_entry", o["B2"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + POSE_A and
        o["B2"]["session_after"]["undo"]["can_undo"] is True, o["B2"]["session_after"]["undo"])
    chk("undo.restores_the_baseline", not R.channel_problems(b1, o["B3"]) and not R.skeleton_problems(b1, o["B3"]) and
        o["B3"]["session_after"]["undo"]["undo_desc"] == b1["session_after"]["undo"]["undo_desc"] and
        o["B3"]["session_after"]["undo"]["can_redo"] is True, R.skeleton_problems(b1, o["B3"])[:5])
    chk("redo.restores_the_applied_pose", not R.channel_problems(o["B2"], o["B4"]) and
        not R.skeleton_problems(o["B2"], o["B4"]) and
        o["B4"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + POSE_A)
    chk("repeat.true_noop", R.doc_unchanged(o["B4"], o["B5"]))

    # Apply the updated B (B6): existing keys updated in place
    chk("apply_B.existing_keys_updated_in_place", not R.written_problems(o["B6"], o["B5"], reg_b, True),
        R.written_problems(o["B6"], o["B5"], reg_b, True)[:8])
    chk("apply_B.updated_posture_reproduced", not R.applied_problems(o["B6"], b1, reg_b),
        R.applied_problems(o["B6"], b1, reg_b)[:8])
    chk("apply_B.other_instance_channels_unchanged", not R.channel_problems(b1, o["B6"], exclude=written))
    chk("apply_B.facial_gaze_and_other_controls_unchanged", not R.control_problems(b1, o["B6"], written))
    chk("apply_B.unrelated_animation_unchanged", R.outside_equal("B1", "B6"))
    chk("apply_B.one_owned_undo_entry", o["B6"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + POSE_B)
    chk("abort.verified_nothing_changed", R.doc_unchanged(o["B6"], o["B7"]))
    chk("navigation.pose_persists", not R.channel_problems(o["B7"], o["B8"]) and
        not R.skeleton_problems(o["B7"], o["B8"]), R.skeleton_problems(o["B7"], o["B8"])[:5])
    chk("refusal.clip_editor_writes_nothing", R.doc_unchanged(o["B9"], o["B10"]))
    chk("refusal.fk_positions_write_nothing", R.doc_unchanged(o["B11"], o["B12"]))

    # Legacy left arm (B13 ... B17)
    b13, b14 = o["B13"], o["B14"]
    if legacy is not None:
        changed = [n for n in LEGACY_WRITTEN if R.channel_problems(b13, b14, names=[n])]
        chk("legacy.left_arm_keys_written", changed == list(LEGACY_WRITTEN), changed)
        chk("legacy.everything_else_unchanged", not R.channel_problems(b13, b14, exclude=LEGACY_WRITTEN) and
            R.outside_equal("B13", "B14"), R.channel_problems(b13, b14, exclude=LEGACY_WRITTEN)[:8])
        chk("legacy.one_owned_undo_entry", b14["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + LEGACY)
        chk("legacy.repeat_true_noop", R.doc_unchanged(b14, o["B15"]))
        chk("legacy.undo_restores", not R.channel_problems(b13, o["B16"]) and not R.skeleton_problems(b13, o["B16"]))
        chk("legacy.redo_restores", not R.channel_problems(b14, o["B17"]) and not R.skeleton_problems(b14, o["B17"]))

    # The CPM log: CPM's own verdicts, and the timing
    logs = parse_logs(os.path.join(R.q, "evidence", "logs"))
    ops = apply_operations(logs, list(pb)[0])
    chk("log.eight_apply_operations", len(ops) == 8, [op["id"] for op in ops])
    if len(ops) == 8:
        d = [p1_detail(op) or {} for op in ops]
        chk("log.apply_A_verified_by_cpm", has(ops[0], "PROD_POSE_BODY-P6 ") and has(ops[0], "PROD_POSE_BODY-P7-verified")
            and '"owned": true' in " ".join(ops[0]["text"]))
        chk("log.repeat_is_noop", d[1].get("noop") is True and not has(ops[1], "PROD_POSE_BODY-P6 "))
        chk("log.apply_B_updates_only", (d[2].get("actions") or {}).get("insert") == 0 and
            (d[2].get("actions") or {}).get("update", 0) > 0 and has(ops[2], "PROD_POSE_BODY-P7-verified"), d[2])
        chk("log.abort_verified", has(ops[3], "PROD_POSE_BODY-abort-verified"))
        chk("log.refusals_wrote_nothing", not any(has(ops[i], "PROD_POSE_BODY-P6 ") or
                                                  has(ops[i], "PROD_POSE_BODY-P3-P6-failure") for i in (4, 5)))
        chk("log.legacy_verified_by_cpm", has(ops[6], "PROD_POSE_P6 ") and has(ops[6], "PROD_POSE_P7-verified"))
        chk("log.legacy_repeat_is_noop", d[7].get("noop") is True and not has(ops[7], "PROD_POSE_P6 "))
    chk("log.no_recovery_or_uncertainty", not any(("RECOVERY_BLOCKED" in r["text"] or "undo-uncertain" in r["text"] or
                                                   "abort-unverified" in r["text"] or "P7-unverified" in r["text"])
                                                  for r in logs))
    R.timing = [dict(timing(op), step=s, id=op["id"]) for op, s in zip(ops, ("B2", "B5", "B6", "B7", "B10", "B12",
                                                                              "B14", "B15"))]

    # Restoration and the sessions
    restore = os.path.join(R.q, "evidence", "restore.json")
    chk("restore.published_and_inventories_equal", os.path.isfile(restore) and read_json(restore).get("restored") is True)
    dest = os.path.join(R.q, "evidence", "destination.json")
    chk("sessions.destination_not_saved_during_the_run", os.path.isfile(dest) and
        s0_hash(os.path.join(R.q, "sessions", "S3_DESTINATION.dmx")) == read_json(dest)["destination_sha256"])


# --- the supplemental run (B9 ... B17 only; S3 run 4) ----------------------------------------------------------------

SUPPLEMENT_STEPS = ["B%d" % i for i in range(9, 18)]
EDITOR_COPY = u"Switch to the Motion Editor to apply a pose. Nothing was changed."
PROPORTIONS_COPY = u"This pose was saved with different body proportions and can't be applied safely. Nothing was changed."
LEFT_ARM_BONES = ("bip_UpperArm_l", "bip_lowerArm_l", "bip_hand_l")


def legacy_distinct(o_source, o_dest):
    """How far the destination's left arm (B13, shot15) is from the legacy pose's own source arm (B11, shot10, where
    NQ1 Pose A was captured): the largest local-orientation difference of the left upper arm, lower arm and hand, and
    of the written Hand_l_o channel (degrees). A meaningful transfer needs a visible difference."""
    out = {}
    for name in LEFT_ARM_BONES:
        if name in o_source["bones"] and name in o_dest["bones"]:
            out[name] = angle(o_source["bones"][name]["local_orientation"], o_dest["bones"][name]["local_orientation"])
    a, b = Run.channels(o_source).get("Hand_l_o"), Run.channels(o_dest).get("Hand_l_o")
    if a and b and isinstance(a.get("value_at_mapped"), list) and isinstance(b.get("value_at_mapped"), list):
        out["Hand_l_o"] = angle(a["value_at_mapped"], b["value_at_mapped"])
    return out


def arm_motion(o1, o2):
    return max([angle(o1["bones"][n]["world_orientation"], o2["bones"][n]["world_orientation"])
                for n in LEFT_ARM_BONES if n in o1["bones"] and n in o2["bones"]] or [0.0])


def evaluate_supplement(R):
    """The supplement's steps come from the configuration ("supplement_steps"; default B9-B17): run 4 covers B9-B17,
    run 5 the legacy segment (B11 as the legacy pose's source arm, then B13-B17). Only the covered steps are checked."""
    o, chk = R.obs, R.check
    steps = list(R.c.get("supplement_steps") or SUPPLEMENT_STEPS)
    refusals = "B9" in steps
    for step in steps:
        if not chk("observed.%s" % step, step in o and step in R.side, LABELS[step]):
            continue
        problems = s0_analyze.validate(o[step]) + list(o[step].get("problems") or []) + list(R.side[step]["mismatch"])
        chk("valid.%s" % step, not problems and o[step]["readonly"]["unchanged"], problems[:5])
        chk("cpm.%s" % step, (o[step].get("cpm_loaded") or {}).get("build_sha256") == R.ids["qualification_cpm_sha256"],
            o[step].get("cpm_loaded"))
    if any(s not in o for s in steps):
        chk("complete", False, "missing observations: %s" % [s for s in steps if s not in o])
        return
    pids = set(o[s]["pid"] for s in steps)
    chk("process.one_sfm_process", len(pids) == 1, sorted(pids))
    chk("process.destination_session", all(o[s]["document"].lower().endswith("s3_destination.dmx")
                                           for s in steps), o[steps[0]]["document"])
    if refusals:
        chk("refusal.clip_editor_writes_nothing", R.doc_unchanged(o["B9"], o["B10"]))
        chk("refusal.fk_proportions_write_nothing", R.doc_unchanged(o["B11"], o["B12"]))
    legacy = R.record(LEGACY)
    chk("library.legacy_record_present", legacy is not None)
    pre_path = os.path.join(R.q, "evidence", "LEGACY_PRECHECK.json")
    pre = read_json(pre_path) if os.path.isfile(pre_path) else {}
    chk("legacy.precheck_visible_difference_before_apply", pre.get("distinct") is True and
        pre.get("source_label") == "S0-18" and pre.get("destination_label") == "S0-20", pre.get("differences_deg"))
    b13, b14 = o["B13"], o["B14"]
    changed = [n for n in LEGACY_WRITTEN if R.channel_problems(b13, b14, names=[n])]
    chk("legacy.left_arm_keys_written", changed == list(LEGACY_WRITTEN), changed)
    motion = arm_motion(b13, b14)
    chk("legacy.visible_left_arm_transfer", motion >= VISIBLE_DEGREES, round(motion, 3))
    taken = dict((k, v) for k, v in legacy_distinct(o["B11"], b14).items() if k in LEFT_ARM_BONES)
    chk("legacy.arm_takes_the_saved_pose", len(taken) == 3 and max(taken.values()) <= R.tol["angle_degrees"],
        taken)      # the arm bones' local orientations equal the pose's source arm (NQ1 Pose A, shot10, B11)
    chk("legacy.everything_else_unchanged", not R.channel_problems(b13, b14, exclude=LEGACY_WRITTEN) and
        R.outside_equal("B13", "B14"), R.channel_problems(b13, b14, exclude=LEGACY_WRITTEN)[:8])
    chk("legacy.one_owned_undo_entry", b14["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + LEGACY)
    chk("legacy.repeat_true_noop", R.doc_unchanged(b14, o["B15"]))
    chk("legacy.undo_restores", not R.channel_problems(b13, o["B16"]) and not R.skeleton_problems(b13, o["B16"]) and
        o["B16"]["session_after"]["undo"]["can_redo"] is True)
    chk("legacy.redo_restores", not R.channel_problems(b14, o["B17"]) and not R.skeleton_problems(b14, o["B17"]) and
        o["B17"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + LEGACY)
    logs = parse_logs(os.path.join(R.q, "evidence", "logs"))
    ops = apply_operations(logs, list(pids)[0])
    expected = 4 if refusals else 2
    chk("log.apply_operations_as_planned", len(ops) == expected, [op["id"] for op in ops])
    if len(ops) == expected:
        text = lambda op: " ".join(op["text"])  # noqa: E731
        if refusals:
            chk("log.clip_editor_refusal_says_switch_to_the_motion_editor", EDITOR_COPY in text(ops[0]) and
                "editor-mode-refused" in text(ops[0]) and not has(ops[0], "PROD_POSE_BODY-P6 "))
            chk("log.proportions_refusal_keeps_its_message", PROPORTIONS_COPY in text(ops[1]) and
                not has(ops[1], "PROD_POSE_BODY-P6 "))
        legacy_ops = ops[-2:]
        chk("log.legacy_verified_by_cpm", has(legacy_ops[0], "PROD_POSE_P6 ") and
            has(legacy_ops[0], "PROD_POSE_P7-verified") and not has(legacy_ops[0], "PROD_POSE_BODY-"))
        chk("log.legacy_repeat_is_noop", (p1_detail(legacy_ops[1]) or {}).get("noop") is True and
            not has(legacy_ops[1], "PROD_POSE_P6 "))
    chk("log.no_recovery_or_uncertainty", not any(("RECOVERY_BLOCKED" in r["text"] or "undo-uncertain" in r["text"] or
                                                   "abort-unverified" in r["text"] or "P7-unverified" in r["text"])
                                                  for r in logs))
    R.timing = [dict(timing(op), step=s, id=op["id"]) for op, s in zip(ops, ("B10", "B12", "B14", "B15") if refusals
                                                                          else ("B14", "B15"))]
    restore = os.path.join(R.q, "evidence", "restore.json")
    chk("restore.published_and_inventories_equal", os.path.isfile(restore) and read_json(restore).get("restored") is True)
    dest = os.path.join(R.q, "evidence", "destination.json")
    chk("sessions.destination_not_saved_during_the_run", os.path.isfile(dest) and
        s0_hash(os.path.join(R.q, "sessions", "S3_DESTINATION.dmx")) == read_json(dest)["destination_sha256"])


def legacy_precheck(c):
    """Read-only, after B13: does shot15's left arm differ visibly from NQ1 Pose A's own source arm (B11, shot10)?"""
    R = Run(c)
    if "B11" not in R.obs or "B13" not in R.obs:
        raise SystemExit("REFUSED: observe B11 and B13 first")
    for s in ("B11", "B13"):
        if R.side[s]["mismatch"] or R.obs[s]["problems"]:
            raise SystemExit("REFUSED: %s is not a valid observation" % s)
    diff = legacy_distinct(R.obs["B11"], R.obs["B13"])
    distinct = bool(diff) and max(diff.values()) >= VISIBLE_DEGREES
    return {"source_label": R.obs["B11"]["label"], "destination_label": R.obs["B13"]["label"],
            "source_shot": R.obs["B11"]["session_after"]["current_shot"],
            "destination_shot": R.obs["B13"]["session_after"]["current_shot"],
            "differences_deg": dict((k, round(v, 3)) for k, v in diff.items()), "threshold_deg": VISIBLE_DEGREES,
            "distinct": distinct}


def s0_hash(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def performance(R):
    rows = [t for t in getattr(R, "timing", []) if t["step"] in ("B2", "B6", "B14")]
    if not rows or any(t["blocking_ms"] is None or t["whole_ms"] is None for t in rows):
        return {"class": "unmeasured", "applies": rows}
    worst = max(max(t["blocking_ms"], t["whole_ms"]) for t in rows)
    cls = "responsive" if worst <= PERF["responsive_ms"] else ("finding" if worst <= PERF["limit_ms"] else "fail")
    return {"class": cls, "worst_ms": worst, "criteria_ms": PERF, "applies": rows}


def run(c):
    R = Run(c)
    R.timing = []
    (evaluate_supplement if c.get("supplement") else evaluate)(R)
    perf = performance(R)
    failed = [x for x in R.checks if not x["pass"]]
    verdict = "PASS" if not failed and perf["class"] in ("responsive", "finding") else "FAIL"
    out = {"format": "F01-S3-verdict-v1", "verdict": verdict, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in failed], "performance": perf, "timing": R.timing}
    ev = os.path.join(R.q, "evidence")
    for name, data in (("S3_VERDICT.json", json.dumps(out, indent=1, sort_keys=True)), ("S3_VERDICT.md", markdown(out))):
        path = os.path.join(ev, name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(markdown(out))
    return 0 if verdict == "PASS" else 1


def markdown(out):
    lines = ["# F-01 full-body S3 verdict: %s" % out["verdict"], "",
             "Qualification CPM `%s`." % out["identities"].get("qualification_cpm_sha256"), "",
             "| Check | Result | Detail |", "|---|---|---|"]
    for x in out["checks"]:
        lines.append("| `%s` | %s | %s |" % (x["id"], "PASS" if x["pass"] else "**FAIL**",
                                            "" if x["pass"] or x["detail"] is None else
                                            json.dumps(x["detail"], default=str)[:200].replace("|", "/")))
    perf = out["performance"]
    lines += ["", "Performance: **%s** (worst %s ms; responsive <= %d ms, limit %d ms)." % (
        perf["class"], perf.get("worst_ms"), PERF["responsive_ms"], PERF["limit_ms"]), "",
        "| Step | Preflight ms | Transaction ms | Blocking ms | Deferred verify ms | Whole ms |", "|---|---|---|---|---|---|"]
    for t in out["timing"]:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (t["step"], t["preflight_ms"], t["transaction_ms"],
                                                         t["blocking_ms"], t["deferred_verify_ms"], t["whole_ms"]))
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import s3_tool
    return run(s3_tool.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
