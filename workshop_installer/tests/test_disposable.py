"""Decision-focused Windows tests; every destination is a disposable directory."""
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from workshop_installer import core, release


class DisposableInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = os.environ.get("SCT_V1_RELEASE_ZIP")
        if not source:
            raise unittest.SkipTest("Set SCT_V1_RELEASE_ZIP to the unchanged release archive")
        cls.full = core.prepare(source, Path(__file__))
        # Use real signed-inventory members and authority for short state-machine
        # tests. The separate full-install test exercises every release member.
        inventory_path = "scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json"
        inv = json.loads((cls.full.root / "data" / inventory_path).read_bytes())
        names = {r["path"] for r in inv["files"]}
        names |= {inventory_path, inventory_path[:-5] + ".sig", core.HELPER, core.MANAGER,
                  core.BUTTON, core.BUTTON_IMPL, core.MASTER, core.MANIFEST, cls.full.sidecar}
        cls.prepared = core.Prepared(cls.full.root, {p: cls.full.files[p] for p in names}, cls.full.sidecar)

    @classmethod
    def tearDownClass(cls):
        cls.full.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sct_install_test_")
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "game"
        (self.game / "usermod" / "cfg").mkdir(parents=True)
        for rel in ("scripts/sfm/autoinit/autoinit_manager.py", "scripts/sfm/sfm_init_local.py",
                    "scripts/sfm/mainmenu/kiwifruitdev/autoinit_manager.py"):
            p = self.game / "workshop" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"disposable dependency marker")
        patcher = mock.patch.object(core, "process_status", return_value=("CLEAR", "test"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def target(self, rel):
        return core._target(self.game, rel)

    def write(self, rel, data):
        p = self.target(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def install(self, prepared=None):
        p = prepared or self.prepared
        return core.install(self.game, p, core.preview(self.game, p)["snapshot"])

    def uninstall(self):
        return core.uninstall(self.game, core.removal_preview(self.game))

    def backups(self):
        p = core._state_path(self.game, "backups")
        return list(p.iterdir()) if p.exists() else []

    def test_full_release_install_and_remove(self):
        self.assertEqual(len(self.full.files), 1006)
        self.install(self.full)
        for rel, wanted in self.full.files.items():
            self.assertEqual(core.digest_file(self.target(rel)), wanted)
        self.assertFalse(core._operation(self.game))
        self.uninstall()
        self.assertTrue(self.target(core.MASTER).exists())
        self.assertFalse(self.target(core.MANIFEST).exists())
        self.assertFalse(self.target(core.AUTH_DIR).exists())
        self.assertFalse(self.target(core.BUTTON).exists())
        self.assertFalse(self.target(core.MANAGER).exists())
        self.assertFalse(self.target(core.HELPER).exists())
        self.assertFalse(self.backups())

    def test_existing_txt_backed_up_and_retained_on_uninstall(self):
        self.write(core.MASTER, b"artist custom TXT\n")
        self.install()
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b"artist custom TXT\n")
        installed = self.target(core.MASTER).read_bytes()
        self.uninstall()
        self.assertEqual(self.target(core.MASTER).read_bytes(), installed)
        self.assertEqual(backups[0].read_bytes(), b"artist custom TXT\n")
        self.assertEqual([p for p in core._state_root(self.game).rglob("*") if p.is_file()], backups)

    def test_backup_failure_changes_no_programs(self):
        self.write(core.MASTER, b"custom")
        with mock.patch.object(core, "_backup_master", side_effect=OSError("backup disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.install()
        self.assertEqual(self.target(core.MASTER).read_bytes(), b"custom")
        self.assertFalse(self.target(core.HELPER).exists())
        self.assertFalse(core._operation(self.game))

    def test_reinstall_repairs_modified_programs_and_partial_button(self):
        self.install()
        self.target(core.BUTTON).unlink()
        self.target(core.BUTTON_IMPL).write_bytes(b"edited program")
        self.install()
        self.assertEqual(core.digest_file(self.target(core.BUTTON_IMPL)), self.prepared.files[core.BUTTON_IMPL])
        self.assertTrue(self.target(core.BUTTON).exists())
        self.assertEqual(len(self.backups()), 1)
        self.uninstall()
        self.assertFalse(self.target(core.BUTTON_IMPL).exists())

    def test_next_release_removes_obsolete_program_and_bytecode(self):
        self.install()
        old = "tools/SFM Control Group Updater/previous.dat"
        added = "tools/SFM Control Group Updater/new.dat"
        module = "scripts/ChadChan3D_CPM/old_module.py"
        for p in (old, module, module + "c", module + "o"):
            self.write(p, b"previous release")
        receipt = core._current_record(self.game)
        receipt["programs"] += [old, module]
        core._write_json(core._state_path(self.game, "installation.json"), receipt)
        new_source = self.prepared.root / "data" / added
        new_source.parent.mkdir(parents=True, exist_ok=True)
        new_source.write_bytes(b"next release member")
        self.addCleanup(new_source.unlink)
        files = dict(self.prepared.files, **{added: core.digest_file(new_source)})
        new = core.Prepared(self.prepared.root, files, self.prepared.sidecar, "test-next", "b" * 64)
        self.install(new)
        self.assertEqual(self.target(added).read_bytes(), b"next release member")
        for p in (old, module, module + "c", module + "o"):
            self.assertFalse(self.target(p).exists())
        self.assertEqual(core._current_record(self.game)["version"], "test-next")

    def interrupt_install(self):
        real_put, count = core._put_file, [0]
        def stop(*args, **kwargs):
            count[0] += 1
            if count[0] == 8:
                raise RuntimeError("simulated exit")
            return real_put(*args, **kwargs)
        with mock.patch.object(core, "_put_file", side_effect=stop):
            with self.assertRaisesRegex(RuntimeError, "simulated exit"):
                self.install()

    def test_interruption_completes_without_old_program_backups(self):
        self.write(core.MASTER, b"original TXT")
        self.interrupt_install()
        record = core._operation(self.game)
        self.assertEqual(record["kind"], "install")
        original_backup = self.backups()[0]
        self.assertEqual(original_backup.read_bytes(), b"original TXT")
        self.assertTrue(self.target(core.MANAGER).exists())
        core.recover(self.game, self.prepared)
        self.assertIsNone(core._operation(self.game))
        self.assertEqual(self.backups(), [original_backup])
        self.assertEqual(original_backup.read_bytes(), b"original TXT")
        self.assertFalse((core._state_root(self.game) / "transactions").exists())

    def test_wrong_package_and_intervening_txt_edit_refuse_retry(self):
        self.write(core.MASTER, b"original TXT")
        self.interrupt_install()
        wrong = core.Prepared(self.prepared.root, self.prepared.files, self.prepared.sidecar, package="c" * 64)
        with self.assertRaisesRegex(core.Refusal, "exact package"):
            core.recover(self.game, wrong)
        self.target(core.MASTER).write_bytes(b"later TXT edit")
        with self.assertRaisesRegex(core.RecoveryConflict, core.MASTER):
            core.recover(self.game, self.prepared)
        self.assertEqual(self.target(core.MASTER).read_bytes(), b"later TXT edit")
        self.assertEqual(self.backups()[0].read_bytes(), b"original TXT")
        with self.assertRaises(TypeError):
            core.recover(self.game)  # No fallback to installed files or a different package.

    def test_recover_requires_autoinit_but_uninstall_does_not(self):
        self.interrupt_install()
        autoinit = self.game / "workshop" / "scripts" / "sfm" / "autoinit" / "autoinit_manager.py"
        original = autoinit.read_bytes()
        autoinit.unlink()
        with mock.patch.object(core, "_put_file", side_effect=AssertionError("recovery wrote a file")):
            with self.assertRaisesRegex(core.Refusal, "Restore Autoinit Manager"):
                core.recover(self.game, self.prepared)
        self.assertEqual(core._operation(self.game)["kind"], "install")
        autoinit.write_bytes(original)
        core.recover(self.game, self.prepared)
        self.assertIsNone(core._operation(self.game))
        autoinit.unlink()
        self.uninstall()
        self.assertFalse(self.target(core.MANAGER).exists())

    def test_consent_snapshot_and_process_checks(self):
        summary = core.preview(self.game, self.prepared)
        self.write(core.MASTER, b"new custom TXT")
        with self.assertRaisesRegex(core.Refusal, "since consent"):
            core.install(self.game, self.prepared, summary["snapshot"])
        for status in ("RUNNING", "UNKNOWN"):
            with mock.patch.object(core, "process_status", return_value=(status, "test")):
                with self.assertRaisesRegex(core.Refusal, "closed"):
                    self.install()
        self.assertFalse(self.target(core.HELPER).exists())

    def test_real_updater_lock_excludes_install(self):
        with core._Lock(self.game):
            with self.assertRaisesRegex(core.Refusal, "busy"):
                self.install()
        self.assertFalse(self.target(core.HELPER).exists())

    def test_uninstall_without_payload_or_autoinit_preserves_unrelated_files(self):
        self.install()
        self.target(core.BUTTON_IMPL).write_bytes(b"modified program approved for removal")
        sidecar = core.AUTH_DIR + "/sfm_master_0_" + "a" * 64 + ".sfmsidecar"
        self.write(sidecar, b"later updater generation")
        unknown = self.write(core.AUTH_DIR + "/artist-notes.txt", b"keep")
        record = self.write("cfg/sfm_character_tools_backups/keep.txt", b"updater backup")
        unrelated = self.write("scripts/ChadChan3D_CPM/artist.py", b"unrelated")
        shutil.rmtree(self.game / "workshop")
        (self.game / "workshop").mkdir()
        with mock.patch.object(core, "prepare", side_effect=AssertionError("uninstall must not prepare")):
            result = self.uninstall()
        self.assertFalse(self.target(sidecar).exists())
        self.assertFalse(self.target(core.BUTTON_IMPL).exists())
        for p in (unknown, record, unrelated):
            self.assertTrue(p.exists())
        self.assertEqual(result["authority_remaining"], ["artist-notes.txt"])

    def test_interrupted_uninstall_retains_management_and_resumes(self):
        self.install()
        real_remove, count = core._remove_if_new, [0]
        def stop(*args):
            count[0] += 1
            if count[0] == 4:
                raise RuntimeError("simulated removal exit")
            return real_remove(*args)
        with mock.patch.object(core, "_remove_if_new", side_effect=stop):
            with self.assertRaisesRegex(RuntimeError, "removal exit"):
                self.uninstall()
        self.assertTrue(self.target(core.MANAGER).exists())
        self.assertTrue(self.target(core.HELPER).exists())
        self.assertEqual(core._operation(self.game)["kind"], "uninstall")
        core.uninstall(self.game)
        self.assertIsNone(core._operation(self.game))
        self.assertFalse(self.target(core.MANAGER).exists())

    def test_failed_lock_cleanup_keeps_management_pair_for_retry(self):
        self.install()
        self.write(core.AUTH_DIR + "/publisher.lock", b"")
        with mock.patch.object(core._LegacyLock, "remove", side_effect=core.Refusal("lock cleanup failed")):
            with self.assertRaisesRegex(core.Refusal, "lock cleanup failed"):
                self.uninstall()
        self.assertTrue(self.target(core.MANAGER).exists())
        self.assertTrue(self.target(core.HELPER).exists())
        core.uninstall(self.game)
        self.assertIsNone(core._operation(self.game))
        self.assertFalse(self.target(core.HELPER).exists())

    def test_running_helper_is_reported_for_manual_cleanup(self):
        self.install()
        with mock.patch.object(core, "_running_helper", return_value=True):
            result = self.uninstall()
        self.assertEqual(result["remaining_helper"], [core.HELPER])
        self.assertTrue(self.target(core.HELPER).exists())
        self.assertFalse(self.target(core.MANAGER).exists())

    def test_legacy_lock_valid_deleted_busy_and_unrecognized_refuse(self):
        self.install()
        lock = self.write(core.AUTH_DIR + "/publisher.lock", b"")
        h, _ = core.w32.create_file(str(lock), core.w32.GENERIC_READ, 0, core.w32.OPEN_EXISTING)
        self.assertIsNotNone(h)
        try:
            with self.assertRaisesRegex(core.Refusal, "in use"):
                self.uninstall()
        finally:
            core.w32.close(h)
        self.assertTrue(self.target(core.MANAGER).exists())
        lock.write_bytes(b"unrecognized")
        with self.assertRaisesRegex(core.Refusal, "recognized empty"):
            self.uninstall()
        self.assertTrue(self.target(core.MANAGER).exists())
        lock.write_bytes(b"")
        self.uninstall()
        self.assertFalse(lock.exists())
        self.assertFalse(self.target(core.AUTH_DIR).exists())

    def test_legacy_lock_single_link_and_install_preservation(self):
        lock = self.write(core.AUTH_DIR + "/publisher.lock", b"")
        alias = self.game / "outside-lock-alias"
        os.link(lock, alias)
        with self.assertRaisesRegex(core.Refusal, "recognized empty"):
            self.install()
        alias.unlink()
        self.install()
        self.assertTrue(lock.exists())

    def test_installer_state_reparse_points_refuse(self):
        original = Path.lstat
        root = self.target(core.STATE_REL)
        for blocked in (root, root / "backups", root / "operation.json"):
            def lstat(path, *args, **kwargs):
                if path == blocked:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return original(path, *args, **kwargs)
            with self.subTest(component=blocked.name), mock.patch.object(Path, "lstat", lstat):
                with self.assertRaisesRegex(core.Refusal, "reparse point"):
                    core._state_path(self.game, "backups" if blocked.name != "operation.json" else "operation.json")
        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
