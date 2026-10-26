"""Decision-focused native-window tests; no SFM or live installation access."""
import ctypes
import threading
import time
import unittest
from ctypes import wintypes as wt
from pathlib import Path
from unittest import mock

from workshop_installer import app, core, stage
from workshop_installer.window import Window, user32
from updater.sfm_character_tools_updater import process_gate

user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.IsWindow.argtypes = [wt.HWND]
user32.IsWindow.restype = wt.BOOL


def caption(handle):
    value = ctypes.create_unicode_buffer(8192)
    user32.GetWindowTextW(handle, value, len(value))
    return value.value


def message(window):
    return caption([h for h in window.children
                    if h not in window.buttons and h != window.details_handle][-1])


def labels(window):
    return {caption(h) for h in window.buttons}


class WindowTests(unittest.TestCase):
    def setup_window(self):
        setup = app.SetupWindow(Path("game"), None, Path("SCT_Setup.exe"))
        self.addCleanup(setup.window.dispose)
        return setup

    def complete(self, setup):
        deadline = time.monotonic() + 5
        while setup.worker is not None:
            self.assertLess(time.monotonic(), deadline, "worker did not finish")
            setup.poll()
            time.sleep(.005)

    def test_windowed_help_does_not_require_console_streams(self):
        parser = app._SetupParser()
        with mock.patch("sys.stdout", None), mock.patch("sys.stderr", None):
            with self.assertRaises(SystemExit) as result:
                parser.parse_args(["--help"])
        self.assertEqual(result.exception.code, 0)

    def test_menu_sources_preserve_python2_grammar(self):
        from lib2to3.refactor import RefactoringTool
        parser = RefactoringTool([])
        for name, source in (("workshop-menu", stage.launcher("a" * 64, "b" * 64)),
                             ("installed-menu", core._manager_source("a" * 64))):
            text = source.decode("ascii")
            parser.refactor_string(text, name)
            compile(text, name, "exec", dont_inherit=True)

    def test_named_actions_crlf_details_busy_close_and_stale_click(self):
        window = Window("Disposable Setup check")
        self.addCleanup(window.dispose)
        called = []
        window.page("Setup", "", app.UPDATE,
                    [("Update / Reinstall", lambda: called.append("update")),
                     ("Uninstall", lambda: called.append("remove")), ("Close", window.close)])
        old_id = min(window.actions)
        window.details("first\nsecond\r\nthird\rfourth")
        self.assertEqual(caption(window.details_handle), "first\r\nsecond\r\nthird\r\nfourth")
        old_details = window.details_handle
        window.details("not another control")
        self.assertEqual(window.details_handle, old_details)
        window.set_busy(True)
        window._message(window.hwnd, 0x111, old_id, 0)
        window._message(window.hwnd, 0x10, 0, 0)
        self.assertTrue(user32.IsWindow(window.hwnd))
        self.assertEqual(called, [])
        window.set_busy(False)
        window.page("Complete", "", "Done", [("Close", lambda: called.append("close"))])
        window._message(window.hwnd, 0x111, old_id, 0)
        self.assertEqual(called, [])
        self.assertIsNone(window.details_handle)

    def test_missing_payload_is_normal_management_with_uninstall(self):
        setup = self.setup_window()
        with mock.patch.object(core, "_legacy_record_clear"), \
                mock.patch.object(core, "_operation", return_value=None), \
                mock.patch.object(core, "_current_record", return_value={"version": "1.0.0"}), \
                mock.patch.object(core, "removal_preview", return_value={core.BUTTON: "a" * 64}):
            setup.shown()
            self.complete(setup)
        self.assertEqual(caption(setup.window.children[0]), "Manage SFM Character Tools")
        self.assertEqual(labels(setup.window), {"Uninstall", "Close"})
        self.assertIn("Installed version: 1.0.0", caption(setup.window.children[1]))
        self.assertNotIn("Package version", caption(setup.window.children[1]))
        self.assertIn("still uninstall", message(setup.window))

    def test_changed_file_shows_blocked_recovery_without_retry(self):
        setup = self.setup_window()
        with mock.patch.object(core, "_legacy_record_clear"), \
                mock.patch.object(core, "_operation", return_value={"kind": "install"}), \
                mock.patch.object(core, "_resume_states", side_effect=core.RecoveryConflict(core.MASTER)):
            setup.shown()
            self.complete(setup)
        text = message(setup.window)
        self.assertIn(core.MASTER, text)
        self.assertIn("Preserve your changes", text)
        self.assertEqual(labels(setup.window), {"Close"})

    def test_preparation_starts_only_after_shown_and_runs_off_ui(self):
        with mock.patch.object(app.SetupWindow, "inspect", return_value={}) as inspect:
            setup = self.setup_window()
            inspect.assert_not_called()
            self.assertEqual(caption(setup.window.children[0]), "Preparing Setup")
            setup.review = mock.Mock()
            setup.shown()
            self.complete(setup)
            inspect.assert_called_once()
            setup.review.assert_called_once_with({})

    def test_install_uses_the_reviewed_snapshot_and_verifies_before_success(self):
        setup = self.setup_window()
        setup.busy = False
        snapshot = {core.MASTER: "original"}
        setup.review({"operation": None, "existing": False, "installed_version": None,
                      "summary": {"snapshot": snapshot, "existing": False, "version": "1.0.0"}})
        self.assertIn("Package version: 1.0.0", caption(setup.window.children[1]))
        self.assertIn("Installation folder:", caption(setup.window.children[1]))
        self.assertIn("Setup will install SFM Character Tools version 1.0.0.\n\n", message(setup.window))
        prepared = mock.Mock()
        setup.prepared = prepared
        with mock.patch.object(core, "install", return_value={"backup": None}) as install:
            setup.install()
            self.complete(setup)
        install.assert_called_once_with(setup.game, prepared, snapshot)
        self.assertEqual(caption(setup.window.children[0]), "Installation complete")
        self.assertEqual(labels(setup.window), {"Close"})
        setup.prepared = None

    def test_corrupt_package_cannot_be_presented_as_ordinary_absence(self):
        setup = self.setup_window()
        setup.review({"operation": None, "existing": True, "installed_version": "1.0.0",
                      "package_error": "wrong archive SHA-256"})
        self.assertEqual(caption(setup.window.children[0]), "Installation package could not be verified")
        self.assertEqual(labels(setup.window), {"Uninstall", "Details", "Close"})
        self.assertIn("wrong archive SHA-256", setup.details)

    def test_single_worker_defers_success_blocks_clicks_close_and_source_cleanup(self):
        setup = self.setup_window()
        setup.busy = False
        setup.window.set_busy(False)
        entered, release = threading.Event(), threading.Event()
        owner = threading.get_ident()
        workers, done = [], []
        source = mock.Mock()
        setup.prepared = source
        def slow():
            workers.append(threading.get_ident())
            entered.set()
            self.assertTrue(release.wait(3))
            return 42
        setup.start("Working", slow, lambda result: done.append((result, threading.get_ident())))
        self.assertTrue(entered.wait(2))
        setup.start("Wrong", lambda: workers.append("duplicate"), lambda _: None)
        setup.close()
        setup.window._message(setup.window.hwnd, 0x10, 0, 0)
        setup.poll()
        self.assertTrue(setup.busy)
        self.assertEqual(done, [])
        source.close.assert_not_called()
        self.assertTrue(user32.IsWindow(setup.window.hwnd))
        release.set()
        self.complete(setup)
        self.assertEqual(len(workers), 1)
        self.assertNotEqual(workers[0], owner)
        self.assertEqual(done, [(42, owner)])
        setup.close()
        self.complete(setup)
        source.close.assert_called_once()
        self.assertFalse(user32.IsWindow(setup.window.hwnd))

    def test_control_access_from_worker_is_rejected(self):
        setup = self.setup_window()
        errors = []
        def wrong_thread():
            try:
                setup.window.set_busy(False)
            except RuntimeError as exc:
                errors.append(str(exc))
        worker = threading.Thread(target=wrong_thread)
        worker.start()
        worker.join()
        self.assertEqual(errors, ["Setup controls belong to the UI thread"])

    def test_running_unknown_and_unreadable_record_remain_distinct(self):
        setup = self.setup_window()
        for status, title, details in (("RUNNING", "Close Source Filmmaker to continue", False),
                                      ("UNKNOWN", "Could not check Source Filmmaker", True)):
            setup.error({"failure": core.ProcessRefusal(status, "query detail"), "operation": None,
                         "record_unreadable": False, "detail": "query detail"})
            self.assertEqual(caption(setup.window.children[0]), title)
            self.assertEqual("Details" in labels(setup.window), details)
            self.assertIn("Back to Setup", labels(setup.window))
            self.assertNotIn(status, message(setup.window))
        setup.error({"failure": OSError("record"), "operation": None,
                     "record_unreadable": True, "detail": "unreadable operation record"})
        self.assertIn("cannot determine", caption(setup.window.children[0]))
        self.assertNotIn("Back to Setup", labels(setup.window))

    def test_worker_failure_clears_busy_only_after_worker_exit(self):
        setup = self.setup_window()
        setup.busy = False
        with mock.patch.object(core, "_operation", return_value={"kind": "uninstall"}):
            def fail():
                raise OSError("disposable failure")
            setup.start("Removing", fail, lambda _: self.fail("false success"))
            self.complete(setup)
        self.assertFalse(setup.busy)
        self.assertEqual(caption(setup.window.children[0]), "Removal incomplete")
        self.assertIn("disposable failure", setup.details)

    def test_remaining_helper_selection_uses_worker_and_preserves_completion(self):
        setup = self.setup_window()
        setup.busy = False
        setup.window.set_busy(False)
        path = Path("disposable game/usermod/tools/SFM Character Tools Installer/SCT_Setup.exe")
        result = {"remaining_helper": [core.HELPER], "remaining_directories": ["ordinary/folder"],
                  "authority_remaining": []}
        owner = threading.get_ident()
        calls = []
        with mock.patch.object(core, "_target", return_value=path), \
                mock.patch.object(app, "show_setup_file", side_effect=lambda p: calls.append((p, threading.get_ident()))):
            setup.removed(result)
            title = caption(setup.window.children[0])
            self.assertNotIn("Details", labels(setup.window))
            setup.reveal_setup()
            self.complete(setup)
        self.assertEqual(calls[0][0], path)
        self.assertNotEqual(calls[0][1], owner)
        self.assertEqual(caption(setup.window.children[0]), title)
        self.assertIn("cannot remove its own", message(setup.window))
        self.assertFalse(setup.busy)
        with mock.patch.object(core, "_target", return_value=path), \
                mock.patch.object(core, "_operation", return_value=None), \
                mock.patch.object(app, "show_setup_file", side_effect=OSError("selection denied")):
            setup.reveal_setup()
            self.complete(setup)
        self.assertEqual(caption(setup.window.children[0]), "Could not show the Setup file")
        self.assertIn(str(path), message(setup.window))
        self.assertIn("selection denied", setup.details)
        self.assertIn("Details", labels(setup.window))

    def test_shell_selection_checks_hresult_and_balances_resources(self):
        for case in ("success", "already-initialized", "initialize", "parse", "partial-parse", "null-item", "select"):
            with self.subTest(case=case):
                ole, shell = mock.Mock(), mock.Mock()
                ole.CoInitializeEx.return_value = -2147467259 if case == "initialize" else 1 if case == "already-initialized" else 0
                def parse(path, bind, output, flags, attributes):
                    self.assertIn("Example Library", path)
                    if case not in ("parse", "null-item"):
                        output._obj.value = 1234
                    return -2147467259 if case in ("parse", "partial-parse") else 0
                shell.SHParseDisplayName.side_effect = parse
                shell.SHOpenFolderAndSelectItems.return_value = -2147467259 if case == "select" else 0
                with mock.patch.object(app.ctypes, "WinDLL", side_effect=[ole, shell]), \
                        mock.patch.object(Path, "is_file", return_value=True):
                    if case in ("success", "already-initialized"):
                        app.show_setup_file(Path("Example Library/SCT_Setup.exe"))
                    else:
                        with self.assertRaises(OSError):
                            app.show_setup_file(Path("Example Library/SCT_Setup.exe"))
                self.assertEqual(ole.CoUninitialize.call_count, 0 if case == "initialize" else 1)
                self.assertEqual(ole.CoTaskMemFree.call_count,
                                 1 if case in ("success", "already-initialized", "partial-parse", "select") else 0)
                if shell.SHOpenFolderAndSelectItems.called:
                    item, count, children, flags = shell.SHOpenFolderAndSelectItems.call_args.args
                    self.assertEqual((item.value, count, children, flags), (1234, 0, None, 0))
        with mock.patch.object(Path, "is_file", return_value=False), \
                mock.patch.object(app.ctypes, "WinDLL") as dll:
            with self.assertRaises(FileNotFoundError):
                app.show_setup_file(Path("missing/SCT_Setup.exe"))
            dll.assert_not_called()

    def test_quiet_cleanup_keeps_page_and_reports_failure_without_false_install_failure(self):
        setup = self.setup_window()
        setup.busy = False
        setup.success({"backup": None})
        source = mock.Mock(root=Path("temporary package"))
        setup.prepared = source
        entered, release = threading.Event(), threading.Event()
        def cleanup():
            entered.set()
            self.assertTrue(release.wait(3))
        source.close.side_effect = cleanup
        with mock.patch.object(setup.window, "page", wraps=setup.window.page) as page:
            setup.close()
            self.assertTrue(entered.wait(2))
            self.assertTrue(setup.busy)
            setup.close()
            self.assertEqual(caption(setup.window.children[0]), "Installation complete")
            page.assert_not_called()
            release.set()
            self.complete(setup)
            page.assert_not_called()
        self.assertFalse(user32.IsWindow(setup.window.hwnd))
        failed = self.setup_window()
        failed.busy = False
        failed.removed({"remaining_helper": [], "remaining_directories": [], "authority_remaining": []})
        failed.prepared = mock.Mock(root=Path("temporary package"))
        failed.prepared.close.side_effect = OSError("temporary file locked")
        with mock.patch.object(core, "_operation", return_value=None):
            failed.close()
            self.complete(failed)
        self.assertEqual(caption(failed.window.children[0]), "Could not remove temporary Setup files")
        self.assertIn("completed removal is unaffected", message(failed.window))
        self.assertIn("temporary file locked", failed.details)
        self.assertIn("Temporary package folder:", failed.details)
        self.assertIsNone(failed.prepared)
        self.assertEqual(labels(failed.window), {"Details", "Close"})

    def test_approved_copy_versions_uninstall_and_toolbar_path(self):
        setup = self.setup_window()
        for installed, existing, verb in (("1.0.0", True, "reinstall"),
                                          ("0.9.0", True, "install"), (None, True, "install"),
                                          (None, False, "install")):
            setup.review({"operation": None, "existing": existing, "installed_version": installed,
                          "summary": {"snapshot": {}, "existing": existing, "version": "1.0.0"}})
            text = message(setup.window)
            self.assertIn("Setup will %s SFM Character Tools version 1.0.0.\n\n" % verb, text)
            self.assertNotIn("Custom edits", text)
            self.assertIn("Keep this window open, then click", text)
            self.assertIn("Installation folder:", caption(setup.window.children[1]))
            self.assertEqual("Installed version:" in caption(setup.window.children[1]), bool(installed))
        setup.installed_version = "0.9.0"
        setup.removal_consent({})
        self.assertIn("Installed version: 0.9.0", caption(setup.window.children[1]))
        self.assertIn("Your Animation Groups file and backups will remain.", message(setup.window))
        self.assertEqual(labels(setup.window), {"Uninstall", "Back"})
        setup.success({"backup": None})
        self.assertIn(app.TOOLBAR, message(setup.window))
        self.assertIn("Scripts → kiwifruit → Autoinit Manager", message(setup.window))
        self.assertNotIn("enable the button there", message(setup.window))

    def test_unknown_diagnostics_and_incomplete_operation_are_preserved(self):
        setup = self.setup_window()
        for reason in ("query exception: timed out after 30 seconds", "nonzero exit 5", "unparseable line"):
            setup.error({"failure": core.ProcessRefusal("UNKNOWN", reason),
                         "operation": {"kind": "install"}, "record_unreadable": False, "detail": "recorded error"})
            self.assertEqual(caption(setup.window.children[0]), "Could not check Source Filmmaker")
            self.assertIn("because the Windows process check failed.", message(setup.window))
            self.assertIn("might be open.", message(setup.window))
            self.assertIn("interrupted installation still needs to be completed", message(setup.window))
            self.assertIn(reason, setup.details)
            self.assertEqual(labels(setup.window), {"Back to Setup", "Details", "Close"})

    def test_removal_omits_routine_folders_but_retains_unexpected_files(self):
        setup = self.setup_window()
        setup.removed({"remaining_helper": [], "remaining_directories": ["ordinary/folder"],
                       "authority_remaining": ["artist-notes.txt"]})
        self.assertIn("Details", labels(setup.window))
        self.assertIn("artist-notes.txt", setup.details)
        self.assertNotIn("ordinary/folder", setup.details)

    def test_empty_metadata_does_not_create_a_control_or_vertical_gap(self):
        window = Window("Disposable spacing check")
        self.addCleanup(window.dispose)
        window.page("Complete", "", "Done", [("Close", window.close)])
        self.assertEqual(len(window.children), 3)
        title, body = wt.RECT(), wt.RECT()
        user32.GetWindowRect(window.children[0], ctypes.byref(title))
        user32.GetWindowRect(window.children[1], ctypes.byref(body))
        self.assertAlmostEqual(body.top - title.bottom, window.px(14), delta=1)

    def test_hidden_process_query_preserves_status_and_timeout(self):
        result = mock.Mock(returncode=0, stdout='"sfm.exe","123"')
        with mock.patch.object(process_gate.hooks, "process_query", None), \
                mock.patch.object(process_gate.subprocess, "run", return_value=result) as run:
            self.assertEqual(process_gate.process_status(no_window=True)[0], "RUNNING")
            self.assertEqual(run.call_args.kwargs["creationflags"], process_gate.subprocess.CREATE_NO_WINDOW)
            self.assertEqual(run.call_args.kwargs["timeout"], 30)
            process_gate.process_status()
            self.assertNotIn("creationflags", run.call_args.kwargs)
            result.stdout = "INFO: No tasks are running which match the specified criteria."
            self.assertEqual(process_gate.process_status(no_window=True)[0], "CLEAR")
            result.stdout = ""
            self.assertEqual(process_gate.process_status(no_window=True)[0], "UNKNOWN")
            run.side_effect = process_gate.subprocess.TimeoutExpired("tasklist", 30)
            self.assertEqual(process_gate.process_status(no_window=True)[0], "UNKNOWN")

    def test_long_destination_and_heading_have_measured_space(self):
        setup = self.setup_window()
        long_path = "destination/" * 20
        setup.window.page("Setup cannot determine whether installation is complete", long_path,
                          app.UPDATE.format(version="1.0.0", verb="reinstall") + "\n\n" + app.CLOSE_SFM.format(action="Update / Reinstall"),
                          [("Update / Reinstall", lambda: None), ("Uninstall", lambda: None), ("Close", lambda: None)])
        previous_bottom = 0
        for handle in setup.window.children:
            rect = wt.RECT()
            user32.GetWindowRect(handle, ctypes.byref(rect))
            if handle not in setup.window.buttons:
                self.assertGreaterEqual(rect.top, previous_bottom)
                self.assertGreater(rect.bottom, rect.top)
                previous_bottom = rect.bottom


if __name__ == "__main__":
    unittest.main()
