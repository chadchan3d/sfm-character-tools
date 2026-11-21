# -*- coding: utf-8 -*-
"""Offline end-to-end test of the WU kit with the real Workshop installer in a disposable game folder: a v1.0.0 Setup
installation, pre, the v1.1.0 update, check-update, uninstall, check-uninstall and restore.

Needs SCT_V1_RELEASE_ZIP (v1.1.0) and SCT_V100_RELEASE_ZIP (v1.0.0 Archive A). usage: python test_wu.py
(from the repository root, so workshop_installer imports)."""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from workshop_installer import core, release  # noqa: E402
import wu_tool as W  # noqa: E402

V100 = {"VERSION": "1.0.0", "ARCHIVE": "SFM.Character.Tools.v1.0.0.zip",
        "SHA256": "5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458",
        "ARCHIVE_ENTRIES": 1006, "INVENTORY_ENTRIES": 31}
REGS = ("scripts/SFM Character Tools/cpm_pose_profiles_v1.json", "scripts/SFM Character Tools/cpm_body_profiles_v1.json")


def as_v100():
    s = contextlib.ExitStack()
    s.enter_context(mock.patch.multiple(release, PATHS=tuple(p for p in release.PATHS if p not in REGS), **V100))
    s.enter_context(mock.patch.object(core, "RELEASE_SHA256", V100["SHA256"]))
    return s


def run(c, cmd):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = getattr(W, "cmd_" + cmd.replace("-", "_"))(c)
        except SystemExit as e:
            code = e
    return code, out.getvalue()


class WUKitTest(unittest.TestCase):
    def test_full_cycle(self):
        new, old = os.environ.get("SCT_V1_RELEASE_ZIP"), os.environ.get("SCT_V100_RELEASE_ZIP")
        if not (new and old):
            self.skipTest("set SCT_V1_RELEASE_ZIP and SCT_V100_RELEASE_ZIP")
        os.environ["WU_TEST_SFM_STATE"] = "closed"
        tmp = tempfile.TemporaryDirectory(prefix="wu_test_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        game = root / "game"
        (game / "usermod" / "cfg").mkdir(parents=True)
        (game / "usermod" / "gameinfo.txt").write_text(
            '"GameInfo" { "FileSystem" { "SearchPaths" { "Game" "|gameinfo_path|." "Game" "workshop" } } }\n')
        for rel in ("scripts/sfm/autoinit/autoinit_manager.py", "scripts/sfm/sfm_init_local.py",
                    "scripts/sfm/mainmenu/kiwifruitdev/autoinit_manager.py",
                    "scripts/sfm/mainmenu/SFM Character Tools/_workshop_installer/sfm.character.tools.v1.0.0.zip"):
            (game / "workshop" / rel).parent.mkdir(parents=True, exist_ok=True)
            (game / "workshop" / rel).write_bytes(b"steam-managed marker")
        stage = root / "stage" / "payload"
        stage.mkdir(parents=True)
        helper = stage / "SCT_Setup.exe"
        helper.write_bytes(b"disposable v1.1.0 setup stand-in")
        fixture = root / "R2.dmx"
        fixture.write_bytes(b"fixture")
        library = root / "Documents" / "SFM Character Preset Manager"
        for rel in ("Characters/krystal/Body Presets/Tall.json", "Characters/krystal/library.json"):
            (library / rel).parent.mkdir(parents=True, exist_ok=True)
            (library / rel).write_bytes(b"{}")
        h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
        with open(os.path.join(HERE, "..", "wu.template.json"), encoding="utf-8") as f:
            c = json.loads(f.read())
        c["paths"] = {"Q": str(root / "Q"), "GAME": str(game), "LIBRARY": str(library), "ZIP": new,
                      "STAGE_PAYLOAD": str(stage), "R2_FIXTURE": str(fixture)}
        c["pins"].update(helper_sha256=h(helper), r2_fixture_sha256=h(fixture),
                         manager_sha256=hashlib.sha256(core._manager_source(h(helper))).hexdigest())

        with mock.patch.object(core, "process_status", return_value=("CLEAR", "test")):
            with as_v100():
                p100 = core.prepare(old, Path(__file__))
                p100.version, p100.package = V100["VERSION"], V100["SHA256"]
                core.install(game, p100, core.preview(game, p100)["snapshot"])
            p100.close()
            user = game / "usermod" / "cfg" / "sfm_character_tools_backups" / "earlier.txt"
            user.parent.mkdir(parents=True, exist_ok=True)
            user.write_bytes(b"updater backup")
            (game / "usermod" / "cfg" / "sfm_defaultanimationgroups.txt").write_bytes(b"customized\n")

            code, out = run(c, "pre")
            self.assertIn("PRE PASS", out, out)
            pre_record = (game / "usermod/cfg/sfm_character_tools_installer/installation.json").read_bytes()

            p110 = core.prepare(new, helper)
            try:
                core.install(game, p110, core.preview(game, p110)["snapshot"])
            finally:
                p110.close()
            (game / "usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.pyc").write_bytes(b"bytecode")
            code, out = run(c, "check-update")
            self.assertEqual(code, 0, out)
            self.assertIn("CHECK-UPDATE PASS", out)

            poses = library / "Characters/krystal/Poses/WU Pose--abc.json"
            poses.parent.mkdir(parents=True)
            poses.write_bytes(b"{}")
            (library / "Characters/krystal/pose_rigs.json").write_bytes(b"{}")
            core.uninstall(game, core.removal_preview(game))
            code, out = run(c, "check-uninstall")
            self.assertEqual(code, 0, out)
            self.assertIn("CHECK-UNINSTALL PASS", out)

            code, out = run(c, "restore")
            self.assertEqual(code, 0, out)
            self.assertIn("RESTORED", out)
        self.assertEqual((game / "usermod/cfg/sfm_character_tools_installer/installation.json").read_bytes(),
                         pre_record)
        self.assertEqual(h(game / "usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py"),
                         c["pins"]["v100_cpm_sha256"])
        for r in REGS:
            self.assertFalse((game / "usermod" / r).exists())
        self.assertFalse(poses.exists())
        self.assertEqual((game / "usermod/cfg/sfm_defaultanimationgroups.txt").read_bytes(), b"customized\n")
        self.assertTrue((root / "Q/evidence/after_restore_removed/library").exists())

    def test_check_update_flags_an_unrelated_change(self):
        pre = {"usermod/cfg/x.txt": "a", "usermod/cfg/sfm_character_tools_backups/b": "b"}
        now = dict(pre, **{"usermod/cfg/x.txt": "changed", "usermod/scripts/other.pyc": "new"})
        c = {"housekeeping": ["cfg\\config.cfg"]}
        self.assertEqual(W.unexpected(c, pre, now, {}), ["usermod/cfg/x.txt"])
        now["usermod/cfg/config.cfg"] = "sfm"
        self.assertEqual(W.unexpected(c, pre, now, {}), ["usermod/cfg/x.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
