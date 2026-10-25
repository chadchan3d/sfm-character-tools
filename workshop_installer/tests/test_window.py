"""Hidden native-window checks; no SFM or installer operation is launched."""
import ctypes
import unittest
from ctypes import wintypes as wt
from pathlib import Path
from unittest import mock

from workshop_installer import app, core, stage
from workshop_installer.window import Window, user32

user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]


def caption(handle):
    value = ctypes.create_unicode_buffer(1024)
    user32.GetWindowTextW(handle, value, len(value))
    return value.value


class WindowTests(unittest.TestCase):
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

    def test_named_actions_details_ownership_and_busy_close(self):
        window = Window("Disposable Setup check")
        try:
            called = []
            window.page("SFM Character Tools Setup", "Version included: test", app.UPDATE,
                        [("Update / Reinstall", lambda: called.append("update")),
                         ("Uninstall…", lambda: called.append("remove")), ("Cancel", window.close)])
            self.assertEqual({caption(h) for h in window.buttons}, {"Update / Reinstall", "Uninstall…", "Cancel"})
            window.details("Technical details")
            original = window.details_handle
            window.details("Must not create another details control")
            self.assertEqual(window.details_handle, original)
            window.set_busy(True)
            window._message(window.hwnd, 0x111, 100, 0)
            self.assertEqual(called, [])
            window.set_busy(False)
            window._message(window.hwnd, 0x111, 100, 0)
            self.assertEqual(called, ["update"])
        finally:
            window.dispose()

    def test_missing_payload_still_offers_uninstall(self):
        window = Window("Disposable management check")
        setup = app.SetupWindow.__new__(app.SetupWindow)
        setup.game = Path("game")
        setup.package, setup.prepared = None, None
        setup.helper, setup.window = Path("SCT_Setup.exe"), window
        setup.details, setup.busy = "", False
        try:
            with mock.patch.object(app.core, "_legacy_record_clear"), \
                    mock.patch.object(app.core, "_operation", return_value=None), \
                    mock.patch.object(app.core, "_current_record", return_value=None), \
                    mock.patch.object(app.core, "removal_preview", return_value={app.core.BUTTON: "a" * 64}):
                setup.refresh()
            self.assertIn("Uninstall…", {caption(h) for h in window.buttons})
        finally:
            window.dispose()


if __name__ == "__main__":
    unittest.main()
