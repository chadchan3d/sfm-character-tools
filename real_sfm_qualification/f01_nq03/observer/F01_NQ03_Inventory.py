# -*- coding: ascii -*-
"""F-01 NQ-03 header inventory: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    NQ_DIR = r"<run folder>"; NQ_REPO = r"<repo>"
    NQ_LABEL = "NQ03-01"; NQ_ANIMSET = "heavy1"
    execfile(NQ_REPO + r"\\real_sfm_qualification\\f01_nq03\\observer\\F01_NQ03_Inventory.py")

Purpose: find a stock model whose engine-loaded studio header declares no procedural bone (a candidate for the first
generic version 3 Full body qualification; F01_SFP1_QUATINTERP_FEASIBILITY.md section 5). For every model listed in
the kit's candidates.json it uses SFM's shipped model cache exactly as Valve's own model pipeline does
(sdktools/python/global/lib/site-packages/modelpipeline/asset.py): g_pMDLCache.FindMDL(path) -> IsErrorModel ->
GetStudioHdr -> per bone pszName, parent, flags, proctype, procindex, physicsbone; the local attachments' bones; the
bone flex drivers' bones -> Release(handle). No scene element is created or changed; the models load into the
engine's cache in process memory only. The values of the STUDIO_PROC_* and BONE_* constants are read from vs.studio.

The reads run inside the read-only window of the natively proven S0 observer (pinned, verified before use, never
modified), anchored on the animation set NQ_ANIMSET of the preserved survey session copy, as the NQ-S6 observer does:
the document digest of every key and the session state are compared before and after. S0's structural surprises for
a non-Krystal anchor are findings, not problems.

It refuses, writing nothing, when the label is not NQ03-NN, the file exists, the S0 observer is not the pinned one, the
candidate list is unreadable, or the shot at the playhead has no single animation set named NQ_ANIMSET. Its only file
write is <NQ_DIR>\\observations\\<NQ_LABEL>.json (exclusive create).
"""
import hashlib
import json
import os
import re
import sys

FORMAT = "F01-NQ03-observation-v1"
S0_REL = os.path.join("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
S0_SHA256 = "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4"
S0_TAIL = b"\n\nmain()\n"
CANDIDATES_REL = os.path.join("real_sfm_qualification", "f01_nq03", "candidates.json")
STUDIO_CONSTANTS = ("STUDIO_PROC_AXISINTERP", "STUDIO_PROC_QUATINTERP", "STUDIO_PROC_AIMATBONE",
                    "STUDIO_PROC_AIMATATTACH", "STUDIO_PROC_JIGGLE", "STUDIO_PROC_TWIST_MASTER",
                    "STUDIO_PROC_TWIST_SLAVE", "STUDIO_PROC_POINT_CONSTRAINT", "STUDIO_PROC_ORIENT_CONSTRAINT",
                    "STUDIO_PROC_AIM_CONSTRAINT", "BONE_PHYSICALLY_SIMULATED", "BONE_PHYSICS_PROCEDURAL",
                    "BONE_ALWAYS_PROCEDURAL", "BONE_SCREEN_ALIGN_SPHERE", "BONE_SCREEN_ALIGN_CYLINDER")
BONE_FIELDS = ("parent", "flags", "proctype", "procindex", "physicsbone")
MAX_BONES = 4096
MAX_ITEMS = 1024
FINDING_PATTERNS = (r"^expected one rig registration for the animation set",
                    r"^rig handle .* is duplicated$",
                    r"^bone .* has \d+ scene elements$",
                    r"^bone .* is duplicated$",
                    r"^unrecognised bone transform name",
                    r"^the model is not in the shot's scene$",
                    r"^expected one channels clip holding every control channel")


def nq3_exec(code, ns):
    exec(code, ns)


def nq3_load_s0(repo):
    path = os.path.join(repo, S0_REL)
    with open(path, "rb") as f:
        raw = f.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != S0_SHA256:
        raise RuntimeError("the S0 observer is not the pinned %s (%s); nothing was written" % (S0_SHA256, digest))
    if not raw.endswith(S0_TAIL):
        raise RuntimeError("the S0 observer does not end with its main() call; nothing was written")
    return path, raw[:-len("main()\n")]


def nq3_candidates(repo):
    path = os.path.join(repo, CANDIDATES_REL)
    with open(path, "rb") as f:
        raw = f.read()
    data = json.loads(raw.decode("utf-8"))
    rows = data.get("candidates")
    if data.get("format") != "F01-NQ03-candidates-v1" or not isinstance(rows, list) or not rows or \
            len(rows) > 64 or not all(isinstance(r.get("path"), (str, type(u""))) for r in rows):
        raise RuntimeError("the candidate list is not readable; nothing was written")
    return hashlib.sha256(raw).hexdigest(), rows


def nq3_read(fn):
    """{status: READ, value} or {status: UNREADABLE, error}: a failed read is recorded, never inferred."""
    try:
        return {"status": "READ", "value": fn()}
    except Exception as exc:
        return {"status": "UNREADABLE", "error": repr(exc)}


def nq3_header(ns, cache, handle):
    out = {"error_model": nq3_read(lambda: bool(cache.IsErrorModel(handle)))}
    hdr = nq3_read(lambda: cache.GetStudioHdr(handle))
    if hdr["status"] != "READ" or hdr["value"] is None:
        out["header"] = {"status": "UNREADABLE", "error": hdr.get("error") or "GetStudioHdr returned None"}
        return out
    hdr = hdr["value"]
    out["name"] = nq3_read(lambda: ns["text"](hdr.name))
    out["checksum"] = nq3_read(lambda: int(hdr.checksum))
    count = nq3_read(lambda: int(hdr.numbones))
    out["numbones"] = count
    out["bones"] = []
    if count["status"] == "READ" and 0 < count["value"] <= MAX_BONES:
        for i in range(count["value"]):
            b = nq3_read(lambda i=i: hdr.pBone(i))
            row = {"index": i}
            if b["status"] != "READ" or b["value"] is None:
                row["unreadable"] = b.get("error") or "pBone returned None"
                out["bones"].append(row)
                continue
            bone = b["value"]
            row["name"] = nq3_read(lambda: ns["text"](bone.pszName()))
            for f in BONE_FIELDS:
                row[f] = nq3_read(lambda f=f: int(getattr(bone, f)))
            out["bones"].append(row)
    n = nq3_read(lambda: int(hdr.numlocalattachments))
    out["attachments"] = {"count": n, "bones": []}
    if n["status"] == "READ" and 0 <= n["value"] <= MAX_ITEMS:
        for i in range(n["value"]):
            out["attachments"]["bones"].append(nq3_read(lambda i=i: int(hdr.pLocalAttachment(i).localbone)))
    n = nq3_read(lambda: int(hdr.BoneFlexDriverCount()))
    out["flex_drivers"] = {"count": n, "bones": []}
    if n["status"] == "READ" and 0 <= n["value"] <= MAX_ITEMS:
        for i in range(n["value"]):
            out["flex_drivers"]["bones"].append(nq3_read(lambda i=i: int(hdr.BoneFlexDriver(i).m_nBoneIndex)))
    return out


def nq3_inventory(ns, candidates):
    from vs import studio
    vs = sys.modules.get("vs")
    cache = getattr(studio, "g_pMDLCache", None) or getattr(vs, "g_pMDLCache", None)
    invalid = getattr(studio, "MDLHANDLE_INVALID", getattr(vs, "MDLHANDLE_INVALID", None))
    out = {"constants": dict((name, nq3_read(lambda name=name: int(getattr(studio, name))))
                             for name in STUDIO_CONSTANTS),
           "mdlhandle_invalid": invalid, "models": []}
    if cache is None or invalid is None:
        out["error"] = "the model cache interface is unavailable"
        return out
    for c in candidates:
        path = c["path"]
        row = {"path": path, "family": c.get("family")}
        h = nq3_read(lambda: cache.FindMDL(str(path)))
        row["find"] = {"status": h["status"], "error": h.get("error")}
        if h["status"] != "READ" or h["value"] == invalid:
            row["status"] = "not-found" if h["status"] == "READ" else "unreadable"
            out["models"].append(row)
            continue
        handle = h["value"]
        try:
            row.update(nq3_header(ns, cache, handle))
            row["status"] = "read"
        finally:
            row["release"] = nq3_read(lambda: int(cache.Release(handle)))
        out["models"].append(row)
    return out


def nq3_reclassify(out):
    keep, findings = [], []
    for p in out["problems"]:
        if any(re.match(r, p) for r in FINDING_PATTERNS):
            findings.append(p)
        else:
            keep.append(p)
    out["problems"], out["findings"] = keep, findings


def nq3_declared(model, constants):
    mask = 0
    for name in STUDIO_CONSTANTS:
        if name.startswith("BONE_"):
            mask |= (constants.get(name) or {}).get("value") or 0
    out = []
    for b in model.get("bones") or []:
        pt, fl = (b.get("proctype") or {}).get("value"), (b.get("flags") or {}).get("value")
        if pt not in (None, 0) or (fl is not None and fl & mask):
            out.append((b.get("name") or {}).get("value"))
    return out


def nq3_observe(repo, label, animset_name):
    path, source = nq3_load_s0(repo)
    candidates_sha, candidates = nq3_candidates(repo)
    ns = {"__name__": "__f01_nq03_s0__", "S0_ANIMSET": animset_name}
    nq3_exec(compile(source, path, "exec"), ns)
    shot = ns["sfmApp"].GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("no shot at the playhead; nothing was written")
    names = [ns["text"](a.GetName()) for a in ns["seq"](ns["attr"](shot, "animationSets"))]
    if names.count(animset_name) != 1:
        raise RuntimeError("the shot at the playhead has animation sets %r, not exactly one %r; nothing was written"
                           % (names, animset_name))
    original = ns["survey"]

    def survey(out):
        original(out)
        try:
            out["nq03"] = nq3_inventory(ns, candidates)
        except Exception as exc:
            out["problems"].append("NQ-03 reads failed: %r" % (exc,))
            out["nq03"] = None

    ns["survey"] = survey
    data = ns["observe"](label)
    data["format"], data["s0_format"], data["s0_observer_sha256"] = FORMAT, ns["FORMAT"], S0_SHA256
    data["candidates_sha256"] = candidates_sha
    data["animation_sets_in_shot"] = names
    nq3_reclassify(data)
    return data


def nq3_summary(data, label):
    inv = data.get("nq03") or {}
    models = inv.get("models") or []
    read = [m for m in models if m.get("status") == "read"]
    clean = [m["path"].split("/")[-1] for m in read if not nq3_declared(m, inv.get("constants") or {})
             and not any("unreadable" in b or any((b.get(f) or {}).get("status") != "READ" for f in BONE_FIELDS)
                         for b in m.get("bones") or [])]
    return ("NQ03 %s: %s models=%d read=%d not_read=%d no_procedural_declaration=%d %s readonly=%s problems=%d%s" % (
        label, "OK" if not data["problems"] and data["readonly"]["unchanged"] else "PROBLEM", len(models), len(read),
        len(models) - len(read), len(clean), clean[:12], data["readonly"]["unchanged"], len(data["problems"]),
        (" first problem: %s" % data["problems"][0]) if data["problems"] else ""))


def nq3_main():
    g = globals()
    root, repo, label, name = g.get("NQ_DIR"), g.get("NQ_REPO"), g.get("NQ_LABEL"), g.get("NQ_ANIMSET")
    if not root or not repo or not name or not label or not re.match(r"^NQ03-\d\d$", label):
        raise RuntimeError("Set NQ_DIR, NQ_REPO, NQ_LABEL (NQ03-NN) and NQ_ANIMSET first; see the docstring.")
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; it is never replaced. Use the next label." % path)
    data = nq3_observe(repo, label, name)
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    summary = nq3_summary(data, label)
    print(summary.encode("ascii", "replace") if sys.version_info[0] == 2 else summary)


nq3_main()
