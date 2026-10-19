# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the one-folder SFM Control Group Updater (L-5). Run through build.py, which
# checks the environment and the pinned dependencies before and after the build.
#
# Two executables share one folder:
#   SFM Control Group Updater.exe   the Tkinter GUI (windowed)
#   sct-updater-worker.exe          the bounded backend worker (console subsystem; the GUI starts it
#                                   with CREATE_NO_WINDOW inside a Job Object)
# The pinned compiler/validator/provider sources are carried byte-for-byte under _internal\sct_deps
# and loaded by candidate.py after verifying their SHA-256 pins.
import os
import re

UPD = os.path.abspath(os.path.join(SPECPATH, ".."))
REPO = os.path.dirname(UPD)
AUTH = os.path.join(REPO, "tests", "sidecar", "qualification", "candidate_b2c_correction6",
                    "sfm_master_authority_productionized")
VERSION_FILE = os.environ["SCT_VERSION_FILE"]
APP = "SFM Control Group Updater"

DEPS = [(os.path.join(REPO, "tools", "sfm_master_sidecar", n), os.path.join("sct_deps", "sfm_master_sidecar"))
        for n in ("__init__.py", "compiler.py", "format.py", "manifest.py", "reader.py", "writer.py")]
DEPS += [(os.path.join(REPO, "tools", "sfm_master_core.py"), "sct_deps"),
         (os.path.join(AUTH, "candidate_packed_validator_r3a2b.py"), os.path.join("sct_deps", "authority")),
         (os.path.join(AUTH, "candidate_packed_provider_r3a2b.py"), os.path.join("sct_deps", "authority"))]

# Standard-library modules the pinned sources import at run time (they are loaded from sct_deps,
# so PyInstaller cannot see their imports).
STDLIB_FOR_DEPS = ["array", "binascii", "bisect", "collections", "dataclasses", "hashlib", "json", "pathlib", "re",
                   "struct", "tempfile", "typing"]
EXCLUDES = ["sfm_character_tools_updater.tests", "test_worker", "fake_github", "net_audit", "gui_driver",
            "make_official_package", "make_software_inventory", "unittest", "pydoc", "lib2to3", "idlelib"]

a_gui = Analysis([os.path.join(SPECPATH, "entry_gui.py")], pathex=[UPD], datas=DEPS,
                 hiddenimports=STDLIB_FOR_DEPS, excludes=EXCLUDES, noarchive=False)
a_wrk = Analysis([os.path.join(SPECPATH, "entry_worker.py")], pathex=[UPD], datas=DEPS,
                 hiddenimports=STDLIB_FOR_DEPS + ["sfm_character_tools_updater.discovery",
                                                  "sfm_character_tools_updater.runtime_check"],
                 excludes=EXCLUDES + ["tkinter", "_tkinter"], noarchive=False)
pyz_gui = PYZ(a_gui.pure)
pyz_wrk = PYZ(a_wrk.pure)
exe_gui = EXE(pyz_gui, a_gui.scripts, [], exclude_binaries=True, name=APP, console=False, upx=False,
              version=VERSION_FILE)
exe_wrk = EXE(pyz_wrk, a_wrk.scripts, [], exclude_binaries=True, name="sct-updater-worker", console=True,
              upx=False, version=VERSION_FILE)
coll = COLLECT(exe_gui, a_gui.binaries, a_gui.datas, exe_wrk, a_wrk.binaries, a_wrk.datas, upx=False, name=APP)
