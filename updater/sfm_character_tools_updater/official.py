# -*- coding: utf-8 -*-
"""Official data packages (R2 D1-D5): strict descriptor, Ed25519 authenticity over the exact
`release.json` bytes, exact payload identities, compatibility, and the remembered release
sequence (high-water mark).

A local package is a directory holding exactly the five R2 D1 files:
    release.json, release.sig, sfm_defaultanimationgroups.txt, manifest.json,
    sfm_master_0_<sidecar-sha256>.sfmsidecar
`release.sig` is the raw 64-byte Ed25519 signature of the exact `release.json` bytes.

Trust: only public keys embedded in TRUSTED_KEYS are trusted. The shipping updater embeds exactly
one key, the owner's production public key (R2 D3); the private key stays with the owner. The
same key signs the installed-software inventory. Test keys are trusted only through the
test-only seam `hooks.extra_trusted_keys`, never through this table.

Signature verification uses the maintained `cryptography` library (R2 D2); no new protocol.
"""
import hashlib
import json
import os
import re

from . import hooks, w32
from .layout import MASTER_NAME, SIDECAR_RE
from .messages import Stop

UPDATER_CONTRACT = 1
# The official repository (owner-confirmed permanent identity, 2026-10-17). Checked exactly: a
# descriptor naming any other repository, including an earlier name of this one, is refused.
REPOSITORY = "chadchan3d/sfm-character-tools"
OBJECT_TYPE = "sfm-character-tools-data"
CHANNEL = "stable"
# L-2 authority profile identifier: sidecar format 0 / semantics 0, FINAL R3-A2B validator and
# provider, runtime API 1.0.0-b2a, build package-boundary-corrected-2026-09-22. The full signed
# profile and installed-software inventory are L-5 (R2 E2-E3). Profile 2 (2026-10-23) is profile 1 with the
# menu commands and inventory under scripts/sfm/mainmenu/SFM Character Tools and the internal library under
# scripts/SFM Character Tools; packages name profile 2.
AUTHORITY_PROFILE = "sct-authority-profile-2"
SUPPORTED_PROFILES = {AUTHORITY_PROFILE}
SIDECAR_CONTRACT = {"format": 0, "semantics": 0}

# Production trust store: key id -> raw Ed25519 public key (hex). Exactly the owner's production
# key (owner-approved, 2026-10-22); never a test key.
TRUSTED_KEYS = {
    "ed25519-5d879134807dff6d": "7f2b9a53fcad0a7818ef5be52ed9fdc8826ac51e3923db30461ddbc96539dba1",
}

DESCRIPTOR = "release.json"
SIGNATURE = "release.sig"
MAX_DESCRIPTOR_BYTES = 16 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SIDECAR_BYTES = 256 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
RELEASE_LOG = "official_releases.log"

_SAFE_TEXT = re.compile(r"^[A-Za-z0-9 ._+\-()]{1,64}$")
_SAFE_TAG = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
_KEY_ID = re.compile(r"^ed25519-[0-9a-f]{16}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key_id_for(public_raw):
    return "ed25519-" + sha(public_raw)[:16]


def trusted_keys():
    keys = dict(TRUSTED_KEYS)
    if hooks.extra_trusted_keys:
        keys.update(hooks.extra_trusted_keys)
    return keys


def _bad(message_key, reason, **details):
    return Stop("REFUSED", message_key, reason=reason, **details)


# ---------------------------------------------------------------- descriptor
class _Dup(ValueError):
    pass


def _no_dups(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise _Dup(k)
        out[k] = v
    return out


def _reject_constant(name):
    raise ValueError("non-finite number %s" % name)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _exact_keys(obj, keys, where):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise _bad("PACKAGE_INVALID", "descriptor fields are not exactly the supported set", where=where,
                   have=sorted(obj) if isinstance(obj, dict) else type(obj).__name__, want=sorted(keys))


def parse_descriptor(data):
    """Bounded, strict parse. Returns the descriptor object; never trusts it by itself."""
    if len(data) > MAX_DESCRIPTOR_BYTES:
        raise _bad("PACKAGE_INVALID", "descriptor too large", size=len(data))
    if data.startswith(b"\xef\xbb\xbf"):
        raise _bad("PACKAGE_INVALID", "descriptor has a byte-order mark")
    try:
        d = json.loads(data.decode("utf-8"), object_pairs_hook=_no_dups, parse_constant=_reject_constant)
    except _Dup as e:
        raise _bad("PACKAGE_INVALID", "duplicate descriptor key", field=str(e))
    except (UnicodeDecodeError, ValueError) as e:
        raise _bad("PACKAGE_INVALID", "descriptor is not valid JSON", error=str(e)[:200])
    _exact_keys(d, ("schema", "object_type", "repository", "channel", "sequence", "data_version", "release_tag",
                    "source_commit", "published_at", "minimum_updater_contract", "compatible_authority_profiles",
                    "sidecar_contract", "compiler_build", "signing_key_id", "files"), "descriptor")
    problems = []
    if not (_int(d["schema"]) and d["schema"] == 1):
        problems.append("schema")
    if d["object_type"] != OBJECT_TYPE:
        problems.append("object_type")
    if d["repository"] != REPOSITORY:
        problems.append("repository")
    if d["channel"] != CHANNEL:
        problems.append("channel")
    if not (_int(d["sequence"]) and 1 <= d["sequence"] <= 2 ** 31 - 1):
        problems.append("sequence")
    if not (isinstance(d["data_version"], str) and _SAFE_TEXT.match(d["data_version"])):
        problems.append("data_version")
    if not (isinstance(d["release_tag"], str) and _SAFE_TAG.match(d["release_tag"])):
        problems.append("release_tag")
    if not (isinstance(d["source_commit"], str) and _HEX40.match(d["source_commit"])):
        problems.append("source_commit")
    if not (isinstance(d["published_at"], str) and _UTC.match(d["published_at"])):
        problems.append("published_at")
    if not (_int(d["minimum_updater_contract"]) and d["minimum_updater_contract"] >= 1):
        problems.append("minimum_updater_contract")
    profs = d["compatible_authority_profiles"]
    if not (isinstance(profs, list) and 1 <= len(profs) <= 8
            and all(isinstance(p, str) and _SAFE_TAG.match(p) for p in profs) and len(set(profs)) == len(profs)):
        problems.append("compatible_authority_profiles")
    sc = d["sidecar_contract"]
    _exact_keys(sc, ("format", "semantics"), "sidecar_contract")
    if not (_int(sc["format"]) and _int(sc["semantics"])):
        problems.append("sidecar_contract")
    if not (isinstance(d["compiler_build"], str) and _SAFE_TAG.match(d["compiler_build"])):
        problems.append("compiler_build")
    if not (isinstance(d["signing_key_id"], str) and _KEY_ID.match(d["signing_key_id"])):
        problems.append("signing_key_id")
    files = d["files"]
    _exact_keys(files, ("master", "manifest", "sidecar"), "files")
    for role, limit in (("master", MAX_SOURCE_BYTES), ("manifest", MAX_MANIFEST_BYTES), ("sidecar", MAX_SIDECAR_BYTES)):
        f = files[role]
        _exact_keys(f, ("name", "byte_length", "sha256"), "files." + role)
        if not (isinstance(f["name"], str) and _int(f["byte_length"]) and 0 < f["byte_length"] <= limit
                and isinstance(f["sha256"], str) and _HEX64.match(f["sha256"])):
            problems.append("files." + role)
    if not problems:
        if files["master"]["name"] != MASTER_NAME:
            problems.append("files.master.name")
        if files["manifest"]["name"] != "manifest.json":
            problems.append("files.manifest.name")
        sn = files["sidecar"]["name"]
        if not SIDECAR_RE.match(sn) or sn != "sfm_master_0_%s.sfmsidecar" % files["sidecar"]["sha256"]:
            problems.append("files.sidecar.name")
    if problems:
        raise _bad("PACKAGE_INVALID", "descriptor fields invalid", fields=problems)
    return d


def verify_signature(descriptor_bytes, signature, key_id, keys=None):
    """Ed25519 over the exact descriptor bytes, with a trusted key chosen by key id only."""
    keys = trusted_keys() if keys is None else keys
    pub_hex = keys.get(key_id)
    if pub_hex is None:
        raise _bad("PACKAGE_UNTRUSTED", "signing key is not trusted", signing_key_id=key_id)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as e:
        raise Stop("REFUSED", "DEPENDENCY", reason="signature library unavailable", error=str(e))
    raw = bytes.fromhex(pub_hex)
    if len(raw) != 32 or key_id_for(raw) != key_id:
        raise _bad("PACKAGE_UNTRUSTED", "trusted key entry is inconsistent", signing_key_id=key_id)
    if len(signature) != 64:
        raise _bad("PACKAGE_UNTRUSTED", "signature is not a 64-byte Ed25519 signature", size=len(signature))
    try:
        Ed25519PublicKey.from_public_bytes(raw).verify(signature, descriptor_bytes)
    except InvalidSignature:
        raise _bad("PACKAGE_UNTRUSTED", "signature does not verify", signing_key_id=key_id)


def check_compatibility(d):
    if d["minimum_updater_contract"] > UPDATER_CONTRACT:
        raise _bad("PACKAGE_NEEDS_NEWER", "package needs a newer updater contract",
                   minimum_updater_contract=d["minimum_updater_contract"], supported=UPDATER_CONTRACT)
    if not SUPPORTED_PROFILES.intersection(d["compatible_authority_profiles"]):
        raise _bad("PACKAGE_INCOMPATIBLE", "no supported authority profile",
                   profiles=d["compatible_authority_profiles"], supported=sorted(SUPPORTED_PROFILES))
    if d["sidecar_contract"] != SIDECAR_CONTRACT:
        raise _bad("PACKAGE_INCOMPATIBLE", "unsupported sidecar contract",
                   sidecar_contract=d["sidecar_contract"], supported=SIDECAR_CONTRACT)


def _read_bounded(path, limit, over_key="PACKAGE_DAMAGED"):
    a = w32.attrs(path)
    if a == w32.INVALID_FILE_ATTRIBUTES:
        raise _bad("PACKAGE_INVALID", "package file missing", file=os.path.basename(path))
    if a & (w32.FILE_ATTRIBUTE_REPARSE_POINT | w32.FILE_ATTRIBUTE_DIRECTORY):
        raise _bad("PACKAGE_INVALID", "package entry is not a regular file", file=os.path.basename(path))
    try:
        with open(path, "rb") as f:
            data = f.read(limit + 1)
    except OSError as e:
        raise Stop("REFUSED", "PACKAGE_UNREADABLE", reason="package file unreadable", file=os.path.basename(path),
                   error="%s winerror=%s" % (type(e).__name__, getattr(e, "winerror", None)))
    if len(data) > limit:
        raise _bad(over_key, "package file larger than allowed", file=os.path.basename(path))
    return data


def read_package(package_dir):
    """Authenticate and read a local package. Returns (descriptor, descriptor_bytes, signature,
    {"master": bytes, "manifest": bytes, "sidecar": bytes})."""
    a = w32.attrs(package_dir)
    if a == w32.INVALID_FILE_ATTRIBUTES or not a & w32.FILE_ATTRIBUTE_DIRECTORY:
        raise _bad("PACKAGE_INVALID", "package folder not found")
    if a & w32.FILE_ATTRIBUTE_REPARSE_POINT:
        raise _bad("PACKAGE_INVALID", "package folder is a link")
    desc_bytes = _read_bounded(os.path.join(package_dir, DESCRIPTOR), MAX_DESCRIPTOR_BYTES, "PACKAGE_INVALID")
    sig = _read_bounded(os.path.join(package_dir, SIGNATURE), 64, "PACKAGE_INVALID")
    d = parse_descriptor(desc_bytes)
    verify_signature(desc_bytes, sig, d["signing_key_id"])
    check_compatibility(d)
    files = d["files"]
    want = sorted([DESCRIPTOR, SIGNATURE, files["master"]["name"], files["manifest"]["name"], files["sidecar"]["name"]])
    try:
        have = sorted(os.listdir(package_dir))
    except OSError as e:
        raise Stop("REFUSED", "PACKAGE_UNREADABLE", reason="package folder unreadable", error=str(e)[:200])
    if have != want:
        raise _bad("PACKAGE_INVALID", "package folder does not contain exactly the five package files",
                   unexpected=sorted(set(have) - set(want)), missing=sorted(set(want) - set(have)))
    payload = {}
    for role, limit in (("master", MAX_SOURCE_BYTES), ("manifest", MAX_MANIFEST_BYTES), ("sidecar", MAX_SIDECAR_BYTES)):
        data = _read_bounded(os.path.join(package_dir, files[role]["name"]), limit)
        if len(data) != files[role]["byte_length"] or sha(data) != files[role]["sha256"]:
            raise _bad("PACKAGE_DAMAGED", "package file does not match the signed descriptor", file=files[role]["name"])
        payload[role] = data
    return d, desc_bytes, sig, payload


def reverify_staged(desc_bytes, sig, payload):
    """For install: the staged descriptor still verifies and still names the staged bytes."""
    d = parse_descriptor(desc_bytes)
    verify_signature(desc_bytes, sig, d["signing_key_id"])
    check_compatibility(d)
    for role in ("master", "manifest", "sidecar"):
        f = d["files"][role]
        if len(payload[role]) != f["byte_length"] or sha(payload[role]) != f["sha256"]:
            raise Stop("REFUSED", "PREPARE_AGAIN", reason="staged official file changed", file=f["name"])
    return d


# ---------------------------------------------------------------- remembered releases
def _line(rec):
    body = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return ("%s\t%s\n" % (body, sha(body.encode("utf-8")))).encode("utf-8")


class ReleaseLog(object):
    """Append-only record of every authenticated official descriptor seen for this installation.
    Held exclusively (share 0) while read and appended, so two updaters cannot interleave. The
    file is created only when the first authenticated release is recorded."""

    def __init__(self, layout):
        self.path = os.path.join(layout.upd, RELEASE_LOG)
        self.records = []
        self.h = None
        if w32.attrs(self.path) == w32.INVALID_FILE_ATTRIBUTES:
            return
        self._open(w32.OPEN_EXISTING)

    def _open(self, disposition):
        self.h, err = w32.create_file(self.path, w32.GENERIC_READ | w32.GENERIC_WRITE, 0, disposition)
        if self.h is None:
            raise Stop("REFUSED", "RELEASE_RECORD_BUSY" if err == 32 else "RELEASE_RECORD_DAMAGED",
                       reason="release record unavailable", error=w32.ename(err))
        data, err = w32.read_all_handle(self.h)
        if data is None:
            self.close()
            raise Stop("REFUSED", "RELEASE_RECORD_DAMAGED", reason="release record unreadable", error=w32.ename(err))
        self.records = []
        try:
            lines = data.split(b"\n")
            if lines.pop() != b"":
                raise ValueError("incomplete final line")
            for raw in lines:
                body, digest = raw.decode("utf-8").rsplit("\t", 1)
                if sha(body.encode("utf-8")) != digest:
                    raise ValueError("checksum")
                rec = json.loads(body)
                if not (isinstance(rec, dict) and _int(rec.get("sequence")) and _HEX64.match(rec.get("descriptor_sha256", ""))
                        and _HEX64.match(rec.get("master_sha256", ""))):
                    raise ValueError("record fields")
                self.records.append(rec)
        except Exception as e:
            self.close()
            raise Stop("REFUSED", "RELEASE_RECORD_DAMAGED", reason="release record damaged", error=str(e)[:200])

    def high_water(self):
        return max((r["sequence"] for r in self.records), default=0)

    def seen(self, sequence):
        return {r["descriptor_sha256"] for r in self.records if r["sequence"] == sequence}

    def recognized_masters(self):
        return {r["master_sha256"] for r in self.records}

    def append(self, rec):
        if self.h is None:
            self._open(w32.OPEN_ALWAYS)
            if self.records:
                raise Stop("REFUSED", "RELEASE_RECORD_BUSY", reason="release record appeared while preparing")
        w32.seek_end(self.h)
        ok, err = w32.write_all(self.h, _line(rec))
        if ok:
            ok, err = w32.flush(self.h)
        if not ok:
            raise Stop("REFUSED", "RELEASE_RECORD_DAMAGED", reason="release record write failed", error=w32.ename(err))
        self.records.append(rec)

    def close(self):
        if self.h is not None:
            w32.close(self.h)
            self.h = None


def check_sequence(log, d, desc_sha, allow_older):
    """D4: never silently roll back or accept a conflicting re-use of a sequence number."""
    seq = d["sequence"]
    seen = log.seen(seq)
    if seen and desc_sha not in seen:
        raise Stop("REFUSED", "PACKAGE_CONFLICT", reason="sequence already seen with different descriptor bytes",
                   sequence=seq)
    hw = log.high_water()
    older = seq < hw
    if older and not allow_older:
        raise Stop("REFUSED", "PACKAGE_OLDER", reason="older than the highest official release seen",
                   sequence=seq, high_water=hw, data_version=d["data_version"])
    return {"sequence": seq, "high_water_before": hw, "older": older, "already_seen": bool(seen)}
