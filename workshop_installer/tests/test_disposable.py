"""Bounded Windows-only tests. All installation targets are temporary directories."""
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from workshop_installer import core


class DisposableInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get("SCT_V1_RELEASE_ZIP")
        if not source:
            raise unittest.SkipTest("Set SCT_V1_RELEASE_ZIP to the unchanged v1.0.0 ZIP")
        cls.prepared = core.prepare(source, Path(__file__))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "prepared"):
            cls.prepared.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sct_install_test_")
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "game"
        (self.game / "usermod" / "cfg").mkdir(parents=True)
        (self.game / "workshop" / "scripts" / "sfm" / "autoinit").mkdir(parents=True)
        (self.game / "workshop" / "scripts" / "sfm" / "autoinit" / "autoinit_manager.py").write_bytes(b"test\n")
        (self.game / "workshop" / "scripts" / "sfm" / "sfm_init_local.py").write_bytes(b"test\n")
        menu = self.game / "workshop" / "scripts" / "sfm" / "mainmenu" / "kiwifruitdev" / "autoinit_manager.py"
        menu.parent.mkdir(parents=True)
        menu.write_bytes(b"test\n")
        patcher = mock.patch.object(core, "process_status", return_value=("CLEAR", "disposable test"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def target(self, rel):
        return core._target(self.game, rel)

    def test_fresh_install_verify_and_remove(self):
        self.assertEqual(core.preview(self.game, self.prepared)["write_count"], 1006)
        core.install(self.game, self.prepared)
        self.assertEqual(core.verify(self.game)["mismatches"], [])
        result = core.uninstall(self.game)
        self.assertEqual(result["preserved"], [core.HELPER])
        self.assertFalse(self.target(core.MASTER).exists())
        self.assertFalse(self.target(core.BUTTON).exists())

    def test_modified_master_requires_consent_and_is_restored(self):
        path = self.target(core.MASTER)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"custom master\n")
        with self.assertRaisesRegex(core.Refusal, "consent"):
            core.install(self.game, self.prepared)
        summary = core.preview(self.game, self.prepared)
        core.install(self.game, self.prepared, replace_authority=True,
                     expected_authority=summary["authority_snapshot"])
        self.assertEqual(core.verify(self.game)["mismatches"], [])
        core.uninstall(self.game)
        self.assertEqual(path.read_bytes(), b"custom master\n")

    def test_existing_sidecar_is_backed_up_and_restored_as_set(self):
        old = self.target("cfg/sfm_shared_authority/sfm_master_0_" + "a" * 64 + ".sfmsidecar")
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_bytes(b"custom sidecar\n")
        with self.assertRaisesRegex(core.Refusal, "consent"):
            core.install(self.game, self.prepared)
        summary = core.preview(self.game, self.prepared)
        core.install(self.game, self.prepared, replace_authority=True,
                     expected_authority=summary["authority_snapshot"])
        self.assertFalse(old.exists())
        core.uninstall(self.game)
        self.assertEqual(old.read_bytes(), b"custom sidecar\n")

    def test_partial_button_and_running_process_refuse(self):
        button = self.target(core.BUTTON)
        button.parent.mkdir(parents=True, exist_ok=True)
        button.write_bytes(b"partial\n")
        with self.assertRaisesRegex(core.Refusal, "partial"):
            core.preview(self.game, self.prepared)
        button.unlink()
        with mock.patch.object(core, "process_status", return_value=("RUNNING", "test")):
            with self.assertRaisesRegex(core.Refusal, "closed"):
                core.install(self.game, self.prepared)
        self.assertFalse(self.target(core.MASTER).exists())

    def test_updater_lock_excludes_install_and_matching_file_is_adopted(self):
        match = self.target("scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py")
        match.parent.mkdir(parents=True, exist_ok=True)
        source = self.prepared.root / "data" / "scripts" / "ChadChan3D_CPM" / match.name
        match.write_bytes(source.read_bytes())
        self.assertEqual(core.preview(self.game, self.prepared)["write_count"], 1005)
        with core._Lock(self.game):
            with self.assertRaisesRegex(core.Refusal, "busy"):
                core.install(self.game, self.prepared)
        self.assertFalse(self.target(core.MASTER).exists())

    def test_interrupted_transaction_recovery(self):
        real_put, count = core._put_file, [0]

        def interrupted(source, destination, previous):
            count[0] += 1
            if count[0] == 8:
                raise RuntimeError("simulated interruption")
            return real_put(source, destination, previous)

        with mock.patch.object(core, "_put_file", side_effect=interrupted), \
                mock.patch.object(core, "_restore", side_effect=RuntimeError("simulated exit")):
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                core.install(self.game, self.prepared)
        self.assertEqual(core._current_record(self.game)["status"], "PREPARED")
        steps = (core._state_root(self.game) / "transactions" /
                 core._current_record(self.game)["id"] / "steps.jsonl")
        self.assertIn(b'"phase": "BEFORE"', steps.read_bytes())
        self.assertIn("restored", core.recover(self.game))
        self.assertEqual(core._current_record(self.game)["status"], "ROLLED_BACK")
        self.assertFalse(self.target(core.MASTER).exists())

    def test_installer_state_reparse_points_refuse(self):
        original_lstat = Path.lstat
        root = self.game / "usermod" / "cfg" / "sfm_character_tools_installer"
        for blocked in (root, root / "transactions", root / "transactions" / ("a" * 32) / "backups"):
            def lstat(path, *args, **kwargs):
                if path == blocked:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return original_lstat(path, *args, **kwargs)

            with self.subTest(path=str(blocked)):
                with mock.patch.object(Path, "lstat", lstat):
                    with self.assertRaisesRegex(core.Refusal, "reparse point"):
                        core._state_path(self.game, "transactions", "a" * 32, "backups", core.MASTER)
                    if blocked == root:
                        with self.assertRaisesRegex(core.Refusal, "reparse point"):
                            core.install(self.game, self.prepared)
        self.assertFalse(root.exists())

    def test_authority_change_after_consent_refuses(self):
        master = self.target(core.MASTER)
        master.parent.mkdir(parents=True, exist_ok=True)
        master.write_bytes(b"original custom master\n")
        summary = core.preview(self.game, self.prepared)
        master.write_bytes(b"later custom master\n")
        with self.assertRaisesRegex(core.Refusal, "changed since consent"):
            core.install(self.game, self.prepared, replace_authority=True,
                         expected_authority=summary["authority_snapshot"])
        self.assertEqual(master.read_bytes(), b"later custom master\n")
        self.assertFalse(self.target(core.MANIFEST).exists())

    def test_interrupted_uninstall_respects_preserved_groups(self):
        core.install(self.game, self.prepared)
        master = self.target(core.MASTER)
        button = self.target(core.BUTTON)
        master.write_bytes(b"user edit\n")
        button.write_bytes(b"user edit\n")
        real_remove, count = core._remove_if_new, [0]

        def interrupted(*args):
            count[0] += 1
            if count[0] == 4:
                raise RuntimeError("simulated interrupted removal")
            return real_remove(*args)

        with mock.patch.object(core, "_remove_if_new", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "interrupted removal"):
                core.uninstall(self.game)
        record = core._current_record(self.game)
        self.assertEqual(record["status"], "UNINSTALLING")
        self.assertEqual(record["preserved_hashes"][core.MASTER], core.digest_file(master))
        master.write_bytes(b"later user edit\n")
        with self.assertRaisesRegex(core.Refusal, "changed during removal"):
            core.uninstall(self.game)
        master.write_bytes(b"user edit\n")
        result = core.uninstall(self.game)
        self.assertIn(core.MASTER, result["preserved"])
        self.assertIn(core.BUTTON, result["preserved"])
        self.assertEqual(master.read_bytes(), b"user edit\n")
        self.assertEqual(button.read_bytes(), b"user edit\n")

    def test_uninstall_preserves_changed_authority_and_button_pair(self):
        core.install(self.game, self.prepared)
        master = self.target(core.MASTER)
        master.write_bytes(b"user edit\n")
        button = self.target(core.BUTTON)
        button.write_bytes(b"user edit\n")
        result = core.uninstall(self.game)
        self.assertIn(core.MASTER, result["preserved"])
        self.assertIn(core.BUTTON, result["preserved"])
        self.assertTrue(self.target(core.MANIFEST).exists())
        self.assertTrue(self.target(core.BUTTON_IMPL).exists())


if __name__ == "__main__":
    unittest.main()
