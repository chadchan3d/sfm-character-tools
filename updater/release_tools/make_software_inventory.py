# -*- coding: utf-8 -*-
"""DEVELOPMENT-SIDE producer of the signed Character Tools software inventory (L-5; R2 E2). Not shipped.

  make_software_inventory.py stage --spec SPEC --out USERMOD
      Copies every file of the software spec from the repository into USERMOD (a new or empty
      folder outside the repository) at its installed path, refusing any byte that differs from the
      qualified identity recorded in the spec.

  make_software_inventory.py sign --spec SPEC --root USERMOD --software-version V --private KEY.pem
          [--passphrase-file F] --out DIR
      Hashes the installed software under USERMOD (the `usermod` folder of an installation or a
      release staging tree), refuses anything that is not the qualified identity, and writes
      sfm_character_tools_inventory.json / .sig into the NEW folder DIR. The inventory names the
      updater's authority profile and its exact contract hash, and the signature covers the exact
      JSON bytes. The private key must be outside the repository (R2 D3).

The spec (release_tools/character_tools_software_v1.json) lists the immutable software files with
their roles and qualified SHA-256. Mutable data (TXT, sidecars, manifest, presets, logs, bytecode)
is never listed.
"""
import argparse
import hashlib
import json
import os
import sys

UPDATER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(UPDATER)
sys.path.insert(0, UPDATER)

from sfm_character_tools_updater import official, w32  # noqa: E402
from sfm_character_tools_updater.compat import inventory, profile  # noqa: E402


def _norm(p):
    return os.path.normcase(os.path.abspath(p)).rstrip("\\")


def _inside_repo(p):
    r = _norm(REPO)
    return _norm(p) == r or _norm(p).startswith(r + "\\")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _write_new(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok, err = w32.write_new_file(path, data)
    if not ok:
        raise SystemExit("write failed %s: %s" % (path, w32.ename(err)))


def load_spec(path):
    spec = json.load(open(path, encoding="utf-8"))
    roles = {f["role"] for f in spec["files"]}
    missing = [r for r in profile.REQUIRED_ROLES if r not in roles]
    if missing or spec["authority_profile"] not in profile.PROFILES:
        raise SystemExit("spec incomplete: roles %s profile %s" % (missing, spec["authority_profile"]))
    return spec


def stage(a):
    if _inside_repo(a.out):
        raise SystemExit("refused: staging must be outside the repository")
    spec = load_spec(a.spec)
    for f in spec["files"]:
        data = open(os.path.join(REPO, *f["source"].split("/")), "rb").read()
        if sha(data) != f["sha256"] or len(data) != f["byte_length"]:
            raise SystemExit("refused: repository source is not the qualified identity: %s" % f["source"])
        _write_new(os.path.join(a.out, *f["path"].split("/")), data)
    print(json.dumps({"staged": len(spec["files"]), "root": a.out}))


def canonical(d):
    return (json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def sign(a):
    from cryptography.hazmat.primitives import serialization
    for p in (a.private, a.out):
        if _inside_repo(p):
            raise SystemExit("refused: keys and signed output stay outside the repository")
    spec = load_spec(a.spec)
    entries = []
    for f in spec["files"]:
        data = open(os.path.join(a.root, *f["path"].split("/")), "rb").read()
        if sha(data) != f["sha256"] or len(data) != f["byte_length"]:
            raise SystemExit("refused: installed file is not the qualified identity: %s" % f["path"])
        entries.append({"path": f["path"], "role": f["role"], "byte_length": len(data), "sha256": sha(data)})
    pw = open(a.passphrase_file, "rb").read().strip() if a.passphrase_file else None
    priv = serialization.load_pem_private_key(open(a.private, "rb").read(), password=pw)
    raw = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    pid = spec["authority_profile"]
    p = profile.PROFILES[pid]
    d = {"schema": 1, "object_type": inventory.OBJECT_TYPE, "software": spec["software"],
         "software_version": a.software_version, "authority_profile": pid,
         "profile_contract_sha256": profile.PROFILE_SHA256[pid],
         "runtime_api_version": p["runtime"]["api_version"], "runtime_build_id": p["runtime"]["build_id"],
         "signing_key_id": official.key_id_for(raw), "files": entries}
    db = canonical(d)
    sig = priv.sign(db)
    inventory.parse(db)
    official.verify_signature(db, sig, d["signing_key_id"], keys={d["signing_key_id"]: raw.hex()})
    os.mkdir(a.out)
    _write_new(os.path.join(a.out, os.path.basename(inventory.INVENTORY_REL)), db)
    _write_new(os.path.join(a.out, os.path.basename(inventory.SIGNATURE_REL)), sig)
    print(json.dumps({"inventory_sha256": sha(db), "files": len(entries), "key_id": d["signing_key_id"],
                      "profile": pid, "profile_contract_sha256": d["profile_contract_sha256"]}))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="make_software_inventory.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--spec", required=True)
    s.add_argument("--out", required=True)
    g = sub.add_parser("sign")
    g.add_argument("--spec", required=True)
    g.add_argument("--root", required=True)
    g.add_argument("--software-version", required=True)
    g.add_argument("--private", required=True)
    g.add_argument("--passphrase-file")
    g.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"stage": stage, "sign": sign}[a.cmd](a)


if __name__ == "__main__":
    main()
