# -*- coding: utf-8 -*-
"""M-06 W2 deferred-verification fixture: READ-ONLY offline scan of a binary DMX (format 5) session file.

usage: python -I scan_deferred_fixture.py FIXTURE.dmx SHOT ANIMSET OUT.json [PREFERRED_LITERAL ...]

The file is only read: its SHA-256, size and modification time are recorded before and after and must be unchanged,
and the parse must consume the file exactly. The reader follows the M-05 offline inspection reader.

Reports, for the animation set in the shot:
  * the existing bone-scale graphs: control <- mode-3 input channel -> DmeExpressionOperator -> mode-3 output
    channel -> bone transform "scale" (the qualified M-05 graph must be present and intact: input and output mode 3);
  * every flex control whose channel has mode 3, exactly one log layer and exactly one key at time zero with a finite
    value, and whose stored source is finite (the representation the deferred case needs);
  * the selected candidate (first preferred literal that qualifies, else the first qualifying literal in name order)
    and the proposed stored source value: distinct from the key, finite and inside [0, 1].
STOP (exit 1, "stop" set) when no flex qualifies or no intact mode-3 graph exists: never broaden the mutation.
Offline evidence cannot show coherent native evaluation or survival across reload; the native preparation procedure
establishes those.
"""
from __future__ import print_function

import hashlib
import io
import json
import math
import os
import struct
import sys

SIZES = {2: 4, 3: 4, 4: 1, 7: 4, 8: 4, 9: 8, 10: 12, 11: 16, 12: 12, 13: 16, 14: 64}
FMT = {2: "<i", 3: "<f", 4: "<B", 7: "<i"}


def identity(path):
    st = os.stat(path)
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest(), st.st_size, int(st.st_mtime)


class Reader(object):
    def __init__(self, data, pos):
        self.b, self.p = data, pos

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = struct.unpack_from("<B", self.b, self.p)[0]
        self.p += 1
        return v

    def cstr(self):
        e = self.b.index(b"\0", self.p)
        s = self.b[self.p:e].decode("utf-8", "replace")
        self.p = e + 1
        return s

    def raw(self, n):
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def scalar(self, t):
        v = self.raw(SIZES[t])
        return struct.unpack(FMT[t], v)[0] if t in FMT else v


def parse(data):
    header = data[:data.index(b"\n")].decode("ascii", "replace")
    if "binary 5" not in header:
        raise ValueError("not a binary DMX format 5 file: %r" % header)
    r = Reader(data, data.index(b"\n") + 2)
    strings = [r.cstr() for _ in range(r.i32())]
    elems = []
    for _ in range(r.i32()):
        t, n = strings[r.i32()], strings[r.i32()]
        guid = r.raw(16)
        elems.append({"type": t, "name": n, "id": "".join("%02x" % c for c in bytearray(guid)), "a": {}})
    for e in elems:
        for _ in range(r.i32()):
            an, at = strings[r.i32()], r.u8()
            if at == 1:
                v = r.i32()
                if v == -2:
                    v = ("ext", r.cstr())
            elif at == 5:
                v = strings[r.i32()]
            elif at == 6:
                v = r.raw(r.i32())
            elif at in SIZES:
                v = r.scalar(at)
            elif 15 <= at <= 28:
                base, cnt = at - 14, r.i32()
                if base == 1:
                    v = []
                    for _ in range(cnt):
                        x = r.i32()
                        v.append(("ext", r.cstr()) if x == -2 else x)
                elif base == 5:
                    v = [r.cstr() for _ in range(cnt)]
                elif base == 6:
                    v = [r.raw(r.i32()) for _ in range(cnt)]
                else:
                    v = [r.scalar(base) for _ in range(cnt)]
            else:
                raise ValueError("unknown attribute type %d" % at)
            e["a"][an] = (at, v)
    if r.p != len(data):
        raise ValueError("parse did not consume the file exactly (%d of %d)" % (r.p, len(data)))
    return header, elems


class Doc(object):
    def __init__(self, elems):
        self.e = elems

    def ref(self, v):
        return self.e[v] if isinstance(v, int) and 0 <= v < len(self.e) else None

    @staticmethod
    def val(el, k):
        x = el["a"].get(k)
        return None if x is None else x[1]

    def log(self, ch):
        lg = self.ref(self.val(ch, "log"))
        if lg is None:
            return None
        layers = [self.ref(x) for x in (self.val(lg, "layers") or [])]
        return {"type": lg["type"], "layers": [{"type": L["type"], "times": list(self.val(L, "times") or []),
                                                 "values": list(self.val(L, "values") or [])}
                                                for L in layers if L is not None],
                "layer_refs_resolved": all(L is not None for L in layers)}


def finite(x):
    return isinstance(x, float) and not (math.isnan(x) or math.isinf(x))


def proposed_stored(key):
    v = key + 0.25 if key <= 0.5 else key - 0.25
    return float(struct.unpack("<f", struct.pack("<f", v))[0])


def scan(path, shot_name, animset_name, preferred):
    before = identity(path)
    with open(path, "rb") as f:
        data = f.read()
    header, elems = parse(data)
    after = identity(path)
    d = Doc(elems)
    channels = [e for e in elems if e["type"] == "DmeChannel"]
    report = {"file": os.path.basename(path), "header": header, "elements": len(elems),
              "file_identity": {"sha256": before[0], "size": before[1], "unchanged_after_read": before == after},
              "shot": shot_name, "animation_set": animset_name, "stop": []}
    sets = []
    for clip in elems:
        if clip["type"] == "DmeFilmClip" and clip["name"] == shot_name:
            for x in d.val(clip, "animationSets") or []:
                a = d.ref(x)
                if a is not None and a["name"] == animset_name:
                    sets.append(a)
    if len(sets) != 1:
        report["stop"].append("expected one animation set %r in %s, found %d" % (animset_name, shot_name, len(sets)))
        return report
    aset = sets[0]
    controls = [d.ref(c) for c in d.val(aset, "controls") or []]
    named = {}
    for c in controls:
        if c is not None:
            named.setdefault(c["name"], []).append(c)
    graphs = []
    for c in controls:
        if c is None or not c["name"].endswith("_scale"):
            continue
        cin = d.ref(d.val(c, "channel"))
        expr = d.ref(d.val(cin, "toElement")) if cin else None
        outs = [o for o in channels if expr is not None and d.ref(d.val(o, "fromElement")) is expr]
        for o in outs:
            tr = d.ref(d.val(o, "toElement"))
            graphs.append({"control": c["name"], "control_id": c["id"], "input_mode": d.val(cin, "mode"),
                           "operator": expr["type"], "operator_id": expr["id"], "output_mode": d.val(o, "mode"),
                           "to_attribute": d.val(o, "toAttribute"), "bone": tr and tr["name"],
                           "bone_scale": tr and d.val(tr, "scale"), "input_log": d.log(cin),
                           "intact": bool(cin and expr and expr["type"] == "DmeExpressionOperator" and tr and
                                          d.val(o, "toAttribute") == "scale" and d.val(cin, "mode") == 3 and
                                          d.val(o, "mode") == 3)})
    report["scale_graphs"] = graphs
    if not any(g["intact"] for g in graphs):
        report["stop"].append("no intact mode-3 bone-scale graph on %r" % animset_name)
    candidates, rejected = [], {}
    for name in sorted(named):
        hits = named[name]
        c = hits[0]
        ch = d.ref(d.val(c, "channel"))
        if ch is None or d.val(ch, "toAttribute") != "flexWeight":
            continue
        why = []
        if len(hits) != 1:
            why.append("control name not unique")
        if d.val(ch, "mode") != 3:
            why.append("mode %r" % d.val(ch, "mode"))
        lg = d.log(ch)
        if lg is None or not lg["layer_refs_resolved"] or len(lg["layers"]) != 1:
            why.append("not exactly one readable log layer")
        else:
            L = lg["layers"][0]
            if L["times"] != [0] or len(L["values"]) != 1 or not finite(L["values"][0]):
                why.append("not exactly one finite key at time zero (%d keys)" % len(L["times"]))
        stored = d.val(c, "value")
        if not finite(stored):
            why.append("stored source not finite")
        if why:
            rejected[name] = why
            continue
        key = lg["layers"][0]["values"][0]
        candidates.append({"literal": name, "control_id": c["id"], "channel_id": ch["id"], "stored": stored,
                           "key": key, "stored_equals_key": stored == key,
                           "destination": (d.ref(d.val(ch, "toElement")) or {}).get("type"),
                           "proposed_stored": proposed_stored(key)})
    report["candidates"] = candidates
    report["rejected_flex"] = rejected
    pick = [c for p in preferred for c in candidates if c["literal"] == p] or candidates
    if not pick:
        report["stop"].append("no flex with mode 3, one layer and one key at time zero: stop fixture preparation")
    else:
        report["selected"] = pick[0]
        if pick[0]["proposed_stored"] == pick[0]["key"]:
            report["stop"].append("proposed stored value is not distinct from the key")
    if not report["file_identity"]["unchanged_after_read"]:
        report["stop"].append("the fixture file changed while it was read")
    return report


def main(argv):
    if len(argv) < 5:
        print(__doc__)
        return 2
    report = scan(argv[1], argv[2], argv[3], argv[5:])
    with io.open(argv[4], "w", encoding="utf-8") as f:
        f.write(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=True))
    print("graphs: %d intact of %d; candidates: %d; selected: %s; STOP: %s" % (
        sum(1 for g in report.get("scale_graphs", []) if g["intact"]), len(report.get("scale_graphs", [])),
        len(report.get("candidates", [])), (report.get("selected") or {}).get("literal"), report["stop"] or "none"))
    return 1 if report["stop"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
