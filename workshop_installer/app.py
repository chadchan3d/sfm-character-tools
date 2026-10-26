"""One responsive native Setup window and one finite worker at a time."""
import argparse
import ctypes
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

from . import core
from .window import Window

FRESH = ("Setup will install SFM Character Tools version {version}.\n\n"
         "If an Animation Groups file already exists, Setup will back it up before replacing it.")
UPDATE = ("Setup will {verb} SFM Character Tools version {version}.\n\n"
          "Your current Animation Groups file will be backed up before replacement.")
CLOSE_SFM = ("Close Source Filmmaker. Keep this window open, then click {action}.\n\n"
             "Steam may still show SFM as Running while Setup is open.")
REMOVE = ("Setup will remove the Character Tools programs, scripts, toolbar button, and support files."
          "\n\nYour Animation Groups file and backups will remain.")
TOOLBAR = ("Optional CPM toolbar button\n"
           "Requires Autoinit Manager. Enable ChadChan3D_CPM_ASE_Button under "
           "Scripts → kiwifruit → Autoinit Manager, then restart SFM.")


def timing(stage):
    """Opt-in local qualification markers containing no paths or environment."""
    target = os.environ.get("SCT_SETUP_TIMING_FILE")
    if target:
        try:
            with open(target, "a", encoding="utf-8") as out:
                out.write(json.dumps({"stage": stage, "time": time.time(),
                                      "monotonic": time.perf_counter()}) + "\n")
        except OSError:
            pass


def show_setup_file(path):
    """Select one exact file without Explorer command-line parsing; run on the worker."""
    path = Path(path).absolute()
    if not path.is_file():
        raise FileNotFoundError("The remaining Setup file was not found: " + str(path))
    ole = ctypes.WinDLL("ole32")
    shell = ctypes.WinDLL("shell32")
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    ole.CoInitializeEx.restype = ctypes.c_long
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole.CoTaskMemFree.restype = None
    shell.SHParseDisplayName.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p,
                                        ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulong,
                                        ctypes.POINTER(ctypes.c_ulong)]
    shell.SHParseDisplayName.restype = ctypes.c_long
    shell.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                               ctypes.c_void_p, ctypes.c_ulong]
    shell.SHOpenFolderAndSelectItems.restype = ctypes.c_long

    def checked(hr, action):
        if hr < 0:
            raise OSError("%s failed (HRESULT 0x%08X)." % (action, hr & 0xFFFFFFFF))

    checked(ole.CoInitializeEx(None, 2), "Windows Shell initialization")
    item = ctypes.c_void_p()
    try:
        checked(shell.SHParseDisplayName(str(path), None, ctypes.byref(item), 0, None),
                "Windows Shell path resolution")
        if not item.value:
            raise OSError("Windows Shell did not return the Setup file identity.")
        checked(shell.SHOpenFolderAndSelectItems(item, 0, None, 0), "Windows file selection")
    finally:
        if item.value:
            ole.CoTaskMemFree(item)
        ole.CoUninitialize()


class SetupWindow:
    def __init__(self, game, package, helper):
        self.game, self.package, self.helper = game, package, helper
        self.prepared = None
        self.busy = False
        self.details = ""
        self.worker = None
        self.results = queue.Queue()
        self.completion = None
        self.failure_handler = None
        self.installed_version = None
        self.completed_action = None
        self.window = Window("SFM Character Tools Setup")
        self.window.on_tick = self.poll
        self.window.on_close = self.close
        self.page("Preparing Setup", "Checking the installation package and your installed files. Please wait.", [])
        self.busy = True
        self.window.set_busy(True)

    def page(self, title, message, buttons, metadata="", destination=False, details=""):
        self.details = details
        if details:
            buttons = list(buttons)
            buttons.insert(max(0, len(buttons) - 1), ("Details", self.show_details))
        if destination:
            metadata += ("\n" if metadata else "") + "Installation folder: " + str(self.game / "usermod")
        self.window.page(title, metadata, message, buttons)

    def capture(self):
        if self.prepared is None:
            if not self.package or not self.package.is_file():
                raise core.Refusal("Restore the Workshop download to update or reinstall Character Tools.")
            self.prepared = core.prepare(self.package, self.helper)
        return self.prepared

    def start(self, title, work, completion, message=None, on_error=None):
        if self.worker is not None or self.busy:
            return
        self.busy = True
        if title is not None:
            self.page(title, message or "Please wait. Keep SFM closed until Setup finishes.", [])
        self.window.set_busy(True)
        self.completion = completion
        self.failure_handler = on_error

        def run():
            try:
                value = work()
            except Exception as exc:
                value = self.failure(exc)
            self.results.put(value)

        self.worker = threading.Thread(target=run, name="Setup operation", daemon=False)
        try:
            self.worker.start()
        except Exception:
            self.worker = None
            self.completion = self.failure_handler = None
            self.busy = False
            self.window.set_busy(False)
            raise

    def poll(self):
        if self.worker is None or self.worker.is_alive():
            return
        self.worker.join()
        value = self.results.get_nowait()
        done = self.completion
        failed = self.failure_handler or self.error
        self.worker = self.completion = self.failure_handler = None
        self.busy = False
        self.window.set_busy(False)
        if isinstance(value, dict) and "failure" in value:
            failed(value)
        else:
            done(value)

    def failure(self, exc):
        # Error diagnosis also runs on the worker, never on the window thread.
        try:
            operation = core._operation(self.game)
            unreadable = False
        except Exception as record_error:
            operation, unreadable = None, True
            detail = str(exc) + "\n\nOperation record: " + str(record_error)
        else:
            detail = str(exc)
        return {"failure": exc, "operation": operation, "record_unreadable": unreadable,
                "detail": detail}

    def inspect(self):
        core._legacy_record_clear(self.game)
        operation = core._operation(self.game)
        if operation:
            core._resume_states(self.game, operation)
            available, detail = False, ""
            if operation["kind"] == "install":
                try:
                    p = self.capture()
                    available = p.package == operation["package"] and p.files == operation["files"]
                except Exception as exc:
                    detail = str(exc)
                if not available:
                    detail += "\nRequired package SHA-256: " + operation["package"]
            return {"operation": operation, "available": available, "detail": detail.strip()}
        removal = core.removal_preview(self.game)
        record = core._current_record(self.game)
        existing = bool(record or any(h is not None for p, h in removal.items() if core._program_path(p)))
        state = {"operation": None, "existing": existing,
                 "installed_version": record["version"] if record else None}
        if not self.package or not self.package.is_file():
            state["package_missing"] = True
            return state
        try:
            prepared = self.capture()
        except Exception as exc:
            state["package_error"] = str(exc)
            return state
        try:
            state["summary"] = core.preview(self.game, prepared)
        except Exception as exc:
            state["preview_error"] = str(exc)
        return state

    def refresh(self):
        self.start("Preparing Setup", self.inspect, self.review,
                   "Checking the installation package and your installed files. Please wait.")

    def review(self, state):
        timing("preparation_complete")
        op = state.get("operation")
        if op:
            install = op["kind"] == "install"
            buttons = []
            if not install or state["available"]:
                buttons.append(("Finish Installation" if install else "Finish Uninstall",
                                self.retry if install else self.finish_remove))
            buttons.append(("Close", self.close))
            message = "Keep SFM closed, then finish the interrupted %s." % ("installation" if install else "removal")
            if install and not state["available"]:
                message = "Restore the exact Workshop package used for this unfinished installation, then reopen Setup."
            self.page("Installation incomplete" if install else "Removal incomplete", message,
                      buttons, destination=True, details=state["detail"])
            return
        installed = state["installed_version"]
        self.installed_version = installed
        metadata = "Installed version: " + installed if installed else ""
        buttons = [("Uninstall", self.confirm_remove)] if state["existing"] else []
        buttons.append(("Close", self.close))
        if state.get("package_missing"):
            message = ("Character Tools is installed." if installed else "Character Tools files were found." if state["existing"]
                       else "No Character Tools installation was found.")
            message += " The Workshop package is unavailable, so updating or reinstalling is unavailable."
            if state["existing"]:
                message += "\n\nYou can still uninstall Character Tools."
            message += "\n\nTo install, update or reinstall, restore the Workshop download and open Install or Update from SFM."
            self.page("Manage SFM Character Tools" if state["existing"] else "Workshop package unavailable",
                      message, buttons, metadata=metadata)
            return
        problem = state.get("package_error") or state.get("preview_error")
        if problem:
            self.page("Installation package could not be verified" if state.get("package_error") else "Setup needs attention",
                      "Restore the Workshop package before installing." if state.get("package_error") else problem,
                      buttons, metadata=metadata, details=problem if state.get("package_error") else "")
            return
        summary = state["summary"]
        self.snapshot = summary["snapshot"]
        action = "Update / Reinstall" if summary["existing"] else "Install"
        buttons.insert(0, (action, self.install))
        metadata += ("\n" if metadata else "") + "Package version: " + summary["version"]
        description = UPDATE if summary["existing"] else FRESH
        self.page("Update or reinstall SFM Character Tools" if summary["existing"] else "Install SFM Character Tools",
                  description.format(version=summary["version"],
                                     verb="reinstall" if installed == summary["version"] else "install") +
                  "\n\n" + CLOSE_SFM.format(action=action),
                  buttons, metadata=metadata, destination=True)

    def error(self, failure):
        exc, op = failure["failure"], failure["operation"]
        buttons = [("Back to Setup", self.refresh), ("Close", self.close)]
        detail = failure["detail"]
        if failure["record_unreadable"]:
            title = "Setup cannot determine whether installation is complete"
            message = "The operation record could not be read. Keep SFM closed and preserve the installation records. Open Details for the error."
            buttons = [("Close", self.close)]
        elif isinstance(exc, core.RecoveryConflict):
            title, message = "Recovery blocked", str(exc)
            buttons = [("Close", self.close)]
            detail = ""
        elif isinstance(exc, core.ProcessRefusal):
            if exc.status == "RUNNING":
                title = "Close Source Filmmaker to continue"
                message = ("Source Filmmaker is still open. Close it, but keep this window open. "
                           "Then click Back to Setup.")
                detail = ""
            else:
                title = "Could not check Source Filmmaker"
                message = ("Setup couldn't determine whether Source Filmmaker is running because "
                           "the Windows process check failed.\n\n"
                           "Setup stopped to avoid changing files while SFM might be open.\n\n"
                           "Close SFM if it's open, then click Back to Setup to try again.")
                detail = exc.detail + ("\n\n" + detail if detail != exc.detail else "")
            if op:
                message += "\n\nThe interrupted %s still needs to be completed." % ("removal" if op["kind"] == "uninstall" else "installation")
        elif op:
            title = "Removal incomplete" if op["kind"] == "uninstall" else "Installation incomplete"
            message = "Keep SFM closed. Return to Setup to review and finish the recorded operation."
        else:
            title = "Setup could not complete this action"
            message = "Open Details for the error. Return to Setup to review the installation before trying again."
        self.page(title, message, buttons, details=detail)

    def show_details(self):
        if self.details:
            self.window.details(self.details)

    def install(self):
        self.start("Installing SFM Character Tools…",
                   lambda: core.install(self.game, self.capture(), self.snapshot), self.success)

    def retry(self):
        self.start("Finishing the interrupted installation…",
                   lambda: core.recover(self.game, self.capture()), self.success)

    def success(self, result):
        self.completed_action = "installation"
        buttons = []
        if result["backup"]:
            buttons.append(("Open Backup Folder", lambda: os.startfile(str(core._state_path(self.game, "backups")))))
        buttons.append(("Close", self.close))
        self.page("Installation complete",
                  "Close Setup, then open SFM and choose Scripts → SFM Character Tools.\n\n"
                  + TOOLBAR, buttons)

    def confirm_remove(self):
        self.start("Preparing removal", lambda: core.removal_preview(self.game), self.removal_consent)

    def removal_consent(self, snapshot):
        self.remove_snapshot = snapshot
        metadata = "Installed version: " + self.installed_version if self.installed_version else ""
        self.page("Uninstall SFM Character Tools?", REMOVE + "\n\n" + CLOSE_SFM.format(action="Uninstall"),
                  [("Uninstall", self.finish_remove), ("Back", self.refresh)],
                  metadata=metadata, destination=True)

    def finish_remove(self):
        self.start("Removing SFM Character Tools…",
                   lambda: core.uninstall(self.game, getattr(self, "remove_snapshot", None)), self.removed)

    def removed(self, result):
        self.completed_action = "removal"
        message = "Your Animation Groups file and backups remain."
        buttons = []
        if result["remaining_helper"]:
            message += ("\n\nSetup cannot remove its own running file. To remove it, choose Show Setup File, "
                        "close Setup, then delete SCT_Setup.exe.")
            buttons.append(("Show Setup File", self.reveal_setup))
        message += "\n\nUnsubscribe from the Workshop item to remove its installer menu entry."
        details = []
        if result["authority_remaining"]:
            details.append("Files retained in the sidecar folder:\n" + "\n".join(result["authority_remaining"]))
        buttons.append(("Close", self.close))
        self.page("Character Tools removed", message, buttons, details="\n\n".join(details))

    def reveal_setup(self):
        path = core._target(self.game, core.HELPER)
        def failed(failure):
            self.page("Could not show the Setup file",
                      "File Explorer could not select the remaining Setup file. "
                      "Its location is shown below. Close Setup before deleting it.\n\n" + str(path),
                      [("Show Setup File", self.reveal_setup), ("Close", self.close)],
                      details=failure["detail"])
        self.start(None, lambda: show_setup_file(path), lambda _: None, on_error=failed)

    def close(self):
        if self.busy:
            return
        if self.prepared is not None:
            def cleanup():
                self.prepared.close()
                self.prepared = None
            self.start(None, cleanup, lambda _: self.window.close(), on_error=self.cleanup_failed)
        else:
            self.window.close()

    def cleanup_failed(self, failure):
        detail = failure["detail"] + "\n\nTemporary package folder: " + str(self.prepared.root)
        # A failed temporary cleanup must not prevent exit or be retried by run's finally.
        self.prepared = None
        message = "Setup could not remove its temporary package files. You can close Setup; temporary files may remain."
        if self.completed_action:
            message += "\n\nThe completed %s is unaffected." % self.completed_action
        self.page("Could not remove temporary Setup files", message, [("Close", self.window.close)], details=detail)

    def shown(self):
        timing("first_visible_window")
        self.busy = False
        self.refresh()

    def run(self):
        try:
            self.window.run(self.shown)
        finally:
            if self.worker is not None:
                self.worker.join()
            if self.prepared is not None:
                self.prepared.close()


class _SetupParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        output = file or sys.stderr or sys.stdout
        if message and output is not None:
            output.write(message)


def main(argv=None):
    timing("helper_main")
    parser = _SetupParser()
    parser.add_argument("--game", required=True)
    parser.add_argument("--manage", action="store_true")
    args = parser.parse_args(argv)
    try:
        game = core._validate_game(args.game)
    except Exception as exc:
        window = Window("SFM Character Tools Setup")
        window.page("Setup needs attention", "", "Setup could not use this SFM location.\n\n" + str(exc),
                    [("Close", window.close)])
        window.run()
        return 1
    executable = Path(sys.executable)
    candidates = [executable.parent / core.release.ARCHIVE,
                  game / "workshop" / "scripts" / "sfm" / "mainmenu" /
                  "SFM Character Tools" / "_workshop_installer" / core.release.ARCHIVE]
    package = next((p for p in candidates if p.is_file()), None)
    SetupWindow(game, package, executable).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
