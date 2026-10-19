# -*- coding: utf-8 -*-
"""Candidate compilation and validation through the unchanged canonical compiler.

Dependencies are used unmodified and hash-pinned: the compiler, manifest, reader, writer and
format modules of tools/sfm_master_sidecar, tools/sfm_master_core.py, and the FINAL R3-A2B
validator/provider of the production authority package. A pin mismatch refuses before
anything is compiled or written.

Location (L-5): in the development tree they are read from the repository (tools/ and the production
authority package's qualified copy); in the packaged application (frozen) they are the same exact
files carried in the bundle under `sct_deps/`. The pins are identical in both cases.
"""
import hashlib
import importlib.util
import json
import os
import sys

from .layout import SIDECAR_RE
from .messages import Stop

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    _REPO = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "sct_deps")
    TOOLS = _REPO
    AUTH_PKG = os.path.join(_REPO, "authority")
    sys.dont_write_bytecode = True  # never write into the application folder
else:
    _REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    TOOLS = os.path.join(_REPO, "tools")
    AUTH_PKG = os.path.join(_REPO, "tests", "sidecar", "qualification", "candidate_b2c_correction6",
                            "sfm_master_authority_productionized")

PINS = {
    os.path.join(TOOLS, "sfm_master_sidecar", "__init__.py"):
        "8cad865fd9954035aebb3e02d5c454228e80a095595bd9cd3746df0b357f904c",
    os.path.join(TOOLS, "sfm_master_sidecar", "compiler.py"):
        "50dd18045c30aa5258b7821bb02d4f68fc0fa88d4e2fa9a335a2972d4e3f7643",
    os.path.join(TOOLS, "sfm_master_sidecar", "format.py"):
        "b401967db8d07943e9f171058a006c30f0e23eb70a7b43bb5ab950203a3c3259",
    os.path.join(TOOLS, "sfm_master_sidecar", "manifest.py"):
        "edc646679e326115a4c8f3b52452476db7cf1885c5d7992ff647e5c0d90c5173",
    os.path.join(TOOLS, "sfm_master_sidecar", "reader.py"):
        "1b95261c52d95c306b28fc6e5e9340afa65de4ea2574ed29c2bab427d252719f",
    os.path.join(TOOLS, "sfm_master_sidecar", "writer.py"):
        "770d5beb1809e425869d12cd697e87fa741f085078589bcb982be8279f07d55d",
    os.path.join(TOOLS, "sfm_master_core.py"):
        "a76e7e4e66f6ee0b4e15f4f2d5c412dcef120240c93d4cd1dd4dd0deff9ef37b",
    os.path.join(AUTH_PKG, "candidate_packed_validator_r3a2b.py"):
        "74fe8d9655018a9450d0803018d61e42ec3d17b2947b60915df6b598ffc1563f",
    os.path.join(AUTH_PKG, "candidate_packed_provider_r3a2b.py"):
        "d6ef96502194c15e594b3e5754e2f5826af1d0ec01b0b358fff08598f7e6b677",
}

_DEPS = {}


def _sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def deps():
    """Verify every pin, then import the pinned modules (once per process)."""
    if _DEPS:
        return _DEPS
    bad = {}
    for p, want in PINS.items():
        try:
            have = _sha_file(p)
        except OSError as e:
            have = "UNREADABLE:%s" % type(e).__name__
        if have != want:
            bad[os.path.relpath(p, _REPO)] = have
    if bad:
        raise Stop("REFUSED", "DEPENDENCY", reason="pinned dependency mismatch", mismatches=bad)
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from sfm_master_sidecar import compiler, manifest, reader
    import sfm_master_core
    for mod in (compiler, manifest, reader, sfm_master_core):
        if os.path.normcase(os.path.abspath(mod.__file__)) not in {os.path.normcase(p) for p in PINS}:
            raise Stop("REFUSED", "DEPENDENCY", reason="dependency imported from an unpinned location",
                       module=mod.__name__)
    for name in ("candidate_packed_validator_r3a2b", "candidate_packed_provider_r3a2b"):
        p = os.path.join(AUTH_PKG, name + ".py")
        spec = importlib.util.spec_from_file_location(name, p)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    _DEPS.update(compiler=compiler, manifest=manifest, reader=reader,
                 provider=sys.modules["candidate_packed_provider_r3a2b"])
    return _DEPS


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compile_real(txt, source_name):
    """Unchanged production compiler (generic acceptance); in-memory reader self-validation."""
    d = deps()
    snap = d["compiler"].SourceSnapshot(source_name, txt)
    try:
        outcome = d["compiler"].parse_and_compile(snap)
        d["compiler"].self_validate_from_bytes(outcome)
    except Exception as e:
        raise Stop("REFUSED", "NOTHING", reason="candidate failed compilation/validation",
                   error="%s: %s" % (type(e).__name__, str(e)[:300]))
    name = d["compiler"].generation_basename(outcome.ordinary_sha256)
    manifest = d["manifest"].serialize_manifest(d["manifest"].build_manifest_dict(outcome, name))
    return name, outcome.blob, manifest, outcome


def _manifest_binding(manifest_bytes, name, sidecar_sha, source_sha, source_len):
    m = json.loads(manifest_bytes.decode("utf-8"))
    if not SIDECAR_RE.match(name) or m.get("generation_basename") != name \
            or m.get("sidecar_sha256") != sidecar_sha \
            or m.get("source_sha256") != source_sha \
            or m.get("source_byte_length") != source_len:
        return "manifest fields do not bind the candidate"
    return None


def admit(sc_path, source_sha):
    """FINAL R3-A2B bounded-provider admission of the file actually on disk."""
    prov = deps()["provider"].BoundedProvider.open_path(sc_path, source_sha)
    prov.close()


def validate_candidate_files(outcome, name, sc_path, manifest_path):
    """From the bytes actually written: reader semantic parity, FINAL R3-A2B admission,
    manifest fields. Returns None or the failure text."""
    try:
        deps()["compiler"].self_validate_from_path(outcome, sc_path)
        admit(sc_path, outcome.snapshot.sha256_hex)
        data = open(manifest_path, "rb").read()
        return _manifest_binding(data, name, outcome.ordinary_sha256, outcome.snapshot.sha256_hex,
                                 len(outcome.snapshot.bytes))
    except Exception as e:
        return "%s: %s" % (type(e).__name__, str(e)[:300])


def validate_official_bytes(outcome, name, body, manifest_bytes):
    """Before anything is written: the official sidecar bytes against the canonical compile of the
    official TXT (reader semantic parity), FINAL R3-A2B admission from the bytes, manifest binding."""
    d = deps()
    src = outcome.snapshot.sha256_hex
    try:
        r = d["reader"].SidecarReader.open_generation_bytes(body, src)
        try:
            d["compiler"].verify_semantic_parity(outcome.result, r)
        finally:
            r.close()
        d["provider"].BoundedProvider.open_bytes(body, src).close()
        return _manifest_binding(manifest_bytes, name, sha(body), src, len(outcome.snapshot.bytes))
    except Exception as e:
        return "%s: %s" % (type(e).__name__, str(e)[:300])


def validate_official_files(outcome, name, sc_path, manifest_path, sidecar_sha):
    """An official sidecar against the official TXT, from the bytes on disk: reader semantic
    parity with the canonical compile of that TXT, FINAL R3-A2B admission, and the official
    manifest binding the official sidecar and TXT. Byte equality with a local compile is not
    required (the producer's compiler build may differ); semantic parity is."""
    try:
        deps()["compiler"].self_validate_from_path(outcome, sc_path)
        admit(sc_path, outcome.snapshot.sha256_hex)
        return _manifest_binding(open(manifest_path, "rb").read(), name, sidecar_sha, outcome.snapshot.sha256_hex,
                                 len(outcome.snapshot.bytes))
    except Exception as e:
        return "%s: %s" % (type(e).__name__, str(e)[:300])


def validate_staged_copy(name, sc_path, manifest_path, sidecar_sha, source_sha, source_len):
    """For candidate files copied from validated staging: exact bytes, authority-bound reader
    open (structure + source binding), FINAL R3-A2B admission, manifest fields."""
    try:
        sc = open(sc_path, "rb").read()
        if sha(sc) != sidecar_sha:
            return "candidate sidecar bytes differ from the prepared candidate"
        r = deps()["reader"].SidecarReader.open_generation_path(sc_path, source_sha)
        r.close()
        admit(sc_path, source_sha)
        return _manifest_binding(open(manifest_path, "rb").read(), name, sidecar_sha, source_sha, source_len)
    except Exception as e:
        return "%s: %s" % (type(e).__name__, str(e)[:300])
