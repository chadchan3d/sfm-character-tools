# -*- coding: utf-8 -*-
"""F-01 full body (stage E): derive compact discovery fixtures from the native S0 survey observations.

A fixture is the portable discovery form that the stage E live layer builds from SFM (prod_body_discover), taken from
one read-only S0 observation (real_sfm_qualification/f01_full_body_s0; run 2, Owner's local archive): element
handles, names, parents, bindings, log and layer types, every key, the value at the mapped tick, the channel clock,
the evaluated transforms and the document-wide writer counts. Nothing is interpreted. The raw observations are not
committed; the derived fixtures are (cpm/convergence/tests/fixtures/f01_body/), each naming its source hash.

usage: python -I f01_body_fixture.py OBSERVATION.json OUT.json
"""
from __future__ import print_function

import hashlib
import io
import json
import sys

CONSTRAINTS = ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigIKConstraintOperator")
CHANNEL_ATTRS = ("positionChannel", "orientationChannel", "channel", "leftvaluechannel", "rightvaluechannel")


def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def ident(x):
    return None if x is None else {"handle": x["handle"], "type": x["type"], "name": x["name"]}


def derive(obs, source_sha256):
    scene = obs["scene"]
    model_state = obs["model"]["state"]
    D = {"format": "f01-body-discovery-fixture-v1",
         "source": {"label": obs["label"], "sha256": source_sha256, "shot": obs["session_after"]["current_shot"],
                    "timeline_mode": obs["session_after"]["timeline_mode"]["name"]},
         "t_chan": obs["time"]["t_chan"], "t_doc": obs["time"]["t_doc"], "t_shot": obs["time"]["t_shot"],
         "model": {"handle": obs["model"]["id"]["handle"], "transform": model_state["transform"]["handle"],
                   "model_ref": value(obs["model"]["modelName"]), "scale": model_state["scale"],
                   "local_position": model_state["local_position"], "local_orientation": model_state["local_orientation"],
                   "world_position": model_state["world_position"], "world_orientation": model_state["world_orientation"]}}
    regs = obs["rig"]["registrations"]
    D["rig"] = {"names": [r["rig"]["name"] for r in regs], "registrations": len(regs),
                "rig_handle": regs[0]["rig"]["handle"], "registration": regs[0]["registration"]["handle"],
                "elements": [e["handle"] for e in regs[0]["elements"]], "handles": {}}
    for n, h in obs["rig"]["handles"].items():
        parents = h["parents"]
        p = scene.get(str(parents[0])) if len(parents) == 1 else None
        D["rig"]["handles"][n] = {
            "handle": h["id"]["handle"], "transform": h["transform"]["handle"], "parent_count": len(parents),
            "parent": {"handle": parents[0], "type": p["type"], "name": p["name"]} if p else None,
            "local_position": h["local_position"], "local_orientation": h["local_orientation"],
            "world_position": h["world_position"], "world_orientation": h["world_orientation"], "scale": h["scale"]}
    D["bones"] = {}
    for n, b in obs["bones"].items():
        D["bones"][n] = {"index": b["index"], "handle": b["dag"], "transform": b["transform"]["handle"],
                         "parent": b["parent_bone"], "parent_count": len(b["parent_dags"]),
                         "parent_dag": b["parent_dags"][0] if len(b["parent_dags"]) == 1 else None,
                         "local_position": b["local_position"], "local_orientation": b["local_orientation"],
                         "world_position": b["world_position"], "world_orientation": b["world_orientation"],
                         "scale": b["scale"]}
    D["operators"] = []
    for op in obs["operators"]:
        row = {"handle": op["id"]["handle"], "type": op["id"]["type"], "name": op["id"]["name"],
               "owners": op["owners"], "slaves": {}, "targets": [], "pole": None, "solver": op.get("solver") or {}}
        for slot, s in (op.get("slaves") or {}).items():
            row["slaves"][slot] = None if s is None or s.get("slave") is None else {
                "slave": s["slave"]["handle"], "target": s["target"]["handle"] if s.get("target") else None}
        for t in op.get("targets") or []:
            row["targets"].append({"handle": t["id"]["handle"], "target": t["target"]["handle"] if t["target"] else None,
                                   "weight": t["targetWeight"], "oOffset": t["oOffset"], "vecOffset": t["vecOffset"]})
        if op.get("pvTarget"):
            row["pole"] = op["pvTarget"]["handle"]
        if op["id"]["type"] == "DmeExpressionOperator":
            row["attributes"] = dict((k, v) for k, v in op["attributes"].items()
                                     if k in ("expr", "value", "result", "name"))
        D["operators"].append(row)
    D["controls"] = {}
    for c in obs["controls"]:
        refs = {}
        for a in CHANNEL_ATTRS:
            v = value(c["attributes"].get(a))
            if a in c["attributes"]:
                refs[a] = v["handle"] if v else None
        values = dict((a, value(c["attributes"][a])) for a in ("valuePosition", "valueOrientation", "value")
                      if a in c["attributes"])
        D["controls"][c["id"]["name"]] = {"handle": c["id"]["handle"], "type": c["id"]["type"], "channels": refs,
                                          "values": values}
    D["channels"] = {}
    destinations = obs["writer_index"]["destinations"]
    D["writers"] = {}
    for ch in obs["channels"]:
        b = ch["binding"]
        to, attr = value(b["toElement"]), value(b["toAttribute"])
        layer = ch["layers"][0]
        D["channels"][ch["id"]["name"]] = {
            "handle": ch["id"]["handle"], "from": ident(value(b["fromElement"])),
            "from_attribute": value(b["fromAttribute"]), "to": ident(to), "to_attribute": attr,
            "mode": value(b["mode"]), "log_type": (ch["log"] or {}).get("type"), "log": (ch["log"] or {}).get("handle"),
            "layers": [l["type"] for l in ch["layers"]], "layer": layer["id"]["handle"], "keys": layer["keys"],
            "value": ch["value_at_mapped"], "clock": ch["current_ticks"],
            "curveinfo": (ch.get("log_fields") or {}).get("curveinfo")}
        if to is not None:
            key = "%d:%s" % (to["handle"], attr)
            D["writers"][key] = len(destinations.get(key, []))
    D["slave_targets"] = dict((k, len(v)) for k, v in obs["writer_index"]["slave_targets"].items())
    known = set(CONSTRAINTS + ("DmeExpressionOperator", "DmePackColorOperator"))
    D["unknown_operator_types"] = sorted(t for t in obs["writer_index"]["operator_types"] if t not in known)
    return D


def main(argv):
    with io.open(argv[1], "rb") as f:
        raw = f.read()
    D = derive(json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest())
    data = (json.dumps(D, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with io.open(argv[2], "wb") as f:
        f.write(data)
    print(argv[2], len(data), hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main(sys.argv)
