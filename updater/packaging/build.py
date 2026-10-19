# -*- coding: utf-8 -*-
"""Reproducible build of the one-folder SFM Control Group Updater (L-5).

  <build-venv python> -E -s -B build.py --out DIR

DIR must be a new folder outside the repository. The build environment is a fresh virtual
environment of CPython 3.10.6 x64 with exactly requirements-build.txt installed (hash-checked,
offline). The script:
  1. checks the interpreter and the locked package versions;
  2. checks the pinned dependency sources against candidate.PINS and the authority profile;
  3. writes the Windows version resource from sfm_character_tools_updater.VERSION;
  4. runs PyInstaller with sct_updater.spec (no UPX);
  5. verifies the bundled pinned sources byte-for-byte, refuses test/development material and
     workstation paths in the bundle, and writes DIR\\bundle_manifest.json (every file, size and
     SHA-256) with the bundle identity (SHA-256 of the manifest's file list).
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UPD = os.path.dirname(HERE)
REPO = os.path.dirname(UPD)
APP = "SFM Control Group Updater"
LOCK = {"pyinstaller": "6.11.1", "pyinstaller-hooks-contrib": "2024.10", "cryptography": "50.0.2",
        "cffi": "2.1.1", "pycparser": "3.11"}
FORBIDDEN_NAMES = ("test_worker", "fake_github", "net_audit", "gui_driver", "run_l1", "make_official_package",
                   "make_software_inventory", ".pem", "/keys/")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(p):
    return os.path.normcase(os.path.abspath(p)).rstrip("\\")


def check_environment():
    from importlib.metadata import version
    problems = []
    if sys.version_info[:2] != (3, 10) or platform.architecture()[0] != "64bit":
        problems.append("interpreter must be CPython 3.10 x64, not %s %s" % (sys.version, platform.architecture()))
    for name, want in LOCK.items():
        try:
            have = version(name)
        except Exception:
            have = None
        if have != want:
            problems.append("%s %s (locked %s)" % (name, have, want))
    if problems:
        raise SystemExit("environment does not match the build lock: %s" % problems)


def pinned():
    sys.path.insert(0, UPD)
    from sfm_character_tools_updater import candidate, VERSION
    from sfm_character_tools_updater.compat import profile
    bad = {p: h for p, h in candidate.PINS.items() if sha(open(p, "rb").read()) != h}
    if bad:
        raise SystemExit("pinned dependency sources differ from their pins: %s" % sorted(bad))
    expected = set(profile.PROFILE_1["compiler"].values()) | {
        v for k, v in profile.PROFILE_1["validator_provider"].items() if k.endswith(".py")}
    if set(candidate.PINS.values()) != expected:
        raise SystemExit("candidate pins and authority profile disagree")
    by_name = {}
    for p, h in candidate.PINS.items():
        rel = os.path.relpath(p, candidate.TOOLS) if norm(p).startswith(norm(candidate.TOOLS)) else \
            os.path.join("authority", os.path.basename(p))
        by_name[rel.replace("\\", "/")] = h
    return VERSION, by_name


def version_file(path, version):
    parts = [int(x) for x in version.split(".")] + [0] * 4
    v = tuple(parts[:4])
    text = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=%(v)r, prodvers=%(v)r, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1,
                    subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'ChadChan3D'),
      StringStruct('FileDescription', '%(app)s'),
      StringStruct('FileVersion', '%(s)s'),
      StringStruct('ProductName', '%(app)s'),
      StringStruct('ProductVersion', '%(s)s')])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""" % {"v": v, "s": version, "app": APP}
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def manifest(bundle):
    files = []
    for dp, dn, fn in os.walk(bundle):
        dn.sort()
        for n in sorted(fn):
            p = os.path.join(dp, n)
            data = open(p, "rb").read()
            files.append({"path": os.path.relpath(p, bundle).replace("\\", "/"), "size": len(data),
                          "sha256": sha(data)})
    files.sort(key=lambda f: f["path"].lower())
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    if norm(out) == norm(REPO) or norm(out).startswith(norm(REPO) + "\\"):
        raise SystemExit("refused: build output must be outside the repository")
    if os.path.exists(out):
        raise SystemExit("refused: output folder already exists")
    check_environment()
    version, pins = pinned()
    os.makedirs(out)
    vf = os.path.join(out, "version_info.txt")
    version_file(vf, version)
    # Fixed hash seed and timestamp: PyInstaller's documented requirements for reproducible output.
    env = dict(os.environ, SCT_VERSION_FILE=vf, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0",
               SOURCE_DATE_EPOCH="1760745600")
    env.pop("PYTHONPATH", None)
    # A minimal PATH: only Windows and the build interpreter. Otherwise PyInstaller's dependency
    # search can collect unrelated DLLs from the workstation (for example another OpenSSL on PATH).
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    env["PATH"] = os.pathsep.join([os.path.join(windir, "System32"), windir, os.path.dirname(sys.executable),
                                   sys.base_prefix, os.path.join(sys.base_prefix, "DLLs")])
    cmd = [sys.executable, "-E", "-s", "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
           "--distpath", os.path.join(out, "dist"), "--workpath", os.path.join(out, "work"),
           os.path.join(HERE, "sct_updater.spec")]
    subprocess.run(cmd, check=True, env=env, cwd=out)
    bundle = os.path.join(out, "dist", APP)
    deps = os.path.join(bundle, "_internal", "sct_deps")
    bad = {}
    for rel, h in pins.items():
        p = os.path.join(deps, *rel.split("/"))
        got = sha(open(p, "rb").read()) if os.path.isfile(p) else None
        if got != h:
            bad[rel] = got
    if bad:
        raise SystemExit("bundled pinned sources differ: %s" % bad)
    files = manifest(bundle)
    forbidden = [f["path"] for f in files if any(x in "/" + f["path"].lower() for x in FORBIDDEN_NAMES)]
    markers = [m.encode() for m in (REPO, os.path.expanduser("~"))] + [b"SFM Animation Group Master"]
    leaks = []
    for f in files:
        data = open(os.path.join(bundle, *f["path"].split("/")), "rb").read()
        if any(m in data for m in markers):
            leaks.append(f["path"])
    if forbidden:
        raise SystemExit("bundle contains test/development material: %s" % forbidden)
    ident = sha(json.dumps([[f["path"], f["sha256"]] for f in files], separators=(",", ":")).encode("utf-8"))
    report = {"application": APP, "version": version, "bundle_identity_sha256": ident, "files": files,
              "pinned_sources": pins, "workstation_path_markers_found_in": leaks,
              "build": {"python": sys.version, "lock": LOCK}}
    with open(os.path.join(out, "bundle_manifest.json"), "x", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    print(json.dumps({"bundle": bundle, "version": version, "files": len(files), "bundle_identity_sha256": ident,
                      "path_markers_in": leaks[:10]}, indent=1))


if __name__ == "__main__":
    main()
