"""Dependency-free Windows dialog front end for the fixed Workshop installer."""
import argparse
import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from . import core


MB_OK = 0
MB_OKCANCEL = 1
MB_YESNOCANCEL = 3
MB_ICONERROR = 0x10
MB_ICONQUESTION = 0x20
MB_ICONINFORMATION = 0x40
IDOK = 1
IDCANCEL = 2
IDYES = 6
IDNO = 7

_messagebox = ctypes.windll.user32.MessageBoxW
_messagebox.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
_messagebox.restype = ctypes.c_int


def dialog(message, flags=MB_OK):
    return _messagebox(None, message, "SFM Character Tools Setup", flags)


def _manage(game):
    choice = dialog("SFM Character Tools installation management\n\n"
                    "Yes: verify installed files\n"
                    "No: removal and recovery options\n"
                    "Cancel: exit\n\n"
                    "Save your project and close SFM before removal or recovery.",
                    MB_YESNOCANCEL | MB_ICONQUESTION)
    if choice == IDYES:
        result = core.verify(game)
        if result["mismatches"]:
            dialog("%d installed paths differ or are missing.\n\n%s" %
                   (len(result["mismatches"]), "\n".join(result["mismatches"][:12])), MB_ICONINFORMATION)
        else:
            dialog("All %d tracked paths match the installed receipt." % result["files"], MB_ICONINFORMATION)
    elif choice == IDNO:
        action = dialog("Choose maintenance action:\n\n"
                        "Yes: remove unchanged installed files\n"
                        "No: recover an interrupted installation\n"
                        "Cancel: exit", MB_YESNOCANCEL | MB_ICONQUESTION)
        if action == IDCANCEL:
            return
        if action == IDNO:
            if dialog("Restore verified previous files from an incomplete installation?\n"
                      "SFM must be closed.", MB_OKCANCEL | MB_ICONQUESTION) == IDOK:
                dialog(core.recover(game), MB_ICONINFORMATION)
            return
        if dialog("Remove only unchanged files owned by this installation?\n"
                  "Changed files, customized Animation Groups data and presets are preserved.",
                  MB_OKCANCEL | MB_ICONQUESTION) == IDOK:
            result = core.uninstall(game)
            dialog("Removal finished. %d changed or in-use paths were preserved.\n\n%s" %
                   (len(result["preserved"]), "\n".join(result["preserved"][:12])),
                   MB_ICONINFORMATION)


def _install(game, executable):
    prepared = core.prepare(executable.parent / "SFM.Character.Tools.v1.0.0.zip", executable)
    try:
        summary = core.preview(game, prepared)
        if dialog("Install SFM Character Tools v1.0.0 into:\n%s\n\n"
                  "Components: Control Group Normalizer, Character Preset Manager, "
                  "Control Group Updater and CPM toolbar button.\n\n"
                  "%d files are tracked; %d need writing.\n\n"
                  "Autoinit Manager must already be installed. Continue?" %
                  (game, summary["file_count"], summary["write_count"]),
                  MB_OKCANCEL | MB_ICONQUESTION) != IDOK:
            return
        replace = False
        if summary["authority_replacement_needs_consent"]:
            replace = dialog("Existing Animation Groups data differs from the bundled release.\n\n"
                             "Replace the Master TXT, sidecar and manifest as one set? "
                             "Verified copies of existing files will be kept for recovery.\n\n"
                             "Cancel to preserve your current data and stop.",
                             MB_OKCANCEL | MB_ICONQUESTION) == IDOK
            if not replace:
                return
        if dialog("Save your SFM project and close SFM normally now.\n\n"
                  "Click OK only after SFM has exited. The installer will check again "
                  "and refuse if SFM is running or its state cannot be read.",
                  MB_OKCANCEL | MB_ICONQUESTION) != IDOK:
            return
        dialog(core.install(game, prepared, replace_authority=replace,
                            expected_authority=summary["authority_snapshot"]), MB_ICONINFORMATION)
    finally:
        prepared.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", required=True, help="SFM game directory")
    parser.add_argument("--manage", action="store_true")
    args = parser.parse_args(argv)
    try:
        game = core._validate_game(args.game)
        if args.manage:
            _manage(game)
        else:
            record = core._current_record(game)
            if record and record["status"] == "PREPARED":
                if dialog("A previous installation was interrupted.\n\n"
                          "Restore the verified previous files before starting again?\n"
                          "SFM must be closed.", MB_OKCANCEL | MB_ICONQUESTION) == IDOK:
                    dialog(core.recover(game), MB_ICONINFORMATION)
            elif record and record["status"] == "UNINSTALLING":
                dialog("Removal was interrupted. Use Manage Installation to finish it.", MB_ICONERROR)
                return 1
            else:
                _install(game, Path(sys.executable))
    except Exception as exc:
        dialog(str(exc), MB_ICONERROR)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
