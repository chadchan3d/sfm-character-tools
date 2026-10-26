"""Build the temporary Workshop Scripts payload from the unchanged v1.0.0 ZIP."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from .core import RELEASE_SHA256, digest_file
from . import release

SCRIPT_REL = "scripts/sfm/mainmenu/SFM Character Tools/Install or Update (Windows Setup).py"
PAYLOAD_DIR = "scripts/sfm/mainmenu/SFM Character Tools/_workshop_installer"


def launcher(exe_sha, zip_sha):
    # SFM's Scripts-menu executor shares a namespace, so the function name is private.
    return ('''# -*- coding: ascii -*-
def _sct_workshop_install_v1():
    import ctypes
    import hashlib
    import os
    import subprocess
    import sys
    buf = ctypes.create_unicode_buffer(32768)
    used = ctypes.windll.kernel32.GetModuleFileNameW(None, buf, len(buf))
    if not used or used >= len(buf):
        sys.stdout.write("SFM installation location could not be determined.\\n")
        return
    sfm_exe = buf.value
    game = os.path.dirname(sfm_exe)
    if os.path.basename(sfm_exe).lower() != "sfm.exe" or not os.path.isdir(os.path.join(game, "usermod")):
        sys.stdout.write("This script must run from the intended SFM installation.\\n")
        return
    base = os.path.join(game, "workshop", "scripts", "sfm", "mainmenu", "SFM Character Tools", "_workshop_installer")
    exe = os.path.join(base, "SCT_Setup.exe")
    release = os.path.join(base, "%(archive)s")
    for path, wanted in ((exe, "%(exe)s"), (release, "%(zip)s")):
        if not os.path.isfile(path):
            sys.stdout.write("SFM Character Tools installation payload is missing.\\n")
            return
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1048576), ""):
                h.update(block)
        if h.hexdigest() != wanted:
            sys.stdout.write("SFM Character Tools installation payload failed verification.\\n")
            return
    try:
        subprocess.Popen([exe, "--game", game], cwd=base, close_fds=True,
                         creationflags=0x00000008 | 0x00000200)
    except Exception as exc:
        sys.stdout.write("SFM Character Tools setup could not start: %%r\\n" %% (exc,))
try:
    _sct_workshop_install_v1()
finally:
    del _sct_workshop_install_v1
''' % {"exe": exe_sha, "zip": zip_sha, "archive": release.ARCHIVE}).encode("ascii")


def stage(release_zip, executable, output):
    release_zip, executable, output = map(Path, (release_zip, executable, output))
    if output.exists():
        raise ValueError("Output already exists; choose a fresh staging directory")
    if digest_file(release_zip) != RELEASE_SHA256:
        raise ValueError("Release ZIP hash differs from the approved v1.0.0 artifact")
    exe_sha = digest_file(executable)
    paths = {
        SCRIPT_REL: launcher(exe_sha, RELEASE_SHA256),
        PAYLOAD_DIR + "/" + release.ARCHIVE: release_zip,
        PAYLOAD_DIR + "/SCT_Setup.exe": executable,
    }
    output.mkdir(parents=True)
    try:
        manifest = {"schema": "sct-workshop-payload-1", "files": []}
        for rel, source in sorted(paths.items()):
            dst = output / Path(*rel.split("/"))
            dst.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                dst.write_bytes(source)
            else:
                shutil.copyfile(source, dst)
            manifest["files"].append({"path": rel, "bytes": dst.stat().st_size,
                                      "sha256": digest_file(dst)})
        manifest_path = output / Path(*PAYLOAD_DIR.split("/")) / "installer_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verify(output)
        return manifest_path
    except Exception:
        shutil.rmtree(output)
        raise


def verify(output):
    output = Path(output)
    manifest = json.loads((output / Path(*PAYLOAD_DIR.split("/")) / "installer_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "sct-workshop-payload-1" or len(manifest.get("files", [])) != 3:
        raise ValueError("Invalid payload manifest")
    expected = {SCRIPT_REL, PAYLOAD_DIR + "/" + release.ARCHIVE, PAYLOAD_DIR + "/SCT_Setup.exe"}
    if {e["path"] for e in manifest["files"]} != expected:
        raise ValueError("Unexpected payload file set")
    for entry in manifest["files"]:
        target = output / Path(*entry["path"].split("/"))
        if target.stat().st_size != entry["bytes"] or digest_file(target) != entry["sha256"]:
            raise ValueError("Payload verification failed: " + entry["path"])
    if digest_file(output / Path(*(PAYLOAD_DIR + "/" + release.ARCHIVE).split("/"))) != RELEASE_SHA256:
        raise ValueError("Release ZIP changed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--release", required=True)
    p.add_argument("--setup", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    print(stage(a.release, a.setup, a.out))


if __name__ == "__main__":
    main()
