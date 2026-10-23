# -*- coding: utf-8 -*-
"""Production trust and release-assembly integration checks (focused, offline; TEST-ONLY).

Checks that the shipping trust table holds exactly the owner-approved production key, that unknown
signers and altered signatures stay refused, that test keys reach trust only through the test-only
seam, that the only product change is the trust table, and that the accepted software identities
(31-file inventory spec, Quick Launch) are unchanged. No private key is used: test signatures come
from ephemeral in-memory keys.

usage: <Python 3.10 with cryptography> -E -s -B updater/tests/test_production_trust.py
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
UPDATER = os.path.dirname(HERE)
REPO = os.path.dirname(UPDATER)
sys.path.insert(0, UPDATER)

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey  # noqa: E402

from sfm_character_tools_updater import hooks, official  # noqa: E402
from sfm_character_tools_updater.messages import Stop  # noqa: E402

PRODUCTION_KEY_ID = "ed25519-5d879134807dff6d"
PRODUCTION_PUBLIC = "7f2b9a53fcad0a7818ef5be52ed9fdc8826ac51e3923db30461ddbc96539dba1"
BASE = "a30f60bcf33d5853752aea19faae457bb0022bbf"
QUICK_LAUNCH = {"cpm/quick_launch/autoinit/ChadChan3D_CPM_ASE_Button.py":
                "23e3a8813057642400b7e06e0b55e13c89f47b684779d907740905a5e28e4070",
                "cpm/quick_launch/cpm_ase_quick_launch.py":
                "7a01bd5eb828631a6bc0f2df2e5a7f692eae812877e0debe7e0a364199b63f67"}  # profile 2 launcher path
SPEC = "updater/release_tools/character_tools_software_v1.json"
SPEC_SHA = "dfe28855edac530d029f75f82191f480c71ff7e2765e46baaae569fc9fd87332"  # profile 2, menu isolation (2026-10-23)
# Profile 2 (2026-10-23) changed exactly these updater sources: the supported profile and the inventory location.
PROFILE2_FILES = ["updater/packaging/build.py", "updater/sfm_character_tools_updater/compat/inventory.py",
                  "updater/sfm_character_tools_updater/compat/profile.py",
                  "updater/sfm_character_tools_updater/official.py",
                  "updater/sfm_character_tools_updater/runtime_check.py"]
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(rel):
    return open(os.path.join(REPO, *rel.split("/")), "rb").read()


def git_show(rel):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (BASE, rel)], capture_output=True, check=True).stdout


def refused(fn, reason):
    try:
        fn()
    except Stop as e:
        return e.message_key == "PACKAGE_UNTRUSTED" and e.details.get("reason") == reason
    return False


def ephemeral():
    k = Ed25519PrivateKey.generate()
    raw = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return k, raw


def main():
    # 1-2. Exactly the approved production key; id and key agree.
    check("production trust is exactly the approved key",
          official.TRUSTED_KEYS == {PRODUCTION_KEY_ID: PRODUCTION_PUBLIC}, official.TRUSTED_KEYS)
    raw = bytes.fromhex(PRODUCTION_PUBLIC)
    Ed25519PublicKey.from_public_bytes(raw)
    check("public key is a 32-byte Ed25519 key and its key id is ed25519-5d879134807dff6d",
          len(raw) == 32 and official.key_id_for(raw) == PRODUCTION_KEY_ID)
    check("shipping configuration: test seam unset, effective trust = production key only",
          hooks.extra_trusted_keys is None and official.trusted_keys() == {PRODUCTION_KEY_ID: PRODUCTION_PUBLIC})

    # 3. Unknown signers and altered signatures are refused.
    msg = b'{"schema":1}\n'
    tk, traw = ephemeral()
    tid = official.key_id_for(traw)
    tsig = tk.sign(msg)
    check("unknown (test) signer refused under shipping trust",
          refused(lambda: official.verify_signature(msg, tsig, tid), "signing key is not trusted"))
    check("signature by another key claiming the production key id refused",
          refused(lambda: official.verify_signature(msg, tsig, PRODUCTION_KEY_ID), "signature does not verify"))
    flipped = bytes([tsig[0] ^ 1]) + tsig[1:]
    check("modified signature refused (production key id)",
          refused(lambda: official.verify_signature(msg, flipped, PRODUCTION_KEY_ID), "signature does not verify"))
    check("truncated signature refused",
          refused(lambda: official.verify_signature(msg, tsig[:63], PRODUCTION_KEY_ID),
                  "signature is not a 64-byte Ed25519 signature"))

    # 4. Test keys reach trust only through the test-only seam, and never the table.
    hooks.extra_trusted_keys = {tid: traw.hex()}
    try:
        official.verify_signature(msg, tsig, tid)
        seam_ok = True
    except Stop:
        seam_ok = False
    finally:
        hooks.extra_trusted_keys = None
    check("test key verifies only while the test seam is set; table unchanged",
          seam_ok and official.TRUSTED_KEYS == {PRODUCTION_KEY_ID: PRODUCTION_PUBLIC}
          and refused(lambda: official.verify_signature(msg, tsig, tid), "signing key is not trusted"))
    pkg = os.path.join(UPDATER, "sfm_character_tools_updater")
    assigners, trust_flag = [], []
    for dp, dn, fn in os.walk(pkg):
        for n in fn:
            if n.endswith(".py"):
                src = open(os.path.join(dp, n), encoding="utf-8").read()
                if re.search(r"extra_trusted_keys\s*=", src) and n != "hooks.py":
                    assigners.append(n)
                if "--trust-key" in src:
                    trust_flag.append(n)
    for n in ("entry_gui.py", "entry_worker.py", "build.py", "sct_updater.spec"):
        if "--trust-key" in open(os.path.join(UPDATER, "packaging", n), encoding="utf-8").read():
            trust_flag.append(n)
    check("no product or packaging module sets the test seam or accepts --trust-key",
          not assigners and not trust_flag, (assigners, trust_flag))
    forbidden = open(os.path.join(UPDATER, "packaging", "build.py"), encoding="utf-8").read()
    check("bundle build still forbids test_worker and release tools",
          '"test_worker"' in forbidden and '"make_official_package"' in forbidden)

    # 8. Since the base checkpoint, official.py changed only in the trust table, the supported profile (profile 2)
    #    and comments; the other updater code changes are exactly the profile-2 set.
    def normalized(src):
        tree = ast.parse(src)
        tree.body = [n for n in tree.body
                     if not (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in ("TRUSTED_KEYS", "AUTHORITY_PROFILE") for t in n.targets))
                     and not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant)
                              and isinstance(n.value.value, str))]
        return ast.dump(tree)
    rel = "updater/sfm_character_tools_updater/official.py"
    check("official.py differs from the base only in TRUSTED_KEYS, AUTHORITY_PROFILE and docstring/comments",
          normalized(read(rel).decode("utf-8")) == normalized(git_show(rel).decode("utf-8")))
    changed = subprocess.run(["git", "-C", REPO, "diff", "--name-only", BASE, "--", "updater/sfm_character_tools_updater",
                              "updater/packaging", "updater/release_tools"], capture_output=True, text=True).stdout.split()
    changed = [c for c in changed if not c.endswith(".md")]  # documentation is not behavior
    check("no other updater product, packaging or release-tool code changed (only the profile-2 set)",
          sorted(c for c in changed if not c.endswith(".json")) == PROFILE2_FILES, changed)
    for frozen in ("tools/sfm_master_sidecar", "tests/sidecar/qualification/candidate_b2c_correction2",
                   "sfm_defaultanimationgroups.txt", "cpm/quick_launch/autoinit",
                   "updater/sfm_character_tools_updater/backend.py", "updater/sfm_character_tools_updater/recovery.py",
                   "updater/sfm_character_tools_updater/journal.py", "updater/sfm_character_tools_updater/candidate.py"):
        diff = subprocess.run(["git", "-C", REPO, "diff", "--name-only", BASE, "--", frozen],
                              capture_output=True, text=True).stdout.split()
        if diff:
            check("unchanged since base: %s" % frozen, False, diff)
    check("compiler, validator/provider, Master, Quick Launch bootstrap and activation/recovery code unchanged since base",
          True)

    # 6-7. Accepted software identities.
    spec = json.loads(read(SPEC))
    bad = [f["source"] for f in spec["files"]
           if sha(read(f["source"])) != f["sha256"] or len(read(f["source"])) != f["byte_length"]]
    check("inventory spec is the profile-2 spec (dfe28855) and all 31 sources match it",
          sha(read(SPEC)) == SPEC_SHA and len(spec["files"]) == 31 and not bad, bad)
    check("launcher outside the 31-file inventory",
          not any(f["path"].endswith("SFM_Control_Group_Updater.py") for f in spec["files"]))
    check("Quick Launch identities: bootstrap unchanged, controller = profile-2 build",
          all(sha(read(p)) == h for p, h in QUICK_LAUNCH.items()))

    sums = {}
    for line in read("updater/SHA256SUMS.txt").decode("ascii").splitlines():
        h, p = line.split("  ", 1)
        sums[p] = h
    stale = [p for p, h in sums.items() if sha(read(p)) != h]
    check("updater/SHA256SUMS.txt matches every listed file", not stale, stale)
    check("SHA256SUMS lists official.py, the launcher and both new tests",
          all(p in sums for p in (rel, "updater/menu/SFM_Control_Group_Updater.py",
                                  "updater/tests/test_production_trust.py", "updater/tests/test_menu_launcher.py")))

    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
