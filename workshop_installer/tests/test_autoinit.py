"""Mounted dependency detection in disposable directories; no SFM execution."""
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from workshop_installer import core


class MountedAutoinitTests(unittest.TestCase):
    FILES = ("scripts/sfm/autoinit/autoinit_manager.py", "scripts/sfm/sfm_init_local.py",
             "scripts/sfm/mainmenu/kiwifruitdev/autoinit_manager.py")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sct_mount_test_")
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "game"
        (self.game / "usermod").mkdir(parents=True)
        (self.game / "workshop").mkdir()
        self.config = self.game / "usermod" / "gameinfo.txt"
        self.mounts('Game "|gameinfo_path|." Game "workshop"')

    def mounts(self, entries):
        self.config.write_text('GameInfo { FileSystem { SearchPaths { ' + entries +
                               ' } } }\n', encoding="utf-8")

    def dependency(self, mod):
        root = self.game / mod
        for rel in self.FILES:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"disposable dependency")
        return root

    def test_mounted_workshop_archive_is_accepted(self):
        self.dependency("workshop_archive")
        self.mounts('// ordinary mount\n "Game" "workshop_archive" /* end */')
        self.assertTrue(core._check_autoinit(self.game))

    def test_unmounted_and_commented_archive_are_rejected(self):
        self.dependency("workshop_archive")
        self.assertFalse(core._check_autoinit(self.game))
        for comment in ('// Game "workshop_archive"\n', '/* Game "workshop_archive" */'):
            self.mounts('Game "workshop" ' + comment)
            self.assertFalse(core._check_autoinit(self.game))
        self.config.write_text('GameInfo { Game "workshop_archive" '
                               'FileSystem { SearchPaths { Game "workshop" } } }', encoding="utf-8")
        self.assertFalse(core._check_autoinit(self.game))

    def test_missing_file_and_split_dependency_are_rejected(self):
        root = self.dependency("workshop_archive")
        self.mounts('Game "workshop_archive" Game "workshop"')
        (root / self.FILES[0]).unlink()
        other = self.game / "workshop" / self.FILES[0]
        other.parent.mkdir(parents=True)
        other.write_bytes(b"separate dependency fragment")
        self.assertFalse(core._check_autoinit(self.game))

    def test_reparse_configuration_mount_and_dependency_are_rejected(self):
        root = self.dependency("workshop_archive")
        self.mounts('Game "workshop_archive"')
        original = Path.lstat
        for blocked in (self.config, root, root / "scripts", root / self.FILES[0]):
            def lstat(path, *args, **kwargs):
                if path == blocked:
                    return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
                return original(path, *args, **kwargs)
            with self.subTest(component=blocked.name), mock.patch.object(Path, "lstat", lstat):
                with self.assertRaisesRegex(core.Refusal, "location could not be verified.*reparse"):
                    core._check_autoinit(self.game)

    def test_default_mounts_qualify_only_when_configured(self):
        for mod in ("usermod", "workshop"):
            with self.subTest(mount=mod):
                self.dependency(mod)
                self.mounts('Game "|gameinfo_path|." Game "workshop"')
                self.assertTrue(core._check_autoinit(self.game))
                self.mounts('Game "empty_mod"')
                self.assertFalse(core._check_autoinit(self.game))
                shutil.rmtree(self.game / mod / "scripts")

    def test_unsupported_paths_and_directives_cannot_establish_a_mount(self):
        self.dependency("workshop")
        for path in ("../outside", "/outside", "C:/outside", "workshop/*", "workshop/..",
                     "|all_source_engine_paths|workshop", "workshop."):
            with self.subTest(path=path):
                # A supported earlier mount must not hide an uninterpretable entry.
                self.mounts('Game "workshop" Game "' + path + '"')
                with self.assertRaisesRegex(core.Refusal, "location could not be verified"):
                    core._check_autoinit(self.game)
        for entry in ('Game "workshop" [$WIN32]', '#include "other.txt"'):
            self.mounts(entry)
            with self.assertRaisesRegex(core.Refusal, "conditional/include"):
                core._check_autoinit(self.game)

    def test_missing_or_ambiguous_configuration_is_not_treated_as_a_mount(self):
        self.dependency("workshop")
        self.config.unlink()
        with self.assertRaisesRegex(core.Refusal, "location could not be verified"):
            core._check_autoinit(self.game)
        for text in ('GameInfo { FileSystem { SearchPaths { Game "workshop" } }',
                     'GameInfo { FileSystem { SearchPaths { Game "workshop" } SearchPaths {} } }'):
            self.config.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(core.Refusal, "location could not be verified"):
                core._check_autoinit(self.game)


if __name__ == "__main__":
    unittest.main()
