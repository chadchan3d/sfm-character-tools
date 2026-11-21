# -*- coding: utf-8 -*-
"""SFM Character Tools v1.1.0: assemble and verify the SIGNED release ZIP from the verified unsigned RC5 build and the
Owner's signature. Never reads, requests or handles a private key: signing is the Owner's step
(updater/release_tools/make_software_inventory.py sign, unchanged), and this tool only consumes its two output files.

Run with a Python that has the `cryptography` package (the updater's own signature verification needs it), with -I.

  package-signed RC.json SIGDIR
      SIGDIR holds exactly sfm_character_tools_inventory.json and .sig from the Owner's signing run. Refuses unless the
      unsigned RC5 build in Q/package is intact, the signed inventory is byte-identical to the verified unsigned
      inventory, and the signature verifies with the updater's PRODUCTION trust store (official.TRUSTED_KEYS, no test
      keys). Writes Q/signed/ (new): the signature copy, SFM.Character.Tools.v1.1.0.zip (deterministic, RC5's ZIP
      rules) and SIGNED_MANIFEST.json.
  verify-signed RC.json
      Read-only checks of Q/signed, from the ZIP's own bytes, written to Q/signed/VERIFY_SIGNED.json (exclusive):
        integrity   entry count, testzip, manifest, equality with the unsigned RC5 ZIP plus exactly the signature
        changes     against v1.0.0: README, CPM, inventory and signature replaced; the two registries added; nothing
                    removed; every other entry the exact v1.0.0 bytes
        identities  README, CPM, registries and inventory equal their pins
        signature   the updater's official.verify_signature with the production trust store; key id equals v1.0.0's
        updater     the updater's inventory.verify_installation (production keys) on the extracted usermod: signature,
                    profile and all 33 files
        version     the CPM's own prod_release_version reads 1.1.0 from the extracted signed inventory for this build
        installer   the Workshop installer's core.prepare accepts the SIGNED ZIP with v1.1.0 release constants derived
                    from it (temporary, in memory; release.py is not changed)
        rollback    v1.0.0's ZIP is the pinned archive and its CPM reads no registry

usage: python -I rc5_signed_tool.py RC.json package-signed SIGDIR | verify-signed
"""
from __future__ import print_function

import hashlib
import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rc5_tool as R5  # noqa: E402  (RC1's rc_tool with the RC5 README entry)

R, P, T = R5.R, R5.P, R5.T
REPO = R.REPO
sys.path.insert(0, os.path.join(REPO, "updater"))
from sfm_character_tools_updater import hooks, official  # noqa: E402
from sfm_character_tools_updater.compat import inventory  # noqa: E402

SIGNED_ZIP = "SFM.Character.Tools.v1.1.0.zip"
UNSIGNED_ZIP = "SFM.Character.Tools.v1.1.0-rc5-UNSIGNED.zip"
NAMES = ("sfm_character_tools_inventory.json", "sfm_character_tools_inventory.sig")


def h(b):
    return hashlib.sha256(b).hexdigest()


def production_keys():
    """The updater's production trust store only; refuse if anything extended it."""
    if hooks.extra_trusted_keys:
        raise SystemExit("REFUSED: extra trusted keys are registered in this process")
    return dict(official.TRUSTED_KEYS)


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        return dict((i.filename, z.read(i)) for i in z.infolist() if not i.is_dir()), bad


def cmd_package_signed(c, sigdir):
    out = P.q(c, "signed")
    problems = []
    if os.path.exists(out):
        problems.append("%s exists" % out)
    problems += P.package_problems(c)
    names = sorted(os.listdir(sigdir)) if os.path.isdir(sigdir) else []
    if names != sorted(NAMES):
        problems.append("%s must hold exactly %s (found %s)" % (sigdir, ", ".join(NAMES), names))
    P.refuse(problems, "PACKAGE-SIGNED")
    with open(os.path.join(sigdir, NAMES[0]), "rb") as f:
        inv = f.read()
    with open(os.path.join(sigdir, NAMES[1]), "rb") as f:
        sig = f.read()
    m, files = R.staged(c)
    if inv != files[P.INV_ENTRY] or h(inv) != c["pins"]["candidate_inventory_sha256"]:
        P.refuse(["the signed inventory %s is not the verified unsigned inventory %s" % (
            h(inv), c["pins"]["candidate_inventory_sha256"])], "PACKAGE-SIGNED")
    d = inventory.parse(inv)
    official.verify_signature(inv, sig, d["signing_key_id"], keys=production_keys())
    files = dict(files)
    files[P.SIG_ENTRY] = sig
    os.makedirs(os.path.join(out, "signature"))
    for n, data in ((NAMES[0], inv), (NAMES[1], sig)):
        with open(os.path.join(out, "signature", n), "xb") as f:
            f.write(data)
    zpath = os.path.join(out, SIGNED_ZIP)
    P.write_zip(zpath, files)
    rows = [{"path": n, "sha256": h(files[n]), "byte_length": len(files[n])} for n in sorted(files)]
    manifest = {"format": "SCT-V110-signed-package-v1", "status": "SIGNED v1.1.0 release package",
                "software_version": d["software_version"], "zip": SIGNED_ZIP, "zip_sha256": T.sha(zpath),
                "entries": len(rows), "unsigned_zip_sha256": m["zip_sha256"],
                "inventory_sha256": h(inv), "signature_sha256": h(sig), "signing_key_id": d["signing_key_id"],
                "files": rows}
    T.write_json(os.path.join(out, "SIGNED_MANIFEST.json"), manifest, exclusive=True)
    print("PACKAGED-SIGNED: %s %s (%d entries); inventory %s; signature %s verified with the production key %s" % (
        SIGNED_ZIP, manifest["zip_sha256"], len(rows), h(inv), h(sig), d["signing_key_id"]))


def check_installer(c, zpath, files):
    sys.path.insert(0, REPO)
    release = importlib.import_module("workshop_installer.release")
    core = importlib.import_module("workshop_installer.core")
    saved = dict((k, getattr(release, k)) for k in ("VERSION", "ARCHIVE", "SHA256", "ARCHIVE_ENTRIES",
                                                     "INVENTORY_ENTRIES", "PATHS"))
    saved_core = core.RELEASE_SHA256
    tmp = tempfile.mkdtemp(prefix="sct_v110_signed_installer_dryrun_")
    out = {}
    try:
        mapped = set(r for r in (core._map_member(n) for n in files) if r is not None)
        new = set(release.PATHS) | set(n[len("usermod/"):] for n in (P.LIB + r for r in P.REGISTRIES))
        out["paths_mapped_equal_v100_plus_registries"] = mapped == new
        release.VERSION, release.ARCHIVE = c["pins"]["software_version"], os.path.basename(zpath)
        release.SHA256 = core.RELEASE_SHA256 = core.digest_file(zpath)
        release.ARCHIVE_ENTRIES, release.INVENTORY_ENTRIES = len(files), len(R.spec(c)["files"])
        release.PATHS = tuple(sorted(new))
        helper = os.path.join(tmp, "SCT_Setup_placeholder.exe")
        with open(helper, "xb") as f:
            f.write(b"placeholder setup executable for the dry run")
        prepared = core.prepare(zpath, helper)
        try:
            out["prepare"] = True
            out["prepared_files"] = len(prepared.files)
            out["cpm_prepared"] = prepared.files.get(P.CPM_ENTRY[len("usermod/"):]) == h(files[P.CPM_ENTRY])
            out["registries_prepared"] = all(("scripts/SFM Character Tools/" + r) in prepared.files
                                             for r in P.REGISTRIES)
            out["signature_prepared"] = prepared.files.get(P.SIG_ENTRY[len("usermod/"):]) == h(files[P.SIG_ENTRY])
        finally:
            prepared.close()
        out["pass"] = all(out[k] for k in ("paths_mapped_equal_v100_plus_registries", "prepare", "cpm_prepared",
                                           "registries_prepared", "signature_prepared"))
    except Exception as e:
        out.update(error="%s: %s" % (type(e).__name__, str(e)[:300]), **{"pass": False})
    finally:
        for k, v in saved.items():
            setattr(release, k, v)
        core.RELEASE_SHA256 = saved_core
        shutil.rmtree(tmp, True)
    return out


class _Layout(object):
    def __init__(self, usermod):
        self.cfg = os.path.join(usermod, "cfg")


def cmd_verify_signed(c):
    out_dir = P.q(c, "signed")
    path = os.path.join(out_dir, "VERIFY_SIGNED.json")
    if os.path.exists(path):
        raise SystemExit("REFUSED: %s exists" % path)
    pins = c["pins"]
    m = T.read_json(os.path.join(out_dir, "SIGNED_MANIFEST.json"))
    zpath = os.path.join(out_dir, SIGNED_ZIP)
    files, bad = read_zip(zpath)
    unsigned, ubad = read_zip(P.q(c, "package", UNSIGNED_ZIP))
    v100 = P.read_zip(c)
    V = {"format": "SCT-V110-signed-verify-v1", "tool_sha256": T.sha(os.path.abspath(__file__)),
         "zip": SIGNED_ZIP, "zip_sha256": T.sha(zpath)}

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
    want_changed = sorted([R5.README_ENTRY, P.CPM_ENTRY, P.INV_ENTRY, P.SIG_ENTRY])
    want_added = sorted(P.LIB + r for r in P.REGISTRIES)
    V["changes"] = {"changed": changed, "added": added, "removed": removed,
                    "v100_entries_kept_exact": len(files) - len(changed) - len(added)}
    V["changes"]["pass"] = changed == want_changed and added == want_added and not removed

    ids = {"readme": (files[R5.README_ENTRY], pins["readme_sha256"]),
           "cpm": (files[P.CPM_ENTRY], pins["candidate_cpm_sha256"]),
           "pose_registry": (files[P.LIB + P.REGISTRIES[0]], pins["profile_sha256"]),
           "body_registry": (files[P.LIB + P.REGISTRIES[1]], pins["body_profile_sha256"]),
           "inventory": (files[P.INV_ENTRY], pins["candidate_inventory_sha256"])}
    V["identities"] = dict((k, {"sha256": h(b), "pinned": h(b) == pin}) for k, (b, pin) in ids.items())
    V["identities"]["readme_byte_length"] = len(files[R5.README_ENTRY])
    V["identities"]["pass"] = all(v["pinned"] for k, v in V["identities"].items() if isinstance(v, dict))

    inv, sig = files[P.INV_ENTRY], files[P.SIG_ENTRY]
    d = inventory.parse(inv)
    v100_key = json.loads(v100[P.INV_ENTRY].decode("utf-8"))["signing_key_id"]
    out = {"signing_key_id": d["signing_key_id"], "v100_signing_key_id": v100_key, "signature_bytes": len(sig),
           "trust_store": sorted(production_keys())}
    try:
        official.verify_signature(inv, sig, d["signing_key_id"], keys=production_keys())
        out["verified"] = True
    except Exception as e:
        out.update(verified=False, error="%s: %s" % (type(e).__name__, str(e)[:300]))
    out["pass"] = out["verified"] and d["signing_key_id"] == v100_key and d["signing_key_id"] in out["trust_store"]
    V["signature"] = out

    tmp = tempfile.mkdtemp(prefix="sct_v110_signed_extract_")
    try:
        for n, b in files.items():
            if n.startswith("usermod/"):
                dst = os.path.join(tmp, *n.split("/"))
                if not os.path.isdir(os.path.dirname(dst)):
                    os.makedirs(os.path.dirname(dst))
                with open(dst, "xb") as f:
                    f.write(b)
        usermod = os.path.join(tmp, "usermod")
        try:
            s = inventory.verify_installation(_Layout(usermod), keys=production_keys())
            V["updater"] = dict(s, **{"pass": s["software_version"] == pins["software_version"] and
                                      s["files"] == len(R.spec(c)["files"]) and
                                      s["inventory_sha256"] == pins["candidate_inventory_sha256"]})
        except Exception as e:
            V["updater"] = {"error": "%s: %s" % (type(e).__name__, str(e)[:300]), "pass": False}
        fn = R.release_version_function(files[P.CPM_ENTRY])
        invp = os.path.join(tmp, *P.INV_ENTRY.split("/"))
        mine, other = fn(inventory_path=invp, build_sha256=h(files[P.CPM_ENTRY])), fn(inventory_path=invp,
                                                                                         build_sha256="0" * 64)
        V["version"] = {"this_build": mine, "another_build": other,
                        "pass": mine == pins["software_version"] and other is None}
    finally:
        shutil.rmtree(tmp, True)

    V["installer"] = check_installer(c, zpath, files)

    v100_cpm = v100[P.CPM_ENTRY]
    V["rollback"] = {"v100_zip_pinned": T.sha(P.p(c, "V100_ZIP")) == pins["v100_zip_sha256"],
                     "v100_cpm": h(v100_cpm),
                     "v100_cpm_reads_no_registry": not any(r.encode("ascii") in v100_cpm for r in P.REGISTRIES)}
    V["rollback"]["pass"] = (V["rollback"]["v100_zip_pinned"] and V["rollback"]["v100_cpm_reads_no_registry"] and
                             V["rollback"]["v100_cpm"] == pins["v100_cpm_sha256"])

    keys = ("integrity", "changes", "identities", "signature", "updater", "version", "installer", "rollback")
    V["pass"] = all(V[k]["pass"] for k in keys)
    T.write_json(path, V, exclusive=True)
    print(json.dumps(V, indent=1))
    print("SIGNED VERIFY %s" % ("PASS" if V["pass"] else "FAIL"))
    return 0 if V["pass"] else 1


def main(argv):
    if len(argv) == 4 and argv[2] == "package-signed":
        return cmd_package_signed(P.load(argv[1]), argv[3]) or 0
    if len(argv) == 3 and argv[2] == "verify-signed":
        return cmd_verify_signed(P.load(argv[1]))
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
