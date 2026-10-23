# -*- coding: utf-8 -*-
"""Signed installed-software inventory (L-5; R2 E2).

The Character Tools software release installs, beside its menu scripts, a signed inventory of its
immutable shipping files:

    usermod\\scripts\\sfm\\mainmenu\\SFM Character Tools\\sfm_character_tools_inventory.json
    usermod\\scripts\\sfm\\mainmenu\\SFM Character Tools\\sfm_character_tools_inventory.sig

`.sig` is a raw 64-byte Ed25519 signature over the exact JSON bytes, made with a key trusted by this
updater (official.trusted_keys(): the same release trust as official data). The updater verifies the
signature, accepts only an authority profile it implements whose contract hash the inventory names
exactly, and hashes every listed file on disk. Mutable data (TXT, sidecars, manifest, presets, logs,
bytecode) is never listed and never checked here.

The updater never writes these files. A missing, unsigned, modified or unsupported installation has
unknown compatibility (not necessarily defective software): no data of any workflow -- published,
rebuilt from SFM's TXT or from another TXT -- is installed into it. Compiling and validating a TXT
(preparation) stay available; recovery of an already-started transaction is never gated.
"""
import hashlib
import json
import os
import re

from .. import official, w32
from ..messages import Stop
from . import profile as prof

OBJECT_TYPE = "sfm-character-tools-software-inventory"
INVENTORY_REL = os.path.join(*prof.CURRENT["installation_layout"]["software_inventory"].split("/"))
SIGNATURE_REL = INVENTORY_REL[:-len(".json")] + ".sig"
MAX_INVENTORY_BYTES = 256 * 1024
MAX_FILES = 512
MAX_FILE_BYTES = 64 * 1024 * 1024
_SAFE_TEXT = re.compile(r"^[A-Za-z0-9 ._+\-()]{1,64}$")
_PATH = re.compile(r"^scripts/[A-Za-z0-9 ._\-()/]{1,240}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
KEYS = ("schema", "object_type", "software", "software_version", "authority_profile", "profile_contract_sha256",
        "runtime_api_version", "runtime_build_id", "signing_key_id", "files")
FILE_KEYS = ("path", "role", "byte_length", "sha256")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _bad(key, reason, **details):
    return Stop("REFUSED", key, reason=reason, **details)


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key %r" % k)
        out[k] = v
    return out


def usermod_dir(layout):
    return os.path.dirname(layout.cfg)


def _read_bounded(path, limit):
    a = w32.attrs(path)
    if a == w32.INVALID_FILE_ATTRIBUTES:
        return None
    if a & (w32.FILE_ATTRIBUTE_DIRECTORY | w32.FILE_ATTRIBUTE_REPARSE_POINT):
        raise _bad("SOFTWARE_UNVERIFIED", "inventory entry is not a regular file", file=os.path.basename(path))
    try:
        with open(path, "rb") as f:
            data = f.read(limit + 1)
    except OSError as e:
        raise _bad("SOFTWARE_UNVERIFIED", "inventory unreadable", error=type(e).__name__)
    if len(data) > limit:
        raise _bad("SOFTWARE_UNVERIFIED", "inventory larger than allowed", file=os.path.basename(path))
    return data


def parse(data):
    """Strict, bounded parse of inventory bytes (no trust implied)."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise _bad("SOFTWARE_UNVERIFIED", "inventory has a byte-order mark")
    try:
        d = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeDecodeError, ValueError) as e:
        raise _bad("SOFTWARE_UNVERIFIED", "inventory is not valid JSON", error=str(e)[:200])
    if not isinstance(d, dict) or sorted(d) != sorted(KEYS):
        raise _bad("SOFTWARE_UNVERIFIED", "inventory keys invalid")
    problems = []
    if d["schema"] != 1 or isinstance(d["schema"], bool):
        problems.append("schema")
    if d["object_type"] != OBJECT_TYPE:
        problems.append("object_type")
    for k in ("software", "software_version", "authority_profile", "runtime_api_version", "runtime_build_id"):
        if not (isinstance(d[k], str) and _SAFE_TEXT.match(d[k])):
            problems.append(k)
    if not (isinstance(d["profile_contract_sha256"], str) and _HEX64.match(d["profile_contract_sha256"])):
        problems.append("profile_contract_sha256")
    if not (isinstance(d["signing_key_id"], str) and re.match(r"^ed25519-[0-9a-f]{16}$", d["signing_key_id"])):
        problems.append("signing_key_id")
    files = d["files"]
    if not (isinstance(files, list) and 1 <= len(files) <= MAX_FILES):
        problems.append("files")
        files = []
    seen = set()
    for f in files:
        if not (isinstance(f, dict) and sorted(f) == sorted(FILE_KEYS)):
            problems.append("files.entry")
            break
        p = f["path"]
        ok = (isinstance(p, str) and _PATH.match(p) and ".." not in p.split("/") and "//" not in p
              and not p.endswith("/") and p.lower() not in seen
              and isinstance(f["role"], str) and _SAFE_TEXT.match(f["role"])
              and isinstance(f["byte_length"], int) and not isinstance(f["byte_length"], bool)
              and 0 <= f["byte_length"] <= MAX_FILE_BYTES
              and isinstance(f["sha256"], str) and _HEX64.match(f["sha256"]))
        if not ok:
            problems.append("files.entry %r" % (p if isinstance(p, str) else "?")[:120])
            break
        seen.add(p.lower())
    if problems:
        raise _bad("SOFTWARE_UNVERIFIED", "inventory fields invalid", fields=problems)
    return d


def check_profile(d):
    """The inventory must name a profile this updater implements, by ID and exact contract hash."""
    pid = d["authority_profile"]
    p = prof.PROFILES.get(pid)
    if p is None:
        raise _bad("SOFTWARE_UNSUPPORTED", "authority profile not implemented by this updater", profile=pid,
                   supported=sorted(prof.PROFILES))
    if d["profile_contract_sha256"] != prof.PROFILE_SHA256[pid]:
        raise _bad("SOFTWARE_UNSUPPORTED", "profile contract differs from this updater's", profile=pid)
    if (d["runtime_api_version"], d["runtime_build_id"]) != (p["runtime"]["api_version"], p["runtime"]["build_id"]):
        raise _bad("SOFTWARE_UNSUPPORTED", "runtime API/build differs from the profile", profile=pid)
    roles = {f["role"] for f in d["files"]}
    missing = [r for r in prof.REQUIRED_ROLES if r not in roles]
    if missing:
        raise _bad("SOFTWARE_UNSUPPORTED", "inventory lacks required software roles", missing=missing)
    return p


def check_files(root, d):
    """Every listed file exists as a plain file under `root` with the signed length and SHA-256."""
    changed, missing = [], []
    for f in d["files"]:
        path = os.path.join(root, *f["path"].split("/"))
        a = w32.attrs(path)
        if a == w32.INVALID_FILE_ATTRIBUTES:
            missing.append(f["path"])
            continue
        if a & (w32.FILE_ATTRIBUTE_DIRECTORY | w32.FILE_ATTRIBUTE_REPARSE_POINT):
            changed.append(f["path"])
            continue
        try:
            if os.path.getsize(path) != f["byte_length"]:
                changed.append(f["path"])
                continue
            with open(path, "rb") as fh:
                if sha(fh.read(f["byte_length"] + 1)) != f["sha256"]:
                    changed.append(f["path"])
        except OSError:
            changed.append(f["path"])
    if missing:
        raise _bad("SOFTWARE_MODIFIED", "installed software file missing", missing=missing[:20])
    if changed:
        raise _bad("SOFTWARE_MODIFIED", "installed software file differs from the signed inventory",
                   changed=changed[:20])


def verify_installation(layout, accepted_profiles=None, keys=None):
    """Verify the installation's signed software inventory. Returns a summary; raises Stop
    (SOFTWARE_UNVERIFIED / SOFTWARE_UNSUPPORTED / SOFTWARE_MODIFIED) otherwise."""
    root = usermod_dir(layout)
    data = _read_bounded(os.path.join(root, INVENTORY_REL), MAX_INVENTORY_BYTES)
    sig = _read_bounded(os.path.join(root, SIGNATURE_REL), 64)
    if data is None or sig is None:
        raise _bad("SOFTWARE_UNVERIFIED", "no signed software inventory in this installation")
    d = parse(data)
    try:
        official.verify_signature(data, sig, d["signing_key_id"], keys=keys)
    except Stop as e:
        raise _bad("SOFTWARE_UNVERIFIED", "software inventory signature not verified",
                   **{k: v for k, v in e.details.items() if k != "reason"})
    check_profile(d)
    if accepted_profiles is not None and d["authority_profile"] not in accepted_profiles:
        raise _bad("SOFTWARE_UNSUPPORTED", "installed software profile not accepted by this data",
                   profile=d["authority_profile"], accepted=sorted(accepted_profiles))
    check_files(root, d)
    return {"software": d["software"], "software_version": d["software_version"],
            "authority_profile": d["authority_profile"], "profile_contract_sha256": d["profile_contract_sha256"],
            "inventory_sha256": sha(data), "files": len(d["files"]), "signing_key_id": d["signing_key_id"]}
