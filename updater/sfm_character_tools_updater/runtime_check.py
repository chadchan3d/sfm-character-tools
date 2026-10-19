# -*- coding: utf-8 -*-
"""Read-only diagnostics of the running application (worker command `runtime-check`, L-5).

Reports where the running code was loaded from and checks the runtime closure the backend needs:
the pinned compiler/validator/provider files, the Ed25519 implementation (RFC 8032 test vector 1;
no key is trusted or used), the TLS trust store used by release discovery, and the compatibility
profile. It reads nothing in the installation beyond resolving it, and writes nothing.
"""
import os
import sys

from . import VERSION, candidate
from .compat import profile as prof

# RFC 8032 section 7.1, TEST 1 (empty message).
_RFC8032_PUBLIC = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
_RFC8032_SIGNATURE = ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555"
                      "fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")


def _ed25519():
    from cryptography import __version__ as cv
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(_RFC8032_PUBLIC))
    key.verify(bytes.fromhex(_RFC8032_SIGNATURE), b"")
    try:
        key.verify(bytes.fromhex(_RFC8032_SIGNATURE), b"x")
        rejects = False
    except InvalidSignature:
        rejects = True
    import cryptography
    return {"version": cv, "rfc8032_test1_verifies": True, "rejects_altered_message": rejects,
            "location": os.path.dirname(cryptography.__file__)}


def _tls():
    import ssl
    ctx = ssl.create_default_context()
    stats = ctx.cert_store_stats()
    return {"openssl": ssl.OPENSSL_VERSION, "verify_mode_required": ctx.verify_mode == ssl.CERT_REQUIRED,
            "check_hostname": ctx.check_hostname, "ca_certificates": stats.get("x509_ca", 0)}


def _origins():
    """Directories modules were loaded from. A relative __file__ (the packaged application's frozen
    bootstrap and entry modules, which live inside the executable) is reported as "<frozen>", never
    resolved against the working directory."""
    roots = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f:
            roots.add(os.path.dirname(f) if os.path.isabs(f) else "<frozen>")
    return sorted(roots)


def run(layout):
    res = {"operation": "runtime-check", "version": VERSION, "frozen": candidate.FROZEN,
           "executable": sys.executable, "python": sys.version, "sys_path": list(sys.path), "checks": {}}
    checks = res["checks"]
    try:
        d = candidate.deps()
        checks["pinned_dependencies"] = {"ok": True, "pins": len(candidate.PINS),
                                         "compiler": d["compiler"].__file__, "reader": d["reader"].__file__,
                                         "deps_root": candidate.TOOLS, "auth_root": candidate.AUTH_PKG}
    except Exception as e:
        checks["pinned_dependencies"] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
    try:
        checks["ed25519"] = dict(_ed25519(), ok=True)
    except Exception as e:
        checks["ed25519"] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
    try:
        t = _tls()
        checks["tls"] = dict(t, ok=t["verify_mode_required"] and t["check_hostname"])
    except Exception as e:
        checks["tls"] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:300])}
    pins = {os.path.relpath(p, candidate.TOOLS if p.startswith(candidate.TOOLS) else candidate.AUTH_PKG)
            .replace("\\", "/"): h for p, h in candidate.PINS.items()}
    expected = dict(prof.PROFILE_1["compiler"])
    expected.update({k: v for k, v in prof.PROFILE_1["validator_provider"].items() if k.endswith(".py")})
    checks["profile_matches_pins"] = {"ok": sorted(pins.values()) == sorted(expected.values()),
                                      "profile": prof.PROFILE_1["profile_id"],
                                      "contract_sha256": prof.PROFILE_SHA256[prof.PROFILE_1["profile_id"]]}
    res["module_origins"] = _origins()
    ok = all(c.get("ok") for c in checks.values())
    res.update(outcome="RUNTIME_OK" if ok else "RUNTIME_FAILED",
               message="Runtime check passed." if ok else "Runtime check failed; see the details.")
    return res
