# -*- coding: utf-8 -*-
"""SFM Character Tools v1.1.0, final release package: RC5 with the Owner-approved v1.1.0 optional-button README
(the simplified README of the public v1.0.0 download, updated for v1.1.0). Re-uses the Owner's existing signature:
the optional README sits outside usermod/, so it is not an inventory file and the signed inventory is unchanged.
Never reads, requests or handles a private key.

Built on RC1's rc_tool.py and RC5's rc5_tool.py / rc5_signed_tool.py, all unchanged. This file adds only:
  - README.txt from this folder (the approved main README, byte-identical to release/v1.1.0-rc5/README.txt);
  - "OPTIONAL - CPM Button/README.txt" from this folder as a sixth candidate entry, pinned by opt_readme_sha256;
  - the expected changes, identities and rollback counts for that entry; the final ZIP names.

Run with a Python that has `cryptography` (the updater's signature verification), with -I.

  package         unsigned build in Q/package (RC5's packager with both README entries)
  verify          RC VERIFY of that build, Q/RC_VERIFY.json (package, updater, version, installer, rollback)
  package-signed  SIGDIR: the Owner's two signing outputs; Q/signed/SFM.Character.Tools.v1.1.0.zip (rc5_signed_tool)
  verify-signed   Q/signed/VERIFY_SIGNED.json: integrity, changes, identities, signature, updater, version,
                  installer, rollback (rc5_signed_tool's checks with this release's expected changes)
  assets          Q/signed/release_assets/: SHA256SUMS.txt and ZIP_CONTENTS_SHA256.txt in v1.0.0's format

usage: python -I v110_tool.py RC.json package | verify | package-signed SIGDIR | verify-signed | assets
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v1.1.0-rc5"))
import rc5_tool as R5  # noqa: E402
import rc5_signed_tool as S  # noqa: E402

R, P, T = R5.R, R5.P, R5.T
OPT_ENTRY = "OPTIONAL - CPM Button/README.txt"
OPT_SOURCE = os.path.join(HERE, "OPTIONAL - CPM Button", "README.txt")
UNSIGNED_ZIP = "SFM.Character.Tools.v1.1.0-UNSIGNED.zip"
DOCS = (R5.README_ENTRY, OPT_ENTRY)

R5.README_SOURCE = os.path.join(HERE, "README.txt")
P.ZIP_NAME = UNSIGNED_ZIP
S.UNSIGNED_ZIP = UNSIGNED_ZIP

_rc5_sources = P.candidate_sources


def candidate_sources(c):
    return _rc5_sources(c) + [(OPT_ENTRY, OPT_SOURCE, c["pins"]["opt_readme_sha256"])]


P.candidate_sources = candidate_sources

_rc5_package = P.cmd_package


def cmd_package(c):
    write_json = T.write_json

    def manifest_writer(path, data, exclusive=False):
        if isinstance(data, dict) and data.get("format") == "F01-PS2-package-v1":
            data["replaced"] = sorted(data["replaced"] + [OPT_ENTRY])
        return write_json(path, data, exclusive=exclusive)

    T.write_json = manifest_writer
    try:
        return _rc5_package(c)
    finally:
        T.write_json = write_json


P.cmd_package = cmd_package


def check_package(c, Rv):
    files, v100 = R5._check_package(c, Rv)          # RC1's own check
    out = Rv["package"]
    want = (sorted([P.CPM_ENTRY, P.INV_ENTRY] + list(DOCS)), sorted(P.LIB + n for n in P.REGISTRIES), [P.SIG_ENTRY])
    for key, entry, pin in (("readme", R5.README_ENTRY, "readme_sha256"), ("opt_readme", OPT_ENTRY,
                                                                           "opt_readme_sha256")):
        b = files.get(entry)
        out[key + "_sha256"] = R.sha_bytes(b) if b is not None else None
        out[key + "_is_approved"] = out[key + "_sha256"] == c["pins"][pin]
    out["pass"] = (not out["problems"] and (out["changed"], out["added"], out["removed"]) == want and
                   out["readme_is_approved"] and out["opt_readme_is_approved"])
    return files, v100


R.check_package = check_package


def check_rollback(c, Rv, files, v100):
    R5._check_rollback(c, Rv, dict((n, b) for n, b in files.items() if n not in DOCS), v100)
    Rv["rollback"]["readmes_replaced"] = all(n in v100 and files.get(n) != v100[n] for n in DOCS)


R.check_rollback = check_rollback


def h(b):
    return hashlib.sha256(b).hexdigest()


def cmd_verify_signed(c):
    """rc5_signed_tool's verify-signed checks, with this release's expected changes and the optional README."""
    out_dir = P.q(c, "signed")
    path = os.path.join(out_dir, "VERIFY_SIGNED.json")
    if os.path.exists(path):
        raise SystemExit("REFUSED: %s exists" % path)
    pins = c["pins"]
    m = T.read_json(os.path.join(out_dir, "SIGNED_MANIFEST.json"))
    zpath = os.path.join(out_dir, S.SIGNED_ZIP)
    files, bad = S.read_zip(zpath)
    unsigned, ubad = S.read_zip(P.q(c, "package", UNSIGNED_ZIP))
    v100 = P.read_zip(c)
    V = {"format": "SCT-V110-signed-verify-v1", "tool_sha256": T.sha(os.path.abspath(__file__)),
         "rc5_signed_tool_sha256": T.sha(os.path.abspath(S.__file__)), "zip": S.SIGNED_ZIP,
         "zip_sha256": T.sha(zpath)}

    rows = dict((r["path"], r["sha256"]) for r in m["files"])
    V["integrity"] = {"entries": len(files), "testzip": bad, "manifest_zip_sha256_matches": m["zip_sha256"] ==
                      V["zip_sha256"], "manifest_rows_match": rows == dict((n, h(b)) for n, b in files.items()),
                      "unsigned_zip_sha256": T.sha(P.q(c, "package", UNSIGNED_ZIP)),
                      "equals_unsigned_plus_signature": ubad is None and set(files) == set(unsigned) | {P.SIG_ENTRY}
                      and all(files[n] == unsigned[n] for n in unsigned)}
    V["integrity"]["pass"] = (bad is None and len(files) == len(v100) + 2 and
                              V["integrity"]["manifest_zip_sha256_matches"] and V["integrity"]["manifest_rows_match"]
                              and V["integrity"]["equals_unsigned_plus_signature"])

    changed = sorted(n for n in files if n in v100 and files[n] != v100[n])
    added = sorted(n for n in files if n not in v100)
    removed = sorted(n for n in v100 if n not in files)
    V["changes"] = {"changed": changed, "added": added, "removed": removed,
                    "v100_entries_kept_exact": len(files) - len(changed) - len(added)}
    V["changes"]["pass"] = (changed == sorted(list(DOCS) + [P.CPM_ENTRY, P.INV_ENTRY, P.SIG_ENTRY]) and
                            added == sorted(P.LIB + r for r in P.REGISTRIES) and not removed)

    ids = {"readme": (files[R5.README_ENTRY], pins["readme_sha256"]),
           "opt_readme": (files[OPT_ENTRY], pins["opt_readme_sha256"]),
           "cpm": (files[P.CPM_ENTRY], pins["candidate_cpm_sha256"]),
           "pose_registry": (files[P.LIB + P.REGISTRIES[0]], pins["profile_sha256"]),
           "body_registry": (files[P.LIB + P.REGISTRIES[1]], pins["body_profile_sha256"]),
           "inventory": (files[P.INV_ENTRY], pins["candidate_inventory_sha256"]),
           "signature": (files[P.SIG_ENTRY], pins["signature_sha256"])}
    V["identities"] = dict((k, {"sha256": h(b), "pinned": h(b) == pin}) for k, (b, pin) in ids.items())
    V["identities"]["pass"] = all(v["pinned"] for v in V["identities"].values())

    inv, sig = files[P.INV_ENTRY], files[P.SIG_ENTRY]
    d = S.inventory.parse(inv)
    v100_key = json.loads(v100[P.INV_ENTRY].decode("utf-8"))["signing_key_id"]
    out = {"signing_key_id": d["signing_key_id"], "v100_signing_key_id": v100_key, "signature_bytes": len(sig),
           "trust_store": sorted(S.production_keys())}
    try:
        S.official.verify_signature(inv, sig, d["signing_key_id"], keys=S.production_keys())
        out["verified"] = True
    except Exception as e:
        out.update(verified=False, error="%s: %s" % (type(e).__name__, str(e)[:300]))
    out["pass"] = out["verified"] and d["signing_key_id"] == v100_key and d["signing_key_id"] in out["trust_store"]
    V["signature"] = out

    tmp = tempfile.mkdtemp(prefix="sct_v110_final_extract_")
    try:
        for n, b in files.items():
            if n.startswith("usermod/"):
                dst = os.path.join(tmp, *n.split("/"))
                if not os.path.isdir(os.path.dirname(dst)):
                    os.makedirs(os.path.dirname(dst))
                with open(dst, "xb") as f:
                    f.write(b)
        try:
            s = S.inventory.verify_installation(S._Layout(os.path.join(tmp, "usermod")), keys=S.production_keys())
            V["updater"] = dict(s, **{"pass": s["software_version"] == pins["software_version"] and
                                      s["files"] == len(R.spec(c)["files"]) and
                                      s["inventory_sha256"] == pins["candidate_inventory_sha256"]})
        except Exception as e:
            V["updater"] = {"error": "%s: %s" % (type(e).__name__, str(e)[:300]), "pass": False}
        fn = R.release_version_function(files[P.CPM_ENTRY])
        invp = os.path.join(tmp, *P.INV_ENTRY.split("/"))
        mine = fn(inventory_path=invp, build_sha256=h(files[P.CPM_ENTRY]))
        other = fn(inventory_path=invp, build_sha256="0" * 64)
        V["version"] = {"this_build": mine, "another_build": other,
                        "pass": mine == pins["software_version"] and other is None}
    finally:
        shutil.rmtree(tmp, True)

    V["installer"] = S.check_installer(c, zpath, files)
    v100_cpm = v100[P.CPM_ENTRY]
    V["rollback"] = {"v100_zip_pinned": T.sha(P.p(c, "V100_ZIP")) == pins["v100_zip_sha256"], "v100_cpm": h(v100_cpm),
                     "v100_cpm_reads_no_registry": not any(r.encode("ascii") in v100_cpm for r in P.REGISTRIES)}
    V["rollback"]["pass"] = (V["rollback"]["v100_zip_pinned"] and V["rollback"]["v100_cpm_reads_no_registry"] and
                             V["rollback"]["v100_cpm"] == pins["v100_cpm_sha256"])
    keys = ("integrity", "changes", "identities", "signature", "updater", "version", "installer", "rollback")
    V["pass"] = all(V[k]["pass"] for k in keys)
    T.write_json(path, V, exclusive=True)
    print(json.dumps(V, indent=1))
    print("SIGNED VERIFY %s" % ("PASS" if V["pass"] else "FAIL"))
    return 0 if V["pass"] else 1


def cmd_assets(c):
    """SHA256SUMS.txt and ZIP_CONTENTS_SHA256.txt in v1.0.0's format (LF; contents sorted by entry name)."""
    out = P.q(c, "signed", "release_assets")
    if os.path.exists(out):
        raise SystemExit("REFUSED: %s exists" % out)
    zpath = P.q(c, "signed", S.SIGNED_ZIP)
    files, bad = S.read_zip(zpath)
    if bad is not None:
        raise SystemExit("REFUSED: the signed ZIP fails testzip")
    os.makedirs(out)
    zs = T.sha(zpath)
    with open(os.path.join(out, "SHA256SUMS.txt"), "xb") as f:
        f.write(("%s  %s\n" % (zs, S.SIGNED_ZIP)).encode("ascii"))
    with open(os.path.join(out, "ZIP_CONTENTS_SHA256.txt"), "xb") as f:
        f.write("".join("%s  %s\n" % (h(files[n]), n) for n in sorted(files)).encode("utf-8"))
    print("ASSETS: %s (ZIP %s, %d entries)" % (out, zs, len(files)))


def main(argv):
    if len(argv) == 4 and argv[2] == "package-signed":
        return S.cmd_package_signed(P.load(argv[1]), argv[3]) or 0
    commands = {"package": lambda c: P.cmd_package(c), "verify": R.cmd_verify, "verify-signed": cmd_verify_signed,
                "assets": cmd_assets}
    if len(argv) != 3 or argv[2] not in commands:
        raise SystemExit(__doc__)
    return commands[argv[2]](P.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
