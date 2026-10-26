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
        self.assertIn("still uninstall", caption(setup.window.children[2]))

    def test_changed_file_shows_blocked_recovery_without_retry(self):
        setup = self.setup_window()
        with mock.patch.object(core, "_legacy_record_clear"), \
                mock.patch.object(core, "_operation", return_value={"kind": "install"}), \
                mock.patch.object(core, "_resume_states", side_effect=core.RecoveryConflict(core.MASTER)):
            setup.shown()
            self.complete(setup)
        message = caption(setup.window.children[2])
        self.assertIn(core.MASTER, message)
        self.assertIn("Preserve your changes", message)
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
        self.assertIn("Install location:", caption(setup.window.children[1]))
        self.assertIn("Custom edits will not be merged", caption(setup.window.children[2]))
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
                                      ("UNKNOWN", "Setup cannot check whether SFM is closed", True)):
            setup.error({"failure": core.ProcessRefusal(status, "query detail"), "operation": None,
                         "record_unreadable": False, "detail": "query detail"})
            self.assertEqual(caption(setup.window.children[0]), title)
            self.assertEqual("Details" in labels(setup.window), details)
            self.assertIn("Back to Setup", labels(setup.window))
            self.assertNotIn(status, caption(setup.window.children[2]))
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

    def test_remaining_helper_reveals_exact_file_without_deletion(self):
        setup = self.setup_window()
        setup.busy = False
        setup.window.set_busy(False)
        with mock.patch.object(core, "_target", return_value=Path("game/usermod/tools/Setup/SCT_Setup.exe")), \
                mock.patch.object(app.subprocess, "Popen") as launch:
            setup.removed({"remaining_helper": [core.HELPER], "remaining_directories": [], "authority_remaining": []})
            action = next(cb for i, cb in setup.window.actions.items()
                          if caption(next(h for h in setup.window.buttons
                                          if user32.GetDlgCtrlID(h) == i)) == "Show Setup File")
            action()
            argv = launch.call_args.args[0]
            self.assertEqual(argv, ["explorer.exe", "/select,game\\usermod\\tools\\Setup\\SCT_Setup.exe"])
            self.assertIn("cannot remove its own", caption(setup.window.children[2]))

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
                          app.UPDATE + "\n\n" + app.CLOSE_SFM.format(action="Update / Reinstall"),
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
