"""v1.1.0 release binding: the official archive, refusal of other archives, and an upgrade from a v1.0.0 Workshop
installation. Every destination is a disposable directory.

SCT_V1_RELEASE_ZIP     the official SFM.Character.Tools.v1.1.0.zip (release.py's archive)
SCT_V100_RELEASE_ZIP   the v1.0.0 Workshop archive (Archive A) that earlier Setup installed (upgrade test only)
"""
import contextlib
import hashlib
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from workshop_installer import core, release, stage

V100 = {"VERSION": "1.0.0", "ARCHIVE": "SFM.Character.Tools.v1.0.0.zip",
        "SHA256": "5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458",
        "ARCHIVE_ENTRIES": 1006, "INVENTORY_ENTRIES": 31}
REGISTRIES = {"scripts/SFM Character Tools/cpm_pose_profiles_v1.json":
              "f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00",
              "scripts/SFM Character Tools/cpm_body_profiles_v1.json":
              "a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622"}
CPM = "scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py"
CPM_V110 = "b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525"
CPM_V100 = "ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df"
INVENTORY = "scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json"
INVENTORY_V110 = "15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948"


def release_zip():
    source = os.environ.get("SCT_V1_RELEASE_ZIP")
    if not source:
        raise unittest.SkipTest("Set SCT_V1_RELEASE_ZIP to the official v1.1.0 archive")
    return source


class ReleaseBindingTests(unittest.TestCase):
    def test_release_constants_describe_the_official_archive(self):
        source = release_zip()
        self.assertEqual(release.VERSION, "1.1.0")
        self.assertEqual(release.ARCHIVE, os.path.basename(source))
        self.assertEqual(core.digest_file(source), release.SHA256)
        with zipfile.ZipFile(source) as z:
            names = z.namelist()
        self.assertEqual(len(names), release.ARCHIVE_ENTRIES)
        self.assertEqual({core._map_member(n) for n in names} - {None}, set(release.PATHS))
        self.assertTrue(set(REGISTRIES) <= set(release.PATHS))

    def test_prepared_package_has_the_pose_library_files(self):
        p = core.prepare(release_zip(), Path(__file__))
        try:
            self.assertEqual((p.version, p.package), ("1.1.0", release.SHA256))
            self.assertEqual(len(p.files), len(release.PATHS) + 2)  # plus Setup helper and management launcher
            for rel, wanted in REGISTRIES.items():
                self.assertEqual(p.files[rel], wanted)
            self.assertEqual(p.files[CPM], CPM_V110)
            self.assertEqual(p.files[INVENTORY], INVENTORY_V110)
        finally:
            p.close()

    def test_other_and_tampered_archives_refuse(self):
        source = release_zip()
        tmp = tempfile.TemporaryDirectory(prefix="sct_v110_refusal_")
        self.addCleanup(tmp.cleanup)
        tampered = Path(tmp.name) / release.ARCHIVE
        with zipfile.ZipFile(source) as src, zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                data = src.read(info)
                if info.filename == "usermod/" + CPM:
                    data += b"\n# tampered\n"
                dst.writestr(info, data)
        candidates = [tampered]
        v100 = os.environ.get("SCT_V100_RELEASE_ZIP")
        if v100:
            candidates.append(Path(v100))
        for candidate in candidates:
            with self.subTest(archive=str(candidate)):
                with self.assertRaisesRegex(core.Refusal, "not the approved v1.1.0 artifact"):
                    core.prepare(str(candidate), Path(__file__))
                with self.assertRaisesRegex(ValueError, "approved v1.1.0 artifact"):
                    stage.stage(Path(candidate), Path(__file__), Path(tmp.name) / "stage_out")
                self.assertFalse((Path(tmp.name) / "stage_out").exists())


class UpgradeFromV100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        new = release_zip()
        old = os.environ.get("SCT_V100_RELEASE_ZIP")
        if not old:
            raise unittest.SkipTest("Set SCT_V100_RELEASE_ZIP to the v1.0.0 Workshop archive")
        with cls.as_v100_setup():
            cls.old = core.prepare(old, Path(__file__))
        # What v1.0.0 Setup recorded: its own version and package identity.
        cls.old.version, cls.old.package = V100["VERSION"], V100["SHA256"]
        cls.new = core.prepare(new, Path(__file__).with_name("test_disposable.py"))

    @staticmethod
    def as_v100_setup():
        """v1.0.0 Setup's release constants (its release.py), for preparing and installing the v1.0.0 archive."""
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.multiple(
            release, PATHS=tuple(p for p in release.PATHS if p not in REGISTRIES), **V100))
        stack.enter_context(mock.patch.object(core, "RELEASE_SHA256", V100["SHA256"]))
        return stack

    @classmethod
    def tearDownClass(cls):
        cls.old.close()
        cls.new.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sct_upgrade_test_")
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "game"
        (self.game / "usermod" / "cfg").mkdir(parents=True)
        (self.game / "usermod" / "gameinfo.txt").write_text(
            '"GameInfo" { "FileSystem" { "SearchPaths" { '
            '"Game" "|gameinfo_path|." "Game" "workshop" } } }\n', encoding="utf-8")
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

    def install(self, prepared):
        return core.install(self.game, prepared, core.preview(self.game, prepared)["snapshot"])

    def snapshot(self, root):
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    def test_upgrade_preserves_user_data_installs_pose_library_and_uninstalls(self):
        with self.as_v100_setup():
            self.install(self.old)
        self.assertEqual(core._current_record(self.game)["version"], "1.0.0")
        self.assertEqual(core.digest_file(self.target(CPM)), CPM_V100)
        for rel in REGISTRIES:
            self.assertFalse(self.target(rel).exists())

        # The artist's own state after using v1.0.0: a customized TXT, updater backups, SFM settings, another
        # add-on, Autoinit's own files, CPM bytecode, and a preset library outside the SFM folder.
        self.target(core.MASTER).write_bytes(b"artist-customized Animation Groups\n")
        user = [self.write("cfg/sfm_character_tools_backups/earlier.txt", b"updater backup"),
                self.write("cfg/config.cfg", b"bind x y"),
                self.write("scripts/sfm/mainmenu/Other Addon/tool.py", b"unrelated add-on"),
                self.write("scripts/ChadChan3D_CPM/artist_notes.txt", b"keep")]
        autoinit_before = self.snapshot(self.game / "workshop")
        library = Path(self.tmp.name) / "Documents" / "SFM Character Preset Manager"
        for rel, data in (("Characters/krystal/Body Presets/Tall.json", b"{}"),
                          ("Characters/krystal/Expressions/Smile.json", b"{}"),
                          ("Characters/krystal/library.json", b'{"favorites": []}')):
            (library / rel).parent.mkdir(parents=True, exist_ok=True)
            (library / rel).write_bytes(data)
        library_before = self.snapshot(library)

        summary = core.preview(self.game, self.new)
        self.assertTrue(summary["existing"])
        self.assertEqual((summary["installed_version"], summary["version"]), ("1.0.0", "1.1.0"))
        self.install(self.new)

        record = core._current_record(self.game)
        self.assertEqual((record["version"], record["package"]), ("1.1.0", release.SHA256))
        for rel, wanted in self.new.files.items():
            self.assertEqual(core.digest_file(self.target(rel)), wanted, rel)
        for rel, wanted in REGISTRIES.items():
            self.assertEqual(core.digest_file(self.target(rel)), wanted)
        self.assertEqual(core.digest_file(self.target(CPM)), CPM_V110)
        self.assertIn(self.new.files[core.HELPER].encode("ascii"), self.target(core.MANAGER).read_bytes())
        backups = list(core._state_path(self.game, "backups").iterdir())
        self.assertTrue(any(p.read_bytes() == b"artist-customized Animation Groups\n" for p in backups))
        for p in user:
            self.assertTrue(p.exists(), p)
        self.assertEqual(self.snapshot(self.game / "workshop"), autoinit_before)
        self.assertEqual(self.snapshot(library), library_before)

        result = core.uninstall(self.game, core.removal_preview(self.game))
        self.assertFalse(result.get("remaining_helper"))
        for rel in list(REGISTRIES) + [CPM, core.BUTTON, core.BUTTON_IMPL, core.MANAGER, core.HELPER,
                                       core.MANIFEST, INVENTORY]:
            self.assertFalse(self.target(rel).exists(), rel)
        self.assertTrue(self.target(core.MASTER).exists())
        self.assertTrue(all(p.exists() for p in backups))
        for p in user:
            self.assertTrue(p.exists(), p)
        self.assertEqual(self.snapshot(self.game / "workshop"), autoinit_before)
        self.assertEqual(self.snapshot(library), library_before)


if __name__ == "__main__":
    unittest.main()
